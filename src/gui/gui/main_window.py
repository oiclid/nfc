from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMessageBox,
    QStatusBar, QMenuBar, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction
from datetime import datetime


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app          = app
        self.current_user = app.current_user
        self.db           = app.db_manager
        self._modules     = []
        self._nav_buttons = []

        self._setup_ui()
        self._setup_menu()
        self._load_modules()
        self._update_status()

        self._clock = QTimer(self)
        self._clock.timeout.connect(self._update_status)
        self._clock.start(1000)

    # -------------------------------------------------------------------------
    # UI setup
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle("NFC Cooperative Management System")
        self.setMinimumSize(1024, 640)

        screen = self.screen().availableGeometry()
        if screen.width() >= 1366:
            self.showMaximized()
        else:
            self.resize(int(screen.width() * 0.95), int(screen.height() * 0.95))
            self.move(
                screen.x() + (screen.width()  - self.width())  // 2,
                screen.y() + (screen.height() - self.height()) // 2,
            )

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("""
            QWidget {
                background-color: #2D2D32;
                border-bottom: 2px solid #2980B9;
            }
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 8, 20, 8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t1 = QLabel("NFC Cooperative")
        t1.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #2980B9; border: none;")
        t2 = QLabel("Management System")
        t2.setFont(QFont("Segoe UI", 9))
        t2.setStyleSheet("color: #BDC3C7; border: none;")
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        layout.addLayout(title_col)
        layout.addStretch()

        user_col = QVBoxLayout()
        user_col.setSpacing(2)
        user_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        u1 = QLabel(self.current_user['username'])
        u1.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        u1.setStyleSheet("color: #E6E6EB; border: none;")
        u2 = QLabel(self.current_user['role'])
        u2.setFont(QFont("Segoe UI", 9))
        u2.setStyleSheet("color: #BDC3C7; border: none;")
        user_col.addWidget(u1)
        user_col.addWidget(u2)
        layout.addLayout(user_col)

        return header

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #2D2D32;
                border-right: 1px solid #3D3D42;
            }
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        u = self.current_user
        nav_items = [("Dashboard", 0)]

        if u['can_maintain']:
            nav_items.append(("Stations",     1))
            nav_items.append(("Members",      2))

        if u['can_operate']:
            nav_items.append(("Savings",          3))
            nav_items.append(("Loans",            4))
            nav_items.append(("Transactions",     5))
            nav_items.append(("Cooperative Fund", 6))

        if u['can_view_reports']:
            nav_items.append(("Reports",          7))

        if u['can_maintain']:
            nav_items.append(("Settings",         8))

        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    color: #BDC3C7;
                    text-align: left;
                    padding-left: 20px;
                }
                QPushButton:hover {
                    background-color: #3D3D42;
                    color: #E6E6EB;
                }
                QPushButton:checked {
                    background-color: #1E1E23;
                    border-left: 3px solid #2980B9;
                    color: #3498DB;
                    font-weight: 600;
                }
            """)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            layout.addWidget(btn)
            self._nav_buttons.append((idx, btn))

        layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #3D3D42; margin: 0 10px;")
        layout.addWidget(sep)

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedHeight(44)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setFont(QFont("Segoe UI", 10))
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                color: #E74C3C;
                text-align: left;
                padding-left: 20px;
                margin: 4px 0;
            }
            QPushButton:hover {
                background-color: #3D3D42;
                color: #FF6B6B;
            }
        """)
        logout_btn.clicked.connect(self._logout)
        layout.addWidget(logout_btn)

        return sidebar

    # -------------------------------------------------------------------------
    # Module loading
    # -------------------------------------------------------------------------

    def _load_modules(self):
        u = self.current_user

        def _try_load(module_path, class_name, slot):
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                return cls(self.app, self)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return self._placeholder(slot, str(e))

        slot_defs = [
            (0, 'gui.dashboard_module',         'DashboardModule',         True),
            (1, 'gui.stations_module',           'StationsModule',          u['can_maintain']),
            (2, 'gui.members_module',            'MembersModule',           u['can_maintain']),
            (3, 'gui.savings_module',            'SavingsModule',           u['can_operate']),
            (4, 'gui.loans_module',              'LoansModule',             u['can_operate']),
            (5, 'gui.transactions_module',       'TransactionsModule',      u['can_operate']),
            (6, 'gui.cooperative_fund_module',   'CooperativeFundModule',   u['can_operate']),
            (7, 'gui.reports_module',            'ReportsModule',           u['can_view_reports']),
            (8, 'gui.settings_module',           'SettingsModule',          u['can_maintain']),
        ]

        for slot, module_path, class_name, allowed in slot_defs:
            if not allowed:
                continue
            widget = _try_load(module_path, class_name, slot)
            self.stack.addWidget(widget)
            self._modules.append((slot, widget))

        # activate dashboard
        self._switch(0)

    def _placeholder(self, slot: int, error: str = "") -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if error:
            lbl = QLabel(f"Module {slot} failed to load:\n{error}")
            lbl.setStyleSheet("color: #E74C3C; font-size: 11pt;")
        else:
            lbl = QLabel(f"Module {slot} — coming soon")
            lbl.setStyleSheet("color: #7F8C8D; font-size: 14pt;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)
        return w

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def _switch(self, target_slot: int):
        # find the stack index for this slot
        for i, (slot, widget) in enumerate(self._modules):
            if slot == target_slot:
                self.stack.setCurrentIndex(i)
                if hasattr(widget, 'refresh'):
                    try:
                        widget.refresh()
                    except Exception:
                        pass
                break

        # update nav button states
        for slot, btn in self._nav_buttons:
            btn.setChecked(slot == target_slot)

    def switch_to(self, slot: int):
        """Public — called by dashboard quick actions."""
        self._switch(slot)

    # -------------------------------------------------------------------------
    # Menu
    # -------------------------------------------------------------------------

    def _setup_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        refresh = QAction("&Refresh", self)
        refresh.setShortcut("F5")
        refresh.triggered.connect(self._refresh_current)
        file_menu.addAction(refresh)
        file_menu.addSeparator()
        exit_act = QAction("E&xit", self)
        exit_act.setShortcut("Alt+F4")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        help_menu = mb.addMenu("&Help")
        about = QAction("&About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _refresh_current(self):
        idx = self.stack.currentIndex()
        if idx < len(self._modules):
            _, widget = self._modules[idx]
            if hasattr(widget, 'refresh'):
                try:
                    widget.refresh()
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Status bar
    # -------------------------------------------------------------------------

    def _update_status(self):
        now = datetime.now()
        self.status_bar.showMessage(
            f"  {now.strftime('%A, %B %d, %Y')}  |  "
            f"{now.strftime('%I:%M:%S %p')}  |  "
            f"User: {self.current_user['username']} "
            f"({self.current_user['role']})"
        )

    # -------------------------------------------------------------------------
    # Logout / close
    # -------------------------------------------------------------------------

    def _logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            from gui.login_window import LoginWindow
            self.app.login_window = LoginWindow(self.app)
            self.app.login_window.login_successful.connect(self.app._on_login_success)
            self.app.login_window.show()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._clock.stop()
            event.accept()
        else:
            event.ignore()

    def _show_about(self):
        QMessageBox.about(
            self, "About NFC Cooperative System",
            "<h2>NFC Cooperative Management System</h2>"
            "<p><b>Version:</b> 2.0.0</p>"
            "<p><b>Organisation:</b> Nigerian Film Corporation</p>"
            "<p><b>Description:</b> Cooperative management for savings, "
            "loans, and financial operations.</p>"
            "<hr><p><small>© 2026 Nigerian Film Corporation.</small></p>"
        )