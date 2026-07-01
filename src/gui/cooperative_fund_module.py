from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QComboBox, QTabWidget, QDoubleSpinBox, QDateEdit, QSpinBox,
    QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


class CooperativeFundModule(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app      = app
        self.db       = app.db_manager
        self.user     = app.current_user
        self.currency = self.db.get_setting('currency_symbol') or '₦'
        self._setup_ui()
        try:
            self.refresh()
        except Exception as e:
            import traceback
            traceback.print_exc()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Cooperative Fund")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        # Balance card
        self.balance_card = QGroupBox()
        self.balance_card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #27AE60;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        bal_layout = QHBoxLayout(self.balance_card)
        bal_layout.setSpacing(24)

        lbl_col = QVBoxLayout()
        lbl_col.setSpacing(4)
        fund_lbl = QLabel("Cooperative Fund Balance")
        fund_lbl.setStyleSheet("color: #7F8C8D; font-size: 11pt;")
        self.balance_lbl = QLabel("₦0.00")
        self.balance_lbl.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.balance_lbl.setStyleSheet("color: #27AE60;")
        lbl_col.addWidget(fund_lbl)
        lbl_col.addWidget(self.balance_lbl)
        bal_layout.addLayout(lbl_col)
        bal_layout.addStretch()

        if self.user.get('role') == 'Admin':
            btn_col = QVBoxLayout()
            btn_col.setSpacing(8)
            credit_btn = QPushButton("Manual Credit")
            credit_btn.setFixedHeight(36)
            credit_btn.setStyleSheet("color: #27AE60; font-weight: 600;")
            credit_btn.clicked.connect(lambda: self._manual_entry(True))
            debit_btn = QPushButton("Manual Debit")
            debit_btn.setFixedHeight(36)
            debit_btn.setStyleSheet("color: #E74C3C; font-weight: 600;")
            debit_btn.clicked.connect(lambda: self._manual_entry(False))
            retire_btn = QPushButton("Pay Retirement Benefit")
            retire_btn.setFixedHeight(36)
            retire_btn.setStyleSheet("color: #8E44AD; font-weight: 600;")
            retire_btn.clicked.connect(self._pay_retirement_benefit)
            other_btn = QPushButton("Record Other Income")
            other_btn.setFixedHeight(36)
            other_btn.setStyleSheet("color: #2980B9; font-weight: 600;")
            other_btn.clicked.connect(self._record_other_income)
            btn_col.addWidget(credit_btn)
            btn_col.addWidget(debit_btn)
            btn_col.addWidget(retire_btn)
            btn_col.addWidget(other_btn)
            bal_layout.addLayout(btn_col)

        layout.addWidget(self.balance_card)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._transactions_tab(),   "Fund Transactions")
        self.tabs.addTab(self._admission_fees_tab(), "Admission Fees")
        self.tabs.addTab(self._annual_fees_tab(),    "Annual Fees")
        self.tabs.addTab(self._other_fees_tab(),     "Other Fees")
        self.tabs.addTab(self._dividends_tab(),      "Dividends")
        layout.addWidget(self.tabs)

    # -------------------------------------------------------------------------
    # Tab builders
    # -------------------------------------------------------------------------

    def _transactions_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()
        self.fund_search = QLineEdit()
        self.fund_search.setPlaceholderText("Search description or category...")
        self.fund_search.setFixedHeight(36)
        self.fund_search.textChanged.connect(self._load_fund_transactions)
        filter_row.addWidget(self.fund_search, 2)

        self.fund_cat_filter = QComboBox()
        self.fund_cat_filter.setFixedHeight(36)
        self.fund_cat_filter.addItem("All Categories", None)
        for cat in ["Admission Fee", "Readmission Fee", "Withdrawal Fee",
                    "Death Charge", "Retirement Benefits", "Loan Form Fee",
                    "Annual Fee", "Transfer Fee", "Other Income",
                    "Death Benefit", "Dividend", "Manual"]:
            self.fund_cat_filter.addItem(cat, cat)
        self.fund_cat_filter.currentIndexChanged.connect(self._load_fund_transactions)
        filter_row.addWidget(self.fund_cat_filter, 1)

        self.fund_type_filter = QComboBox()
        self.fund_type_filter.setFixedHeight(36)
        self.fund_type_filter.addItems(["All", "Credit", "Debit"])
        self.fund_type_filter.currentIndexChanged.connect(self._load_fund_transactions)
        filter_row.addWidget(self.fund_type_filter)

        self.fund_date_from = QDateEdit()
        self.fund_date_from.setFixedHeight(36)
        self.fund_date_from.setCalendarPopup(True)
        self.fund_date_from.setDate(QDate(2010, 1, 1))
        self.fund_date_from.setDisplayFormat("dd/MM/yyyy")
        self.fund_date_from.dateChanged.connect(self._load_fund_transactions)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.fund_date_from)

        self.fund_date_to = QDateEdit()
        self.fund_date_to.setFixedHeight(36)
        self.fund_date_to.setCalendarPopup(True)
        self.fund_date_to.setDate(QDate.currentDate())
        self.fund_date_to.setDisplayFormat("dd/MM/yyyy")
        self.fund_date_to.dateChanged.connect(self._load_fund_transactions)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.fund_date_to)
        layout.addLayout(filter_row)

        self.fund_table = QTableWidget()
        self.fund_table.setColumnCount(7)
        self.fund_table.setHorizontalHeaderLabels([
            "Date", "Type", "Category", "Description",
            "Amount", "Running Balance", "Created By"
        ])
        self.fund_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fund_table.setAlternatingRowColors(True)
        self.fund_table.verticalHeader().setVisible(False)
        self.fund_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fund_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.fund_table)

        self.fund_summary = QLabel()
        self.fund_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.fund_summary)
        return w

    def _admission_fees_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()
        self.ef_status_filter = QComboBox()
        self.ef_status_filter.setFixedHeight(36)
        self.ef_status_filter.addItems(["Unpaid", "Paid", "All"])
        self.ef_status_filter.currentIndexChanged.connect(self._load_admission_fees)
        filter_row.addWidget(self.ef_status_filter)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.ef_table = QTableWidget()
        self.ef_table.setColumnCount(6)
        self.ef_table.setHorizontalHeaderLabels([
            "Member ID", "Member Name", "Amount", "Status", "Due Date", "Paid Date"
        ])
        self.ef_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ef_table.setAlternatingRowColors(True)
        self.ef_table.verticalHeader().setVisible(False)
        self.ef_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ef_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.ef_table)

        btn_row = QHBoxLayout()
        self.pay_ef_btn = QPushButton("Mark as Paid")
        self.pay_ef_btn.setFixedHeight(34)
        self.pay_ef_btn.setEnabled(False)
        self.pay_ef_btn.setStyleSheet("QPushButton:enabled { color: #27AE60; font-weight: 600; }")
        self.pay_ef_btn.clicked.connect(self._pay_admission_fee)
        btn_row.addWidget(self.pay_ef_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.ef_table.selectionModel().selectionChanged.connect(self._on_ef_selection)
        self.ef_summary = QLabel()
        self.ef_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.ef_summary)
        return w

    def _annual_fees_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        if self.user.get('role') == 'Admin':
            charge_btn = QPushButton("Charge Annual Fee")
            charge_btn.setFixedHeight(36)
            charge_btn.clicked.connect(self._charge_annual_fee)
            hdr.addWidget(charge_btn)
        layout.addLayout(hdr)

        filter_row = QHBoxLayout()
        self.af_year_filter = QComboBox()
        self.af_year_filter.setFixedHeight(36)
        from datetime import date
        current_year = date.today().year
        for y in range(current_year, current_year - 10, -1):
            self.af_year_filter.addItem(str(y), y)
        self.af_year_filter.currentIndexChanged.connect(self._load_annual_fees)
        filter_row.addWidget(QLabel("Year:"))
        filter_row.addWidget(self.af_year_filter)

        self.af_status_filter = QComboBox()
        self.af_status_filter.setFixedHeight(36)
        self.af_status_filter.addItems(["All", "Unpaid", "Paid"])
        self.af_status_filter.currentIndexChanged.connect(self._load_annual_fees)
        filter_row.addWidget(self.af_status_filter)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.af_table = QTableWidget()
        self.af_table.setColumnCount(6)
        self.af_table.setHorizontalHeaderLabels([
            "Member ID", "Member Name", "Year", "Amount", "Status", "Due Date"
        ])
        self.af_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.af_table.setAlternatingRowColors(True)
        self.af_table.verticalHeader().setVisible(False)
        self.af_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.af_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.af_table)

        self.af_summary = QLabel()
        self.af_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.af_summary)
        return w

    def _other_fees_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        # Fee summary cards row
        self.other_fee_cards_layout = QHBoxLayout()
        self.other_fee_cards_layout.setSpacing(10)
        layout.addLayout(self.other_fee_cards_layout)

        # Charge buttons row (Admin only)
        if self.user.get('role') == 'Admin':
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)

            self._fee_buttons = {}
            fee_actions = [
                ("Readmission Fee",     "readmission",  "#8E44AD"),
                ("Withdrawal Fee",      "withdrawal",   "#E67E22"),
                ("Transfer Fee",        "transfer",     "#2980B9"),
                ("Loan Form Fee",       "loan_form",    "#16A085"),
                ("Death Charge",        "death_charge", "#7B241C"),
            ]
            for label, key, colour in fee_actions:
                btn = QPushButton(f"Charge {label}")
                btn.setFixedHeight(34)
                btn.setStyleSheet(f"color: {colour}; font-weight: 600;")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, k=key, l=label: self._charge_other_fee(k, l))
                self._fee_buttons[key] = btn
                btn_row.addWidget(btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

        # Filter row
        filter_row = QHBoxLayout()
        self.of_search = QLineEdit()
        self.of_search.setPlaceholderText("Search member ID or description...")
        self.of_search.setFixedHeight(36)
        self.of_search.textChanged.connect(self._load_other_fees)
        filter_row.addWidget(self.of_search, 2)

        self.of_type_filter = QComboBox()
        self.of_type_filter.setFixedHeight(36)
        self.of_type_filter.addItems([
            "All Fee Types",
            "Readmission Fee",
            "Withdrawal Fee",
            "Transfer Fee",
            "Loan Form Fee",
            "Death Charge",
        ])
        self.of_type_filter.currentIndexChanged.connect(self._load_other_fees)
        filter_row.addWidget(self.of_type_filter, 1)

        self.of_date_from = QDateEdit()
        self.of_date_from.setFixedHeight(36)
        self.of_date_from.setCalendarPopup(True)
        self.of_date_from.setDate(QDate(2000, 1, 1))
        self.of_date_from.setDisplayFormat("dd/MM/yyyy")
        self.of_date_from.dateChanged.connect(self._load_other_fees)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.of_date_from)

        self.of_date_to = QDateEdit()
        self.of_date_to.setFixedHeight(36)
        self.of_date_to.setCalendarPopup(True)
        self.of_date_to.setDate(QDate.currentDate())
        self.of_date_to.setDisplayFormat("dd/MM/yyyy")
        self.of_date_to.dateChanged.connect(self._load_other_fees)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.of_date_to)
        layout.addLayout(filter_row)

        self.of_table = QTableWidget()
        self.of_table.setColumnCount(6)
        self.of_table.setHorizontalHeaderLabels([
            "Date", "Member ID", "Member Name", "Fee Type", "Amount", "Recorded By"
        ])
        self.of_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.of_table.setAlternatingRowColors(True)
        self.of_table.verticalHeader().setVisible(False)
        self.of_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.of_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.of_table)

        self.of_summary = QLabel()
        self.of_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.of_summary)
        return w

    def _dividends_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        if self.user.get('role') == 'Admin':
            dist_btn = QPushButton("Distribute Dividends")
            dist_btn.setFixedHeight(36)
            dist_btn.setStyleSheet("font-weight: 600; color: #2980B9;")
            dist_btn.clicked.connect(self._distribute_dividends)
            hdr.addWidget(dist_btn)
        layout.addLayout(hdr)

        self.div_table = QTableWidget()
        self.div_table.setColumnCount(6)
        self.div_table.setHorizontalHeaderLabels([
            "Date", "Period", "Method", "Members Paid",
            "Total Distributed", "Created By"
        ])
        self.div_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.div_table.setAlternatingRowColors(True)
        self.div_table.verticalHeader().setVisible(False)
        self.div_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.div_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.div_table)

        self.div_summary = QLabel()
        self.div_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.div_summary)
        return w

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _fmt(self, amount) -> str:
        return f"{self.currency}{float(amount or 0):,.2f}"

    def _confirm(self, title: str, msg: str) -> bool:
        return QMessageBox.question(
            self, title, msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

    def _on_ef_selection(self):
        row = self.ef_table.currentRow()
        if row < 0:
            self.pay_ef_btn.setEnabled(False)
            return
        item = self.ef_table.item(row, 3)
        self.pay_ef_btn.setEnabled(item and item.text() == "Unpaid")

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def refresh(self):
        balance = self.db.get_fund_balance()
        self.balance_lbl.setText(self._fmt(balance))
        self.balance_lbl.setStyleSheet(
            f"color: {'#27AE60' if balance >= 0 else '#E74C3C'};"
            "font-size: 24pt; font-weight: bold;"
        )
        self._load_fund_transactions()
        self._load_admission_fees()
        self._load_annual_fees()
        self._load_other_fees()
        self._load_dividends()

    def _load_fund_transactions(self):
        search    = self.fund_search.text().strip()
        cat       = self.fund_cat_filter.currentData()
        txn_type  = self.fund_type_filter.currentText()
        date_from = self.fund_date_from.date().toString("yyyy-MM-dd")
        date_to   = self.fund_date_to.date().toString("yyyy-MM-dd")

        q = """
            SELECT * FROM cooperative_fund_transactions
            WHERE txn_date >= ? AND txn_date <= ?
        """
        params = [date_from, date_to]

        if search:
            terms = [t.strip() for t in search.replace(',', ' ').split() if t.strip()]
            for term in terms:
                q += " AND (description LIKE ? OR category LIKE ?)"
                like = f"%{term}%"
                params.extend([like, like])

        if cat:
            q += " AND category=?"; params.append(cat)
        if txn_type == "Credit":
            q += " AND is_credit=1"
        elif txn_type == "Debit":
            q += " AND is_credit=0"

        q += " ORDER BY txn_date DESC, fund_txn_id DESC"
        rows = self.db.fetchall(q, tuple(params))

        self.fund_table.setRowCount(len(rows))
        total_credits = total_debits = 0.0

        for row, t in enumerate(rows):
            amount    = float(t['amount'] or 0)
            is_credit = bool(t['is_credit'])

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            self.fund_table.setItem(row, 0, cell(t['txn_date']))
            type_item = cell(t['txn_type'])
            type_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            self.fund_table.setItem(row, 1, type_item)
            self.fund_table.setItem(row, 2, cell(t['category']))
            self.fund_table.setItem(row, 3, cell(t['description'] or ""))
            amt_item = cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight)
            amt_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            self.fund_table.setItem(row, 4, amt_item)
            self.fund_table.setItem(row, 5, cell(
                self._fmt(t['running_balance'] or 0), Qt.AlignmentFlag.AlignRight
            ))
            self.fund_table.setItem(row, 6, cell(t['created_by'] or ""))

            if is_credit: total_credits += amount
            else:         total_debits  += amount

        self.fund_table.resizeColumnsToContents()
        self.fund_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.fund_summary.setText(
            f"{len(rows)} record(s)  —  "
            f"Credits: {self._fmt(total_credits)}  |  "
            f"Debits: {self._fmt(total_debits)}"
        )

    def _load_admission_fees(self):
        status = self.ef_status_filter.currentText()
        q = """
            SELECT ef.*, m.first_name, m.last_name
            FROM entrance_fees ef
            JOIN members m ON ef.member_id=m.member_id
        """
        if status == "Unpaid":
            q += " WHERE ef.is_paid=0"
        elif status == "Paid":
            q += " WHERE ef.is_paid=1"
        q += " ORDER BY ef.is_paid ASC, ef.member_id"
        rows = self.db.fetchall(q)

        self.ef_table.setRowCount(len(rows))
        unpaid_total = paid_total = 0.0

        for row, r in enumerate(rows):
            amount = float(r['amount'] or 0)

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            mid_item = cell(r['member_id'])
            mid_item.setData(Qt.ItemDataRole.UserRole, r['member_id'])
            self.ef_table.setItem(row, 0, mid_item)
            self.ef_table.setItem(row, 1, cell(f"{r['first_name']} {r['last_name']}"))
            self.ef_table.setItem(row, 2, cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight))

            is_paid   = bool(r['is_paid'])
            paid_item = cell("Paid" if is_paid else "Unpaid", Qt.AlignmentFlag.AlignCenter)
            paid_item.setForeground(QColor("#27AE60") if is_paid else QColor("#E74C3C"))
            self.ef_table.setItem(row, 3, paid_item)
            self.ef_table.setItem(row, 4, cell(r['due_date'] or ""))
            self.ef_table.setItem(row, 5, cell(r['paid_date'] or ""))

            if is_paid: paid_total   += amount
            else:       unpaid_total += amount

        self.ef_table.resizeColumnsToContents()
        self.ef_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ef_summary.setText(
            f"{len(rows)} record(s)  —  "
            f"Unpaid: {self._fmt(unpaid_total)}  |  "
            f"Paid: {self._fmt(paid_total)}"
        )

    def _load_annual_fees(self):
        year   = self.af_year_filter.currentData()
        status = self.af_status_filter.currentText()

        q = """
            SELECT af.*, m.first_name, m.last_name
            FROM annual_fees af
            JOIN members m ON af.member_id=m.member_id
            WHERE af.year=?
        """
        params = [year]
        if status == "Unpaid":
            q += " AND af.is_paid=0"
        elif status == "Paid":
            q += " AND af.is_paid=1"
        q += " ORDER BY af.is_paid ASC, af.member_id"
        rows = self.db.fetchall(q, tuple(params))

        self.af_table.setRowCount(len(rows))
        unpaid_total = paid_total = 0.0

        for row, r in enumerate(rows):
            amount = float(r['amount'] or 0)

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            mid_item = cell(r['member_id'])
            mid_item.setData(Qt.ItemDataRole.UserRole, r['member_id'])
            self.af_table.setItem(row, 0, mid_item)
            self.af_table.setItem(row, 1, cell(f"{r['first_name']} {r['last_name']}"))
            self.af_table.setItem(row, 2, cell(str(r['year']), Qt.AlignmentFlag.AlignCenter))
            self.af_table.setItem(row, 3, cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight))
            is_paid   = bool(r['is_paid'])
            paid_item = cell("Paid" if is_paid else "Unpaid", Qt.AlignmentFlag.AlignCenter)
            paid_item.setForeground(QColor("#27AE60") if is_paid else QColor("#E74C3C"))
            self.af_table.setItem(row, 4, paid_item)
            self.af_table.setItem(row, 5, cell(r['due_date'] or ""))

            if is_paid: paid_total   += amount
            else:       unpaid_total += amount

        self.af_table.resizeColumnsToContents()
        self.af_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.af_summary.setText(
            f"{len(rows)} record(s)  —  "
            f"Unpaid: {self._fmt(unpaid_total)}  |  "
            f"Paid: {self._fmt(paid_total)}"
        )

    def _load_other_fees(self):
        # Pull from cooperative_fund_transactions for non-admission, non-annual fee categories
        other_fee_cats = [
            "Readmission Fee", "Withdrawal Fee", "Transfer Fee",
            "Loan Form Fee", "Death Charge",
        ]
        search     = self.of_search.text().strip()
        type_sel   = self.of_type_filter.currentText()
        date_from  = self.of_date_from.date().toString("yyyy-MM-dd")
        date_to    = self.of_date_to.date().toString("yyyy-MM-dd")

        placeholders = ",".join("?" * len(other_fee_cats))
        q = f"""
            SELECT cft.txn_date, cft.member_id, cft.category,
                   cft.amount, cft.created_by,
                   m.first_name, m.last_name
            FROM cooperative_fund_transactions cft
            LEFT JOIN members m ON cft.member_id = m.member_id
            WHERE cft.category IN ({placeholders})
              AND cft.txn_date >= ? AND cft.txn_date <= ?
        """
        params = list(other_fee_cats) + [date_from, date_to]

        if type_sel != "All Fee Types":
            q += " AND cft.category = ?"
            params.append(type_sel)

        if search:
            q += " AND (cft.member_id LIKE ? OR cft.description LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like])

        q += " ORDER BY cft.txn_date DESC, cft.fund_txn_id DESC"
        rows = self.db.fetchall(q, tuple(params))

        # Fee summary cards — configured amounts from settings
        fee_config = [
            ("Readmission Fee",  "readmission_fee_amount"),
            ("Withdrawal Fee",   "withdrawal_fee_amount"),
            ("Transfer Fee",     "transfer_fee_amount"),
            ("Loan Form Fee",    "loan_form_fee_amount"),
            ("Death Charge",     "death_charge_amount"),
        ]
        # Clear and rebuild cards
        while self.other_fee_cards_layout.count():
            item = self.other_fee_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for fee_label, setting_key in fee_config:
            amount = float(self.db.get_setting(setting_key) or 0)
            card = QGroupBox(fee_label)
            card.setStyleSheet("QGroupBox { border: 1px solid #3D3D4A; border-radius: 6px; padding: 8px; font-size: 9pt; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 12, 8, 8)
            val_lbl = QLabel(self._fmt(amount))
            val_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            val_lbl.setStyleSheet("color: #2980B9;")
            card_layout.addWidget(val_lbl)
            self.other_fee_cards_layout.addWidget(card)
        self.other_fee_cards_layout.addStretch()

        # Populate table
        self.of_table.setRowCount(len(rows))
        total = 0.0

        for row, r in enumerate(rows):
            amount = float(r['amount'] or 0)
            total += amount
            name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip() if r['first_name'] else "—"

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            self.of_table.setItem(row, 0, cell(r['txn_date']))
            self.of_table.setItem(row, 1, cell(r['member_id'] or ""))
            self.of_table.setItem(row, 2, cell(name))
            self.of_table.setItem(row, 3, cell(r['category']))
            self.of_table.setItem(row, 4, cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight))
            self.of_table.setItem(row, 5, cell(r['created_by'] or ""))

        self.of_table.resizeColumnsToContents()
        self.of_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.of_summary.setText(
            f"{len(rows)} record(s)  —  Total collected: {self._fmt(total)}"
        )

    def _load_dividends(self):
        rows = self.db.get_dividends_history()
        self.div_table.setRowCount(len(rows))
        total = 0.0

        for row, r in enumerate(rows):
            amount = float(r['total_distributed'] or 0)
            total += amount

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            self.div_table.setItem(row, 0, cell(r['distribution_date']))
            self.div_table.setItem(row, 1, cell(r['period']))
            self.div_table.setItem(row, 2, cell(r['distribution_method']))
            self.div_table.setItem(row, 3, cell(str(r['members_paid']), Qt.AlignmentFlag.AlignCenter))
            self.div_table.setItem(row, 4, cell(self._fmt(amount), Qt.AlignmentFlag.AlignRight))
            self.div_table.setItem(row, 5, cell(r['created_by'] or ""))

        self.div_table.resizeColumnsToContents()
        self.div_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.div_summary.setText(
            f"{len(rows)} distribution(s)  —  Total paid out: {self._fmt(total)}"
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _manual_entry(self, is_credit: bool):
        dlg = ManualFundEntryDialog(is_credit, self.currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.data()
            action = "Credit" if is_credit else "Debit"
            if not self._confirm(
                f"Confirm Fund {action}",
                f"Record {action} of {self._fmt(data['amount'])} to Cooperative Fund?\n\n"
                f"Category: {data['category']}\n"
                f"Description: {data['description']}"
            ):
                return
            try:
                self.db.manual_fund_entry(
                    data['amount'], is_credit,
                    data['category'], data['description'],
                    self.user['username']
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to record entry:\n{e}")

    def _pay_admission_fee(self):
        row = self.ef_table.currentRow()
        if row < 0: return
        mid = self.ef_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not mid: return
        if not self._confirm("Mark Admission Fee Paid",
                             f"Mark admission fee as paid for {mid}?"):
            return
        try:
            self.db.pay_entrance_fee(mid, self.user['username'])
            self.db.commit()
            self._load_admission_fees()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")

    def _charge_annual_fee(self):
        from datetime import date
        year = date.today().year
        amount = float(self.db.get_setting('annual_fee_amount') or 0)

        # Danger warning
        dlg = DangerConfirmDialog(
            "Charge Annual Fee",
            f"This will charge the annual fee of {self._fmt(amount)} "
            f"to ALL active members for {year}.\n\n"
            f"This action cannot be undone.",
            confirm_word="CHARGE",
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            charged = self.db.charge_annual_fee_all(year, self.user['username'])
            self.db.commit()
            self.refresh()
            QMessageBox.information(
                self, "Annual Fee Charged",
                f"Annual fee charged to {charged} members for {year}."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")

    def _pay_retirement_benefit(self):
        amount = float(self.db.get_setting('retirement_benefit_fee_amount') or 0)
        if amount <= 0:
            QMessageBox.warning(
                self, "Not Configured",
                "Retirement benefit amount is set to zero.\n"
                "Configure it under Settings \u2192 Fees first."
            )
            return
        from PyQt6.QtWidgets import QInputDialog
        member_id, ok = QInputDialog.getText(self, "Pay Retirement Benefit", "Enter Member ID:")
        if not ok or not member_id.strip():
            return
        member_id = member_id.strip()
        member = self.db.get_member(member_id)
        if not member:
            QMessageBox.warning(self, "Not Found", f"Member '{member_id}' not found.")
            return
        name = f"{member['first_name']} {member['last_name']}"
        if not self._confirm(
            "Confirm Retirement Benefit",
            f"Pay retirement benefit of {self._fmt(amount)} to {name} ({member_id})?\n\n"
            "This will debit the cooperative fund."
        ):
            return
        try:
            self.db.charge_retirement_benefit(member_id, self.user['username'])
            self.db.commit()
            self.refresh()
            QMessageBox.information(
                self, "Retirement Benefit Paid",
                f"Retirement benefit of {self._fmt(amount)} paid for {name}."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")

    def _charge_other_fee(self, fee_key: str, fee_label: str):
        from PyQt6.QtWidgets import QInputDialog

        setting_map = {
            "readmission":  "readmission_fee_amount",
            "withdrawal":   "withdrawal_fee_amount",
            "transfer":     "transfer_fee_amount",
            "loan_form":    "loan_form_fee_amount",
            "death_charge": "death_charge_amount",
        }
        setting_key = setting_map.get(fee_key)
        amount = float(self.db.get_setting(setting_key) or 0) if setting_key else 0

        if amount <= 0:
            QMessageBox.warning(
                self, "Not Configured",
                f"{fee_label} is set to zero.\n"
                "Configure it under Settings → Fees first."
            )
            return

        member_id, ok = QInputDialog.getText(
            self, f"Charge {fee_label}", "Enter Member ID:"
        )
        if not ok or not member_id.strip():
            return
        member_id = member_id.strip().upper()
        member = self.db.get_member(member_id)
        if not member:
            QMessageBox.warning(self, "Not Found", f"Member '{member_id}' not found.")
            return

        name = f"{member['first_name']} {member['last_name']}"
        if not self._confirm(
            f"Charge {fee_label}",
            f"Charge {fee_label} of {self._fmt(amount)} for {name} ({member_id})?\n\n"
            "This will credit the cooperative fund."
        ):
            return

        try:
            method_map = {
                "readmission":  self.db.charge_readmission_fee,
                "withdrawal":   self.db.charge_withdrawal_fee,
                "transfer":     lambda mid, by: self.db._credit_fund(
                    float(self.db.get_setting('transfer_fee_amount') or 0),
                    "Transfer Fee",
                    f"Transfer fee — {mid}",
                    member_id=mid, created_by=by
                ),
                "loan_form":    lambda mid, by: self.db.charge_loan_form_fee(None, mid, by),
            }
            if fee_key == "death_charge":
                QMessageBox.information(
                    self, "Use Death Benefits Module",
                    "Death charges are applied automatically via the Death Benefits module."
                )
                return
            method_map[fee_key](member_id, self.user['username'])
            self.db.commit()
            self.refresh()
            QMessageBox.information(
                self, f"{fee_label} Charged",
                f"{self._fmt(amount)} charged for {name}."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to charge {fee_label}:\n{e}")

    def _record_other_income(self):
        dlg = OtherIncomeDialog(self.currency, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.data()
        if not self._confirm(
            "Record Other Income",
            f"Credit {self._fmt(data['amount'])} to the fund?\n\n"
            f"Description: {data['description']}"
        ):
            return
        try:
            self.db.record_other_income(
                data['amount'], data['description'],
                member_id=data.get('member_id') or None,
                created_by=self.user['username']
            )
            self.db.commit()
            self.refresh()
            QMessageBox.information(self, "Income Recorded",
                                    f"{self._fmt(data['amount'])} recorded as other income.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")

    def _distribute_dividends(self):
        method  = self.db.get_setting('dividend_distribution_method') or 'percentage'
        pct     = self.db.get_setting('dividend_percentage') or '0'
        fixed   = self.db.get_setting('dividend_fixed_amount') or '0'
        balance = self.db.get_fund_balance()
        members = self.db.get_all_members(active_only=True)

        if method == 'percentage':
            preview = f"{pct}% of each member's savings balance"
        else:
            preview = f"{self._fmt(float(fixed))} per member"

        dlg = DividendDistributeDialog(
            preview=preview,
            fund_balance=self._fmt(balance),
            member_count=len(members),
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        period = dlg.period()

        # Danger confirm
        danger = DangerConfirmDialog(
            "Distribute Dividends",
            f"This will distribute dividends to {len(members)} active members.\n\n"
            f"Period: {period}\n"
            f"Method: {preview}\n\n"
            f"THIS IS A SYSTEM-WIDE IRREVERSIBLE OPERATION.",
            confirm_word="DISTRIBUTE",
            parent=self
        )
        if danger.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            result = self.db.distribute_dividends(period, self.user['username'])
            self.refresh()
            QMessageBox.information(
                self, "Dividends Distributed",
                f"Distributed {self._fmt(result['total_distributed'])} "
                f"to {result['members_paid']} members for period {period}."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")


# ---------------------------------------------------------------------------
# Other income dialog
# ---------------------------------------------------------------------------

class OtherIncomeDialog(QDialog):
    def __init__(self, currency: str, parent=None):
        super().__init__(parent)
        self.currency = currency
        self.setWindowTitle("Record Other Income")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setFixedHeight(36)
        self.amount_input.setRange(0.01, 999_999_999)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix(f"{self.currency} ")
        self.amount_input.setSingleStep(1000)

        self.member_input = QLineEdit()
        self.member_input.setFixedHeight(36)
        self.member_input.setPlaceholderText("Optional")

        self.desc_input = QLineEdit()
        self.desc_input.setFixedHeight(36)
        self.desc_input.setPlaceholderText("Required")

        form.addRow("Amount:",      self.amount_input)
        form.addRow("Member ID:",   self.member_input)
        form.addRow("Description:", self.desc_input)
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
            'amount':      self.amount_input.value(),
            'member_id':   self.member_input.text().strip() or None,
            'description': self.desc_input.text().strip(),
        }

    def _validate(self):
        if not self.desc_input.text().strip():
            QMessageBox.warning(self, "Validation", "Description is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Manual fund entry dialog
# ---------------------------------------------------------------------------

class ManualFundEntryDialog(QDialog):
    def __init__(self, is_credit: bool, currency: str, parent=None):
        super().__init__(parent)
        self.currency  = currency
        self.is_credit = is_credit
        self.setWindowTitle(f"Manual Fund {'Credit' if is_credit else 'Debit'}")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setFixedHeight(36)
        self.amount_input.setRange(0.01, 999_999_999)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix(f"{self.currency} ")
        self.amount_input.setSingleStep(1000)

        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(36)
        self.category_combo.addItems(["Manual", "Adjustment", "Correction", "Other"])

        self.desc_input = QLineEdit()
        self.desc_input.setFixedHeight(36)
        self.desc_input.setPlaceholderText("Required")

        form.addRow("Amount:",      self.amount_input)
        form.addRow("Category:",    self.category_combo)
        form.addRow("Description:", self.desc_input)
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
            'amount':      self.amount_input.value(),
            'category':    self.category_combo.currentText(),
            'description': self.desc_input.text().strip(),
        }

    def _validate(self):
        if not self.desc_input.text().strip():
            QMessageBox.warning(self, "Validation", "Description is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Dividend distribution dialog
# ---------------------------------------------------------------------------

class DividendDistributeDialog(QDialog):
    def __init__(self, preview: str, fund_balance: str,
                 member_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Distribute Dividends")
        self.setFixedWidth(440)
        self._setup_ui(preview, fund_balance, member_count)

    def _setup_ui(self, preview, fund_balance, member_count):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        info = QGroupBox("Distribution Preview")
        form = QFormLayout(info)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Method:",        QLabel(preview))
        form.addRow("Fund Balance:",  QLabel(fund_balance))
        form.addRow("Active Members:", QLabel(str(member_count)))
        layout.addWidget(info)

        period_grp  = QGroupBox("Period")
        period_form = QFormLayout(period_grp)
        self.period_input = QLineEdit()
        self.period_input.setFixedHeight(36)
        from datetime import date
        self.period_input.setText(str(date.today().year))
        self.period_input.setPlaceholderText("e.g. 2026 or Q1-2026")
        period_form.addRow("Period:", self.period_input)
        layout.addWidget(period_grp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def period(self) -> str:
        return self.period_input.text().strip()

    def _validate(self):
        if not self.period_input.text().strip():
            QMessageBox.warning(self, "Validation", "Period is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Danger confirmation dialog (shared — used across modules)
# ---------------------------------------------------------------------------

class DangerConfirmDialog(QDialog):
    def __init__(self, title: str, message: str,
                 confirm_word: str = "CONFIRM", parent=None):
        super().__init__(parent)
        self.confirm_word = confirm_word
        self.setWindowTitle(title)
        self.setFixedWidth(460)
        self._setup_ui(message, confirm_word)

    def _setup_ui(self, message: str, confirm_word: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        # Danger banner
        banner = QLabel("⚠  WARNING — THIS ACTION CANNOT BE UNDONE")
        banner.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setStyleSheet("""
            QLabel {
                background-color: #7B241C;
                color: #FADBD8;
                border: 2px solid #E74C3C;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout.addWidget(banner)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 10pt; color: #E6E6EB;")
        layout.addWidget(msg_lbl)

        confirm_grp  = QGroupBox(f"Type {confirm_word} to confirm:")
        confirm_form = QFormLayout(confirm_grp)
        self.confirm_input = QLineEdit()
        self.confirm_input.setFixedHeight(36)
        self.confirm_input.setPlaceholderText(f"Type {confirm_word} here")
        confirm_form.addRow("", self.confirm_input)
        layout.addWidget(confirm_grp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self):
        if self.confirm_input.text().strip() != self.confirm_word:
            QMessageBox.warning(
                self, "Incorrect",
                f"You must type exactly: {self.confirm_word}"
            )
            return
        self.accept()