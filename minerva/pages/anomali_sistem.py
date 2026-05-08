# pages/sistem.py
import streamlit as st
import pandas as pd
from db import get_conn


def _sec_header(n, title):
    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
        f'margin:20px 0 14px 0">'
        f'<span style="color:#2e2e48;margin-right:8px">§ {n}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def _tablo_baslik(kolonlar):
    cols_css = " ".join(w for _, w in kolonlar)
    headers = "".join(f"<span>{h}</span>" for h, _ in kolonlar)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:{cols_css};gap:0;'
        f'padding:7px 14px;border-bottom:1px solid #1a1a24;'
        f'font-size:9px;color:#2e2e48;letter-spacing:0.12em;text-transform:uppercase">'
        f'{headers}</div>',
        unsafe_allow_html=True,
    )


def goster():
    conn = get_conn()

    _sec_header(1, "Fiyat Verisi Durumu")

    son_veri = pd.read_sql("""
        SELECT s.symbol AS hisse_kodu, MAX(sp.price_date) AS son_tarih,
               COUNT(*) AS kayit_sayisi
        FROM stock_prices sp
        JOIN stocks s ON s.id = sp.stock_id
        WHERE s.is_active = true
        GROUP BY s.symbol ORDER BY s.symbol
    """, conn)

    _tablo_baslik([("Hisse", "150px"), ("Son Veri", "130px"), ("Kayit", "100px")])
    for _, row in son_veri.iterrows():
        st.markdown(
            f'<div style="display:grid;grid-template-columns:150px 130px 100px;gap:0;'
            f'padding:9px 14px;border-bottom:1px solid #0f0f18;align-items:center">'
            f'<span style="font-size:12px;color:#e0e0f0">{row["hisse_kodu"]}</span>'
            f'<span style="font-size:11px;color:#22c55e">{str(row["son_tarih"])}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{int(row["kayit_sayisi"])}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _sec_header(2, "Z-Score (Volume Analysis) Durumu")

    zscore_durum = pd.read_sql("""
        SELECT s.symbol AS hisse_kodu, MAX(va.price_date) AS son_tarih,
               COUNT(*) AS kayit_sayisi
        FROM volume_analysis va
        JOIN stocks s ON s.id = va.stock_id
        WHERE s.is_active = true
        GROUP BY s.symbol ORDER BY s.symbol
    """, conn)

    _tablo_baslik([("Hisse", "150px"), ("Son Tarih", "130px"), ("Kayit", "100px")])
    for _, row in zscore_durum.iterrows():
        st.markdown(
            f'<div style="display:grid;grid-template-columns:150px 130px 100px;gap:0;'
            f'padding:9px 14px;border-bottom:1px solid #0f0f18;align-items:center">'
            f'<span style="font-size:12px;color:#e0e0f0">{row["hisse_kodu"]}</span>'
            f'<span style="font-size:11px;color:#22c55e">{str(row["son_tarih"])}</span>'
            f'<span style="font-size:11px;color:#4a4a68">{int(row["kayit_sayisi"])}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _sec_header(3, "Anomali Kayit Ozeti")

    anomali_ozet = pd.read_sql("""
        SELECT
            COUNT(*) as toplam,
            COUNT(*) FILTER (WHERE durum = 'beklemede') as beklemede,
            COUNT(*) FILTER (WHERE durum = 'onaylandi') as onaylandi,
            COUNT(*) FILTER (WHERE durum = 'ret') as reddedildi,
            COUNT(*) FILTER (WHERE kaynak = 't_dagilimi') as t_dagilimi,
            COUNT(*) FILTER (WHERE kaynak = 'volume_analysis') as ecdf
        FROM anomali_kayitlari
    """, conn)

    r = anomali_ozet.iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, label, val, renk in [
        (c1, "Toplam",     int(r["toplam"]),     "#e0e0f0"),
        (c2, "Beklemede",  int(r["beklemede"]),  "#d4820a"),
        (c3, "Onaylandi",  int(r["onaylandi"]),  "#e84040"),
        (c4, "Reddedildi", int(r["reddedildi"]), "#22c55e"),
        (c5, "ECDF",       int(r["ecdf"]),       "#4d8ef0"),
        (c6, "T-Dagilim",  int(r["t_dagilimi"]), "#a07af0"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:12px 14px">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:22px;color:{renk};font-weight:300">{val:,}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
