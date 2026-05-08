# pages/ecdf.py — ECDF Analiz Sayfası
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import psycopg2
import os


@st.cache_resource
def get_ext_conn():
    return psycopg2.connect(
        host=os.environ["EXT_DB_HOST"],
        port=int(os.environ["EXT_DB_PORT"]),
        database=os.environ["EXT_DB_NAME"],
        user=os.environ["EXT_DB_USER"],
        password=os.environ["EXT_DB_PASSWORD"],
    )


def ecdf_hesapla(seri: pd.Series):
    temiz = seri.dropna().sort_values().values
    n = len(temiz)
    return temiz, np.arange(1, n + 1) / n


SERILER = [
    ("Z-SCORE 60G",      "z_score_60",         "#e0e0f0"),
    ("Z-SCORE 120G",     "z_score_120",         "#e0e0f0"),
    ("ROBUST Z 60G",     "z_score_robust_60",   "#e0e0f0"),
    ("ROBUST Z 120G",    "z_score_robust_120",  "#e0e0f0"),
]

SIGMA_RENK = [
    (-3, "#e84040", "−3σ"),
    (-2, "#d4820a", "−2σ"),
    ( 2, "#d4820a", "+2σ"),
    ( 3, "#e84040", "+3σ"),
]


def _ecdf_fig(seri: pd.Series, etiket: str, renk: str, gun: int) -> go.Figure:
    x, y = ecdf_hesapla(seri)
    s = seri.dropna()
    asiri    = int((s.abs() > 2).sum())
    cok_asiri= int((s.abs() > 3).sum())

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="lines",
        line=dict(color=renk, width=1.2),
        hovertemplate="z: %{x:.3f} · p: %{y:.1%}<extra></extra>",
    ))

    for sigma, srenk, _ in SIGMA_RENK:
        fig.add_vline(
            x=sigma,
            line_dash="dot",
            line_color=srenk,
            line_width=1,
            opacity=0.6,
        )

    # σ etiketleri (annotation olarak ekle)
    for sigma, srenk, label in SIGMA_RENK:
        fig.add_annotation(
            x=sigma, y=1.04,
            text=label,
            showarrow=False,
            font=dict(size=8, color=srenk, family="IBM Plex Mono"),
            xref="x", yref="paper",
        )

    # İstatistik satırı altta
    stats_text = (
        f"μ  {s.mean():.3f}   "
        f"σ  {s.std():.3f}   "
        f"|z|>2  {asiri}g   "
        f"|z|>3  {cok_asiri}g"
    )
    fig.add_annotation(
        x=0.02, y=-0.18,
        text=stats_text,
        showarrow=False,
        font=dict(size=8, color="#3a3a55", family="IBM Plex Mono"),
        xref="paper", yref="paper",
        align="left",
    )

    fig.update_layout(
        paper_bgcolor="#0c0c13",
        plot_bgcolor="#0f0f18",
        margin=dict(l=36, r=16, t=28, b=36),
        height=220,
        showlegend=False,
        title=dict(
            text=f'<span style="font-size:9px;color:#3a3a55">{etiket}</span>'
                 f'<span style="font-size:9px;color:#2e2e48">    {gun} gün</span>',
            x=0, xanchor="left",
            font=dict(family="IBM Plex Mono", size=9, color="#3a3a55"),
            pad=dict(l=0, t=0),
        ),
        xaxis=dict(
            range=[-4.5, 4.5],
            tickvals=[-3, -2, 0, 2, 3],
            tickfont=dict(size=8, color="#2e2e48", family="IBM Plex Mono"),
            gridcolor="#0f0f18",
            showline=False,
            zeroline=False,
        ),
        yaxis=dict(
            range=[0, 1],
            tickformat=".0%",
            tickvals=[0, 0.25, 0.5, 0.75, 1],
            tickfont=dict(size=8, color="#2e2e48", family="IBM Plex Mono"),
            gridcolor="#131320",
            showline=False,
        ),
        font=dict(family="IBM Plex Mono"),
    )
    return fig


def _anomali_badge(tip):
    renk_map = {
        "anomali_z60":   ("#4d8ef0", "Z60"),
        "anomali_z120":  ("#06b6d4", "Z120"),
        "anomali_rz60":  ("#d4820a", "RZ60"),
        "anomali_rz120": ("#22c55e", "RZ120"),
        "anomali_t":     ("#a07af0", "T"),
    }
    renk, etiket = renk_map.get(tip, ("#3a3a55", tip))
    return (f'<span style="border:1px solid {renk};color:{renk};'
            f'font-size:10px;padding:1px 5px;border-radius:2px">{etiket}</span>')


