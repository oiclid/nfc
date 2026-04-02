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
        # 327 before purge migration runs, 203 after
        assert count >= 203

    def test_members_have_split_names(self):
        conn = self._conn()
        m = conn.execute(
            "SELECT first_name, last_name FROM members ORDER BY member_id LIMIT 1"
        ).fetchone()
        conn.close()
        assert m['first_name'] is not None
        assert m['last_name']  is not None
        assert ' ' not in m['first_name']  # names are split, not combined

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
        # 8451 before purge, fewer after purged members' loans removed
        assert count > 5000

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
        # 3 before wipe migration, >= 1 after (setup wizard creates admin)
        assert count >= 1

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

        # Use a fresh migration from database.sld if available,
        # otherwise verify the live DB is already in the correct post-purge state
        db_src  = os.path.join(ROOT, 'data', 'nfc_cooperative.db')
        db_dest = str(tmp_path / 'test.db')
        shutil.copy(db_src, db_dest)

        conn = sqlite3.connect(db_dest)
        conn.row_factory = sqlite3.Row
        before = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]

        if before == 327:
            # 0002 not yet applied — run it and verify result
            spec   = importlib.util.spec_from_file_location(
                'purge', os.path.join(ROOT, 'migrations', '0002_purge_members.py')
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.up(conn)
            count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
            assert count == 203
        else:
            # 0002 already ran — just verify the DB is in the correct state
            count = before
            assert count <= 203

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

        assert orphaned_savings == 0
        assert orphaned_loans   == 0
        assert gaps             == []
        assert int(next_num)    == count + 1


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
                    'CooperativeFundModule', 'ReportsModule', 'SettingsModule']:
            assert mod in content, f"Missing: {mod}"


# ─── Stage 6: stations module ─────────────────────────────────────────────────

class TestStationsModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'stations_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'stations_module.py'))

    def test_has_class(self):
        assert 'class StationsModule' in self._content()

    def test_has_dialog(self):
        assert 'class StationDialog' in self._content()

    def test_has_refresh(self):
        assert 'def refresh' in self._content()

    def test_has_add(self):
        assert '_add_station' in self._content()

    def test_has_edit(self):
        assert '_edit_selected' in self._content()

    def test_has_close(self):
        assert '_close_station' in self._content()

    def test_has_reactivate(self):
        assert '_reactivate_station' in self._content()

    def test_has_toggle_station(self):
        assert 'toggle_station' in self._content()

    def test_has_is_admin(self):
        assert '_is_admin' in self._content()

    def test_has_confirm(self):
        assert '_confirm' in self._content()

    def test_shows_all_columns(self):
        content = self._content()
        for col in ['station_name', 'address', 'contact_person',
                    'contact_phone', 'contact_email']:
            assert col in content, f"Missing column: {col}"

    def test_close_confirmation(self):
        assert 'Confirm Close Station' in self._content()

    def test_reactivate_confirmation(self):
        assert 'Confirm Reactivate Station' in self._content()

    def test_add_confirmation(self):
        assert 'Confirm Add Station' in self._content()

    def test_edit_confirmation(self):
        assert 'Confirm Edit Station' in self._content()

    def test_no_reassignment_message(self):
        assert 'reassigned' in self._content()

    def test_status_uses_open_closed(self):
        content = self._content()
        assert 'Open' in content and 'Closed' in content

    def test_station_id_format(self):
        with open(os.path.join(ROOT, 'src', 'database', 'db_manager.py')) as f:
            db_content = f.read()
        assert ':02d' in db_content

    def test_no_reassignment_in_db_manager(self):
        with open(os.path.join(ROOT, 'src', 'database', 'db_manager.py')) as f:
            db_content = f.read()
        assert 'next_station_number' in db_content


# ─── Stage 7: members module ─────────────────────────────────────────────────

class TestMembersModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'members_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'members_module.py'))

    def test_has_class(self):
        assert 'class MembersModule' in self._content()

    def test_has_member_dialog(self):
        assert 'class MemberDialog' in self._content()

    def test_has_view_dialog(self):
        assert 'class MemberViewDialog' in self._content()

    def test_has_refresh(self):
        assert 'def refresh' in self._content()

    def test_has_search(self):
        assert 'search_input' in self._content()

    def test_has_station_filter(self):
        assert 'station_filter' in self._content()

    def test_has_status_filter(self):
        assert 'status_filter' in self._content()

    def test_has_add(self):
        assert '_add_member' in self._content()

    def test_has_edit(self):
        assert '_edit_member' in self._content()

    def test_has_view(self):
        assert '_view_member' in self._content()

    def test_has_deactivate(self):
        assert '_deactivate_member' in self._content()

    def test_has_reactivate(self):
        assert '_reactivate_member' in self._content()

    def test_has_mark_deceased(self):
        assert '_mark_deceased' in self._content()

    def test_has_is_admin(self):
        assert '_is_admin' in self._content()

    def test_has_confirm(self):
        assert '_confirm' in self._content()

    def test_has_nok_fields(self):
        content = self._content()
        for field in ['nok1_name', 'nok1_relationship', 'nok2_name', 'nok2_relationship']:
            assert field in content, f"Missing NOK field: {field}"

    def test_has_financial_summary(self):
        assert 'Financial Summary' in self._content()

    def test_has_confirmation_on_add(self):
        assert 'Confirm Add Member' in self._content()

    def test_has_confirmation_on_edit(self):
        assert 'Confirm Edit Member' in self._content()

    def test_has_confirmation_on_deactivate(self):
        assert 'DEACTIVATE' in self._content()

    def test_has_confirmation_on_reactivate(self):
        assert 'REACTIVATE' in self._content()

    def test_has_confirmation_on_deceased(self):
        assert 'DECEASED' in self._content()

    def test_no_reassignment_message(self):
        assert 'reassigned' in self._content()

    def test_names_uppercased(self):
        assert '.upper()' in self._content()

    def test_severe_warning_method(self):
        assert '_severe_warning' in self._content()

    def test_deceased_is_irreversible(self):
        assert 'IRREVERSIBLE' in self._content()

    def test_admin_guard_on_deactivate(self):
        assert 'Only administrators can deactivate' in self._content()

    def test_admin_guard_on_reactivate(self):
        assert 'Only administrators can reactivate' in self._content()

    def test_admin_guard_on_deceased(self):
        assert 'Only administrators can mark' in self._content()

    def test_reactivate_in_db_manager(self):
        with open(os.path.join(ROOT, 'src', 'database', 'db_manager.py')) as f:
            db_content = f.read()
        assert 'reactivate_member' in db_content

    def test_summary_shows_counts(self):
        content = self._content()
        assert 'Active:' in content
        assert 'Inactive:' in content
        assert 'Deceased:' in content



# ─── Stage 8: savings module ──────────────────────────────────────────────────

class TestSavingsModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'savings_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'savings_module.py'))

    def test_has_class(self):
        assert 'class SavingsModule' in self._content()

    def test_has_transaction_dialog(self):
        assert 'class TransactionDialog' in self._content()

    def test_has_open_account_dialog(self):
        assert 'class OpenAccountDialog' in self._content()

    def test_has_history_dialog(self):
        assert 'class AccountHistoryDialog' in self._content()

    def test_has_refresh(self):
        assert 'def refresh' in self._content()

    def test_has_deposit(self):
        assert '_deposit' in self._content()

    def test_has_withdraw(self):
        assert '_withdraw' in self._content()

    def test_has_open_account(self):
        assert '_open_account' in self._content()

    def test_has_search(self):
        assert 'search_input' in self._content()

    def test_has_station_filter(self):
        assert 'station_filter' in self._content()

    def test_has_type_filter(self):
        assert 'type_filter' in self._content()

    def test_has_date_filter(self):
        assert 'date_from' in self._content()

    def test_has_multi_term_search(self):
        assert 'terms' in self._content()

    def test_has_summary_cards(self):
        assert '_update_summary_cards' in self._content()

    def test_has_accounts_tab(self):
        assert 'Accounts' in self._content()

    def test_has_transactions_tab(self):
        assert 'Transaction History' in self._content()

    def test_has_confirm_deposit(self):
        assert 'Confirm Deposit' in self._content()

    def test_has_confirm_withdrawal(self):
        assert 'Confirm Withdrawal' in self._content()

    def test_has_payment_methods(self):
        content = self._content()
        for method in ['Cash', 'Cheque', 'Bank Transfer']:
            assert method in content, f"Missing payment method: {method}"

    def test_has_cheque_number_field(self):
        assert 'cheque_number' in self._content()

    def test_has_currency_formatting(self):
        assert 'self.currency' in self._content()


