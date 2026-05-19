"""
Faz 2 — Kutu içindeki hacim ölçümü.

  2.1 Fiziki Limit  : kutu_hacim / dolasim_lot
  2.2 Efor Rasyosu  : kutu_hacim / (ADV_k * k)
      ADV_k = hissenin kutu öncesi k günlük ortalama hacmi

  Radar 2 v2 varyantı (faz2_hesapla_radar2):
  2.2b Kayan Efor   : son_20g_hacim / (ADV_onceki_20g * 20)
"""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from typing import Optional

EFOR_PENCERE = 20   # kayan efor penceresi (işlem günü)


@dataclass
class HacimSonucu:
    kutu_hacim:     float
    fiziki_limit:   Optional[float]
    efor_rasyosu:   Optional[float]


def faz2_hesapla(
    df_tam: pd.DataFrame,
    kutu_baslangic: pd.Timestamp,
    kutu_bitis: pd.Timestamp,
    dolasim_lot: Optional[float],
) -> HacimSonucu:
    """Radar 1 için standart efor: toplam kutu hacmi / (ADV_k × k)."""
    if "price_date" in df_tam.columns:
        df_tam = df_tam.set_index("price_date")
    df_tam = df_tam.sort_index()

    mask    = (df_tam.index >= kutu_baslangic) & (df_tam.index <= kutu_bitis)
    df_kutu = df_tam.loc[mask]
    if df_kutu.empty:
        return HacimSonucu(kutu_hacim=0.0, fiziki_limit=None, efor_rasyosu=None)

    kutu_hacim = float(df_kutu["hacim"].sum())
    pencere_k  = len(df_kutu)

    fiziki = None
    if dolasim_lot and dolasim_lot > 0:
        fiziki = kutu_hacim / dolasim_lot

    efor = None
    df_oncesi = df_tam.loc[df_tam.index < kutu_baslangic]
    if len(df_oncesi) >= pencere_k:
        adv = float(df_oncesi["hacim"].iloc[-pencere_k:].mean())
        if adv > 0:
            efor = kutu_hacim / (adv * pencere_k)

    return HacimSonucu(kutu_hacim=kutu_hacim, fiziki_limit=fiziki, efor_rasyosu=efor)


def faz2_hesapla_radar2(
    df_tam: pd.DataFrame,
    milat_tarihi: pd.Timestamp,
    kopus_tarihi: pd.Timestamp,
    dolasim_lot: Optional[float],
) -> HacimSonucu:
    """
    Radar 2 v2 için kayan pencere efor:
      efor = son_EFOR_PENCERE_g_hacim / (ADV_onceki × EFOR_PENCERE)
    Emilim süresi EFOR_PENCERE'den kısaysa fallback:
      efor = toplam_emilim_hacim / (ADV_onceki × gecen_gun)
    """
    if "price_date" in df_tam.columns:
        df_tam = df_tam.set_index("price_date")
    df_tam = df_tam.sort_index()

    mask    = (df_tam.index >= milat_tarihi) & (df_tam.index <= kopus_tarihi)
    df_emil = df_tam.loc[mask]
    if df_emil.empty:
        return HacimSonucu(kutu_hacim=0.0, fiziki_limit=None, efor_rasyosu=None)

    emilim_hacim = float(df_emil["hacim"].sum())
    gecen_gun    = len(df_emil)

    fiziki = None
    if dolasim_lot and dolasim_lot > 0:
        fiziki = emilim_hacim / dolasim_lot

    efor = None
    df_oncesi = df_tam.loc[df_tam.index < milat_tarihi]
    if len(df_oncesi) >= EFOR_PENCERE:
        adv_onceki = float(df_oncesi["hacim"].iloc[-EFOR_PENCERE:].mean())
        if adv_onceki > 0:
            if gecen_gun >= EFOR_PENCERE:
                # Kayan pencere: emilim içi son 20g
                son_20g_hacim = float(df_emil["hacim"].iloc[-EFOR_PENCERE:].sum())
                efor = son_20g_hacim / (adv_onceki * EFOR_PENCERE)
            else:
                # Fallback: toplam / (ADV × geçen gün)
                efor = emilim_hacim / (adv_onceki * gecen_gun)

    return HacimSonucu(kutu_hacim=emilim_hacim, fiziki_limit=fiziki, efor_rasyosu=efor)
