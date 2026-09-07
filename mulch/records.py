import json
import os
import shutil
import sqlite3
import sys
import threading
from datetime import datetime
from pathlib import Path

_lock = threading.RLock()
_conn = None
_CONFIG = None

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


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _project_root() -> Path:
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _app_user_dir() -> Path:
    if is_frozen():
        return Path(os.path.expanduser("~/.mulch"))
    return _project_root() / "mulch"


def _default_data_dir() -> Path:
    if is_frozen():
        return Path(os.path.expanduser("~/.mulch"))
    return _project_root() / "mulch" / "records"


def _config_path() -> Path:
    return _app_user_dir() / "config.json"


def _load_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        try:
            with open(_config_path(), encoding="utf-8") as f:
                _CONFIG = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _CONFIG = {}
    return _CONFIG


def _save_config() -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_CONFIG, f, indent=2)


def _copy_storage(src: Path, dst: Path) -> None:
    db = src / "mulch.db"
    if db.exists() and not (dst / "mulch.db").exists():
        shutil.copy2(db, dst / "mulch.db")
    cases_src = src / "cases"
    if cases_src.exists() and not (dst / "cases").exists():
        shutil.copytree(cases_src, dst / "cases", dirs_exist_ok=True)


def _resolve_data_dir() -> Path:
    env_dir = os.environ.get("MULCH_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    preferred = _load_config().get("data_dir")
    if preferred:
        return Path(preferred)
    return _default_data_dir()


DATA_DIR = _resolve_data_dir()


def set_data_dir(path: str) -> dict:
    target = Path(os.path.abspath(os.path.expanduser(path.strip())))
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise ValueError("Chosen path is not a directory")
    global DATA_DIR, _conn
    with _lock:
        _copy_storage(DATA_DIR, target)
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        _conn = None
        DATA_DIR = target
    _load_config()["data_dir"] = str(DATA_DIR)
    _save_config()
    return get_settings()


def reset_data_dir() -> dict:
    target = _default_data_dir()
    target.mkdir(parents=True, exist_ok=True)
    global DATA_DIR, _conn
    with _lock:
        _copy_storage(DATA_DIR, target)
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        _conn = None
        DATA_DIR = target
    _load_config().pop("data_dir", None)
    _save_config()
    return get_settings()


def get_settings() -> dict:
    return {
        "data_dir": str(DATA_DIR),
        "default_data_dir": str(_default_data_dir()),
    }


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
        shutil.rmtree(case_dir(case_id), ignore_errors=True)
        return True
    return False