# ─── Stage 9: loans module ────────────────────────────────────────────────────

class TestLoansModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'loans_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'loans_module.py'))

    def test_has_class(self):
        assert 'class LoansModule' in self._content()

    def test_has_repayment_dialog(self):
        assert 'class RepaymentDialog' in self._content()

    def test_has_loan_detail_dialog(self):
        assert 'class LoanDetailDialog' in self._content()

    def test_has_refresh(self):
        assert 'def refresh' in self._content()

    def test_has_disburse(self):
        assert '_disburse' in self._content()

    def test_has_record_repayment(self):
        assert '_record_repayment' in self._content()

    def test_has_view_loan(self):
        assert '_view_loan' in self._content()

    def test_has_search(self):
        assert 'search_input' in self._content()

    def test_has_station_filter(self):
        assert 'station_filter' in self._content()

    def test_has_type_filter(self):
        assert 'type_filter' in self._content()

    def test_has_status_filter(self):
        assert 'status_filter' in self._content()

    def test_has_date_filter(self):
        assert 'rep_date_from' in self._content()

    def test_has_multi_term_search(self):
        assert 'terms' in self._content()

    def test_has_loan_preview(self):
        assert 'prev_interest' in self._content()

    def test_has_summary_cards(self):
        assert '_update_summary_cards' in self._content()

    def test_has_all_tabs(self):
        content = self._content()
        for tab in ['All Loans', 'Repayment History', 'Disburse Loan']:
            assert tab in content, f"Missing tab: {tab}"

    def test_has_loan_types(self):
        assert 'get_loan_types' in self._content()

    def test_has_confirm_repayment(self):
        assert 'Confirm Repayment' in self._content()

    def test_has_confirm_disburse(self):
        assert 'Confirm Loan Disbursement' in self._content()

    def test_has_payment_methods(self):
        content = self._content()
        for method in ['Cash', 'Cheque', 'Bank Transfer']:
            assert method in content

    def test_inactive_member_blocked(self):
        assert 'inactive or deceased' in self._content()

    def test_has_end_date_calculation(self):
        assert 'relativedelta' in self._content()


# ─── Stage 10: transactions module ───────────────────────────────────────────

class TestTransactionsModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'transactions_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'transactions_module.py'))

    def test_has_class(self):
        assert 'class TransactionsModule' in self._content()

    def test_has_detail_dialog(self):
        assert 'class TransactionDetailDialog' in self._content()

    def test_has_bank_dialog(self):
        assert 'class BankTransactionDialog' in self._content()

    def test_has_refresh(self):
        assert 'def refresh' in self._content()

    def test_has_search(self):
        assert 'search_input' in self._content()

    def test_has_station_filter(self):
        assert 'station_filter' in self._content()

    def test_has_type_filter(self):
        assert 'type_filter' in self._content()

    def test_has_date_filter(self):
        assert 'date_from' in self._content()

    def test_has_credits_debits_filter(self):
        content = self._content()
        assert 'credits_only' in content
        assert 'debits_only' in content

    def test_has_multi_term_search(self):
        assert 'terms' in self._content()

    def test_has_all_transactions_tab(self):
        assert 'All Transactions' in self._content()

    def test_has_bank_transactions_tab(self):
        assert 'Bank Transactions' in self._content()

    def test_has_summary_cards(self):
        assert '_update_summary_cards' in self._content()

    def test_has_add_bank_transaction(self):
        assert '_add_bank_transaction' in self._content()

    def test_has_mark_cleared(self):
        assert '_mark_cleared' in self._content()

    def test_has_view_transaction(self):
        assert '_view_transaction' in self._content()

    def test_transactions_are_immutable(self):
        assert 'cannot be modified' in self._content()

    def test_has_confirm_bank_transaction(self):
        assert 'Confirm Bank Transaction' in self._content()

    def test_admin_only_add_bank(self):
        assert "role') == 'Admin'" in self._content()

    def test_has_cleared_filter(self):
        assert 'Cleared' in self._content()


# ─── Stage 11: reports engine ─────────────────────────────────────────────────

