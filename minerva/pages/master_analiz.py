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

def _kart(label, value, renk="#e0e0f0", alt=""):
    alt_html = f'<div style="font-size:9px;color:#3a3a55;margin-top:4px">{alt}</div>' if alt else ""
    st.markdown(
        f'<div style="background:#0f0f18;border:1px solid #1a1a24;border-radius:2px;padding:12px 16px">'
        f'<div style="font-size:9px;color:#3a3a55;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:22px;color:{renk};font-weight:300">{value}</div>'
        f'{alt_html}</div>',
        unsafe_allow_html=True
    )

def master_grafik_goster(df, kutular, anomaliler, key="master_grafik", yukseklik=450, secili_kutu_bas=None):
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values("price_date")
    df["time"] = df["price_date"].dt.strftime("%Y-%m-%d")

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

        zirve_val = k.get("cekirdek_zirve") or 0
        dip_val   = k.get("cekirdek_dip")   or 0

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

def _liderlik_tablosu() -> pd.DataFrame:
    st.markdown('<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:10px 0 14px 0">'
                '<span style="color:#2e2e48;margin-right:8px">§ 0</span>STRATEJİK SIRALAMA (TOP 15)'
                '<span style="color:#2e2e48;font-size:10px;margin-left:10px">· hisseye tıklayarak aç</span></div>',
                unsafe_allow_html=True)

    df_lider = cache.liderlik_top15()

    if df_lider.empty:
        st.info("Son 14 güne ait stratejik sinyal bulunamadı.")
        st.markdown('<div style="margin-bottom:30px; border-bottom:1px solid #1a1a24"></div>', unsafe_allow_html=True)
        return df_lider

    col_weights = [1, 1, 0.8, 0.6, 0.8, 1.8, 0.8]
    h_cols = st.columns(col_weights)
    for c, txt in zip(h_cols, ["Hisse", "Radar", "Efor", "Şok", "% Şok", "Gün / Aralık", "M-Skor"]):
        c.markdown(
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase;'
            f'padding:6px 4px;border-bottom:1px solid #1a1a24">{txt}</div>',
            unsafe_allow_html=True,
        )

    for _, row in df_lider.iterrows():
        radars = row['radars'].upper().replace('RADAR', 'R')
        r_renk = "#4d8ef0" if "R1" in radars and "R2" not in radars else ("#d4820a" if "R2" in radars and "R1" not in radars else "#a07af0")
        skor_renk = "#22c55e" if row['master_skor'] >= 10 else ("#d4820a" if row['master_skor'] >= 5 else "#4a4a68")

        efor_val = f"{row['efor_rasyosu']:.2f}x" if pd.notna(row['efor_rasyosu']) else "—"
        sok_val  = str(int(row['sok_sayisi'])) if pd.notna(row['sok_sayisi']) else "0"
        yuzde_val = f"%{row['sok_hacim_yuzdesi']:.1f}" if pd.notna(row['sok_hacim_yuzdesi']) else "%0.0"

        gun_n = int(row['pencere_uzunlugu']) if pd.notna(row['pencere_uzunlugu']) else 0
        bas = str(row['kutu_baslangic'])[5:] if pd.notna(row['kutu_baslangic']) else "—"
        bit = str(row['kutu_bitis'])[5:] if pd.notna(row['kutu_bitis']) else "—"

        secili = st.session_state.get("gb_secilen") == row["symbol"]
        cols = st.columns(col_weights)

        with cols[0]:
            if st.button(
                row["symbol"],
                key=f"lider_btn_{row['symbol']}",
                use_container_width=True,
                type="primary" if secili else "secondary",
            ):
                st.session_state["gb_secilen"] = row["symbol"]
                st.rerun()

        cols[1].markdown(f'<div style="padding:8px 4px;font-size:10px;color:{r_renk}">{radars}</div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div style="padding:8px 4px;font-size:11px;color:#8888a8">{efor_val}</div>', unsafe_allow_html=True)
        cols[3].markdown(f'<div style="padding:8px 4px;font-size:11px;color:#d4820a">{sok_val}</div>', unsafe_allow_html=True)
        cols[4].markdown(f'<div style="padding:8px 4px;font-size:11px;color:#4a4a68">{yuzde_val}</div>', unsafe_allow_html=True)
        cols[5].markdown(
            f'<div style="padding:8px 4px;font-size:11px"><span style="color:#e0e0f0">{gun_n}g</span> '
            f'<span style="color:#3a3a55;font-size:10px">({bas} / {bit})</span></div>',
            unsafe_allow_html=True,
        )
        cols[6].markdown(
            f'<div style="padding:8px 4px;font-size:12px;color:{skor_renk};font-weight:600">{row["master_skor"]:.2f}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="margin:20px 0 30px; border-bottom:1px solid #1a1a24"></div>', unsafe_allow_html=True)
    return df_lider

