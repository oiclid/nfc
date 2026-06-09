"""
Remove duplicate loans created by multiple migrate.py runs.
Keeps the lowest loan_id for each (member_id, loan_type_id, principal_amount, start_date).
Also cleans up orphaned loan_repayments and loan_fees.
"""

def up(conn):
    to_delete = conn.execute("""
        SELECT loan_id FROM loans
        WHERE loan_id NOT IN (
            SELECT MIN(loan_id)
            FROM loans
            GROUP BY member_id, loan_type_id, principal_amount, start_date
        )
    """).fetchall()

    if not to_delete:
        print("  [0005] No duplicate loans found")
        return

    ids = [r[0] for r in to_delete]
    ph  = ','.join('?' * len(ids))

    conn.execute(f"DELETE FROM loan_repayments WHERE loan_id IN ({ph})", ids)
    conn.execute(f"DELETE FROM loan_fees       WHERE loan_id IN ({ph})", ids)
    conn.execute(f"DELETE FROM loans           WHERE loan_id IN ({ph})", ids)

    remaining = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    print(f"  [0005] Removed {len(ids)} duplicate loans — {remaining} remain")