from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QComboBox, QTabWidget, QDoubleSpinBox, QDateEdit, QSpinBox,
    QAbstractItemView, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from datetime import date as dt_date
from dateutil.relativedelta import relativedelta


class LoansModule(QWidget):
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
        title = QLabel("Loans")
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
        self.tabs.addTab(self._loans_tab(),       "All Loans")
        self.tabs.addTab(self._repayments_tab(),  "Repayment History")
        self.tabs.addTab(self._disburse_tab(),    "Disburse Loan")
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

    def _loans_tab(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        # Filters
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by member name or ID...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._load_loans)
        filter_row.addWidget(self.search_input, 2)

        self.station_filter = QComboBox()
        self.station_filter.setFixedHeight(36)
        self.station_filter.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            self.station_filter.addItem(s['station_name'], s['station_id'])
        self.station_filter.currentIndexChanged.connect(self._load_loans)
        filter_row.addWidget(self.station_filter, 1)

        self.type_filter = QComboBox()
        self.type_filter.setFixedHeight(36)
        self.type_filter.addItem("All Types", None)
        for lt in self.db.get_loan_types():
            self.type_filter.addItem(lt['type_name'], lt['loan_type_id'])
        self.type_filter.currentIndexChanged.connect(self._load_loans)
        filter_row.addWidget(self.type_filter, 1)

        self.status_filter = QComboBox()
        self.status_filter.setFixedHeight(36)
        self.status_filter.addItems(["All", "Active", "Defaulted", "Completed"])
        self.status_filter.currentIndexChanged.connect(self._load_loans)
        filter_row.addWidget(self.status_filter)

        layout.addLayout(filter_row)

        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(10)
        self.loans_table.setHorizontalHeaderLabels([
            "Loan No", "Member ID", "Member Name", "Station",
            "Type", "Principal", "Total", "Paid", "Outstanding", "Status"
        ])
        self.loans_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.loans_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.loans_table.setAlternatingRowColors(True)
        self.loans_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.loans_table.verticalHeader().setVisible(False)
        self.loans_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.loans_table.doubleClicked.connect(self._view_loan)
        layout.addWidget(self.loans_table)

        btn_row = QHBoxLayout()

        self.repay_btn = QPushButton("Record Repayment")
        self.repay_btn.setFixedHeight(34)
        self.repay_btn.setEnabled(False)
        self.repay_btn.setStyleSheet("QPushButton:enabled { color: #27AE60; font-weight: 600; }")
        self.repay_btn.clicked.connect(self._record_repayment)
        btn_row.addWidget(self.repay_btn)

        self.view_btn = QPushButton("View Details")
        self.view_btn.setFixedHeight(34)
        self.view_btn.setEnabled(False)
        self.view_btn.clicked.connect(self._view_loan)
        btn_row.addWidget(self.view_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.loans_table.selectionModel().selectionChanged.connect(self._on_loan_selection)

        self.loans_summary = QLabel()
        self.loans_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.loans_summary)

        return w

    def _repayments_tab(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()

        self.rep_search = QLineEdit()
        self.rep_search.setPlaceholderText("Search by member name or ID...")
        self.rep_search.setFixedHeight(36)
        self.rep_search.textChanged.connect(self._load_repayments)
        filter_row.addWidget(self.rep_search, 2)

        self.rep_station_filter = QComboBox()
        self.rep_station_filter.setFixedHeight(36)
        self.rep_station_filter.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            self.rep_station_filter.addItem(s['station_name'], s['station_id'])
        self.rep_station_filter.currentIndexChanged.connect(self._load_repayments)
        filter_row.addWidget(self.rep_station_filter, 1)

        self.rep_date_from = QDateEdit()
        self.rep_date_from.setFixedHeight(36)
        self.rep_date_from.setCalendarPopup(True)
        self.rep_date_from.setDate(QDate(2000, 1, 1))
        self.rep_date_from.setDisplayFormat("dd/MM/yyyy")
        self.rep_date_from.dateChanged.connect(self._load_repayments)
        filter_row.addWidget(self.rep_date_from)

        self.rep_date_to = QDateEdit()
        self.rep_date_to.setFixedHeight(36)
        self.rep_date_to.setCalendarPopup(True)
        self.rep_date_to.setDate(QDate.currentDate())
        self.rep_date_to.setDisplayFormat("dd/MM/yyyy")
        self.rep_date_to.dateChanged.connect(self._load_repayments)
        filter_row.addWidget(self.rep_date_to)

        layout.addLayout(filter_row)

        self.rep_table = QTableWidget()
        self.rep_table.setColumnCount(8)
        self.rep_table.setHorizontalHeaderLabels([
            "Date", "Member ID", "Member Name", "Station",
            "Loan No", "Amount Paid", "Balance Before", "Balance After"
        ])
        self.rep_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rep_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rep_table.setAlternatingRowColors(True)
        self.rep_table.verticalHeader().setVisible(False)
        self.rep_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rep_table)

        self.rep_summary = QLabel()
        self.rep_summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.rep_summary)

        return w

    def _disburse_tab(self) -> QWidget:
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 12, 8, 20)
        layout.setSpacing(20)

        form_group = QGroupBox("New Loan Disbursement")
        form       = QFormLayout(form_group)
        form.setSpacing(14)
        form.setVerticalSpacing(14)
        form.setContentsMargins(16, 20, 16, 20)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.dis_member_input = QLineEdit()
        self.dis_member_input.setFixedHeight(36)
        self.dis_member_input.setPlaceholderText("e.g. NFC0001")
        self.dis_member_input.textChanged.connect(self._lookup_member)
        form.addRow("Member ID:", self.dis_member_input)

        self.dis_member_lbl = QLabel("—")
        self.dis_member_lbl.setStyleSheet("color: #7F8C8D;")
        form.addRow("Name:", self.dis_member_lbl)

        self.dis_type_combo = QComboBox()
        self.dis_type_combo.setFixedHeight(36)
        for lt in self.db.get_loan_types():
            self.dis_type_combo.addItem(
                f"{lt['type_name']} ({lt['interest_rate']}% / {lt['max_duration_months']} months max)",
                lt
            )
        self.dis_type_combo.currentIndexChanged.connect(self._on_loan_type_change)
        form.addRow("Loan Type:", self.dis_type_combo)

        self.dis_principal = QDoubleSpinBox()
        self.dis_principal.setFixedHeight(36)
        self.dis_principal.setRange(1000, 99_999_999)
        self.dis_principal.setDecimals(2)
        self.dis_principal.setPrefix(f"{self.currency} ")
        self.dis_principal.setSingleStep(10000)
        self.dis_principal.valueChanged.connect(self._update_loan_preview)
        form.addRow("Principal Amount:", self.dis_principal)

        self.dis_rate = QDoubleSpinBox()
        self.dis_rate.setFixedHeight(36)
        self.dis_rate.setRange(0, 100)
        self.dis_rate.setDecimals(2)
        self.dis_rate.setSuffix(" %")
        self.dis_rate.valueChanged.connect(self._update_loan_preview)
        form.addRow("Interest Rate:", self.dis_rate)

        self.dis_duration = QSpinBox()
        self.dis_duration.setFixedHeight(36)
        self.dis_duration.setRange(1, 120)
        self.dis_duration.setSuffix(" months")
        self.dis_duration.valueChanged.connect(self._update_loan_preview)
        form.addRow("Duration:", self.dis_duration)

        self.dis_start = QDateEdit()
        self.dis_start.setFixedHeight(36)
        self.dis_start.setCalendarPopup(True)
        self.dis_start.setDate(QDate.currentDate())
        self.dis_start.setDisplayFormat("dd/MM/yyyy")
        self.dis_start.dateChanged.connect(self._update_loan_preview)
        form.addRow("Start Date:", self.dis_start)

        self.dis_method = QComboBox()
        self.dis_method.setFixedHeight(36)
        self.dis_method.addItems(["Cheque", "Cash", "Bank Transfer"])
        self.dis_method.currentTextChanged.connect(self._on_dis_method_change)
        form.addRow("Payment Method:", self.dis_method)

        self.dis_cheque = QLineEdit()
        self.dis_cheque.setFixedHeight(36)
        self.dis_cheque.setPlaceholderText("Cheque number")
        form.addRow("Cheque No:", self.dis_cheque)

        layout.addWidget(form_group)

        # Preview
        preview_group = QGroupBox("Loan Preview")
        pf            = QFormLayout(preview_group)
        pf.setSpacing(8)
        pf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.prev_interest  = QLabel("—")
        self.prev_total     = QLabel("—")
        self.prev_monthly   = QLabel("—")
        self.prev_end_date  = QLabel("—")

        self.prev_interest.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.prev_total.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.prev_monthly.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))

        pf.addRow("Interest Amount:", self.prev_interest)
        pf.addRow("Total Repayable:", self.prev_total)
        pf.addRow("Monthly Installment:", self.prev_monthly)
        pf.addRow("End Date:", self.prev_end_date)
        layout.addWidget(preview_group)

        disburse_btn = QPushButton("Disburse Loan")
        disburse_btn.setFixedHeight(44)
        disburse_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        disburse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        disburse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980B9; color: white;
                border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #3498DB; }
        """)
        disburse_btn.clicked.connect(self._disburse)
        layout.addWidget(disburse_btn)
        layout.addStretch()

        scroll.setWidget(w)
        outer_layout.addWidget(scroll)

        # trigger initial state
        self._on_loan_type_change()
        return outer

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

    def _selected_loan_id(self):
        row = self.loans_table.currentRow()
        if row < 0:
            return None
        item = self.loans_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_loan_selection(self):
        lid = self._selected_loan_id()
        has = lid is not None
        self.view_btn.setEnabled(has)
        if has:
            loan = self.db.get_loan(lid)
            self.repay_btn.setEnabled(loan and loan['status'] == 'Active')
        else:
            self.repay_btn.setEnabled(False)

    def _lookup_member(self, mid):
        mid = mid.strip().upper()
        if len(mid) >= 7:
            member = self.db.get_member(mid)
            if member:
                name = f"{member['first_name']} {member.get('middle_name','') or ''} {member['last_name']}".strip()
                self.dis_member_lbl.setText(name)
                self.dis_member_lbl.setStyleSheet("color: #27AE60;")
                return
        self.dis_member_lbl.setText("—")
        self.dis_member_lbl.setStyleSheet("color: #7F8C8D;")

    def _on_loan_type_change(self):
        lt = self.dis_type_combo.currentData()
        if lt:
            self.dis_rate.setValue(lt['interest_rate'])
            self.dis_duration.setMaximum(lt['max_duration_months'])
            self.dis_duration.setValue(lt['max_duration_months'])
        self._update_loan_preview()

    def _on_dis_method_change(self, method):
        self.dis_cheque.setVisible(method == "Cheque")

    def _update_loan_preview(self):
        principal = self.dis_principal.value()
        rate      = self.dis_rate.value()
        duration  = self.dis_duration.value()
        interest  = round(principal * (rate / 100), 2)
        total     = principal + interest
        monthly   = round(total / duration, 2) if duration > 0 else 0

        start_date = self.dis_start.date().toPyDate()
        end_date   = start_date + relativedelta(months=duration)

        self.prev_interest.setText(self._fmt(interest))
        self.prev_total.setText(self._fmt(total))
        self.prev_monthly.setText(self._fmt(monthly))
        self.prev_end_date.setText(end_date.strftime("%d/%m/%Y"))

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    def refresh(self):
        self._update_summary_cards()
        self._load_loans()
        self._load_repayments()

    def _update_summary_cards(self):
        while self.summary_row.count():
            item = self.summary_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = self.db.fetchall("""
            SELECT
                COUNT(*) as total_loans,
                SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END) as active_loans,
                SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completed_loans,
                ROUND(SUM(CASE WHEN status='Active' THEN balance_outstanding ELSE 0 END),2) as total_outstanding,
                ROUND(SUM(amount_paid),2) as total_collected
            FROM loans
        """)
        r = rows[0] if rows else {}

        cards = [
            ("Total Loans",       str(r.get('total_loans', 0)),             "#2C3E50"),
            ("Active Loans",      str(r.get('active_loans', 0)),             "#E67E22"),
            ("Completed Loans",   str(r.get('completed_loans', 0)),          "#27AE60"),
            ("Total Outstanding", self._fmt(r.get('total_outstanding', 0)), "#E74C3C"),
            ("Total Collected",   self._fmt(r.get('total_collected', 0)),   "#2980B9"),
        ]
        for label, value, color in cards:
            self.summary_row.addWidget(self._summary_card(label, value, color))

    def _load_loans(self):
        search     = self.search_input.text().strip()
        station_id = self.station_filter.currentData()
        type_id    = self.type_filter.currentData()
        status     = self.status_filter.currentText()

        q = """
            SELECT l.*, lt.type_name, lt.type_code,
                   m.first_name, m.middle_name, m.last_name, m.station_id
            FROM loans l
            JOIN loan_types lt ON l.loan_type_id=lt.loan_type_id
            JOIN members m ON l.member_id=m.member_id
            WHERE 1=1
        """
        params = []

        if search:
            terms = [t.strip() for t in search.replace(',', ' ').split() if t.strip()]
            for term in terms:
                q += """ AND (l.member_id LIKE ? OR m.first_name LIKE ?
                          OR m.last_name LIKE ?
                          OR (m.first_name || ' ' || COALESCE(m.middle_name,'') || ' ' || m.last_name) LIKE ?)"""
                like = f"%{term}%"
                params.extend([like, like, like, like])

        if station_id:
            q += " AND m.station_id=?"
            params.append(station_id)

        if type_id:
            q += " AND l.loan_type_id=?"
            params.append(type_id)

        if status != "All":
            q += " AND l.status=?"
            params.append(status)

        q += " ORDER BY l.created_date DESC, l.loan_id DESC"
        loans = self.db.fetchall(q, tuple(params))

        stations = {s['station_id']: s['station_name']
                    for s in self.db.get_all_stations(enabled_only=False)}

        self.loans_table.setRowCount(len(loans))
        total_outstanding = total_principal = 0.0

        for row, l in enumerate(loans):
            full_name = ' '.join(filter(None, [
                l['first_name'], l.get('middle_name'), l['last_name']
            ]))

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            loan_item = cell(l['loan_number'])
            loan_item.setData(Qt.ItemDataRole.UserRole, l['loan_id'])
            self.loans_table.setItem(row, 0, loan_item)
            self.loans_table.setItem(row, 1, cell(l['member_id']))
            self.loans_table.setItem(row, 2, cell(full_name))
            self.loans_table.setItem(row, 3, cell(stations.get(l['station_id'], l['station_id'])))
            self.loans_table.setItem(row, 4, cell(l['type_name']))

            principal    = float(l['principal_amount'] or 0)
            total        = float(l['total_amount'] or 0)
            paid         = float(l['amount_paid'] or 0)
            outstanding  = float(l['balance_outstanding'] or 0)
            total_principal    += principal
            total_outstanding  += outstanding

            self.loans_table.setItem(row, 5, cell(self._fmt(principal), Qt.AlignmentFlag.AlignRight))
            self.loans_table.setItem(row, 6, cell(self._fmt(total),     Qt.AlignmentFlag.AlignRight))
            self.loans_table.setItem(row, 7, cell(self._fmt(paid),      Qt.AlignmentFlag.AlignRight))

            out_item = cell(self._fmt(outstanding), Qt.AlignmentFlag.AlignRight)
            out_item.setForeground(QColor("#E74C3C") if outstanding > 0 else QColor("#27AE60"))
            self.loans_table.setItem(row, 8, out_item)

            status_item = cell(l['status'])
            status_item.setForeground(
                QColor("#27AE60") if l['status'] == 'Completed' else
                QColor("#E67E22") if l['status'] == 'Active' else QColor("#7F8C8D")
            )
            self.loans_table.setItem(row, 9, status_item)

        self.loans_table.resizeColumnsToContents()
        self.loans_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.loans_summary.setText(
            f"{len(loans)} loan(s) shown  —  "
            f"Principal: {self._fmt(total_principal)}  |  "
            f"Outstanding: {self._fmt(total_outstanding)}"
        )

    def _load_repayments(self):
        search     = self.rep_search.text().strip()
        station_id = self.rep_station_filter.currentData()
        date_from  = self.rep_date_from.date().toString("yyyy-MM-dd")
        date_to    = self.rep_date_to.date().toString("yyyy-MM-dd")

        q = """
            SELECT r.*, l.loan_number, m.first_name, m.middle_name, m.last_name, m.station_id
            FROM loan_repayments r
            JOIN loans l ON r.loan_id=l.loan_id
            JOIN members m ON r.member_id=m.member_id
            WHERE r.payment_date >= ? AND r.payment_date <= ?
        """
        params = [date_from, date_to]

        if search:
            terms = [t.strip() for t in search.replace(',', ' ').split() if t.strip()]
            for term in terms:
                q += """ AND (r.member_id LIKE ? OR m.first_name LIKE ?
                          OR m.last_name LIKE ?
                          OR (m.first_name || ' ' || COALESCE(m.middle_name,'') || ' ' || m.last_name) LIKE ?)"""
                like = f"%{term}%"
                params.extend([like, like, like, like])

        if station_id:
            q += " AND m.station_id=?"
            params.append(station_id)

        q += " ORDER BY r.payment_date DESC, r.repayment_id DESC"
        repayments = self.db.fetchall(q, tuple(params))

        stations = {s['station_id']: s['station_name']
                    for s in self.db.get_all_stations(enabled_only=False)}

        self.rep_table.setRowCount(len(repayments))
        total_paid = 0.0

        for row, r in enumerate(repayments):
            full_name = ' '.join(filter(None, [
                r['first_name'], r.get('middle_name'), r['last_name']
            ]))
            paid = float(r['actual_amount'] or 0)
            total_paid += paid

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            self.rep_table.setItem(row, 0, cell(r['payment_date']))
            self.rep_table.setItem(row, 1, cell(r['member_id']))
            self.rep_table.setItem(row, 2, cell(full_name))
            self.rep_table.setItem(row, 3, cell(stations.get(r['station_id'], r['station_id'] or "")))
            self.rep_table.setItem(row, 4, cell(r['loan_number']))
            self.rep_table.setItem(row, 5, cell(self._fmt(paid),                           Qt.AlignmentFlag.AlignRight))
            self.rep_table.setItem(row, 6, cell(self._fmt(r['balance_before'] or 0),       Qt.AlignmentFlag.AlignRight))
            self.rep_table.setItem(row, 7, cell(self._fmt(r['balance_after'] or 0),        Qt.AlignmentFlag.AlignRight))

        self.rep_table.resizeColumnsToContents()
        self.rep_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.rep_summary.setText(
            f"{len(repayments)} repayment(s)  —  Total collected: {self._fmt(total_paid)}"
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _record_repayment(self):
        lid = self._selected_loan_id()
        if not lid:
            return
        loan   = self.db.get_loan(lid)
        member = self.db.get_member(loan['member_id'])
        if not loan or not member:
            return
        dlg = RepaymentDialog(loan, member, self.currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data      = dlg.data()
            full_name = f"{member['first_name']} {member['last_name']}"
            if not self._confirm(
                "Confirm Repayment",
                f"Record repayment of {self._fmt(data['amount'])} for {full_name}?\n\n"
                f"Loan: {loan['loan_number']}\n"
                f"Current outstanding: {self._fmt(loan['balance_outstanding'])}"
            ):
                return
            try:
                self.db.record_loan_repayment(
                    lid, data['amount'],
                    {'payment_date':   data['payment_date'],
                     'payment_method': data['method'],
                     'cheque_number':  data.get('cheque_number'),
                     'receipt_number': data.get('receipt_number')},
                    self.user['username']
                )
                QMessageBox.information(
                    self, "Repayment Recorded",
                    f"Repayment of {self._fmt(data['amount'])} recorded successfully."
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to record repayment:\n{e}")

    def _view_loan(self):
        lid = self._selected_loan_id()
        if not lid:
            return
        loan   = self.db.get_loan(lid)
        member = self.db.get_member(loan['member_id'])
        if not loan or not member:
            return
        LoanDetailDialog(self.db, loan, member, self.currency, parent=self).exec()

    def _disburse(self):
        mid = self.dis_member_input.text().strip().upper()
        if not mid:
            QMessageBox.warning(self, "Validation", "Member ID is required.")
            return
        member = self.db.get_member(mid)
        if not member:
            QMessageBox.warning(self, "Validation", f"Member '{mid}' not found.")
            return
        if not member['is_active'] or member['is_deceased']:
            QMessageBox.warning(self, "Validation",
                                "Cannot disburse loan to an inactive or deceased member.")
            return

        lt        = self.dis_type_combo.currentData()
        principal = self.dis_principal.value()
        rate      = self.dis_rate.value()
        duration  = self.dis_duration.value()
        interest  = round(principal * (rate / 100), 2)
        total     = principal + interest
        monthly   = round(total / duration, 2)
        start     = self.dis_start.date().toPyDate()
        end       = start + relativedelta(months=duration)

        if self.dis_method.currentText() == "Cheque" and not self.dis_cheque.text().strip():
            QMessageBox.warning(self, "Validation", "Cheque number is required.")
            return

        full_name = f"{member['first_name']} {member['last_name']}"
        if not self._confirm(
            "Confirm Loan Disbursement",
            f"Disburse loan to {full_name} ({mid})?\n\n"
            f"Type: {lt['type_name']}\n"
            f"Principal: {self._fmt(principal)}\n"
            f"Interest: {self._fmt(interest)} ({rate}%)\n"
            f"Total: {self._fmt(total)}\n"
            f"Monthly: {self._fmt(monthly)}\n"
            f"Duration: {duration} months\n"
            f"End Date: {end.strftime('%d/%m/%Y')}"
        ):
            return

        try:
            lid = self.db.disburse_loan({
                'member_id':        mid,
                'station_id':       member['station_id'],
                'loan_type_id':     lt['loan_type_id'],
                'principal_amount': principal,
                'interest_rate':    rate,
                'duration_months':  duration,
                'start_date':       start.isoformat(),
                'end_date':         end.isoformat(),
                'cheque_number':    self.dis_cheque.text().strip() or None,
                'payment_method':   self.dis_method.currentText(),
            }, self.user['username'])
            QMessageBox.information(
                self, "Loan Disbursed",
                f"Loan disbursed successfully.\nLoan ID: {lid}"
            )
            self.dis_member_input.clear()
            self.dis_principal.setValue(1000)
            self.refresh()
            self.tabs.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to disburse loan:\n{e}")


# ---------------------------------------------------------------------------
# Repayment dialog
# ---------------------------------------------------------------------------

class RepaymentDialog(QDialog):
    def __init__(self, loan, member, currency, parent=None):
        super().__init__(parent)
        self.loan     = loan
        self.currency = currency
        self.setWindowTitle(f"Record Repayment — {loan['loan_number']}")
        self.setFixedWidth(420)
        self._setup_ui(member)

    def _setup_ui(self, member):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        full_name = f"{member['first_name']} {member.get('middle_name','') or ''} {member['last_name']}".strip()

        info = QGroupBox("Loan Details")
        form = QFormLayout(info)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Member:", QLabel(f"{member['member_id']} — {full_name}"))
        form.addRow("Loan No:", QLabel(self.loan['loan_number']))

        bal = float(self.loan['balance_outstanding'])
        bal_lbl = QLabel(f"{self.currency}{bal:,.2f}")
        bal_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        bal_lbl.setStyleSheet("color: #E74C3C;")
        form.addRow("Outstanding:", bal_lbl)

        monthly = float(self.loan['monthly_installment'])
        form.addRow("Monthly Installment:", QLabel(f"{self.currency}{monthly:,.2f}"))
        layout.addWidget(info)

        txn = QGroupBox("Payment Details")
        tf  = QFormLayout(txn)
        tf.setSpacing(10)
        tf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setFixedHeight(36)
        self.amount_input.setRange(0.01, bal)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix(f"{self.currency} ")
        self.amount_input.setValue(min(monthly, bal))
        self.amount_input.setSingleStep(1000)
        tf.addRow("Amount:", self.amount_input)

        self.date_input = QDateEdit()
        self.date_input.setFixedHeight(36)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        tf.addRow("Payment Date:", self.date_input)

        self.method_combo = QComboBox()
        self.method_combo.setFixedHeight(36)
        self.method_combo.addItems(["Cash", "Cheque", "Bank Transfer"])
        self.method_combo.currentTextChanged.connect(self._on_method_change)
        tf.addRow("Payment Method:", self.method_combo)

        self.cheque_input = QLineEdit()
        self.cheque_input.setFixedHeight(36)
        self.cheque_input.setPlaceholderText("Cheque number")
        self.cheque_input.setVisible(False)
        tf.addRow("Cheque No:", self.cheque_input)

        self.receipt_input = QLineEdit()
        self.receipt_input.setFixedHeight(36)
        self.receipt_input.setPlaceholderText("Optional")
        tf.addRow("Receipt No:", self.receipt_input)

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
            'amount':         self.amount_input.value(),
            'payment_date':   self.date_input.date().toString("yyyy-MM-dd"),
            'method':         self.method_combo.currentText(),
            'cheque_number':  self.cheque_input.text().strip() or None,
            'receipt_number': self.receipt_input.text().strip() or None,
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
# Loan detail dialog
# ---------------------------------------------------------------------------

class LoanDetailDialog(QDialog):
    def __init__(self, db, loan, member, currency, parent=None):
        super().__init__(parent)
        self.db       = db
        self.loan     = loan
        self.currency = currency
        self.setWindowTitle(f"Loan Details — {loan['loan_number']}")
        self.setMinimumWidth(640)
        self.setMinimumHeight(500)
        self._setup_ui(member)

    def _setup_ui(self, member):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        l        = self.loan
        tabs     = QTabWidget()
        currency = self.currency

        # Loan summary
        summary = QWidget()
        sf      = QFormLayout(summary)
        sf.setContentsMargins(12, 12, 12, 12)
        sf.setSpacing(10)
        sf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        full_name = f"{member['first_name']} {member.get('middle_name','') or ''} {member['last_name']}".strip()
        for label, val in [
            ("Member:",          f"{member['member_id']} — {full_name}"),
            ("Loan Number:",     l['loan_number']),
            ("Status:",          l['status']),
            ("Principal:",       f"{currency}{float(l['principal_amount']):,.2f}"),
            ("Interest Rate:",   f"{l['interest_rate']}%"),
            ("Interest Amount:", f"{currency}{float(l['interest_amount']):,.2f}"),
            ("Total Repayable:", f"{currency}{float(l['total_amount']):,.2f}"),
            ("Monthly Install:", f"{currency}{float(l['monthly_installment']):,.2f}"),
            ("Duration:",        f"{l['duration_months']} months"),
            ("Start Date:",      l['start_date']),
            ("End Date:",        l['end_date']),
            ("Amount Paid:",     f"{currency}{float(l['amount_paid']):,.2f}"),
            ("Outstanding:",     f"{currency}{float(l['balance_outstanding']):,.2f}"),
        ]:
            lbl = QLabel(val)
            if label in ("Outstanding:", "Total Repayable:"):
                lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            sf.addRow(label, lbl)

        tabs.addTab(summary, "Summary")

        # Repayment history
        repayments = self.db.get_loan_repayments(l['loan_id'])
        rep_tab    = QWidget()
        rl         = QVBoxLayout(rep_tab)
        rl.setContentsMargins(8, 8, 8, 8)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Date", "Amount", "Balance Before", "Balance After", "Method"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setRowCount(len(repayments))

        for row, r in enumerate(repayments):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item
            table.setItem(row, 0, cell(r['payment_date']))
            table.setItem(row, 1, cell(f"{currency}{float(r['actual_amount']):,.2f}", Qt.AlignmentFlag.AlignRight))
            table.setItem(row, 2, cell(f"{currency}{float(r['balance_before']):,.2f}", Qt.AlignmentFlag.AlignRight))
            table.setItem(row, 3, cell(f"{currency}{float(r['balance_after']):,.2f}",  Qt.AlignmentFlag.AlignRight))
            table.setItem(row, 4, cell(r['payment_method'] or ""))

        rl.addWidget(table)
        tabs.addTab(rep_tab, f"Repayments ({len(repayments)})")

        layout.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)