def goster():
    # 0. Liderlik Tablosu (tıklanabilir)
    df_lider = _liderlik_tablosu()

    # Seçili hisse: kullanıcı tıklamadıysa liderlik tablosunun ilk satırı
    symbol = st.session_state.get("gb_secilen")
    if not symbol:
        if df_lider.empty:
            st.info("Detay görmek için bir hisse seçimi yapılmadı.")
            return
        symbol = df_lider.iloc[0]["symbol"]

    st.markdown(
        f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:0 0 14px 0">'
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

    # Son Sıkışma Kaydı
    son_s = df_sikisma.iloc[0] if not df_sikisma.empty else None

    # 1. Üst Metrik Paneli
    st.markdown('<div style="margin-top:10px"></div>', unsafe_allow_html=True)
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

    # 2. Merkez Grafik + Tarih Seçici
    st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)

    if not df_fiyat.empty:
        df_fiyat["price_date"] = pd.to_datetime(df_fiyat["price_date"])
        max_date = df_fiyat["price_date"].max().date()
        min_date = df_fiyat["price_date"].min().date()

        row_period, row_dates = st.columns([4, 6])
        with row_period:
            period_sec = st.radio(
                "gb_period",
                list(GB_PERIODS.keys()),
                horizontal=True,
                index=3,
                label_visibility="collapsed",
                key="gb_period",
            )

        gun = GB_PERIODS[period_sec]
        raw_bas = (max_date - timedelta(days=gun)) if gun else min_date
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

        with row_dates:
            col_lbl, col_bas, col_ok, col_bit = st.columns([0.8, 3, 0.3, 3])
            col_lbl.markdown(
                '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
                'text-transform:uppercase;padding-top:10px">Tarih</div>',
                unsafe_allow_html=True,
            )
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

        kutular_ham = []
        for _, row in df_sikisma.iterrows():
            bitis_k = pd.to_datetime(row["kutu_bitis"])
            bas_k   = pd.to_datetime(row["kutu_baslangic"])
            if bitis_k < cutoff or bas_k > bitis_ts:
                continue
            kutular_ham.append(row.to_dict())

        df_anomali_f = df_anomali
        if not df_anomali.empty:
            df_anomali_f = df_anomali.copy()
            df_anomali_f["baslangic_zaman"] = pd.to_datetime(df_anomali_f["baslangic_zaman"])
            df_anomali_f = df_anomali_f[
                (df_anomali_f["baslangic_zaman"] >= cutoff) &
                (df_anomali_f["baslangic_zaman"] <= bitis_ts)
            ]

        # ── Sinyal filtresi (pills) ──
        sinyal_sec = st.pills(
            "Sinyal",
            PILL_OPTS,
            selection_mode="multi",
            default=PILL_OPTS,
            key=f"gb_sinyal_{symbol}",
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

        # ── Seçili kutu (kanal highlight) ──
        secili_kutu_bas = st.session_state.get(f"gb_kutu_bas_{symbol}")
        # Seçili kutu artık filtrede yoksa sıfırla
        gecerli_baslar = {str(k["kutu_baslangic"]) for k in kutular_f}
        if secili_kutu_bas not in gecerli_baslar:
            secili_kutu_bas = None
            st.session_state[f"gb_kutu_bas_{symbol}"] = None

        master_grafik_goster(
            df_fiyat_f, kutular_f, df_anomali_f,
            key=f"master_{symbol}_{tarih_bas}_{tarih_bit}_{'_'.join(sorted(sinyal_sec or []))}_{secili_kutu_bas}",
            secili_kutu_bas=secili_kutu_bas,
        )

        # ── Kanal seçici (grafik altı butonlar) ──
        if kutular_f:
            st.markdown(
                '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
                'text-transform:uppercase;margin:8px 0 6px 0">Kanal Odak</div>',
                unsafe_allow_html=True,
            )
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
                        if st.button(label, key=f"gb_kbtn_{symbol}_{bas_s}_{bit_s}_{k['radar']}",
                                     type="primary" if is_sec else "secondary",
                                     use_container_width=True):
                            st.session_state[f"gb_kutu_bas_{symbol}"] = None if is_sec else bas_s
                            st.rerun()
    else:
        st.info("Fiyat verisi bulunamadı.")

    # 3. Alt Panel — Z-Score
    st.markdown('<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;text-transform:uppercase;margin:10px 0">§ Z-Score & Anomaliler</div>', unsafe_allow_html=True)
    df_z = cache.zscore_son(stock_id, n=10)

    if not df_z.empty:
        st.markdown('<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;padding:6px 10px;border-bottom:1px solid #1a1a24;font-size:9px;color:#2e2e48;text-transform:uppercase"><span>Tarih</span><span>RZ 60</span><span>RZ 120</span></div>', unsafe_allow_html=True)
        for _, zr in df_z.iterrows():
            z60 = float(zr['z_score_robust_60']) if pd.notna(zr['z_score_robust_60']) else 0
            z120 = float(zr['z_score_robust_120']) if pd.notna(zr['z_score_robust_120']) else 0
            c60 = "#e84040" if abs(z60) >= 4 else ("#d4820a" if abs(z60) >= 2.5 else "#4a4a68")
            c120 = "#e84040" if abs(z120) >= 4 else ("#d4820a" if abs(z120) >= 2.5 else "#4a4a68")
            st.markdown(f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;padding:6px 10px;border-bottom:1px solid #0f0f18;font-size:11px"><span style="color:#8888a8">{zr["price_date"]}</span><span style="color:{c60}">{z60:.3f}</span><span style="color:{c120}">{z120:.3f}</span></div>', unsafe_allow_html=True)

    r1_kayit = df_sikisma[df_sikisma["radar"] == "radar1"]
    if not r1_kayit.empty:
        st.markdown('<div style="margin-top:15px;padding:10px;background:#0d1a2e33;border-left:2px solid #4d8ef0;font-size:11px;color:#8888a8"><b>Radar 1 Notu:</b> %10 köpük toleransı ile hesaplanmıştır. Kutu dışına taşan volatilite emilmiştir.</div>', unsafe_allow_html=True)
