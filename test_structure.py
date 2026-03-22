"""
Structural tests — grow with each stage.
Run with: pytest test_structure.py -v
"""
import os
import sqlite3
import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))


# ─── Stage 1 Step 1: config files ────────────────────────────────────────────

class TestConfigFiles:
    def test_gitignore_exists(self):
        assert os.path.isfile(os.path.join(ROOT, '.gitignore'))

    def test_gitignore_excludes_db(self):
        with open(os.path.join(ROOT, '.gitignore')) as f:
            content = f.read()
        assert '*.db' in content or 'data/*.db' in content

    def test_gitignore_excludes_pycache(self):
        with open(os.path.join(ROOT, '.gitignore')) as f:
            content = f.read()
        assert '__pycache__' in content

    def test_requirements_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'requirements.txt'))

    def test_requirements_has_pyqt6(self):
        with open(os.path.join(ROOT, 'requirements.txt')) as f:
            content = f.read()
        assert 'PyQt6' in content

    def test_requirements_has_reportlab(self):
        with open(os.path.join(ROOT, 'requirements.txt')) as f:
            content = f.read()
        assert 'reportlab' in content

    def test_requirements_has_openpyxl(self):
        with open(os.path.join(ROOT, 'requirements.txt')) as f:
            content = f.read()
        assert 'openpyxl' in content

    def test_requirements_has_dateutil(self):
        with open(os.path.join(ROOT, 'requirements.txt')) as f:
            content = f.read()
        assert 'python-dateutil' in content

    def test_requirements_has_bcrypt(self):
        with open(os.path.join(ROOT, 'requirements.txt')) as f:
            content = f.read()
        assert 'bcrypt' in content

    def test_readme_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'README.md'))

    def test_readme_not_empty(self):
        with open(os.path.join(ROOT, 'README.md')) as f:
            content = f.read().strip()
        assert len(content) > 0


# ─── Stage 2: migration ───────────────────────────────────────────────────────

class TestMigrationScript:
    def test_migrate_script_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'migrations', 'migrate.py'))

    def test_migrate_script_not_empty(self):
        with open(os.path.join(ROOT, 'migrations', 'migrate.py')) as f:
            content = f.read().strip()
        assert len(content) > 0


