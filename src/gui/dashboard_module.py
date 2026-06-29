from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class DashboardModule(QWidget):
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
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.layout_ = QVBoxLayout(container)
        self.layout_.setContentsMargins(24, 20, 24, 20)
        self.layout_.setSpacing(20)

        # Header
        org   = self.db.get_setting('organization_name') or 'NFC Cooperative'
        title = QLabel(f"Welcome, {self.user['username']}")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        sub   = QLabel(f"{org}  —  Cooperative Management System")
        sub.setStyleSheet("color: #7F8C8D;")
        self.layout_.addWidget(title)
        self.layout_.addWidget(sub)

        # Summary cards row
        self.cards_row = QHBoxLayout()
        self.cards_row.setSpacing(14)
        self.layout_.addLayout(self.cards_row)

        # Two-column section
        cols = QHBoxLayout()
        cols.setSpacing(20)

        left  = QVBoxLayout()
        right = QVBoxLayout()

        self.recent_group   = QGroupBox("Recent Transactions")
        self.members_group  = QGroupBox("Members by Station")
        self.savings_group  = QGroupBox("Savings by Type")
        self.quickact_group = QGroupBox("Quick Actions")

        left.addWidget(self.recent_group)
        left.addWidget(self.members_group)
        right.addWidget(self.savings_group)
        right.addWidget(self.quickact_group)

        cols.addLayout(left, 3)
        cols.addLayout(right, 2)
        self.layout_.addLayout(cols)
        self.layout_.addStretch()

    # -------------------------------------------------------------------------
    # Cards
    # -------------------------------------------------------------------------

    def _card(self, label: str, value: str, sub: str, color: str,
               slot: int = None) -> QGroupBox:
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {color};
                border-radius: 8px;
                padding: 12px 10px 10px 10px;
                background-color: transparent;
            }}
            QGroupBox:hover {{ background-color: #2D2D32; }}
        """)
        inner = QVBoxLayout(card)
        inner.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #7F8C8D; font-size: 10pt;")

        val = QLabel(value)
        val.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {color};")

        s = QLabel(sub)
        s.setStyleSheet("color: #7F8C8D; font-size: 9pt;")

        inner.addWidget(lbl)
        inner.addWidget(val)
        inner.addWidget(s)

        if slot is not None and hasattr(self.app, 'main_window'):
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda e, sl=slot: self._navigate(sl)

        return card

    def _navigate(self, slot: int):
        if hasattr(self.app, 'main_window'):
            self.app.main_window.switch_to(slot)

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    def refresh(self):
        self._load_cards()
        self._load_recent_transactions()
        self._load_members_by_station()
        self._load_savings_by_type()
        self._load_quick_actions()

    def _load_cards(self):
        # clear
        while self.cards_row.count():
            item = self.cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        currency = self.currency

        members = self.db.fetchone("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_active=1 AND is_deceased=0 THEN 1 ELSE 0 END) as active
            FROM members
        """)
        savings = self.db.fetchone("""
            SELECT ROUND(SUM(current_balance),2) as total
            FROM savings_accounts WHERE is_active=1
        """)
        loans = self.db.fetchone("""
            SELECT COUNT(CASE WHEN status='Active' THEN 1 END) as active_loans,
                   ROUND(SUM(CASE WHEN status='Active' THEN balance_outstanding ELSE 0 END),2) as outstanding
            FROM loans
        """)

        txns = self.db.fetchone("""
            SELECT COUNT(*) as total FROM transactions
        """)

        cards = [
            ("Active Members",      str(members['active'] or 0),
             f"of {members['total']} total", "#2980B9", 2),
            ("Total Savings",
             f"{currency}{float(savings['total'] or 0):,.0f}",
             "across all accounts", "#27AE60", 3),
            ("Active Loans",        str(loans['active_loans'] or 0),
             "outstanding loans", "#E67E22", 4),
            ("Loan Outstanding",
             f"{currency}{float(loans['outstanding'] or 0):,.0f}",
             "total balance", "#E74C3C", 4),
            ("Transactions",        f"{int(txns['total'] or 0):,}",
             "total recorded", "#8E44AD", 5),
        ]

        for label, value, sub, color, slot in cards:
            self.cards_row.addWidget(self._card(label, value, sub, color, slot))

    def _load_recent_transactions(self):
        layout = self.recent_group.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.recent_group)
            layout.setContentsMargins(10, 14, 10, 10)
            layout.setSpacing(6)

        txns = self.db.fetchall("""
            SELECT t.transaction_date, t.transaction_type,
                   t.amount, t.is_credit,
                   m.first_name || ' ' || m.last_name AS full_name
            FROM transactions t
            LEFT JOIN members m ON t.member_id=m.member_id
            ORDER BY t.transaction_id DESC
            LIMIT 10
        """)

        if not txns:
            lbl = QLabel("No transactions recorded yet.")
            lbl.setStyleSheet("color: #7F8C8D;")
            layout.addWidget(lbl)
            return

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Date", "Member", "Type", "Amount"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(txns))

        for row, t in enumerate(txns):
            amount    = float(t['amount'] or 0)
            is_credit = bool(t['is_credit'])

            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            table.setItem(row, 0, cell(t['transaction_date']))
            table.setItem(row, 1, cell(t['full_name'] or "—"))
            table.setItem(row, 2, cell(t['transaction_type']))
            amt_item = cell(f"{self.currency}{amount:,.0f}", Qt.AlignmentFlag.AlignRight)
            amt_item.setForeground(QColor("#27AE60") if is_credit else QColor("#E74C3C"))
            table.setItem(row, 3, amt_item)

        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setFixedHeight(min(len(txns) * 30 + 30, 340))
        layout.addWidget(table)

    def _load_members_by_station(self):
        layout = self.members_group.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.members_group)
            layout.setContentsMargins(10, 14, 10, 10)
            layout.setSpacing(6)

        rows = self.db.fetchall("""
            SELECT s.station_name,
                   SUM(CASE WHEN m.is_active=1 AND m.is_deceased=0 THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN m.is_active=0 AND m.is_deceased=0 THEN 1 ELSE 0 END) as inactive,
                   SUM(CASE WHEN m.is_deceased=1 THEN 1 ELSE 0 END) as deceased,
                   COUNT(*) as total
            FROM members m
            JOIN stations s ON m.station_id=s.station_id
            GROUP BY s.station_id
            ORDER BY s.station_id
        """)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Station", "Active", "Inactive", "Deceased", "Total"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(rows))

        for row, r in enumerate(rows):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val) if val else "0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item
            table.setItem(row, 0, cell(r['station_name']))
            table.setItem(row, 1, cell(r['active'],   Qt.AlignmentFlag.AlignCenter))
            table.setItem(row, 2, cell(r['inactive'], Qt.AlignmentFlag.AlignCenter))
            table.setItem(row, 3, cell(r['deceased'], Qt.AlignmentFlag.AlignCenter))
            table.setItem(row, 4, cell(r['total'],    Qt.AlignmentFlag.AlignCenter))

        table.setFixedHeight(len(rows) * 30 + 36)
        layout.addWidget(table)

    def _load_savings_by_type(self):
        layout = self.savings_group.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.savings_group)
            layout.setContentsMargins(10, 14, 10, 10)
            layout.setSpacing(6)

        rows = self.db.fetchall("""
            SELECT st.type_name, COUNT(*) as accounts,
                   ROUND(SUM(sa.current_balance),2) as total
            FROM savings_accounts sa
            JOIN savings_types st ON sa.savings_type_id=st.savings_type_id
            WHERE sa.is_active=1
            GROUP BY st.savings_type_id
            ORDER BY total DESC
        """)

        currency = self.currency
        for r in rows:
            row_w  = QWidget()
            row_l  = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 2, 0, 2)
            name   = QLabel(r['type_name'])
            name.setStyleSheet("font-size: 10pt;")
            amount = QLabel(f"{currency}{float(r['total'] or 0):,.0f}")
            amount.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            amount.setStyleSheet("color: #27AE60;")
            count  = QLabel(f"({r['accounts']} accounts)")
            count.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
            row_l.addWidget(name)
            row_l.addStretch()
            row_l.addWidget(count)
            row_l.addWidget(amount)
            layout.addWidget(row_w)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("border: none; border-top: 1px solid #3D3D42;")
            layout.addWidget(sep)

    def _load_quick_actions(self):
        layout = self.quickact_group.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.quickact_group)
            layout.setContentsMargins(10, 14, 10, 10)
            layout.setSpacing(8)

        u = self.user
        actions = []

        if u.get('can_maintain'):
            actions.append(("Add Member",         2))
            actions.append(("Manage Stations",     1))
        if u.get('can_operate'):
            actions.append(("Record Deposit",      3))
            actions.append(("Disburse Loan",       4))
            actions.append(("Record Repayment",    4))
        if u.get('can_view_reports'):
            actions.append(("Generate Reports",    6))

        for label, slot in actions:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D32;
                    border: 1px solid #3D3D42;
                    border-radius: 4px;
                    color: #E6E6EB;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #3D3D42;
                    border-color: #2980B9;
                    color: #3498DB;
                }
            """)
            btn.clicked.connect(lambda _, s=slot: self._navigate(s))
            layout.addWidget(btn)