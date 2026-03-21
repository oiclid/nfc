"""
Stage 1 tests: DatabaseManager

Run with: pytest test_database.py -v
"""
import os
import sys
import pytest
import sqlite3
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from database.db_manager import DatabaseManager

DB_TEMPLATE = os.path.join(os.path.dirname(__file__), 'data', 'nfc_cooperative.db')


@pytest.fixture
def db(tmp_path):
    """Fresh copy of the real DB for each test."""
    dest = tmp_path / 'test.db'
    shutil.copy(DB_TEMPLATE, dest)
    mgr = DatabaseManager(str(dest))
    yield mgr
    mgr.close()


# ─── Settings ────────────────────────────────────────────────────────────────

class TestSettings:
    def test_get_existing_setting(self, db):
        val = db.get_setting('next_member_number')
        assert val is not None
        assert int(val) >= 1

    def test_update_existing_setting(self, db):
        db.update_setting('currency_symbol', '$')
        assert db.get_setting('currency_symbol') == '$'

    def test_upsert_new_setting(self, db):
        db.update_setting('custom_key', 'custom_value', 'admin')
        assert db.get_setting('custom_key') == 'custom_value'

    def test_get_nonexistent_setting_returns_none(self, db):
        assert db.get_setting('this_key_does_not_exist') is None


# ─── Authentication ───────────────────────────────────────────────────────────

class TestAuth:
    def test_authenticate_valid_user(self, db):
        # Create a known user first
        db.create_user({
            'username': 'testuser',
            'password': 'secret123',
            'full_name': 'Test User',
            'role': 'Cashier',
            'can_operate': 1,
        }, created_by='admin')
        user = db.authenticate_user('testuser', 'secret123')
        assert user is not None
        assert user['username'] == 'testuser'

    def test_authenticate_wrong_password(self, db):
        db.create_user({
            'username': 'testuser2',
            'password': 'correct',
            'role': 'Cashier',
        }, created_by='admin')
        assert db.authenticate_user('testuser2', 'wrong') is None

    def test_authenticate_inactive_user(self, db):
        uid = db.create_user({
            'username': 'inactive_user',
            'password': 'pass',
            'role': 'Cashier',
        }, created_by='admin')
        db.deactivate_user(uid, 'admin')
        assert db.authenticate_user('inactive_user', 'pass') is None

    def test_change_password(self, db):
        uid = db.create_user({
            'username': 'pwuser',
            'password': 'oldpass',
            'role': 'Cashier',
        }, created_by='admin')
        db.change_password(uid, 'newpass')
        assert db.authenticate_user('pwuser', 'newpass') is not None
        assert db.authenticate_user('pwuser', 'oldpass') is None


# ─── Users ────────────────────────────────────────────────────────────────────

class TestUsers:
    def test_create_and_get_user(self, db):
        uid = db.create_user({
            'username': 'alice',
            'password': 'alicepass',
            'full_name': 'Alice Smith',
            'email': 'alice@nfc.ng',
            'role': 'Accountant',
            'can_view_reports': 1,
            'can_operate': 1,
        }, created_by='admin')
        user = db.get_user_by_id(uid)
        assert user['full_name'] == 'Alice Smith'
        assert user['role'] == 'Accountant'

    def test_get_all_users_returns_list(self, db):
        users = db.get_all_users()
        assert isinstance(users, list)
        assert len(users) >= 1

    def test_update_user(self, db):
        uid = db.create_user({
            'username': 'bob',
            'password': 'bobpass',
            'role': 'Cashier',
        }, created_by='admin')
        db.update_user(uid, {
            'full_name': 'Bob Updated',
            'email': 'bob@nfc.ng',
            'role': 'Accountant',
            'can_view_reports': 1,
            'can_operate': 1,
            'can_maintain': 0,
            'can_edit': 0,
        }, modified_by='admin')
        user = db.get_user_by_id(uid)
        assert user['full_name'] == 'Bob Updated'
        assert user['role'] == 'Accountant'


# ─── Stations ─────────────────────────────────────────────────────────────────