class TestMigratedDatabase:
    DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'nfc_cooperative.db')

    def _conn(self):
        assert os.path.isfile(self.DB), "nfc_cooperative.db not found — run: python migrations/migrate.py"
        conn = sqlite3.connect(self.DB)
        conn.row_factory = sqlite3.Row
        return conn

    def test_db_exists(self):
        assert os.path.isfile(self.DB)

    def test_stations_migrated(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        conn.close()
        assert count == 3

    def test_members_migrated(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        conn.close()
        assert count == 327

    def test_members_have_split_names(self):
        conn = self._conn()
        m = conn.execute(
            "SELECT first_name, last_name FROM members WHERE member_id='NFC0001'"
        ).fetchone()
        conn.close()
        assert m['first_name'] == 'JAMES'
        assert m['last_name']  == 'GEORGE'

    def test_savings_accounts_migrated(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM savings_accounts").fetchone()[0]
        conn.close()
        assert count > 0

    def test_savings_balances_positive(self):
        conn = self._conn()
        total = conn.execute(
            "SELECT SUM(current_balance) FROM savings_accounts"
        ).fetchone()[0]
        conn.close()
        assert total > 0

    def test_loans_migrated(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
        conn.close()
        assert count > 8000

    def test_loans_have_valid_status(self):
        conn = self._conn()
        invalid = conn.execute(
            "SELECT COUNT(*) FROM loans WHERE status NOT IN ('Active','Completed','Pending','Defaulted')"
        ).fetchone()[0]
        conn.close()
        assert invalid == 0

    def test_users_migrated(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        assert count == 3

    def test_savings_types_seeded(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM savings_types").fetchone()[0]
        conn.close()
        assert count == 4

    def test_loan_types_seeded(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM loan_types").fetchone()[0]
        conn.close()
        assert count == 8

    def test_system_settings_seeded(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM system_settings").fetchone()[0]
        conn.close()
        assert count >= 10

    def test_member_summary_view_works(self):
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM vw_member_summary LIMIT 5"
        ).fetchall()
        conn.close()
        assert len(rows) > 0
        assert 'total_savings' in rows[0].keys()

    def test_no_orphaned_savings_accounts(self):
        conn = self._conn()
        orphans = conn.execute("""
            SELECT COUNT(*) FROM savings_accounts sa
            WHERE NOT EXISTS (
                SELECT 1 FROM members m WHERE m.member_id = sa.member_id
            )
        """).fetchone()[0]
        conn.close()
        assert orphans == 0

    def test_no_orphaned_loans(self):
        conn = self._conn()
        orphans = conn.execute("""
            SELECT COUNT(*) FROM loans l
            WHERE NOT EXISTS (
                SELECT 1 FROM members m WHERE m.member_id = l.member_id
            )
        """).fetchone()[0]
        conn.close()
        assert orphans == 0

    def test_bank_transactions_migrated(self):
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]
        conn.close()
        assert count == 6

    def test_migrations_table_exists(self):
        conn = self._conn()
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert 'migrations' in tables


# ─── Stage 3: database layer ──────────────────────────────────────────────────

class TestDBManagerFile:
    def test_db_manager_is_full(self):
        path = os.path.join(ROOT, 'src', 'database', 'db_manager.py')
        with open(path) as f:
            content = f.read()
        assert 'class DatabaseManager' in content

    def test_db_manager_has_auth(self):
        path = os.path.join(ROOT, 'src', 'database', 'db_manager.py')
        with open(path) as f:
            content = f.read()
        assert 'authenticate_user' in content

    def test_db_manager_has_members(self):
        path = os.path.join(ROOT, 'src', 'database', 'db_manager.py')
        with open(path) as f:
            content = f.read()
        assert 'add_member' in content

    def test_db_manager_has_savings(self):
        path = os.path.join(ROOT, 'src', 'database', 'db_manager.py')
        with open(path) as f:
            content = f.read()
        assert 'deposit_to_savings' in content

    def test_db_manager_has_loans(self):
        path = os.path.join(ROOT, 'src', 'database', 'db_manager.py')
        with open(path) as f:
            content = f.read()
        assert 'disburse_loan' in content

    def test_migrations_runner_is_full(self):
        path = os.path.join(ROOT, 'src', 'database', 'migrations.py')
        with open(path) as f:
            content = f.read()
        assert 'def run(' in content

    def test_wipe_migration_exists(self):
        assert os.path.isfile(
            os.path.join(ROOT, 'migrations', '0001_wipe_legacy_users.py')
        )

    def test_wipe_migration_has_up(self):
        path = os.path.join(ROOT, 'migrations', '0001_wipe_legacy_users.py')
        with open(path) as f:
            content = f.read()
        assert 'def up(' in content


class TestDBManagerFunctions:
    """Functional tests against a temp copy of the migrated DB."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        import shutil
        import sys
        src_path = os.path.join(ROOT, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        from database.db_manager import DatabaseManager
        db_src  = os.path.join(ROOT, 'data', 'nfc_cooperative.db')
        db_dest = str(tmp_path / 'test.db')
        shutil.copy(db_src, db_dest)
        self.db = DatabaseManager(db_dest)
        yield
        self.db.close()

    def test_get_setting(self):
        val = self.db.get_setting('next_member_number')
        assert val is not None

    def test_update_setting(self):
        self.db.update_setting('currency_symbol', 'USD')
        assert self.db.get_setting('currency_symbol') == 'USD'

    def test_upsert_new_setting(self):
        self.db.update_setting('test_key', 'test_val')
        assert self.db.get_setting('test_key') == 'test_val'

    def test_create_and_auth_user(self):
        self.db.create_user({
            'username': 'testuser', 'password': 'pass123',
            'role': 'Cashier', 'can_operate': 1
        }, 'admin')
        user = self.db.authenticate_user('testuser', 'pass123')
        assert user is not None
        assert user['username'] == 'testuser'

    def test_wrong_password_fails(self):
        self.db.create_user({
            'username': 'testuser2', 'password': 'correct',
            'role': 'Cashier'
        }, 'admin')
        assert self.db.authenticate_user('testuser2', 'wrong') is None

    def test_get_all_stations(self):
        stations = self.db.get_all_stations()
        assert len(stations) == 3

    def test_add_member(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Test',
            'last_name': 'User', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        assert mid.startswith('NFC')
        assert self.db.get_member(mid) is not None

    def test_search_members(self):
        results = self.db.search_members('NFC0001')
        assert len(results) >= 1

    def test_get_savings_types(self):
        types = self.db.get_savings_types()
        assert len(types) == 4

    def test_create_savings_account(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Save',
            'last_name': 'Test', 'gender': 'Female',
            'date_joined': '2026-01-01'
        }, 'admin')
        aid = self.db.create_savings_account(mid, 1)
        assert isinstance(aid, int)

    def test_deposit_and_balance(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Dep',
            'last_name': 'Test', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        aid = self.db.create_savings_account(mid, 1)
        self.db.deposit_to_savings(aid, 5000.0, {'payment_method': 'Cash'}, 'admin')
        acct = self.db.get_savings_account(aid)
        assert acct['current_balance'] == 5000.0

    def test_withdraw_reduces_balance(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'With',
            'last_name': 'Test', 'gender': 'Female',
            'date_joined': '2026-01-01'
        }, 'admin')
        aid = self.db.create_savings_account(mid, 1)
        self.db.deposit_to_savings(aid, 5000.0, {'payment_method': 'Cash'}, 'admin')
        self.db.withdraw_from_savings(aid, 2000.0, {'payment_method': 'Cash'}, 'admin')
        assert self.db.get_savings_account(aid)['current_balance'] == 3000.0

    def test_overdraft_raises(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Over',
            'last_name': 'Test', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        aid = self.db.create_savings_account(mid, 1)
        self.db.deposit_to_savings(aid, 100.0, {'payment_method': 'Cash'}, 'admin')
        with pytest.raises(ValueError, match="Insufficient balance"):
            self.db.withdraw_from_savings(aid, 500.0, {'payment_method': 'Cash'}, 'admin')

    def test_disburse_loan(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Loan',
            'last_name': 'Test', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        lid = self.db.disburse_loan({
            'member_id': mid, 'station_id': '01', 'loan_type_id': 1,
            'principal_amount': 100000.0, 'interest_rate': 10.0,
            'duration_months': 12, 'start_date': '2026-01-01',
            'end_date': '2026-12-31'
        }, 'admin')
        loan = self.db.get_loan(lid)
        assert loan['interest_amount']     == 10000.0
        assert loan['total_amount']        == 110000.0
        assert loan['balance_outstanding'] == 110000.0

    def test_loan_repayment(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Rep',
            'last_name': 'Test', 'gender': 'Female',
            'date_joined': '2026-01-01'
        }, 'admin')
        lid = self.db.disburse_loan({
            'member_id': mid, 'station_id': '01', 'loan_type_id': 1,
            'principal_amount': 100000.0, 'interest_rate': 10.0,
            'duration_months': 12, 'start_date': '2026-01-01',
            'end_date': '2026-12-31'
        }, 'admin')
        self.db.record_loan_repayment(
            lid, 110000.0, {'payment_method': 'Cash'}, 'admin'
        )
        assert self.db.get_loan(lid)['status'] == 'Completed'

    def test_get_transactions(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Txn',
            'last_name': 'Test', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        aid = self.db.create_savings_account(mid, 1)
        self.db.deposit_to_savings(aid, 1000.0, {'payment_method': 'Cash'}, 'admin')
        txns = self.db.get_transactions(member_id=mid)
        assert len(txns) >= 1

    def test_member_summary_view(self):
        summaries = self.db.get_member_summary()
        assert isinstance(summaries, list)
        assert len(summaries) > 0
        assert 'total_savings' in summaries[0]


# ─── Stage 4: auth ────────────────────────────────────────────────────────────

class TestAuthFiles:
    def _content(self, *parts):
        with open(os.path.join(ROOT, *parts)) as f:
            return f.read()

    def test_main_py_is_full(self):
        assert 'class NFCApp' in self._content('main.py')

    def test_main_py_has_migration_runner(self):
        assert 'run_migrations' in self._content('main.py')

    def test_main_py_has_first_launch_check(self):
        assert 'get_all_users' in self._content('main.py')

    def test_main_py_has_setup_wizard(self):
        assert 'SetupWizard' in self._content('main.py')

    def test_main_py_has_login_window(self):
        assert 'LoginWindow' in self._content('main.py')

    def test_login_window_is_full(self):
        assert 'class LoginWindow' in self._content('src', 'gui', 'login_window.py')

    def test_login_window_has_signal(self):
        assert 'login_successful' in self._content('src', 'gui', 'login_window.py')

    def test_login_window_has_auth(self):
        assert 'authenticate_user' in self._content('src', 'gui', 'login_window.py')

    def test_setup_wizard_is_full(self):
        assert 'class SetupWizard' in self._content('src', 'gui', 'setup_wizard.py')

    def test_setup_wizard_has_signal(self):
        assert 'setup_complete' in self._content('src', 'gui', 'setup_wizard.py')

    def test_setup_wizard_has_validation(self):
        content = self._content('src', 'gui', 'setup_wizard.py')
        assert 'len(password)' in content

    def test_setup_wizard_creates_admin(self):
        content = self._content('src', 'gui', 'setup_wizard.py')
        assert 'create_user' in content
        assert "'Admin'" in content


class TestPurgeMigration:
    def test_purge_migration_exists(self):
        assert os.path.isfile(
            os.path.join(ROOT, 'migrations', '0002_purge_members.py')
        )

    def test_purge_migration_has_up(self):
        with open(os.path.join(ROOT, 'migrations', '0002_purge_members.py')) as f:
            content = f.read()
        assert 'def up(' in content

    def test_purge_migration_has_126_ids(self):
        with open(os.path.join(ROOT, 'migrations', '0002_purge_members.py')) as f:
            content = f.read()
        assert content.count("'NFC") == 126

    def test_purge_migration_renumbers(self):
        with open(os.path.join(ROOT, 'migrations', '0002_purge_members.py')) as f:
            content = f.read()
        assert 'next_member_number' in content

    def test_purge_result_on_temp_db(self, tmp_path):
        import shutil
        import importlib.util
        db_src  = os.path.join(ROOT, 'data', 'nfc_cooperative.db')
        db_dest = str(tmp_path / 'test.db')
        shutil.copy(db_src, db_dest)

        spec   = importlib.util.spec_from_file_location(
            'purge', os.path.join(ROOT, 'migrations', '0002_purge_members.py')
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        conn = sqlite3.connect(db_dest)
        conn.row_factory = sqlite3.Row
        module.up(conn)

        count    = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        next_num = conn.execute(
            "SELECT setting_value FROM system_settings WHERE setting_key='next_member_number'"
        ).fetchone()[0]
        orphaned_savings = conn.execute(
            """SELECT COUNT(*) FROM savings_accounts sa
               WHERE NOT EXISTS (SELECT 1 FROM members m WHERE m.member_id=sa.member_id)"""
        ).fetchone()[0]
        orphaned_loans = conn.execute(
            """SELECT COUNT(*) FROM loans l
               WHERE NOT EXISTS (SELECT 1 FROM members m WHERE m.member_id=l.member_id)"""
        ).fetchone()[0]
        ids  = [r[0] for r in conn.execute("SELECT member_id FROM members ORDER BY member_id").fetchall()]
        nums = [int(mid[3:]) for mid in ids]
        gaps = [i for i in range(1, len(nums) + 1) if i not in nums]
        conn.close()

        assert count == 203
        assert next_num == '204'
        assert orphaned_savings == 0
        assert orphaned_loans   == 0
        assert gaps             == []


# ─── Stage 5: main window ─────────────────────────────────────────────────────

class TestMainWindow:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'main_window.py')) as f:
            return f.read()

    def test_main_window_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'main_window.py'))

    def test_main_window_has_class(self):
        assert 'class MainWindow' in self._content()

    def test_main_window_has_sidebar(self):
        assert '_build_sidebar' in self._content()

    def test_main_window_has_header(self):
        assert '_build_header' in self._content()

    def test_main_window_has_stack(self):
        assert 'QStackedWidget' in self._content()

    def test_main_window_has_role_checks(self):
        content = self._content()
        assert 'can_maintain' in content
        assert 'can_operate' in content
        assert 'can_view_reports' in content

    def test_main_window_has_switch(self):
        assert '_switch' in self._content()

    def test_main_window_has_logout(self):
        assert '_logout' in self._content()

    def test_main_window_has_status_bar(self):
        assert '_update_status' in self._content()

    def test_main_window_loads_all_modules(self):
        content = self._content()
        for mod in ['DashboardModule', 'StationsModule', 'MembersModule',
                    'SavingsModule', 'LoansModule', 'TransactionsModule',
                    'ReportsModule', 'SettingsModule']:
            assert mod in content, f"Missing: {mod}"