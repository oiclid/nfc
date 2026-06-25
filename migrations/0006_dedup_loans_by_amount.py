"""
Remove duplicate loans where a member has multiple loans of the same type
and amount. Keeps only the earliest (lowest loan_id) per
(member_id, loan_type_id, principal_amount) combination.
"""


def up(conn):
    before = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]

    to_delete = conn.execute("""
        SELECT loan_id FROM loans
        WHERE loan_id NOT IN (
            SELECT MIN(loan_id)
            FROM loans
            GROUP BY member_id, loan_type_id, principal_amount
        )
    """).fetchall()

    if not to_delete:
        print("  [0006] No duplicate loans found")
        return

    ids = [r[0] for r in to_delete]
    ph  = ','.join('?' * len(ids))

    conn.execute(f"DELETE FROM loan_repayments WHERE loan_id IN ({ph})", ids)
    conn.execute(f"DELETE FROM loan_fees        WHERE loan_id IN ({ph})", ids)
    conn.execute(f"DELETE FROM loans            WHERE loan_id IN ({ph})", ids)

    after = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    total = conn.execute(
        "SELECT ROUND(SUM(principal_amount),2) FROM loans"
    ).fetchone()[0]
    print(f"  [0006] Removed {before - after} duplicate loans — "
          f"{after} remain — total principal: {total:,.2f}")