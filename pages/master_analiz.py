import streamlit as st
import pandas as pd
from datetime import timedelta
import cache
from streamlit_lightweight_charts import renderLightweightCharts

GB_PERIODS = {"1A": 30, "3A": 90, "6A": 180, "1Y": 365, "TÜM": None}

CHART_BG   = "#0c0c13"
GRID_COLOR = "#0f0f18"
BORDER_COL = "#1a1a24"
TEXT_COLOR = "#3a3a55"

TIP_RENK = {
    "anomali_z60":   "#4d8ef0",
    "anomali_z120":  "#06b6d4",
    "anomali_rz60":  "#d4820a",
    "anomali_rz120": "#22c55e",
    "anomali_t":     "#a07af0",
}
TIP_KISA = {
    "anomali_z60": "Z60", "anomali_z120": "Z120",
    "anomali_rz60": "RZ60", "anomali_rz120": "RZ120",
    "anomali_t": "T",
}
RADAR_RENK = {
    "radar1": "#4d8ef0",
    "radar2": "#d4820a",
}
RADAR_RENK_DIM = {
    "radar1": "#4d8ef022",
    "radar2": "#d4820a22",
}

PILL_OPTS  = ["R1", "R2", "Z60", "Z120", "RZ60", "RZ120"]
RADAR_MAP  = {"R1": "radar1", "R2": "radar2"}
ZSCORE_MAP = {"Z60": "anomali_z60", "Z120": "anomali_z120",
              "RZ60": "anomali_rz60", "RZ120": "anomali_rz120"}

# --- Liste sabitleri ---
_LW = [1.2, 0.65, 0.55, 0.65, 0.5, 0.75, 0.75]
_HDRS = [
    ("Hisse",  None),
    ("Radar",  "radars"),
    ("Gün",    "pencere_uzunlugu"),
    ("Efor",   "efor_rasyosu"),
    ("Şok",    "sok_sayisi"),
    ("F.Lim",  "fiziki_limit"),
    ("M-Skor", "master_skor"),
]
PAGE_SIZE = 18


def _kart(label, value, renk="#e0e0f0", alt=""):
    alt_html = f'<div style="font-size:9px;color:#3a3a55;margin-top:4px">{alt}</div>' if alt else ""
    st.markdown(
        f'<div style="background:#0f0f18;border:1px solid #1a1a24;border-radius:2px;padding:10px 12px">'
        f'<div style="font-size:9px;color:#3a3a55;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:18px;color:{renk};font-weight:300">{value}</div>'
        f'{alt_html}</div>',
        unsafe_allow_html=True,
    )


