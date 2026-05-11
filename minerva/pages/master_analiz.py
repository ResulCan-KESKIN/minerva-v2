import streamlit as st
import pandas as pd
from db import get_conn
import cache
from components.anomali_tablo import tip_badge
from streamlit_lightweight_charts import renderLightweightCharts

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

def _kart(label, value, renk="#e0e0f0", alt=""):
    alt_html = f'<div style="font-size:9px;color:#3a3a55;margin-top:4px">{alt}</div>' if alt else ""
    st.markdown(
        f'<div style="background:#0f0f18;border:1px solid #1a1a24;border-radius:2px;padding:12px 16px">'
        f'<div style="font-size:9px;color:#3a3a55;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:22px;color:{renk};font-weight:300">{value}</div>'
        f'{alt_html}</div>',
        unsafe_allow_html=True
    )

def master_grafik_goster(df, kutular, anomaliler, key="master_grafik", yukseklik=450):
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values("price_date")
    df["time"] = df["price_date"].dt.strftime("%Y-%m-%d")
    
    anomali_set = set()
    markers = []
    
    # Anomali Markers
    if anomaliler is not None and not anomaliler.empty:
        anoms = anomaliler.copy()
        anoms["tarih"] = pd.to_datetime(anoms["baslangic_zaman"]).dt.date.astype(str)
        for _, row in anoms.iterrows():
            anomali_set.add(row["tarih"])
            tip = row["anomali_tipi"]
            skor = row["skor"]
            renk = TIP_RENK.get(tip, "#666680")
            kisa = TIP_KISA.get(tip, "A")
            markers.append({
                "time": row["tarih"],
                "position": "aboveBar",
                "color": renk,
                "shape": "arrowDown",
                "text": f"{kisa}·{skor:.1f}",
            })

    # Kutu Markers (Radar sınırı)
    for k in kutular:
        bas = str(k["kutu_baslangic"])
        bit = str(k["kutu_bitis"])
        renk = RADAR_RENK.get(k["radar"], "#4d8ef0")
        markers.append({
            "time": bas, "position": "belowBar", "color": renk,
            "shape": "arrowUp", "text": k["radar"].upper()
        })
        markers.append({
            "time": bit, "position": "aboveBar", "color": renk,
            "shape": "circle", "text": f'BOX END'
        })

    candle_data = df[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(
        columns={"acilis": "open", "yuksek": "high", "dusuk": "low", "kapanis": "close"}
    ).to_dict("records")

    volume_data = [
        {
            "time": row["time"],
            "value": float(row["hacim"]),
            "color": "#d4820a66" if row["time"] in anomali_set else "#1e1e3044",
        }
        for _, row in df.iterrows()
    ]

    # Kutu Sınırları (Line series ile)
    extra_series = []
    for i, k in enumerate(kutular):
        renk = RADAR_RENK.get(k["radar"], "#4d8ef0")
        # Zirve Çizgisi
        zirve_data = [
            {"time": row["time"], "value": float(k["cekirdek_zirve"])}
            for _, row in df.iterrows() 
            if str(k["kutu_baslangic"]) <= row["time"] <= str(k["kutu_bitis"])
        ]
        if zirve_data:
            extra_series.append({
                "type": "Line",
                "data": zirve_data,
                "options": {
                    "color": renk, "lineWidth": 1, "lineStyle": 2, 
                    "priceScaleId": "right", "lastValueVisible": False, "priceLineVisible": False
                }
            })
        # Dip Çizgisi
        dip_data = [
            {"time": row["time"], "value": float(k["cekirdek_dip"])}
            for _, row in df.iterrows() 
            if str(k["kutu_baslangic"]) <= row["time"] <= str(k["kutu_bitis"])
        ]
        if dip_data:
            extra_series.append({
                "type": "Line",
                "data": dip_data,
                "options": {
                    "color": renk, "lineWidth": 1, "lineStyle": 2, 
                    "priceScaleId": "right", "lastValueVisible": False, "priceLineVisible": False
                }
            })

    chart_cfg = {
        "layout": {"background": {"type": "solid", "color": CHART_BG}, "textColor": TEXT_COLOR, "fontSize": 10, "fontFamily": "IBM Plex Mono"},
        "grid": {"vertLines": {"color": GRID_COLOR}, "horzLines": {"color": GRID_COLOR}},
        "crosshair": {"mode": 1},
        "timeScale": {"borderColor": BORDER_COL, "barSpacing": 6},
        "rightPriceScale": {"borderColor": BORDER_COL, "scaleMargins": {"top": 0.05, "bottom": 0.22}},
        "height": yukseklik,
    }

    series_list = [
        {
            "type": "Candlestick",
            "data": candle_data,
            "markers": markers,
            "options": {"upColor": "#22c55e", "downColor": "#e84040", "borderUpColor": "#22c55e", "borderDownColor": "#e84040", "wickUpColor": "#22c55e", "wickDownColor": "#e84040"}
        },
        {
            "type": "Histogram",
            "data": volume_data,
            "options": {"priceFormat": {"type": "volume"}, "priceScaleId": "vol", "scaleMargins": {"top": 0.82, "bottom": 0}}
        }
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

    df_fiyat   = cache.fiyat_verisi(stock_id, gun=300)
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

    # 2. Merkez Grafik
    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
    kutular = df_sikisma.to_dict("records") if not df_sikisma.empty else []
    master_grafik_goster(df_fiyat, kutular, df_anomali, key=f"master_{symbol}")

    # 3. Alt Paneller
    col_l, col_r = st.columns([6, 4], gap="medium")
    
    with col_l:
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
        
        # Köpük Detayı (Radar 1 için)
        r1_kayit = df_sikisma[df_sikisma["radar"] == "radar1"]
        if not r1_kayit.empty:
            st.markdown('<div style="margin-top:15px;padding:10px;background:#0d1a2e33;border-left:2px solid #4d8ef0;font-size:11px;color:#8888a8"><b>Radar 1 Notu:</b> %10 köpük toleransı ile hesaplanmıştır. Kutu dışına taşan volatilite emilmiştir.</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;text-transform:uppercase;margin:10px 0">§ Aksiyon & Karar</div>', unsafe_allow_html=True)
        bekleyen = df_anomali[df_anomali["durum"] == "beklemede"]
        if bekleyen.empty:
            st.markdown('<div style="font-size:11px;color:#2e2e48;padding:20px;border:1px solid #1a1a24;text-align:center">Bekleyen anomali yok.</div>', unsafe_allow_html=True)
        else:
            for _, anom in bekleyen.iterrows():
                with st.container():
                    st.markdown(f'<div style="background:#0d0d1a;padding:10px;border:1px solid #1a1a24;margin-bottom:10px">'
                                f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
                                f'<span>{tip_badge(anom["anomali_tipi"])}</span>'
                                f'<span style="color:#e0e0f0;font-size:11px">{str(anom["baslangic_zaman"])[:10]}</span></div>'
                                f'<div style="font-size:14px;color:#4d8ef0;margin-bottom:8px">Skor: {anom["skor"]:.4f}</div>'
                                f'</div>', unsafe_allow_html=True)
                    notlar = st.text_area("İnceleme Notu", key=f"note_{anom['id']}", height=60, label_visibility="collapsed", placeholder="Karar notu...")
                    bc1, bc2 = st.columns(2)
                    if bc1.button("ONAYLA", key=f"app_{anom['id']}", type="primary", use_container_width=True):
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute("UPDATE anomali_kayitlari SET durum='onaylandi', notlar=%s WHERE id=%s", (notlar, anom['id']))
                        conn.commit()
                        cache.anomali_mutasyon_sonrasi(symbol)
                        st.rerun()
                    if bc2.button("REDDET", key=f"rej_{anom['id']}", use_container_width=True):
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute("UPDATE anomali_kayitlari SET durum='ret', notlar=%s WHERE id=%s", (notlar, anom['id']))
                        conn.commit()
                        cache.anomali_mutasyon_sonrasi(symbol)
                        st.rerun()