class TestStations:
    def test_get_all_stations(self, db):
        stations = db.get_all_stations()
        assert isinstance(stations, list)

    def test_add_station(self, db):
        sid = db.add_station('Kano', 'No 1 Station Road')
        s = db.get_station(sid)
        assert s is not None
        assert 'Kano' in s['station_name']

    def test_update_station(self, db):
        sid = db.add_station('Enugu')
        db.update_station(sid, {
            'station_name': 'NFC - Enugu HQ',
            'address': '5 Coal Camp Road',
            'city': 'Enugu',
            'contact_person': 'Mr. Obi',
            'contact_phone': '08012345678',
            'contact_email': 'enugu@nfc.ng',
        }, modified_by='admin')
        s = db.get_station(sid)
        assert s['station_name'] == 'NFC - Enugu HQ'
        assert s['contact_person'] == 'Mr. Obi'

    def test_toggle_station(self, db):
        sid = db.add_station('Benin')
        db.toggle_station(sid, False)
        assert db.get_station(sid)['enabled'] == 0
        db.toggle_station(sid, True)
        assert db.get_station(sid)['enabled'] == 1


# ─── Members ─────────────────────────────────────────────────────────────────

class TestMembers:
    MEMBER_DATA = {
        'station_id': '01',
        'first_name': 'Amaka',
        'last_name': 'Okonkwo',
        'gender': 'Female',
        'date_joined': '2026-01-01',
    }

    def test_add_member_returns_id(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        assert mid.startswith('NFC')

    def test_add_member_increments_counter(self, db):
        before = db.get_next_member_number()
        db.add_member(self.MEMBER_DATA, 'admin')
        assert db.get_next_member_number() == before + 1

    def test_get_member(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        m = db.get_member(mid)
        assert m['first_name'] == 'Amaka'
        assert m['last_name'] == 'Okonkwo'

    def test_update_member(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        data = dict(self.MEMBER_DATA)
        data['first_name'] = 'Ngozi'
        db.update_member(mid, data, 'admin')
        assert db.get_member(mid)['first_name'] == 'Ngozi'

    def test_search_members_by_name(self, db):
        db.add_member(self.MEMBER_DATA, 'admin')
        results = db.search_members('Amaka')
        names = [r['first_name'] for r in results]
        assert 'Amaka' in names

    def test_search_members_by_id(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        results = db.search_members(mid)
        assert any(r['member_id'] == mid for r in results)

    def test_deactivate_member(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        db.deactivate_member(mid, 'admin')
        m = db.get_member(mid)
        assert m['is_active'] == 0

    def test_mark_member_deceased(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        db.mark_member_deceased(mid, '2026-03-01', 'admin')
        m = db.get_member(mid)
        assert m['is_deceased'] == 1
        assert m['is_active'] == 0

    def test_get_all_members_active_only(self, db):
        mid = db.add_member(self.MEMBER_DATA, 'admin')
        db.deactivate_member(mid, 'admin')
        active_ids = [m['member_id'] for m in db.get_all_members(active_only=True)]
        assert mid not in active_ids

    def test_member_summary_view(self, db):
        summaries = db.get_member_summary()
        assert isinstance(summaries, list)
        if summaries:
            assert 'total_savings' in summaries[0]
            assert 'net_balance' in summaries[0]


# ─── Savings ─────────────────────────────────────────────────────────────────

class TestSavings:
    def _make_member(self, db):
        return db.add_member({
            'station_id': '01', 'first_name': 'Tunde',
            'last_name': 'Bello', 'gender': 'Male', 'date_joined': '2026-01-01'
        }, 'admin')

    def test_get_savings_types(self, db):
        types = db.get_savings_types()
        assert len(types) >= 1
        assert 'type_code' in types[0]

    def test_create_savings_account(self, db):
        mid = self._make_member(db)
        aid = db.create_savings_account(mid, 1)
        assert isinstance(aid, int)

    def test_deposit_increases_balance(self, db):
        mid = self._make_member(db)
        aid = db.create_savings_account(mid, 1)
        db.deposit_to_savings(aid, 10000.0, {'payment_method': 'Cash'}, 'admin')
        acct = db.get_savings_account(aid)
        assert acct['current_balance'] == 10000.0
        assert acct['total_deposits'] == 10000.0

    def test_withdraw_reduces_balance(self, db):
        mid = self._make_member(db)
        aid = db.create_savings_account(mid, 1)
        db.deposit_to_savings(aid, 5000.0, {'payment_method': 'Cash'}, 'admin')
        db.withdraw_from_savings(aid, 2000.0, {'payment_method': 'Cash'}, 'admin')
        assert db.get_savings_account(aid)['current_balance'] == 3000.0

    def test_withdraw_insufficient_balance_raises(self, db):
        mid = self._make_member(db)
        aid = db.create_savings_account(mid, 1)
        db.deposit_to_savings(aid, 500.0, {'payment_method': 'Cash'}, 'admin')
        with pytest.raises(ValueError, match="Insufficient balance"):
            db.withdraw_from_savings(aid, 1000.0, {'payment_method': 'Cash'}, 'admin')

    def test_calculate_monthly_interest(self, db):
        mid = self._make_member(db)
        aid = db.create_savings_account(mid, 1)  # PREMIUM: 2%
        db.deposit_to_savings(aid, 100000.0, {'payment_method': 'Cash'}, 'admin')
        interest = db.calculate_monthly_interest(aid)
        assert interest == 2000.0  # 2% of 100,000


# ─── Loans ────────────────────────────────────────────────────────────────────

class TestLoans:
    def _make_member(self, db):
        return db.add_member({
            'station_id': '01', 'first_name': 'Chidi',
            'last_name': 'Eze', 'gender': 'Male', 'date_joined': '2026-01-01'
        }, 'admin')

    def _loan_data(self, member_id):
        return {
            'member_id':        member_id,
            'station_id':       '01',
            'loan_type_id':     1,
            'principal_amount': 100000.0,
            'interest_rate':    10.0,
            'duration_months':  12,
            'start_date':       '2026-01-01',
            'end_date':         '2026-12-31',
        }

    def test_disburse_loan_returns_id(self, db):
        mid = self._make_member(db)
        lid = db.disburse_loan(self._loan_data(mid), 'admin')
        assert isinstance(lid, int)

    def test_loan_amounts_calculated(self, db):
        mid = self._make_member(db)
        lid = db.disburse_loan(self._loan_data(mid), 'admin')
        loan = db.get_loan(lid)
        assert loan['interest_amount'] == 10000.0
        assert loan['total_amount']    == 110000.0
        assert loan['balance_outstanding'] == 110000.0

    def test_get_loan_types(self, db):
        types = db.get_loan_types()
        assert len(types) >= 1

    def test_record_repayment_reduces_balance(self, db):
        mid = self._make_member(db)
        lid = db.disburse_loan(self._loan_data(mid), 'admin')
        db.record_loan_repayment(lid, 10000.0, {'payment_method': 'Cash'}, 'admin')
        loan = db.get_loan(lid)
        assert loan['balance_outstanding'] == 100000.0
        assert loan['status'] == 'Active'

    def test_full_repayment_marks_completed(self, db):
        mid = self._make_member(db)
        lid = db.disburse_loan(self._loan_data(mid), 'admin')
        loan = db.get_loan(lid)
        db.record_loan_repayment(lid, loan['total_amount'], {'payment_method': 'Cash'}, 'admin')
        assert db.get_loan(lid)['status'] == 'Completed'

    def test_repayment_logged_in_repayments_table(self, db):
        mid = self._make_member(db)
        lid = db.disburse_loan(self._loan_data(mid), 'admin')
        db.record_loan_repayment(lid, 5000.0, {'payment_method': 'Cheque', 'cheque_number': 'CHQ001'}, 'admin')
        repayments = db.get_loan_repayments(lid)
        assert len(repayments) == 1
        assert repayments[0]['actual_amount'] == 5000.0


# ─── Transactions ─────────────────────────────────────────────────────────────

class TestTransactions:
    def test_deposit_creates_transaction(self, db):
        mid = db.add_member({
            'station_id': '01', 'first_name': 'Ada',
            'last_name': 'Nwosu', 'gender': 'Female', 'date_joined': '2026-01-01'
        }, 'admin')
        aid = db.create_savings_account(mid, 1)
        db.deposit_to_savings(aid, 5000.0, {'payment_method': 'Cash'}, 'admin')
        txns = db.get_transactions(member_id=mid)
        assert len(txns) >= 1
        assert any(t['transaction_type'] == 'Savings Deposit' for t in txns)

    def test_get_transactions_date_filter(self, db):
        txns = db.get_transactions(start_date='2026-01-01', end_date='2026-12-31')
        assert isinstance(txns, list)


# ─── Rollback on error ────────────────────────────────────────────────────────

class TestTransactionIntegrity:
    def test_failed_deposit_rolls_back(self, db):
        mid = db.add_member({
            'station_id': '01', 'first_name': 'Kemi',
            'last_name': 'Ade', 'gender': 'Female', 'date_joined': '2026-01-01'
        }, 'admin')
        aid = db.create_savings_account(mid, 1)
        # Corrupt the account_id to force a failure mid-transaction
        with pytest.raises(Exception):
            db.deposit_to_savings(999999, 1000.0, {}, 'admin')
        # Balance of our real account must be untouched
        assert db.get_savings_account(aid)['current_balance'] == 0.0mkdir -p data migrations src/database src/gui src/reports src/utils