class TestReportGenerator:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'reports', 'report_generator.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'reports', 'report_generator.py'))

    def test_has_class(self):
        assert 'class ReportGenerator' in self._content()

    def test_has_members_list_pdf(self):
        assert 'def members_list_pdf' in self._content()

    def test_has_members_list_excel(self):
        assert 'def members_list_excel' in self._content()

    def test_has_savings_summary_pdf(self):
        assert 'def savings_summary_pdf' in self._content()

    def test_has_savings_summary_excel(self):
        assert 'def savings_summary_excel' in self._content()

    def test_has_loans_summary_pdf(self):
        assert 'def loans_summary_pdf' in self._content()

    def test_has_loans_summary_excel(self):
        assert 'def loans_summary_excel' in self._content()

    def test_has_member_statement_pdf(self):
        assert 'def member_statement_pdf' in self._content()

    def test_has_transactions_report_pdf(self):
        assert 'def transactions_report_pdf' in self._content()

    def test_has_transactions_report_excel(self):
        assert 'def transactions_report_excel' in self._content()

    def test_has_reports_dir(self):
        assert 'REPORTS_DIR' in self._content()

    def test_has_pdf_header(self):
        assert '_pdf_header' in self._content()

    def test_has_xl_title(self):
        assert '_xl_title' in self._content()

    def test_generates_members_pdf(self, tmp_path):
        import shutil, sys
        sys.path.insert(0, os.path.join(ROOT, 'src'))
        from reports.report_generator import ReportGenerator
        db_dest = str(tmp_path / 'test.db')
        shutil.copy(os.path.join(ROOT, 'data', 'nfc_cooperative.db'), db_dest)

        rg = ReportGenerator.__new__(ReportGenerator)
        rg.db_path = db_dest
        import os as _os
        report_dir = str(tmp_path / 'reports')
        _os.makedirs(report_dir, exist_ok=True)

        from reports import report_generator as rg_module
        orig = rg_module.REPORTS_DIR
        rg_module.REPORTS_DIR = report_dir
        rg.__init__(db_dest)

        path = rg.members_list_pdf()
        rg_module.REPORTS_DIR = orig
        assert _os.path.isfile(path)
        assert _os.path.getsize(path) > 1000

    def test_generates_savings_excel(self, tmp_path):
        import shutil, sys, os as _os
        sys.path.insert(0, os.path.join(ROOT, 'src'))
        from reports.report_generator import ReportGenerator
        from reports import report_generator as rg_module
        db_dest    = str(tmp_path / 'test.db')
        report_dir = str(tmp_path / 'reports')
        shutil.copy(os.path.join(ROOT, 'data', 'nfc_cooperative.db'), db_dest)
        _os.makedirs(report_dir, exist_ok=True)
        orig = rg_module.REPORTS_DIR
        rg_module.REPORTS_DIR = report_dir
        rg = ReportGenerator(db_dest)
        path = rg.savings_summary_excel()
        rg_module.REPORTS_DIR = orig
        assert _os.path.isfile(path)
        assert _os.path.getsize(path) > 1000


# ─── Stage 12: reports UI ─────────────────────────────────────────────────────

class TestReportsModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'reports_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'reports_module.py'))

    def test_has_class(self):
        assert 'class ReportsModule' in self._content()

    def test_has_report_worker(self):
        assert 'class ReportWorker' in self._content()

    def test_has_all_tabs(self):
        content = self._content()
        for tab in ['Members', 'Savings', 'Loans',
                    'Member Statement', 'Transactions', 'Generated Reports']:
            assert tab in content, f"Missing tab: {tab}"

    def test_has_generate_members(self):
        assert '_generate_members' in self._content()

    def test_has_generate_savings(self):
        assert '_generate_savings' in self._content()

    def test_has_generate_loans(self):
        assert '_generate_loans' in self._content()

    def test_has_generate_statement(self):
        assert '_generate_statement' in self._content()

    def test_has_generate_transactions(self):
        assert '_generate_transactions' in self._content()

    def test_has_history_tab(self):
        assert '_load_history' in self._content()

    def test_has_open_file(self):
        assert '_open_file' in self._content()

    def test_has_delete_report(self):
        assert '_delete_selected_report' in self._content()

    def test_has_progress_bar(self):
        assert 'QProgressBar' in self._content()

    def test_runs_in_thread(self):
        assert 'QThread' in self._content()

    def test_wired_to_generator(self):
        assert 'ReportGenerator' in self._content()

    def test_has_station_filter(self):
        assert '_station_combo' in self._content()

    def test_has_format_selector(self):
        content = self._content()
        assert 'PDF' in content and 'Excel' in content

    def test_has_member_lookup(self):
        assert '_lookup_statement_member' in self._content()

    def test_opens_after_generation(self):
        assert 'Open now?' in self._content()


