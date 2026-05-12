import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

_conn = None


def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = _yeni_baglanti()
    else:
        try:
            cur = _conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        except Exception:
            _conn = _yeni_baglanti()
    return _conn


def _clean(v): return v.replace(chr(0xFEFF), "").strip()

def _yeni_baglanti():
    return psycopg2.connect(
        host=_clean(os.environ["EXT_DB_HOST"]),
        port=int(_clean(os.environ["EXT_DB_PORT"])),
        database=_clean(os.environ["EXT_DB_NAME"]),
        user=_clean(os.environ["EXT_DB_USER"]),
        password=_clean(os.environ["EXT_DB_PASSWORD"]),
    )
