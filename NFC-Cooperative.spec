# NFC-Cooperative.spec
# PyInstaller build spec for the NFC Cooperative Management System.
#
# Usage (from the nfc\ directory):
#   pyinstaller NFC-Cooperative.spec --noconfirm
#
# Or via the build script:
#   .\build.ps1 -Installer

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT), str(ROOT / 'src')],
    binaries=[],
    datas=[
        # Seed database — copied to %APPDATA%\NFC-Cooperative on first launch
        (str(ROOT / 'data' / 'nfc_cooperative.db'), 'data'),
        # Fonts used by ReportLab for PDF generation
        (str(ROOT / 'data' / 'fonts'), 'data/fonts'),
        # Migration scripts — loaded at runtime via importlib
        (str(ROOT / 'migrations' / '*.py'), 'migrations'),
        (str(ROOT / 'migrations' / 'migrate.py'), 'migrations'),
    ],
    hiddenimports=[
        # reportlab registers fonts and codecs dynamically
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.colors',
        'reportlab.lib.enums',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.pdfbase',
        'reportlab.pdfbase.pdfmetrics',
        'reportlab.pdfbase.ttfonts',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        'reportlab.platypus',
        'reportlab.platypus.tables',
        'reportlab.platypus.paragraph',
        'reportlab.platypus.flowables',
        # openpyxl uses pkg_resources for its templates
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        # dateutil
        'dateutil',
        'dateutil.relativedelta',
        # bcrypt uses cffi
        'bcrypt',
        'cffi',
        '_cffi_backend',
        # SQLite + importlib used to load migration files at runtime
        'sqlite3',
        'importlib.util',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Keep the bundle lean
        'tkinter',
        'unittest',
        'email',
        'html',
        'http',
        'urllib',
        'xmlrpc',
        'xml',
        'pydoc',
        'doctest',
        'difflib',
        'ftplib',
        'getpass',
        'getopt',
        'calendar',
        'cgi',
        'csv',       # not used directly
        'curses',
        'antigravity',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NFC-Cooperative',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'app.ico') if (ROOT / 'assets' / 'app.ico').exists() else None,
    version=str(ROOT / 'assets' / 'version.txt') if (ROOT / 'assets' / 'version.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NFC-Cooperative',
)
