from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFileDialog, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import os
import shutil


class SetupWizard(QWidget):
    setup_complete = pyqtSignal(dict)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("NFC Cooperative — First Time Setup")
        self.setFixedSize(500, 580)
        self.setWindowFlags(
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        self.stack = QStackedWidget(self)
        self.stack.setGeometry(0, 0, 500, 580)

        self.stack.addWidget(self._build_choice_page())   # page 0
        self.stack.addWidget(self._build_admin_page())    # page 1
        self.stack.setCurrentIndex(0)

    # -------------------------------------------------------------------------
    # Page 0 — Import or Fresh Start
    # -------------------------------------------------------------------------

    def _build_choice_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(48, 40, 48, 36)
        root.setSpacing(0)

        self._add_header(root, "First-Time Setup")

        root.addSpacing(16)

        info = QLabel(
            "No database found. Would you like to import an existing\n"
            "database or start with a fresh installation?"
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet(
            "background-color: #1A2A3A; border: 1px solid #2980B9;"
            "border-radius: 6px; padding: 10px; color: #A8C8E8; font-size: 10pt;"
        )
        root.addWidget(info)

        root.addSpacing(40)

        # Import button
        btn_import = QPushButton("Import Existing Database")
        btn_import.setFixedHeight(56)
        btn_import.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: #2980B9; border: none;
                border-radius: 4px; color: white;
            }
            QPushButton:hover   { background-color: #3498DB; }
            QPushButton:pressed { background-color: #1F6699; }
        """)
        btn_import.clicked.connect(self._on_import)
        root.addWidget(btn_import)

        root.addSpacing(4)

        import_hint = QLabel("Browse for an existing nfc_cooperative.db file")
        import_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        import_hint.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        root.addWidget(import_hint)

        root.addSpacing(24)

        # Divider
        divider = QLabel("— or —")
        divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        divider.setStyleSheet("color: #5D6D7E; font-size: 10pt;")
        root.addWidget(divider)

        root.addSpacing(24)

        # Fresh start button
        btn_fresh = QPushButton("Start Fresh Installation")
        btn_fresh.setFixedHeight(56)
        btn_fresh.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_fresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fresh.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; border: none;
                border-radius: 4px; color: white;
            }
            QPushButton:hover   { background-color: #2ECC71; }
            QPushButton:pressed { background-color: #1E8449; }
        """)
        btn_fresh.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        root.addWidget(btn_fresh)

        root.addSpacing(4)

        fresh_hint = QLabel("Create a new administrator account and empty database")
        fresh_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fresh_hint.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        root.addWidget(fresh_hint)

        root.addStretch()
        root.addWidget(self._footer())
        return page

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database File",
            "",
            "SQLite Database (nfc_cooperative.db);;All Files (*)"
        )
        if not path:
            return

        from utils.app_paths import get_db_path
        dest = get_db_path()

        try:
            shutil.copy2(path, dest)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not copy database:\n{e}")
            return

        # Reload db_manager against the imported DB
        try:
            from database.db_manager import DatabaseManager
            self.app.db_manager.close()
            self.app.db_manager = DatabaseManager(dest)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not open imported database:\n{e}")
            return

        # Run any pending migrations on the imported DB
        try:
            from database.migrations import run as run_migrations
            from utils.app_paths import get_migrations_dir
            run_migrations(dest, get_migrations_dir())
            self.app.db_manager.close()
            self.app.db_manager = DatabaseManager(dest)
        except Exception as e:
            QMessageBox.warning(self, "Migration Warning", f"Migrations had issues:\n{e}")

        users = self.app.db_manager.get_all_users()
        if users:
            # Imported DB has users — go straight to login
            self.close()
            self.app._show_login()
        else:
            # Imported DB has no users — still need admin account
            QMessageBox.information(
                self, "Database Imported",
                "Database imported successfully.\n"
                "No user accounts found — please create an administrator."
            )
            self.stack.setCurrentIndex(1)

    # -------------------------------------------------------------------------
    # Page 1 — Create Administrator
    # -------------------------------------------------------------------------

    def _build_admin_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(48, 40, 48, 36)
        root.setSpacing(0)

        self._add_header(root, "Create Administrator")

        root.addSpacing(16)

        info = QLabel(
            "No user accounts found. Create the initial administrator\n"
            "account to get started."
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet(
            "background-color: #1A2A3A; border: 1px solid #2980B9;"
            "border-radius: 6px; padding: 10px; color: #A8C8E8; font-size: 10pt;"
        )
        root.addWidget(info)

        root.addSpacing(24)

        for attr, label, placeholder, is_pw in [
            ('fullname_input', 'Full Name',       'e.g. John Adeyemi',      False),
            ('username_input', 'Username',         'Choose a login username', False),
            ('password_input', 'Password',         'Minimum 6 characters',   True),
            ('confirm_input',  'Confirm Password', 'Re-enter password',      True),
        ]:
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            root.addWidget(lbl)
            root.addSpacing(5)

            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            field.setFixedHeight(40)
            if is_pw:
                field.setEchoMode(QLineEdit.EchoMode.Password)
            setattr(self, attr, field)
            root.addWidget(field)
            root.addSpacing(14)

        self.confirm_input.returnPressed.connect(self._on_submit)

        # Back button + Submit button
        root.addSpacing(8)
        btn_row = QHBoxLayout()

        btn_back = QPushButton("← Back")
        btn_back.setFixedHeight(46)
        btn_back.setFont(QFont("Segoe UI", 10))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #2D2D32; border: 1px solid #3D3D42;
                border-radius: 4px; color: #E6E6EB;
            }
            QPushButton:hover { background-color: #3D3D42; }
        """)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_row.addWidget(btn_back, 1)

        btn_row.addSpacing(12)

        btn_submit = QPushButton("Create Administrator Account")
        btn_submit.setFixedHeight(46)
        btn_submit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; border: none;
                border-radius: 4px; color: white; font-weight: 600;
            }
            QPushButton:hover   { background-color: #2ECC71; }
            QPushButton:pressed { background-color: #1E8449; }
        """)
        btn_submit.clicked.connect(self._on_submit)
        btn_row.addWidget(btn_submit, 2)

        root.addLayout(btn_row)
        root.addStretch()
        root.addWidget(self._footer())
        return page

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _add_header(self, layout, badge_text: str):
        org = QLabel("Nigerian Film Corporation")
        org.setAlignment(Qt.AlignmentFlag.AlignCenter)
        org.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        org.setStyleSheet("color: #2980B9;")
        layout.addWidget(org)

        layout.addSpacing(4)

        title = QLabel("Cooperative Management System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addSpacing(8)

        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "background-color: #2980B9; color: white; border-radius: 4px;"
            "padding: 4px 12px; font-size: 10pt; font-weight: 600;"
        )
        badge.setFixedHeight(28)
        layout.addWidget(badge)

    def _footer(self):
        footer = QLabel("© 2026 Nigerian Film Corporation. All rights reserved.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        return footer

    def _on_submit(self):
        fullname = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm  = self.confirm_input.text()

        if not fullname:
            return self._warn("Full name is required.")
        if len(username) < 3:
            return self._warn("Username must be at least 3 characters.")
        if len(password) < 6:
            return self._warn("Password must be at least 6 characters.")
        if password != confirm:
            self.confirm_input.clear()
            self.password_input.setFocus()
            return self._warn("Passwords do not match.")

        try:
            uid = self.app.db_manager.create_user(
                {
                    'username':         username,
                    'password':         password,
                    'full_name':        fullname,
                    'role':             'Admin',
                    'can_maintain':     1,
                    'can_operate':      1,
                    'can_edit':         1,
                    'can_view_reports': 1,
                },
                created_by='setup'
            )
            user = self.app.db_manager.get_user_by_id(uid)
            self.setup_complete.emit(user)
        except Exception as e:
            self._warn(f"Failed to create account:\n{e}")

    def _warn(self, msg: str):
        QMessageBox.warning(self, "Setup Error", msg)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            pass  # cannot skip first-launch setup
        else:
            super().keyPressEvent(event)