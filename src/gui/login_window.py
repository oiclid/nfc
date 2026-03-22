from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class LoginWindow(QWidget):
    login_successful = pyqtSignal(dict)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("NFC Cooperative — Login")
        self.setFixedSize(480, 540)
        self.setWindowFlags(
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 44, 48, 36)
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

        root.addSpacing(4)

        version = QLabel("Version 2.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        root.addWidget(version)

        root.addSpacing(32)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border: none; border-top: 1px solid #3D3D42;")
        root.addWidget(line)

        root.addSpacing(28)

        # Username
        user_lbl = QLabel("Username")
        user_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        root.addWidget(user_lbl)

        root.addSpacing(6)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(40)
        self.username_input.returnPressed.connect(self._on_login)
        root.addWidget(self.username_input)

        root.addSpacing(16)

        # Password
        pw_lbl = QLabel("Password")
        pw_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        root.addWidget(pw_lbl)

        root.addSpacing(6)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(40)
        self.password_input.returnPressed.connect(self._on_login)
        root.addWidget(self.password_input)

        root.addSpacing(28)

        # Login button
        self.login_btn = QPushButton("LOGIN")
        self.login_btn.setFixedHeight(44)
        self.login_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980B9; border: none;
                border-radius: 4px; color: white; font-weight: 600;
            }
            QPushButton:hover   { background-color: #3498DB; }
            QPushButton:pressed { background-color: #21618C; }
        """)
        self.login_btn.clicked.connect(self._on_login)
        root.addWidget(self.login_btn)

        root.addStretch()

        footer = QLabel("© 2026 Nigerian Film Corporation. All rights reserved.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        root.addWidget(footer)

        self.username_input.setFocus()

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Login Failed",
                                "Please enter both username and password.")
            return

        try:
            user = self.app.db_manager.authenticate_user(username, password)
            if user:
                self.login_successful.emit(user)
            else:
                QMessageBox.warning(self, "Login Failed",
                                    "Invalid username or password.")
                self.password_input.clear()
                self.password_input.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Login Error",
                                 f"An error occurred:\n{e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            pass  # block Esc on login screen
        else:
            super().keyPressEvent(event)