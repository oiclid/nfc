"""
Mark all loans where end_date has passed as Defaulted.
Only 90 loans with future end dates remain Active.
No repayment history existed in legacy system — balances are original principals.
"""
from datetime import date


def up(conn):
    today = date.today().isoformat()

    # mark past end-date loans as Defaulted
    conn.execute("""
        UPDATE loans
        SET status = 'Defaulted'
        WHERE status = 'Active'
        AND end_date < ?
        AND end_date IS NOT NULL
        AND end_date != ''
        AND end_date < '2100-01-01'
    """, (today,))

    defaulted = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE status='Defaulted'"
    ).fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE status='Active'"
    ).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE status='Completed'"
    ).fetchone()[0]

    print(f"  [0007] Loans — Active: {active}  Defaulted: {defaulted}  Completed: {completed}")