import sqlite3
from pathlib import Path

from app.config import settings
from app.models import Stats

_DB = Path(settings.db_path)


def _get_conn():
    conn = sqlite3.connect(str(_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, timeframe TEXT, price REAL, signal TEXT,
        confidence REAL, confluence REAL, session TEXT,
        tp1 REAL, tp2 REAL, tp3 REAL, tp4 REAL, tp5 REAL, sl REAL,
        resultado TEXT DEFAULT 'PENDIENTE', trailing_sl REAL,
        volatility_ratio REAL, filtered_reason TEXT
    )""")
    conn.commit()
    return conn


def save_signal(sig) -> int:
    conn = _get_conn()
    setup = sig.trade_setup
    conn.execute(
        """INSERT INTO signals (timestamp, timeframe, price, signal, confidence, confluence,
           session, tp1, tp2, tp3, tp4, tp5, sl, resultado, volatility_ratio, filtered_reason)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (sig.timestamp.isoformat(), sig.timeframe, sig.price, sig.signal.value,
         sig.confidence, sig.confluence, sig.session,
         setup.tp1 if setup else None, setup.tp2 if setup else None,
         setup.tp3 if setup else None, setup.tp4 if setup else None,
         setup.tp5 if setup else None, setup.sl if setup else None,
         sig.resultado.value, sig.volatility_ratio, sig.filtered_reason)
    )
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return row_id


def update_result(signal_id: int, resultado: str, trailing_sl: float | None = None):
    conn = _get_conn()
    conn.execute("UPDATE signals SET resultado=?, trailing_sl=? WHERE id=?",
                 (resultado, trailing_sl, signal_id))
    conn.commit()
    conn.close()


def get_stats(timeframe: str | None = None) -> Stats:
    conn = _get_conn()
    where = "WHERE filtered_reason IS NULL"
    params = []
    if timeframe:
        where += " AND timeframe=?"
        params.append(timeframe)

    total = conn.execute(f"SELECT COUNT(*) FROM signals {where}", params).fetchone()[0]
    wins = conn.execute(f"SELECT COUNT(*) FROM signals {where} AND resultado LIKE 'TP%'", params).fetchone()[0]
    losses = conn.execute(f"SELECT COUNT(*) FROM signals {where} AND resultado='SL_ALCANZADO'", params).fetchone()[0]
    pending = conn.execute(f"SELECT COUNT(*) FROM signals {where} AND resultado='PENDIENTE'", params).fetchone()[0]
    avg_conf = conn.execute(f"SELECT AVG(confluence) FROM signals {where} AND resultado LIKE 'TP%'", params).fetchone()[0]
    conn.close()

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    return Stats(
        total_signals=total, wins=wins, losses=losses, pending=pending,
        win_rate=round(win_rate, 1), avg_confluence=round(avg_conf or 0, 4)
    )


def get_history_db(timeframe: str, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT timestamp, signal, price, tp1, sl, resultado, trailing_sl, confluence "
        "FROM signals WHERE timeframe=? AND filtered_reason IS NULL "
        "ORDER BY id DESC LIMIT ?", (timeframe, limit)
    ).fetchall()
    conn.close()
    return [{"timestamp": r[0], "signal": r[1], "price": r[2], "tp1": r[3],
             "sl": r[4], "resultado": r[5], "trailing_sl": r[6], "confluence": r[7]} for r in rows]
