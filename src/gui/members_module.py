from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QComboBox, QCheckBox, QTabWidget, QDateEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


class MembersModule(QWidget):
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

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Members")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        if self._is_admin():
            add_btn = QPushButton("Add Member")
            add_btn.setFixedHeight(36)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._add_member)
            hdr.addWidget(add_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        # Search + filters
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or ID...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search)
        filter_row.addWidget(self.search_input, 2)

        self.station_filter = QComboBox()
        self.station_filter.setFixedHeight(36)
        self.station_filter.addItem("All Stations", None)
        for s in self.db.get_all_stations():
            self.station_filter.addItem(s['station_name'], s['station_id'])
        self.station_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.station_filter, 1)

        self.status_filter = QComboBox()
        self.status_filter.setFixedHeight(36)
        self.status_filter.addItems(["All", "Active", "Inactive", "Deceased"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.status_filter)

        layout.addLayout(filter_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Full Name", "Gender", "Station",
            "Date Joined", "Phone", "Grade", "Status"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._view_member)
        layout.addWidget(self.table)

        # Action buttons
        btn_row = QHBoxLayout()

        self.view_btn = QPushButton("View")
        self.view_btn.setFixedHeight(34)
        self.view_btn.setEnabled(False)
        self.view_btn.clicked.connect(self._view_member)
        btn_row.addWidget(self.view_btn)

        if self._is_admin():
            self.edit_btn = QPushButton("Edit")
            self.edit_btn.setFixedHeight(34)
            self.edit_btn.setEnabled(False)
            self.edit_btn.clicked.connect(self._edit_member)
            btn_row.addWidget(self.edit_btn)

            self.deactivate_btn = QPushButton("Deactivate")
            self.deactivate_btn.setFixedHeight(34)
            self.deactivate_btn.setEnabled(False)
            self.deactivate_btn.clicked.connect(self._deactivate_member)
            self.deactivate_btn.setStyleSheet("QPushButton:enabled { color: #E74C3C; }")
            btn_row.addWidget(self.deactivate_btn)

            self.reactivate_btn = QPushButton("Reactivate")
            self.reactivate_btn.setFixedHeight(34)
            self.reactivate_btn.setEnabled(False)
            self.reactivate_btn.clicked.connect(self._reactivate_member)
            self.reactivate_btn.setStyleSheet("QPushButton:enabled { color: #27AE60; }")
            btn_row.addWidget(self.reactivate_btn)

            self.deceased_btn = QPushButton("Mark Deceased")
            self.deceased_btn.setFixedHeight(34)
            self.deceased_btn.setEnabled(False)
            self.deceased_btn.clicked.connect(self._mark_deceased)
            self.deceased_btn.setStyleSheet("QPushButton:enabled { color: #8E44AD; }")
            btn_row.addWidget(self.deceased_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table.selectionModel().selectionChanged.connect(self._on_selection)

        self.summary = QLabel()
        self.summary.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.summary)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _is_admin(self) -> bool:
        return self.user.get('role') == 'Admin'

    def _confirm(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _severe_warning(self, title: str, warning: str, confirm_word: str) -> bool:
        from PyQt6.QtWidgets import QInputDialog
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("<b>WARNING — This action requires administrator authorisation.</b>")
        msg.setInformativeText(warning)
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return False
        text, ok = QInputDialog.getText(
            self, "Confirm Action",
            f"Type  {confirm_word}  to confirm:"
        )
        return ok and text.strip().upper() == confirm_word.upper()

    def _selected_member_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection(self):
        mid    = self._selected_member_id()
        has    = mid is not None
        self.view_btn.setEnabled(has)

        if self._is_admin():
            member   = self.db.get_member(mid) if mid else None
            is_active   = bool(member and member['is_active'] and not member['is_deceased'])
            is_inactive = bool(member and not member['is_active'] and not member['is_deceased'])
            self.edit_btn.setEnabled(has)
            self.deactivate_btn.setEnabled(is_active)
            self.reactivate_btn.setEnabled(is_inactive)
            self.deceased_btn.setEnabled(is_active)

    def _full_name(self, m) -> str:
        parts = [m['first_name'], m.get('middle_name'), m['last_name']]
        return ' '.join(p for p in parts if p)

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    def refresh(self):
        search        = self.search_input.text().strip()
        station_id    = self.station_filter.currentData()
        status_filter = self.status_filter.currentText()

        members = self.db.search_members(search) if search else self.db.get_all_members(active_only=False)

        if station_id:
            members = [m for m in members if m['station_id'] == station_id]

        if status_filter == "Active":
            members = [m for m in members if m['is_active'] and not m['is_deceased']]
        elif status_filter == "Inactive":
            members = [m for m in members if not m['is_active'] and not m['is_deceased']]
        elif status_filter == "Deceased":
            members = [m for m in members if m['is_deceased']]
        # "All" shows everything

        stations = {s['station_id']: s['station_name']
                    for s in self.db.get_all_stations(enabled_only=False)}

        self.table.setRowCount(len(members))
        for row, m in enumerate(members):
            def cell(val):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                return item

            id_item = cell(m['member_id'])
            id_item.setData(Qt.ItemDataRole.UserRole, m['member_id'])
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, cell(self._full_name(m)))
            self.table.setItem(row, 2, cell(m['gender'] or ""))
            self.table.setItem(row, 3, cell(stations.get(m['station_id'], m['station_id'])))
            self.table.setItem(row, 4, cell(m['date_joined'] or ""))
            self.table.setItem(row, 5, cell(m['phone_number'] or ""))
            self.table.setItem(row, 6, cell(m['grade_level'] or ""))

            if m['is_deceased']:
                status, color = "Deceased", QColor("#8E44AD")
            elif not m['is_active']:
                status, color = "Inactive", QColor("#E74C3C")
            else:
                status, color = "Active", QColor("#27AE60")

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.table.setItem(row, 7, status_item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        active   = sum(1 for m in members if m['is_active'] and not m['is_deceased'])
        inactive = sum(1 for m in members if not m['is_active'] and not m['is_deceased'])
        deceased = sum(1 for m in members if m['is_deceased'])
        self.summary.setText(
            f"{len(members)} member(s) shown  —  "
            f"Active: {active}  |  Inactive: {inactive}  |  Deceased: {deceased}"
        )

    def _on_search(self):
        self.refresh()

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _add_member(self):
        dlg = MemberDialog(self.db, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.data()
            if not self._confirm(
                "Confirm Add Member",
                f"Add new member '{d['first_name']} {d['last_name']}'?\n\n"
                "Note: Member IDs are permanent and never reassigned."
            ):
                return
            try:
                mid = self.db.add_member(d, self.user['username'])
                QMessageBox.information(self, "Member Added",
                                        f"Member added successfully.\nID: {mid}")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add member:\n{e}")

    def _edit_member(self):
        mid = self._selected_member_id()
        if not mid:
            return
        member = self.db.get_member(mid)
        if not member:
            return
        dlg = MemberDialog(self.db, member=member, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if not self._confirm("Confirm Edit Member",
                                 f"Save changes to '{self._full_name(member)}'?"):
                return
            try:
                self.db.update_member(mid, dlg.data(), self.user['username'])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update member:\n{e}")

    def _view_member(self):
        mid = self._selected_member_id()
        if not mid:
            return
        member = self.db.get_member(mid)
        if not member:
            return
        MemberViewDialog(self.db, member, parent=self).exec()

    def _deactivate_member(self):
        mid = self._selected_member_id()
        if not mid:
            return
        if not self._is_admin():
            QMessageBox.warning(self, "Access Denied", "Only administrators can deactivate members.")
            return
        member = self.db.get_member(mid)
        if not member:
            return
        name = self._full_name(member)
        if not self._severe_warning(
            "Deactivate Member",
            f"You are about to deactivate member {member['member_id']} — {name}.\n\n"
            "This will immediately suspend all operations for this member.\n"
            "They will no longer appear in active member lists.\n\n"
            "Their member ID is permanently retained and will NEVER be reassigned.\n\n"
            "You can reactivate them at any time.",
            "DEACTIVATE"
        ):
            return
        try:
            self.db.deactivate_member(mid, self.user['username'])
            self.refresh()
            QMessageBox.information(self, "Member Deactivated",
                                    f"{name} has been deactivated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to deactivate member:\n{e}")

    def _reactivate_member(self):
        mid = self._selected_member_id()
        if not mid:
            return
        if not self._is_admin():
            QMessageBox.warning(self, "Access Denied", "Only administrators can reactivate members.")
            return
        member = self.db.get_member(mid)
        if not member:
            return
        name = self._full_name(member)
        if not self._severe_warning(
            "Reactivate Member",
            f"You are about to reactivate member {member['member_id']} — {name}.\n\n"
            "This will restore their active status and allow all operations\n"
            "to resume for this member.\n\n"
            "Ensure all documentation is in order before proceeding.",
            "REACTIVATE"
        ):
            return
        try:
            self.db.reactivate_member(mid, self.user['username'])
            self.refresh()
            QMessageBox.information(self, "Member Reactivated",
                                    f"{name} has been reactivated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reactivate member:\n{e}")

    def _mark_deceased(self):
        mid = self._selected_member_id()
        if not mid:
            return
        if not self._is_admin():
            QMessageBox.warning(self, "Access Denied", "Only administrators can mark members as deceased.")
            return
        member = self.db.get_member(mid)
        if not member:
            return
        name = self._full_name(member)
        if not self._severe_warning(
            "Mark Member as Deceased",
            f"You are about to mark member {member['member_id']} — {name} — as DECEASED.\n\n"
            "THIS ACTION IS IRREVERSIBLE.\n\n"
            "The member will be permanently marked as deceased.\n"
            "All active operations for this member will be suspended.\n"
            "Their record will be retained for audit and historical purposes.\n\n"
            "The death benefit process must be completed separately from Settings.\n\n"
            "Only proceed if you have verified the member's death certificate.",
            "DECEASED"
        ):
            return
        try:
            self.db.mark_member_deceased(
                mid,
                QDate.currentDate().toString("yyyy-MM-dd"),
                self.user['username']
            )
            # auto-process death benefit
            benefit_msg = ""
            try:
                result = self.db.process_death_benefit(
                    mid, name, self.user['username']
                )
                currency = self.db.get_setting('currency_symbol') or '₦'
                lines = []
                if result['charge_per_member'] > 0:
                    lines.append(f"  Death charge per member: {currency}{result['charge_per_member']:,.2f}")
                    lines.append(f"  Members charged: {result['members_charged']}")
                    lines.append(f"  Total collected: {currency}{result['total_collected']:,.2f}")
                if result['benefit_payout'] > 0:
                    lines.append(f"  Death benefit paid to account: {currency}{result['benefit_payout']:,.2f}")
                if lines:
                    benefit_msg = "\n\nDeath benefit processed:\n" + "\n".join(lines)
            except Exception:
                pass  # death benefit disabled or zero amount
            self.refresh()
            QMessageBox.information(
                self, "Member Marked as Deceased",
                f"{name} has been marked as deceased.{benefit_msg}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to mark member as deceased:\n{e}")


# ---------------------------------------------------------------------------
# Member add / edit dialog
# ---------------------------------------------------------------------------

class MemberDialog(QDialog):
    def __init__(self, db, member=None, parent=None):
        super().__init__(parent)
        self.db     = db
        self.member = member
        self.setWindowTitle("Edit Member" if member else "Add Member")
        self.setMinimumWidth(540)
        self._setup_ui()
        if member:
            self._populate(member)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._personal_tab(), "Personal")
        tabs.addTab(self._contact_tab(),  "Contact")
        tabs.addTab(self._nok_tab(),      "Next of Kin")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _field(self, placeholder=""):
        f = QLineEdit()
        f.setFixedHeight(36)
        f.setPlaceholderText(placeholder)
        return f

    def _personal_tab(self):
        w    = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.first_name_input  = self._field("Required")
        self.middle_name_input = self._field("Optional")
        self.last_name_input   = self._field("Required")

        self.gender_combo = QComboBox()
        self.gender_combo.setFixedHeight(36)
        self.gender_combo.addItems(["Male", "Female"])

        self.station_combo = QComboBox()
        self.station_combo.setFixedHeight(36)
        for s in self.db.get_all_stations():
            self.station_combo.addItem(s['station_name'], s['station_id'])

        self.date_joined = QDateEdit()
        self.date_joined.setFixedHeight(36)
        self.date_joined.setCalendarPopup(True)
        self.date_joined.setDate(QDate.currentDate())
        self.date_joined.setDisplayFormat("dd/MM/yyyy")

        self.dob_input      = self._field("Optional (YYYY-MM-DD)")
        self.employee_input = self._field("Optional")
        self.grade_input    = self._field("Optional")

        form.addRow("First Name:",    self.first_name_input)
        form.addRow("Middle Name:",   self.middle_name_input)
        form.addRow("Last Name:",     self.last_name_input)
        form.addRow("Gender:",        self.gender_combo)
        form.addRow("Station:",       self.station_combo)
        form.addRow("Date Joined:",   self.date_joined)
        form.addRow("Date of Birth:", self.dob_input)
        form.addRow("Employee ID:",   self.employee_input)
        form.addRow("Grade Level:",   self.grade_input)
        return w

    def _contact_tab(self):
        w    = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.phone_input   = self._field("e.g. 08012345678")
        self.email_input   = self._field("Optional")
        self.address_input = self._field("Optional")

        form.addRow("Phone Number:", self.phone_input)
        form.addRow("Email:",        self.email_input)
        form.addRow("Address:",      self.address_input)
        return w

    def _nok_tab(self):
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        g1 = QGroupBox("Next of Kin 1")
        f1 = QFormLayout(g1)
        f1.setSpacing(8)
        f1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.nok1_name  = self._field("Full name")
        self.nok1_rel   = self._field("e.g. Wife, Son")
        self.nok1_addr  = self._field("Address")
        self.nok1_phone = self._field("Phone number")
        f1.addRow("Name:",         self.nok1_name)
        f1.addRow("Relationship:", self.nok1_rel)
        f1.addRow("Address:",      self.nok1_addr)
        f1.addRow("Phone:",        self.nok1_phone)
        layout.addWidget(g1)

        g2 = QGroupBox("Next of Kin 2 (Optional)")
        f2 = QFormLayout(g2)
        f2.setSpacing(8)
        f2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.nok2_name  = self._field("Full name")
        self.nok2_rel   = self._field("e.g. Wife, Son")
        self.nok2_addr  = self._field("Address")
        self.nok2_phone = self._field("Phone number")
        f2.addRow("Name:",         self.nok2_name)
        f2.addRow("Relationship:", self.nok2_rel)
        f2.addRow("Address:",      self.nok2_addr)
        f2.addRow("Phone:",        self.nok2_phone)
        layout.addWidget(g2)
        layout.addStretch()
        return w

    def _populate(self, m):
        self.first_name_input.setText(m['first_name'] or "")
        self.middle_name_input.setText(m['middle_name'] or "")
        self.last_name_input.setText(m['last_name'] or "")
        self.gender_combo.setCurrentText(m['gender'] or "Male")

        for i in range(self.station_combo.count()):
            if self.station_combo.itemData(i) == m['station_id']:
                self.station_combo.setCurrentIndex(i)
                break

        if m['date_joined']:
            self.date_joined.setDate(QDate.fromString(m['date_joined'], "yyyy-MM-dd"))

        self.dob_input.setText(m['date_of_birth'] or "")
        self.employee_input.setText(m['employee_id'] or "")
        self.grade_input.setText(m['grade_level'] or "")
        self.phone_input.setText(m['phone_number'] or "")
        self.email_input.setText(m['email'] or "")
        self.address_input.setText(m['address'] or "")
        self.nok1_name.setText(m['nok1_name'] or "")
        self.nok1_rel.setText(m['nok1_relationship'] or "")
        self.nok1_addr.setText(m['nok1_address'] or "")
        self.nok1_phone.setText(m['nok1_phone'] or "")
        self.nok2_name.setText(m['nok2_name'] or "")
        self.nok2_rel.setText(m['nok2_relationship'] or "")
        self.nok2_addr.setText(m['nok2_address'] or "")
        self.nok2_phone.setText(m['nok2_phone'] or "")

    def data(self) -> dict:
        return {
            'first_name':        self.first_name_input.text().strip().upper(),
            'middle_name':       self.middle_name_input.text().strip().upper() or None,
            'last_name':         self.last_name_input.text().strip().upper(),
            'gender':            self.gender_combo.currentText(),
            'station_id':        self.station_combo.currentData(),
            'date_joined':       self.date_joined.date().toString("yyyy-MM-dd"),
            'date_of_birth':     self.dob_input.text().strip() or None,
            'employee_id':       self.employee_input.text().strip() or None,
            'grade_level':       self.grade_input.text().strip() or None,
            'phone_number':      self.phone_input.text().strip() or None,
            'email':             self.email_input.text().strip() or None,
            'address':           self.address_input.text().strip() or None,
            'nok1_name':         self.nok1_name.text().strip() or None,
            'nok1_relationship': self.nok1_rel.text().strip() or None,
            'nok1_address':      self.nok1_addr.text().strip() or None,
            'nok1_phone':        self.nok1_phone.text().strip() or None,
            'nok2_name':         self.nok2_name.text().strip() or None,
            'nok2_relationship': self.nok2_rel.text().strip() or None,
            'nok2_address':      self.nok2_addr.text().strip() or None,
            'nok2_phone':        self.nok2_phone.text().strip() or None,
        }

    def _validate(self):
        if not self.first_name_input.text().strip():
            QMessageBox.warning(self, "Validation", "First name is required.")
            return
        if not self.last_name_input.text().strip():
            QMessageBox.warning(self, "Validation", "Last name is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# Member view dialog (read-only + financial summary)
# ---------------------------------------------------------------------------

class MemberViewDialog(QDialog):
    def __init__(self, db, member, parent=None):
        super().__init__(parent)
        self.db     = db
        self.member = member
        full_name   = ' '.join(filter(None, [
            member['first_name'], member.get('middle_name'), member['last_name']
        ]))
        self.setWindowTitle(f"Member — {full_name}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        m    = self.member
        tabs = QTabWidget()

        # Personal
        personal = QWidget()
        pf = QFormLayout(personal)
        pf.setContentsMargins(12, 12, 12, 12)
        pf.setSpacing(10)
        pf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        stations  = {s['station_id']: s['station_name']
                     for s in self.db.get_all_stations(enabled_only=False)}
        full_name = ' '.join(filter(None, [
            m['first_name'], m.get('middle_name'), m['last_name']
        ]))

        if m['is_deceased']:
            status = "Deceased"
        elif not m['is_active']:
            status = "Inactive"
        else:
            status = "Active"

        for label, val in [
            ("Member ID:",     m['member_id']),
            ("Full Name:",     full_name),
            ("Gender:",        m['gender'] or "—"),
            ("Station:",       stations.get(m['station_id'], m['station_id'])),
            ("Date Joined:",   m['date_joined'] or "—"),
            ("Date of Birth:", m['date_of_birth'] or "—"),
            ("Employee ID:",   m['employee_id'] or "—"),
            ("Grade Level:",   m['grade_level'] or "—"),
            ("Status:",        status),
        ]:
            lbl = QLabel(val or "—")
            lbl.setWordWrap(True)
            pf.addRow(label, lbl)

        tabs.addTab(personal, "Personal")

        # Contact
        contact = QWidget()
        cf = QFormLayout(contact)
        cf.setContentsMargins(12, 12, 12, 12)
        cf.setSpacing(10)
        cf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        for label, val in [
            ("Phone:",   m['phone_number'] or "—"),
            ("Email:",   m['email'] or "—"),
            ("Address:", m['address'] or "—"),
        ]:
            cf.addRow(label, QLabel(val))
        tabs.addTab(contact, "Contact")

        # NOK
        nok    = QWidget()
        nf     = QVBoxLayout(nok)
        nf.setContentsMargins(12, 12, 12, 12)
        nf.setSpacing(12)
        for title, fields in [
            ("Next of Kin 1", [
                ("Name:",         m['nok1_name'] or "—"),
                ("Relationship:", m['nok1_relationship'] or "—"),
                ("Address:",      m['nok1_address'] or "—"),
                ("Phone:",        m['nok1_phone'] or "—"),
            ]),
            ("Next of Kin 2", [
                ("Name:",         m['nok2_name'] or "—"),
                ("Relationship:", m['nok2_relationship'] or "—"),
                ("Address:",      m['nok2_address'] or "—"),
                ("Phone:",        m['nok2_phone'] or "—"),
            ]),
        ]:
            grp = QGroupBox(title)
            gf  = QFormLayout(grp)
            gf.setSpacing(8)
            gf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            for lbl, val in fields:
                gf.addRow(lbl, QLabel(val))
            nf.addWidget(grp)
        nf.addStretch()
        tabs.addTab(nok, "Next of Kin")

        # Financial Summary
        summary_tab = QWidget()
        sf = QFormLayout(summary_tab)
        sf.setContentsMargins(12, 12, 12, 12)
        sf.setSpacing(10)
        sf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        summaries = self.db.get_member_summary(m['member_id'])
        if summaries:
            s        = summaries[0]
            currency = self.db.get_setting('currency_symbol') or '₦'
            for label, val in [
                ("Total Savings:",         f"{currency}{s['total_savings']:,.2f}"),
                ("Premium Savings:",       f"{currency}{s['premium_savings']:,.2f}"),
                ("Fixed/Target Deposits:", f"{currency}{s['fixed_target_deposits']:,.2f}"),
                ("Shares:",                f"{currency}{s['shares_investment']:,.2f}"),
                ("Loans Outstanding:",     f"{currency}{s['total_loans_outstanding']:,.2f}"),
                ("Net Balance:",           f"{currency}{s['net_balance']:,.2f}"),
            ]:
                lbl = QLabel(val)
                lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                sf.addRow(label, lbl)
        tabs.addTab(summary_tab, "Financial Summary")

        layout.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)