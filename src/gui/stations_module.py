from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QGroupBox,
    QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class StationsModule(QWidget):
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
        title = QLabel("Stations")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        if self._is_admin():
            add_btn = QPushButton("Add Station")
            add_btn.setFixedHeight(36)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._add_station)
            hdr.addWidget(add_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        self.show_all_cb = QCheckBox("Show disabled stations")
        self.show_all_cb.stateChanged.connect(self.refresh)
        layout.addWidget(self.show_all_cb)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Address", "Contact Person",
            "Phone", "Email", "Status"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        if self._is_admin():
            btn_row = QHBoxLayout()
            self.edit_btn = QPushButton("Edit")
            self.edit_btn.setFixedHeight(34)
            self.edit_btn.setEnabled(False)
            self.edit_btn.clicked.connect(self._edit_selected)
            btn_row.addWidget(self.edit_btn)

            self.toggle_btn = QPushButton("Enable / Disable")
            self.toggle_btn.setFixedHeight(34)
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.clicked.connect(self._toggle_selected)
            btn_row.addWidget(self.toggle_btn)

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

    def _selected_station_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection(self):
        has = self._selected_station_id() is not None
        self.edit_btn.setEnabled(has)
        self.toggle_btn.setEnabled(has)

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    def refresh(self):
        show_all = self.show_all_cb.isChecked()
        stations = self.db.get_all_stations(enabled_only=not show_all)
        self.table.setRowCount(len(stations))

        for row, s in enumerate(stations):
            def cell(val):
                item = QTableWidgetItem(str(val) if val else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                return item

            self.table.setItem(row, 0, cell(s['station_id']))
            self.table.setItem(row, 1, cell(s['station_name']))
            self.table.setItem(row, 2, cell(s['address']))
            self.table.setItem(row, 3, cell(s['contact_person']))
            self.table.setItem(row, 4, cell(s['contact_phone']))
            self.table.setItem(row, 5, cell(s['contact_email']))

            status      = "Enabled" if s['enabled'] else "Disabled"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(
                Qt.GlobalColor.green if s['enabled'] else Qt.GlobalColor.red
            )
            self.table.setItem(row, 6, status_item)
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, s['station_id'])

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.summary.setText(f"{len(stations)} station(s) shown")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _add_station(self):
        dlg = StationDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            city    = dlg.city_input.text().strip()
            address = dlg.address_input.text().strip()
            if not self._confirm(
                "Confirm Add Station",
                f"Add new station 'NFC - {city}'?"
            ):
                return
            try:
                self.db.add_station(city, address)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add station:\n{e}")

    def _edit_selected(self):
        sid = self._selected_station_id()
        if not sid:
            return
        station = self.db.get_station(sid)
        if not station:
            return
        dlg = StationDialog(station=station, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if not self._confirm(
                "Confirm Edit Station",
                f"Save changes to '{station['station_name']}'?"
            ):
                return
            try:
                self.db.update_station(sid, {
                    'station_name':   dlg.name_input.text().strip(),
                    'address':        dlg.address_input.text().strip(),
                    'city':           dlg.city_input.text().strip(),
                    'contact_person': dlg.contact_person_input.text().strip() or None,
                    'contact_phone':  dlg.contact_phone_input.text().strip() or None,
                    'contact_email':  dlg.contact_email_input.text().strip() or None,
                }, self.user['username'])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update station:\n{e}")

    def _toggle_selected(self):
        sid = self._selected_station_id()
        if not sid:
            return
        station = self.db.get_station(sid)
        if not station:
            return
        action = "disable" if station['enabled'] else "enable"
        if not self._confirm(
            "Confirm",
            f"Are you sure you want to {action} station '{station['station_name']}'?"
        ):
            return
        try:
            self.db.toggle_station(sid, not station['enabled'])
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update station:\n{e}")


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class StationDialog(QDialog):
    def __init__(self, station=None, parent=None):
        super().__init__(parent)
        self.station = station
        self.setWindowTitle("Edit Station" if station else "Add Station")
        self.setFixedWidth(440)
        self._setup_ui()
        if station:
            self._populate(station)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        group = QGroupBox("Station Details")
        form  = QFormLayout(group)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def field(placeholder=""):
            f = QLineEdit()
            f.setFixedHeight(36)
            f.setPlaceholderText(placeholder)
            return f

        self.name_input           = field("Auto-generated from city")
        self.city_input           = field("e.g. Kano")
        self.address_input        = field("Full address")
        self.contact_person_input = field("Optional")
        self.contact_phone_input  = field("Optional")
        self.contact_email_input  = field("Optional")

        if self.station:
            form.addRow("Name:",           self.name_input)
        form.addRow("City:",               self.city_input)
        form.addRow("Address:",            self.address_input)
        form.addRow("Contact Person:",     self.contact_person_input)
        form.addRow("Contact Phone:",      self.contact_phone_input)
        form.addRow("Contact Email:",      self.contact_email_input)

        layout.addWidget(group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, s):
        self.name_input.setText(s['station_name'] or "")
        self.city_input.setText(s['city'] or "")
        self.address_input.setText(s['address'] or "")
        self.contact_person_input.setText(s['contact_person'] or "")
        self.contact_phone_input.setText(s['contact_phone'] or "")
        self.contact_email_input.setText(s['contact_email'] or "")

    def _validate(self):
        if not self.city_input.text().strip():
            QMessageBox.warning(self, "Validation", "City is required.")
            return
        self.accept()