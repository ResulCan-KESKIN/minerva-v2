"""
Candlestick + FAZ A (anomali) + FAZ B (sıkışma kutuları) birleşik grafik.
"""

import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

CHART_BG   = "#0c0c13"
GRID_COLOR = "#0f0f18"
BORDER_COL = "#1a1a24"
TEXT_COLOR = "#3a3a55"

RADAR_RENK = {
    "radar1": "#4d8ef0",
    "radar2": "#d4820a",
}

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


def _hazirla(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values("price_date")
    df["time"] = df["price_date"].dt.strftime("%Y-%m-%d")
    return df


def grafik_kutu_goster(
    df: pd.DataFrame,
    kutular: list[dict],
    anomali_tarihleri: set | None = None,
    anomaliler_df: pd.DataFrame | None = None,
    key: str = "grafik_kutu",
    yukseklik: int = 420,
):
    """
    df            : price_date, acilis, yuksek, dusuk, kapanis, hacim sütunlu OHLCV.
    kutular       : Sıkışma kutuları — {baslangic, bitis, radar, zirve, dip}.
    anomali_tarihleri : Set; hacim barlarını vurgulamak için (geriye uyumluluk).
    anomaliler_df : DataFrame; verilirse marker olarak tipli anomaliler basılır.
                    Beklenen sütunlar: baslangic_zaman, anomali_tipi, skor.
    """
    df = _hazirla(df)

    # Anomali tarihleri set'i — DataFrame varsa oradan da topla
    anomali_set = {str(t) for t in (anomali_tarihleri or set())}
    if anomaliler_df is not None and not anomaliler_df.empty:
        anom_dates = pd.to_datetime(anomaliler_df["baslangic_zaman"]).dt.date.astype(str)
        anomali_set.update(anom_dates.tolist())

    # ── Markers ──
    markers = []

    # FAZ A: Tipli anomali markerları (üst tarafta)
    if anomaliler_df is not None and not anomaliler_df.empty:
        anoms = anomaliler_df.copy()
        anoms["tarih"] = pd.to_datetime(anoms["baslangic_zaman"]).dt.date.astype(str)
        for _, row in anoms.iterrows():
            tip = row.get("anomali_tipi", "")
            skor = float(row["skor"]) if pd.notna(row.get("skor")) else 0.0
            renk = TIP_RENK.get(tip, "#666680")
            kisa = TIP_KISA.get(tip, "A")
            markers.append({
                "time": row["tarih"],
                "position": "aboveBar",
                "color": renk,
                "shape": "arrowDown",
                "text": f"{kisa}·{skor:.1f}",
            })

    # FAZ B: Sıkışma kutu markerları (alt tarafta)
    for k in kutular:
        bas = str(k["baslangic"])
        bit = str(k["bitis"])
        renk = RADAR_RENK.get(k.get("radar", "radar1"), "#4d8ef0")
        markers.append({
            "time": bas, "position": "belowBar", "color": renk,
            "shape": "arrowUp", "text": k.get("radar", "").upper(),
        })
        markers.append({
            "time": bit, "position": "belowBar", "color": renk,
            "shape": "circle", "text": "BOX",
        })

    # ── Seriler ──
    candle_data = df[["time", "acilis", "yuksek", "dusuk", "kapanis"]].rename(
        columns={"acilis": "open", "yuksek": "high", "dusuk": "low", "kapanis": "close"}
    ).to_dict("records")

    volume_data = [
        {
            "time":  row["time"],
            "value": float(row["hacim"]),
            "color": "#d4820a66" if row["time"] in anomali_set else "#1e1e3044",
        }
        for _, row in df.iterrows()
    ]

    # Kutu zirve/dip seviye çizgileri
    extra_series = []
    for k in kutular:
        renk = RADAR_RENK.get(k.get("radar", "radar1"), "#4d8ef0")
        bas, bit = str(k["baslangic"]), str(k["bitis"])
        zirve = float(k.get("zirve") or 0)
        dip   = float(k.get("dip")   or 0)

        if zirve > 0:
            zirve_data = [
                {"time": row["time"], "value": zirve}
                for _, row in df.iterrows() if bas <= row["time"] <= bit
            ]
            if zirve_data:
                extra_series.append({
                    "type": "Line", "data": zirve_data,
                    "options": {
                        "color": renk, "lineWidth": 1, "lineStyle": 2,
                        "priceScaleId": "right",
                        "lastValueVisible": False, "priceLineVisible": False,
                    },
                })

        if dip > 0:
            dip_data = [
                {"time": row["time"], "value": dip}
                for _, row in df.iterrows() if bas <= row["time"] <= bit
            ]
            if dip_data:
                extra_series.append({
                    "type": "Line", "data": dip_data,
                    "options": {
                        "color": renk, "lineWidth": 1, "lineStyle": 2,
                        "priceScaleId": "right",
                        "lastValueVisible": False, "priceLineVisible": False,
                    },
                })

    chart_cfg = {
        "layout": {
            "background": {"type": "solid", "color": CHART_BG},
            "textColor": TEXT_COLOR,
            "fontSize": 10,
            "fontFamily": "IBM Plex Mono",
        },
        "grid": {
            "vertLines": {"color": GRID_COLOR},
            "horzLines": {"color": GRID_COLOR},
        },
        "crosshair": {"mode": 1},
        "timeScale":       {"borderColor": BORDER_COL, "barSpacing": 5},
        "rightPriceScale": {
            "borderColor":  BORDER_COL,
            "scaleMargins": {"top": 0.05, "bottom": 0.22},
        },
        "height": yukseklik,
    }

    series_list = [
        {
            "type": "Candlestick",
            "data": candle_data,
            "markers": markers,
            "options": {
                "upColor":       "#22c55e",
                "downColor":     "#e84040",
                "borderUpColor": "#22c55e",
                "borderDownColor": "#e84040",
                "wickUpColor":   "#22c55e",
                "wickDownColor": "#e84040",
                "priceScaleId":  "right",
            },
        },
        {
            "type": "Histogram",
            "data": volume_data,
            "options": {
                "priceFormat":  {"type": "volume"},
                "priceScaleId": "vol",
                "scaleMargins": {"top": 0.82, "bottom": 0},
            },
        },
    ] + extra_series

    renderLightweightCharts([{"chart": chart_cfg, "series": series_list}], key=key)
