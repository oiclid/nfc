"""
Purge the 126 members identified for removal and renumber
all remaining member IDs sequentially with no gaps.

The 126 IDs were verified manually against the names spreadsheet
in the initial data review session.
"""
import sqlite3


PURGE_IDS = [
    'NFC0001','NFC0002','NFC0003','NFC0004','NFC0005','NFC0008','NFC0010','NFC0011',
    'NFC0012','NFC0013','NFC0014','NFC0019','NFC0020','NFC0021','NFC0023','NFC0024',
    'NFC0025','NFC0027','NFC0028','NFC0029','NFC0030','NFC0036','NFC0041','NFC0042',
    'NFC0043','NFC0044','NFC0045','NFC0046','NFC0048','NFC0050','NFC0052','NFC0056',
    'NFC0057','NFC0063','NFC0067','NFC0068','NFC0069','NFC0071','NFC0072','NFC0073',
    'NFC0074','NFC0082','NFC0087','NFC0088','NFC0089','NFC0090','NFC0093','NFC0094',
    'NFC0095','NFC0096','NFC0098','NFC0101','NFC0102','NFC0103','NFC0105','NFC0106',
    'NFC0107','NFC0108','NFC0113','NFC0117','NFC0120','NFC0122','NFC0128','NFC0129',
    'NFC0130','NFC0132','NFC0136','NFC0141','NFC0157','NFC0160','NFC0161','NFC0162',
    'NFC0165','NFC0170','NFC0171','NFC0172','NFC0175','NFC0178','NFC0181','NFC0184',
    'NFC0187','NFC0188','NFC0189','NFC0190','NFC0191','NFC0192','NFC0195','NFC0196',
    'NFC0202','NFC0207','NFC0208','NFC0209','NFC0210','NFC0211','NFC0212','NFC0213',
    'NFC0223','NFC0225','NFC0229','NFC0234','NFC0238','NFC0245','NFC0246','NFC0248',
    'NFC0251','NFC0252','NFC0255','NFC0257','NFC0259','NFC0261','NFC0265','NFC0268',
    'NFC0271','NFC0272','NFC0285','NFC0286','NFC0292','NFC0303','NFC0311','NFC0312',
    'NFC0314','NFC0320','NFC0321','NFC0324','NFC0330','NFC0331',
]

CHILD_TABLES = [
    'savings_accounts',
    'loans',
    'loan_repayments',
    'transactions',
    'dividends',
    'death_benefit_charges',
    'withdrawal_benefits',
    'member_transfers',
]


def up(conn: sqlite3.Connection):
    conn.execute("PRAGMA foreign_keys = OFF")

    ph = ','.join('?' * len(PURGE_IDS))

    # Delete loan_repayments linked via loans (not directly by member_id)
    loan_ids = [r[0] for r in conn.execute(
        f"SELECT loan_id FROM loans WHERE member_id IN ({ph})", PURGE_IDS
    ).fetchall()]
    if loan_ids:
        lph = ','.join('?' * len(loan_ids))
        conn.execute(f"DELETE FROM loan_repayments WHERE loan_id IN ({lph})", loan_ids)

    # Delete all child records
    for table in CHILD_TABLES:
        try:
            conn.execute(f"DELETE FROM {table} WHERE member_id IN ({ph})", PURGE_IDS)
        except Exception:
            pass

    # Delete the members
    conn.execute(f"DELETE FROM members WHERE member_id IN ({ph})", PURGE_IDS)

    # Renumber remaining members sequentially
    remaining = conn.execute(
        "SELECT member_id FROM members ORDER BY member_id"
    ).fetchall()

    id_map = {}
    for i, (old_id,) in enumerate(remaining, 1):
        new_id = f"NFC{i:04d}"
        if old_id != new_id:
            id_map[old_id] = new_id

    # Update child tables and members in order
    ref_tables = [
        'savings_accounts', 'loans', 'loan_repayments', 'transactions',
        'dividends', 'death_benefit_charges', 'withdrawal_benefits',
        'member_transfers',
    ]
    for old_id, new_id in id_map.items():
        for table in ref_tables:
            try:
                conn.execute(
                    f"UPDATE {table} SET member_id=? WHERE member_id=?",
                    (new_id, old_id)
                )
            except Exception:
                pass
        conn.execute(
            "UPDATE members SET member_id=?, registration_number=? WHERE member_id=?",
            (new_id, new_id, old_id)
        )

    # Update next_member_number
    new_count = len(remaining)
    conn.execute(
        "UPDATE system_settings SET setting_value=? WHERE setting_key='next_member_number'",
        (str(new_count + 1),)
    )

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()