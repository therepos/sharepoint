"""SQLite layer — connection, schema init, basic CRUD helpers."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from app.config import DB_PATH


SCHEMA_DIR = Path(__file__).parent / "schema"


@contextmanager
def get_conn():
    """Context-managed SQLite connection with FK enforcement."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Run all SQL files in app/schema/ in lexical order. Idempotent (uses IF NOT EXISTS)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        for sql_file in sorted(SCHEMA_DIR.glob("*.sql")):
            sql = sql_file.read_text()
            conn.executescript(sql)


# ---------------------------------------------------------------------------
# Read helpers — return pandas DataFrames for easy display
# ---------------------------------------------------------------------------
def fetch_df(query: str, params: tuple = ()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params)


def fetch_one(query: str, params: tuple = ()) -> dict | None:
    with get_conn() as conn:
        cur = conn.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------
def execute(query: str, params: tuple = ()):
    with get_conn() as conn:
        conn.execute(query, params)


def execute_many(query: str, rows: list[tuple]):
    with get_conn() as conn:
        conn.executemany(query, rows)


def insert(table: str, data: dict) -> int:
    """Insert a single row. Returns lastrowid."""
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    with get_conn() as conn:
        cur = conn.execute(query, tuple(data.values()))
        return cur.lastrowid


def update(table: str, pk_col: str, pk_val, data: dict):
    set_clause = ", ".join(f"{k} = ?" for k in data.keys())
    query = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?"
    with get_conn() as conn:
        conn.execute(query, tuple(data.values()) + (pk_val,))


def delete(table: str, pk_col: str, pk_val):
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {table} WHERE {pk_col} = ?", (pk_val,))


def next_id(table: str, prefix: str, pk_col: str) -> str:
    """Generate next ID like P001, PRJ027 by scanning existing IDs."""
    rows = fetch_all(f"SELECT {pk_col} FROM {table} WHERE {pk_col} LIKE ?", (f"{prefix}%",))
    nums = []
    for r in rows:
        rid = r[pk_col]
        try:
            nums.append(int(rid[len(prefix):]))
        except (ValueError, TypeError):
            continue
    next_num = (max(nums) + 1) if nums else 1
    width = 3
    return f"{prefix}{next_num:0{width}d}"
