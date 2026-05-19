"""
Ana pipeline — bir hisse için Faz 1-4'ü zincirler ve sonuçları DB'ye yazar.
"""

from __future__ import annotations
import logging
import pandas as pd
from typing import Optional

from engine.radar1 import radar1_tara, KutuSonucu
from engine.radar2 import radar2_tara, Radar2Sonucu
from engine.hacim_olcum import faz2_hesapla, faz2_hesapla_radar2
from engine.sok_sayaci import faz3_faz4_hesapla

log = logging.getLogger(__name__)


def _kaydet(
    cur,
    stock_id: int,
    symbol: str,
    radar: str,
    kutu_bas,
    kutu_bit,
    zirve,
    dip,
    pencere,
    fiziki,
    efor,
    sok_s,
    sok_y,
    # Radar1 v2.3 kanalı
    m_norm=None,
    kanal_yonu=None,
    trend_m=None,
    trend_c=None,
    ust_offset=None,
    alt_offset=None,
    # Radar2 v2 AVWAP
    milat_tipi=None,
    guncel_avwap=None,
    fiyat_avwap_sapma=None,
    kopus_yonu=None,
    kum_tp_vol=None,
    kum_vol=None,
):
    cur.execute("""
        INSERT INTO fiyat_sikismasi_kayitlari
            (stock_id, symbol, radar,
             kutu_baslangic, kutu_bitis,
             cekirdek_zirve, cekirdek_dip,
             pencere_uzunlugu,
             fiziki_limit, efor_rasyosu,
             sok_sayisi, sok_hacim_yuzdesi,
             m_norm, kanal_yonu,
             trend_m, trend_c,
             kanal_ust_offset, kanal_alt_offset,
             milat_tipi, guncel_avwap, fiyat_avwap_sapma,
             kopus_yonu, kum_tp_vol, kum_vol)
        VALUES
            (%s,%s,%s, %s,%s, %s,%s, %s, %s,%s, %s,%s,
             %s,%s, %s,%s, %s,%s,
             %s,%s,%s, %s,%s,%s)
        ON CONFLICT (stock_id, radar, kutu_baslangic, kutu_bitis) DO UPDATE SET
            cekirdek_zirve     = EXCLUDED.cekirdek_zirve,
            cekirdek_dip       = EXCLUDED.cekirdek_dip,
            pencere_uzunlugu   = EXCLUDED.pencere_uzunlugu,
            fiziki_limit       = EXCLUDED.fiziki_limit,
            efor_rasyosu       = EXCLUDED.efor_rasyosu,
            sok_sayisi         = EXCLUDED.sok_sayisi,
            sok_hacim_yuzdesi  = EXCLUDED.sok_hacim_yuzdesi,
            m_norm             = EXCLUDED.m_norm,
            kanal_yonu         = EXCLUDED.kanal_yonu,
            trend_m            = EXCLUDED.trend_m,
            trend_c            = EXCLUDED.trend_c,
            kanal_ust_offset   = EXCLUDED.kanal_ust_offset,
            kanal_alt_offset   = EXCLUDED.kanal_alt_offset,
            milat_tipi         = EXCLUDED.milat_tipi,
            guncel_avwap       = EXCLUDED.guncel_avwap,
            fiyat_avwap_sapma  = EXCLUDED.fiyat_avwap_sapma,
            kopus_yonu         = EXCLUDED.kopus_yonu,
            kum_tp_vol         = EXCLUDED.kum_tp_vol,
            kum_vol            = EXCLUDED.kum_vol,
            olusturma_zaman    = NOW()
    """, (
        stock_id, symbol, radar,
        kutu_bas, kutu_bit, zirve, dip, pencere,
        fiziki, efor, sok_s, sok_y,
        m_norm, kanal_yonu, trend_m, trend_c, ust_offset, alt_offset,
        milat_tipi, guncel_avwap, fiyat_avwap_sapma,
        kopus_yonu, kum_tp_vol, kum_vol,
    ))


def hisse_tara(
    conn,
    stock_id: int,
    symbol: str,
    df_fiyat: pd.DataFrame,
    anomali_tarihleri: set,
    dolasim_lot: Optional[float],
) -> int:
    """Tek hisse için 4 fazı çalıştır ve DB'ye yaz. Döner: kaydedilen kayıt sayısı."""
    cur = conn.cursor()
    kayit_sayisi = 0

    # ── Radar 1 (v2.3) ───────────────────────────────────────────────────────
    r1 = radar1_tara(df_fiyat.copy())
    if r1 is not None:
        h = faz2_hesapla(df_fiyat.copy(), r1.baslangic, r1.bitis, dolasim_lot)
        s = faz3_faz4_hesapla(df_fiyat.copy(), anomali_tarihleri,
                               r1.baslangic, r1.bitis, h.kutu_hacim)
        son_t     = r1.pencere_uzunlugu - 1
        zirve_son = r1.trend_m * son_t + r1.trend_c + r1.kanal_ust_offset
        dip_son   = r1.trend_m * son_t + r1.trend_c + r1.kanal_alt_offset
        _kaydet(cur, stock_id, symbol, "radar1",
                r1.baslangic.date(), r1.bitis.date(),
                zirve_son, dip_son, r1.pencere_uzunlugu,
                h.fiziki_limit, h.efor_rasyosu,
                s.sok_sayisi, s.sok_hacim_yuzdesi,
                m_norm=r1.m_norm, kanal_yonu=r1.kanal_yonu,
                trend_m=r1.trend_m, trend_c=r1.trend_c,
                ust_offset=r1.kanal_ust_offset, alt_offset=r1.kanal_alt_offset)
        kayit_sayisi += 1
        log.info(f"{symbol} radar1: {r1.pencere_uzunlugu}g {r1.kanal_yonu} "
                 f"efor={h.efor_rasyosu} şok={s.sok_sayisi}")

    # ── Radar 2 v2 ───────────────────────────────────────────────────────────
    r2_liste = radar2_tara(df_fiyat.copy(), anomali_tarihleri)
    for r2 in r2_liste:
        h = faz2_hesapla_radar2(
            df_fiyat.copy(), r2.milat_tarihi, r2.kutu_bitis, dolasim_lot
        )
        s = faz3_faz4_hesapla(
            df_fiyat.copy(), anomali_tarihleri,
            r2.milat_tarihi, r2.kutu_bitis, h.kutu_hacim
        )
        _kaydet(cur, stock_id, symbol, "radar2",
                r2.kutu_baslangic.date(), r2.kutu_bitis.date(),
                None, None,   # cekirdek_zirve / cekirdek_dip — AVWAP modunda yok
                r2.pencere_uzunlugu,
                h.fiziki_limit, h.efor_rasyosu,
                s.sok_sayisi, s.sok_hacim_yuzdesi,
                milat_tipi=r2.milat_tipi,
                guncel_avwap=r2.guncel_avwap,
                fiyat_avwap_sapma=r2.fiyat_avwap_sapma,
                kopus_yonu=r2.kopus_yonu,
                kum_tp_vol=r2.kum_tp_vol,
                kum_vol=int(r2.kum_vol),
                )
        kayit_sayisi += 1
        log.info(f"{symbol} radar2: {r2.milat_tipi} T0={r2.milat_tarihi.date()} "
                 f"{r2.pencere_uzunlugu}g avwap={r2.guncel_avwap} "
                 f"kopus={r2.kopus_yonu}")

    conn.commit()
    cur.close()
    return kayit_sayisi
