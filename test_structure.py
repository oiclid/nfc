"""
Structural tests — grow with each stage.
Run with: pytest test_structure.py -v
"""
import os
import sys
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
    def _exists(self, *parts):
        return os.path.isfile(os.path.join(ROOT, *parts))

    def _isdir(self, *parts):
        return os.path.isdir(os.path.join(ROOT, *parts))

    def test_src_dir(self):
        assert self._isdir('src')

    def test_src_database_dir(self):
        assert self._isdir('src', 'database')

    def test_src_gui_dir(self):
        assert self._isdir('src', 'gui')

    def test_src_reports_dir(self):
        assert self._isdir('src', 'reports')

    def test_src_utils_dir(self):
        assert self._isdir('src', 'utils')


class TestInitFiles:
    def _exists(self, *parts):
        return os.path.isfile(os.path.join(ROOT, *parts))

    def test_src_init(self):
        assert self._exists('src', '__init__.py')

    def test_database_init(self):
        assert self._exists('src', 'database', '__init__.py')

    def test_gui_init(self):
        assert self._exists('src', 'gui', '__init__.py')

    def test_reports_init(self):
        assert self._exists('src', 'reports', '__init__.py')

    def test_utils_init(self):
        assert self._exists('src', 'utils', '__init__.py')


class TestDatabaseStubs:
    def _exists(self, *parts):
        return os.path.isfile(os.path.join(ROOT, *parts))

    def test_db_manager_exists(self):
        assert self._exists('src', 'database', 'db_manager.py')

    def test_migrations_runner_exists(self):
        assert self._exists('src', 'database', 'migrations.py')


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
    def _exists(self, *parts):
        return os.path.isfile(os.path.join(ROOT, *parts))

    def test_report_generator_exists(self):
        assert self._exists('src', 'reports', 'report_generator.py')

    def test_utils_init_exists(self):
        assert self._exists('src', 'utils', '__init__.py')


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
        count = conn.execute(
            "SELECT COUNT(*) FROM MemberDataTbl"
        ).fetchone()[0]
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