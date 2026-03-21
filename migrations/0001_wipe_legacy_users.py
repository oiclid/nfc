"""
Wipe all legacy user accounts so the first-launch wizard
creates a fresh admin. Dependent tables are cleared first.
"""
import sqlite3


def up(conn: sqlite3.Connection):
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in ("user_shortcuts", "undo_stack", "dashboard_exports",
                  "audit_log", "activity_log"):
        try:
            conn.execute(f"DELETE FROM {table}")
        except Exception:
            pass
    conn.execute("DELETE FROM users")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()