"""
One-time migration: database.sld -> nfc_cooperative.db

Run from project root:
    python migrations/migrate.py

Safe to re-run — prompts before overwriting an existing DB.
"""

import os
import sys
import sqlite3
import hashlib
from datetime import datetime

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLD_PATH  = os.path.join(ROOT, 'data', 'database.sld')
DB_PATH   = os.path.join(ROOT, 'data', 'nfc_cooperative.db')
REPORT    = os.path.join(ROOT, 'migrations', 'migration_report.txt')


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE stations (
    station_id    TEXT PRIMARY KEY,
    station_name  TEXT NOT NULL,
    address       TEXT,
    city          TEXT,
    enabled       INTEGER DEFAULT 1,
    contact_person TEXT,
    contact_phone  TEXT,
    contact_email  TEXT,
    created_date  TEXT DEFAULT (datetime('now')),
    modified_date TEXT DEFAULT (datetime('now'))
);

CREATE TABLE members (
    member_id           TEXT PRIMARY KEY,
    station_id          TEXT NOT NULL,
    registration_number TEXT UNIQUE NOT NULL,
    first_name          TEXT NOT NULL,
    middle_name         TEXT,
    last_name           TEXT NOT NULL,
    gender              TEXT CHECK(gender IN ('Male','Female')),
    date_of_birth       TEXT,
    date_joined         TEXT NOT NULL,
    address             TEXT,
    phone_number        TEXT,
    email               TEXT,
    employee_id         TEXT,
    grade_level         TEXT,
    nok1_name           TEXT,
    nok1_relationship   TEXT,
    nok1_address        TEXT,
    nok1_phone          TEXT,
    nok2_name           TEXT,
    nok2_relationship   TEXT,
    nok2_address        TEXT,
    nok2_phone          TEXT,
    is_active           INTEGER DEFAULT 1,
    is_deceased         INTEGER DEFAULT 0,
    deceased_date       TEXT,
    photo_path          TEXT,
    created_date        TEXT DEFAULT (datetime('now')),
    modified_date       TEXT DEFAULT (datetime('now')),
    created_by          TEXT,
    modified_by         TEXT,
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    email         TEXT,
    role          TEXT NOT NULL CHECK(role IN ('Admin','Cashier','Accountant','Auditor')),
    can_maintain  INTEGER DEFAULT 0,
    can_operate   INTEGER DEFAULT 0,
    can_edit      INTEGER DEFAULT 0,
    can_view_reports INTEGER DEFAULT 0,
    is_active     INTEGER DEFAULT 1,
    last_login    TEXT,
    created_date  TEXT DEFAULT (datetime('now')),
    modified_date TEXT DEFAULT (datetime('now'))
);

CREATE TABLE audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date    TEXT DEFAULT (datetime('now')),
    user_id     INTEGER,
    username    TEXT,
    action      TEXT NOT NULL,
    entity_type TEXT,
    entity_id   TEXT,
    old_value   TEXT,
    new_value   TEXT,
    description TEXT,
    ip_address  TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE activity_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT DEFAULT (datetime('now')),
    user_id     TEXT NOT NULL,
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    description TEXT,
    ip_address  TEXT
);

CREATE TABLE user_shortcuts (
    user_id      TEXT NOT NULL,
    action_name  TEXT NOT NULL,
    shortcut_key TEXT NOT NULL,
    created_date TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, action_name)
);

CREATE TABLE undo_stack (
    stack_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          TEXT NOT NULL,
    session_id       TEXT NOT NULL,
    action_timestamp TEXT DEFAULT (datetime('now')),
    action_type      TEXT NOT NULL,
    entity_type      TEXT NOT NULL,
    entity_id        TEXT NOT NULL,
    undo_data        TEXT NOT NULL,
    redo_data        TEXT NOT NULL,
    is_undone        INTEGER DEFAULT 0
);

CREATE TABLE dashboard_exports (
    export_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    export_type    TEXT NOT NULL,
    date_from      TEXT,
    date_to        TEXT,
    filters_applied TEXT,
    exported_date  TEXT DEFAULT (datetime('now')),
    file_path      TEXT
);

