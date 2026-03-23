import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QComboBox, QDateEdit, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from reports.report_generator import ReportGenerator


class ReportWorker(QThread):
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn     = fn
        self.args   = args
        self.kwargs = kwargs

    def run(self):
        try:
            path = self.fn(*self.args, **self.kwargs)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class ReportsModule(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app  = app
        self.db   = app.db_manager
        self.user = app.current_user
        self.rg   = ReportGenerator(app.db_manager.db_path)
        self._setup_ui()
        self._load_history()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Reports")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._members_tab(),      "Members")
        self.tabs.addTab(self._savings_tab(),      "Savings")
        self.tabs.addTab(self._loans_tab(),        "Loans")
        self.tabs.addTab(self._statement_tab(),    "Member Statement")
        self.tabs.addTab(self._transactions_tab(), "Transactions")
        self.tabs.addTab(self._history_tab(),      "Generated Reports")
        layout.addWidget(self.tabs)

    def _station_combo(self) -> QComboBox:
        cb = QComboBox()
        cb.setFixedHeight(36)
        cb.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            cb.addItem(s['station_name'], s['station_id'])
        return cb

    def _format_combo(self) -> QComboBox:
        cb = QComboBox()
        cb.setFixedHeight(36)
        cb.addItems(["PDF", "Excel"])
        return cb

    def _generate_btn(self, label="Generate Report") -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(42)
        btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2980B9; color: white;
                border: none; border-radius: 4px;
            }
            QPushButton:hover   { background-color: #3498DB; }
            QPushButton:pressed { background-color: #21618C; }
            QPushButton:disabled { background-color: #555; color: #999; }
        """)
        return btn

    def _progress_bar(self) -> QProgressBar:
        pb = QProgressBar()
        pb.setFixedHeight(8)
        pb.setRange(0, 0)
        pb.setVisible(False)
        pb.setStyleSheet("QProgressBar { border: none; background: #3D3D42; border-radius: 4px; }"
                         "QProgressBar::chunk { background: #2980B9; border-radius: 4px; }")
        return pb

    # -------------------------------------------------------------------------
    # Tab builders
    # -------------------------------------------------------------------------

    def _members_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        grp  = QGroupBox("Members List Report")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.mem_station = self._station_combo()
        self.mem_status  = QComboBox()
        self.mem_status.setFixedHeight(36)
        self.mem_status.addItems(["Active", "Inactive", "Deceased", "All"])
        self.mem_format  = self._format_combo()

        form.addRow("Station:", self.mem_station)
        form.addRow("Status:",  self.mem_status)
        form.addRow("Format:",  self.mem_format)
        layout.addWidget(grp)

        self.mem_progress = self._progress_bar()
        layout.addWidget(self.mem_progress)

        btn = self._generate_btn()
        btn.clicked.connect(self._generate_members)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _savings_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        grp  = QGroupBox("Savings Summary Report")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.sav_station = self._station_combo()
        self.sav_format  = self._format_combo()

        form.addRow("Station:", self.sav_station)
        form.addRow("Format:",  self.sav_format)
        layout.addWidget(grp)

        self.sav_progress = self._progress_bar()
        layout.addWidget(self.sav_progress)

        btn = self._generate_btn()
        btn.clicked.connect(self._generate_savings)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _loans_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        grp  = QGroupBox("Loans Summary Report")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.loan_station = self._station_combo()
        self.loan_status  = QComboBox()
        self.loan_status.setFixedHeight(36)
        self.loan_status.addItems(["Active", "Completed", "All"])
        self.loan_format  = self._format_combo()

        form.addRow("Station:", self.loan_station)
        form.addRow("Status:",  self.loan_status)
        form.addRow("Format:",  self.loan_format)
        layout.addWidget(grp)

        self.loan_progress = self._progress_bar()
        layout.addWidget(self.loan_progress)

        btn = self._generate_btn()
        btn.clicked.connect(self._generate_loans)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _statement_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        grp  = QGroupBox("Member Statement (PDF)")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.stmt_member = QLineEdit()
        self.stmt_member.setFixedHeight(36)
        self.stmt_member.setPlaceholderText("e.g. NFC0001")
        self.stmt_member.textChanged.connect(self._lookup_statement_member)

        self.stmt_member_lbl = QLabel("—")
        self.stmt_member_lbl.setStyleSheet("color: #7F8C8D;")

        form.addRow("Member ID:", self.stmt_member)
        form.addRow("Name:",      self.stmt_member_lbl)
        layout.addWidget(grp)

        self.stmt_progress = self._progress_bar()
        layout.addWidget(self.stmt_progress)

        btn = self._generate_btn("Generate Statement")
        btn.clicked.connect(self._generate_statement)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _transactions_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        grp  = QGroupBox("Transaction Report")
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txn_station = self._station_combo()
        self.txn_format  = self._format_combo()

        self.txn_member = QLineEdit()
        self.txn_member.setFixedHeight(36)
        self.txn_member.setPlaceholderText("Optional — leave blank for all members")

        self.txn_date_from = QDateEdit()
        self.txn_date_from.setFixedHeight(36)
        self.txn_date_from.setCalendarPopup(True)
        self.txn_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.txn_date_from.setDisplayFormat("dd/MM/yyyy")

        self.txn_date_to = QDateEdit()
        self.txn_date_to.setFixedHeight(36)
        self.txn_date_to.setCalendarPopup(True)
        self.txn_date_to.setDate(QDate.currentDate())
        self.txn_date_to.setDisplayFormat("dd/MM/yyyy")

        form.addRow("Station:",   self.txn_station)
        form.addRow("Member ID:", self.txn_member)
        form.addRow("Date From:", self.txn_date_from)
        form.addRow("Date To:",   self.txn_date_to)
        form.addRow("Format:",    self.txn_format)
        layout.addWidget(grp)

        self.txn_progress = self._progress_bar()
        layout.addWidget(self.txn_progress)

        btn = self._generate_btn()
        btn.clicked.connect(self._generate_transactions)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _history_tab(self) -> QWidget:
        w, layout = QWidget(), QVBoxLayout()
        w.setLayout(layout)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self._load_history)
        hdr.addWidget(refresh_btn)
        open_folder_btn = QPushButton("Open Reports Folder")
        open_folder_btn.setFixedHeight(32)
        open_folder_btn.clicked.connect(self._open_reports_folder)
        hdr.addWidget(open_folder_btn)
        layout.addLayout(hdr)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(
            ["Filename", "Type", "Size", "Generated"]
        )
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.doubleClicked.connect(self._open_selected_report)
        layout.addWidget(self.history_table)

        btn_row = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.setFixedHeight(34)
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_selected_report)
        btn_row.addWidget(self.open_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFixedHeight(34)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton:enabled { color: #E74C3C; }")
        self.delete_btn.clicked.connect(self._delete_selected_report)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.history_table.selectionModel().selectionChanged.connect(self._on_history_selection)
        return w

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _lookup_statement_member(self, mid):
        mid = mid.strip().upper()
        if len(mid) >= 7:
            member = self.db.get_member(mid)
            if member:
                name = f"{member['first_name']} {member.get('middle_name','') or ''} {member['last_name']}".strip()
                self.stmt_member_lbl.setText(name)
                self.stmt_member_lbl.setStyleSheet("color: #27AE60;")
                return
        self.stmt_member_lbl.setText("—")
        self.stmt_member_lbl.setStyleSheet("color: #7F8C8D;")

    def _run_worker(self, progress_bar: QProgressBar, btn, fn, *args, **kwargs):
        progress_bar.setVisible(True)
        btn.setEnabled(False)

        def on_done(path):
            progress_bar.setVisible(False)
            btn.setEnabled(True)
            self._load_history()
            reply = QMessageBox.question(
                self, "Report Generated",
                f"Report saved to:\n{path}\n\nOpen now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._open_file(path)

        def on_error(msg):
            progress_bar.setVisible(False)
            btn.setEnabled(True)
            QMessageBox.critical(self, "Report Error", f"Failed to generate report:\n{msg}")

        worker = ReportWorker(fn, *args, **kwargs)
        worker.finished.connect(on_done)
        worker.error.connect(on_error)
        worker.start()
        self._worker = worker  # keep reference

    def _open_file(self, path: str):
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])

    def _open_reports_folder(self):
        from reports.report_generator import REPORTS_DIR
        os.makedirs(REPORTS_DIR, exist_ok=True)
        self._open_file(REPORTS_DIR)

    def _on_history_selection(self):
        has = self.history_table.currentRow() >= 0
        self.open_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)

    def _selected_report_path(self) -> str:
        row = self.history_table.currentRow()
        if row < 0:
            return ""
        item = self.history_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    # -------------------------------------------------------------------------
    # Generate actions
    # -------------------------------------------------------------------------

    def _generate_members(self):
        station_id = self.mem_station.currentData()
        status     = self.mem_status.currentText()
        fmt        = self.mem_format.currentText()
        sender     = self.sender()
        fn = self.rg.members_list_pdf if fmt == "PDF" else self.rg.members_list_excel
        self._run_worker(self.mem_progress, sender, fn,
                         station_id=station_id, status=status)

    def _generate_savings(self):
        station_id = self.sav_station.currentData()
        fmt        = self.sav_format.currentText()
        sender     = self.sender()
        fn = self.rg.savings_summary_pdf if fmt == "PDF" else self.rg.savings_summary_excel
        self._run_worker(self.sav_progress, sender, fn, station_id=station_id)

    def _generate_loans(self):
        station_id = self.loan_station.currentData()
        status     = self.loan_status.currentText()
        fmt        = self.loan_format.currentText()
        sender     = self.sender()
        fn = self.rg.loans_summary_pdf if fmt == "PDF" else self.rg.loans_summary_excel
        self._run_worker(self.loan_progress, sender, fn,
                         station_id=station_id, status=status)

    def _generate_statement(self):
        mid = self.stmt_member.text().strip().upper()
        if not mid:
            QMessageBox.warning(self, "Validation", "Member ID is required.")
            return
        if not self.db.get_member(mid):
            QMessageBox.warning(self, "Validation", f"Member '{mid}' not found.")
            return
        sender = self.sender()
        self._run_worker(self.stmt_progress, sender,
                         self.rg.member_statement_pdf, mid)

    def _generate_transactions(self):
        station_id = self.txn_station.currentData()
        member_id  = self.txn_member.text().strip().upper() or None
        date_from  = self.txn_date_from.date().toString("yyyy-MM-dd")
        date_to    = self.txn_date_to.date().toString("yyyy-MM-dd")
        fmt        = self.txn_format.currentText()
        sender     = self.sender()

        if member_id and not self.db.get_member(member_id):
            QMessageBox.warning(self, "Validation", f"Member '{member_id}' not found.")
            return

        fn = (self.rg.transactions_report_pdf if fmt == "PDF"
              else self.rg.transactions_report_excel)
        self._run_worker(self.txn_progress, sender, fn,
                         start_date=date_from, end_date=date_to,
                         member_id=member_id, station_id=station_id)

    # -------------------------------------------------------------------------
    # History tab
    # -------------------------------------------------------------------------

    def _load_history(self):
        from reports.report_generator import REPORTS_DIR
        os.makedirs(REPORTS_DIR, exist_ok=True)

        files = []
        for f in os.listdir(REPORTS_DIR):
            path = os.path.join(REPORTS_DIR, f)
            if os.path.isfile(path) and f.endswith(('.pdf', '.xlsx')):
                stat  = os.stat(path)
                files.append({
                    'name':    f,
                    'path':    path,
                    'ext':     f.rsplit('.', 1)[-1].upper(),
                    'size':    stat.st_size,
                    'mtime':   stat.st_mtime,
                })
        files.sort(key=lambda x: x['mtime'], reverse=True)

        self.history_table.setRowCount(len(files))
        for row, f in enumerate(files):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | align)
                return item

            name_item = cell(f['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, f['path'])
            self.history_table.setItem(row, 0, name_item)
            self.history_table.setItem(row, 1, cell(f['ext']))
            self.history_table.setItem(row, 2, cell(
                f"{f['size'] / 1024:.1f} KB", Qt.AlignmentFlag.AlignRight
            ))
            import datetime
            self.history_table.setItem(row, 3, cell(
                datetime.datetime.fromtimestamp(f['mtime']).strftime('%d/%m/%Y %H:%M')
            ))

        self.history_table.resizeColumnsToContents()
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _open_selected_report(self):
        path = self._selected_report_path()
        if path and os.path.isfile(path):
            self._open_file(path)

    def _delete_selected_report(self):
        path = self._selected_report_path()
        if not path:
            return
        reply = QMessageBox.question(
            self, "Delete Report",
            f"Delete '{os.path.basename(path)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self._load_history()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")

    def refresh(self):
        self._load_history()