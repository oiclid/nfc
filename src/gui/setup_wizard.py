from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


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

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 36)
        root.setSpacing(0)

        # Header
        org = QLabel("Nigerian Film Corporation")
        org.setAlignment(Qt.AlignmentFlag.AlignCenter)
        org.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        org.setStyleSheet("color: #2980B9;")
        root.addWidget(org)

        root.addSpacing(4)

        title = QLabel("Cooperative Management System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        root.addWidget(title)

        root.addSpacing(8)

        badge = QLabel("First-Time Setup")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "background-color: #2980B9; color: white; border-radius: 4px;"
            "padding: 4px 12px; font-size: 10pt; font-weight: 600;"
        )
        badge.setFixedHeight(28)
        root.addWidget(badge)

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

        # Form
        for attr, label, placeholder, is_pw in [
            ('fullname_input', 'Full Name',        'e.g. John Adeyemi',     False),
            ('username_input', 'Username',          'Choose a login username', False),
            ('password_input', 'Password',          'Minimum 6 characters',  True),
            ('confirm_input',  'Confirm Password',  'Re-enter password',     True),
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

        root.addSpacing(8)

        btn = QPushButton("Create Administrator Account")
        btn.setFixedHeight(46)
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; border: none;
                border-radius: 4px; color: white; font-weight: 600;
            }
            QPushButton:hover   { background-color: #2ECC71; }
            QPushButton:pressed { background-color: #1E8449; }
        """)
        btn.clicked.connect(self._on_submit)
        root.addWidget(btn)

        root.addStretch()

        footer = QLabel("© 2026 Nigerian Film Corporation. All rights reserved.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        root.addWidget(footer)

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