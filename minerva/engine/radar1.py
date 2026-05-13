"""
Radar 1 v2.3 — Hacim Ağırlıklı Empirik Kanal Tespiti.

Algoritma (doküman v2.3):
  Adım 1: Tipik Fiyat = (High + Low) / 2
  Adım 2: 2-Pass Robust Log-WLS regresyon
           - Pass 1: Ağırlıksız lineer fit → mutlak sapması en yüksek %10'u outlier say
           - Pass 2: Temiz %90 üzerinde w = log(1 + Volume) ağırlıklı lineer fit
  Adım 3: Detrending → R = Y_tipik − (mX + c)
  Adım 4: ΔR = max(R_core) − min(R_core)
  Adım 5: Ampirik dağılım eşiği (son 250 günde aynı N uzunluklu pencerelerin
           ΔR dağılımının 10. yüzdeliği)
  Adım 6: Dinamik arama — 60g başarılıysa geriye 10'ar gün genişle (eğim işareti
           değişimi veya kural ihlali durana dek); başarısızsa 10'ar gün daral.
  Adım 7: m_norm = m / mean(Y_tipik); ±0.001 eşik → yatay/yukselen/dusen.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


BAZ_GUN             = 60
GENISLEME_ADIM      = 10
MIN_PENCERE         = 10
MAX_PENCERE         = 200
KOPUK_ORAN          = 0.10
THRESHOLD_QUANTILE  = 0.10
YATAY_ESIGI         = 0.001
HISTORY_LEN         = 250


@dataclass
class KutuSonucu:
    baslangic:         pd.Timestamp
    bitis:             pd.Timestamp
    pencere_uzunlugu:  int
    trend_m:           float    # Pass-2 lineer regresyonun eğim katsayısı
    trend_c:           float    # Pass-2 lineer regresyonun sabit terimi
    m_norm:            float    # m / mean(Y_tipik), günlük yüzdesel drift
    kanal_yonu:        str      # 'yatay' | 'yukselen' | 'dusen'
    kanal_ust_offset:  float    # max(R_core)
    kanal_alt_offset:  float    # min(R_core)
    delta_r:           float    # ΔR = ust_offset − alt_offset
    threshold:         float    # bu pencere için ampirik eşik


def _wls_fit(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    """Ağırlıklı en küçük kareler lineer fit. Döner (m, c)."""
    W = w.sum()
    if W <= 0:
        return 0.0, float(y.mean()) if len(y) else 0.0
    xm = (w * x).sum() / W
    ym = (w * y).sum() / W
    dx = x - xm
    var = (w * dx * dx).sum()
    if var <= 0:
        return 0.0, ym
    m = (w * dx * (y - ym)).sum() / var
    c = ym - m * xm
    return float(m), float(c)


def _ols_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Ağırlıksız (ağırlık=1) lineer fit kısayolu."""
    return _wls_fit(x, y, np.ones_like(x, dtype=float))


def _pencere_kanal(
    y_tipik: np.ndarray,
    volume: np.ndarray,
) -> Optional[dict]:
    """
    Verilen N uzunluklu (y_tipik, volume) penceresine 2-pass Log-WLS uygula
    ve kanal istatistiklerini döner. Geçersizse None.
    """
    n = len(y_tipik)
    if n < MIN_PENCERE:
        return None

    x = np.arange(n, dtype=float)

    # Pass 1 — Ağırlıksız kaba fit
    m1, c1 = _ols_fit(x, y_tipik)
    resid1 = y_tipik - (m1 * x + c1)

    # En aşırı %10'u outlier olarak çıkar
    kopuk_n = max(1, int(round(n * KOPUK_ORAN)))
    outlier_idx = np.argsort(np.abs(resid1))[-kopuk_n:]
    keep_mask = np.ones(n, dtype=bool)
    keep_mask[outlier_idx] = False

    x_core = x[keep_mask]
    y_core = y_tipik[keep_mask]
    v_core = volume[keep_mask]
    if len(x_core) < MIN_PENCERE:
        return None

    # Pass 2 — Log-hacim ağırlıklı fit
    w = np.log1p(np.maximum(v_core, 0.0))
    if w.sum() <= 0:
        w = np.ones_like(w)
    m2, c2 = _wls_fit(x_core, y_core, w)

    # Detrending — core veri üzerinde residual
    resid_core = y_core - (m2 * x_core + c2)
    ust_off = float(resid_core.max())
    alt_off = float(resid_core.min())
    delta_r = ust_off - alt_off

    mean_y = float(np.mean(y_tipik))
    m_norm = (m2 / mean_y) if mean_y > 0 else 0.0
    if m_norm >= YATAY_ESIGI:
        yon = "yukselen"
    elif m_norm <= -YATAY_ESIGI:
        yon = "dusen"
    else:
        yon = "yatay"

    return {
        "trend_m": float(m2),
        "trend_c": float(c2),
        "m_norm": float(m_norm),
        "kanal_yonu": yon,
        "ust_off": ust_off,
        "alt_off": alt_off,
        "delta_r": float(delta_r),
    }


