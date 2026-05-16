# veri_guncelle.py — Yahoo Finance → stock_prices (günlük güncelleme)
# Trigger otomatik volume_analysis'i dolduracak
import psycopg2
import pandas as pd
import numpy as np
import yfinance as yf
import time
import os
import warnings

warnings.filterwarnings('ignore')

def _clean(v): return v.replace(chr(0xFEFF), "").strip()

DB_CONFIG = {
    "host": _clean(os.environ.get("EXT_DB_HOST", "130.110.245.87")),
    "port": int(_clean(os.environ.get("EXT_DB_PORT", "5432"))),
    "database": _clean(os.environ.get("EXT_DB_NAME", "postgres")),
    "user": _clean(os.environ.get("EXT_DB_USER", "postgres")),
    "password": _clean(os.environ.get("EXT_DB_PASSWORD", "QuantShine2025."))
}

GRUP_BOYUTU = 50


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def hisseleri_cek(conn) -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute("SELECT id, symbol FROM stocks WHERE is_active = true ORDER BY symbol")
    hisseler = cur.fetchall()
    cur.close()
    return hisseler


def son_tarih_cek(conn, stock_id: int):
    """Bu hisse için stock_prices'taki son veri tarihini bul."""
    cur = conn.cursor()
    cur.execute("""
        SELECT MAX(price_date::date) FROM stock_prices WHERE stock_id = %s
    """, (stock_id,))
    sonuc = cur.fetchone()[0]
    cur.close()
    return sonuc


def db_yaz(conn, stock_id: int, df: pd.DataFrame) -> int:
    cur = conn.cursor()
    eklenen = 0

    for _, satir in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO stock_prices
                    (stock_id, price_date, open_price, high_price,
                     low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_id, price_date) DO NOTHING
            """, (
                stock_id,
                satir["price_date"],
                float(satir["open"]),
                float(satir["high"]),
                float(satir["low"]),
                float(satir["close"]),
                int(satir["volume"]),
            ))
            if cur.rowcount > 0:
                eklenen += 1
        except Exception as e:
            print(f"  Satır hatası: {e}")
            continue

    conn.commit()
    cur.close()
    return eklenen


def grup_isle(conn, grup: list[tuple[int, str]]) -> int:
    """50 hisseyi toplu çek, yeni günleri yaz."""
    tickerlar = [f"{s}.IS" for _, s in grup]
    id_map = {f"{s}.IS": sid for sid, s in grup}

    # En eski son tarih — o günden itibaren çek
    son_tarihler = []
    for sid, _ in grup:
        t = son_tarih_cek(conn, sid)
        if t:
            son_tarihler.append(t)

    if son_tarihler:
        en_eski = min(son_tarihler)
        start = pd.Timestamp(en_eski) + pd.Timedelta(days=1)
        start_str = start.strftime("%Y-%m-%d")
        end_str = (pd.Timestamp.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start_str = "2016-01-01"
        end_str = (pd.Timestamp.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        raw = yf.download(
            tickerlar,
            start=start_str,
            end=end_str,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True
        )
    except Exception as e:
        print(f"  Grup çekme hatası: {e}")
        return 0

    if raw.empty:
        return 0

    toplam = 0
    for ticker, stock_id in id_map.items():
        symbol = ticker.replace(".IS", "")
        try:
            if len(tickerlar) == 1:
                df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
            else:
                if ticker not in raw.columns.get_level_values(0):
                    continue
                df = raw[ticker][["Open", "High", "Low", "Close", "Volume"]].copy()

            df.columns = ["open", "high", "low", "close", "volume"]
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df["price_date"] = df.index.date
            df = df.reset_index(drop=True).dropna(subset=["close"])

            if df.empty:
                continue

            eklenen = db_yaz(conn, stock_id, df)
            if eklenen > 0:
                print(f"  {symbol}: {eklenen} yeni satır eklendi.")
            toplam += eklenen

        except Exception as e:
            print(f"  {symbol}: HATA — {e}")

    return toplam


if __name__ == "__main__":
    print("Minerva Veri Güncelleme Başladı...")
    print("=" * 60)

    conn = get_conn()
    hisseler = hisseleri_cek(conn)
    print(f"{len(hisseler)} hisse güncellenecek.\n")

    toplam = 0
    for i in range(0, len(hisseler), GRUP_BOYUTU):
        grup = hisseler[i:i + GRUP_BOYUTU]
        print(f"Grup {i//GRUP_BOYUTU + 1}: {grup[0][1]} → {grup[-1][1]}")
        toplam += grup_isle(conn, grup)
        time.sleep(2)

    conn.close()
    print("=" * 60)
    print(f"Tamamlandı. Toplam {toplam} yeni satır eklendi.")
