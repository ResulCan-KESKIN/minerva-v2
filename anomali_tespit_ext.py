# anomali_tespit_ext.py — volume_analysis tablosundan Z-Score anomali tespiti
# Yöntem: ≥120g → ECDF 4 seri | 60-119g → ECDF 60g | 0-59g → t-dağılımı
# Eşik: her yeni gün için o günden önceki son 60/120 günün %95 persantili
# Kontrol: sadece son işlemden sonraki yeni günler
import psycopg2
import pandas as pd
import numpy as np
from scipy import stats
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

def _clean(v): return v.replace(chr(0xFEFF), "").strip()

EXT_CONFIG = {
    "host": _clean(os.environ["EXT_DB_HOST"]),
    "port": int(_clean(os.environ["EXT_DB_PORT"])),
    "database": _clean(os.environ["EXT_DB_NAME"]),
    "user": _clean(os.environ["EXT_DB_USER"]),
    "password": _clean(os.environ["EXT_DB_PASSWORD"]),
}

# Kolon adı, anomali tipi, pencere boyutu
ZSCORE_4 = [
    ("z_score_60",         "anomali_z60",  60),
    ("z_score_120",        "anomali_z120", 120),
    ("z_score_robust_60",  "anomali_rz60",  60),
    ("z_score_robust_120", "anomali_rz120", 120),
]

ZSCORE_60 = [
    ("z_score_60",        "anomali_z60",  60),
    ("z_score_robust_60", "anomali_rz60", 60),
]

MAX_WORKERS = 2


def get_conn():
    return psycopg2.connect(**EXT_CONFIG)


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1 — VERİ ÇEKME
# ═══════════════════════════════════════════════════════════════

def hisseleri_cek() -> list[tuple[int, str]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT s.id, s.symbol
        FROM stocks s
        INNER JOIN volume_analysis va ON va.stock_id = s.id
        WHERE s.is_active = true
        ORDER BY s.symbol
    """)
    hisseler = cur.fetchall()
    cur.close()
    conn.close()
    return hisseler


def son_islenen_tarih(conn, symbol: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT MAX(baslangic_zaman::date)
        FROM anomali_kayitlari
        WHERE hisse_kodu = %s
    """, (symbol,))
    sonuc = cur.fetchone()[0]
    cur.close()
    return sonuc


def zscore_verisi_cek(conn, stock_id: int) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT price_date, z_score_60, z_score_120,
               z_score_robust_60, z_score_robust_120
        FROM volume_analysis
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))


def fiyat_verisi_cek(conn, stock_id: int) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT price_date, close_price
        FROM stock_prices
        WHERE stock_id = %s
        ORDER BY price_date
    """, conn, params=(stock_id,))


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2 — FEATURE MÜHENDİSLİĞİ (inaktif — ileriki fazlar için)
# ═══════════════════════════════════════════════════════════════

def fiyat_hacim_uyumsuzlugu(df):
    """İNAKTİF — ileriki fazlar için hazır bekliyor."""
    pass


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3 — ANOMALİ TESPİTİ
# ═══════════════════════════════════════════════════════════════

def _kaydet_toplu(cur, kayitlar: list) -> int:
    if not kayitlar:
        return 0
    cur.executemany("""
        INSERT INTO anomali_kayitlari
            (hisse_kodu, anomali_tipi, skor, baslangic_zaman, durum, kaynak)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, kayitlar)
    return cur.rowcount


def _ecdf_anomaliler(df_tam: pd.DataFrame, df_yeni: pd.DataFrame, tanimlar: list) -> list:
    """
    Her yeni gün için:
    - Eşik = o günden önceki son N günün Z-Score'larının %95 persantili
    - O günün Z-Score'u eşiği aşıyorsa → anomali
    """
    sonuclar = []

    for kolon, tip, pencere in tanimlar:
        for _, yeni_satir in df_yeni.iterrows():
            yeni_tarih = yeni_satir["price_date"]
            yeni_deger = pd.to_numeric(yeni_satir[kolon], errors="coerce")

            if pd.isna(yeni_deger):
                continue

            # Bu günden önceki son `pencere` günün Z-Score'ları
            gecmis = df_tam[df_tam["price_date"] < yeni_tarih][kolon].dropna().iloc[-pencere:]

            if len(gecmis) < pencere // 2:
                continue

            esik = float(gecmis.abs().quantile(0.95))

            if abs(yeni_deger) >= esik:
                sonuclar.append((tip, float(abs(yeni_deger)), yeni_tarih.date(), "volume_analysis"))

    return sonuclar


