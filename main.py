import sys
import os

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from gui.login_window import LoginWindow
from gui.setup_wizard import SetupWizard
from database.db_manager import DatabaseManager
from database.migrations import run as run_migrations
from utils.app_paths import get_db_path, get_migrations_dir

DB_PATH        = get_db_path()
MIGRATIONS_DIR = get_migrations_dir()


class NFCApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("NFC Cooperative Management System")
        self.setOrganizationName("Nigerian Film Corporation")
        self.setApplicationVersion("2.0.0")
        self.setStyle("Fusion")
        self._apply_theme()

        self.db_manager   = None
        self.current_user = None
        self.main_window  = None

        self._init_db()
        self._run_migrations()

        if not self.db_manager.get_all_users():
            self._show_wizard()
        else:
            self._show_login()

    # -------------------------------------------------------------------------

    def _init_db(self):
        if not os.path.isfile(DB_PATH):
            QMessageBox.critical(
                None, "Database Error",
                f"Database not found:\n{DB_PATH}\n\n"
                "Run the migration script first:\n"
                "  python migrations/migrate.py"
            )
            sys.exit(1)
        try:
            self.db_manager = DatabaseManager(DB_PATH)
        except Exception as e:
            QMessageBox.critical(None, "Database Error",
                                 f"Failed to open database:\n{e}")
            sys.exit(1)

    def _run_migrations(self):
        try:
            applied = run_migrations(DB_PATH, MIGRATIONS_DIR)
            if applied:
                self.db_manager.close()
                self.db_manager = DatabaseManager(DB_PATH)
        except RuntimeError as e:
            QMessageBox.critical(None, "Migration Failed",
                                 f"A required migration failed:\n\n{e}")
            sys.exit(1)

    def _show_wizard(self):
        self.wizard = SetupWizard(self)
        self.wizard.setup_complete.connect(self._on_setup_complete)
        self.wizard.show()

    def _show_login(self):
        self.login_window = LoginWindow(self)
        self.login_window.login_successful.connect(self._on_login_success)
        self.login_window.show()

    def _on_setup_complete(self, user: dict):
        self.current_user = user
        self.wizard.close()
        self._load_main_window()

    def _on_login_success(self, user: dict):
        self.current_user = user
        self.login_window.close()
        self._load_main_window()

    def _load_main_window(self):
        from gui.main_window import MainWindow
        self.main_window = MainWindow(self)
        self.main_window.show()

    # -------------------------------------------------------------------------

    def _apply_theme(self):
        palette = QPalette()
        dark_bg    = QColor(30, 30, 35)
        darker_bg  = QColor(20, 20, 25)
        light_bg   = QColor(45, 45, 50)
        text_color = QColor(230, 230, 235)
        accent     = QColor(41, 128, 185)

        palette.setColor(QPalette.ColorRole.Window,          dark_bg)
        palette.setColor(QPalette.ColorRole.WindowText,      text_color)
        palette.setColor(QPalette.ColorRole.Base,            darker_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase,   light_bg)
        palette.setColor(QPalette.ColorRole.ToolTipBase,     darker_bg)
        palette.setColor(QPalette.ColorRole.ToolTipText,     text_color)
        palette.setColor(QPalette.ColorRole.Text,            text_color)
        palette.setColor(QPalette.ColorRole.Button,          light_bg)
        palette.setColor(QPalette.ColorRole.ButtonText,      text_color)
        palette.setColor(QPalette.ColorRole.BrightText,      Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Link,            accent)
        palette.setColor(QPalette.ColorRole.Highlight,       accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        self.setPalette(palette)
        self.setFont(QFont("Segoe UI", 10))

        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E23; }
            QPushButton {
                background-color: #2D2D32; border: 1px solid #3D3D42;
                border-radius: 4px; padding: 8px 16px;
                color: #E6E6EB; font-weight: 500;
            }
            QPushButton:hover    { background-color: #3498DB; border-color: #3498DB; }
            QPushButton:pressed  { background-color: #2980B9; }
            QPushButton:disabled { background-color: #252529; color: #606066; border-color: #303035; }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #14141A; border: 1px solid #3D3D42;
                border-radius: 4px; padding: 6px; color: #E6E6EB;
            }
            QLineEdit:focus, QTextEdit:focus,
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #2980B9; }
            QTableWidget {
                background-color: #14141A; alternate-background-color: #1A1A20;
                border: 1px solid #3D3D42; gridline-color: #3D3D42;
            }
            QTableWidget::item          { padding: 8px; }
            QTableWidget::item:selected { background-color: #2980B9; }
            QHeaderView::section {
                background-color: #2D2D32; padding: 8px; border: none;
                border-right: 1px solid #3D3D42; border-bottom: 1px solid #3D3D42;
                font-weight: 600;
            }
            QTabWidget::pane { border: 1px solid #3D3D42; background-color: #1E1E23; }
            QTabBar::tab {
                background-color: #2D2D32; border: 1px solid #3D3D42;
                border-bottom: none; border-top-left-radius: 4px;
                border-top-right-radius: 4px; padding: 8px 16px; margin-right: 2px;
            }
            QTabBar::tab:selected { background-color: #1E1E23; border-bottom: 2px solid #2980B9; }
            QTabBar::tab:hover    { background-color: #3D3D42; }
            QMenuBar { background-color: #2D2D32; border-bottom: 1px solid #3D3D42; }
            QMenuBar::item              { padding: 8px 12px; background: transparent; }
            QMenuBar::item:selected     { background-color: #3D3D42; }
            QMenu { background-color: #2D2D32; border: 1px solid #3D3D42; }
            QMenu::item          { padding: 8px 24px; }
            QMenu::item:selected { background-color: #2980B9; }
            QStatusBar  { background-color: #2D2D32; border-top: 1px solid #3D3D42; }
            QGroupBox {
                border: 1px solid #3D3D42; border-radius: 4px;
                margin-top: 12px; padding-top: 12px; font-weight: 600;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QScrollBar:vertical {
                border: none; background-color: #1E1E23; width: 12px; border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3D3D42; border-radius: 6px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover    { background-color: #4D4D52; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical        { height: 0px; }
            QMessageBox { background-color: #1E1E23; }
        """)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = NFCApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()