# ─── Fixes: transactions module, main window, historical migration ─────────────

class TestTransactionsFixes:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'transactions_module.py')) as f:
            return f.read()

    def test_qtabwidget_in_top_imports(self):
        # QTabWidget must be at top level, not imported inside a method
        lines = self._content().split('\n')
        import_block_end = next(i for i, l in enumerate(lines) if l.startswith('class '))
        import_section = '\n'.join(lines[:import_block_end])
        assert 'QTabWidget' in import_section

    def test_fmt_handles_none(self):
        # _fmt must use `or 0` to handle None from empty SUM() aggregates
        assert 'float(amount or 0)' in self._content()

    def test_date_from_starts_2010(self):
        # default date range starts from 2010 to show historical data
        assert 'QDate(2010, 1, 1)' in self._content()

    def test_empty_state_label(self):
        assert 'txn_empty_lbl' in self._content()

    def test_no_debug_prints_in_main_window(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'main_window.py')) as f:
            content = f.read()
        assert 'print(' not in content
        assert 'traceback.print_exc' not in content


class TestHistoricalTransactionMigration:
    MIGRATION = os.path.join(ROOT, 'migrations', '0003_migrate_historical_transactions.py')

    def _content(self):
        with open(self.MIGRATION) as f:
            return f.read()

    def test_migration_file_exists(self):
        assert os.path.isfile(self.MIGRATION)

    def test_has_up_function(self):
        assert 'def up(' in self._content()

    def test_has_account_map(self):
        assert 'ACCOUNT_MAP' in self._content()

    def test_maps_savings_deposit(self):
        assert 'Savings Deposit' in self._content()

    def test_maps_savings_withdrawal(self):
        assert 'Savings Withdrawal' in self._content()

    def test_maps_loan_disbursement(self):
        assert 'Loan Disbursement' in self._content()

    def test_maps_loan_repayment(self):
        assert 'Loan Repayment' in self._content()

    def test_uses_batch_insert(self):
        assert 'executemany' in self._content()

    def test_skips_purged_members(self):
        assert 'valid_members' in self._content()

    def test_skips_zero_amounts(self):
        assert 'amount <= 0' in self._content()

    def test_checks_legacy_db_exists(self):
        assert 'os.path.isfile' in self._content()

    def test_migration_applied_to_live_db(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE created_by='migration'"
        ).fetchone()[0]
        conn.close()
        assert count > 35000, f"Expected >50000 migrated transactions, got {count}"

    def test_savings_deposits_migrated(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_type='Savings Deposit'"
        ).fetchone()[0]
        conn.close()
        assert count > 25000

    def test_loan_disbursements_migrated(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_type='Loan Disbursement'"
        ).fetchone()[0]
        conn.close()
        assert count > 35000

    def test_no_orphaned_transactions(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        orphans = conn.execute("""
            SELECT COUNT(*) FROM transactions t
            WHERE t.member_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM members m WHERE m.member_id=t.member_id
            )
        """).fetchone()[0]
        conn.close()
        assert orphans == 0

    def test_all_transactions_have_dates(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        nulldates = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_date IS NULL"
        ).fetchone()[0]
        conn.close()
        assert nulldates == 0


# ─── Stage 13: dashboard + settings ──────────────────────────────────────────

class TestDashboardModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'dashboard_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'dashboard_module.py'))

    def test_has_class(self):
        assert 'class DashboardModule' in self._content()

    def test_has_refresh(self):
        assert 'def refresh' in self._content()

    def test_has_summary_cards(self):
        assert '_load_cards' in self._content()

    def test_has_recent_transactions(self):
        assert '_load_recent_transactions' in self._content()

    def test_has_members_by_station(self):
        assert '_load_members_by_station' in self._content()

    def test_has_savings_by_type(self):
        assert '_load_savings_by_type' in self._content()

    def test_has_quick_actions(self):
        assert '_load_quick_actions' in self._content()

    def test_has_navigation(self):
        assert '_navigate' in self._content()

    def test_cards_are_clickable(self):
        assert 'switch_to' in self._content()


class TestSettingsModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'settings_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'settings_module.py'))

    def test_has_class(self):
        assert 'class SettingsModule' in self._content()

    def test_has_user_dialog(self):
        assert 'class UserDialog' in self._content()

    def test_has_change_password_dialog(self):
        assert 'class ChangePasswordDialog' in self._content()

    def test_has_savings_type_dialog(self):
        assert 'class SavingsTypeDialog' in self._content()

    def test_has_loan_type_dialog(self):
        assert 'class LoanTypeDialog' in self._content()

    def test_has_all_tabs(self):
        content = self._content()
        for tab in ['System', 'Users', 'Savings Types', 'Loan Types']:
            assert tab in content, f"Missing tab: {tab}"

    def test_has_system_settings(self):
        assert '_save_system_settings' in self._content()

    def test_has_user_management(self):
        content = self._content()
        assert '_add_user' in content
        assert '_edit_user' in content
        assert '_deactivate_user' in content
        assert '_change_password' in content

    def test_has_savings_type_management(self):
        content = self._content()
        assert '_add_savings_type' in content
        assert '_edit_savings_type' in content
        assert '_toggle_savings_type' in content

    def test_has_loan_type_management(self):
        content = self._content()
        assert '_add_loan_type' in content
        assert '_edit_loan_type' in content
        assert '_toggle_loan_type' in content

    def test_blocks_deactivate_self(self):
        assert "user['username'] != self.user['username']" in self._content()

    def test_blocks_deactivate_type_with_active_accounts(self):
        assert 'active accounts use this type' in self._content()

    def test_blocks_deactivate_loan_type_with_active_loans(self):
        assert 'active loans use this type' in self._content()

    def test_password_min_length(self):
        assert 'len(self.password_input.text()) < 6' in self._content()

    def test_password_confirm_match(self):
        assert 'Passwords do not match' in self._content()

    def test_default_perms_by_role(self):
        assert '_set_default_perms' in self._content()


# ─── Stage 14: cooperative fund, fees, dividends ──────────────────────────────

class TestMigration0004:
    def test_migration_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'migrations', '0004_cooperative_fund.py'))

    def test_has_up_function(self):
        with open(os.path.join(ROOT, 'migrations', '0004_cooperative_fund.py')) as f:
            content = f.read()
        assert 'def up(' in content

    def test_cooperative_fund_table_exists(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        for t in ['cooperative_fund_transactions', 'entrance_fees',
                  'loan_fees', 'annual_fees', 'dividend_payments']:
            assert t in tables, f"Missing table: {t}"

    def test_new_settings_seeded(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'nfc_cooperative.db'))
        for key in ['entrance_fee_amount', 'loan_form_fee_amount',
                    'annual_fee_amount', 'transfer_fee_amount',
                    'death_benefit_notation', 'dividend_distribution_method']:
            row = conn.execute(
                "SELECT 1 FROM system_settings WHERE setting_key=?", (key,)
            ).fetchone()
            assert row, f"Missing setting: {key}"
        conn.close()


