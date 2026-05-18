# veri_guncelle.py — Yahoo Finance → stock_prices (günlük güncelleme + 10 yıl backfill)
import psycopg2
import pandas as pd
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
TARGET_START = (pd.Timestamp.today() - pd.DateOffset(years=10)).strftime("%Y-%m-%d")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def hisseleri_cek(conn) -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute("SELECT id, symbol FROM stocks WHERE is_active = true ORDER BY symbol")
    hisseler = cur.fetchall()
    cur.close()
    return hisseler


def tarih_aralik_cek(conn, stock_id: int) -> tuple:
    """Hisse için (en_eski, en_yeni) tarih ikilisi; veri yoksa (None, None)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT MIN(price_date::date), MAX(price_date::date)
        FROM stock_prices WHERE stock_id = %s
    """, (stock_id,))
    row = cur.fetchone()
    cur.close()
    return (row[0], row[1]) if row else (None, None)


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


def _fetch_ve_yaz(conn, grup: list[tuple[int, str]], start_str: str, end_str: str) -> int:
    """Verilen tarih aralığını yfinance'den çek, DB'ye yaz."""
    tickerlar = [f"{s}.IS" for _, s in grup]
    id_map = {f"{s}.IS": sid for sid, s in grup}

    try:
        raw = yf.download(
            tickerlar,
            start=start_str,
            end=end_str,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"  Çekme hatası ({start_str} → {end_str}): {e}")
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
                print(f"  {symbol}: +{eklenen} satır")
            toplam += eklenen

        except Exception as e:
            print(f"  {symbol}: HATA — {e}")

    return toplam


def grup_isle(conn, grup: list[tuple[int, str]]) -> int:
    """
    Her grup için iki aralık hesapla:
      1. Backfill  : TARGET_START → en eski mevcut tarih  (geçmiş boşluk)
      2. İleri fill: en yeni tarih+1 → bugün              (yeni günler)
    Veri hiç yoksa: TARGET_START → bugün (tek seferde).
    """
    today_str = (pd.Timestamp.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    target_ts = pd.Timestamp(TARGET_START)

    # Gruptaki her hisse için (en_eski, en_yeni) çek
    araliklar = [tarih_aralik_cek(conn, sid) for sid, _ in grup]
    mevcut    = [(e, y) for e, y in araliklar if e is not None and y is not None]

    toplam = 0

    if not mevcut:
        # Hiç veri yok — tam 10 yıl çek
        print(f"  Backfill (yeni): {TARGET_START} → bugün")
        toplam += _fetch_ve_yaz(conn, grup, TARGET_START, today_str)
        return toplam

    en_eski_db = min(pd.Timestamp(e) for e, _ in mevcut)
    en_yeni_db = max(pd.Timestamp(y) for _, y in mevcut)

    # 1. Backfill: DB'deki en eski tarih TARGET_START'tan sonraysa
    if en_eski_db > target_ts:
        bf_end = en_eski_db.strftime("%Y-%m-%d")
        print(f"  Backfill: {TARGET_START} → {bf_end}")
        toplam += _fetch_ve_yaz(conn, grup, TARGET_START, bf_end)
        time.sleep(1)

    # 2. İleri fill: son günden bugüne
    ileri_start = (en_yeni_db + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    if ileri_start < today_str:
        print(f"  İleri fill: {ileri_start} → bugün")
        toplam += _fetch_ve_yaz(conn, grup, ileri_start, today_str)

    return toplam


if __name__ == "__main__":
    print("Minerva Veri Güncelleme Başladı...")
    print(f"Hedef başlangıç: {TARGET_START}")
    print("=" * 60)

    conn = get_conn()
    hisseler = hisseleri_cek(conn)
    print(f"{len(hisseler)} hisse güncellenecek.\n")

    toplam = 0
    for i in range(0, len(hisseler), GRUP_BOYUTU):
        grup = hisseler[i:i + GRUP_BOYUTU]
        print(f"Grup {i // GRUP_BOYUTU + 1}: {grup[0][1]} → {grup[-1][1]}")
        toplam += grup_isle(conn, grup)
        time.sleep(2)

    conn.close()
    print("=" * 60)
    print(f"Tamamlandı. Toplam {toplam} yeni satır eklendi.")
