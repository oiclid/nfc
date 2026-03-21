"""
Auto-migration runner — called by main.py on every launch.
Discovers *.py migration files in migrations/ ordered by filename,
tracks applied ones in the migrations table, runs pending ones.
"""
import os
import importlib.util
import sqlite3
import traceback
from typing import List


def _ensure_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _applied(conn: sqlite3.Connection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM migrations ORDER BY id"
    ).fetchall()]


def _pending(migrations_dir: str, applied: List[str]) -> List[str]:
    if not os.path.isdir(migrations_dir):
        return []
    files = sorted(
        f for f in os.listdir(migrations_dir)
        if f.endswith('.py') and f[0].isdigit()
    )
    return [f for f in files if f not in applied]


def run(db_path: str, migrations_dir: str) -> List[str]:
    """
    Run all pending migrations. Returns names applied this session.
    Raises RuntimeError on failure — caller should abort app startup.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)

    applied  = _applied(conn)
    pending  = _pending(migrations_dir, applied)
    ran: List[str] = []

    for filename in pending:
        filepath = os.path.join(migrations_dir, filename)
        spec     = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module   = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            module.up(conn)
            conn.execute("INSERT INTO migrations (name) VALUES (?)", (filename,))
            conn.commit()
            ran.append(filename)
        except Exception:
            conn.rollback()
            conn.close()
            raise RuntimeError(
                f"Migration '{filename}' failed:\n{traceback.format_exc()}"
            )

    conn.close()
    return ran