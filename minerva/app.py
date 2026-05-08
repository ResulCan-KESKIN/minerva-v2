import streamlit as st
import pandas as pd
from db import get_conn
from pages import (
    anomali_gunluk, anomali_en_aktif, anomali_genel_bakis, anomali_hisse_detay,
    anomali_degerlendirme, anomali_ecdf, anomali_backtest, anomali_sistem,
    sikisma_genel_bakis, sikisma_hisse_detay,
)

st.set_page_config(
    page_title="Minerva",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: #0c0c13 !important;
    color: #c0c0d0;
}
.stApp { background-color: #0c0c13 !important; }
.block-container { padding-top: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stToolbar"]     { display: none !important; }
header[data-testid="stHeader"]   { display: none !important; }
footer { display: none !important; }

div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
    display: flex !important; flex-direction: row !important;
    gap: 0 !important; flex-wrap: nowrap !important;
    border-bottom: 1px solid #1a1a24 !important;
    padding: 0 !important; margin: 0 !important;
    background: transparent !important;
}
div[data-testid="stRadio"] label {
    display: flex !important; align-items: center !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #3a3a55 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    padding: 9px 16px 10px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important; cursor: pointer !important;
    white-space: nowrap !important; background: transparent !important;
    transition: color 0.1s !important;
}
div[data-testid="stRadio"] label:hover { color: #8888a8 !important; }
div[data-testid="stRadio"] label:has(input:checked) {
    color: #e0e0f0 !important;
    border-bottom: 2px solid #4d8ef0 !important;
}
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
div[data-testid="stRadio"] label > p { margin: 0 !important; }

.stButton > button {
    background: transparent !important; border: 1px solid #1e1e30 !important;
    color: #4a4a68 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important; border-radius: 2px !important;
    padding: 4px 12px !important;
}
.stButton > button:hover {
    border-color: #4d8ef0 !important; color: #4d8ef0 !important;
    background: #0d1a2e !important;
}
.stButton > button[kind="primary"] {
    background: #0d1a2e !important; border-color: #4d8ef0 !important;
    color: #4d8ef0 !important;
}
.stButton > button[kind="primary"]:hover { background: #152438 !important; }

div[data-baseweb="select"] > div {
    background: #0c0c13 !important; border: 1px solid #1e1e30 !important;
    border-radius: 2px !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #8888a8 !important; min-height: 32px !important;
}
div[data-baseweb="select"] svg { color: #3a3a55 !important; }
[data-baseweb="popover"] { background: #12121e !important; border: 1px solid #1e1e30 !important; }
[role="option"] {
    background: #12121e !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #8888a8 !important;
}
[role="option"]:hover { background: #1a1a2e !important; color: #e0e0f0 !important; }
[aria-selected="true"] { background: #1a1a2e !important; color: #4d8ef0 !important; }

input[type="date"], div[data-baseweb="input"] input {
    background: #0c0c13 !important; border: 1px solid #1e1e30 !important;
    border-radius: 2px !important; color: #8888a8 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; padding: 4px 8px !important;
}
textarea {
    background: #0c0c13 !important; border: 1px solid #1e1e30 !important;
    color: #c0c0d0 !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; border-radius: 2px !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important; border-bottom: 1px solid #1a1a24 !important; gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important;
    letter-spacing: 0.1em !important; color: #3a3a55 !important;
    text-transform: uppercase !important; padding: 8px 14px !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] { color: #e0e0f0 !important; }
.stTabs [data-baseweb="tab-border"] { background: #4d8ef0 !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 16px 0 0 !important; }

.stProgress > div > div { background: #4d8ef0 !important; border-radius: 0 !important; }
.stProgress > div { background: #1a1a24 !important; border-radius: 0 !important; height: 2px !important; }

.stDataFrame iframe { border: 1px solid #1a1a24 !important; }
[data-testid="stDataFrame"] div {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
}

div[data-testid="stExpander"] {
    border: 1px solid #1a1a24 !important; border-radius: 2px !important;
    background: #0f0f18 !important;
}
div[data-testid="stExpander"] summary {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
    color: #4a4a68 !important; padding: 8px 12px !important;
}

div[data-testid="stInfo"], div[data-testid="stWarning"], div[data-testid="stError"] {
    background: #0f0f18 !important; border-radius: 2px !important;
    font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
}

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #0c0c13; }
::-webkit-scrollbar-thumb { background: #1e1e30; border-radius: 1px; }
::-webkit-scrollbar-thumb:hover { background: #2e2e44; }

div[data-testid="stVerticalBlock"] > div { padding-top: 0 !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def _anomali_stats():
    conn = get_conn()
    return pd.read_sql("""
        SELECT
            (SELECT COUNT(*) FROM stocks WHERE is_active = true) AS hisse_sayisi,
            COUNT(*)                                              AS toplam,
            COUNT(*) FILTER (WHERE durum = 'beklemede')          AS beklemede,
            COUNT(*) FILTER (WHERE durum = 'onaylandi')          AS onaylandi,
            MAX(baslangic_zaman)                                  AS son_guncelleme
        FROM anomali_kayitlari
    """, conn).iloc[0]


@st.cache_data(ttl=300)
def _sikisma_stats():
    conn = get_conn()
    from data_access import ozet_metrikler_cek
    return ozet_metrikler_cek(conn)


@st.cache_data(ttl=300)
def _hisse_listesi():
    conn = get_conn()
    return pd.read_sql(
        "SELECT symbol FROM stocks WHERE is_active = true ORDER BY symbol", conn
    )["symbol"].tolist()


# ── Module seçici (session state ile kalıcı) ──
if "modul" not in st.session_state:
    st.session_state["modul"] = "FAZ A"

try:
    hisseler = _hisse_listesi()
except Exception:
    hisseler = []

# ── Stats ──
try:
    sa = _anomali_stats()
    a_hisse   = int(sa["hisse_sayisi"])
    a_toplam  = int(sa["toplam"])
    a_bekl    = int(sa["beklemede"])
    a_onayli  = int(sa["onaylandi"])
    a_son     = sa["son_guncelleme"]
    a_son_str = a_son.strftime("%Y-%m-%d %H:%M") if a_son is not None else "—"
except Exception:
    a_hisse = a_toplam = a_bekl = a_onayli = 0
    a_son_str = "—"

try:
    sb = _sikisma_stats()
    b_hisse  = int(sb.get("hisse_sayisi", 0))
    b_toplam = int(sb.get("toplam_sikisma", 0))
    b_son    = sb.get("son_guncelleme")
    b_son_str = str(b_son)[:10] if b_son else "—"
except Exception:
    b_hisse = b_toplam = 0
    b_son_str = "—"

modul = st.session_state["modul"]
son_str = a_son_str if modul == "FAZ A" else b_son_str

# ── Header ──
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0 0 0">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:22px;height:22px;border-radius:50%;background:#4d8ef0;
                display:flex;align-items:center;justify-content:center;
                font-size:11px;font-weight:500;color:#fff;flex-shrink:0">M</div>
    <span style="font-size:13px;font-weight:500;color:#e0e0f0;letter-spacing:0.04em">Minerva</span>
    <span style="color:#1e1e30;font-size:13px">·</span>
    <span style="font-size:11px;color:#{'4d8ef0' if modul == 'FAZ A' else 'd4820a'};letter-spacing:0.06em">{modul}</span>
    <span style="color:#1e1e30;font-size:11px">·</span>
    <span style="font-size:11px;color:#3a3a55;letter-spacing:0.06em">
      {'ANOMALİ TESPİTİ' if modul == 'FAZ A' else 'FİYAT SIKIŞ MASI'}
    </span>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <span style="font-size:10px;color:#3a3a55;letter-spacing:0.06em">
      piyasa <span style="color:#6a6a88">BIST</span>
    </span>
    <span style="font-size:10px;color:#3a3a55">·</span>
    <span style="font-size:10px;color:#3a3a55;letter-spacing:0.06em">
      son güncelleme <span style="color:#6a6a88">{son_str}</span>
    </span>
    <span style="font-size:10px;color:#3a3a55">·</span>
    <span style="font-size:10px;color:#22c55e;letter-spacing:0.06em">● ready</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Module toggle + Hisse seçici ──
col_mod, col_nav, col_hisse = st.columns([2, 7, 2])

with col_mod:
    yeni_modul = st.radio(
        "modul",
        ["FAZ A", "FAZ B"],
        horizontal=True,
        label_visibility="collapsed",
        key="modul_radio",
        index=0 if modul == "FAZ A" else 1,
    )
    if yeni_modul != modul:
        st.session_state["modul"] = yeni_modul
        st.rerun()

with col_nav:
    if modul == "FAZ A":
        sayfa = st.radio(
            "nav",
            ["Gunluk", "En Aktif", "Genel Bakis", "Hisse Detay",
             "Degerlendirme", "ECDF", "Backtest", "Sistem"],
            horizontal=True,
            label_visibility="collapsed",
            key="nav_faz_a",
        )
    else:
        sayfa = st.radio(
            "nav",
            ["Genel Bakis", "Hisse Detay"],
            horizontal=True,
            label_visibility="collapsed",
            key="nav_faz_b",
        )

with col_hisse:
    secilen = st.selectbox(
        "hisse", hisseler,
        label_visibility="collapsed",
        key="nav_hisse",
    )

# ── Status bar ──
if modul == "FAZ A":
    st.markdown(f"""
<div style="font-size:10px;color:#2e2e48;letter-spacing:0.06em;
            padding:5px 0 12px 0;border-bottom:1px solid #12121e;
            display:flex;justify-content:space-between">
  <span>
    takip <span style="color:#4a4a68">{a_hisse}</span> hisse
    &nbsp;·&nbsp; toplam <span style="color:#4a4a68">{a_toplam:,}</span>
    &nbsp;·&nbsp; beklemede <span style="color:#d4820a">{a_bekl:,}</span>
    &nbsp;·&nbsp; onaylı <span style="color:#4a4a68">{a_onayli}</span>
    &nbsp;·&nbsp; kaynak <span style="color:#4a4a68">volume_analysis · z-rz · 60g-120g</span>
  </span>
  <span style="color:#2e2e48">ticker — {secilen}</span>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="font-size:10px;color:#2e2e48;letter-spacing:0.06em;
            padding:5px 0 12px 0;border-bottom:1px solid #12121e;
            display:flex;justify-content:space-between">
  <span>
    takip <span style="color:#4a4a68">{b_hisse}</span> hisse
    &nbsp;·&nbsp; toplam sıkışma <span style="color:#4a4a68">{b_toplam:,}</span>
    &nbsp;·&nbsp; kaynak <span style="color:#4a4a68">stock_prices · anomali_kayitlari</span>
  </span>
  <span style="color:#2e2e48">ticker — {secilen}</span>
</div>
""", unsafe_allow_html=True)

# ── Page routing ──
if modul == "FAZ A":
    if sayfa == "Gunluk":
        anomali_gunluk.goster()
    elif sayfa == "En Aktif":
        anomali_en_aktif.goster()
    elif sayfa == "Genel Bakis":
        anomali_genel_bakis.goster()
    elif sayfa == "Hisse Detay":
        anomali_hisse_detay.goster(secilen)
    elif sayfa == "Degerlendirme":
        anomali_degerlendirme.goster(secilen)
    elif sayfa == "ECDF":
        anomali_ecdf.goster(secilen)
    elif sayfa == "Backtest":
        anomali_backtest.goster()
    elif sayfa == "Sistem":
        anomali_sistem.goster()
else:
    if sayfa == "Genel Bakis":
        sikisma_genel_bakis.goster()
    elif sayfa == "Hisse Detay":
        sikisma_hisse_detay.goster(secilen)

# ── Footer ──
if modul == "FAZ A":
    st.markdown(f"""
<div style="margin-top:40px;padding:8px 0;border-top:1px solid #12121e;
            display:flex;justify-content:space-between;align-items:center">
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">
    <span style="color:#22c55e">●</span>
    &nbsp;db · synced &nbsp;·&nbsp; queue <span style="color:#2e2e48">{a_bekl:,}</span>
  </span>
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">
    cmd: <span style="color:#2e2e48">j/k</span> sonraki/önceki
    &nbsp;·&nbsp; <span style="color:#2e2e48">a</span> onayla
    &nbsp;·&nbsp; <span style="color:#2e2e48">r</span> reddet
  </span>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div style="margin-top:40px;padding:8px 0;border-top:1px solid #12121e;
            display:flex;justify-content:space-between;align-items:center">
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">
    <span style="color:#22c55e">●</span>
    &nbsp;fiyat sıkışması — radar1 · radar2 · faz 2-3-4
  </span>
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">Minerva FAZ B</span>
</div>
""", unsafe_allow_html=True)
