import streamlit as st
import pandas as pd
from datetime import timedelta
import cache
from components.grafik_kutu import grafik_kutu_goster
from components.anomali_tablo import tip_badge, durum_badge
from components.zscore_panel import zscore_panel_goster
from components.faz_kart import faz_metrikler_goster

PERIODS = {"1A": 30, "3A": 90, "6A": 180, "1Y": 365, "TÜM": None}


def goster(secilen: str):
    stock_id = cache.stock_id_lookup(secilen)
    if stock_id is None:
        st.warning(f"{secilen} bulunamadı.")
        return

    df_fiyat          = cache.fiyat_verisi(stock_id, gun=500)
    anomaliler        = cache.anomali_kayitlari(secilen)
    anomali_tarihleri = cache.anomali_tarihleri(secilen)
    df_kayitlar       = cache.sikisma_kayitlari(secilen)
    zscore_df         = cache.zscore_seri(stock_id, gun=500)

    # ── Üst metrikler ──
    veri_gun    = len(df_fiyat)
    son_tarih   = df_fiyat["price_date"].max() if not df_fiyat.empty else None
    toplam_a    = len(anomaliler)
    beklemede_a = int((anomaliler["durum"] == "beklemede").sum()) if not anomaliler.empty else 0
    toplam_s    = len(df_kayitlar)
    radar1_n    = int((df_kayitlar["radar"] == "radar1").sum()) if not df_kayitlar.empty else 0
    radar2_n    = int((df_kayitlar["radar"] == "radar2").sum()) if not df_kayitlar.empty else 0

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    for col, label, val, renk in [
        (m1, "Veri",          f"{veri_gun}g",                                  "#e0e0f0"),
        (m2, "Son",           str(son_tarih)[:10] if son_tarih is not None else "—", "#8888a8"),
        (m3, "Anomali",       toplam_a,                                        "#8888a8"),
        (m4, "Beklemede",     beklemede_a,                                     "#d4820a"),
        (m5, "Sıkışma R1",    radar1_n,                                        "#4d8ef0"),
        (m6, "Sıkışma R2",    radar2_n,                                        "#d4820a"),
    ]:
        col.markdown(
            f'<div style="background:#0f0f18;border:1px solid #1a1a24;'
            f'border-radius:2px;padding:10px 12px;margin-bottom:12px">'
            f'<div style="font-size:9px;color:#2e2e48;letter-spacing:0.12em;'
            f'text-transform:uppercase;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:16px;color:{renk};font-weight:300">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── İki kolon: sol = grafik + zscore + metrikler, sağ = kayıt listeleri ──
    col_main, col_side = st.columns([13, 7], gap="large")

    with col_main:
        row_baslik, row_period = st.columns([4, 4])
        with row_baslik:
            st.markdown(
                '<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;'
                'text-transform:uppercase;padding-top:8px">'
                '§ 1 &nbsp; Fiyat Grafiği + Sıkışma Kutuları + Anomaliler</div>',
                unsafe_allow_html=True,
            )
        with row_period:
            period_sec = st.radio(
                "period",
                list(PERIODS.keys()),
                horizontal=True,
                index=3,
                label_visibility="collapsed",
                key="hd_period",
            )

        gun = PERIODS[period_sec]

        if not df_fiyat.empty:
            df_fiyat["price_date"] = pd.to_datetime(df_fiyat["price_date"])
            cutoff = df_fiyat["price_date"].max() - timedelta(days=gun) if gun else None
            df_filtered = df_fiyat[df_fiyat["price_date"] >= cutoff].copy() if cutoff is not None else df_fiyat.copy()

            kutular = []
            for _, row in df_kayitlar.iterrows():
                bitis = pd.to_datetime(row["kutu_bitis"])
                if cutoff is not None and bitis < cutoff:
                    continue
                kutular.append({
                    "baslangic": row["kutu_baslangic"],
                    "bitis":     row["kutu_bitis"],
                    "radar":     row["radar"],
                    "zirve":     row.get("cekirdek_zirve") or 0,
                    "dip":       row.get("cekirdek_dip")   or 0,
                })

            anoms_filtered = anomaliler
            if cutoff is not None and not anomaliler.empty:
                anoms_filtered = anomaliler.copy()
                anoms_filtered["baslangic_zaman"] = pd.to_datetime(anoms_filtered["baslangic_zaman"])
                anoms_filtered = anoms_filtered[anoms_filtered["baslangic_zaman"] >= cutoff]

            grafik_kutu_goster(
                df_filtered, kutular,
                anomali_tarihleri=anomali_tarihleri,
                anomaliler_df=anoms_filtered,
                key=f"grafik_{secilen}_{period_sec}", yukseklik=360,
            )

            if not zscore_df.empty:
                zscore_df["tarih"] = pd.to_datetime(zscore_df["tarih"])
                if gun:
                    zscore_df = zscore_df[zscore_df["tarih"] >= (zscore_df["tarih"].max() - timedelta(days=gun))]
                zscore_panel_goster(zscore_df)
        else:
            st.info("Fiyat verisi bulunamadı.")

        if not df_kayitlar.empty:
            st.markdown(
                '<div style="font-size:10px;color:#2a2a40;letter-spacing:0.1em;'
                'text-transform:uppercase;margin:16px 0 8px 0">'
                '§ 2 &nbsp; Son Sıkışma Metrikleri</div>',
                unsafe_allow_html=True,
            )
            son = df_kayitlar.iloc[0]
            faz_metrikler_goster(
                pencere_gun=int(son["pencere_uzunlugu"]) if pd.notna(son.get("pencere_uzunlugu")) else None,
                fiziki_limit=float(son["fiziki_limit"]) if pd.notna(son.get("fiziki_limit")) else None,
                efor_rasyosu=float(son["efor_rasyosu"]) if pd.notna(son.get("efor_rasyosu")) else None,
                sok_sayisi=int(son["sok_sayisi"]) if pd.notna(son.get("sok_sayisi")) else None,
                sok_hacim_yuzdesi=float(son["sok_hacim_yuzdesi"]) if pd.notna(son.get("sok_hacim_yuzdesi")) else None,
            )

    with col_side:
        # ── Anomali Kayıtları ──
        st.markdown(
            f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
            f'margin:0 0 10px 0">'
            f'<span style="color:#2e2e48;margin-right:8px">§ 3</span>'
            f'Anomali Kayıtları'
            f'<span style="color:#2e2e48;font-size:10px;margin-left:8px">'
            f'· {toplam_a} kayıt</span></div>',
            unsafe_allow_html=True,
        )

        if anomaliler.empty:
            st.markdown(
                '<div style="font-size:11px;color:#2e2e48;padding:16px;'
                'border:1px solid #1a1a24;border-radius:2px">Kayıt yok.</div>',
                unsafe_allow_html=True,
            )
        else:
            sort_a = st.radio(
                "sort_a",
                ["Skor↓", "Tarih↓"],
                horizontal=True,
                label_visibility="collapsed",
                key="hd_sort_anomali",
            )
            if sort_a == "Tarih↓":
                anomaliler = anomaliler.sort_values("baslangic_zaman", ascending=False)
            else:
                anomaliler = anomaliler.sort_values("skor", ascending=False)

            st.markdown(
                '<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                'gap:0;padding:6px 10px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
                '<span>Tarih</span><span>Tip</span><span>Skor</span><span>Durum</span></div>',
                unsafe_allow_html=True,
            )
            for _, row in anomaliler.iterrows():
                tarih = str(row["baslangic_zaman"])[:10]
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:88px 52px 64px 80px;'
                    f'gap:0;padding:8px 10px;border-bottom:1px solid #0f0f18;align-items:center">'
                    f'<span style="font-size:10px;color:#8888a8">{tarih}</span>'
                    f'<span>{tip_badge(row["anomali_tipi"])}</span>'
                    f'<span style="font-size:10px;color:#4a4a68">{row["skor"]:.4f}</span>'
                    f'{durum_badge(row["durum"])}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── Sıkışma Kayıtları ──
        st.markdown(
            f'<div style="font-size:11px;color:#e0e0f0;letter-spacing:0.06em;'
            f'margin:20px 0 10px 0">'
            f'<span style="color:#2e2e48;margin-right:8px">§ 4</span>'
            f'Sıkışma Kayıtları'
            f'<span style="color:#2e2e48;font-size:10px;margin-left:8px">'
            f'· {toplam_s} kayıt</span></div>',
            unsafe_allow_html=True,
        )

        if df_kayitlar.empty:
            st.markdown(
                '<div style="font-size:11px;color:#2e2e48;padding:16px;'
                'border:1px solid #1a1a24;border-radius:2px">Kayıt yok.</div>',
                unsafe_allow_html=True,
            )
        else:
            sort_s = st.radio(
                "sort_s",
                ["Tarih↓", "Efor↓"],
                horizontal=True,
                label_visibility="collapsed",
                key="hd_sort_sikisma",
            )
            df_kayitlar = df_kayitlar.sort_values(
                "efor_rasyosu" if sort_s == "Efor↓" else "kutu_bitis",
                ascending=False,
            )

            st.markdown(
                '<div style="display:grid;grid-template-columns:56px 100px 42px 62px 48px;'
                'gap:0;padding:6px 10px;border-bottom:1px solid #1a1a24;'
                'font-size:9px;color:#2e2e48;letter-spacing:0.1em;text-transform:uppercase">'
                '<span>Radar</span><span>Bitiş</span><span>Gün</span>'
                '<span>Efor</span><span>Şok</span></div>',
                unsafe_allow_html=True,
            )

            for _, row in df_kayitlar.iterrows():
                radar_renk = "#4d8ef0" if row["radar"] == "radar1" else "#d4820a"
                efor_str   = f'{row["efor_rasyosu"]:.2f}x' if pd.notna(row.get("efor_rasyosu")) else "—"
                sok_str    = str(int(row["sok_sayisi"])) if pd.notna(row.get("sok_sayisi")) else "—"
                pencere    = str(int(row["pencere_uzunlugu"])) if pd.notna(row.get("pencere_uzunlugu")) else "—"
                bitis      = str(row["kutu_bitis"])[:10]

                st.markdown(
                    f'<div style="display:grid;grid-template-columns:56px 100px 42px 62px 48px;'
                    f'gap:0;padding:8px 10px;border-bottom:1px solid #0f0f18;align-items:center">'
                    f'<span style="font-size:10px;color:{radar_renk}">{row["radar"].upper()}</span>'
                    f'<span style="font-size:10px;color:#8888a8">{bitis}</span>'
                    f'<span style="font-size:10px;color:#4a4a68">{pencere}g</span>'
                    f'<span style="font-size:10px;color:#e0e0f0">{efor_str}</span>'
                    f'<span style="font-size:10px;color:#d4820a">{sok_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
