"""
Migrates 102,496 historical transactions from PayOrWithdrawTbl in database.sld
into the transactions table.

AccountID mapping:
  B   = Premium Savings deposit
  B1  = Premium Savings withdrawal
  G   = Target Savings deposit
  G1  = Target Savings withdrawal
  A   = Shares deposit
  A1  = Shares withdrawal
  C   = Major loan disbursement
  D   = Emergency loan disbursement/repayment
  E   = Essentials loan disbursement/repayment
  F   = Purchases loan disbursement/repayment
  H   = Entrance fee
  H1  = Entrance fee refund
"""
import os
import sqlite3

LEGACY_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'database.sld'
)

# AccountID -> (transaction_type, account_type, savings_type_code or None)
ACCOUNT_MAP = {
    'B':  ('Savings Deposit',    'Savings', 'PREMIUM'),
    'B1': ('Savings Withdrawal', 'Savings', 'PREMIUM'),
    'G':  ('Savings Deposit',    'Savings', 'TARGET'),
    'G1': ('Savings Withdrawal', 'Savings', 'TARGET'),
    'A':  ('Savings Deposit',    'Savings', 'SHARES'),
    'A1': ('Savings Withdrawal', 'Savings', 'SHARES'),
    'C':  ('Loan Disbursement',  'Loan',    'MAJOR'),
    'D':  ('Loan Disbursement',  'Loan',    'EMERGENCY'),
    'E':  ('Loan Disbursement',  'Loan',    'ESSENTIALS'),
    'F':  ('Loan Disbursement',  'Loan',    'PURCHASES'),
    'H':  ('Entrance Fee',       'Fee',     None),
    'H1': ('Entrance Fee',       'Fee',     None),
}

# AccountIDs that are always repayments when Credit=No
LOAN_ACCOUNTS = {'C', 'D', 'E', 'F'}


def up(conn: sqlite3.Connection):
    if not os.path.isfile(LEGACY_DB):
        print("  [0003] Legacy DB not found — skipping historical transaction migration")
        return

    legacy = sqlite3.connect(LEGACY_DB)
    legacy.row_factory = sqlite3.Row

    # Build lookup: (member_id, savings_type_code) -> account_id
    savings_lookup = {}
    for r in conn.execute("""
        SELECT sa.account_id, sa.member_id, st.type_code
        FROM savings_accounts sa
        JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
    """).fetchall():
        savings_lookup[(r[1], r[2])] = r[0]

    # Build lookup: member_id -> station_id
    station_lookup = {
        r[0]: r[1]
        for r in conn.execute("SELECT member_id, station_id FROM members").fetchall()
    }

    # Build set of valid member IDs in new DB
    valid_members = set(station_lookup.keys())

    rows = legacy.execute("""
        SELECT SysDate, MemberID, StationID, AccountID,
               Description, Amount, Medium, ChequeNo, RecieptNo, Credit
        FROM PayOrWithdrawTbl
        WHERE Enable='Yes'
        ORDER BY SysDate, MemberID
    """).fetchall()
    legacy.close()

    batch = []
    skipped = 0

    for r in rows:
        member_id  = r['MemberID']
        account_id = r['AccountID']
        credit_str = r['Credit']

        # skip purged members
        if member_id not in valid_members:
            skipped += 1
            continue

        # skip unknown account types
        if account_id not in ACCOUNT_MAP:
            skipped += 1
            continue

        txn_type, acct_type, savings_code = ACCOUNT_MAP[account_id]
        is_credit = (credit_str == 'Yes')

        # for loan accounts, Credit=No means repayment
        if account_id in LOAN_ACCOUNTS and not is_credit:
            txn_type = 'Loan Repayment'

        # resolve account reference
        if savings_code:
            sa_id = savings_lookup.get((member_id, savings_code))
            acct_ref = str(sa_id) if sa_id else f"LEGACY-{savings_code}"
        else:
            acct_ref = f"LEGACY-{account_id}"

        try:
            amount = abs(float(r['Amount'] or 0))
        except (TypeError, ValueError):
            skipped += 1
            continue

        if amount <= 0:
            skipped += 1
            continue

        station_id = station_lookup.get(member_id, r['StationID'])

        batch.append((
            r['SysDate'] or '2010-01-01',
            member_id,
            station_id,
            txn_type,
            acct_type,
            acct_ref,
            r['Description'] or '',
            amount,
            int(is_credit),
            r['Medium'] or 'Cash',
            r['ChequeNo'] or None,
            r['RecieptNo'] or None,
            'migration',
        ))

        # insert in batches of 5000 for performance
        if len(batch) >= 5000:
            conn.executemany("""
                INSERT INTO transactions (
                    transaction_date, member_id, station_id,
                    transaction_type, account_type, account_id,
                    description, amount, is_credit,
                    payment_method, cheque_number, receipt_number, created_by
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, batch)
            batch.clear()

    if batch:
        conn.executemany("""
            INSERT INTO transactions (
                transaction_date, member_id, station_id,
                transaction_type, account_type, account_id,
                description, amount, is_credit,
                payment_method, cheque_number, receipt_number, created_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, batch)

    total = conn.execute("SELECT COUNT(*) FROM transactions WHERE created_by='migration'").fetchone()[0]
    print(f"  [0003] Migrated {total:,} historical transactions ({skipped} skipped)")