def master_grafik_goster(df, kutular, anomaliler, key="master_grafik", yukseklik=400, secili_kutu_bas=None):
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values("price_date")
    df["time"] = df["price_date"].dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["acilis", "yuksek", "dusuk", "kapanis"])
    df["hacim"] = df["hacim"].fillna(0)

    anomali_set = set()
    markers = []

    if anomaliler is not None and not anomaliler.empty:
        anoms = anomaliler.copy()
        anoms["tarih"] = pd.to_datetime(anoms["baslangic_zaman"]).dt.date.astype(str)
        for _, row in anoms.iterrows():
            anomali_set.add(row["tarih"])
            tip  = row["anomali_tipi"]
            skor = row["skor"]
            markers.append({
                "time": row["tarih"], "position": "aboveBar",
                "color": TIP_RENK.get(tip, "#666680"), "shape": "arrowDown",
                "text": f"{TIP_KISA.get(tip,'A')}·{skor:.1f}",
            })

    has_selected = secili_kutu_bas is not None
    for k in kutular:
        bas  = str(k["kutu_baslangic"])
        bit  = str(k["kutu_bitis"])
        is_s = has_selected and bas == secili_kutu_bas
        renk = RADAR_RENK.get(k["radar"], "#4d8ef0") if (not has_selected or is_s) else RADAR_RENK_DIM.get(k["radar"], "#33334422")
        markers.append({"time": bas, "position": "belowBar", "color": renk, "shape": "arrowUp",  "text": k["radar"].upper()})
        markers.append({"time": bit, "position": "belowBar", "color": renk, "shape": "circle",   "text": "END"})

    candle_data = df[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(
        columns={"acilis": "open", "yuksek": "high", "dusuk": "low", "kapanis": "close"}
    ).to_dict("records")

    volume_data = [
        {"time": row["time"], "value": float(row["hacim"]),
         "color": "#d4820a66" if row["time"] in anomali_set else "#1e1e3044"}
        for _, row in df.iterrows()
    ]

    extra_series = []
    for k in kutular:
        bas_s = str(k["kutu_baslangic"])
        bit_s = str(k["kutu_bitis"])
        is_s  = has_selected and bas_s == secili_kutu_bas

        if has_selected and not is_s:
            renk       = RADAR_RENK_DIM.get(k["radar"], "#33334422")
            lw, ls     = 1, 2
        elif is_s:
            renk       = RADAR_RENK.get(k["radar"], "#4d8ef0")
            lw, ls     = 2, 0
        else:
            renk       = RADAR_RENK.get(k["radar"], "#4d8ef0")
            lw, ls     = 1, 2

        trend_m = k.get("trend_m")
        trend_c = k.get("trend_c")
        ust_off = k.get("kanal_ust_offset")
        alt_off = k.get("kanal_alt_offset")

        if all(pd.notna(v) for v in (trend_m, trend_c, ust_off, alt_off)):
            kutu_rows = [r for _, r in df.iterrows() if bas_s <= r["time"] <= bit_s]
            if kutu_rows:
                ust_data, alt_data = [], []
                for t_idx, r in enumerate(kutu_rows):
                    trend_val = float(trend_m) * t_idx + float(trend_c)
                    ust_data.append({"time": r["time"], "value": trend_val + float(ust_off)})
                    alt_data.append({"time": r["time"], "value": trend_val + float(alt_off)})
                for data in (ust_data, alt_data):
                    extra_series.append({"type": "Line", "data": data,
                        "options": {"color": renk, "lineWidth": lw, "lineStyle": ls,
                                    "priceScaleId": "right", "lastValueVisible": False, "priceLineVisible": False}})
            continue

        zirve_raw = k.get("cekirdek_zirve")
        dip_raw   = k.get("cekirdek_dip")
        zirve_val = float(zirve_raw) if pd.notna(zirve_raw) else 0.0
        dip_val   = float(dip_raw)   if pd.notna(dip_raw)   else 0.0

        if float(zirve_val) > 0:
            zd = [{"time": r["time"], "value": float(zirve_val)}
                  for _, r in df.iterrows() if bas_s <= r["time"] <= bit_s]
            if zd:
                extra_series.append({"type": "Line", "data": zd,
                    "options": {"color": renk, "lineWidth": lw, "lineStyle": ls,
                                "priceScaleId": "right", "lastValueVisible": False, "priceLineVisible": False}})

        if float(dip_val) > 0:
            dd = [{"time": r["time"], "value": float(dip_val)}
                  for _, r in df.iterrows() if bas_s <= r["time"] <= bit_s]
            if dd:
                extra_series.append({"type": "Line", "data": dd,
                    "options": {"color": renk, "lineWidth": lw, "lineStyle": ls,
                                "priceScaleId": "right", "lastValueVisible": False, "priceLineVisible": False}})

    chart_cfg = {
        "layout": {"background": {"type": "solid", "color": CHART_BG}, "textColor": TEXT_COLOR,
                   "fontSize": 10, "fontFamily": "IBM Plex Mono"},
        "grid": {"vertLines": {"color": GRID_COLOR}, "horzLines": {"color": GRID_COLOR}},
        "crosshair": {"mode": 1},
        "timeScale": {"borderColor": BORDER_COL, "barSpacing": 6},
        "rightPriceScale": {"borderColor": BORDER_COL, "scaleMargins": {"top": 0.05, "bottom": 0.22}},
        "height": yukseklik,
    }

    series_list = [
        {"type": "Candlestick", "data": candle_data, "markers": markers,
         "options": {"upColor": "#22c55e", "downColor": "#e84040",
                     "borderUpColor": "#22c55e", "borderDownColor": "#e84040",
                     "wickUpColor": "#22c55e", "wickDownColor": "#e84040"}},
        {"type": "Histogram", "data": volume_data,
         "options": {"priceFormat": {"type": "volume"}, "priceScaleId": "vol",
                     "scaleMargins": {"top": 0.82, "bottom": 0}}},
    ] + extra_series

    renderLightweightCharts([{"chart": chart_cfg, "series": series_list}], key=key)


# ─── Unified Liste ────────────────────────────────────────────────────────────

def _header_row():
    sort_col = st.session_state.get("liste_sort_col", "master_skor")
    sort_asc = st.session_state.get("liste_sort_asc", False)
    h_cols = st.columns(_LW)
    for i, (label, key) in enumerate(_HDRS):
        with h_cols[i]:
            if key is None:
                st.markdown(
                    f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
                    f'text-transform:uppercase;padding:4px 2px;border-bottom:1px solid #1a1a24">'
                    f'{label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                ind = ("▲" if sort_asc else "▼") if sort_col == key else ""
                if st.button(f"{label} {ind}".strip(), key=f"sh_{key}", use_container_width=True):
                    if sort_col == key:
                        st.session_state["liste_sort_asc"] = not sort_asc
                    else:
                        st.session_state["liste_sort_col"] = key
                        st.session_state["liste_sort_asc"] = False
                    st.session_state["liste_sayfa"] = 0
                    st.rerun()


def _satir(row):
    radars = str(row["radars"]).upper().replace("RADAR", "R")
    r_renk = "#4d8ef0" if radars == "R1" else ("#d4820a" if radars == "R2" else "#a07af0")
    skor_renk = (
        "#22c55e" if row["master_skor"] >= 10 else
        ("#d4820a" if row["master_skor"] >= 5 else "#4a4a68")
    )
    secili = st.session_state.get("gb_secilen") == row["symbol"]
    cols = st.columns(_LW)
    with cols[0]:
        if st.button(
            row["symbol"], key=f"lb_{row['symbol']}",
            use_container_width=True,
            type="primary" if secili else "secondary",
        ):
            st.session_state["gb_secilen"] = row["symbol"]
            st.rerun()
    cols[1].markdown(
        f'<div style="padding:5px 2px;font-size:10px;color:{r_renk}">{radars}</div>',
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        f'<div style="padding:5px 2px;font-size:11px;color:#e0e0f0">'
        f'{int(row["pencere_uzunlugu"])}g</div>',
        unsafe_allow_html=True,
    )
    ef = f"{row['efor_rasyosu']:.2f}x" if pd.notna(row["efor_rasyosu"]) else "—"
    cols[3].markdown(
        f'<div style="padding:5px 2px;font-size:11px;color:#8888a8">{ef}</div>',
        unsafe_allow_html=True,
    )
    sk = str(int(row["sok_sayisi"])) if pd.notna(row["sok_sayisi"]) else "0"
    cols[4].markdown(
        f'<div style="padding:5px 2px;font-size:11px;color:#d4820a">{sk}</div>',
        unsafe_allow_html=True,
    )
    fl = f"{row['fiziki_limit']:.4f}" if pd.notna(row["fiziki_limit"]) else "—"
    cols[5].markdown(
        f'<div style="padding:5px 2px;font-size:11px;color:#4d8ef0">{fl}</div>',
        unsafe_allow_html=True,
    )
    cols[6].markdown(
        f'<div style="padding:5px 2px;font-size:12px;color:{skor_renk};font-weight:600">'
        f'{row["master_skor"]:.2f}</div>',
        unsafe_allow_html=True,
    )


def _liste_paneli(df: pd.DataFrame):
    sort_col = st.session_state.get("liste_sort_col", "master_skor")
    sort_asc = st.session_state.get("liste_sort_asc", False)

    df_s = df.copy()
    if sort_col in df_s.columns:
        df_s = df_s.sort_values(sort_col, ascending=sort_asc).reset_index(drop=True)

    total       = len(df_s)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = int(st.session_state.get("liste_sayfa", 0))
    page        = max(0, min(page, total_pages - 1))

    st.markdown(
        f'<div style="font-size:9px;color:#2e2e48;margin:2px 0 6px">'
        f'{total} hisse &nbsp;·&nbsp; sayfa {page + 1} / {total_pages}</div>',
        unsafe_allow_html=True,
    )

    _header_row()

    with st.container(height=750, border=False):
        page_rows = df_s.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
        for _, row in page_rows.iterrows():
            _satir(row)

    # Sayfa butonları
    p1, pmid, p3 = st.columns([1, 4, 1])
    with p1:
        if st.button("◀", key="pg_prev", disabled=(page == 0), use_container_width=True):
            st.session_state["liste_sayfa"] = page - 1
            st.rerun()
    with pmid:
        visible = list(range(max(0, page - 2), min(total_pages, page + 3)))
        if visible:
            btn_cols = st.columns(len(visible))
            for i, pg in enumerate(visible):
                with btn_cols[i]:
                    if st.button(
                        str(pg + 1), key=f"pg_{pg}",
                        type="primary" if pg == page else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["liste_sayfa"] = pg
                        st.rerun()
    with p3:
        if st.button("▶", key="pg_next", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state["liste_sayfa"] = page + 1
            st.rerun()


# ─── Detay Paneli ─────────────────────────────────────────────────────────────

def _detay_paneli(symbol: str):
    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:0 0 10px 0">'
        f'<span style="color:#2e2e48;margin-right:8px">§ 1</span>'
        f'DETAY · <span style="color:#4d8ef0">{symbol}</span></div>',
        unsafe_allow_html=True,
    )

    stock_id = cache.stock_id_lookup(symbol)
    if stock_id is None:
        st.error(f"{symbol} bulunamadı.")
        return

    df_fiyat   = cache.fiyat_verisi(stock_id, gun=500)
    df_sikisma = cache.sikisma_kayitlari(symbol)
    df_anomali = cache.anomali_kayitlari(symbol)
    son_s = df_sikisma.iloc[0] if not df_sikisma.empty else None

    # Metrik kartlar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        val = f"{son_s['fiziki_limit']:.4f}" if son_s is not None and pd.notna(son_s['fiziki_limit']) else "—"
        _kart("Fiziki Limit", val, "#4d8ef0", "Hacim / Dolaşım Lot")
    with c2:
        val = f"{son_s['efor_rasyosu']:.2f}x" if son_s is not None and pd.notna(son_s['efor_rasyosu']) else "—"
        renk = "#22c55e" if son_s is not None and (son_s['efor_rasyosu'] or 0) >= 1.5 else "#e0e0f0"
        _kart("Efor Rasyosu", val, renk, "Kutu / Normal ADV")
    with c3:
        val = str(int(son_s['sok_sayisi'])) if son_s is not None and pd.notna(son_s['sok_sayisi']) else "0"
        _kart("Şok Sayacı", val, "#d4820a", "Anomali Gün Sayısı")
    with c4:
        val = f"%{son_s['sok_hacim_yuzdesi']:.1f}" if son_s is not None and pd.notna(son_s['sok_hacim_yuzdesi']) else "%0.0"
        _kart("Şok Oranı", val, "#d4820a", "Şok Hacim / Toplam")

    st.markdown('<div style="margin-top:10px"></div>', unsafe_allow_html=True)

    r1_kayit = df_sikisma[df_sikisma["radar"] == "radar1"]

    if not df_fiyat.empty:
        df_fiyat["price_date"] = pd.to_datetime(df_fiyat["price_date"])
        max_date = df_fiyat["price_date"].max().date()
        min_date = df_fiyat["price_date"].min().date()

        # Period seçici — kendi satırında
        period_sec = st.radio(
            "gb_period", list(GB_PERIODS.keys()),
            horizontal=True, index=3,
            label_visibility="collapsed", key="gb_period",
        )

        gun = GB_PERIODS[period_sec]
        raw_bas     = (max_date - timedelta(days=gun)) if gun else min_date
        default_bas = max(raw_bas, min_date)

        prev_key = f"gb_prev_period_{symbol}"
        if st.session_state.get(prev_key) != period_sec:
            st.session_state[f"gb_tarih_bas_{symbol}"] = default_bas
            st.session_state[f"gb_tarih_bit_{symbol}"] = max_date
            st.session_state[prev_key] = period_sec

        bas_key = f"gb_tarih_bas_{symbol}"
        bit_key = f"gb_tarih_bit_{symbol}"
        if bas_key in st.session_state:
            st.session_state[bas_key] = max(min_date, min(max_date, st.session_state[bas_key]))
        if bit_key in st.session_state:
            st.session_state[bit_key] = max(min_date, min(max_date, st.session_state[bit_key]))

        # Tarih seçiciler — kendi satırında
        col_bas, col_ok, col_bit = st.columns([5, 0.4, 5])
        with col_bas:
            tarih_bas = st.date_input(
                "gb_bas", key=f"gb_tarih_bas_{symbol}",
                min_value=min_date, max_value=max_date,
                label_visibility="collapsed",
            )
        col_ok.markdown(
            '<div style="color:#2e2e48;padding-top:8px;text-align:center">→</div>',
            unsafe_allow_html=True,
        )
        with col_bit:
            tarih_bit = st.date_input(
                "gb_bit", key=f"gb_tarih_bit_{symbol}",
                min_value=min_date, max_value=max_date,
                label_visibility="collapsed",
            )

        cutoff   = pd.Timestamp(tarih_bas)
        bitis_ts = pd.Timestamp(tarih_bit)

        df_fiyat_f = df_fiyat[
            (df_fiyat["price_date"] >= cutoff) &
            (df_fiyat["price_date"] <= bitis_ts)
        ].copy()

        kutular_ham = [
            row.to_dict() for _, row in df_sikisma.iterrows()
            if not (pd.to_datetime(row["kutu_bitis"]) < cutoff or
                    pd.to_datetime(row["kutu_baslangic"]) > bitis_ts)
        ]

        df_anomali_f = df_anomali
        if not df_anomali.empty:
            df_anomali_f = df_anomali.copy()
            df_anomali_f["baslangic_zaman"] = pd.to_datetime(df_anomali_f["baslangic_zaman"])
            df_anomali_f = df_anomali_f[
                (df_anomali_f["baslangic_zaman"] >= cutoff) &
                (df_anomali_f["baslangic_zaman"] <= bitis_ts)
            ]

        sinyal_sec = st.pills(
            "Sinyal", PILL_OPTS, selection_mode="multi",
            default=PILL_OPTS, key=f"gb_sinyal_{symbol}",
            label_visibility="collapsed",
        )
        aktif_radarlar = {RADAR_MAP[r] for r in (sinyal_sec or []) if r in RADAR_MAP}
        aktif_zscore   = {ZSCORE_MAP[z] for z in (sinyal_sec or []) if z in ZSCORE_MAP}

        kutular_f = [k for k in kutular_ham if k.get("radar") in aktif_radarlar]

        if not df_anomali_f.empty:
            if aktif_zscore:
                df_anomali_f = df_anomali_f[df_anomali_f["anomali_tipi"].isin(aktif_zscore)]
            else:
                df_anomali_f = df_anomali_f.iloc[0:0]

        secili_kutu_bas = st.session_state.get(f"gb_kutu_bas_{symbol}")
        gecerli_baslar  = {str(k["kutu_baslangic"]) for k in kutular_f}
        if secili_kutu_bas not in gecerli_baslar:
            secili_kutu_bas = None
            st.session_state[f"gb_kutu_bas_{symbol}"] = None

        # Grafik — sabit
        master_grafik_goster(
            df_fiyat_f, kutular_f, df_anomali_f,
            key=f"master_{symbol}_{tarih_bas}_{tarih_bit}_{'_'.join(sorted(sinyal_sec or []))}_{secili_kutu_bas}",
            yukseklik=340,
            secili_kutu_bas=secili_kutu_bas,
        )

        # Kanal listesi — yalnızca bu kısım scrollable
        if kutular_f:
            st.markdown(
                '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
                'text-transform:uppercase;margin:8px 0 4px 0">Kanal Odak</div>',
                unsafe_allow_html=True,
            )
            with st.container(height=85, border=False):
                MAX_ROW = 6
                for row_start in range(0, len(kutular_f), MAX_ROW):
                    chunk = kutular_f[row_start:row_start + MAX_ROW]
                    cols  = st.columns(len(chunk))
                    for col, k in zip(cols, chunk):
                        bas_s   = str(k["kutu_baslangic"])
                        bit_s   = str(k["kutu_bitis"])
                        radar_s = k["radar"].upper()
                        is_sec  = secili_kutu_bas == bas_s
                        label   = f"{radar_s} · {bas_s[5:]} → {bit_s[5:]}"
                        with col:
                            if st.button(
                                label,
                                key=f"gb_kbtn_{symbol}_{bas_s}_{bit_s}_{k['radar']}",
                                type="primary" if is_sec else "secondary",
                                use_container_width=True,
                            ):
                                st.session_state[f"gb_kutu_bas_{symbol}"] = None if is_sec else bas_s
                                st.rerun()

        # Z-Score
        st.markdown(
            '<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;'
            'text-transform:uppercase;margin:10px 0">§ Z-Score & Anomaliler</div>',
            unsafe_allow_html=True,
        )
        df_z = cache.zscore_son(stock_id, n=10)
        if not df_z.empty:
            st.markdown(
                '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;padding:6px 10px;'
                'border-bottom:1px solid #1a1a24;font-size:9px;color:#2e2e48;text-transform:uppercase">'
                '<span>Tarih</span><span>RZ 60</span><span>RZ 120</span></div>',
                unsafe_allow_html=True,
            )
            with st.container(height=90, border=False):
                for _, zr in df_z.iterrows():
                    z60  = float(zr["z_score_robust_60"])  if pd.notna(zr["z_score_robust_60"])  else 0
                    z120 = float(zr["z_score_robust_120"]) if pd.notna(zr["z_score_robust_120"]) else 0
                    c60  = "#e84040" if abs(z60)  >= 4 else ("#d4820a" if abs(z60)  >= 2.5 else "#4a4a68")
                    c120 = "#e84040" if abs(z120) >= 4 else ("#d4820a" if abs(z120) >= 2.5 else "#4a4a68")
                    st.markdown(
                        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;padding:6px 10px;'
                        f'border-bottom:1px solid #0f0f18;font-size:11px">'
                        f'<span style="color:#8888a8">{zr["price_date"]}</span>'
                        f'<span style="color:{c60}">{z60:.3f}</span>'
                        f'<span style="color:{c120}">{z120:.3f}</span></div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Fiyat verisi bulunamadı.")

    # R1 notu — her zaman en altta
    if not r1_kayit.empty:
        st.markdown(
            '<div style="margin-top:55px;padding:10px;background:#0d1a2e33;border-left:2px solid #4d8ef0;'
            'font-size:11px;color:#8888a8"><b>Radar 1 Notu:</b> %10 köpük toleransı ile hesaplanmıştır. '
            'Kutu dışına taşan volatilite emilmiştir.</div>',
            unsafe_allow_html=True,
        )


# ─── Ana Sayfa ────────────────────────────────────────────────────────────────

def goster():
    # Filtreler — kolon ayrımından önce (SQL cache key'i belirler)
    gun_opts = {"14g": 14, "30g": 30, "90g": 90, "180g": 180, "Tümü": 0}
    fc1, fc2, _fc3 = st.columns([2, 2, 8])
    with fc1:
        gun_sec = st.selectbox(
            "gun_filtre", list(gun_opts.keys()), index=1,
            label_visibility="collapsed", key="liste_gun_filtre",
        )
        gun_siniri = gun_opts[gun_sec]
    with fc2:
        radar_sec = st.multiselect(
            "radar_filtre", ["R1", "R2"], default=[],
            label_visibility="collapsed",
            placeholder="Radar filtrele",
            key="liste_radar_filtre",
        )

    df_liste = cache.liderlik_liste(gun_siniri)

    # Radar filtresi Python tarafında
    df_f = df_liste.copy()
    if radar_sec:
        def _match(r):
            n = str(r).upper().replace("RADAR", "R")
            return any(x in n for x in radar_sec)
        df_f = df_f[df_f["radars"].apply(_match)].reset_index(drop=True)

    # Sol: liste  |  Sağ: grafik
    col_liste, col_detay = st.columns([1, 1])

    with col_liste:
        st.markdown(
            '<div style="font-size:10px;color:#e0e0f0;letter-spacing:0.06em;margin:0 0 8px 0">'
            '<span style="color:#2e2e48;margin-right:8px">§ 0</span>STRATEJİK SIRALAMA'
            '<span style="color:#2e2e48;font-size:9px;margin-left:10px">· hisseye tıkla</span></div>',
            unsafe_allow_html=True,
        )
        _liste_paneli(df_f)

    symbol = st.session_state.get("gb_secilen")
    if not symbol and not df_f.empty:
        symbol = df_f.iloc[0]["symbol"]

    with col_detay:
        if symbol:
            _detay_paneli(symbol)
        else:
            st.info("Bir hisse seçin.")
