# Runtime hook: add the src/ directory to sys.path when running frozen.
# main.py does this for dev mode via sys.path.insert, but PyInstaller
# bundles src/ as a flat package — we need to tell the importer where to find it.
import sys
import os

if getattr(sys, 'frozen', False):
    src_path = os.path.join(sys._MEIPASS, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)