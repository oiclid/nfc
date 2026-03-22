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
        self.commit()

    def reactivate_member(self, member_id: str, modified_by: str):
        self.execute(
            "UPDATE members SET is_active=1, modified_by=?, modified_date=? WHERE member_id=?",
            (modified_by, datetime.now().isoformat(), member_id)
        )
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
    # Death Benefits
    # -------------------------------------------------------------------------

    def process_death_benefit(self, deceased_member_id: str,
                              processed_by: str) -> Dict:
        if self.get_setting('death_benefit_enabled') != '1':
            raise ValueError("Death benefit system is disabled")
        charge         = float(self.get_setting('death_benefit_amount') or 0)
        active_members = self.get_all_members(active_only=True)
        total_benefit  = len(active_members) * charge

        with self.transaction():
            cursor = self.execute(
                """INSERT INTO death_benefits
                   (member_id, benefit_amount, charge_per_member,
                    members_charged, processed_by, processed_date)
                   VALUES (?,?,?,?,?,?)""",
                (deceased_member_id, total_benefit, charge,
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
            self.mark_member_deceased(
                deceased_member_id, date.today().isoformat(), processed_by
            )
        return {
            'benefit_id':        benefit_id,
            'total_benefit':     total_benefit,
            'members_charged':   len(active_members),
            'charge_per_member': charge
        }

    def get_death_benefits(self) -> List[Dict]:
        return self.fetchall(
            "SELECT * FROM death_benefits ORDER BY processed_date DESC"
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