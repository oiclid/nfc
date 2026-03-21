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