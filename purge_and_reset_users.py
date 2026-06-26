import os
import sys
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'nfc_cooperative.db')


def confirm(prompt: str) -> bool:
    ans = input(f"{prompt} [yes/no]: ").strip().lower()
    return ans == 'yes'


def main():
    if not os.path.isfile(DB_PATH):
        print(f"ERROR: database not found at {DB_PATH}")
        sys.exit(1)

    print("=" * 60)
    print("  NFC Cooperative — User Purge & Reset")
    print("=" * 60)
    print()
    print("This will permanently delete ALL user accounts and clear")
    print("all logs. The app will show the setup wizard on next launch.")
    print()

    if not confirm("Are you sure you want to continue?"):
        print("Aborted.")
        sys.exit(0)

    if not confirm("FINAL CHECK — this cannot be undone. Proceed?"):
        print("Aborted.")
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = OFF")

        tables_to_clear = [
            'user_shortcuts',
            'undo_stack',
            'dashboard_exports',
            'audit_log',
            'activity_log',
            'users',
        ]

        print()
        for table in tables_to_clear:
            try:
                before = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                conn.execute(f"DELETE FROM {table}")
                print(f"  Cleared {table:<22} ({before} rows removed)")
            except sqlite3.OperationalError:
                print(f"  Skipped {table:<22} (table not found)")

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

        remaining = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print()
        print(f"Done. Users remaining: {remaining}")
        print()
        print("Run `python main.py` — the setup wizard will appear.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        print("No changes were committed.")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()