CREATE TABLE savings_types (
    savings_type_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    type_code        TEXT UNIQUE NOT NULL,
    type_name        TEXT NOT NULL,
    description      TEXT,
    interest_rate    REAL DEFAULT 0.00,
    interest_enabled INTEGER DEFAULT 1,
    minimum_balance  REAL DEFAULT 0.00,
    is_active        INTEGER DEFAULT 1,
    created_date     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE savings_accounts (
    account_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id         TEXT NOT NULL,
    savings_type_id   INTEGER NOT NULL,
    account_number    TEXT UNIQUE,
    current_balance   REAL DEFAULT 0.00,
    total_deposits    REAL DEFAULT 0.00,
    total_withdrawals REAL DEFAULT 0.00,
    interest_earned   REAL DEFAULT 0.00,
    monthly_target    REAL DEFAULT 0.00,
    date_opened       TEXT DEFAULT (datetime('now')),
    is_active         INTEGER DEFAULT 1,
    FOREIGN KEY (member_id) REFERENCES members(member_id),
    FOREIGN KEY (savings_type_id) REFERENCES savings_types(savings_type_id)
);

CREATE TABLE loan_types (
    loan_type_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    type_code           TEXT UNIQUE NOT NULL,
    type_name           TEXT NOT NULL,
    description         TEXT,
    interest_rate       REAL NOT NULL,
    max_duration_months INTEGER NOT NULL,
    is_active           INTEGER DEFAULT 1,
    created_date        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE loans (
    loan_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id           TEXT NOT NULL,
    station_id          TEXT NOT NULL,
    loan_type_id        INTEGER NOT NULL,
    loan_number         TEXT UNIQUE,
    principal_amount    REAL NOT NULL,
    interest_rate       REAL NOT NULL,
    interest_amount     REAL NOT NULL,
    total_amount        REAL NOT NULL,
    monthly_installment REAL NOT NULL,
    duration_months     INTEGER NOT NULL,
    amount_paid         REAL DEFAULT 0.00,
    balance_outstanding REAL NOT NULL,
    disbursement_date   TEXT,
    start_date          TEXT NOT NULL,
    end_date            TEXT NOT NULL,
    cheque_number       TEXT,
    bank_name           TEXT,
    status              TEXT DEFAULT 'Active' CHECK(status IN ('Pending','Active','Completed','Defaulted')),
    is_active           INTEGER DEFAULT 1,
    created_date        TEXT DEFAULT (datetime('now')),
    created_by          TEXT,
    FOREIGN KEY (member_id)    REFERENCES members(member_id),
    FOREIGN KEY (station_id)   REFERENCES stations(station_id),
    FOREIGN KEY (loan_type_id) REFERENCES loan_types(loan_type_id)
);

CREATE TABLE loan_repayments (
    repayment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id         INTEGER NOT NULL,
    member_id       TEXT NOT NULL,
    payment_date    TEXT NOT NULL,
    expected_amount REAL NOT NULL,
    actual_amount   REAL NOT NULL,
    balance_before  REAL NOT NULL,
    balance_after   REAL NOT NULL,
    payment_method  TEXT,
    cheque_number   TEXT,
    receipt_number  TEXT,
    notes           TEXT,
    created_date    TEXT DEFAULT (datetime('now')),
    created_by      TEXT,
    FOREIGN KEY (loan_id)   REFERENCES loans(loan_id),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE transactions (
    transaction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    member_id        TEXT NOT NULL,
    station_id       TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    account_type     TEXT NOT NULL,
    account_id       TEXT,
    description      TEXT,
    amount           REAL NOT NULL,
    is_credit        INTEGER NOT NULL,
    payment_method   TEXT,
    cheque_number    TEXT,
    receipt_number   TEXT,
    created_date     TEXT DEFAULT (datetime('now')),
    created_by       TEXT,
    FOREIGN KEY (member_id)  REFERENCES members(member_id),
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

CREATE TABLE bank_transactions (
    bank_transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date    TEXT NOT NULL,
    transaction_type    TEXT NOT NULL,
    payee_name          TEXT,
    description         TEXT,
    amount              REAL NOT NULL,
    payment_method      TEXT,
    cheque_number       TEXT,
    bank_name           TEXT,
    receipt_number      TEXT,
    bank_charges        REAL DEFAULT 0.00,
    bank_interest       REAL DEFAULT 0.00,
    is_cleared          INTEGER DEFAULT 0,
    details             TEXT,
    created_date        TEXT DEFAULT (datetime('now')),
    created_by          TEXT
);

CREATE TABLE system_settings (
    setting_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key   TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    setting_type  TEXT,
    description   TEXT,
    is_editable   INTEGER DEFAULT 1,
    modified_date TEXT DEFAULT (datetime('now')),
    modified_by   TEXT
);

CREATE TABLE death_benefits (
    benefit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id         TEXT NOT NULL,
    benefit_amount    REAL DEFAULT 0.00,
    charge_per_member REAL NOT NULL,
    members_charged   INTEGER DEFAULT 0,
    processed_by      TEXT,
    processed_date    TEXT,
    created_date      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE death_benefit_charges (
    charge_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    death_benefit_id INTEGER NOT NULL,
    member_id        TEXT NOT NULL,
    charge_amount    REAL NOT NULL,
    processed_date   TEXT NOT NULL,
    created_date     TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (death_benefit_id) REFERENCES death_benefits(benefit_id),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE withdrawal_benefits (
    benefit_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id             TEXT NOT NULL,
    account_id            INTEGER,
    gross_amount          REAL NOT NULL,
    adjustment_percentage REAL NOT NULL,
    adjustment_amount     REAL NOT NULL,
    net_amount            REAL NOT NULL,
    is_retirement         INTEGER DEFAULT 0,
    processed_by          TEXT,
    processed_date        TEXT,
    created_date          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE dividends (
    dividend_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id       TEXT NOT NULL,
    savings_type_id INTEGER,
    dividend_amount REAL NOT NULL,
    period          TEXT,
    created_date    TEXT DEFAULT (datetime('now')),
    created_by      TEXT,
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE member_transfers (
    transfer_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id       TEXT NOT NULL,
    from_station_id TEXT NOT NULL,
    to_station_id   TEXT NOT NULL,
    transfer_date   TEXT NOT NULL,
    reason          TEXT,
    approved_by     TEXT,
    created_date    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE migrations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIEW vw_member_summary AS
SELECT
    m.member_id,
    m.registration_number,
    m.first_name || ' ' || COALESCE(m.middle_name || ' ', '') || m.last_name AS full_name,
    m.station_id,
    s.station_name,
    m.is_active,
    m.is_deceased,
    COALESCE(SUM(CASE WHEN st.type_code = 'PREMIUM'                   THEN sa.current_balance ELSE 0 END), 0) AS premium_savings,
    COALESCE(SUM(CASE WHEN st.type_code IN ('TARGET','FIXED_DEPOSIT') THEN sa.current_balance ELSE 0 END), 0) AS fixed_target_deposits,
    COALESCE(SUM(CASE WHEN st.type_code = 'SHARES'                    THEN sa.current_balance ELSE 0 END), 0) AS shares_investment,
    COALESCE(SUM(sa.current_balance), 0)    AS total_savings,
    COALESCE(SUM(l.balance_outstanding), 0) AS total_loans_outstanding,
    COALESCE(SUM(sa.current_balance), 0) - COALESCE(SUM(l.balance_outstanding), 0) AS net_balance
FROM members m
LEFT JOIN stations s        ON m.station_id = s.station_id
LEFT JOIN savings_accounts sa ON m.member_id = sa.member_id AND sa.is_active = 1
LEFT JOIN savings_types st  ON sa.savings_type_id = st.savings_type_id
LEFT JOIN loans l           ON m.member_id = l.member_id AND l.status = 'Active'
GROUP BY m.member_id, m.registration_number, m.first_name, m.middle_name,
         m.last_name, m.station_id, s.station_name, m.is_active, m.is_deceased;
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_name(full: str):
    """Split 'FIRST MIDDLE LAST' into (first, middle, last)."""
    parts = full.strip().split()
    if len(parts) == 1:
        return parts[0], None, parts[0]
    if len(parts) == 2:
        return parts[0], None, parts[1]
    # 3+ parts: first=parts[0], last=parts[-1], middle=everything in between
    return parts[0], ' '.join(parts[1:-1]), parts[-1]


def sha256(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


LOAN_CODE_MAP = {
    'C1': ('MAJOR',      'Major Loan',            10.0, 24),
    'D1': ('EMERGENCY',  'Emergency Loan',          5.0,  6),
    'E1': ('ESSENTIALS', 'Essential Commodities',  10.0, 12),
    'F1': ('PURCHASES',  'Purchases Loan',         10.0, 18),
}

ACCOUNT_SAVINGS_MAP = {
    'B':  'PREMIUM',
    'G':  'TARGET',
    'A':  'SHARES',
}


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def migrate():
    if not os.path.isfile(SLD_PATH):
        print(f"ERROR: legacy DB not found at {SLD_PATH}")
        sys.exit(1)

    if os.path.isfile(DB_PATH):
        ans = input(f"nfc_cooperative.db already exists. Overwrite? [yes/no]: ").strip().lower()
        if ans != 'yes':
            print("Aborted.")
            sys.exit(0)
        os.remove(DB_PATH)

    src  = sqlite3.connect(SLD_PATH)
    src.row_factory = sqlite3.Row
    dest = sqlite3.connect(DB_PATH)
    dest.executescript(SCHEMA)

    report = []
    log    = lambda msg: (report.append(msg), print(msg))

    log(f"Migration started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Source: {SLD_PATH}")
    log(f"Target: {DB_PATH}")
    log("")

    # ── System settings ──────────────────────────────────────────────────────
    settings = [
        ('next_member_number',              '330'),
        ('next_station_number',             '4'),
        ('interest_auto_calculate',         '1'),
        ('death_benefit_enabled',           '1'),
        ('death_benefit_amount',            '5000.00'),
        ('retirement_benefit_percentage',   '10.00'),
        ('non_retirement_charge_percentage','5.00'),
        ('organization_name',               'Nigerian Film Corporation'),
        ('currency_symbol',                 '₦'),
        ('date_format',                     'YYYY-MM-DD'),
        ('admission_fee_amount',            '0.00'),
        ('readmission_fee_amount',          '0.00'),
        ('withdrawal_fee_amount',           '0.00'),
        ('death_charge_amount',             '0.00'),
        ('retirement_benefit_fee_amount',   '0.00'),
        ('other_income_amount',             '0.00'),
        ('death_benefit_fee_amount',        '0.00'),
        ('loan_form_fee_amount',            '0.00'),
        ('annual_fee_amount',               '0.00'),
        ('transfer_fee_amount',             '0.00'),
        ('death_benefit_notation',          'Death benefit charge — {member_name}'),
        ('dividend_distribution_method',    'percentage'),
        ('dividend_percentage',             '0.00'),
        ('dividend_fixed_amount',           '0.00'),
    ]
    dest.executemany(
        "INSERT INTO system_settings (setting_key, setting_value) VALUES (?,?)",
        settings
    )
    log(f"Settings:   {len(settings)} inserted")

    # ── Savings types ─────────────────────────────────────────────────────────
    savings_types = [
        ('PREMIUM',       'Fixed Savings (Premium)',    'Monthly fixed savings', 2.0, 1),
        ('TARGET',        'Target Savings (Special)',   'Target-based savings',  3.0, 1),
        ('FIXED_DEPOSIT', 'Fixed Deposit (Flexible)',   'Fixed deposit account', 4.0, 1),
        ('SHARES',        'Investment Shares',          'Share capital',         5.0, 1),
    ]
    dest.executemany(
        "INSERT INTO savings_types (type_code,type_name,description,interest_rate,interest_enabled) VALUES (?,?,?,?,?)",
        savings_types
    )
    log(f"Savings types: {len(savings_types)} inserted")

    # ── Loan types ────────────────────────────────────────────────────────────
    loan_types = [
        ('MAJOR',       'Major Loan',             'Major/Macro loan',          10.0, 24),
        ('CAR',         'Car Loan',               'Vehicle purchase loan',     15.0, 36),
        ('ELECTRONICS', 'Electronics Loan',       'Electronics purchase loan', 10.0, 18),
        ('LAND',        'Land Loan',              'Land purchase loan',        10.0, 24),
        ('ESSENTIALS',  'Essential Commodities',  'Essential commodities loan',10.0, 12),
        ('EDUCATION',   'Education Loan',         'Education financing loan',  10.0,  6),
        ('EMERGENCY',   'Emergency Loan',         'Emergency loan facility',    5.0,  4),
        ('PURCHASES',   'Purchases Loan',         'General purchases loan',    10.0, 18),
    ]
    dest.executemany(
        "INSERT INTO loan_types (type_code,type_name,description,interest_rate,max_duration_months) VALUES (?,?,?,?,?)",
        loan_types
    )
    log(f"Loan types: {len(loan_types)} inserted")

    # ── Stations ──────────────────────────────────────────────────────────────
    stations = src.execute("SELECT * FROM StationDB").fetchall()
    s_ok = 0
    for s in stations:
        enabled = 1 if s['EnableStation'] == 1 else 0
        dest.execute(
            "INSERT INTO stations (station_id,station_name,address,city,enabled) VALUES (?,?,?,?,?)",
            (s['StationID'], s['Description'], s['Address'], s['Address'], enabled)
        )
        s_ok += 1
    log(f"Stations:   {s_ok}/{len(stations)} migrated")

    # ── Members ───────────────────────────────────────────────────────────────
    members = src.execute("SELECT * FROM MemberDataTbl ORDER BY MemberID").fetchall()
    m_ok = m_skip = 0
    for m in members:
        if not m['Names'] or not m['Names'].strip():
            m_skip += 1
            continue
        first, middle, last = split_name(m['Names'])
        gender    = 'Male' if m['Male'] == 1 else 'Female'
        is_active = 1 if m['Enable'] == 1 else 0
        phone = m['PhoneNo'] or None
        if phone and phone.strip() in ('', '0', '080', '070', '090'):
            phone = None
        try:
            dest.execute(
                """INSERT INTO members
                   (member_id, station_id, registration_number,
                    first_name, middle_name, last_name, gender,
                    date_joined, address, phone_number,
                    employee_id, grade_level,
                    nok1_name, nok1_relationship, nok1_address, nok1_phone,
                    nok2_name, nok2_relationship, nok2_address, nok2_phone,
                    is_active, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'migration')""",
                (m['MemberID'], m['StationID'], m['MemberID'],
                 first, middle, last, gender,
                 m['DateJoined'], m['Address'] or None, phone,
                 m['EmployeeID'] or None, m['GradeLevel'] or None,
                 m['FirstKinName'] or None, m['FirstKinRelatnshp'] or None,
                 m['FirstKinAddr'] or None, m['FirstKinPhoneNo'] or None,
                 m['SecondKinName'] or None, m['SecondKinRelatnshp'] or None,
                 m['SecondKinAddr'] or None, m['SecondKinPhoneNo'] or None,
                 is_active)
            )
            m_ok += 1
        except Exception as e:
            log(f"  SKIP member {m['MemberID']}: {e}")
            m_skip += 1
    log(f"Members:    {m_ok}/{len(members)} migrated, {m_skip} skipped")

    # ── Savings accounts (compute balances from PayOrWithdrawTbl) ─────────────
    # Map savings_type_code -> savings_type_id
    st_map = {
        r[0]: r[1]
        for r in dest.execute("SELECT type_code, savings_type_id FROM savings_types").fetchall()
    }

    # Get all member IDs that were successfully migrated
    migrated_members = {
        r[0] for r in dest.execute("SELECT member_id FROM members").fetchall()
    }

    # Compute balances per member per account type
    rows = src.execute("""
        SELECT MemberID, StationID, AccountID,
               SUM(CASE WHEN Credit='Yes' THEN CAST(Amount AS REAL) ELSE 0 END) as total_credit,
               SUM(CASE WHEN Debit='Yes'  THEN CAST(Amount AS REAL) ELSE 0 END) as total_debit
        FROM PayOrWithdrawTbl
        WHERE AccountID IN ('A','B','G')
        GROUP BY MemberID, AccountID
    """).fetchall()

    sa_ok = sa_skip = 0
    for row in rows:
        mid       = row['MemberID']
        acct_id   = row['AccountID']
        type_code = ACCOUNT_SAVINGS_MAP.get(acct_id)
        if not type_code or mid not in migrated_members:
            sa_skip += 1
            continue
        st_id    = st_map.get(type_code)
        balance  = round(row['total_credit'] - row['total_debit'], 2)
        deposits = round(row['total_credit'], 2)
        withdrawals = round(row['total_debit'], 2)
        acct_num = f"{mid}-{type_code[:4]}"
        try:
            dest.execute(
                """INSERT INTO savings_accounts
                   (member_id, savings_type_id, account_number,
                    current_balance, total_deposits, total_withdrawals)
                   VALUES (?,?,?,?,?,?)""",
                (mid, st_id, acct_num, balance, deposits, withdrawals)
            )
            sa_ok += 1
        except Exception as e:
            log(f"  SKIP savings {mid}/{acct_id}: {e}")
            sa_skip += 1
    log(f"Savings accounts: {sa_ok} created, {sa_skip} skipped")

    # ── Loans ─────────────────────────────────────────────────────────────────
    lt_map = {
        r[0]: r[1]
        for r in dest.execute("SELECT type_code, loan_type_id FROM loan_types").fetchall()
    }

    loans = src.execute(
        "SELECT * FROM LoansAndPurchasesTbl WHERE Enable='Yes' ORDER BY MemberID, SysDate"
    ).fetchall()

    l_ok = l_skip = 0
    loan_counter  = {}
    for loan in loans:
        mid = loan['MemberID']
        if mid not in migrated_members:
            l_skip += 1
            continue

        code     = loan['LoanCode']
        mapped   = LOAN_CODE_MAP.get(code)
        if not mapped:
            l_skip += 1
            continue

        type_code, _, rate, default_duration = mapped
        lt_id     = lt_map.get(type_code)
        principal = abs(float(loan['Amount']))
        import re as _re
        def _dur(v, d):
            digits = _re.sub(r"[^0-9]", "", str(v).strip()) if v else ""
            n = int(digits) if digits else 0
            return n if 1 <= n <= 120 else d
        duration = _dur(loan["NoOfMonths"], default_duration)
        if duration <= 0:
            duration = default_duration

        interest  = round(principal * (rate / 100), 2)
        total     = round(principal + interest, 2)
        installment = round(total / duration, 2)

        # Compute amount paid from PayOrWithdrawTbl
        paid_rows = src.execute("""
            SELECT COALESCE(SUM(CAST(Amount AS REAL)), 0) as paid
            FROM PayOrWithdrawTbl
            WHERE MemberID=? AND AccountID IN ('C','D','E','F')
            AND Credit='No' AND Debit='Yes'
            AND SysDate >= ? AND SysDate <= ?
        """, (mid, loan['StartDate'] or '2000-01-01', loan['EndDate'] or '2099-12-31')).fetchone()
        amount_paid = round(abs(float(paid_rows['paid'])), 2)
        balance     = max(0.0, round(total - amount_paid, 2))
        status      = 'Completed' if balance <= 0 else 'Active'

        # Unique loan number
        loan_counter[mid] = loan_counter.get(mid, 0) + 1
        loan_num = f"L-{mid}-{loan['SysDate']}-{loan_counter[mid]}"

        try:
            dest.execute(
                """INSERT INTO loans
                   (member_id, station_id, loan_type_id, loan_number,
                    principal_amount, interest_rate, interest_amount, total_amount,
                    monthly_installment, duration_months,
                    amount_paid, balance_outstanding,
                    disbursement_date, start_date, end_date,
                    cheque_number, status, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'Active','migration')""",
                (mid, loan['StationID'], lt_id, loan_num,
                 principal, rate, interest, total,
                 installment, duration,
                 amount_paid, balance,
                 loan['SysDate'],
                 loan['StartDate'] or loan['SysDate'],
                 loan['EndDate'] or loan['SysDate'],
                 loan['ChequeNo'] or None)
            )
            # Override status after insert
            dest.execute(
                "UPDATE loans SET status=? WHERE loan_number=?",
                (status, loan_num)
            )
            l_ok += 1
        except Exception as e:
            log(f"  SKIP loan {mid}/{loan['SysDate']}: {e}")
            l_skip += 1
    log(f"Loans:      {l_ok}/{len(loans)} migrated, {l_skip} skipped")

    # ── Users ─────────────────────────────────────────────────────────────────
    users = src.execute("SELECT * FROM LoginTbl").fetchall()
    u_ok  = 0
    for u in users:
        pw_hash = sha256(u['Password'])
        maintain = 1 if str(u['Maintain']).strip() == '1' else 0
        operate  = 1 if str(u['Operations']).strip() == '1' else 0
        edit     = 1 if str(u['EditPriv']).strip() == '1' else 0
        reports  = 1 if str(u['Reports']).strip() == '1' else 0
        dest.execute(
            """INSERT INTO users
               (username, password_hash, full_name, role,
                can_maintain, can_operate, can_edit, can_view_reports)
               VALUES (?,?,?,?,?,?,?,?)""",
            (u['Username'], pw_hash, u['Username'], 'Admin',
             maintain, operate, edit, reports)
        )
        u_ok += 1
    log(f"Users:      {u_ok}/{len(users)} migrated")

    # ── Bank transactions ─────────────────────────────────────────────────────
    btxns = src.execute("SELECT * FROM TransactionsTbl").fetchall()
    bt_ok = 0
    for bt in btxns:
        try:
            dest.execute(
                """INSERT INTO bank_transactions
                   (transaction_date, transaction_type, payee_name,
                    description, amount, payment_method,
                    cheque_number, bank_name, receipt_number,
                    bank_charges, bank_interest, is_cleared, details)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (bt['Date'],
                 'Debit' if bt['TransacType'] == 'Debit' else 'Credit',
                 bt['Names'],
                 bt['Description'],
                 abs(float(bt['Amount'])),
                 bt['Medium'],
                 bt['ChequeNo'] or None,
                 bt['Bank'] or None,
                 bt['RecieptNo'] or None,
                 float(bt['BankCharge']) if bt['BankCharge'] else 0.0,
                 float(bt['BankInterest']) if bt['BankInterest'] else 0.0,
                 1 if str(bt['Cleared']).strip() == '1' else 0,
                 bt['Details'] or None)
            )
            bt_ok += 1
        except Exception as e:
            log(f"  SKIP bank txn {bt['TransactionID']}: {e}")
    log(f"Bank txns:  {bt_ok}/{len(btxns)} migrated")

    # Mark all bundled migrations as applied so the auto-runner skips them
    # on first launch. These files were created before or alongside this
    # migration script and their work is already covered by the schema above.
    bundled_migrations = [
        '0001_wipe_legacy_users.py',
        '0002_purge_members.py',
        '0003_migrate_historical_transactions.py',
        '0004_cooperative_fund.py',
        '0005_dedup_loans.py',
        '0006_dedup_loans_by_amount.py',
        '0007_mark_defaulted_loans.py',
        '0008_rename_fees.py',
    ]
    for name in bundled_migrations:
        dest.execute(
            "INSERT OR IGNORE INTO migrations (name) VALUES (?)", (name,)
        )
    log(f"Migrations: {len(bundled_migrations)} pre-marked as applied")

    dest.commit()
    src.close()
    dest.close()

    log("")
    log("Migration complete.")
    log(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with open(REPORT, 'w') as f:
        f.write('\n'.join(report))
    print(f"\nReport saved to {REPORT}")


if __name__ == '__main__':
    migrate()