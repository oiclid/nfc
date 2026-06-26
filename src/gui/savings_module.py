from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QComboBox, QTabWidget, QDoubleSpinBox, QDateEdit, QSplitter,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


class SavingsModule(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app      = app
        self.db       = app.db_manager
        self.user     = app.current_user
        self.currency = self.db.get_setting('currency_symbol') or '₦'
        self._setup_ui()
        self.refresh()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Savings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        # Summary cards
        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(12)
        layout.addLayout(self.summary_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._accounts_tab(), "Accounts")
        self.tabs.addTab(self._transactions_tab(), "Transaction History")
        layout.addWidget(self.tabs)

    def _summary_card(self, label: str, value: str, color: str) -> QGroupBox:
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {color};
                border-radius: 6px;
                padding: 8px;
                background-color: transparent;
            }}
        """)
        inner = QVBoxLayout(card)
        inner.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #7F8C8D; font-size: 10pt;")
        val = QLabel(value)
        val.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {color};")
        inner.addWidget(lbl)
        inner.addWidget(val)
        return card

    def _accounts_tab(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        # Filters
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by member name or ID...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self.refresh)
        filter_row.addWidget(self.search_input, 2)

        self.station_filter = QComboBox()
        self.station_filter.setFixedHeight(36)
        self.station_filter.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            self.station_filter.addItem(s['station_name'], s['station_id'])
        self.station_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.station_filter, 1)

        self.type_filter = QComboBox()
        self.type_filter.setFixedHeight(36)
        self.type_filter.addItem("All Types", None)
        for st in self.db.get_savings_types():
            self.type_filter.addItem(st['type_name'], st['savings_type_id'])
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.type_filter, 1)

        layout.addLayout(filter_row)

        # Accounts table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(8)
        self.accounts_table.setHorizontalHeaderLabels([
            "Account No", "Member ID", "Member Name", "Station",
            "Type", "Balance", "Total Deposits", "Total Withdrawals"
        ])
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.accounts_table.verticalHeader().setVisible(False)
        self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.accounts_table.doubleClicked.connect(self._view_account)
        layout.addWidget(self.accounts_table)

        # Action buttons
        btn_row = QHBoxLayout()

        self.deposit_btn = QPushButton("Deposit")
        self.deposit_btn.setFixedHeight(34)
        self.deposit_btn.setEnabled(False)
        self.deposit_btn.setStyleSheet("QPushButton:enabled { color: #27AE60; font-weight: 600; }")
        self.deposit_btn.clicked.connect(self._deposit)
        btn_row.addWidget(self.deposit_btn)

        self.withdraw_btn = QPushButton("Withdraw")
        self.withdraw_btn.setFixedHeight(34)
        self.withdraw_btn.setEnabled(False)
        self.withdraw_btn.setStyleSheet("QPushButton:enabled { color: #E74C3C; font-weight: 600; }")
        self.withdraw_btn.clicked.connect(self._withdraw)
        btn_row.addWidget(self.withdraw_btn)

        self.new_account_btn = QPushButton("Open New Account")
        self.new_account_btn.setFixedHeight(34)
        self.new_account_btn.clicked.connect(self._open_account)
        btn_row.addWidget(self.new_account_btn)

        self.view_btn = QPushButton("View History")
        self.view_btn.setFixedHeight(34)
        self.view_btn.setEnabled(False)
        self.view_btn.clicked.connect(self._view_account)
        btn_row.addWidget(self.view_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.accounts_table.selectionModel().selectionChanged.connect(self._on_account_selection)

        self.accounts_summary = QLabel()
        self.accounts_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.accounts_summary)

        return w

    def _transactions_tab(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()

        self.txn_search = QLineEdit()
        self.txn_search.setPlaceholderText("Search by member name or ID...")
        self.txn_search.setFixedHeight(36)
        self.txn_search.textChanged.connect(self._load_transactions)
        filter_row.addWidget(self.txn_search, 2)

        self.txn_station_filter = QComboBox()
        self.txn_station_filter.setFixedHeight(36)
        self.txn_station_filter.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            self.txn_station_filter.addItem(s['station_name'], s['station_id'])
        self.txn_station_filter.currentIndexChanged.connect(self._load_transactions)
        filter_row.addWidget(self.txn_station_filter, 1)

        self.txn_type_filter = QComboBox()
        self.txn_type_filter.setFixedHeight(36)
        self.txn_type_filter.addItems(["All", "Savings Deposit", "Savings Withdrawal", "Interest Credit"])
        self.txn_type_filter.currentIndexChanged.connect(self._load_transactions)
        filter_row.addWidget(self.txn_type_filter)

        self.date_from = QDateEdit()
        self.date_from.setFixedHeight(36)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.dateChanged.connect(self._load_transactions)
        filter_row.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setFixedHeight(36)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.dateChanged.connect(self._load_transactions)
        filter_row.addWidget(self.date_to)

        layout.addLayout(filter_row)

        self.txn_table = QTableWidget()
        self.txn_table.setColumnCount(7)
        self.txn_table.setHorizontalHeaderLabels([
            "Date", "Member ID", "Member Name", "Station",
            "Type", "Amount", "Method"
        ])
        self.txn_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.txn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.txn_table.setAlternatingRowColors(True)
        self.txn_table.verticalHeader().setVisible(False)
        self.txn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.txn_table)

        self.txn_summary = QLabel()
        self.txn_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.txn_summary)

        return w

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _fmt(self, amount) -> str:
        return f"{self.currency}{float(amount):,.2f}"

    def _confirm(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _selected_account_id(self):
        row = self.accounts_table.currentRow()
        if row < 0:
            return None
        item = self.accounts_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_account_selection(self):
        aid = self._selected_account_id()
        has = aid is not None
        self.deposit_btn.setEnabled(has)
        self.withdraw_btn.setEnabled(has)
        self.view_btn.setEnabled(has)

    def _get_filtered_accounts(self):
        search     = self.search_input.text().strip()
        station_id = self.station_filter.currentData()
        type_id    = self.type_filter.currentData()

        q = """
            SELECT sa.*, st.type_name, st.type_code, st.interest_rate,
                   m.first_name, m.middle_name, m.last_name, m.station_id
            FROM savings_accounts sa
            JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
            JOIN members m ON sa.member_id=m.member_id
            WHERE sa.is_active=1
        """
        params = []

        if search:
            # support multiple search terms separated by space or comma
            terms = [t.strip() for t in search.replace(',', ' ').split() if t.strip()]
            for term in terms:
                q += """ AND (m.member_id LIKE ? OR m.first_name LIKE ?
                          OR m.last_name LIKE ?
                          OR (m.first_name || ' ' || COALESCE(m.middle_name,'') || ' ' || m.last_name) LIKE ?)"""
                like = f"%{term}%"
                params.extend([like, like, like, like])

        if station_id:
            q += " AND m.station_id=?"
            params.append(station_id)

        if type_id:
            q += " AND sa.savings_type_id=?"
            params.append(type_id)

        q += " ORDER BY m.member_id, sa.savings_type_id"
        return self.db.fetchall(q, tuple(params))

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    def refresh(self):
        self._load_accounts()
        self._update_summary_cards()

    def _update_summary_cards(self):
        # clear existing cards
        while self.summary_row.count():
            item = self.summary_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        totals = self.db.fetchall("""
            SELECT st.type_name, st.type_code,
                   COUNT(*) as accounts,
                   ROUND(SUM(sa.current_balance),2) as total
            FROM savings_accounts sa
            JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
            WHERE sa.is_active=1
            GROUP BY st.savings_type_id
        """)

        colors = {'PREMIUM': '#2980B9', 'TARGET': '#27AE60',
                  'FIXED_DEPOSIT': '#8E44AD', 'SHARES': '#E67E22'}

        grand_total = sum(t['total'] or 0 for t in totals)
        card = self._summary_card("Total Savings",
                                  self._fmt(grand_total), "#2C3E50")
        self.summary_row.addWidget(card)

        for t in totals:
            color = colors.get(t['type_code'], '#7F8C8D')
            card  = self._summary_card(
                t['type_name'],
                self._fmt(t['total'] or 0),
                color
            )
            self.summary_row.addWidget(card)

    def _load_accounts(self):
        accounts = self._get_filtered_accounts()
        stations = {s['station_id']: s['station_name']
                    for s in self.db.get_all_stations(enabled_only=False)}

        self.accounts_table.setRowCount(len(accounts))
        total_balance = 0.0

        for row, a in enumerate(accounts):
            full_name = ' '.join(filter(None, [
                a['first_name'], a.get('middle_name'), a['last_name']
            ]))

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            acct_item = cell(a['account_number'])
            acct_item.setData(Qt.ItemDataRole.UserRole, a['account_id'])
            self.accounts_table.setItem(row, 0, acct_item)
            self.accounts_table.setItem(row, 1, cell(a['member_id']))
            self.accounts_table.setItem(row, 2, cell(full_name))
            self.accounts_table.setItem(row, 3, cell(stations.get(a['station_id'], a['station_id'])))
            self.accounts_table.setItem(row, 4, cell(a['type_name']))

            bal = float(a['current_balance'] or 0)
            total_balance += bal
            bal_item = cell(self._fmt(bal), Qt.AlignmentFlag.AlignRight)
            bal_item.setForeground(QColor("#27AE60") if bal >= 0 else QColor("#E74C3C"))
            self.accounts_table.setItem(row, 5, bal_item)

            dep_item = cell(self._fmt(a['total_deposits'] or 0), Qt.AlignmentFlag.AlignRight)
            self.accounts_table.setItem(row, 6, dep_item)
            wit_item = cell(self._fmt(a['total_withdrawals'] or 0), Qt.AlignmentFlag.AlignRight)
            self.accounts_table.setItem(row, 7, wit_item)

        self.accounts_table.resizeColumnsToContents()
        self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.accounts_summary.setText(
            f"{len(accounts)} account(s) shown  —  "
            f"Filtered total: {self._fmt(total_balance)}"
        )

    def _load_transactions(self):
        search     = self.txn_search.text().strip()
        station_id = self.txn_station_filter.currentData()
        txn_type   = self.txn_type_filter.currentText()
        date_from  = self.date_from.date().toString("yyyy-MM-dd")
        date_to    = self.date_to.date().toString("yyyy-MM-dd")

        q = """
            SELECT t.*, m.first_name, m.middle_name, m.last_name, m.station_id
            FROM transactions t
            JOIN members m ON t.member_id=m.member_id
            WHERE t.account_type='Savings'
            AND t.transaction_date >= ? AND t.transaction_date <= ?
        """
        params = [date_from, date_to]

        if search:
            terms = [t.strip() for t in search.replace(',', ' ').split() if t.strip()]
            for term in terms:
                q += """ AND (t.member_id LIKE ? OR m.first_name LIKE ?
                          OR m.last_name LIKE ?
                          OR (m.first_name || ' ' || COALESCE(m.middle_name,'') || ' ' || m.last_name) LIKE ?)"""
                like = f"%{term}%"
                params.extend([like, like, like, like])

        if station_id:
            q += " AND m.station_id=?"
            params.append(station_id)

        if txn_type != "All":
            q += " AND t.transaction_type=?"
            params.append(txn_type)

        q += " ORDER BY t.transaction_date DESC, t.transaction_id DESC"
        txns = self.db.fetchall(q, tuple(params))

        stations = {s['station_id']: s['station_name']
                    for s in self.db.get_all_stations(enabled_only=False)}

        self.txn_table.setRowCount(len(txns))
        total_credits = total_debits = 0.0

        for row, t in enumerate(txns):
            full_name = ' '.join(filter(None, [
                t['first_name'], t.get('middle_name'), t['last_name']
            ]))
            amount = float(t['amount'] or 0)
            is_credit = bool(t['is_credit'])

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            self.txn_table.setItem(row, 0, cell(t['transaction_date']))
            self.txn_table.setItem(row, 1, cell(t['member_id']))
            self.txn_table.setItem(row, 2, cell(full_name))
            self.txn_table.setItem(row, 3, cell(stations.get(t['station_id'], t['station_id'] or "")))
            self.txn_table.setItem(row, 4, cell(t['transaction_type']))

            amt_item = cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight)
            amt_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            self.txn_table.setItem(row, 5, amt_item)
            self.txn_table.setItem(row, 6, cell(t['payment_method'] or ""))

            if is_credit:
                total_credits += amount
            else:
                total_debits += amount

        self.txn_table.resizeColumnsToContents()
        self.txn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.txn_summary.setText(
            f"{len(txns)} transaction(s)  —  "
            f"Credits: {self._fmt(total_credits)}  |  "
            f"Debits: {self._fmt(total_debits)}"
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _deposit(self):
        aid = self._selected_account_id()
        if not aid:
            return
        account = self.db.get_savings_account(aid)
        member  = self.db.get_member(account['member_id'])
        if not account or not member:
            return
        dlg = TransactionDialog("Deposit", account, member, self.currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            full_name = f"{member['first_name']} {member['last_name']}"
            if not self._confirm(
                "Confirm Deposit",
                f"Deposit {self._fmt(data['amount'])} to {full_name}'s "
                f"{account['account_number']}?"
            ):
                return
            try:
                self.db.deposit_to_savings(
                    aid, data['amount'],
                    {'payment_method': data['method'],
                     'cheque_number':  data.get('cheque_number'),
                     'description':    data.get('description', 'Savings deposit')},
                    self.user['username']
                )
                QMessageBox.information(
                    self, "Deposit Successful",
                    f"Deposited {self._fmt(data['amount'])} to {account['account_number']}."
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Deposit failed:\n{e}")

    def _withdraw(self):
        aid = self._selected_account_id()
        if not aid:
            return
        account = self.db.get_savings_account(aid)
        member  = self.db.get_member(account['member_id'])
        if not account or not member:
            return
        dlg = TransactionDialog("Withdrawal", account, member, self.currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            full_name = f"{member['first_name']} {member['last_name']}"
            if not self._confirm(
                "Confirm Withdrawal",
                f"Withdraw {self._fmt(data['amount'])} from {full_name}'s "
                f"{account['account_number']}?\n\n"
                f"Current balance: {self._fmt(account['current_balance'])}"
            ):
                return
            try:
                self.db.withdraw_from_savings(
                    aid, data['amount'],
                    {'payment_method': data['method'],
                     'cheque_number':  data.get('cheque_number'),
                     'description':    data.get('description', 'Savings withdrawal')},
                    self.user['username']
                )
                self.db.charge_withdrawal_fee(account['member_id'], self.user['username'])
                self.db.commit()
                QMessageBox.information(
                    self, "Withdrawal Successful",
                    f"Withdrew {self._fmt(data['amount'])} from {account['account_number']}."
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Withdrawal failed:\n{e}")

    def _open_account(self):
        dlg = OpenAccountDialog(self.db, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data   = dlg.data()
            member = self.db.get_member(data['member_id'])
            if not member:
                QMessageBox.warning(self, "Error", f"Member {data['member_id']} not found.")
                return
            full_name = f"{member['first_name']} {member['last_name']}"
            stype  = self.db.fetchone(
                "SELECT type_name FROM savings_types WHERE savings_type_id=?",
                (data['savings_type_id'],)
            )
            if not self._confirm(
                "Confirm Open Account",
                f"Open a new {stype['type_name']} account for {full_name}?"
            ):
                return
            try:
                self.db.create_savings_account(data['member_id'], data['savings_type_id'])
                QMessageBox.information(self, "Account Opened",
                                        f"New savings account opened for {full_name}.")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open account:\n{e}")

    def _view_account(self):
        aid = self._selected_account_id()
        if not aid:
            return
        AccountHistoryDialog(self.db, aid, self.currency, parent=self).exec()


# ---------------------------------------------------------------------------
# Deposit / Withdrawal dialog
# ---------------------------------------------------------------------------

class TransactionDialog(QDialog):
    def __init__(self, mode: str, account, member, currency, parent=None):
        super().__init__(parent)
        self.mode     = mode
        self.account  = account
        self.currency = currency
        self.setWindowTitle(f"{mode} — {account['account_number']}")
        self.setFixedWidth(420)
        self._setup_ui(member)

    def _setup_ui(self, member):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        full_name = f"{member['first_name']} {member.get('middle_name', '') or ''} {member['last_name']}".strip()

        info = QGroupBox("Account Details")
        form = QFormLayout(info)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Member:", QLabel(f"{member['member_id']} — {full_name}"))
        form.addRow("Account:", QLabel(self.account['account_number']))
        form.addRow("Type:", QLabel(self.account.get('type_name', '')))
        bal = float(self.account['current_balance'] or 0)
        bal_lbl = QLabel(f"{self.currency}{bal:,.2f}")
        bal_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        bal_lbl.setStyleSheet("color: #27AE60;" if bal >= 0 else "color: #E74C3C;")
        form.addRow("Current Balance:", bal_lbl)
        layout.addWidget(info)

        txn = QGroupBox(f"{self.mode} Details")
        tf  = QFormLayout(txn)
        tf.setSpacing(10)
        tf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setFixedHeight(36)
        self.amount_input.setRange(0.01, 999_999_999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix(f"{self.currency} ")
        self.amount_input.setSingleStep(1000)
        tf.addRow("Amount:", self.amount_input)

        self.method_combo = QComboBox()
        self.method_combo.setFixedHeight(36)
        self.method_combo.addItems(["Cash", "Cheque", "Bank Transfer", "Direct Debit"])
        self.method_combo.currentTextChanged.connect(self._on_method_change)
        tf.addRow("Payment Method:", self.method_combo)

        self.cheque_input = QLineEdit()
        self.cheque_input.setFixedHeight(36)
        self.cheque_input.setPlaceholderText("Cheque number")
        self.cheque_input.setVisible(False)
        tf.addRow("Cheque No:", self.cheque_input)

        self.desc_input = QLineEdit()
        self.desc_input.setFixedHeight(36)
        self.desc_input.setPlaceholderText("Optional")
        tf.addRow("Description:", self.desc_input)

        layout.addWidget(txn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_method_change(self, method):
        self.cheque_input.setVisible(method == "Cheque")

    def data(self) -> dict:
        return {
            'amount':        self.amount_input.value(),
            'method':        self.method_combo.currentText(),
            'cheque_number': self.cheque_input.text().strip() or None,
            'description':   self.desc_input.text().strip(),
        }

    def _validate(self):
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
            return
        if self.method_combo.currentText() == "Cheque" and not self.cheque_input.text().strip():
            QMessageBox.warning(self, "Validation", "Cheque number is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Open new savings account dialog
# ---------------------------------------------------------------------------

class OpenAccountDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Open New Savings Account")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.member_input = QLineEdit()
        self.member_input.setFixedHeight(36)
        self.member_input.setPlaceholderText("e.g. NFC0001")
        self.member_input.textChanged.connect(self._lookup_member)
        form.addRow("Member ID:", self.member_input)

        self.member_name_lbl = QLabel("—")
        self.member_name_lbl.setStyleSheet("color: #7F8C8D;")
        form.addRow("Name:", self.member_name_lbl)

        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(36)
        for st in self.db.get_savings_types():
            self.type_combo.addItem(
                f"{st['type_name']} ({st['interest_rate']}%/mo)",
                st['savings_type_id']
            )
        form.addRow("Account Type:", self.type_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _lookup_member(self, mid):
        mid = mid.strip().upper()
        if len(mid) >= 7:
            member = self.db.get_member(mid)
            if member:
                self.member_name_lbl.setText(
                    f"{member['first_name']} {member.get('middle_name', '') or ''} {member['last_name']}".strip()
                )
                self.member_name_lbl.setStyleSheet("color: #27AE60;")
                return
        self.member_name_lbl.setText("—")
        self.member_name_lbl.setStyleSheet("color: #7F8C8D;")

    def data(self) -> dict:
        return {
            'member_id':       self.member_input.text().strip().upper(),
            'savings_type_id': self.type_combo.currentData(),
        }

    def _validate(self):
        mid = self.member_input.text().strip().upper()
        if not mid:
            QMessageBox.warning(self, "Validation", "Member ID is required.")
            return
        if not self.db.get_member(mid):
            QMessageBox.warning(self, "Validation", f"Member '{mid}' not found.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Account history dialog
# ---------------------------------------------------------------------------

class AccountHistoryDialog(QDialog):
    def __init__(self, db, account_id: int, currency: str, parent=None):
        super().__init__(parent)
        self.db         = db
        self.account_id = account_id
        self.currency   = currency
        account         = db.get_savings_account(account_id)
        self.setWindowTitle(f"Account History — {account['account_number']}")
        self.setMinimumWidth(640)
        self.setMinimumHeight(480)
        self._setup_ui(account)

    def _setup_ui(self, account):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        # Account summary
        info = QGroupBox("Account Summary")
        form = QFormLayout(info)
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        bal = float(account['current_balance'] or 0)
        for label, val in [
            ("Account No:",     account['account_number']),
            ("Balance:",        f"{self.currency}{bal:,.2f}"),
            ("Total Deposits:", f"{self.currency}{float(account['total_deposits'] or 0):,.2f}"),
            ("Withdrawals:",    f"{self.currency}{float(account['total_withdrawals'] or 0):,.2f}"),
            ("Interest Earned:",f"{self.currency}{float(account['interest_earned'] or 0):,.2f}"),
        ]:
            lbl = QLabel(val)
            if label == "Balance:":
                lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                lbl.setStyleSheet("color: #27AE60;" if bal >= 0 else "color: #E74C3C;")
            form.addRow(label, lbl)
        layout.addWidget(info)

        # Transactions
        txns = self.db.fetchall(
            """SELECT * FROM transactions
               WHERE account_id=?
               ORDER BY transaction_date DESC, transaction_id DESC""",
            (str(account_id),)
        )

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Date", "Type", "Amount", "Method", "Description"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(txns))

        for row, t in enumerate(txns):
            amount    = float(t['amount'] or 0)
            is_credit = bool(t['is_credit'])

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            table.setItem(row, 0, cell(t['transaction_date']))
            table.setItem(row, 1, cell(t['transaction_type']))
            amt_item = cell(f"{self.currency}{amount:,.2f}", Qt.AlignmentFlag.AlignRight)
            amt_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            table.setItem(row, 2, amt_item)
            table.setItem(row, 3, cell(t['payment_method'] or ""))
            table.setItem(row, 4, cell(t['description'] or ""))

        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)