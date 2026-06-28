import sqlite3
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, List, Dict, Any


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    def _connect(self):
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")

    @contextmanager
    def transaction(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(query, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        row = self._conn.execute(query, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        return [dict(r) for r in self._conn.execute(query, params).fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # -------------------------------------------------------------------------
    # Authentication & Users
    # -------------------------------------------------------------------------

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        user = self.fetchone(
            "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
            (username, pw_hash)
        )
        if user:
            self.execute(
                "UPDATE users SET last_login=? WHERE user_id=?",
                (datetime.now().isoformat(), user['user_id'])
            )
            self.commit()
        return user

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        return self.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))

    def get_all_users(self) -> List[Dict]:
        return self.fetchall("SELECT * FROM users ORDER BY username")

    def create_user(self, data: Dict, created_by: str) -> int:
        pw_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        cursor = self.execute(
            """INSERT INTO users
               (username, password_hash, full_name, email, role,
                can_maintain, can_operate, can_edit, can_view_reports)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (data['username'], pw_hash, data.get('full_name', ''),
             data.get('email', ''), data['role'],
             int(data.get('can_maintain', 0)),
             int(data.get('can_operate', 0)),
             int(data.get('can_edit', 0)),
             int(data.get('can_view_reports', 0)))
        )
        self.commit()
        return cursor.lastrowid

    def update_user(self, user_id: int, data: Dict, modified_by: str):
        self.execute(
            """UPDATE users SET full_name=?, email=?, role=?,
               can_maintain=?, can_operate=?, can_edit=?, can_view_reports=?,
               modified_date=? WHERE user_id=?""",
            (data.get('full_name', ''), data.get('email', ''), data['role'],
             int(data.get('can_maintain', 0)),
             int(data.get('can_operate', 0)),
             int(data.get('can_edit', 0)),
             int(data.get('can_view_reports', 0)),
             datetime.now().isoformat(), user_id)
        )
        self.commit()

    def change_password(self, user_id: int, new_password: str):
        pw_hash = hashlib.sha256(new_password.encode()).hexdigest()
        self.execute(
            "UPDATE users SET password_hash=?, modified_date=? WHERE user_id=?",
            (pw_hash, datetime.now().isoformat(), user_id)
        )
        self.commit()

    def deactivate_user(self, user_id: int, modified_by: str):
        self.execute(
            "UPDATE users SET is_active=0, modified_date=? WHERE user_id=?",
            (datetime.now().isoformat(), user_id)
        )
        self.commit()

    # -------------------------------------------------------------------------
    # Stations
    # -------------------------------------------------------------------------

    def get_all_stations(self, enabled_only: bool = True) -> List[Dict]:
        q = "SELECT * FROM stations"
        if enabled_only:
            q += " WHERE enabled=1"
        return self.fetchall(q + " ORDER BY station_id")

    def get_station(self, station_id: str) -> Optional[Dict]:
        return self.fetchone("SELECT * FROM stations WHERE station_id=?", (station_id,))

    def add_station(self, city: str, address: str = "") -> str:
        next_num = int(self.get_setting('next_station_number'))
        station_id = f"{next_num:02d}"
        self.execute(
            "INSERT INTO stations (station_id,station_name,address,city,enabled) VALUES (?,?,?,?,1)",
            (station_id, f"NFC - {city}", address or city, city)
        )
        self.update_setting('next_station_number', str(next_num + 1))
        self.commit()
        return station_id

    def update_station(self, station_id: str, data: Dict, modified_by: str):
        self.execute(
            """UPDATE stations SET station_name=?, address=?, city=?,
               contact_person=?, contact_phone=?, contact_email=?, modified_date=?
               WHERE station_id=?""",
            (data.get('station_name'), data.get('address'), data.get('city'),
             data.get('contact_person'), data.get('contact_phone'),
             data.get('contact_email'), datetime.now().isoformat(), station_id)
        )
        self.commit()

    def toggle_station(self, station_id: str, enabled: bool):
        self.execute(
            "UPDATE stations SET enabled=? WHERE station_id=?",
            (int(enabled), station_id)
        )
        self.commit()

    # -------------------------------------------------------------------------
    # Members
    # -------------------------------------------------------------------------

    def get_all_members(self, active_only: bool = True) -> List[Dict]:
        q = "SELECT * FROM members"
        if active_only:
            q += " WHERE is_active=1 AND is_deceased=0"
        return self.fetchall(q + " ORDER BY member_id")

    def get_member(self, member_id: str) -> Optional[Dict]:
        return self.fetchone("SELECT * FROM members WHERE member_id=?", (member_id,))

    def search_members(self, search_term: str) -> List[Dict]:
        term = f"%{search_term}%"
        return self.fetchall(
            """SELECT * FROM members
               WHERE member_id LIKE ? OR first_name LIKE ? OR middle_name LIKE ?
                  OR last_name LIKE ?
                  OR (first_name || ' ' || COALESCE(middle_name,'') || ' ' || last_name) LIKE ?
               ORDER BY member_id""",
            (term, term, term, term, term)
        )

    def add_member(self, data: Dict, created_by: str) -> str:
        next_num = self.get_next_member_number()
        member_id = f"NFC{next_num:04d}"
        self.execute(
            """INSERT INTO members (
                member_id, station_id, registration_number,
                first_name, middle_name, last_name, gender,
                date_of_birth, date_joined, address, phone_number, email,
                employee_id, grade_level,
                nok1_name, nok1_relationship, nok1_address, nok1_phone,
                nok2_name, nok2_relationship, nok2_address, nok2_phone,
                created_by
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (member_id, data['station_id'], member_id,
             data['first_name'], data.get('middle_name'), data['last_name'],
             data['gender'], data.get('date_of_birth'), data['date_joined'],
             data.get('address'), data.get('phone_number'), data.get('email'),
             data.get('employee_id'), data.get('grade_level'),
             data.get('nok1_name'), data.get('nok1_relationship'),
             data.get('nok1_address'), data.get('nok1_phone'),
             data.get('nok2_name'), data.get('nok2_relationship'),
             data.get('nok2_address'), data.get('nok2_phone'),
             created_by)
        )
        self.update_setting('next_member_number', str(next_num + 1))
        self.charge_admission_fee(member_id, created_by)
        self.commit()
        return member_id

    def update_member(self, member_id: str, data: Dict, modified_by: str):
        self.execute(
            """UPDATE members SET
                station_id=?, first_name=?, middle_name=?, last_name=?,
                gender=?, date_of_birth=?, address=?, phone_number=?,
                email=?, employee_id=?, grade_level=?,
                nok1_name=?, nok1_relationship=?, nok1_address=?, nok1_phone=?,
                nok2_name=?, nok2_relationship=?, nok2_address=?, nok2_phone=?,
                modified_by=?, modified_date=?
               WHERE member_id=?""",
            (data['station_id'], data['first_name'], data.get('middle_name'),
             data['last_name'], data['gender'], data.get('date_of_birth'),
             data.get('address'), data.get('phone_number'), data.get('email'),
             data.get('employee_id'), data.get('grade_level'),
             data.get('nok1_name'), data.get('nok1_relationship'),
             data.get('nok1_address'), data.get('nok1_phone'),
             data.get('nok2_name'), data.get('nok2_relationship'),
             data.get('nok2_address'), data.get('nok2_phone'),
             modified_by, datetime.now().isoformat(), member_id)
        )
        self.commit()

    def deactivate_member(self, member_id: str, modified_by: str):
        self.execute(
            "UPDATE members SET is_active=0, modified_by=?, modified_date=? WHERE member_id=?",
            (modified_by, datetime.now().isoformat(), member_id)
        )
        self.commit()

    def reactivate_member(self, member_id: str, modified_by: str):
        self.execute(
            "UPDATE members SET is_active=1, modified_by=?, modified_date=? WHERE member_id=?",
            (modified_by, datetime.now().isoformat(), member_id)
        )
        self.charge_readmission_fee(member_id, modified_by)
        self.commit()

    def mark_member_deceased(self, member_id: str, deceased_date: str, modified_by: str):
        self.execute(
            """UPDATE members SET is_deceased=1, is_active=0,
               deceased_date=?, modified_by=?, modified_date=? WHERE member_id=?""",
            (deceased_date, modified_by, datetime.now().isoformat(), member_id)
        )
        self.commit()

    def get_member_summary(self, member_id: Optional[str] = None) -> List[Dict]:
        q = "SELECT * FROM vw_member_summary"
        if member_id:
            return self.fetchall(q + " WHERE member_id=?", (member_id,))
        return self.fetchall(q)

    # -------------------------------------------------------------------------
    # Savings
    # -------------------------------------------------------------------------

    def get_savings_types(self) -> List[Dict]:
        return self.fetchall("SELECT * FROM savings_types WHERE is_active=1")

    def get_member_savings_accounts(self, member_id: str) -> List[Dict]:
        return self.fetchall(
            """SELECT sa.*, st.type_name, st.type_code, st.interest_rate
               FROM savings_accounts sa
               JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
               WHERE sa.member_id=? AND sa.is_active=1""",
            (member_id,)
        )

    def get_savings_account(self, account_id: int) -> Optional[Dict]:
        return self.fetchone(
            "SELECT * FROM savings_accounts WHERE account_id=?", (account_id,)
        )

    def create_savings_account(self, member_id: str, savings_type_id: int) -> int:
        stype = self.fetchone(
            "SELECT type_code FROM savings_types WHERE savings_type_id=?",
            (savings_type_id,)
        )
        base   = f"{member_id}-{stype['type_code'][:4].upper()}"
        # ensure uniqueness — account may already exist from migration
        existing = self.fetchone(
            "SELECT account_number FROM savings_accounts WHERE account_number=?", (base,)
        )
        account_number = base if not existing else f"{base}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor = self.execute(
            "INSERT INTO savings_accounts (member_id,savings_type_id,account_number) VALUES (?,?,?)",
            (member_id, savings_type_id, account_number)
        )
        self.commit()
        return cursor.lastrowid

    def deposit_to_savings(self, account_id: int, amount: float,
                           txn_data: Dict, created_by: str):
        account = self.fetchone(
            "SELECT member_id FROM savings_accounts WHERE account_id=?", (account_id,)
        )
        if not account:
            raise ValueError("Savings account not found")
        with self.transaction():
            self.execute(
                """UPDATE savings_accounts
                   SET current_balance=current_balance+?,
                       total_deposits=total_deposits+?
                   WHERE account_id=?""",
                (amount, amount, account_id)
            )
            self._record_transaction(
                member_id=account['member_id'],
                transaction_type="Savings Deposit",
                account_type="Savings",
                account_id=str(account_id),
                amount=amount,
                is_credit=True,
                txn_data=txn_data,
                created_by=created_by
            )

    def withdraw_from_savings(self, account_id: int, amount: float,
                              txn_data: Dict, created_by: str):
        account = self.fetchone(
            "SELECT member_id, current_balance FROM savings_accounts WHERE account_id=?",
            (account_id,)
        )
        if not account:
            raise ValueError("Savings account not found")
        if account['current_balance'] < amount:
            raise ValueError("Insufficient balance")
        with self.transaction():
            self.execute(
                """UPDATE savings_accounts
                   SET current_balance=current_balance-?,
                       total_withdrawals=total_withdrawals+?
                   WHERE account_id=?""",
                (amount, amount, account_id)
            )
            self._record_transaction(
                member_id=account['member_id'],
                transaction_type="Savings Withdrawal",
                account_type="Savings",
                account_id=str(account_id),
                amount=amount,
                is_credit=False,
                txn_data=txn_data,
                created_by=created_by
            )

    def calculate_monthly_interest(self, account_id: int) -> float:
        row = self.fetchone(
            """SELECT sa.current_balance, st.interest_rate, st.interest_enabled
               FROM savings_accounts sa
               JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
               WHERE sa.account_id=? AND sa.is_active=1""",
            (account_id,)
        )
        if not row or not row['interest_enabled']:
            return 0.0
        return round(row['current_balance'] * (row['interest_rate'] / 100), 2)

    def apply_monthly_interest_all(self, created_by: str) -> int:
        accounts = self.fetchall(
            """SELECT sa.account_id, sa.member_id, sa.current_balance,
                      st.interest_rate, st.interest_enabled
               FROM savings_accounts sa
               JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
               WHERE sa.is_active=1 AND st.interest_enabled=1"""
        )
        applied = 0
        with self.transaction():
            for acct in accounts:
                interest = round(acct['current_balance'] * (acct['interest_rate'] / 100), 2)
                if interest <= 0:
                    continue
                self.execute(
                    """UPDATE savings_accounts
                       SET current_balance=current_balance+?,
                           interest_earned=interest_earned+?
                       WHERE account_id=?""",
                    (interest, interest, acct['account_id'])
                )
                self._record_transaction(
                    member_id=acct['member_id'],
                    transaction_type="Interest Credit",
                    account_type="Savings",
                    account_id=str(acct['account_id']),
                    amount=interest,
                    is_credit=True,
                    txn_data={'description': 'Monthly interest credit'},
                    created_by=created_by
                )
                applied += 1
        return applied

    # -------------------------------------------------------------------------
    # Loans
    # -------------------------------------------------------------------------

    def get_loan_types(self) -> List[Dict]:
        return self.fetchall("SELECT * FROM loan_types WHERE is_active=1")

    def get_member_loans(self, member_id: str, active_only: bool = True) -> List[Dict]:
        q = """SELECT l.*, lt.type_name, lt.type_code
               FROM loans l
               JOIN loan_types lt ON l.loan_type_id=lt.loan_type_id
               WHERE l.member_id=?"""
        if active_only:
            q += " AND l.status='Active'"
        return self.fetchall(q + " ORDER BY l.created_date DESC", (member_id,))

    def get_loan(self, loan_id: int) -> Optional[Dict]:
        return self.fetchone("SELECT * FROM loans WHERE loan_id=?", (loan_id,))

    def get_all_loans(self, active_only: bool = False) -> List[Dict]:
        q = """SELECT l.*, lt.type_name, lt.type_code,
                      m.first_name, m.last_name
               FROM loans l
               JOIN loan_types lt ON l.loan_type_id=lt.loan_type_id
               JOIN members m ON l.member_id=m.member_id"""
        if active_only:
            q += " WHERE l.status='Active'"
        return self.fetchall(q + " ORDER BY l.created_date DESC")

    def disburse_loan(self, data: Dict, created_by: str) -> int:
        principal   = data['principal_amount']
        rate        = data['interest_rate']
        duration    = data['duration_months']
        interest    = round(principal * (rate / 100), 2)
        total       = principal + interest
        installment = round(total / duration, 2)
        loan_number = f"L-{data['member_id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        with self.transaction():
            cursor = self.execute(
                """INSERT INTO loans (
                    member_id, station_id, loan_type_id, loan_number,
                    principal_amount, interest_rate, interest_amount, total_amount,
                    monthly_installment, duration_months, balance_outstanding,
                    disbursement_date, start_date, end_date,
                    cheque_number, bank_name, status, created_by
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'Active',?)""",
                (data['member_id'], data['station_id'], data['loan_type_id'],
                 loan_number, principal, rate, interest, total,
                 installment, duration, total,
                 data.get('disbursement_date', date.today().isoformat()),
                 data['start_date'], data['end_date'],
                 data.get('cheque_number'), data.get('bank_name'),
                 created_by)
            )
            loan_id = cursor.lastrowid
            self._record_transaction(
                member_id=data['member_id'],
                transaction_type="Loan Disbursement",
                account_type="Loan",
                account_id=str(loan_id),
                amount=principal,
                is_credit=True,
                txn_data={
                    'description': f"Loan Disbursement - {loan_number}",
                    'cheque_number': data.get('cheque_number'),
                    'payment_method': data.get('payment_method', 'Cheque')
                },
                created_by=created_by
            )
        self.charge_loan_form_fee(loan_id, data['member_id'], created_by)
        return loan_id

    def record_loan_repayment(self, loan_id: int, amount: float,
                              payment_data: Dict, created_by: str):
        loan = self.fetchone("SELECT * FROM loans WHERE loan_id=?", (loan_id,))
        if not loan:
            raise ValueError("Loan not found")

        balance_before = loan['balance_outstanding']
        balance_after  = max(0.0, balance_before - amount)
        new_status     = 'Completed' if balance_after <= 0 else 'Active'

        with self.transaction():
            self.execute(
                """INSERT INTO loan_repayments (
                    loan_id, member_id, payment_date,
                    expected_amount, actual_amount, balance_before, balance_after,
                    payment_method, cheque_number, receipt_number, notes, created_by
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (loan_id, loan['member_id'],
                 payment_data.get('payment_date', date.today().isoformat()),
                 loan['monthly_installment'], amount,
                 balance_before, balance_after,
                 payment_data.get('payment_method'),
                 payment_data.get('cheque_number'),
                 payment_data.get('receipt_number'),
                 payment_data.get('notes'),
                 created_by)
            )
            self.execute(
                """UPDATE loans SET amount_paid=?, balance_outstanding=?, status=?
                   WHERE loan_id=?""",
                (loan['amount_paid'] + amount, balance_after, new_status, loan_id)
            )
            self._record_transaction(
                member_id=loan['member_id'],
                transaction_type="Loan Repayment",
                account_type="Loan",
                account_id=str(loan_id),
                amount=amount,
                is_credit=False,
                txn_data=payment_data,
                created_by=created_by
            )

    def get_loan_repayments(self, loan_id: int) -> List[Dict]:
        return self.fetchall(
            "SELECT * FROM loan_repayments WHERE loan_id=? ORDER BY payment_date DESC",
            (loan_id,)
        )

    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------

    def _record_transaction(self, member_id: str, transaction_type: str,
                            account_type: str, account_id: str,
                            amount: float, is_credit: bool,
                            txn_data: Dict, created_by: str):
        member = self.get_member(member_id)
        self.execute(
            """INSERT INTO transactions (
                transaction_date, member_id, station_id,
                transaction_type, account_type, account_id,
                description, amount, is_credit,
                payment_method, cheque_number, receipt_number, created_by
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (txn_data.get('transaction_date', date.today().isoformat()),
             member_id, member['station_id'] if member else None,
             transaction_type, account_type, account_id,
             txn_data.get('description', ''),
             amount, int(is_credit),
             txn_data.get('payment_method'),
             txn_data.get('cheque_number'),
             txn_data.get('receipt_number'),
             created_by)
        )

    def record_transaction(self, member_id, transaction_type, account_type,
                           account_id, amount, is_credit, transaction_data, created_by):
        self._record_transaction(member_id, transaction_type, account_type,
                                 account_id, amount, is_credit, transaction_data, created_by)
        self.commit()

    def get_transactions(self, member_id: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict]:
        q = "SELECT * FROM transactions WHERE 1=1"
        params: list = []
        if member_id:
            q += " AND member_id=?"; params.append(member_id)
        if start_date:
            q += " AND transaction_date>=?"; params.append(start_date)
        if end_date:
            q += " AND transaction_date<=?"; params.append(end_date)
        return self.fetchall(
            q + " ORDER BY transaction_date DESC, transaction_id DESC",
            tuple(params)
        )

    # -------------------------------------------------------------------------
    # Withdrawal Benefits
    # -------------------------------------------------------------------------

    def record_withdrawal_benefit(self, member_id: str, account_id: int,
                                  gross_amount: float, is_retirement: bool,
                                  created_by: str) -> float:
        key        = ('retirement_benefit_percentage' if is_retirement
                      else 'non_retirement_charge_percentage')
        pct        = float(self.get_setting(key) or 0)
        adjustment = round(gross_amount * (pct / 100), 2)
        net        = gross_amount + adjustment if is_retirement else gross_amount - adjustment

        with self.transaction():
            self.execute(
                """INSERT INTO withdrawal_benefits
                   (member_id, account_id, gross_amount, adjustment_percentage,
                    adjustment_amount, net_amount, is_retirement,
                    processed_by, processed_date)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (member_id, account_id, gross_amount, pct,
                 adjustment, net, int(is_retirement),
                 created_by, date.today().isoformat())
            )
            self.withdraw_from_savings(
                account_id, gross_amount,
                {'description': 'Withdrawal benefit', 'payment_method': 'Cash'},
                created_by
            )
        return net

    # -------------------------------------------------------------------------
    # Dividends
    # -------------------------------------------------------------------------

    def record_dividend(self, member_id: str, savings_type_id: int,
                        amount: float, period: str, created_by: str) -> int:
        with self.transaction():
            cursor = self.execute(
                """INSERT INTO dividends
                   (member_id, savings_type_id, dividend_amount, period, created_by)
                   VALUES (?,?,?,?,?)""",
                (member_id, savings_type_id, amount, period, created_by)
            )
        return cursor.lastrowid

    def get_dividends(self, member_id: Optional[str] = None,
                      period: Optional[str] = None) -> List[Dict]:
        q = "SELECT * FROM dividends WHERE 1=1"
        params: list = []
        if member_id:
            q += " AND member_id=?"; params.append(member_id)
        if period:
            q += " AND period=?"; params.append(period)
        return self.fetchall(q + " ORDER BY created_date DESC", tuple(params))

    # -------------------------------------------------------------------------
    # System Settings
    # -------------------------------------------------------------------------

    def get_setting(self, key: str) -> Optional[str]:
        row = self.fetchone(
            "SELECT setting_value FROM system_settings WHERE setting_key=?", (key,)
        )
        return row['setting_value'] if row else None

    def update_setting(self, key: str, value: str,
                       modified_by: Optional[str] = None):
        existing = self.fetchone(
            "SELECT 1 FROM system_settings WHERE setting_key=?", (key,)
        )
        if existing:
            self.execute(
                "UPDATE system_settings SET setting_value=?, modified_by=? WHERE setting_key=?",
                (value, modified_by, key)
            )
        else:
            self.execute(
                "INSERT INTO system_settings (setting_key,setting_value,modified_by) VALUES (?,?,?)",
                (key, value, modified_by)
            )
        self.commit()

    def get_next_member_number(self) -> int:
        return int(self.get_setting('next_member_number') or 1)

    def get_all_settings(self) -> List[Dict]:
        return self.fetchall("SELECT * FROM system_settings ORDER BY setting_key")

    def record_fee_change(self, fee_key: str, fee_label: str,
                          old_value: float, new_value: float,
                          changed_by: str, note: str = None):
        self.execute(
            """INSERT INTO fee_history
               (fee_key, fee_label, old_value, new_value, changed_by, note)
               VALUES (?,?,?,?,?,?)""",
            (fee_key, fee_label, old_value, new_value, changed_by, note)
        )
        self.commit()

    def get_fee_history(self, fee_key: str = None) -> List[Dict]:
        if fee_key:
            return self.fetchall(
                "SELECT * FROM fee_history WHERE fee_key=? ORDER BY changed_at DESC",
                (fee_key,)
            )
        return self.fetchall(
            "SELECT * FROM fee_history ORDER BY changed_at DESC"
        )

    # -------------------------------------------------------------------------
    # Cooperative Fund
    # -------------------------------------------------------------------------

    def get_fund_balance(self) -> float:
        row = self.fetchone(
            "SELECT COALESCE(SUM(CASE WHEN is_credit=1 THEN amount ELSE -amount END),0) as bal FROM cooperative_fund_transactions"
        )
        return round(float(row['bal']), 2) if row else 0.0

    def get_fund_transactions(self, limit: int = None) -> List[Dict]:
        q = "SELECT * FROM cooperative_fund_transactions ORDER BY txn_date DESC, fund_txn_id DESC"
        if limit:
            q += f" LIMIT {limit}"
        return self.fetchall(q)

    def _credit_fund(self, amount: float, category: str, description: str,
                     member_id: str = None, reference_id: str = None,
                     txn_date: str = None, created_by: str = 'system'):
        from datetime import date
        balance = self.get_fund_balance() + amount
        self.execute(
            """INSERT INTO cooperative_fund_transactions
               (txn_date, txn_type, category, description, amount, is_credit,
                member_id, reference_id, running_balance, created_by)
               VALUES (?,?,?,?,?,1,?,?,?,?)""",
            (txn_date or date.today().isoformat(),
             'Credit', category, description, amount,
             member_id, reference_id, balance, created_by)
        )

    def _debit_fund(self, amount: float, category: str, description: str,
                    member_id: str = None, reference_id: str = None,
                    txn_date: str = None, created_by: str = 'system'):
        from datetime import date
        balance = self.get_fund_balance() - amount
        self.execute(
            """INSERT INTO cooperative_fund_transactions
               (txn_date, txn_type, category, description, amount, is_credit,
                member_id, reference_id, running_balance, created_by)
               VALUES (?,?,?,?,?,0,?,?,?,?)""",
            (txn_date or date.today().isoformat(),
             'Debit', category, description, amount,
             member_id, reference_id, balance, created_by)
        )

    def manual_fund_entry(self, amount: float, is_credit: bool,
                          category: str, description: str,
                          created_by: str):
        with self.transaction():
            if is_credit:
                self._credit_fund(amount, category, description, created_by=created_by)
            else:
                self._debit_fund(amount, category, description, created_by=created_by)

    # -------------------------------------------------------------------------
    # Admission Fees
    # -------------------------------------------------------------------------

    def charge_admission_fee(self, member_id: str, created_by: str):
        amount = float(self.get_setting('admission_fee_amount') or 0)
        from datetime import date
        self.execute(
            """INSERT INTO entrance_fees (member_id, amount, is_paid, due_date)
               VALUES (?,?,?,?)""",
            (member_id, amount, 0, date.today().isoformat())
        )
        if amount > 0:
            self._credit_fund(
                amount, 'Admission Fee',
                f"Admission fee — {member_id}",
                member_id=member_id, created_by=created_by
            )

    def pay_entrance_fee(self, member_id: str, paid_by: str):
        from datetime import date
        fee = self.fetchone(
            "SELECT * FROM entrance_fees WHERE member_id=? AND is_paid=0", (member_id,)
        )
        if not fee:
            return
        self.execute(
            "UPDATE entrance_fees SET is_paid=1, paid_date=?, paid_by=? WHERE fee_id=?",
            (date.today().isoformat(), paid_by, fee['fee_id'])
        )

    def get_admission_fee_status(self, member_id: str) -> Optional[Dict]:
        return self.fetchone(
            "SELECT * FROM entrance_fees WHERE member_id=? ORDER BY fee_id DESC LIMIT 1",
            (member_id,)
        )

    # -------------------------------------------------------------------------
    # Withdrawal Fee
    # -------------------------------------------------------------------------

    def charge_withdrawal_fee(self, member_id: str, created_by: str):
        amount = float(self.get_setting('withdrawal_fee_amount') or 0)
        if amount <= 0:
            return
        from datetime import date
        self._credit_fund(
            amount, 'Withdrawal Fee',
            f"Withdrawal fee — {member_id}",
            member_id=member_id, created_by=created_by
        )

    # -------------------------------------------------------------------------
    # Death Charge (charged to all active members when someone dies)
    # -------------------------------------------------------------------------

    def charge_death_charge_all(self, deceased_member_id: str,
                                deceased_name: str, created_by: str) -> int:
        amount  = float(self.get_setting('death_charge_amount') or 0)
        members = self.get_all_members(active_only=True)
        from datetime import date
        charged = 0
        with self.transaction():
            for m in members:
                if amount > 0:
                    self._credit_fund(
                        amount, 'Death Charge',
                        f"Death charge — {deceased_name} — {m['member_id']}",
                        member_id=m['member_id'], created_by=created_by
                    )
                charged += 1
        return charged

    # -------------------------------------------------------------------------
    # Death Benefit (paid into the deceased member's account)
    # -------------------------------------------------------------------------

    def pay_death_benefit(self, deceased_member_id: str,
                          deceased_name: str, created_by: str):
        amount = float(self.get_setting('death_benefit_fee_amount') or 0)
        if amount <= 0:
            return
        from datetime import date
        self._debit_fund(
            amount, 'Death Benefit',
            f"Death benefit paid — {deceased_name}",
            member_id=deceased_member_id, created_by=created_by
        )

    # -------------------------------------------------------------------------
    # Readmission Fee
    # -------------------------------------------------------------------------

    def charge_readmission_fee(self, member_id: str, created_by: str):
        amount = float(self.get_setting('readmission_fee_amount') or 0)
        if amount <= 0:
            return
        from datetime import date
        self._credit_fund(
            amount, 'Readmission Fee',
            f"Readmission fee — {member_id}",
            member_id=member_id, created_by=created_by
        )

    # -------------------------------------------------------------------------
    # Retirement Benefits
    # -------------------------------------------------------------------------

    def charge_retirement_benefit(self, member_id: str, created_by: str):
        amount = float(self.get_setting('retirement_benefit_fee_amount') or 0)
        if amount <= 0:
            return
        from datetime import date
        self._debit_fund(
            amount, 'Retirement Benefits',
            f"Retirement benefit — {member_id}",
            member_id=member_id, created_by=created_by
        )

    # -------------------------------------------------------------------------
    # Other Income
    # -------------------------------------------------------------------------

    def record_other_income(self, amount: float, description: str,
                            member_id: str = None, created_by: str = 'system'):
        if amount <= 0:
            return
        self._credit_fund(
            amount, 'Other Income',
            description or 'Other income',
            member_id=member_id, created_by=created_by
        )

    # -------------------------------------------------------------------------
    # Loan Form Fees
    # -------------------------------------------------------------------------

    def charge_loan_form_fee(self, loan_id: int, member_id: str, created_by: str):
        amount = float(self.get_setting('loan_form_fee_amount') or 0)
        from datetime import date
        self.execute(
            """INSERT INTO loan_fees (loan_id, member_id, amount, is_paid, due_date)
               VALUES (?,?,?,?,?)""",
            (loan_id, member_id, amount, 0, date.today().isoformat())
        )
        if amount > 0:
            self._credit_fund(
                amount, 'Loan Form Fee',
                f"Loan form fee — loan #{loan_id}",
                member_id=member_id,
                reference_id=str(loan_id),
                created_by=created_by
            )

    # -------------------------------------------------------------------------
    # Annual Fees
    # -------------------------------------------------------------------------

    def charge_annual_fee_all(self, year: int, created_by: str) -> int:
        amount  = float(self.get_setting('annual_fee_amount') or 0)
        members = self.get_all_members(active_only=True)
        charged = 0
        from datetime import date
        with self.transaction():
            for m in members:
                existing = self.fetchone(
                    "SELECT 1 FROM annual_fees WHERE member_id=? AND year=?",
                    (m['member_id'], year)
                )
                if existing:
                    continue
                self.execute(
                    """INSERT INTO annual_fees (member_id, year, amount, is_paid, due_date)
                       VALUES (?,?,?,0,?)""",
                    (m['member_id'], year, amount, date.today().isoformat())
                )
                if amount > 0:
                    self._credit_fund(
                        amount, 'Annual Fee',
                        f"Annual fee {year} — {m['member_id']}",
                        member_id=m['member_id'],
                        created_by=created_by
                    )
                charged += 1
        return charged

    def get_annual_fees(self, year: int = None) -> List[Dict]:
        q = "SELECT af.*, m.first_name, m.last_name FROM annual_fees af JOIN members m ON af.member_id=m.member_id"
        if year:
            return self.fetchall(q + " WHERE af.year=? ORDER BY af.member_id", (year,))
        return self.fetchall(q + " ORDER BY af.year DESC, af.member_id")

    # -------------------------------------------------------------------------
    # Death Benefit (updated)
    # -------------------------------------------------------------------------

    def process_death_benefit(self, deceased_member_id: str,
                               deceased_name: str,
                               processed_by: str) -> Dict:
        if self.get_setting('death_benefit_enabled') != '1':
            raise ValueError("Death benefit system is disabled")

        charge         = float(self.get_setting('death_charge_amount') or 0)
        benefit_payout = float(self.get_setting('death_benefit_fee_amount') or 0)
        notation_tmpl  = self.get_setting('death_benefit_notation') or \
                         'Death benefit charge — {member_name}'
        notation       = notation_tmpl.replace('{member_name}', deceased_name)
        active_members = self.get_all_members(active_only=True)
        total_collected = len(active_members) * charge

        from datetime import date
        with self.transaction():
            cursor = self.execute(
                """INSERT INTO death_benefits
                   (member_id, benefit_amount, charge_per_member,
                    members_charged, processed_by, processed_date)
                   VALUES (?,?,?,?,?,?)""",
                (deceased_member_id, total_collected, charge,
                 len(active_members), processed_by, date.today().isoformat())
            )
            benefit_id = cursor.lastrowid

            for m in active_members:
                self.execute(
                    """INSERT INTO death_benefit_charges
                       (death_benefit_id, member_id, charge_amount, processed_date)
                       VALUES (?,?,?,?)""",
                    (benefit_id, m['member_id'], charge, date.today().isoformat())
                )
                if charge > 0:
                    acct = self.fetchone(
                        """SELECT sa.account_id, sa.current_balance
                           FROM savings_accounts sa
                           JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
                           WHERE sa.member_id=? AND st.type_code='PREMIUM' AND sa.is_active=1""",
                        (m['member_id'],)
                    )
                    if acct:
                        self.execute(
                            """UPDATE savings_accounts
                               SET current_balance=current_balance-?,
                                   total_withdrawals=total_withdrawals+?
                               WHERE account_id=?""",
                            (charge, charge, acct['account_id'])
                        )
                        self._record_transaction(
                            member_id=m['member_id'],
                            transaction_type='Death Charge',
                            account_type='Savings',
                            account_id=str(acct['account_id']),
                            amount=charge,
                            is_credit=False,
                            txn_data={'description': notation,
                                      'payment_method': 'System'},
                            created_by=processed_by
                        )

            # Credit fund from death charges collected
            if charge > 0:
                self._credit_fund(
                    total_collected, 'Death Charge',
                    f"Death charge collected — {deceased_name}",
                    member_id=deceased_member_id,
                    reference_id=str(benefit_id),
                    created_by=processed_by
                )

            # Debit fund for death benefit paid to deceased's account
            if benefit_payout > 0:
                self._debit_fund(
                    benefit_payout, 'Death Benefit',
                    f"Death benefit paid — {deceased_name}",
                    member_id=deceased_member_id,
                    reference_id=str(benefit_id),
                    created_by=processed_by
                )

        return {
            'benefit_id':        benefit_id,
            'total_collected':   total_collected,
            'members_charged':   len(active_members),
            'charge_per_member': charge,
            'benefit_payout':    benefit_payout,
        }

    def get_death_benefits(self) -> List[Dict]:
        return self.fetchall(
            "SELECT * FROM death_benefits ORDER BY processed_date DESC"
        )

    # -------------------------------------------------------------------------
    # Transfer Fee
    # -------------------------------------------------------------------------

    def transfer_member(self, member_id: str, new_station_id: str,
                         reason: str, created_by: str):
        member = self.get_member(member_id)
        if not member:
            raise ValueError(f"Member {member_id} not found")
        old_station = member['station_id']
        fee = float(self.get_setting('transfer_fee_amount') or 0)
        from datetime import date
        with self.transaction():
            self.execute(
                "UPDATE members SET station_id=?, modified_by=?, modified_date=? WHERE member_id=?",
                (new_station_id, created_by, date.today().isoformat(), member_id)
            )
            self.execute(
                """INSERT INTO member_transfers
                   (member_id, from_station_id, to_station_id, transfer_date, reason, approved_by)
                   VALUES (?,?,?,?,?,?)""",
                (member_id, old_station, new_station_id,
                 date.today().isoformat(), reason, created_by)
            )
            if fee > 0:
                self._credit_fund(
                    fee, 'Transfer Fee',
                    f"Transfer fee — {member_id} ({old_station} → {new_station_id})",
                    member_id=member_id, created_by=created_by
                )

    # -------------------------------------------------------------------------
    # Dividends
    # -------------------------------------------------------------------------

    def distribute_dividends(self, period: str, created_by: str) -> Dict:
        method      = self.get_setting('dividend_distribution_method') or 'percentage'
        pct         = float(self.get_setting('dividend_percentage') or 0)
        fixed_amt   = float(self.get_setting('dividend_fixed_amount') or 0)
        members     = self.get_all_members(active_only=True)
        total_dist  = 0.0
        from datetime import date

        with self.transaction():
            cursor = self.execute(
                """INSERT INTO dividends
                   (distribution_date, period, distribution_method,
                    total_distributed, members_paid, created_by, created_date)
                   VALUES (?,?,?,0,0,?,datetime('now','localtime'))""",
                (date.today().isoformat(), period, method, created_by)
            )
            div_id = cursor.lastrowid

            for m in members:
                if method == 'percentage':
                    savings = self.fetchone(
                        "SELECT COALESCE(SUM(current_balance),0) as bal FROM savings_accounts WHERE member_id=? AND is_active=1",
                        (m['member_id'],)
                    )
                    amount = round(float(savings['bal']) * (pct / 100), 2)
                else:
                    amount = fixed_amt

                if amount <= 0:
                    continue

                savings_row = self.fetchone(
                    """SELECT sa.account_id, sa.current_balance
                       FROM savings_accounts sa
                       JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
                       WHERE sa.member_id=? AND st.type_code='PREMIUM' AND sa.is_active=1""",
                    (m['member_id'],)
                )
                if savings_row:
                    self.execute(
                        """UPDATE savings_accounts
                           SET current_balance=current_balance+?,
                               interest_earned=interest_earned+?
                           WHERE account_id=?""",
                        (amount, amount, savings_row['account_id'])
                    )
                    self._record_transaction(
                        member_id=m['member_id'],
                        transaction_type='Dividend Payment',
                        account_type='Savings',
                        account_id=str(savings_row['account_id']),
                        amount=amount,
                        is_credit=True,
                        txn_data={'description': f"Dividend — {period}",
                                  'payment_method': 'System'},
                        created_by=created_by
                    )

                self.execute(
                    """INSERT INTO dividend_payments
                       (dividend_id, member_id, amount, savings_balance)
                       VALUES (?,?,?,?)""",
                    (div_id, m['member_id'], amount,
                     savings_row['current_balance'] if savings_row else 0)
                )
                total_dist += amount

            self.execute(
                "UPDATE dividends SET total_distributed=?, members_paid=? WHERE dividend_id=?",
                (total_dist, len(members), div_id)
            )

            # debit fund
            if total_dist > 0:
                self._debit_fund(
                    total_dist, 'Dividend',
                    f"Dividend distribution — {period}",
                    created_by=created_by
                )

        return {
            'dividend_id':     div_id,
            'total_distributed': total_dist,
            'members_paid':    len(members),
            'period':          period,
        }

    def get_dividends_history(self) -> List[Dict]:
        return self.fetchall(
            "SELECT * FROM dividends ORDER BY distribution_date DESC"
        )