def up(conn):
    existing_entrance = conn.execute(
        "SELECT setting_value FROM system_settings WHERE setting_key='entrance_fee_amount'"
    ).fetchone()
    entrance_value = existing_entrance[0] if existing_entrance else '0.00'

    new_settings = [
        ('admission_fee_amount',          entrance_value),
        ('readmission_fee_amount',        '0.00'),
        ('withdrawal_fee_amount',         '0.00'),
        ('death_charge_amount',           '0.00'),
        ('retirement_benefit_fee_amount', '0.00'),
        ('other_income_amount',           '0.00'),
        ('death_benefit_fee_amount',      '0.00'),
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

    conn.execute(
        "UPDATE cooperative_fund_transactions SET category='Admission Fee' WHERE category='Entrance Fee'"
    )

    print("  [0005] Fee settings seeded and fund transaction categories updated")