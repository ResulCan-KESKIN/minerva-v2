import streamlit as st
import pandas as pd
from db import get_conn
from pages import hisse_detay, anomali_backtest, master_analiz

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
.block-container {
    padding: 12px 20px 24px 20px !important;
    max-width: 100% !important;
}
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stToolbar"]     { display: none !important; }
header[data-testid="stHeader"]   { display: none !important; }
footer { display: none !important; }

div[data-testid="stRadio"] > label,
div[data-testid="stRadio"] [data-testid="stWidgetLabel"],
div[data-testid="stRadio"] > div:first-child > p { display: none !important; }
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

div[data-testid="stVerticalBlock"] > div { padding-top: 0 !important; padding-bottom: 0 !important; }
div[data-testid="stVerticalBlock"] { gap: 0 !important; }
div[data-testid="stHorizontalBlock"] { gap: 12px !important; flex-wrap: nowrap !important; }
div[data-testid="column"] { padding: 0 !important; min-width: 0 !important; overflow: visible !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { padding: 0 !important; }

/* Scroll container'ın kendi border'ını gizle */
div[data-testid="stVerticalBlockBorderWrapper"][style*="overflow"] {
    border: none !important;
    background: transparent !important;
}

/* ── Mobile ──────────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .block-container { padding: 6px 8px 16px 8px !important; }

  /* Tüm kolon grupları dikey yığılsın */
  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 4px !important;
  }
  div[data-testid="column"] {
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }

  /* Ok/boşluk ayırıcıları gizle */
  .mv-arrow { display: none !important; }
  /* Tarih etiketi gizle (tarih inputları kalır) */
  .mv-label { display: none !important; }

  /* Header: sağ taraftaki istatistikleri gizle, sol yeterli */
  .mv-header { flex-wrap: wrap !important; gap: 6px !important; }
  .mv-header-right { display: none !important; }

  /* Status bar: iki taraf üst üste */
  .mv-statusbar { flex-direction: column !important; gap: 3px !important; }

  /* Radio sekmeler daha dar */
  div[data-testid="stRadio"] label { padding: 8px 10px 9px !important; }

  /* Butonların font biraz daha büyük */
  .stButton > button { font-size: 11px !important; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def _anomali_stats():
    conn = get_conn()
    return pd.read_sql("""
        SELECT
            (SELECT COUNT(*) FROM stocks WHERE is_active = true) AS hisse_sayisi,
            COUNT(*)                                              AS toplam,
            MAX(baslangic_zaman)                                  AS son_guncelleme
        FROM anomali_kayitlari
    """, conn).iloc[0]


@st.cache_data(ttl=300)
def _hisse_listesi():
    conn = get_conn()
    return pd.read_sql(
        "SELECT symbol FROM stocks WHERE is_active = true ORDER BY symbol", conn
    )["symbol"].tolist()


try:
    hisseler = _hisse_listesi()
except Exception:
    hisseler = []

try:
    sa = _anomali_stats()
    a_hisse   = int(sa["hisse_sayisi"])
    a_toplam  = int(sa["toplam"])
    a_son     = sa["son_guncelleme"]
    a_son_str = a_son.strftime("%Y-%m-%d %H:%M") if a_son is not None else "—"
except Exception:
    a_hisse = a_toplam = 0
    a_son_str = "—"

# ── Header ──
st.markdown(f"""
<div class="mv-header" style="display:flex;align-items:center;justify-content:space-between;padding:10px 0 0 0">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:22px;height:22px;border-radius:50%;background:#4d8ef0;
                display:flex;align-items:center;justify-content:center;
                font-size:11px;font-weight:500;color:#fff;flex-shrink:0">M</div>
    <span style="font-size:13px;font-weight:500;color:#e0e0f0;letter-spacing:0.04em">Minerva</span>
    <span style="color:#1e1e30;font-size:13px">·</span>
    <span style="font-size:11px;color:#3a3a55;letter-spacing:0.06em">ANOMALİ + SIKIŞMA</span>
  </div>
  <div class="mv-header-right" style="display:flex;align-items:center;gap:16px">
    <span style="font-size:10px;color:#3a3a55;letter-spacing:0.06em">
      piyasa <span style="color:#6a6a88">BIST</span>
    </span>
    <span style="font-size:10px;color:#3a3a55">·</span>
    <span style="font-size:10px;color:#3a3a55;letter-spacing:0.06em">
      son güncelleme <span style="color:#6a6a88">{a_son_str}</span>
    </span>
    <span style="font-size:10px;color:#3a3a55">·</span>
    <span style="font-size:10px;color:#22c55e;letter-spacing:0.06em">● ready</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Nav + Hisse seçici ──
col_nav, col_hisse = st.columns([9, 2])

with col_nav:
    sayfa = st.radio(
        "nav",
        ["Genel Bakis", "Hisse Detay", "Backtest"],
        horizontal=True,
        label_visibility="collapsed",
        key="nav",
    )

with col_hisse:
    if sayfa in ("Genel Bakis", "Hisse Detay"):
        # Hisse Detay manages its own selector inside the page
        secilen = st.session_state.get("hd_hisse", "")
    else:
        secilen = st.selectbox(
            "hisse", hisseler,
            label_visibility="collapsed",
            key="nav_hisse",
        )

# ── Status bar ──
ticker_html = f'ticker — {secilen}' if secilen else 'tıkla → aç'
st.markdown(f"""
<div class="mv-statusbar" style="font-size:10px;color:#2e2e48;letter-spacing:0.06em;
            padding:5px 0 12px 0;border-bottom:1px solid #12121e;
            display:flex;justify-content:space-between">
  <span>
    takip <span style="color:#4a4a68">{a_hisse}</span> hisse
    &nbsp;·&nbsp; toplam <span style="color:#4a4a68">{a_toplam:,}</span> anomali
  </span>
  <span style="color:#2e2e48">{ticker_html}</span>
</div>
""", unsafe_allow_html=True)

# ── Page routing ──
if sayfa == "Genel Bakis":
    master_analiz.goster()
elif sayfa == "Hisse Detay":
    hisse_detay.goster(hisseler)
elif sayfa == "Backtest":
    anomali_backtest.goster()

# ── Footer ──
st.markdown(f"""
<div style="margin-top:40px;padding:8px 0;border-top:1px solid #12121e;
            display:flex;justify-content:space-between;align-items:center">
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">
    <span style="color:#22c55e">●</span>
    &nbsp;db · synced
  </span>
  <span style="font-size:10px;color:#2a2a40;letter-spacing:0.06em">Minerva</span>
</div>
""", unsafe_allow_html=True)
