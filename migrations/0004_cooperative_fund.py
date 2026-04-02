"""
Adds cooperative fund tables, fee tracking, and new system settings.
"""

def up(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cooperative_fund_transactions (
            fund_txn_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_date        TEXT    NOT NULL,
            txn_type        TEXT    NOT NULL,
            category        TEXT    NOT NULL,
            description     TEXT,
            amount          REAL    NOT NULL,
            is_credit       INTEGER NOT NULL DEFAULT 1,
            member_id       TEXT,
            reference_id    TEXT,
            running_balance REAL    NOT NULL DEFAULT 0,
            created_by      TEXT,
            created_date    TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS entrance_fees (
            fee_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       TEXT    NOT NULL,
            amount          REAL    NOT NULL DEFAULT 0,
            is_paid         INTEGER NOT NULL DEFAULT 0,
            due_date        TEXT,
            paid_date       TEXT,
            paid_by         TEXT,
            created_date    TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (member_id) REFERENCES members(member_id)
        );

        CREATE TABLE IF NOT EXISTS loan_fees (
            fee_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id         INTEGER NOT NULL,
            member_id       TEXT    NOT NULL,
            amount          REAL    NOT NULL DEFAULT 0,
            is_paid         INTEGER NOT NULL DEFAULT 0,
            due_date        TEXT,
            paid_date       TEXT,
            paid_by         TEXT,
            created_date    TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (loan_id)    REFERENCES loans(loan_id),
            FOREIGN KEY (member_id)  REFERENCES members(member_id)
        );

        CREATE TABLE IF NOT EXISTS annual_fees (
            fee_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       TEXT    NOT NULL,
            year            INTEGER NOT NULL,
            amount          REAL    NOT NULL DEFAULT 0,
            is_paid         INTEGER NOT NULL DEFAULT 0,
            due_date        TEXT,
            paid_date       TEXT,
            paid_by         TEXT,
            created_date    TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (member_id) REFERENCES members(member_id)
        );

        CREATE TABLE IF NOT EXISTS dividend_payments (
            payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            dividend_id     INTEGER NOT NULL,
            member_id       TEXT    NOT NULL,
            amount          REAL    NOT NULL,
            savings_balance REAL,
            created_date    TEXT
        );
    """)

    # New settings
    new_settings = [
        ('entrance_fee_amount',          '0.00'),
        ('loan_form_fee_amount',         '0.00'),
        ('annual_fee_amount',            '0.00'),
        ('transfer_fee_amount',          '0.00'),
        ('death_benefit_notation',       'Death benefit charge — {member_name}'),
        ('dividend_distribution_method', 'percentage'),
        ('dividend_percentage',          '0.00'),
        ('dividend_fixed_amount',        '0.00'),
    ]
    for key, val in new_settings:
        existing = conn.execute(
            "SELECT 1 FROM system_settings WHERE setting_key=?", (key,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO system_settings (setting_key, setting_value) VALUES (?,?)",
                (key, val)
            )

    # fix dividend_payments if FK points to renamed table
    fk_list = conn.execute('PRAGMA foreign_key_list(dividend_payments)').fetchall()
    broken = any(row[2] == 'legacy_dividend_records' for row in fk_list)
    if broken:
        conn.execute('DROP TABLE IF EXISTS dividend_payments')
        conn.execute(
            'CREATE TABLE dividend_payments ('
            '    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,'
            '    dividend_id INTEGER NOT NULL,'
            '    member_id TEXT NOT NULL,'
            '    amount REAL NOT NULL,'
            '    savings_balance REAL,'
            '    created_date TEXT)'
        )

    # handle dividends table — may already exist with old schema from migrate.py
    existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(dividends)").fetchall()]
    if 'distribution_date' not in existing_cols and existing_cols:
        conn.execute("ALTER TABLE dividends RENAME TO legacy_dividend_records")
    if 'distribution_date' not in existing_cols:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                dividend_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                distribution_date   TEXT    NOT NULL,
                period              TEXT    NOT NULL,
                distribution_method TEXT    NOT NULL,
                total_distributed   REAL    NOT NULL DEFAULT 0,
                members_paid        INTEGER NOT NULL DEFAULT 0,
                created_by          TEXT,
                created_date        TEXT
            )
        """)

    print("  [0004] Cooperative fund tables and settings created")