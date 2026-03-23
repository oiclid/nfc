from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QComboBox, QDateEdit, QDoubleSpinBox, QTextEdit, QCheckBox, QTabWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


class TransactionsModule(QWidget):
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

        hdr = QHBoxLayout()
        title = QLabel("Transactions")
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

        self.tabs = QTabWidget()
        self.tabs.addTab(self._all_transactions_tab(), "All Transactions")
        self.tabs.addTab(self._bank_transactions_tab(), "Bank Transactions")
        self.tabs.currentChanged.connect(self._on_tab_change)
        layout.addWidget(self.tabs)

    def _summary_card(self, label, value, color) -> QGroupBox:
        card = QGroupBox()
        card.setStyleSheet(f"QGroupBox {{ border: 1px solid {color}; border-radius: 6px; padding: 8px; }}")
        inner = QVBoxLayout(card)
        inner.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #7F8C8D; font-size: 10pt;")
        val = QLabel(value)
        val.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {color};")
        inner.addWidget(lbl)
        inner.addWidget(val)
        return card

    def _all_transactions_tab(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by member name or ID...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._load_transactions)
        filter_row.addWidget(self.search_input, 2)

        self.station_filter = QComboBox()
        self.station_filter.setFixedHeight(36)
        self.station_filter.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            self.station_filter.addItem(s['station_name'], s['station_id'])
        self.station_filter.currentIndexChanged.connect(self._load_transactions)
        filter_row.addWidget(self.station_filter, 1)

        self.type_filter = QComboBox()
        self.type_filter.setFixedHeight(36)
        self.type_filter.addItem("All Types", None)
        for t in ["Savings Deposit", "Savings Withdrawal", "Interest Credit",
                  "Loan Disbursement", "Loan Repayment"]:
            self.type_filter.addItem(t, t)
        self.type_filter.currentIndexChanged.connect(self._load_transactions)
        filter_row.addWidget(self.type_filter, 1)

        layout.addLayout(filter_row)

        date_row = QHBoxLayout()

        self.date_from = QDateEdit()
        self.date_from.setFixedHeight(36)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(2010, 1, 1))
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.dateChanged.connect(self._load_transactions)
        date_row.addWidget(QLabel("From:"))
        date_row.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setFixedHeight(36)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.dateChanged.connect(self._load_transactions)
        date_row.addWidget(QLabel("To:"))
        date_row.addWidget(self.date_to)

        self.credits_only_cb = QCheckBox("Credits only")
        self.credits_only_cb.stateChanged.connect(self._load_transactions)
        date_row.addWidget(self.credits_only_cb)

        self.debits_only_cb = QCheckBox("Debits only")
        self.debits_only_cb.stateChanged.connect(self._load_transactions)
        date_row.addWidget(self.debits_only_cb)

        date_row.addStretch()
        layout.addLayout(date_row)

        self.txn_table = QTableWidget()
        self.txn_table.setColumnCount(8)
        self.txn_table.setHorizontalHeaderLabels([
            "Date", "Member ID", "Member Name", "Station",
            "Type", "Account", "Amount", "Method"
        ])
        self.txn_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.txn_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.txn_table.setAlternatingRowColors(True)
        self.txn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.txn_table.verticalHeader().setVisible(False)
        self.txn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.txn_table.doubleClicked.connect(self._view_transaction)
        layout.addWidget(self.txn_table)

        btn_row = QHBoxLayout()
        self.view_txn_btn = QPushButton("View Details")
        self.view_txn_btn.setFixedHeight(34)
        self.view_txn_btn.setEnabled(False)
        self.view_txn_btn.clicked.connect(self._view_transaction)
        btn_row.addWidget(self.view_txn_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.txn_table.selectionModel().selectionChanged.connect(
            lambda: self.view_txn_btn.setEnabled(self.txn_table.currentRow() >= 0)
        )

        self.txn_summary = QLabel()
        self.txn_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.txn_summary)

        self.txn_empty_lbl = QLabel(
            "No transactions found.\n\n"
            "Transactions are recorded automatically when you make deposits, "
            "withdrawals, or loan disbursements through the Savings and Loans modules."
        )
        self.txn_empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txn_empty_lbl.setWordWrap(True)
        self.txn_empty_lbl.setStyleSheet("color: #7F8C8D; font-size: 11pt;")
        self.txn_empty_lbl.setVisible(False)
        layout.addWidget(self.txn_empty_lbl)

        return w

    def _bank_transactions_tab(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        if self.user.get('role') == 'Admin':
            add_btn = QPushButton("Add Bank Transaction")
            add_btn.setFixedHeight(36)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._add_bank_transaction)
            hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        filter_row = QHBoxLayout()

        self.bank_search = QLineEdit()
        self.bank_search.setPlaceholderText("Search by payee, description, cheque no...")
        self.bank_search.setFixedHeight(36)
        self.bank_search.textChanged.connect(self._load_bank_transactions)
        filter_row.addWidget(self.bank_search, 2)

        self.bank_type_filter = QComboBox()
        self.bank_type_filter.setFixedHeight(36)
        self.bank_type_filter.addItems(["All", "Credit", "Debit"])
        self.bank_type_filter.currentIndexChanged.connect(self._load_bank_transactions)
        filter_row.addWidget(self.bank_type_filter)

        self.bank_cleared_filter = QComboBox()
        self.bank_cleared_filter.setFixedHeight(36)
        self.bank_cleared_filter.addItems(["All", "Cleared", "Uncleared"])
        self.bank_cleared_filter.currentIndexChanged.connect(self._load_bank_transactions)
        filter_row.addWidget(self.bank_cleared_filter)

        self.bank_date_from = QDateEdit()
        self.bank_date_from.setFixedHeight(36)
        self.bank_date_from.setCalendarPopup(True)
        self.bank_date_from.setDate(QDate(2010, 1, 1))
        self.bank_date_from.setDisplayFormat("dd/MM/yyyy")
        self.bank_date_from.dateChanged.connect(self._load_bank_transactions)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.bank_date_from)

        self.bank_date_to = QDateEdit()
        self.bank_date_to.setFixedHeight(36)
        self.bank_date_to.setCalendarPopup(True)
        self.bank_date_to.setDate(QDate.currentDate())
        self.bank_date_to.setDisplayFormat("dd/MM/yyyy")
        self.bank_date_to.dateChanged.connect(self._load_bank_transactions)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.bank_date_to)

        layout.addLayout(filter_row)

        self.bank_table = QTableWidget()
        self.bank_table.setColumnCount(9)
        self.bank_table.setHorizontalHeaderLabels([
            "Date", "Type", "Payee", "Description",
            "Amount", "Method", "Cheque No", "Bank", "Cleared"
        ])
        self.bank_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bank_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.bank_table.setAlternatingRowColors(True)
        self.bank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bank_table.verticalHeader().setVisible(False)
        self.bank_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.bank_table)

        btn_row = QHBoxLayout()
        if self.user.get('role') == 'Admin':
            self.mark_cleared_btn = QPushButton("Mark Cleared")
            self.mark_cleared_btn.setFixedHeight(34)
            self.mark_cleared_btn.setEnabled(False)
            self.mark_cleared_btn.clicked.connect(self._mark_cleared)
            btn_row.addWidget(self.mark_cleared_btn)
            self.bank_table.selectionModel().selectionChanged.connect(self._on_bank_selection)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.bank_summary = QLabel()
        self.bank_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.bank_summary)

        return w

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _fmt(self, amount) -> str:
        return f"{self.currency}{float(amount or 0):,.2f}"

    def _confirm(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _selected_bank_id(self):
        row = self.bank_table.currentRow()
        if row < 0:
            return None
        item = self.bank_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_bank_selection(self):
        bid = self._selected_bank_id()
        if bid and hasattr(self, 'mark_cleared_btn'):
            txn = self.db.fetchone(
                "SELECT is_cleared FROM bank_transactions WHERE bank_transaction_id=?", (bid,)
            )
            self.mark_cleared_btn.setEnabled(txn and not txn['is_cleared'])

    def _on_tab_change(self, idx):
        if idx == 1:
            self._load_bank_transactions()

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    def refresh(self):
        self._update_summary_cards()
        self._load_transactions()
        self._load_bank_transactions()

    def _update_summary_cards(self):
        while self.summary_row.count():
            item = self.summary_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = self.db.fetchall("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_credit=1 THEN amount ELSE 0 END) as total_credits,
                SUM(CASE WHEN is_credit=0 THEN amount ELSE 0 END) as total_debits,
                SUM(CASE WHEN transaction_type='Savings Deposit'   THEN amount ELSE 0 END) as deposits,
                SUM(CASE WHEN transaction_type='Loan Disbursement' THEN amount ELSE 0 END) as disbursements,
                SUM(CASE WHEN transaction_type='Loan Repayment'    THEN amount ELSE 0 END) as repayments
            FROM transactions
        """)
        r = rows[0] if rows else {}

        bank_rows = self.db.fetchall("""
            SELECT ROUND(SUM(amount),2) as bank_total FROM bank_transactions
        """)
        bank_total = bank_rows[0]['bank_total'] or 0 if bank_rows else 0

        cards = [
            ("Total Transactions", str(r.get('total', 0)),                   "#2C3E50"),
            ("Total Credits",      self._fmt(r.get('total_credits', 0)),     "#27AE60"),
            ("Total Debits",       self._fmt(r.get('total_debits', 0)),      "#E74C3C"),
            ("Loan Disbursements", self._fmt(r.get('disbursements', 0)),     "#E67E22"),
            ("Loan Repayments",    self._fmt(r.get('repayments', 0)),        "#2980B9"),
            ("Bank Transactions",  self._fmt(bank_total),                    "#8E44AD"),
        ]
        for label, value, color in cards:
            self.summary_row.addWidget(self._summary_card(label, value, color))

    def _load_transactions(self):
        search     = self.search_input.text().strip()
        station_id = self.station_filter.currentData()
        txn_type   = self.type_filter.currentData()
        date_from  = self.date_from.date().toString("yyyy-MM-dd")
        date_to    = self.date_to.date().toString("yyyy-MM-dd")
        credits_only = self.credits_only_cb.isChecked()
        debits_only  = self.debits_only_cb.isChecked()

        q = """
            SELECT t.*, m.first_name, m.middle_name, m.last_name, m.station_id
            FROM transactions t
            LEFT JOIN members m ON t.member_id=m.member_id
            WHERE t.transaction_date >= ? AND t.transaction_date <= ?
        """
        params = [date_from, date_to]

        if search:
            terms = [s.strip() for s in search.replace(',', ' ').split() if s.strip()]
            for term in terms:
                q += """ AND (t.member_id LIKE ? OR m.first_name LIKE ?
                          OR m.last_name LIKE ?
                          OR (m.first_name || ' ' || COALESCE(m.middle_name,'') || ' ' || m.last_name) LIKE ?)"""
                like = f"%{term}%"
                params.extend([like, like, like, like])

        if station_id:
            q += " AND t.station_id=?"
            params.append(station_id)

        if txn_type:
            q += " AND t.transaction_type=?"
            params.append(txn_type)

        if credits_only:
            q += " AND t.is_credit=1"
        elif debits_only:
            q += " AND t.is_credit=0"

        q += " ORDER BY t.transaction_date DESC, t.transaction_id DESC"
        txns = self.db.fetchall(q, tuple(params))

        stations = {s['station_id']: s['station_name']
                    for s in self.db.get_all_stations(enabled_only=False)}

        self.txn_table.setRowCount(len(txns))
        total_credits = total_debits = 0.0

        for row, t in enumerate(txns):
            full_name = ' '.join(filter(None, [
                t.get('first_name'), t.get('middle_name'), t.get('last_name')
            ])) or "—"
            amount    = float(t['amount'] or 0)
            is_credit = bool(t['is_credit'])

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            id_item = cell(t['transaction_date'])
            id_item.setData(Qt.ItemDataRole.UserRole, t['transaction_id'])
            self.txn_table.setItem(row, 0, id_item)
            self.txn_table.setItem(row, 1, cell(t['member_id']))
            self.txn_table.setItem(row, 2, cell(full_name))
            self.txn_table.setItem(row, 3, cell(stations.get(t.get('station_id',''), t.get('station_id','') or "—")))
            self.txn_table.setItem(row, 4, cell(t['transaction_type']))
            self.txn_table.setItem(row, 5, cell(t['account_type']))

            amt_item = cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight)
            amt_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            self.txn_table.setItem(row, 6, amt_item)
            self.txn_table.setItem(row, 7, cell(t['payment_method'] or ""))

            if is_credit:
                total_credits += amount
            else:
                total_debits += amount

        self.txn_table.resizeColumnsToContents()
        self.txn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.txn_empty_lbl.setVisible(len(txns) == 0)
        self.txn_table.setVisible(len(txns) > 0)
        self.txn_summary.setText(
            f"{len(txns)} transaction(s)  —  "
            f"Credits: {self._fmt(total_credits)}  |  "
            f"Debits: {self._fmt(total_debits)}"
        )

    def _load_bank_transactions(self):
        search    = self.bank_search.text().strip()
        txn_type  = self.bank_type_filter.currentText()
        cleared   = self.bank_cleared_filter.currentText()
        date_from = self.bank_date_from.date().toString("yyyy-MM-dd")
        date_to   = self.bank_date_to.date().toString("yyyy-MM-dd")

        q = """
            SELECT * FROM bank_transactions
            WHERE transaction_date >= ? AND transaction_date <= ?
        """
        params = [date_from, date_to]

        if search:
            terms = [s.strip() for s in search.replace(',', ' ').split() if s.strip()]
            for term in terms:
                q += """ AND (payee_name LIKE ? OR description LIKE ?
                          OR cheque_number LIKE ? OR details LIKE ?)"""
                like = f"%{term}%"
                params.extend([like, like, like, like])

        if txn_type != "All":
            q += " AND transaction_type=?"
            params.append(txn_type)

        if cleared == "Cleared":
            q += " AND is_cleared=1"
        elif cleared == "Uncleared":
            q += " AND is_cleared=0"

        q += " ORDER BY transaction_date DESC, bank_transaction_id DESC"
        txns = self.db.fetchall(q, tuple(params))

        self.bank_table.setRowCount(len(txns))
        total_credits = total_debits = 0.0

        for row, t in enumerate(txns):
            amount    = float(t['amount'] or 0)
            is_credit = t['transaction_type'] == 'Credit'

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            date_item = cell(t['transaction_date'])
            date_item.setData(Qt.ItemDataRole.UserRole, t['bank_transaction_id'])
            self.bank_table.setItem(row, 0, date_item)

            type_item = cell(t['transaction_type'])
            type_item.setForeground(
                QColor("#27AE60") if is_credit else QColor("#E74C3C")
            )
            self.bank_table.setItem(row, 1, type_item)
            self.bank_table.setItem(row, 2, cell(t['payee_name'] or ""))
            self.bank_table.setItem(row, 3, cell(t['description'] or ""))

            amt_item = cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight)
            amt_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            self.bank_table.setItem(row, 4, amt_item)

            self.bank_table.setItem(row, 5, cell(t['payment_method'] or ""))
            self.bank_table.setItem(row, 6, cell(t['cheque_number'] or ""))
            self.bank_table.setItem(row, 7, cell(t['bank_name'] or ""))

            cleared_item = cell("Yes" if t['is_cleared'] else "No")
            cleared_item.setForeground(
                QColor("#27AE60") if t['is_cleared'] else QColor("#E67E22")
            )
            self.bank_table.setItem(row, 8, cleared_item)

            if is_credit:
                total_credits += amount
            else:
                total_debits += amount

        self.bank_table.resizeColumnsToContents()
        self.bank_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.bank_summary.setText(
            f"{len(txns)} bank transaction(s)  —  "
            f"Credits: {self._fmt(total_credits)}  |  "
            f"Debits: {self._fmt(total_debits)}"
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _view_transaction(self):
        row = self.txn_table.currentRow()
        if row < 0:
            return
        tid  = self.txn_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        txn  = self.db.fetchone("SELECT * FROM transactions WHERE transaction_id=?", (tid,))
        if not txn:
            return
        TransactionDetailDialog(txn, self.currency, parent=self).exec()

    def _add_bank_transaction(self):
        dlg = BankTransactionDialog(self.currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            if not self._confirm(
                "Confirm Bank Transaction",
                f"Record {data['transaction_type']} of {self._fmt(data['amount'])} "
                f"for {data['payee_name']}?"
            ):
                return
            try:
                self.db.execute(
                    """INSERT INTO bank_transactions
                       (transaction_date, transaction_type, payee_name, description,
                        amount, payment_method, cheque_number, bank_name,
                        receipt_number, bank_charges, bank_interest, details, created_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (data['transaction_date'], data['transaction_type'],
                     data['payee_name'], data.get('description'),
                     data['amount'], data['payment_method'],
                     data.get('cheque_number'), data.get('bank_name'),
                     data.get('receipt_number'), data.get('bank_charges', 0),
                     data.get('bank_interest', 0), data.get('details'),
                     self.user['username'])
                )
                self.db.commit()
                self.refresh()
                QMessageBox.information(self, "Success", "Bank transaction recorded.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to record transaction:\n{e}")

    def _mark_cleared(self):
        bid = self._selected_bank_id()
        if not bid:
            return
        if not self._confirm("Mark Cleared",
                             "Mark this bank transaction as cleared?"):
            return
        try:
            self.db.execute(
                "UPDATE bank_transactions SET is_cleared=1 WHERE bank_transaction_id=?",
                (bid,)
            )
            self.db.commit()
            self._load_bank_transactions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update:\n{e}")


# ---------------------------------------------------------------------------
# Transaction detail dialog (read-only)
# ---------------------------------------------------------------------------

class TransactionDetailDialog(QDialog):
    def __init__(self, txn, currency, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Transaction Details — #{txn['transaction_id']}")
        self.setFixedWidth(440)
        self._setup_ui(txn, currency)

    def _setup_ui(self, t, currency):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        group = QGroupBox("Transaction Details")
        form  = QFormLayout(group)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        amount    = float(t['amount'] or 0)
        is_credit = bool(t['is_credit'])
        amt_lbl   = QLabel(f"{currency}{amount:,.2f}")
        amt_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        amt_lbl.setStyleSheet("color: #27AE60;" if is_credit else "color: #E74C3C;")

        for label, val in [
            ("Transaction ID:",  str(t['transaction_id'])),
            ("Date:",            t['transaction_date']),
            ("Member ID:",       t['member_id']),
            ("Type:",            t['transaction_type']),
            ("Account Type:",    t['account_type']),
            ("Direction:",       "Credit" if is_credit else "Debit"),
            ("Payment Method:",  t['payment_method'] or "—"),
            ("Cheque No:",       t['cheque_number'] or "—"),
            ("Receipt No:",      t['receipt_number'] or "—"),
            ("Description:",     t['description'] or "—"),
            ("Created By:",      t['created_by'] or "—"),
            ("Created Date:",    t['created_date'] or "—"),
        ]:
            form.addRow(label, QLabel(val or "—"))

        form.addRow("Amount:", amt_lbl)
        layout.addWidget(group)

        note = QLabel("Transactions are permanent audit records and cannot be modified.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #7F8C8D; font-size: 9pt; font-style: italic;")
        layout.addWidget(note)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)


# ---------------------------------------------------------------------------
# Bank transaction add dialog
# ---------------------------------------------------------------------------

class BankTransactionDialog(QDialog):
    def __init__(self, currency, parent=None):
        super().__init__(parent)
        self.currency = currency
        self.setWindowTitle("Add Bank Transaction")
        self.setFixedWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        group = QGroupBox("Bank Transaction Details")
        form  = QFormLayout(group)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def field(placeholder=""):
            f = QLineEdit()
            f.setFixedHeight(36)
            f.setPlaceholderText(placeholder)
            return f

        self.date_input = QDateEdit()
        self.date_input.setFixedHeight(36)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Date:", self.date_input)

        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(36)
        self.type_combo.addItems(["Credit", "Debit"])
        form.addRow("Type:", self.type_combo)

        self.payee_input   = field("Payee name — required")
        self.desc_input    = field("Optional")
        form.addRow("Payee:", self.payee_input)
        form.addRow("Description:", self.desc_input)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setFixedHeight(36)
        self.amount_input.setRange(0.01, 999_999_999)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix(f"{self.currency} ")
        self.amount_input.setSingleStep(1000)
        form.addRow("Amount:", self.amount_input)

        self.method_combo = QComboBox()
        self.method_combo.setFixedHeight(36)
        self.method_combo.addItems(["Cheque", "Cash", "Bank Transfer"])
        self.method_combo.currentTextChanged.connect(self._on_method_change)
        form.addRow("Payment Method:", self.method_combo)

        self.cheque_input  = field("Cheque number")
        self.bank_input    = field("Bank name")
        self.receipt_input = field("Optional")
        self.details_input = field("Optional")
        form.addRow("Cheque No:",   self.cheque_input)
        form.addRow("Bank:",        self.bank_input)
        form.addRow("Receipt No:",  self.receipt_input)
        form.addRow("Details:",     self.details_input)

        self.charges_input = QDoubleSpinBox()
        self.charges_input.setFixedHeight(36)
        self.charges_input.setRange(0, 999_999)
        self.charges_input.setDecimals(2)
        self.charges_input.setPrefix(f"{self.currency} ")
        form.addRow("Bank Charges:", self.charges_input)

        layout.addWidget(group)

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
            'transaction_date': self.date_input.date().toString("yyyy-MM-dd"),
            'transaction_type': self.type_combo.currentText(),
            'payee_name':       self.payee_input.text().strip(),
            'description':      self.desc_input.text().strip() or None,
            'amount':           self.amount_input.value(),
            'payment_method':   self.method_combo.currentText(),
            'cheque_number':    self.cheque_input.text().strip() or None,
            'bank_name':        self.bank_input.text().strip() or None,
            'receipt_number':   self.receipt_input.text().strip() or None,
            'details':          self.details_input.text().strip() or None,
            'bank_charges':     self.charges_input.value(),
        }

    def _validate(self):
        if not self.payee_input.text().strip():
            QMessageBox.warning(self, "Validation", "Payee name is required.")
            return
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
            return
        if self.method_combo.currentText() == "Cheque" and not self.cheque_input.text().strip():
            QMessageBox.warning(self, "Validation", "Cheque number is required.")
            return
        self.accept()