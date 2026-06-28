# NFC-Cooperative.spec
# PyInstaller build spec for the NFC Cooperative Management System.
#
# Usage (from the nfc\ directory):
#   pyinstaller NFC-Cooperative.spec --noconfirm

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

block_cipher = None

# Collect everything PyQt6 ships — binaries, datas, and hidden imports.
qt_datas, qt_binaries, qt_hiddenimports = collect_all('PyQt6')

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT), str(ROOT / 'src')],
    binaries=qt_binaries,
    datas=qt_datas + [
        # Seed database
        (str(ROOT / 'data' / 'nfc_cooperative.db'), 'data'),
        # Fonts for ReportLab
        (str(ROOT / 'data' / 'fonts'), 'data/fonts'),
        # Migration scripts loaded at runtime via importlib
        (str(ROOT / 'migrations' / '*.py'), 'migrations'),
        # Bundle entire src/ tree so importlib.import_module('gui.x') works frozen
        (str(ROOT / 'src'), 'src'),
    ],
    hiddenimports=qt_hiddenimports + collect_submodules('gui') + collect_submodules('database') + collect_submodules('utils') + [
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
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'dateutil',
        'dateutil.relativedelta',
        'bcrypt',
        'sqlite3',
        'importlib.util',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / 'hooks' / 'rthook_src_path.py')],
    excludes=[
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'difflib',
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'app.ico') if (ROOT / 'assets' / 'app.ico').exists() else None,
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