def _t_dagilimi_anomaliler(conn, stock_id: int, df_yeni: pd.DataFrame) -> list:
    df_fiyat = fiyat_verisi_cek(conn, stock_id)
    if len(df_fiyat) < 3:
        return []
    df_fiyat["price_date"] = pd.to_datetime(df_fiyat["price_date"])
    df_fiyat["close_price"] = pd.to_numeric(df_fiyat["close_price"], errors="coerce")
    df_fiyat = df_fiyat.dropna()
    df_fiyat["log_getiri"] = np.log(df_fiyat["close_price"] / df_fiyat["close_price"].shift(1))
    df_fiyat = df_fiyat.dropna(subset=["log_getiri"])
    if len(df_fiyat) < 3:
        return []
    mu = float(df_fiyat["log_getiri"].mean())
    std = float(df_fiyat["log_getiri"].std(ddof=1)) or 1.0
    t_kritik = float(stats.t.ppf(0.95, df=len(df_fiyat) - 1))
    yeni_tarihler = set(pd.to_datetime(df_yeni["price_date"]).dt.date)
    sonuclar = []
    for _, satir in df_fiyat[df_fiyat["price_date"].dt.date.isin(yeni_tarihler)].iterrows():
        t_stat = float(abs((satir["log_getiri"] - mu) / std))
        if t_stat >= t_kritik:
            sonuclar.append(("anomali_t", t_stat, satir["price_date"].date(), "t_dagilimi"))
    return sonuclar


def anomali_tara(stock_id: int, symbol: str) -> str:
    try:
        conn = get_conn()
        df_tam = zscore_verisi_cek(conn, stock_id)
        n = len(df_tam)

        if n == 0:
            conn.close()
            return f"{symbol}: Veri yok."

        df_tam["price_date"] = pd.to_datetime(df_tam["price_date"])

        # Sadece yeni günleri işle
        son_tarih = son_islenen_tarih(conn, symbol)
        if son_tarih is not None:
            df_yeni = df_tam[df_tam["price_date"].dt.date > son_tarih].copy()
        else:
            df_yeni = df_tam.copy()

        if df_yeni.empty:
            conn.close()
            return f"{symbol}: Yeni veri yok, atlanıyor."

        # Yöntem seçimi
        if n >= 120:
            anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_4)
            mod = "ECDF 4 seri"
        elif n >= 60:
            anomaliler = _ecdf_anomaliler(df_tam, df_yeni, ZSCORE_60)
            mod = "ECDF 60g"
        else:
            anomaliler = _t_dagilimi_anomaliler(conn, stock_id, df_yeni)
            mod = "t-dağılımı"

        kayitlar = [
            (symbol, tip, float(skor), tarih, "onaylandi", kaynak)
            for tip, skor, tarih, kaynak in anomaliler
        ]

        cur = conn.cursor()
        toplam = _kaydet_toplu(cur, kayitlar)
        conn.commit()
        cur.close()
        conn.close()

        return f"{symbol} [{mod}]: {toplam} yeni anomali, {len(df_yeni)} gün tarandı."

    except Exception as e:
        return f"{symbol}: HATA — {e}"


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4 — ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Minerva Anomali Tespiti Başladı (Kayan ECDF | Incremental)...")
    print("=" * 60)

    hisseler = hisseleri_cek()
    print(f"Toplam {len(hisseler)} hisse taranacak.\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(anomali_tara, sid, sym): sym for sid, sym in hisseler}
        for i, future in enumerate(as_completed(futures), 1):
            sonuc = future.result()
            print(f"[{i}/{len(hisseler)}] {sonuc}")

    print("=" * 60)
    print("Tarama tamamlandı.")
