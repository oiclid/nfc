from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QComboBox, QTabWidget, QDoubleSpinBox, QCheckBox, QSpinBox,
    QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from gui.cooperative_fund_module import DangerConfirmDialog


class SettingsModule(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app  = app
        self.db   = app.db_manager
        self.user = app.current_user
        self._setup_ui()
        self.refresh()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._system_tab(),    "System")
        self.tabs.addTab(self._fees_tab(),      "Fees")
        self.tabs.addTab(self._dividends_tab(), "Dividends")
        self.tabs.addTab(self._users_tab(),     "Users")
        self.tabs.addTab(self._savings_tab(),   "Savings Types")
        self.tabs.addTab(self._loans_tab(),     "Loan Types")
        layout.addWidget(self.tabs)

    # -------------------------------------------------------------------------
    # System settings tab
    # -------------------------------------------------------------------------

    def _system_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        grp  = QGroupBox("Organisation & General")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.org_name    = QLineEdit(); self.org_name.setFixedHeight(36)
        self.currency    = QLineEdit(); self.currency.setFixedHeight(36)
        self.currency.setMaximumWidth(80)

        form.addRow("Organisation Name:", self.org_name)
        form.addRow("Currency Symbol:",   self.currency)
        layout.addWidget(grp)

        grp2  = QGroupBox("Benefits")
        form2 = QFormLayout(grp2)
        form2.setSpacing(12)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.death_enabled   = QCheckBox("Enable Death Benefit System")
        self.death_amount    = QDoubleSpinBox()
        self.death_amount.setFixedHeight(36)
        self.death_amount.setRange(0, 999_999_999)
        self.death_amount.setDecimals(2)
        self.death_amount.setSingleStep(500)

        self.retirement_pct  = QDoubleSpinBox()
        self.retirement_pct.setFixedHeight(36)
        self.retirement_pct.setRange(0, 100)
        self.retirement_pct.setDecimals(2)
        self.retirement_pct.setSuffix(" %")

        self.non_retire_pct  = QDoubleSpinBox()
        self.non_retire_pct.setFixedHeight(36)
        self.non_retire_pct.setRange(0, 100)
        self.non_retire_pct.setDecimals(2)
        self.non_retire_pct.setSuffix(" %")

        self.interest_auto   = QCheckBox("Auto-calculate monthly interest")

        form2.addRow("",                                    self.death_enabled)
        form2.addRow("Death Benefit Amount:",               self.death_amount)
        form2.addRow("Retirement Benefit (%):",             self.retirement_pct)
        form2.addRow("Non-Retirement Charge (%):",          self.non_retire_pct)
        form2.addRow("",                                    self.interest_auto)
        layout.addWidget(grp2)

        warn = QLabel("⚠  Changes to system settings affect all users and operations immediately.")
        warn.setWordWrap(True)
        warn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        warn.setStyleSheet("""
            QLabel {
                background-color: #7D6608;
                color: #FEF9E7;
                border: 1px solid #F1C40F;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(warn)

        save_btn = QPushButton("Save System Settings")
        save_btn.setFixedHeight(40)
        save_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980B9; color: white;
                border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #3498DB; }
        """)
        save_btn.clicked.connect(self._save_system_settings)
        layout.addWidget(save_btn)
        layout.addStretch()
        return w

    # -------------------------------------------------------------------------
    # Users tab
    # -------------------------------------------------------------------------


    def _fees_tab(self) -> QWidget:
        # Outer widget that fills the tab and holds the scroll area
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Inner scrollable widget
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 24)
        layout.setSpacing(20)

        warn = QLabel("⚠  Fee changes apply to ALL future operations. "
                      "Existing unpaid fees are not retroactively updated.")
        warn.setWordWrap(True)
        warn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        warn.setStyleSheet("""
            QLabel {
                background-color: #7D6608;
                color: #FEF9E7;
                border: 1px solid #F1C40F;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(warn)

        grp  = QGroupBox("Fee Configuration")
        form = QFormLayout(grp)
        form.setSpacing(16)
        form.setContentsMargins(16, 16, 16, 16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def fee_spin():
            s = QDoubleSpinBox()
            s.setFixedHeight(40)
            s.setRange(0, 999_999_999)
            s.setDecimals(2)
            s.setSingleStep(500)
            return s

        self.admission_fee    = fee_spin()
        self.readmission_fee  = fee_spin()
        self.withdrawal_fee   = fee_spin()
        self.death_charge     = fee_spin()
        self.retirement_fee   = fee_spin()
        self.loan_fee         = fee_spin()
        self.annual_fee       = fee_spin()
        self.transfer_fee     = fee_spin()
        self.other_income     = fee_spin()
        self.death_benefit    = fee_spin()

        form.addRow("Admission Fee:", self.admission_fee)
        form.addRow("Readmission Fee:", self.readmission_fee)
        form.addRow("Withdrawal Fee:", self.withdrawal_fee)
        form.addRow("Death Charge (charged to all members):", self.death_charge)
        form.addRow("Retirement Benefits:", self.retirement_fee)
        form.addRow("Sales of Loan Form:", self.loan_fee)
        form.addRow("Annual Fee:", self.annual_fee)
        form.addRow("Transfer Fee:", self.transfer_fee)
        form.addRow("Other Income:", self.other_income)
        form.addRow("Death Benefit (paid to deceased account):", self.death_benefit)

        layout.addWidget(grp)

        notation_grp  = QGroupBox("Death Benefit Notification")
        notation_form = QFormLayout(notation_grp)
        notation_form.setSpacing(10)
        notation_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.death_notation = QLineEdit()
        self.death_notation.setFixedHeight(36)
        self.death_notation.setPlaceholderText("Use {member_name} as placeholder")
        notation_form.addRow("Notation Template:", self.death_notation)
        hint = QLabel("Placeholder {member_name} will be replaced with deceased member name.")
        hint.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        notation_form.addRow("", hint)
        layout.addWidget(notation_grp)

        save_btn = QPushButton("Save Fee Settings")
        save_btn.setFixedHeight(40)
        save_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980B9; color: white;
                border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #3498DB; }
        """)
        save_btn.clicked.connect(self._save_fee_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

        scroll.setWidget(w)
        outer_layout.addWidget(scroll)
        return outer

    def _dividends_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        warn = QLabel("⚠  MAJOR WARNING: Dividend settings are system-wide. "
                      "Changing these values will affect ALL future distributions. "
                      "Each distribution is permanent and irreversible.")
        warn.setWordWrap(True)
        warn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        warn.setStyleSheet("""
            QLabel {
                background-color: #7B241C;
                color: #FADBD8;
                border: 2px solid #E74C3C;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout.addWidget(warn)

        grp  = QGroupBox("Dividend Configuration")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.div_method = QComboBox()
        self.div_method.setFixedHeight(36)
        self.div_method.addItems(["percentage", "fixed"])
        self.div_method.currentTextChanged.connect(self._on_div_method_change)

        self.div_pct = QDoubleSpinBox()
        self.div_pct.setFixedHeight(36)
        self.div_pct.setRange(0, 100)
        self.div_pct.setDecimals(2)
        self.div_pct.setSuffix(" % of savings balance")

        self.div_fixed = QDoubleSpinBox()
        self.div_fixed.setFixedHeight(36)
        self.div_fixed.setRange(0, 999_999_999)
        self.div_fixed.setDecimals(2)
        self.div_fixed.setSingleStep(1000)

        form.addRow("Distribution Method:", self.div_method)
        form.addRow("Percentage:", self.div_pct)
        form.addRow("Fixed Amount:", self.div_fixed)
        layout.addWidget(grp)

        save_btn = QPushButton("Save Dividend Settings")
        save_btn.setFixedHeight(40)
        save_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #922B21; color: white;
                border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #E74C3C; }
        """)
        save_btn.clicked.connect(self._save_dividend_settings)
        layout.addWidget(save_btn)
        layout.addStretch()
        return w

    def _on_div_method_change(self, method):
        self.div_pct.setEnabled(method == 'percentage')
        self.div_fixed.setEnabled(method == 'fixed')

    def _users_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        add_btn = QPushButton("Add User")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_user)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels([
            "Username", "Full Name", "Role",
            "Maintain", "Operate", "Reports", "Active"
        ])
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.users_table)

        btn_row = QHBoxLayout()
        self.edit_user_btn = QPushButton("Edit")
        self.edit_user_btn.setFixedHeight(34)
        self.edit_user_btn.setEnabled(False)
        self.edit_user_btn.clicked.connect(self._edit_user)
        btn_row.addWidget(self.edit_user_btn)

        self.pw_btn = QPushButton("Change Password")
        self.pw_btn.setFixedHeight(34)
        self.pw_btn.setEnabled(False)
        self.pw_btn.clicked.connect(self._change_password)
        btn_row.addWidget(self.pw_btn)

        self.deact_user_btn = QPushButton("Deactivate")
        self.deact_user_btn.setFixedHeight(34)
        self.deact_user_btn.setEnabled(False)
        self.deact_user_btn.setStyleSheet("QPushButton:enabled { color: #E74C3C; }")
        self.deact_user_btn.clicked.connect(self._deactivate_user)
        btn_row.addWidget(self.deact_user_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.users_table.selectionModel().selectionChanged.connect(self._on_user_selection)
        return w

    # -------------------------------------------------------------------------
    # Savings types tab
    # -------------------------------------------------------------------------

    def _savings_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        add_btn = QPushButton("Add Savings Type")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_savings_type)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        self.stypes_table = QTableWidget()
        self.stypes_table.setColumnCount(5)
        self.stypes_table.setHorizontalHeaderLabels([
            "Code", "Name", "Interest Rate", "Min Balance", "Active"
        ])
        self.stypes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.stypes_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.stypes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stypes_table.setAlternatingRowColors(True)
        self.stypes_table.verticalHeader().setVisible(False)
        self.stypes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.stypes_table)

        btn_row = QHBoxLayout()
        self.edit_stype_btn = QPushButton("Edit")
        self.edit_stype_btn.setFixedHeight(34)
        self.edit_stype_btn.setEnabled(False)
        self.edit_stype_btn.clicked.connect(self._edit_savings_type)
        btn_row.addWidget(self.edit_stype_btn)

        self.toggle_stype_btn = QPushButton("Deactivate")
        self.toggle_stype_btn.setFixedHeight(34)
        self.toggle_stype_btn.setEnabled(False)
        self.toggle_stype_btn.clicked.connect(self._toggle_savings_type)
        btn_row.addWidget(self.toggle_stype_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.stypes_table.selectionModel().selectionChanged.connect(self._on_stype_selection)
        return w

    # -------------------------------------------------------------------------
    # Loan types tab
    # -------------------------------------------------------------------------

    def _loans_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        add_btn = QPushButton("Add Loan Type")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_loan_type)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        self.ltypes_table = QTableWidget()
        self.ltypes_table.setColumnCount(5)
        self.ltypes_table.setHorizontalHeaderLabels([
            "Code", "Name", "Interest Rate", "Max Duration", "Active"
        ])
        self.ltypes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ltypes_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.ltypes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ltypes_table.setAlternatingRowColors(True)
        self.ltypes_table.verticalHeader().setVisible(False)
        self.ltypes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.ltypes_table)

        btn_row = QHBoxLayout()
        self.edit_ltype_btn = QPushButton("Edit")
        self.edit_ltype_btn.setFixedHeight(34)
        self.edit_ltype_btn.setEnabled(False)
        self.edit_ltype_btn.clicked.connect(self._edit_loan_type)
        btn_row.addWidget(self.edit_ltype_btn)

        self.toggle_ltype_btn = QPushButton("Deactivate")
        self.toggle_ltype_btn.setFixedHeight(34)
        self.toggle_ltype_btn.setEnabled(False)
        self.toggle_ltype_btn.clicked.connect(self._toggle_loan_type)
        btn_row.addWidget(self.toggle_ltype_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.ltypes_table.selectionModel().selectionChanged.connect(self._on_ltype_selection)
        return w

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _confirm(self, title: str, msg: str) -> bool:
        return QMessageBox.question(
            self, title, msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

    def _selected_user_id(self):
        row = self.users_table.currentRow()
        if row < 0: return None
        item = self.users_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_stype_id(self):
        row = self.stypes_table.currentRow()
        if row < 0: return None
        item = self.stypes_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_ltype_id(self):
        row = self.ltypes_table.currentRow()
        if row < 0: return None
        item = self.ltypes_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_user_selection(self):
        uid = self._selected_user_id()
        has = uid is not None
        self.edit_user_btn.setEnabled(has)
        self.pw_btn.setEnabled(has)
        # cannot deactivate yourself
        if has:
            user = self.db.get_user_by_id(uid)
            self.deact_user_btn.setEnabled(
                has and user and user['is_active'] and
                user['username'] != self.user['username']
            )
        else:
            self.deact_user_btn.setEnabled(False)

    def _on_stype_selection(self):
        sid = self._selected_stype_id()
        self.edit_stype_btn.setEnabled(sid is not None)
        self.toggle_stype_btn.setEnabled(sid is not None)
        if sid:
            stype = self.db.fetchone(
                "SELECT is_active FROM savings_types WHERE savings_type_id=?", (sid,)
            )
            self.toggle_stype_btn.setText(
                "Deactivate" if stype and stype['is_active'] else "Activate"
            )

    def _on_ltype_selection(self):
        lid = self._selected_ltype_id()
        self.edit_ltype_btn.setEnabled(lid is not None)
        self.toggle_ltype_btn.setEnabled(lid is not None)
        if lid:
            ltype = self.db.fetchone(
                "SELECT is_active FROM loan_types WHERE loan_type_id=?", (lid,)
            )
            self.toggle_ltype_btn.setText(
                "Deactivate" if ltype and ltype['is_active'] else "Activate"
            )

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def refresh(self):
        self._load_system_settings()
        self._load_fee_settings()
        self._load_dividend_settings()
        self._load_users()
        self._load_savings_types()
        self._load_loan_types()

    def _load_system_settings(self):
        self.org_name.setText(self.db.get_setting('organization_name') or '')
        self.currency.setText(self.db.get_setting('currency_symbol') or '₦')
        self.death_enabled.setChecked(self.db.get_setting('death_benefit_enabled') == '1')
        self.death_amount.setValue(float(self.db.get_setting('death_benefit_amount') or 0))
        self.retirement_pct.setValue(float(self.db.get_setting('retirement_benefit_percentage') or 0))
        self.non_retire_pct.setValue(float(self.db.get_setting('non_retirement_charge_percentage') or 0))
        self.interest_auto.setChecked(self.db.get_setting('interest_auto_calculate') == '1')

    def _load_users(self):
        users = self.db.get_all_users()
        self.users_table.setRowCount(len(users))
        for row, u in enumerate(users):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            id_item = cell(u['username'])
            id_item.setData(Qt.ItemDataRole.UserRole, u['user_id'])
            if not u['is_active']:
                id_item.setForeground(QTableWidgetItem().foreground())
                id_item.setStyleSheet = lambda: None
            self.users_table.setItem(row, 0, id_item)
            self.users_table.setItem(row, 1, cell(u['full_name'] or ''))
            self.users_table.setItem(row, 2, cell(u['role']))
            for col, key in enumerate(['can_maintain', 'can_operate', 'can_view_reports'], start=3):
                v = cell("Yes" if u[key] else "No", Qt.AlignmentFlag.AlignCenter)
                self.users_table.setItem(row, col, v)
            active_item = cell("Yes" if u['is_active'] else "No", Qt.AlignmentFlag.AlignCenter)
            if not u['is_active']:
                from PyQt6.QtGui import QColor
                active_item.setForeground(QColor("#E74C3C"))
            self.users_table.setItem(row, 6, active_item)

        self.users_table.resizeColumnsToContents()
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def _load_savings_types(self):
        stypes = self.db.fetchall("SELECT * FROM savings_types ORDER BY savings_type_id")
        self.stypes_table.setRowCount(len(stypes))
        for row, s in enumerate(stypes):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item
            code_item = cell(s['type_code'])
            code_item.setData(Qt.ItemDataRole.UserRole, s['savings_type_id'])
            self.stypes_table.setItem(row, 0, code_item)
            self.stypes_table.setItem(row, 1, cell(s['type_name']))
            self.stypes_table.setItem(row, 2, cell(f"{s['interest_rate']}%", Qt.AlignmentFlag.AlignCenter))
            self.stypes_table.setItem(row, 3, cell(f"{s['minimum_balance']:,.2f}", Qt.AlignmentFlag.AlignRight))
            active_item = cell("Yes" if s['is_active'] else "No", Qt.AlignmentFlag.AlignCenter)
            if not s['is_active']:
                from PyQt6.QtGui import QColor
                active_item.setForeground(QColor("#E74C3C"))
            self.stypes_table.setItem(row, 4, active_item)
        self.stypes_table.resizeColumnsToContents()
        self.stypes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def _load_loan_types(self):
        ltypes = self.db.fetchall("SELECT * FROM loan_types ORDER BY loan_type_id")
        self.ltypes_table.setRowCount(len(ltypes))
        for row, l in enumerate(ltypes):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item
            code_item = cell(l['type_code'])
            code_item.setData(Qt.ItemDataRole.UserRole, l['loan_type_id'])
            self.ltypes_table.setItem(row, 0, code_item)
            self.ltypes_table.setItem(row, 1, cell(l['type_name']))
            self.ltypes_table.setItem(row, 2, cell(f"{l['interest_rate']}%", Qt.AlignmentFlag.AlignCenter))
            self.ltypes_table.setItem(row, 3, cell(f"{l['max_duration_months']} months", Qt.AlignmentFlag.AlignCenter))
            active_item = cell("Yes" if l['is_active'] else "No", Qt.AlignmentFlag.AlignCenter)
            if not l['is_active']:
                from PyQt6.QtGui import QColor
                active_item.setForeground(QColor("#E74C3C"))
            self.ltypes_table.setItem(row, 4, active_item)
        self.ltypes_table.resizeColumnsToContents()
        self.ltypes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    # -------------------------------------------------------------------------
    # System settings actions
    # -------------------------------------------------------------------------

    def _save_system_settings(self):
        dlg = DangerConfirmDialog(
            "Save System Settings",
            "Saving system settings will affect all users and operations immediately.\n\n"
            "Review your changes carefully before confirming.",
            confirm_word="SAVE",
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        u = self.user['username']
        settings = {
            'organization_name':              self.org_name.text().strip(),
            'currency_symbol':                self.currency.text().strip() or '₦',
            'death_benefit_enabled':          '1' if self.death_enabled.isChecked() else '0',
            'death_benefit_amount':           f"{self.death_amount.value():.2f}",
            'retirement_benefit_percentage':  f"{self.retirement_pct.value():.2f}",
            'non_retirement_charge_percentage': f"{self.non_retire_pct.value():.2f}",
            'interest_auto_calculate':        '1' if self.interest_auto.isChecked() else '0',
        }
        for key, val in settings.items():
            self.db.update_setting(key, val, u)
        QMessageBox.information(self, "Saved", "System settings saved successfully.")

    # -------------------------------------------------------------------------
    # User actions
    # -------------------------------------------------------------------------

    def _add_user(self):
        dlg = UserDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm("Add User", f"Create user '{data['username']}'?"):
                return
            try:
                self.db.create_user(data, self.user['username'])
                self._load_users()
                QMessageBox.information(self, "User Created",
                                        f"User '{data['username']}' created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create user:\n{e}")

    def _edit_user(self):
        uid = self._selected_user_id()
        if not uid: return
        user = self.db.get_user_by_id(uid)
        if not user: return
        dlg = UserDialog(user=user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm("Edit User", f"Update user '{user['username']}'?"):
                return
            try:
                self.db.update_user(uid, data, self.user['username'])
                self._load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update user:\n{e}")

    def _change_password(self):
        uid = self._selected_user_id()
        if not uid: return
        user = self.db.get_user_by_id(uid)
        if not user: return
        dlg = ChangePasswordDialog(user['username'], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.db.change_password(uid, dlg.new_password())
            QMessageBox.information(self, "Password Changed",
                                    f"Password for '{user['username']}' updated.")

    def _deactivate_user(self):
        uid = self._selected_user_id()
        if not uid: return
        user = self.db.get_user_by_id(uid)
        if not user: return
        dlg = DangerConfirmDialog(
            "Deactivate User",
            f"Deactivate user '{user['username']}'?\n\n"
            "They will immediately lose access to the system.",
            confirm_word="DEACTIVATE",
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.db.deactivate_user(uid, self.user['username'])
        self._load_users()

    # -------------------------------------------------------------------------
    # Savings type actions
    # -------------------------------------------------------------------------

    def _add_savings_type(self):
        dlg = SavingsTypeDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm("Add Savings Type",
                                 f"Create savings type '{data['type_name']}'?"):
                return
            try:
                self.db.execute(
                    """INSERT INTO savings_types
                       (type_code, type_name, description, interest_rate,
                        minimum_balance, interest_enabled, is_active)
                       VALUES (?,?,?,?,?,1,1)""",
                    (data['type_code'].upper(), data['type_name'],
                     data.get('description', ''),
                     data['interest_rate'], data['minimum_balance'])
                )
                self.db.commit()
                self._load_savings_types()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add savings type:\n{e}")

    def _edit_savings_type(self):
        sid = self._selected_stype_id()
        if not sid: return
        stype = self.db.fetchone(
            "SELECT * FROM savings_types WHERE savings_type_id=?", (sid,)
        )
        if not stype: return
        dlg = SavingsTypeDialog(stype=stype, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm("Edit Savings Type",
                                 f"Update '{stype['type_name']}'?"):
                return
            self.db.execute(
                """UPDATE savings_types SET type_name=?, description=?,
                   interest_rate=?, minimum_balance=? WHERE savings_type_id=?""",
                (data['type_name'], data.get('description', ''),
                 data['interest_rate'], data['minimum_balance'], sid)
            )
            self.db.commit()
            self._load_savings_types()

    def _toggle_savings_type(self):
        sid = self._selected_stype_id()
        if not sid: return
        stype = self.db.fetchone(
            "SELECT * FROM savings_types WHERE savings_type_id=?", (sid,)
        )
        if not stype: return
        new_state  = 0 if stype['is_active'] else 1
        action     = "Deactivate" if stype['is_active'] else "Activate"

        if stype['is_active']:
            # check for active accounts
            count = self.db.fetchone(
                "SELECT COUNT(*) as c FROM savings_accounts WHERE savings_type_id=? AND is_active=1",
                (sid,)
            )['c']
            if count > 0:
                QMessageBox.warning(
                    self, "Cannot Deactivate",
                    f"Cannot deactivate — {count} active accounts use this type."
                )
                return

        if not self._confirm(f"{action} Savings Type",
                             f"{action} '{stype['type_name']}'?"):
            return
        self.db.execute(
            "UPDATE savings_types SET is_active=? WHERE savings_type_id=?",
            (new_state, sid)
        )
        self.db.commit()
        self._load_savings_types()

    # -------------------------------------------------------------------------
    # Loan type actions
    # -------------------------------------------------------------------------

    def _add_loan_type(self):
        dlg = LoanTypeDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm("Add Loan Type",
                                 f"Create loan type '{data['type_name']}'?"):
                return
            try:
                self.db.execute(
                    """INSERT INTO loan_types
                       (type_code, type_name, description,
                        interest_rate, max_duration_months, is_active)
                       VALUES (?,?,?,?,?,1)""",
                    (data['type_code'].upper(), data['type_name'],
                     data.get('description', ''),
                     data['interest_rate'], data['max_duration_months'])
                )
                self.db.commit()
                self._load_loan_types()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add loan type:\n{e}")

    def _edit_loan_type(self):
        lid = self._selected_ltype_id()
        if not lid: return
        ltype = self.db.fetchone(
            "SELECT * FROM loan_types WHERE loan_type_id=?", (lid,)
        )
        if not ltype: return
        dlg = LoanTypeDialog(ltype=ltype, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm("Edit Loan Type",
                                 f"Update '{ltype['type_name']}'?"):
                return
            self.db.execute(
                """UPDATE loan_types SET type_name=?, description=?,
                   interest_rate=?, max_duration_months=? WHERE loan_type_id=?""",
                (data['type_name'], data.get('description', ''),
                 data['interest_rate'], data['max_duration_months'], lid)
            )
            self.db.commit()
            self._load_loan_types()

    def _toggle_loan_type(self):
        lid = self._selected_ltype_id()
        if not lid: return
        ltype = self.db.fetchone(
            "SELECT * FROM loan_types WHERE loan_type_id=?", (lid,)
        )
        if not ltype: return
        new_state = 0 if ltype['is_active'] else 1
        action    = "Deactivate" if ltype['is_active'] else "Activate"

        if ltype['is_active']:
            count = self.db.fetchone(
                "SELECT COUNT(*) as c FROM loans WHERE loan_type_id=? AND status='Active'",
                (lid,)
            )['c']
            if count > 0:
                QMessageBox.warning(
                    self, "Cannot Deactivate",
                    f"Cannot deactivate — {count} active loans use this type."
                )
                return

        if not self._confirm(f"{action} Loan Type",
                             f"{action} '{ltype['type_name']}'?"):
            return
        self.db.execute(
            "UPDATE loan_types SET is_active=? WHERE loan_type_id=?",
            (new_state, lid)
        )
        self.db.commit()
        self._load_loan_types()


    def _load_fee_settings(self):
        self.admission_fee.setValue(float(self.db.get_setting('admission_fee_amount') or 0))
        self.readmission_fee.setValue(float(self.db.get_setting('readmission_fee_amount') or 0))
        self.withdrawal_fee.setValue(float(self.db.get_setting('withdrawal_fee_amount') or 0))
        self.death_charge.setValue(float(self.db.get_setting('death_charge_amount') or 0))
        self.retirement_fee.setValue(float(self.db.get_setting('retirement_benefit_fee_amount') or 0))
        self.loan_fee.setValue(float(self.db.get_setting('loan_form_fee_amount') or 0))
        self.annual_fee.setValue(float(self.db.get_setting('annual_fee_amount') or 0))
        self.transfer_fee.setValue(float(self.db.get_setting('transfer_fee_amount') or 0))
        self.other_income.setValue(float(self.db.get_setting('other_income_amount') or 0))
        self.death_benefit.setValue(float(self.db.get_setting('death_benefit_fee_amount') or 0))
        self.death_notation.setText(
            self.db.get_setting('death_benefit_notation') or
            'Death benefit charge — {member_name}'
        )

    def _save_fee_settings(self):
        dlg = DangerConfirmDialog(
            "Save Fee Settings",
            "Fee changes apply to ALL future operations immediately.\n\n"
            "Existing unpaid fees are not retroactively updated.",
            confirm_word="SAVE",
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        u = self.user['username']
        self.db.update_setting('admission_fee_amount',        f"{self.admission_fee.value():.2f}", u)
        self.db.update_setting('readmission_fee_amount',      f"{self.readmission_fee.value():.2f}", u)
        self.db.update_setting('withdrawal_fee_amount',       f"{self.withdrawal_fee.value():.2f}", u)
        self.db.update_setting('death_charge_amount',         f"{self.death_charge.value():.2f}", u)
        self.db.update_setting('retirement_benefit_fee_amount', f"{self.retirement_fee.value():.2f}", u)
        self.db.update_setting('loan_form_fee_amount',        f"{self.loan_fee.value():.2f}", u)
        self.db.update_setting('annual_fee_amount',           f"{self.annual_fee.value():.2f}", u)
        self.db.update_setting('transfer_fee_amount',         f"{self.transfer_fee.value():.2f}", u)
        self.db.update_setting('other_income_amount',         f"{self.other_income.value():.2f}", u)
        self.db.update_setting('death_benefit_fee_amount',    f"{self.death_benefit.value():.2f}", u)
        self.db.update_setting('death_benefit_notation', self.death_notation.text().strip(), u)
        QMessageBox.information(self, "Saved", "Fee settings saved.")

    def _load_dividend_settings(self):
        method = self.db.get_setting('dividend_distribution_method') or 'percentage'
        idx = self.div_method.findText(method)
        if idx >= 0:
            self.div_method.setCurrentIndex(idx)
        self.div_pct.setValue(float(self.db.get_setting('dividend_percentage') or 0))
        self.div_fixed.setValue(float(self.db.get_setting('dividend_fixed_amount') or 0))
        self._on_div_method_change(method)

    def _save_dividend_settings(self):
        dlg = DangerConfirmDialog(
            "Save Dividend Settings",
            "MAJOR WARNING: These settings are system-wide and will affect ALL future "
            "dividend distributions.\n\nThis cannot be undone.",
            confirm_word="SAVE",
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        u = self.user['username']
        self.db.update_setting('dividend_distribution_method',
                               self.div_method.currentText(), u)
        self.db.update_setting('dividend_percentage',
                               f"{self.div_pct.value():.2f}", u)
        self.db.update_setting('dividend_fixed_amount',
                               f"{self.div_fixed.value():.2f}", u)
        QMessageBox.information(self, "Saved", "Dividend settings saved.")


# ---------------------------------------------------------------------------
# User dialog
# ---------------------------------------------------------------------------

class UserDialog(QDialog):
    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Edit User" if user else "Add User")
        self.setFixedWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_input = QLineEdit()
        self.username_input.setFixedHeight(36)
        if self.user:
            self.username_input.setText(self.user['username'])
            self.username_input.setEnabled(False)

        self.fullname_input = QLineEdit()
        self.fullname_input.setFixedHeight(36)
        if self.user:
            self.fullname_input.setText(self.user.get('full_name') or '')

        self.role_combo = QComboBox()
        self.role_combo.setFixedHeight(36)
        self.role_combo.addItems(["Admin", "Manager", "Cashier", "Viewer"])
        if self.user:
            idx = self.role_combo.findText(self.user['role'])
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)

        self.password_input = QLineEdit()
        self.password_input.setFixedHeight(36)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Required for new users")

        form.addRow("Username:",  self.username_input)
        form.addRow("Full Name:", self.fullname_input)
        form.addRow("Role:",      self.role_combo)
        if not self.user:
            form.addRow("Password:",  self.password_input)

        layout.addLayout(form)

        perms_grp = QGroupBox("Permissions")
        pf        = QVBoxLayout(perms_grp)
        self.perm_maintain = QCheckBox("Maintain (stations, members, settings)")
        self.perm_operate  = QCheckBox("Operate (savings, loans, transactions)")
        self.perm_reports  = QCheckBox("View Reports")

        if self.user:
            self.perm_maintain.setChecked(bool(self.user.get('can_maintain')))
            self.perm_operate.setChecked(bool(self.user.get('can_operate')))
            self.perm_reports.setChecked(bool(self.user.get('can_view_reports')))
        else:
            # sensible defaults per role
            self.role_combo.currentTextChanged.connect(self._set_default_perms)
            self._set_default_perms(self.role_combo.currentText())

        pf.addWidget(self.perm_maintain)
        pf.addWidget(self.perm_operate)
        pf.addWidget(self.perm_reports)
        layout.addWidget(perms_grp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_default_perms(self, role: str):
        defaults = {
            'Admin':   (True,  True,  True),
            'Manager': (True,  True,  True),
            'Cashier': (False, True,  False),
            'Viewer':  (False, False, True),
        }
        m, o, r = defaults.get(role, (False, False, False))
        self.perm_maintain.setChecked(m)
        self.perm_operate.setChecked(o)
        self.perm_reports.setChecked(r)

    def data(self) -> dict:
        d = {
            'username':        self.username_input.text().strip(),
            'full_name':       self.fullname_input.text().strip(),
            'role':            self.role_combo.currentText(),
            'can_maintain':    int(self.perm_maintain.isChecked()),
            'can_operate':     int(self.perm_operate.isChecked()),
            'can_view_reports': int(self.perm_reports.isChecked()),
        }
        if not self.user:
            d['password'] = self.password_input.text()
        return d

    def _validate(self):
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "Validation", "Username is required.")
            return
        if not self.user and not self.password_input.text():
            QMessageBox.warning(self, "Validation", "Password is required.")
            return
        if not self.user and len(self.password_input.text()) < 6:
            QMessageBox.warning(self, "Validation", "Password must be at least 6 characters.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Change password dialog
# ---------------------------------------------------------------------------

class ChangePasswordDialog(QDialog):
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Change Password — {username}")
        self.setFixedWidth(360)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.new_pw  = QLineEdit(); self.new_pw.setFixedHeight(36)
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.conf_pw = QLineEdit(); self.conf_pw.setFixedHeight(36)
        self.conf_pw.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("New Password:",     self.new_pw)
        form.addRow("Confirm Password:", self.conf_pw)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def new_password(self) -> str:
        return self.new_pw.text()

    def _validate(self):
        if len(self.new_pw.text()) < 6:
            QMessageBox.warning(self, "Validation", "Password must be at least 6 characters.")
            return
        if self.new_pw.text() != self.conf_pw.text():
            QMessageBox.warning(self, "Validation", "Passwords do not match.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Savings type dialog
# ---------------------------------------------------------------------------

class SavingsTypeDialog(QDialog):
    def __init__(self, stype=None, parent=None):
        super().__init__(parent)
        self.stype = stype
        self.setWindowTitle("Edit Savings Type" if stype else "Add Savings Type")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.code_input = QLineEdit(); self.code_input.setFixedHeight(36)
        self.code_input.setPlaceholderText("e.g. PREMIUM")
        self.name_input = QLineEdit(); self.name_input.setFixedHeight(36)
        self.desc_input = QLineEdit(); self.desc_input.setFixedHeight(36)

        self.rate_input = QDoubleSpinBox(); self.rate_input.setFixedHeight(36)
        self.rate_input.setRange(0, 100); self.rate_input.setDecimals(2)
        self.rate_input.setSuffix(" %/month")

        self.min_bal = QDoubleSpinBox(); self.min_bal.setFixedHeight(36)
        self.min_bal.setRange(0, 999_999_999); self.min_bal.setDecimals(2)

        if self.stype:
            self.code_input.setText(self.stype['type_code'])
            self.code_input.setEnabled(False)
            self.name_input.setText(self.stype['type_name'])
            self.desc_input.setText(self.stype.get('description') or '')
            self.rate_input.setValue(float(self.stype['interest_rate']))
            self.min_bal.setValue(float(self.stype['minimum_balance'] or 0))

        form.addRow("Code:",          self.code_input)
        form.addRow("Name:",          self.name_input)
        form.addRow("Description:",   self.desc_input)
        form.addRow("Interest Rate:", self.rate_input)
        form.addRow("Min Balance:",   self.min_bal)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def data(self) -> dict:
        return {
            'type_code':       self.code_input.text().strip(),
            'type_name':       self.name_input.text().strip(),
            'description':     self.desc_input.text().strip(),
            'interest_rate':   self.rate_input.value(),
            'minimum_balance': self.min_bal.value(),
        }

    def _validate(self):
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "Validation", "Code is required.")
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Loan type dialog
# ---------------------------------------------------------------------------

class LoanTypeDialog(QDialog):
    def __init__(self, ltype=None, parent=None):
        super().__init__(parent)
        self.ltype = ltype
        self.setWindowTitle("Edit Loan Type" if ltype else "Add Loan Type")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.code_input = QLineEdit(); self.code_input.setFixedHeight(36)
        self.code_input.setPlaceholderText("e.g. MAJOR")
        self.name_input = QLineEdit(); self.name_input.setFixedHeight(36)
        self.desc_input = QLineEdit(); self.desc_input.setFixedHeight(36)

        self.rate_input = QDoubleSpinBox(); self.rate_input.setFixedHeight(36)
        self.rate_input.setRange(0, 100); self.rate_input.setDecimals(2)
        self.rate_input.setSuffix(" %")

        self.duration_input = QSpinBox(); self.duration_input.setFixedHeight(36)
        self.duration_input.setRange(1, 360); self.duration_input.setSuffix(" months")

        if self.ltype:
            self.code_input.setText(self.ltype['type_code'])
            self.code_input.setEnabled(False)
            self.name_input.setText(self.ltype['type_name'])
            self.desc_input.setText(self.ltype.get('description') or '')
            self.rate_input.setValue(float(self.ltype['interest_rate']))
            self.duration_input.setValue(int(self.ltype['max_duration_months']))

        form.addRow("Code:",         self.code_input)
        form.addRow("Name:",         self.name_input)
        form.addRow("Description:",  self.desc_input)
        form.addRow("Interest Rate:", self.rate_input)
        form.addRow("Max Duration:", self.duration_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def data(self) -> dict:
        return {
            'type_code':          self.code_input.text().strip(),
            'type_name':          self.name_input.text().strip(),
            'description':        self.desc_input.text().strip(),
            'interest_rate':      self.rate_input.value(),
            'max_duration_months': self.duration_input.value(),
        }

    def _validate(self):
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "Validation", "Code is required.")
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        self.accept()