"""
Resolves DB and migrations paths for both dev and packaged (PyInstaller) modes.

Dev mode   : paths are relative to project root
Packaged   : DB lives in %APPDATA%/NFC-Cooperative so reinstalls never
             overwrite the live database. Seed DB is copied on first launch.
"""
import os
import sys
import shutil

APP_NAME = 'NFC-Cooperative'


def get_db_path() -> str:
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
        app_dir = os.path.join(appdata, APP_NAME)
        os.makedirs(app_dir, exist_ok=True)
        live_db = os.path.join(app_dir, 'nfc_cooperative.db')
        if not os.path.isfile(live_db):
            seed = os.path.join(sys._MEIPASS, 'data', 'nfc_cooperative.db')
            shutil.copy2(seed, live_db)
        return live_db
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, 'data', 'nfc_cooperative.db')


def get_migrations_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'migrations')
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, 'migrations')
