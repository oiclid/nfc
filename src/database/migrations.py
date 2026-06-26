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


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _pending(migrations_dir: str, applied: List[str], conn: sqlite3.Connection) -> List[str]:
    if not os.path.isdir(migrations_dir):
        return []
    files = sorted(
        f for f in os.listdir(migrations_dir)
        if f.endswith('.py') and f[0].isdigit()
    )
    # Migrations marked as applied but whose sentinel table doesn't exist
    # were pre-marked by migrate.py without actually being run (e.g. 0004).
    # Force-re-queue them so the tables get created.
    SENTINEL_TABLES = {
        '0002_purge_members.py':      'members',        # check via row count instead
        '0004_cooperative_fund.py':   'cooperative_fund_transactions',
    }
    force_rerun = []
    for f in files:
        if f not in applied or f not in SENTINEL_TABLES:
            continue
        sentinel = SENTINEL_TABLES[f]
        if f == '0002_purge_members.py':
            # Re-run if any of the purge IDs still exist in members
            purge_sample = ('NFC0001', 'NFC0002', 'NFC0003')
            still_there = conn.execute(
                "SELECT 1 FROM members WHERE member_id IN (?,?,?) LIMIT 1",
                purge_sample
            ).fetchone()
            if still_there:
                force_rerun.append(f)
        elif not _table_exists(conn, sentinel):
            force_rerun.append(f)
    pending = [f for f in files if f not in applied]
    # Preserve order: force-rerun first (they're already in applied order), then new ones
    combined = force_rerun + [f for f in pending if f not in force_rerun]
    return combined


def run(db_path: str, migrations_dir: str) -> List[str]:
    """
    Run all pending migrations. Returns names applied this session.
    Raises RuntimeError on failure — caller should abort app startup.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)

    applied  = _applied(conn)
    pending  = _pending(migrations_dir, applied, conn)
    ran: List[str] = []

    for filename in pending:
        filepath = os.path.join(migrations_dir, filename)
        spec     = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module   = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            module.up(conn)
            conn.execute("INSERT OR IGNORE INTO migrations (name) VALUES (?)", (filename,))
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