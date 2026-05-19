"""
Faz 1 Radar 2 v2 — AVWAP Bazlı Teslimiyet & Emilim Tespiti

Milat (T0) tespiti: devasa hacim anomalisi günlerinde 4 senaryo kontrol edilir.
Emilim izleme: T0'dan itibaren kümülatif AVWAP hesaplanır; ATR bazlı kopuş testi.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ── Sabitler ──────────────────────────────────────────────────────────────────
MILAT_KORUMA_SURESI  = 10     # işlem günü — çoklu milat koruma penceresi
ATR_CARPANI_KARA_GUN = 2.0    # Senaryo 2: düşüş >= 2×ATR
ATR_CARPANI_GAP      = 1.5    # Senaryo 3: gap >= 1.5×ATR
TAVAN_FILTRE         = 0.92   # Senaryo 2: Close < High × 0.92
DOJI_GOVDE_ORANI     = 0.20   # Senaryo 4: gövde <= %20 × dalgalanma
FITIL_PERCENTILE     = 95     # Senaryo 1: alt fitil oranı %95 üstü

KOPUS_ATR_CARPANI    = 2.0    # kopuş bandı = AVWAP ± 2×ATR
KOPUS_ONAY_GUN       = 2      # 2 ardışık kapanış gerekli
MAX_IZLEME_GUN       = 120    # ~6 ay, sonra zaman_asimi
MIN_VERI_GUN         = 60     # bundan az veri → devre dışı


@dataclass
class Radar2Sonucu:
    milat_tarihi:      pd.Timestamp
    kopus_tarihi:      Optional[pd.Timestamp]   # None → hâlâ açık
    milat_tipi:        str                      # savas_mumu/kara_gun/gap_down/doji
    guncel_avwap:      float
    fiyat_avwap_sapma: float
    kopus_yonu:        Optional[str]            # yukari/asagi/zaman_asimi/None
    pencere_uzunlugu:  int
    kum_tp_vol:        float
    kum_vol:           float

    # Geriye uyumluluk — tarama.py bu alan adlarını kullanır
    @property
    def kutu_baslangic(self) -> pd.Timestamp:
        return self.milat_tarihi

    @property
    def kutu_bitis(self) -> pd.Timestamp:
        return self.kopus_tarihi if self.kopus_tarihi is not None else self.milat_tarihi

    # v2'de statik sınır yok
    ust_sinir: Optional[float] = None
    alt_sinir: Optional[float] = None


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _atr_hesapla(df: pd.DataFrame, n: int) -> pd.Series:
    """N günlük Average True Range."""
    h = df["yuksek"]
    l = df["dusuk"]
    c = df["kapanis"].shift(1)
    tr = pd.concat([(h - l), (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=max(1, n // 2)).mean()


def _fitil_p95(df: pd.DataFrame, k: int) -> float:
    """Alt fitil oranının k günlük %95 persantili."""
    son = df.tail(k).copy()
    aralik = (son["yuksek"] - son["dusuk"]).replace(0, np.nan)
    alt_fitil = (son[["acilis", "kapanis"]].min(axis=1) - son["dusuk"]).clip(lower=0)
    oran = (alt_fitil / aralik).dropna()
    return float(np.percentile(oran, FITIL_PERCENTILE)) if len(oran) >= 10 else 0.30


def _milat_tipi_belirle(
    row: pd.Series,
    prev_kap: float,
    atr: float,
    fitil_p95_val: float,
) -> Optional[str]:
    """4 senaryodan hangisi → milat tipi. None = milat değil."""
    kap    = float(row["kapanis"])
    acilis = float(row["acilis"])
    yuk    = float(row["yuksek"])
    dus    = float(row["dusuk"])
    aralik = yuk - dus

    # Senaryo 1 — Savaş Mumu (adaptif alt fitil)
    if aralik > 0:
        alt_fitil   = max(0.0, min(acilis, kap) - dus)
        fitil_orani = alt_fitil / aralik
        if fitil_orani >= fitil_p95_val:
            return "savas_mumu"

    # Senaryo 3 — Gap Down (mumun rengine bakılmaz)
    if atr > 0 and (prev_kap - acilis) >= ATR_CARPANI_GAP * atr:
        return "gap_down"

    # Senaryo 2 — Kara Gün (ATR bazlı sert düşüş)
    dusus = max(acilis - kap, prev_kap - kap)
    if atr > 0 and dusus >= ATR_CARPANI_KARA_GUN * atr and kap < yuk * TAVAN_FILTRE:
        return "kara_gun"

    # Senaryo 4 — Doji (emilim patı)
    govde = abs(kap - acilis)
    if aralik > 0 and govde <= DOJI_GOVDE_ORANI * aralik:
        return "doji"

    return None


# ── Ana tarama fonksiyonu ─────────────────────────────────────────────────────

def radar2_tara(df: pd.DataFrame, anomali_tarihleri: set) -> list[Radar2Sonucu]:
    """
    df               : price_date (index ya da sütun) + OHLCV sütunları.
    anomali_tarihleri: set of date — Faz A onaylı hacim anomalisi günleri.
    Döner: Radar2Sonucu listesi.
    """
    if "price_date" in df.columns:
        df = df.set_index("price_date")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index)

    if len(df) < MIN_VERI_GUN:
        return []

    # Adaptif ATR + fitil percentile penceresi
    n_veri = len(df)
    atr_n  = 60
    for esik in [250, 120, 60]:
        if n_veri >= esik:
            atr_n = esik
            break

    atr_seri      = _atr_hesapla(df, atr_n)
    fitil_p95_val = _fitil_p95(df, atr_n)
    tarihler      = df.index.tolist()
    sonuclar: list[Radar2Sonucu] = []

    # Aktif milat durumu
    aktif: Optional[dict] = None
    kopus_aday_gun = 0
    kopus_aday_yon: Optional[str] = None

    for i, tarih in enumerate(tarihler):
        if i == 0:
            continue

        row      = df.loc[tarih]
        kap      = float(row["kapanis"])
        yuk      = float(row["yuksek"])
        dus      = float(row["dusuk"])
        hacim    = float(row["hacim"])
        prev_kap = float(df.iloc[i - 1]["kapanis"])

        atr_raw  = atr_seri.iloc[i]
        atr      = float(atr_raw) if pd.notna(atr_raw) and atr_raw > 0 else 1.0

        # ── Aktif milat güncelle ──────────────────────────────────────────
        if aktif is not None:
            y_tipik = (yuk + dus + kap) / 3
            if hacim > 0:
                aktif["kum_tp_vol"] += y_tipik * hacim
                aktif["kum_vol"]    += hacim
            avwap = aktif["kum_tp_vol"] / aktif["kum_vol"] if aktif["kum_vol"] > 0 else kap
            aktif["avwap"]       = avwap
            aktif["son_kap"]     = kap
            aktif["gecen_gun"]  += 1

            sapma        = (kap - avwap) / avwap * 100 if avwap > 0 else 0.0
            kopus_esigi  = KOPUS_ATR_CARPANI * atr

            # Kopuş yönü kontrolü
            yon: Optional[str] = None
            if kap > avwap + kopus_esigi:
                yon = "yukari"
            elif kap < avwap - kopus_esigi:
                yon = "asagi"

            if yon:
                if yon == kopus_aday_yon:
                    kopus_aday_gun += 1
                else:
                    kopus_aday_gun = 1
                    kopus_aday_yon = yon

                if kopus_aday_gun >= KOPUS_ONAY_GUN:
                    kopus_t = tarihler[i - KOPUS_ONAY_GUN + 1]
                    sonuclar.append(Radar2Sonucu(
                        milat_tarihi=aktif["milat_tarihi"],
                        kopus_tarihi=kopus_t,
                        milat_tipi=aktif["milat_tipi"],
                        guncel_avwap=round(avwap, 4),
                        fiyat_avwap_sapma=round(sapma, 4),
                        kopus_yonu=yon,
                        pencere_uzunlugu=aktif["gecen_gun"],
                        kum_tp_vol=aktif["kum_tp_vol"],
                        kum_vol=aktif["kum_vol"],
                    ))
                    aktif          = None
                    kopus_aday_gun = 0
                    kopus_aday_yon = None
                    continue
            else:
                kopus_aday_gun = 0
                kopus_aday_yon = None

            # Zaman aşımı
            if aktif is not None and aktif["gecen_gun"] >= MAX_IZLEME_GUN:
                sonuclar.append(Radar2Sonucu(
                    milat_tarihi=aktif["milat_tarihi"],
                    kopus_tarihi=tarih,
                    milat_tipi=aktif["milat_tipi"],
                    guncel_avwap=round(avwap, 4),
                    fiyat_avwap_sapma=round(sapma, 4),
                    kopus_yonu="zaman_asimi",
                    pencere_uzunlugu=aktif["gecen_gun"],
                    kum_tp_vol=aktif["kum_tp_vol"],
                    kum_vol=aktif["kum_vol"],
                ))
                aktif          = None
                kopus_aday_gun = 0
                kopus_aday_yon = None
                continue

        # ── Yeni milat tespiti ────────────────────────────────────────────
        if tarih.date() not in anomali_tarihleri:
            continue

        milat_tipi = _milat_tipi_belirle(row, prev_kap, atr, fitil_p95_val)
        if milat_tipi is None:
            continue

        # Çoklu milat yönetimi
        if aktif is not None:
            if aktif["gecen_gun"] < MILAT_KORUMA_SURESI:
                continue  # koruma süresi — yeni milatı bırak
            # Eski milat kapat, yeni aç
            avwap = aktif["avwap"]
            sapma = (aktif["son_kap"] - avwap) / avwap * 100 if avwap > 0 else 0.0
            sonuclar.append(Radar2Sonucu(
                milat_tarihi=aktif["milat_tarihi"],
                kopus_tarihi=tarihler[i - 1],
                milat_tipi=aktif["milat_tipi"],
                guncel_avwap=round(avwap, 4),
                fiyat_avwap_sapma=round(sapma, 4),
                kopus_yonu=None,
                pencere_uzunlugu=aktif["gecen_gun"],
                kum_tp_vol=aktif["kum_tp_vol"],
                kum_vol=aktif["kum_vol"],
            ))
            aktif          = None
            kopus_aday_gun = 0
            kopus_aday_yon = None

        # Yeni milat aç
        y_tipik = (yuk + dus + kap) / 3
        aktif = {
            "milat_tarihi": tarih,
            "milat_tipi":   milat_tipi,
            "kum_tp_vol":   y_tipik * hacim if hacim > 0 else y_tipik,
            "kum_vol":      hacim if hacim > 0 else 1.0,
            "avwap":        y_tipik,
            "son_kap":      kap,
            "gecen_gun":    1,
        }
        kopus_aday_gun = 0
        kopus_aday_yon = None

    # Açık kalan milat — veri son gününe kapat
    if aktif is not None:
        avwap = aktif["avwap"]
        sapma = (aktif["son_kap"] - avwap) / avwap * 100 if avwap > 0 else 0.0
        son_t = tarihler[-1] if tarihler else aktif["milat_tarihi"]
        sonuclar.append(Radar2Sonucu(
            milat_tarihi=aktif["milat_tarihi"],
            kopus_tarihi=son_t,
            milat_tipi=aktif["milat_tipi"],
            guncel_avwap=round(avwap, 4),
            fiyat_avwap_sapma=round(sapma, 4),
            kopus_yonu=None,
            pencere_uzunlugu=aktif["gecen_gun"],
            kum_tp_vol=aktif["kum_tp_vol"],
            kum_vol=aktif["kum_vol"],
        ))

    return sonuclar
