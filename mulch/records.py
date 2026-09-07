import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("MULCH_DATA_DIR", os.path.expanduser("~/.mulch")))

_lock = threading.RLock()
_conn = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    case_id             TEXT PRIMARY KEY,
    patient_name        TEXT NOT NULL DEFAULT '',
    patient_mrn         TEXT NOT NULL DEFAULT '',
    patient_sex         TEXT NOT NULL DEFAULT '',
    scan_date           TEXT NOT NULL DEFAULT '',
    diagnosis           TEXT NOT NULL,
    confidence          REAL,
    probability_normal  REAL,
    probability_pneumonia  REAL,
    confidence_level    TEXT,
    interpretation      TEXT,
    model_label         TEXT,
    model_key           TEXT,
    latency_ms          INTEGER,
    reported_at         TEXT,
    image_path          TEXT,
    overlay_path        TEXT,
    heatmap_path        TEXT
);
"""


def _connect() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(str(DATA_DIR / "mulch.db"), check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute(_SCHEMA)
            _conn.commit()
        return _conn


def case_dir(case_id: str) -> Path:
    return DATA_DIR / "cases" / case_id


def ensure_case_dir(case_id: str) -> Path:
    d = case_dir(case_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_record(case_id: str, fields: dict) -> dict:
    case_dir(case_id).mkdir(parents=True, exist_ok=True)
    fields.setdefault("reported_at", datetime.now().isoformat(timespec="seconds"))
    cols = [
        "case_id", "patient_name", "patient_mrn", "patient_sex", "scan_date",
        "diagnosis", "confidence", "probability_normal", "probability_pneumonia",
        "confidence_level", "interpretation", "model_label", "model_key",
        "latency_ms", "reported_at", "image_path", "overlay_path", "heatmap_path",
    ]
    values = [fields.get(c) for c in cols]
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    with _lock:
        conn = _connect()
        conn.execute(
            f"INSERT INTO records ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT(case_id) DO UPDATE SET {updates}",
            values,
        )
        conn.commit()
    return get_record(case_id)


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    rec = {k: row[k] for k in row.keys()}
    for key in ("confidence", "probability_normal", "probability_pneumonia"):
        if rec.get(key) is not None:
            rec[key] = round(float(rec[key]), 4)
    return rec


def get_record(case_id: str) -> dict | None:
    with _lock:
        row = _connect().execute(
            "SELECT * FROM records WHERE case_id = ?", (case_id,)
        ).fetchone()
    return _row_to_dict(row)


def list_records(limit: int = 200) -> list[dict]:
    with _lock:
        rows = _connect().execute(
            "SELECT * FROM records ORDER BY reported_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def delete_record(case_id: str) -> bool:
    with _lock:
        cur = _connect().execute("DELETE FROM records WHERE case_id = ?", (case_id,))
        _connect().commit()
    if cur.rowcount:
        import shutil

        shutil.rmtree(case_dir(case_id), ignore_errors=True)
        return True
    return False