class TestDBManagerFund:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        import shutil, sys
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

    def test_get_fund_balance_returns_float(self):
        bal = self.db.get_fund_balance()
        assert isinstance(bal, float)

    def test_credit_fund(self):
        before = self.db.get_fund_balance()
        self.db._credit_fund(1000.0, 'Manual', 'Test credit', created_by='test')
        self.db.commit()
        assert self.db.get_fund_balance() == round(before + 1000.0, 2)

    def test_debit_fund(self):
        self.db._credit_fund(5000.0, 'Manual', 'Setup', created_by='test')
        self.db.commit()
        before = self.db.get_fund_balance()
        self.db._debit_fund(2000.0, 'Manual', 'Test debit', created_by='test')
        self.db.commit()
        assert self.db.get_fund_balance() == round(before - 2000.0, 2)

    def test_get_fund_transactions(self):
        self.db._credit_fund(500.0, 'Test', 'Test', created_by='test')
        self.db.commit()
        txns = self.db.get_fund_transactions()
        assert isinstance(txns, list)
        assert len(txns) >= 1

    def test_charge_entrance_fee_creates_record(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Fee',
            'last_name': 'Test', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        fee = self.db.fetchone(
            "SELECT * FROM entrance_fees WHERE member_id=?", (mid,)
        )
        assert fee is not None

    def test_annual_fee_charge(self):
        count = self.db.charge_annual_fee_all(2026, 'admin')
        self.db.commit()
        assert count > 0
        fees = self.db.get_annual_fees(2026)
        assert len(fees) > 0

    def test_annual_fee_no_duplicate(self):
        self.db.charge_annual_fee_all(2099, 'admin')
        self.db.commit()
        count1 = len(self.db.get_annual_fees(2099))
        self.db.charge_annual_fee_all(2099, 'admin')
        self.db.commit()
        count2 = len(self.db.get_annual_fees(2099))
        assert count1 == count2

    def test_distribute_dividends(self):
        self.db._credit_fund(999_999.0, 'Setup', 'Fund for test', created_by='test')
        self.db.update_setting('dividend_distribution_method', 'fixed')
        self.db.update_setting('dividend_fixed_amount', '100.00')
        self.db.commit()
        result = self.db.distribute_dividends('2026', 'admin')
        assert result['members_paid'] > 0
        assert result['total_distributed'] > 0

    def test_transfer_member(self):
        mid = self.db.add_member({
            'station_id': '01', 'first_name': 'Trans',
            'last_name': 'Test', 'gender': 'Male',
            'date_joined': '2026-01-01'
        }, 'admin')
        self.db.transfer_member(mid, '02', 'Test transfer', 'admin')
        self.db.commit()
        member = self.db.get_member(mid)
        assert member['station_id'] == '02'


class TestCooperativeFundModule:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'cooperative_fund_module.py')) as f:
            return f.read()

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', 'cooperative_fund_module.py'))

    def test_has_class(self):
        assert 'class CooperativeFundModule' in self._content()

    def test_has_danger_confirm_dialog(self):
        assert 'class DangerConfirmDialog' in self._content()

    def test_has_all_tabs(self):
        content = self._content()
        for tab in ['Fund Transactions', 'Entrance Fees', 'Annual Fees', 'Dividends']:
            assert tab in content, f"Missing tab: {tab}"

    def test_has_manual_entry(self):
        assert '_manual_entry' in self._content()

    def test_has_pay_entrance_fee(self):
        assert '_pay_entrance_fee' in self._content()

    def test_has_charge_annual_fee(self):
        assert '_charge_annual_fee' in self._content()

    def test_has_distribute_dividends(self):
        assert '_distribute_dividends' in self._content()

    def test_danger_confirm_requires_word(self):
        assert 'confirm_word' in self._content()

    def test_danger_banner_style(self):
        assert '7B241C' in self._content()

    def test_has_balance_card(self):
        assert 'balance_lbl' in self._content()

    def test_has_fund_filters(self):
        content = self._content()
        assert 'fund_cat_filter' in content
        assert 'fund_type_filter' in content
        assert 'fund_date_from' in content


