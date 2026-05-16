import streamlit as st
import pandas as pd
from datetime import timedelta
import cache
from components.grafik_kutu import grafik_kutu_goster
from components.anomali_tablo import tip_badge, durum_badge
from components.faz_kart import faz_metrikler_goster

PERIODS = {"1A": 30, "3A": 90, "6A": 180, "1Y": 365, "TÜM": None}

ANOM_SCROLL_H  = 200
SIKIS_SCROLL_H = 130
CHART_H        = 380

PILL_OPTS  = ["R1", "R2", "Z60", "Z120", "RZ60", "RZ120"]
RADAR_MAP  = {"R1": "radar1", "R2": "radar2"}
ZSCORE_MAP = {"Z60": "anomali_z60", "Z120": "anomali_z120",
              "RZ60": "anomali_rz60", "RZ120": "anomali_rz120"}


def goster(hisseler: list):
    if not hisseler:
        st.warning("Hisse listesi boş.")
        return

    default_idx = 0
    mevcut = st.session_state.get("hd_hisse")
    if mevcut in hisseler:
        default_idx = hisseler.index(mevcut)

    # ── Tek satır: hisse seçici | period | tarih kontrolleri ──
    # Önce tüm sütunlar açılır; selectbox + radio hemen yazılır,
    # tarih sütunları veri geldikten sonra (ama aynı görsel satırda) doldurulur.
    c_h, c_p, c_lbl, c_bas, c_ok, c_bit = st.columns([2.2, 3.2, 0.7, 2.5, 0.3, 2.5])

    with c_h:
        secilen = st.selectbox(
            "", hisseler,
            index=default_idx,
            label_visibility="collapsed",
            key="hd_hisse",
        )

    with c_p:
        period_sec = st.radio(
            "", list(PERIODS.keys()),
            horizontal=True, index=3,
            label_visibility="collapsed",
            key="hd_period",
        )

    # ── Veri çekme ──
    stock_id = cache.stock_id_lookup(secilen)
    if stock_id is None:
        st.warning(f"{secilen} bulunamadı.")
        return

    df_fiyat          = cache.fiyat_verisi(stock_id, gun=500)
    anomaliler        = cache.anomali_kayitlari(secilen)
    anomali_tarihleri = cache.anomali_tarihleri(secilen)
    df_kayitlar       = cache.sikisma_kayitlari(secilen)

    # ── Metrik kartlar (kontrol satırının altında çıkar) ──
    veri_gun  = len(df_fiyat)
    son_tarih = df_fiyat["price_date"].max() if not df_fiyat.empty else None
    toplam_a  = len(anomaliler)
    toplam_s  = len(df_kayitlar)
    radar1_n  = int((df_kayitlar["radar"] == "radar1").sum()) if not df_kayitlar.empty else 0
    radar2_n  = int((df_kayitlar["radar"] == "radar2").sum()) if not df_kayitlar.empty else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    for col, label, val, renk in [
        (m1, "Veri",       f"{veri_gun}g",                                       "#e0e0f0"),
        (m2, "Son",        str(son_tarih)[:10] if son_tarih is not None else "—", "#8888a8"),
        (m3, "Anomali",    toplam_a,                                              "#8888a8"),
        (m4, "Sıkışma R1", radar1_n,                                              "#4d8ef0"),
        (m5, "Sıkışma R2", radar2_n,                                              "#d4820a"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;border-radius:2px;'
            f'padding:10px 12px;margin:6px 0">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:16px;color:{renk};font-weight:300">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Tarih aralığı sütunlarını doldur (üstteki kontrole geri döner) ──
    if not df_fiyat.empty:
        df_fiyat["price_date"] = pd.to_datetime(df_fiyat["price_date"])
        max_date = df_fiyat["price_date"].max().date()
        min_date = df_fiyat["price_date"].min().date()

        gun = PERIODS[period_sec]
        raw_bas = (max_date - timedelta(days=gun)) if gun else min_date
        default_bas = max(raw_bas, min_date)  # veri aralığına sıkıştır

        prev_key = f"hd_prev_period_{secilen}"
        if st.session_state.get(prev_key) != period_sec:
            st.session_state[f"hd_tarih_bas_{secilen}"] = default_bas
            st.session_state[f"hd_tarih_bit_{secilen}"] = max_date
            st.session_state[prev_key] = period_sec

        # Session state'deki değer geçerli aralık dışındaysa sıkıştır
        bas_key = f"hd_tarih_bas_{secilen}"
        bit_key = f"hd_tarih_bit_{secilen}"
        if bas_key in st.session_state:
            st.session_state[bas_key] = max(min_date, min(max_date, st.session_state[bas_key]))
        if bit_key in st.session_state:
            st.session_state[bit_key] = max(min_date, min(max_date, st.session_state[bit_key]))

        c_lbl.markdown(
            '<div class="mv-label" style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
            'text-transform:uppercase;padding-top:10px">Tarih</div>',
            unsafe_allow_html=True,
        )
        with c_bas:
            tarih_bas = st.date_input(
                "bas", key=f"hd_tarih_bas_{secilen}",
                min_value=min_date, max_value=max_date,
                label_visibility="collapsed",
            )
        c_ok.markdown(
            '<div class="mv-arrow" style="color:#2e2e48;padding-top:8px;text-align:center">→</div>',
            unsafe_allow_html=True,
        )
        with c_bit:
            tarih_bit = st.date_input(
                "bit", key=f"hd_tarih_bit_{secilen}",
                min_value=min_date, max_value=max_date,
                label_visibility="collapsed",
            )

        cutoff   = pd.Timestamp(tarih_bas)
        bitis_ts = pd.Timestamp(tarih_bit)
    else:
        cutoff = bitis_ts = tarih_bas = tarih_bit = None

    # ── Sinyal filtresi ──
    sinyal_sec = st.pills(
        "Sinyal",
        PILL_OPTS,
        selection_mode="multi",
        default=PILL_OPTS,
        key=f"hd_sinyal_{secilen}",
        label_visibility="collapsed",
    )
    aktif_radarlar = {RADAR_MAP[r] for r in (sinyal_sec or []) if r in RADAR_MAP}
    aktif_zscore   = {ZSCORE_MAP[z] for z in (sinyal_sec or []) if z in ZSCORE_MAP}

    # ── Ana iki kolon: grafik | listeler ──
    col_main, col_side = st.columns([13, 7], gap="large")

    with col_main:
        if not df_fiyat.empty and cutoff is not None:
            df_filtered = df_fiyat[
                (df_fiyat["price_date"] >= cutoff) &
                (df_fiyat["price_date"] <= bitis_ts)
            ].copy()

            kutular = []
            for _, row in df_kayitlar.iterrows():
                if row.get("radar") not in aktif_radarlar:
                    continue
                bitis_k = pd.to_datetime(row["kutu_bitis"])
                bas_k   = pd.to_datetime(row["kutu_baslangic"])
                if bitis_k < cutoff or bas_k > bitis_ts:
                    continue
                kutular.append({
                    "baslangic": row["kutu_baslangic"],
                    "bitis":     row["kutu_bitis"],
                    "radar":     row["radar"],
                    "zirve":     row.get("cekirdek_zirve") or 0,
                    "dip":       row.get("cekirdek_dip")   or 0,
                    "trend_m":          row.get("trend_m"),
                    "trend_c":          row.get("trend_c"),
                    "kanal_ust_offset": row.get("kanal_ust_offset"),
                    "kanal_alt_offset": row.get("kanal_alt_offset"),
                })

            anoms_filtered = anomaliler
            if not anomaliler.empty:
                anoms_filtered = anomaliler.copy()
                anoms_filtered["baslangic_zaman"] = pd.to_datetime(anoms_filtered["baslangic_zaman"])
                anoms_filtered = anoms_filtered[
                    (anoms_filtered["baslangic_zaman"] >= cutoff) &
                    (anoms_filtered["baslangic_zaman"] <= bitis_ts)
                ]
                if aktif_zscore:
                    anoms_filtered = anoms_filtered[anoms_filtered["anomali_tipi"].isin(aktif_zscore)]
                else:
                    anoms_filtered = anoms_filtered.iloc[0:0]

            # Kanal highlight
            secili_kutu_bas = st.session_state.get(f"hd_kutu_bas_{secilen}")
            gecerli_baslar = {str(k["baslangic"]) for k in kutular}
            if secili_kutu_bas not in gecerli_baslar:
                secili_kutu_bas = None
                st.session_state[f"hd_kutu_bas_{secilen}"] = None

            sinyal_key = "_".join(sorted(sinyal_sec or []))
            grafik_kutu_goster(
                df_filtered, kutular,
                anomali_tarihleri=anomali_tarihleri,
                anomaliler_df=anoms_filtered,
                key=f"grafik_{secilen}_{tarih_bas}_{tarih_bit}_{sinyal_key}_{secili_kutu_bas}",
                yukseklik=CHART_H,
                secili_kutu_bas=secili_kutu_bas,
            )

            # Kanal Odak
            if kutular:
                st.markdown(
                    '<div style="font-size:9px;color:#2e2e48;letter-spacing:0.1em;'
                    'text-transform:uppercase;margin:8px 0 6px 0">Kanal Odak</div>',
                    unsafe_allow_html=True,
                )
                MAX_ROW = 6
                for row_start in range(0, len(kutular), MAX_ROW):
                    chunk = kutular[row_start:row_start + MAX_ROW]
                    cols  = st.columns(len(chunk))
                    for col_b, k in zip(cols, chunk):
                        bas_s   = str(k["baslangic"])
                        bit_s   = str(k["bitis"])
                        radar_s = k["radar"].upper()
                        is_sec  = secili_kutu_bas == bas_s
                        label   = f"{radar_s} · {bas_s[5:]} → {bit_s[5:]}"
                        with col_b:
                            if st.button(label, key=f"hd_kbtn_{secilen}_{bas_s}_{bit_s}_{k['radar']}",
                                         type="primary" if is_sec else "secondary",
                                         use_container_width=True):
                                st.session_state[f"hd_kutu_bas_{secilen}"] = None if is_sec else bas_s
                                st.rerun()
        else:
            st.info("Fiyat verisi bulunamadı.")

        if not df_kayitlar.empty:
            st.markdown(
                '<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;'
                'text-transform:uppercase;margin:12px 0 6px 0">'
                '§ 2 &nbsp; Son Sıkışma Metrikleri</div>',
                unsafe_allow_html=True,
            )
            son = df_kayitlar.iloc[0]
            faz_metrikler_goster(
                pencere_gun      =int(son["pencere_uzunlugu"])    if pd.notna(son.get("pencere_uzunlugu"))    else None,
                fiziki_limit     =float(son["fiziki_limit"])      if pd.notna(son.get("fiziki_limit"))        else None,
                efor_rasyosu     =float(son["efor_rasyosu"])      if pd.notna(son.get("efor_rasyosu"))        else None,
                sok_sayisi       =int(son["sok_sayisi"])          if pd.notna(son.get("sok_sayisi"))          else None,
                sok_hacim_yuzdesi=float(son["sok_hacim_yuzdesi"]) if pd.notna(son.get("sok_hacim_yuzdesi"))  else None,
            )

    with col_side:
        # ── Anomali Kayıtları ──
        st.markdown(
            f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:0 0 6px 0">'
            f'<span style="color:#2e2e48;margin-right:8px">§ 3</span>Anomali Kayıtları'
            f'<span style="color:#2e2e48;font-size:10px;margin-left:8px">· {toplam_a} kayıt</span></div>',
            unsafe_allow_html=True,
        )

        if anomaliler.empty:
            st.markdown(
                '<div style="font-size:11px;color:#2e2e48;padding:12px;'
                'border:1px solid #1a1a24;border-radius:2px">Kayıt yok.</div>',
                unsafe_allow_html=True,
            )
        else:
            sort_a = st.radio(
                "sort_a", ["Skor↓", "Tarih↓"],
                horizontal=True, label_visibility="collapsed",
                key="hd_sort_anomali",
            )
            anomaliler = (
                anomaliler.sort_values("baslangic_zaman", ascending=False)
                if sort_a == "Tarih↓"
                else anomaliler.sort_values("skor", ascending=False)
            )
            st.markdown(
                '<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                'gap:0;padding:5px 10px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
                '<span>Tarih</span><span>Tip</span><span>Skor</span><span>Durum</span></div>',
                unsafe_allow_html=True,
            )
            with st.container(height=ANOM_SCROLL_H, border=False):
                for _, row in anomaliler.iterrows():
                    tarih = str(row["baslangic_zaman"])[:10]
                    st.markdown(
                        f'<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                        f'gap:0;padding:7px 10px;border-bottom:1px solid #0f0f18;align-items:center">'
                        f'<span style="font-size:10px;color:#8888a8">{tarih}</span>'
                        f'<span>{tip_badge(row["anomali_tipi"])}</span>'
                        f'<span style="font-size:10px;color:#4a4a68">{row["skor"]:.4f}</span>'
                        f'{durum_badge(row["durum"])}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # ── Sıkışma Kayıtları ──
        st.markdown(
            f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;margin:14px 0 6px 0">'
            f'<span style="color:#2e2e48;margin-right:8px">§ 4</span>Sıkışma Kayıtları'
            f'<span style="color:#2e2e48;font-size:10px;margin-left:8px">· {toplam_s} kayıt</span></div>',
            unsafe_allow_html=True,
        )

        if df_kayitlar.empty:
            st.markdown(
                '<div style="font-size:11px;color:#2e2e48;padding:12px;'
                'border:1px solid #1a1a24;border-radius:2px">Kayıt yok.</div>',
                unsafe_allow_html=True,
            )
        else:
            sort_s = st.radio(
                "sort_s", ["Tarih↓", "Efor↓"],
                horizontal=True, label_visibility="collapsed",
                key="hd_sort_sikisma",
            )
            df_kayitlar = df_kayitlar.sort_values(
                "efor_rasyosu" if sort_s == "Efor↓" else "kutu_bitis",
                ascending=False,
            )
            st.markdown(
                '<div style="display:grid;grid-template-columns:56px 100px 42px 62px 48px;'
                'gap:0;padding:5px 10px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
                '<span>Radar</span><span>Bitiş</span><span>Gün</span>'
                '<span>Efor</span><span>Şok</span></div>',
                unsafe_allow_html=True,
            )
            with st.container(height=SIKIS_SCROLL_H, border=False):
                for _, row in df_kayitlar.iterrows():
                    radar_renk = "#4d8ef0" if row["radar"] == "radar1" else "#d4820a"
                    efor_str   = f'{row["efor_rasyosu"]:.2f}x' if pd.notna(row.get("efor_rasyosu")) else "—"
                    sok_str    = str(int(row["sok_sayisi"]))    if pd.notna(row.get("sok_sayisi"))    else "—"
                    pencere    = str(int(row["pencere_uzunlugu"])) if pd.notna(row.get("pencere_uzunlugu")) else "—"
                    bitis      = str(row["kutu_bitis"])[:10]
                    st.markdown(
                        f'<div style="display:grid;grid-template-columns:56px 100px 42px 62px 48px;'
                        f'gap:0;padding:7px 10px;border-bottom:1px solid #0f0f18;align-items:center">'
                        f'<span style="font-size:10px;color:{radar_renk}">{row["radar"].upper()}</span>'
                        f'<span style="font-size:10px;color:#8888a8">{bitis}</span>'
                        f'<span style="font-size:10px;color:#4a4a68">{pencere}g</span>'
                        f'<span style="font-size:10px;color:#e0e0f0">{efor_str}</span>'
                        f'<span style="font-size:10px;color:#d4820a">{sok_str}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