def _empirik_esik(
    y_tipik_all: np.ndarray,
    volume_all: np.ndarray,
    N: int,
    son_idx_haric: int,
) -> Optional[float]:
    """
    Son 250 günlük periyot içinde N uzunluklu kayan pencerelerin ΔR dağılımını
    çıkar, 10. yüzdeliği döner.

    son_idx_haric: bu indeks (mevcut test penceresinin başı) ve sonrası dağılıma
                   dahil edilmez — leakage önlemek için.
    """
    M = len(y_tipik_all)
    # Geçmiş havuz: son 250 günden, ama mevcut pencereyi içermeden
    havuz_son = max(0, son_idx_haric)
    havuz_bas = max(0, havuz_son - HISTORY_LEN)
    havuz_y = y_tipik_all[havuz_bas:havuz_son]
    havuz_v = volume_all[havuz_bas:havuz_son]

    if len(havuz_y) < N + MIN_PENCERE:
        return None

    deltalar: list[float] = []
    # Kayan pencere — her başlangıç için bir ΔR
    for i in range(0, len(havuz_y) - N + 1):
        sonuc = _pencere_kanal(havuz_y[i:i+N], havuz_v[i:i+N])
        if sonuc is not None:
            deltalar.append(sonuc["delta_r"])

    if len(deltalar) < 10:
        return None
    return float(np.quantile(deltalar, THRESHOLD_QUANTILE))


def _kutu_olustur(
    y_tipik_all: np.ndarray,
    volume_all: np.ndarray,
    tarihler: pd.DatetimeIndex,
    N: int,
) -> Optional[tuple[KutuSonucu, dict]]:
    """
    Son N günlük pencere için kanal hesabı + ampirik eşik testi.
    Test geçerse (KutuSonucu, ham_kanal_dict) döner.
    """
    M = len(y_tipik_all)
    if N > M or N < MIN_PENCERE:
        return None

    bas_idx = M - N
    y_win = y_tipik_all[bas_idx:]
    v_win = volume_all[bas_idx:]

    kanal = _pencere_kanal(y_win, v_win)
    if kanal is None:
        return None

    esik = _empirik_esik(y_tipik_all, volume_all, N, son_idx_haric=bas_idx)
    if esik is None:
        return None
    if kanal["delta_r"] > esik:
        return None

    sonuc = KutuSonucu(
        baslangic=tarihler[bas_idx],
        bitis=tarihler[-1],
        pencere_uzunlugu=N,
        trend_m=kanal["trend_m"],
        trend_c=kanal["trend_c"],
        m_norm=kanal["m_norm"],
        kanal_yonu=kanal["kanal_yonu"],
        kanal_ust_offset=kanal["ust_off"],
        kanal_alt_offset=kanal["alt_off"],
        delta_r=kanal["delta_r"],
        threshold=esik,
    )
    return sonuc, kanal


def radar1_tara(df: pd.DataFrame) -> Optional[KutuSonucu]:
    """
    df: 'price_date' (index ya da sütun), 'yuksek', 'dusuk', 'hacim' sütunlu OHLCV.
        Tarih sıralı (eskiden yeniye).

    Döner: KutuSonucu veya None.
    """
    if "price_date" in df.columns:
        df = df.set_index("price_date")
    df = df.sort_index()

    # Tipik fiyat = (H+L)/2
    if "yuksek" not in df.columns or "dusuk" not in df.columns:
        return None
    y_tipik = ((df["yuksek"] + df["dusuk"]) / 2.0).to_numpy(dtype=float)
    volume = df["hacim"].to_numpy(dtype=float) if "hacim" in df.columns else np.ones(len(df))
    tarihler = df.index

    M = len(y_tipik)
    if M < MIN_PENCERE:
        return None

    # Baz test
    baz_N = min(BAZ_GUN, M)
    baz = _kutu_olustur(y_tipik, volume, tarihler, baz_N)

    if baz is not None:
        # Genişleme — eğim işareti değişimini veya kural ihlalini izle
        son_gecerli, son_kanal = baz
        son_sign = np.sign(son_kanal["trend_m"])
        N = baz_N + GENISLEME_ADIM
        while N <= min(M, MAX_PENCERE):
            aday = _kutu_olustur(y_tipik, volume, tarihler, N)
            if aday is None:
                break
            aday_sonuc, aday_kanal = aday
            aday_sign = np.sign(aday_kanal["trend_m"])
            # Eğim işareti değişti mi? (yatay → 0, izin verilir; aksi durumda dur)
            if son_sign != 0 and aday_sign != 0 and aday_sign != son_sign:
                break
            son_gecerli = aday_sonuc
            son_kanal = aday_kanal
            son_sign = aday_sign
            N += GENISLEME_ADIM
        return son_gecerli

    # Daralma
    N = BAZ_GUN - GENISLEME_ADIM
    while N >= MIN_PENCERE:
        aday = _kutu_olustur(y_tipik, volume, tarihler, N)
        if aday is not None:
            return aday[0]
        N -= GENISLEME_ADIM
    return None