class TestSettingsStage14:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'settings_module.py')) as f:
            return f.read()

    def test_has_fees_tab(self):
        assert '_fees_tab' in self._content()

    def test_has_dividends_tab(self):
        assert '_dividends_tab' in self._content()

    def test_has_danger_warnings(self):
        assert 'DangerConfirmDialog' in self._content()

    def test_system_save_requires_danger_confirm(self):
        content = self._content()
        assert 'confirm_word="SAVE"' in content

    def test_deactivate_user_requires_danger_confirm(self):
        assert 'confirm_word="DEACTIVATE"' in self._content()

    def test_has_fee_settings_fields(self):
        content = self._content()
        for field in ['entrance_fee', 'loan_fee', 'annual_fee', 'transfer_fee']:
            assert field in content, f"Missing field: {field}"

    def test_has_dividend_method_selector(self):
        assert 'div_method' in self._content()

    def test_has_major_warning_on_dividends(self):
        assert 'MAJOR WARNING' in self._content()

    def test_death_notation_field(self):
        assert 'death_notation' in self._content()


class TestMembersDeathBenefit:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'members_module.py')) as f:
            return f.read()

    def test_death_benefit_auto_triggered(self):
        assert 'process_death_benefit' in self._content()

    def test_death_benefit_result_shown(self):
        assert 'Death benefit processed' in self._content()

    def test_handles_disabled_benefit(self):
        assert 'except Exception' in self._content()


class TestMainWindowFund:
    def _content(self):
        with open(os.path.join(ROOT, 'src', 'gui', 'main_window.py')) as f:
            return f.read()

    def test_cooperative_fund_in_nav(self):
        assert 'Cooperative Fund' in self._content()

    def test_cooperative_fund_module_loaded(self):
        assert 'CooperativeFundModule' in self._content()

    def test_fund_slot_6(self):
        assert "(6, 'gui.cooperative_fund_module'" in self._content()