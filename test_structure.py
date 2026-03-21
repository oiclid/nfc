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


# ─── Stage 1 Step 2: entry point ─────────────────────────────────────────────

class TestEntryPoint:
    def test_main_py_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'main.py'))

    def test_migrations_dir_exists(self):
        assert os.path.isdir(os.path.join(ROOT, 'migrations'))


# ─── Stage 1 Steps 3-5: stubs ────────────────────────────────────────────────

class TestDirectoryStructure:
    def test_src_dir(self):
        assert os.path.isdir(os.path.join(ROOT, 'src'))

    def test_src_database_dir(self):
        assert os.path.isdir(os.path.join(ROOT, 'src', 'database'))

    def test_src_gui_dir(self):
        assert os.path.isdir(os.path.join(ROOT, 'src', 'gui'))

    def test_src_reports_dir(self):
        assert os.path.isdir(os.path.join(ROOT, 'src', 'reports'))

    def test_src_utils_dir(self):
        assert os.path.isdir(os.path.join(ROOT, 'src', 'utils'))


class TestInitFiles:
    def test_src_init(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', '__init__.py'))

    def test_database_init(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'database', '__init__.py'))

    def test_gui_init(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'gui', '__init__.py'))

    def test_reports_init(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'reports', '__init__.py'))

    def test_utils_init(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'utils', '__init__.py'))


class TestDatabaseStubs:
    def test_db_manager_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'database', 'db_manager.py'))

    def test_migrations_runner_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'database', 'migrations.py'))


class TestGUIStubs:
    MODULES = [
        'login_window',
        'setup_wizard',
        'main_window',
        'dashboard_module',
        'stations_module',
        'members_module',
        'savings_module',
        'loans_module',
        'transactions_module',
        'reports_module',
        'settings_module',
    ]

    @pytest.mark.parametrize('module', MODULES)
    def test_gui_stub_exists(self, module):
        path = os.path.join(ROOT, 'src', 'gui', f'{module}.py')
        assert os.path.isfile(path), f"Missing: src/gui/{module}.py"


class TestReportsAndUtilsStubs:
    def test_report_generator_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'reports', 'report_generator.py'))

    def test_utils_init_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'src', 'utils', '__init__.py'))


# ─── Legacy DB readable ───────────────────────────────────────────────────────

class TestLegacyDatabase:
    def test_legacy_db_exists(self):
        assert os.path.isfile(os.path.join(ROOT, 'data', 'database.sld'))

    def test_can_open_legacy_db(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert len(tables) > 0

    def test_member_table_exists(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert 'MemberDataTbl' in tables

    def test_member_count_is_327(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        count = conn.execute("SELECT COUNT(*) FROM MemberDataTbl").fetchone()[0]
        conn.close()
        assert count == 327

    def test_station_table_exists(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert 'StationDB' in tables

    def test_loans_table_exists(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert 'LoansAndPurchasesTbl' in tables

    def test_ledger_table_exists(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert 'LedgerTbl' in tables

    def test_login_table_exists(self):
        conn = sqlite3.connect(os.path.join(ROOT, 'data', 'database.sld'))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert 'LoginTbl' in tables


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