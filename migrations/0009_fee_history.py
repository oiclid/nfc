"""
Create fee_history table to track all fee setting changes.
Records old value, new value, who changed it, and when — never retroactive.
"""


def up(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fee_history (
            history_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            fee_key       TEXT    NOT NULL,
            fee_label     TEXT    NOT NULL,
            old_value     REAL    NOT NULL DEFAULT 0,
            new_value     REAL    NOT NULL DEFAULT 0,
            changed_by    TEXT    NOT NULL,
            changed_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            note          TEXT
        )
    """)
    print("  [0009] fee_history table created")