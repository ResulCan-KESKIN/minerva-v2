"""
BIST hisselerinin dolaşımdaki lot miktarını çeker ve stocks.dolasim_lot günceller.

Yöntem (öncelik sırasıyla):
  1. Yahoo Finance fast_info / info → sharesOutstanding (BIST için 1 lot = 1 TL nominal)
  2. İş Yatırım şirket kartı HTML → JSON embed paidCapital parse

Çalıştırma:
  python isyatirim_fetch.py            # sadece NULL/0 olanları doldur
  python isyatirim_fetch.py --tum      # tüm hisseleri yeniden çek
  python isyatirim_fetch.py --test THYAO GARAN   # test modu (DB'ye yazmaz)
"""

import re
import time
import logging
import argparse
import requests
import pandas as pd
from db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# İş Yatırım şirket kartı (HTML embed parse)
_IY_CARD = (
    "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/"
    "sirket-karti.aspx?hisse={symbol}"
)

# JSON içinde ödenmiş sermaye için denenen anahtar desenleri
_IY_PATTERNS = [
    r'"paidCapital"\s*:\s*([\d.]+)',
    r'"odenmisSermaye"\s*:\s*([\d.]+)',
    r'"PaidCapital"\s*:\s*([\d.]+)',
    r'"PAID_CAPITAL"\s*:\s*([\d.]+)',
    r'"odenmis_sermaye"\s*:\s*([\d.]+)',
    # HTML tablo satırı formatı
    r'[Öö]denmi[sş]\s+[Ss]ermaye[^<]*<[^>]+>\s*([\d.,]+)',
]


# ───────────────────────────────────────────
# KAYNAK 1 — Yahoo Finance
# ───────────────────────────────────────────

def _yfinance_lot(symbol: str) -> float | None:
    try:
        import yfinance as yf
        t = yf.Ticker(f"{symbol}.IS")

        # fast_info (daha hızlı, yfinance ≥ 0.2)
        try:
            fi = t.fast_info
            # fast_info bir nesne; attribute erişimi
            val = getattr(fi, "shares", None)
            if val and float(val) > 0:
                log.debug(f"  {symbol}: fast_info.shares={val:.0f}")
                return float(val)
        except Exception:
            pass

        # info (yavaş ama kapsamlı)
        info = t.info
        for key in ("sharesOutstanding", "impliedSharesOutstanding", "floatShares"):
            v = info.get(key)
            if v and float(v) > 0:
                log.debug(f"  {symbol}: info[{key}]={v:.0f}")
                return float(v)

    except Exception as e:
        log.debug(f"  {symbol} yfinance hata: {e}")
    return None


# ───────────────────────────────────────────
# KAYNAK 2 — İş Yatırım HTML embed
# ───────────────────────────────────────────

def _isyatirim_lot(symbol: str) -> float | None:
    try:
        url = _IY_CARD.format(symbol=symbol)
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        text = r.text

        for pattern in _IY_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                raw = m.group(1).strip().replace(".", "").replace(",", ".")
                try:
                    val = float(raw)
                    if val > 0:
                        log.debug(f"  {symbol}: isyatirim embed={val:.0f}")
                        return val
                except ValueError:
                    continue
    except Exception as e:
        log.debug(f"  {symbol} isyatirim hata: {e}")
    return None


# ───────────────────────────────────────────
# BİRLEŞİK ÇEKME
# ───────────────────────────────────────────

def lot_cek(symbol: str) -> float | None:
    lot = _yfinance_lot(symbol)
    if lot is None:
        lot = _isyatirim_lot(symbol)
    return lot


# ───────────────────────────────────────────
# DB GÜNCELLEME
# ───────────────────────────────────────────

def tumunu_guncelle(sadece_bos: bool = True, kuru_calistir: bool = False):
    """
    sadece_bos=True  → dolasim_lot NULL veya 0 olan hisseleri güncelle
    sadece_bos=False → tüm aktif hisseleri yeniden çek
    kuru_calistir    → DB'ye yazma, sadece logla
    """
    conn = get_conn()

    where = "WHERE is_active = true"
    if sadece_bos:
        where += " AND (dolasim_lot IS NULL OR dolasim_lot = 0)"

    hisseler = pd.read_sql(
        f"SELECT id, symbol FROM stocks {where} ORDER BY symbol", conn
    )
    log.info(f"{len(hisseler)} hisse taranacak (sadece_bos={sadece_bos})")

    cur = conn.cursor()
    guncellenen = 0
    basarisiz = []

    for i, (_, row) in enumerate(hisseler.iterrows(), 1):
        symbol   = row["symbol"]
        stock_id = row["id"]

        lot = lot_cek(symbol)
        prefix = f"[{i}/{len(hisseler)}] {symbol}"

        if lot and lot > 0:
            if not kuru_calistir:
                cur.execute(
                    "UPDATE stocks SET dolasim_lot = %s WHERE id = %s",
                    (lot, stock_id),
                )
            log.info(f"{prefix}: {lot:>18,.0f} lot")
            guncellenen += 1
        else:
            log.warning(f"{prefix}: VERİ ALINAMADI")
            basarisiz.append(symbol)

        if i % 20 == 0 and not kuru_calistir:
            conn.commit()  # ara commit
        time.sleep(0.5)   # rate-limit

    if not kuru_calistir:
        conn.commit()
    cur.close()

    log.info("=" * 60)
    log.info(f"Tamamlandı → {guncellenen} güncellendi, {len(basarisiz)} başarısız")
    if basarisiz:
        log.info(f"Başarısız: {', '.join(basarisiz)}")


# ───────────────────────────────────────────
# TEST MODU
# ───────────────────────────────────────────

def test_semboller(semboller: list[str]):
    """Birkaç sembol için veriyi çek, DB'ye yazma."""
    log.info("TEST MODU — DB'ye yazılmıyor")
    for sym in semboller:
        lot = lot_cek(sym)
        if lot:
            log.info(f"  {sym}: {lot:,.0f} lot")
        else:
            log.warning(f"  {sym}: veri alınamadı")


# ───────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="BIST dolaşım lot güncelleme")
    ap.add_argument("--tum",  action="store_true", help="Tüm hisseleri yeniden çek")
    ap.add_argument("--test", nargs="+", metavar="SEMBOL",
                    help="Sadece bu sembolleri test et (DB'ye yazmaz)")
    args = ap.parse_args()

    if args.test:
        test_semboller(args.test)
    else:
        tumunu_guncelle(sadece_bos=not args.tum)