def goster(secilen: str = None):
    ext_conn = get_ext_conn()

    # Hisse seçici + meta bilgi
    col_sec, col_meta = st.columns([2, 8])
    with col_sec:
        hisseler_df = pd.read_sql(
            "SELECT symbol FROM stocks WHERE is_active = true ORDER BY symbol", ext_conn
        )
        semboller = hisseler_df["symbol"].tolist()
        temiz = secilen.replace(".IS", "") if secilen else None
        default_idx = semboller.index(temiz) if temiz in semboller else 0
        secilen_sembol = st.selectbox(
            "Hisse", semboller, index=default_idx,
            key="ecdf_sec", label_visibility="collapsed",
        )

    id_df = pd.read_sql("SELECT id FROM stocks WHERE symbol = %s", ext_conn, params=(secilen_sembol,))
    if id_df.empty:
        st.warning("Hisse bulunamadı.")
        return
    stock_id = int(id_df["id"].iloc[0])

    df = pd.read_sql("""
        SELECT price_date, z_score_60, z_score_120, z_score_robust_60, z_score_robust_120
        FROM volume_analysis WHERE stock_id = %s ORDER BY price_date
    """, ext_conn, params=(stock_id,))

    if df.empty:
        st.warning(f"{secilen_sembol} için veri bulunamadı.")
        return

    df["price_date"] = pd.to_datetime(df["price_date"])
    gun = len(df)

    with col_meta:
        st.markdown(
            f'<div style="display:flex;gap:20px;align-items:center;padding:6px 0">'
            f'<span style="font-size:10px;color:#2e2e48">pencere</span>'
            f'<span style="font-size:10px;color:#4a4a68">{gun}g</span>'
            f'<span style="font-size:10px;color:#2e2e48">aralık</span>'
            f'<span style="font-size:10px;color:#4a4a68">'
            f'{df["price_date"].min().strftime("%Y-%m-%d")}'
            f' → {df["price_date"].max().strftime("%Y-%m-%d")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── İki kolon: sol = 4 ECDF grafik, sağ = anomali listesi ──
    col_grafik, col_anomali = st.columns([3, 2], gap="large")

    with col_grafik:
        st.markdown(
            '<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:12px 0 12px 0">'
            '<span style="color:#2e2e48;margin-right:8px">§ 1</span>'
            'Empirik Dağılım Analizi</div>',
            unsafe_allow_html=True,
        )
        row1_c1, row1_c2 = st.columns(2)
        row2_c1, row2_c2 = st.columns(2)

        for col, (etiket, kolon, renk) in zip(
            [row1_c1, row1_c2, row2_c1, row2_c2], SERILER
        ):
            with col:
                fig = _ecdf_fig(df[kolon], etiket, renk, gun)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Eşik bilgisi kutusu
        st.markdown(
            '<div style="background:#0f0f18;border:1px solid #1a1a24;border-radius:2px;'
            'padding:10px 14px;margin-top:4px">'
            '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
            'text-transform:uppercase;margin-bottom:6px">Eşik</div>'
            '<div style="font-size:11px;color:#4a4a68">'
            '|z| > 2 = anormal &nbsp;·&nbsp; |z| > 3 = kritik</div>'
            '<div style="font-size:10px;color:#2e2e48;margin-top:4px">'
            'kaynak · volume_analysis</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_anomali:
        anomali_df = pd.read_sql("""
            SELECT baslangic_zaman::date AS tarih, anomali_tipi, skor, durum
            FROM anomali_kayitlari
            WHERE hisse_kodu = %s
            ORDER BY baslangic_zaman DESC
            LIMIT 50
        """, ext_conn, params=(secilen_sembol,))

        kayit_n = len(anomali_df)
        st.markdown(
            f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
            f'margin:12px 0 10px 0">'
            f'<span style="color:#2e2e48;margin-right:8px">§ 2</span>'
            f'Tespit Edilen Anomaliler'
            f'<span style="color:#2e2e48;font-size:10px;margin-left:8px">'
            f'· {kayit_n} kayıt</span></div>',
            unsafe_allow_html=True,
        )

        if anomali_df.empty:
            st.markdown(
                '<div style="font-size:11px;color:#2e2e48;padding:16px;'
                'border:1px solid #1a1a24;border-radius:2px">'
                'Henüz anomali kaydı yok.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                'gap:0;padding:6px 10px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
                '<span>Tarih</span><span>Tip</span>'
                '<span>Skor</span><span>Durum</span></div>',
                unsafe_allow_html=True,
            )
            for _, r in anomali_df.iterrows():
                durum_renk = {
                    "beklemede": "#d4820a",
                    "onaylandi": "#e84040",
                    "ret":       "#22c55e",
                }.get(r["durum"], "#3a3a55")
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                    f'gap:0;padding:8px 10px;border-bottom:1px solid #0f0f18;align-items:center">'
                    f'<span style="font-size:10px;color:#8888a8">{r["tarih"]}</span>'
                    f'<span>{_anomali_badge(r["anomali_tipi"])}</span>'
                    f'<span style="font-size:10px;color:#4a4a68">{r["skor"]:.4f}</span>'
                    f'<span style="font-size:10px;color:{durum_renk}">{r["durum"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
