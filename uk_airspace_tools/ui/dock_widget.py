from __future__ import annotations

try:
    from qgis.PyQt.QtCore import QDate, pyqtSignal
    from qgis.PyQt.QtGui import QTextCursor
    from qgis.PyQt.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDockWidget,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover - QGIS-only UI module.
    class _DummySignal:
        def connect(self, *_args, **_kwargs):
            return None

        def emit(self, *_args, **_kwargs):
            return None

    def pyqtSignal(*_args, **_kwargs):
        return _DummySignal()

    class QDockWidget:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("PyQGIS/PyQt is required to create the UK Airspace Tools dock widget.")


class UkAirspaceDockWidget(QDockWidget):
    refreshRequested = pyqtSignal()
    permanentRefreshRequested = pyqtSignal()
    localFileRequested = pyqtSignal(str)
    localAipFileRequested = pyqtSignal(str)
    clearRequested = pyqtSignal()
    clearPermanentRequested = pyqtSignal()
    clearIsolationRequested = pyqtSignal()
    zoomRequested = pyqtSignal()
    inspectNotamsRequested = pyqtSignal()
    inspectAirspaceRequested = pyqtSignal()
    filtersChanged = pyqtSignal()
    cancelRefreshRequested = pyqtSignal()
    warningsRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("UK Airspace Tools", parent)
        self.setObjectName("UkAirspaceToolsDockWidget")
        self._build_ui()

    def selected_source(self) -> str:
        return self.source_selector.currentData()

    def filters(self) -> dict:
        return {
            "time_filter": self.time_filter.currentData(),
            "custom_start_date": self.start_date_filter.date().toString("yyyy-MM-dd"),
            "custom_end_date": self.end_date_filter.date().toString("yyyy-MM-dd"),
            "status_filter": self.status_filter.currentData(),
            "activity_filter": self.activity_filter.currentData(),
            "fir_filter": self.fir_filter.currentData(),
            "scope_filter": self.scope_filter.currentData(),
            "qcode_filter": self.qcode_filter.currentData(),
            "radius_filter": self.radius_filter.currentData(),
            "altitude_filter": self.altitude_filter.currentData(),
            "custom_min_altitude_ft": self.min_altitude_filter.text(),
            "custom_max_altitude_ft": self.max_altitude_filter.text(),
            "static_category_filter": self.static_category_filter.currentData(),
            "static_type_filter": self.static_type_filter.currentData(),
            "static_altitude_filter": self.static_altitude_filter.currentData(),
            "static_custom_min_altitude_ft": self.static_min_altitude_filter.text(),
            "static_custom_max_altitude_ft": self.static_max_altitude_filter.text(),
            "keyword": self.keyword_filter.text(),
            "static_keyword": self.static_keyword_filter.text(),
            "show_polygons": self.show_polygon_notams.isChecked(),
            "show_points": self.show_point_notams.isChecked(),
            "show_text_only": self.show_text_only_notams.isChecked(),
            "show_expired": self.show_expired_notams.isChecked(),
            "show_permanent_airspace": self.show_permanent_airspace.isChecked(),
        }

    def set_status(self, stats: dict) -> None:
        for key, label in self.status_labels.items():
            label.setText(str(stats.get(key, "0" if key.endswith("_count") else "")))

    def set_refresh_state(self, running: bool, message: str = "") -> None:
        self.refresh_status_label.setText(message)
        for button in [
            self.refresh_button,
            self.load_file_button,
            self.refresh_permanent_button,
            self.load_aip_file_button,
        ]:
            button.setEnabled(not running)
        self.cancel_refresh_button.setEnabled(running)

    def set_layer_action_state(self, *, has_notams: bool, has_static_airspace: bool, isolation_active: bool = False) -> None:
        self.zoom_button.setEnabled(has_notams)
        self.inspect_notams_button.setEnabled(has_notams)
        self.inspect_airspace_button.setEnabled(has_static_airspace)
        self.clear_button.setEnabled(has_notams)
        self.clear_permanent_button.setEnabled(has_static_airspace)
        self.clear_isolation_button.setEnabled(isolation_active)

    def set_warning_action_state(self, warning_count: int) -> None:
        self.review_warnings_button.setEnabled(warning_count > 0)
        self.review_warnings_button.setText(f"Review Parse Warnings ({warning_count})")

    def set_filter_options(self, options: dict) -> None:
        self._set_combo_items(self.activity_filter, [("All activity types", "all")] + [(value, value) for value in options.get("activity_groups", [])])
        self._set_combo_items(self.fir_filter, [("All FIRs", "all")] + [(value, value) for value in options.get("firs", [])])
        self._set_combo_items(self.scope_filter, [("All scopes", "all")] + [(value, value) for value in options.get("scopes", [])])
        self._set_combo_items(self.qcode_filter, [("All Q-codes", "all")] + [(value, value) for value in options.get("qcodes", [])])

    def set_static_filter_options(self, options: dict) -> None:
        self._set_combo_items(
            self.static_category_filter,
            [("All permanent categories", "all")] + [(value, value) for value in options.get("static_categories", [])],
        )
        self._set_combo_items(
            self.static_type_filter,
            [("All airspace types", "all")] + [(value, value) for value in options.get("static_types", [])],
        )

    def set_feature_details(self, title: str, details: str, rich: bool = False) -> None:
        self.details_title.setText(title)
        if rich:
            self.details_text.setHtml(details)
        else:
            self.details_text.setPlainText(details)
        self.details_text.moveCursor(QTextCursor.Start)
        self.details_text.setFocus()

    def _build_ui(self) -> None:
        container = QWidget(self)
        outer_layout = QVBoxLayout(container)

        scroll_area = QScrollArea(container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area = scroll_area
        scroll_content = QWidget(scroll_area)
        layout = QVBoxLayout(scroll_content)

        self.tabs = QTabWidget()
        notam_tab = QWidget()
        notam_layout = QVBoxLayout(notam_tab)
        airspace_tab = QWidget()
        airspace_layout = QVBoxLayout(airspace_tab)
        self.tabs.addTab(notam_tab, "NOTAMs")
        self.tabs.addTab(airspace_tab, "Airspace")
        layout.addWidget(self.tabs)

        button_row = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh NOTAMs")
        self.load_file_button = QPushButton("Load NOTAM XML File")
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.load_file_button)
        notam_layout.addLayout(button_row)

        second_row = QHBoxLayout()
        self.clear_button = QPushButton("Clear NOTAM Layers")
        self.zoom_button = QPushButton("Zoom to Active NOTAMs")
        second_row.addWidget(self.clear_button)
        second_row.addWidget(self.zoom_button)
        notam_layout.addLayout(second_row)

        notam_inspect_row = QHBoxLayout()
        self.inspect_notams_button = QPushButton("Inspect NOTAM")
        notam_inspect_row.addWidget(self.inspect_notams_button)
        notam_layout.addLayout(notam_inspect_row)

        permanent_row = QHBoxLayout()
        self.refresh_permanent_button = QPushButton("Refresh Permanent Airspace")
        self.load_aip_file_button = QPushButton("Load AIP XML/KML File")
        permanent_row.addWidget(self.refresh_permanent_button)
        permanent_row.addWidget(self.load_aip_file_button)
        airspace_layout.addLayout(permanent_row)

        permanent_second_row = QHBoxLayout()
        self.clear_permanent_button = QPushButton("Clear Permanent Airspace")
        self.clear_isolation_button = QPushButton("Show Filtered Airspace")
        permanent_second_row.addWidget(self.clear_permanent_button)
        permanent_second_row.addWidget(self.clear_isolation_button)
        airspace_layout.addLayout(permanent_second_row)

        refresh_control_row = QHBoxLayout()
        self.cancel_refresh_button = QPushButton("Cancel Refresh")
        self.cancel_refresh_button.setEnabled(False)
        self.review_warnings_button = QPushButton("Review Parse Warnings (0)")
        self.review_warnings_button.setEnabled(False)
        refresh_control_row.addWidget(self.cancel_refresh_button)
        refresh_control_row.addWidget(self.review_warnings_button)
        layout.addLayout(refresh_control_row)

        form = QFormLayout()
        self.source_selector = QComboBox()
        self.source_selector.addItem("NATS PIB XML URL", "nats")
        self.source_selector.addItem("Local XML file", "local")
        form.addRow("Source", self.source_selector)

        self.time_filter = QComboBox()
        self.time_filter.addItem("Active now", "active_now")
        self.time_filter.addItem("Active today", "today")
        self.time_filter.addItem("Active tomorrow", "tomorrow")
        self.time_filter.addItem("Active this week", "this_week")
        self.time_filter.addItem("Active this weekend", "this_weekend")
        self.time_filter.addItem("Next 24 hours", "next_24_hours")
        self.time_filter.addItem("Next 7 days", "next_7_days")
        self.time_filter.addItem("Custom date range", "custom_dates")
        self.time_filter.addItem("All loaded", "all")
        form.addRow("Date/time", self.time_filter)

        date_row = QHBoxLayout()
        today = QDate.currentDate()
        self.start_date_filter = QDateEdit(today)
        self.start_date_filter.setCalendarPopup(True)
        self.start_date_filter.setDisplayFormat("yyyy-MM-dd")
        self.end_date_filter = QDateEdit(today.addDays(7))
        self.end_date_filter.setCalendarPopup(True)
        self.end_date_filter.setDisplayFormat("yyyy-MM-dd")
        date_row.addWidget(self.start_date_filter)
        date_row.addWidget(self.end_date_filter)
        form.addRow("Custom dates", date_row)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Not cancelled/expired", "operational")
        self.status_filter.addItem("Active only", "active")
        self.status_filter.addItem("Upcoming only", "upcoming")
        self.status_filter.addItem("Cancelled only", "cancelled")
        self.status_filter.addItem("Expired only", "expired")
        self.status_filter.addItem("Unknown only", "unknown")
        self.status_filter.addItem("All statuses", "all")
        form.addRow("Status", self.status_filter)

        self.radius_filter = QComboBox()
        self.radius_filter.addItem("Up to 100 NM", "up_to_100")
        self.radius_filter.addItem("Up to 25 NM", "up_to_25")
        self.radius_filter.addItem("Large only (>100 NM)", "large_only")
        self.radius_filter.addItem("All sizes", "all")
        form.addRow("Area size", self.radius_filter)

        self.altitude_filter = QComboBox()
        self.altitude_filter.addItem("All altitudes", "all")
        self.altitude_filter.addItem("Surface to 1,000 ft", "sfc_1000")
        self.altitude_filter.addItem("Surface to 5,000 ft", "sfc_5000")
        self.altitude_filter.addItem("Surface to FL100", "sfc_fl100")
        self.altitude_filter.addItem("FL100 to FL200", "fl100_fl200")
        self.altitude_filter.addItem("Above FL200", "above_fl200")
        self.altitude_filter.addItem("Custom ft range", "custom")
        form.addRow("Altitude", self.altitude_filter)

        altitude_row = QHBoxLayout()
        self.min_altitude_filter = QLineEdit()
        self.min_altitude_filter.setPlaceholderText("Min ft")
        self.max_altitude_filter = QLineEdit()
        self.max_altitude_filter.setPlaceholderText("Max ft")
        altitude_row.addWidget(self.min_altitude_filter)
        altitude_row.addWidget(self.max_altitude_filter)
        form.addRow("Custom altitude", altitude_row)

        self.activity_filter = QComboBox()
        self.activity_filter.addItem("All activity types", "all")
        form.addRow("Activity", self.activity_filter)

        self.fir_filter = QComboBox()
        self.fir_filter.addItem("All FIRs", "all")
        form.addRow("FIR", self.fir_filter)

        self.scope_filter = QComboBox()
        self.scope_filter.addItem("All scopes", "all")
        form.addRow("Scope", self.scope_filter)

        self.qcode_filter = QComboBox()
        self.qcode_filter.addItem("All Q-codes", "all")
        form.addRow("Q-code", self.qcode_filter)

        self.keyword_filter = QLineEdit()
        self.keyword_filter.setPlaceholderText("Keyword, Q-code text, location")
        form.addRow("Keyword", self.keyword_filter)
        notam_layout.addLayout(form)

        self.show_polygon_notams = QCheckBox("Show polygon NOTAMs")
        self.show_polygon_notams.setChecked(True)
        self.show_point_notams = QCheckBox("Show point NOTAMs")
        self.show_point_notams.setChecked(True)
        self.show_text_only_notams = QCheckBox("Show text-only NOTAMs")
        self.show_text_only_notams.setChecked(True)
        self.show_expired_notams = QCheckBox("Show expired NOTAMs")
        self.show_expired_notams.setChecked(False)
        for checkbox in [
            self.show_polygon_notams,
            self.show_point_notams,
            self.show_text_only_notams,
            self.show_expired_notams,
        ]:
            notam_layout.addWidget(checkbox)

        airspace_form = QFormLayout()
        self.static_category_filter = QComboBox()
        self.static_category_filter.addItem("All permanent categories", "all")
        airspace_form.addRow("Category", self.static_category_filter)

        self.static_type_filter = QComboBox()
        self.static_type_filter.addItem("All airspace types", "all")
        airspace_form.addRow("Airspace type", self.static_type_filter)

        self.static_altitude_filter = QComboBox()
        self._add_altitude_items(self.static_altitude_filter)
        airspace_form.addRow("Altitude", self.static_altitude_filter)

        static_altitude_row = QHBoxLayout()
        self.static_min_altitude_filter = QLineEdit()
        self.static_min_altitude_filter.setPlaceholderText("Min ft")
        self.static_max_altitude_filter = QLineEdit()
        self.static_max_altitude_filter.setPlaceholderText("Max ft")
        static_altitude_row.addWidget(self.static_min_altitude_filter)
        static_altitude_row.addWidget(self.static_max_altitude_filter)
        airspace_form.addRow("Custom altitude", static_altitude_row)

        self.static_keyword_filter = QLineEdit()
        self.static_keyword_filter.setPlaceholderText("Name, designator, remarks")
        airspace_form.addRow("Keyword", self.static_keyword_filter)
        airspace_layout.addLayout(airspace_form)

        self.show_permanent_airspace = QCheckBox("Show permanent airspace")
        self.show_permanent_airspace.setChecked(True)
        airspace_layout.addWidget(self.show_permanent_airspace)

        airspace_inspect_row = QHBoxLayout()
        self.inspect_airspace_button = QPushButton("Inspect / Cross-section")
        airspace_inspect_row.addWidget(self.inspect_airspace_button)
        airspace_layout.addLayout(airspace_inspect_row)
        airspace_layout.addStretch(1)
        notam_layout.addStretch(1)

        status_group = QGroupBox("Status")
        status_layout = QFormLayout(status_group)
        self.status_labels = {
            "refresh_status": QLabel("Idle"),
            "last_refresh": QLabel(""),
            "source_label": QLabel(""),
            "notam_count": QLabel("0"),
            "polygon_count": QLabel("0"),
            "point_count": QLabel("0"),
            "text_only_count": QLabel("0"),
            "local_regional_count": QLabel("0"),
            "large_area_count": QLabel("0"),
            "activity_group_count": QLabel("0"),
            "permanent_airspace_count": QLabel("0"),
            "permanent_polygon_count": QLabel("0"),
            "permanent_text_only_count": QLabel("0"),
            "permanent_category_count": QLabel("0"),
            "warning_count": QLabel("0"),
        }
        self.refresh_status_label = self.status_labels["refresh_status"]
        status_layout.addRow("Refresh status", self.status_labels["refresh_status"])
        status_layout.addRow("Last refresh time (UTC)", self.status_labels["last_refresh"])
        status_layout.addRow("Latest source", self.status_labels["source_label"])
        status_layout.addRow("Number of NOTAMs parsed", self.status_labels["notam_count"])
        status_layout.addRow("Number of polygon NOTAMs", self.status_labels["polygon_count"])
        status_layout.addRow("Number of point NOTAMs", self.status_labels["point_count"])
        status_layout.addRow("Number of text-only NOTAMs", self.status_labels["text_only_count"])
        status_layout.addRow("Local/regional NOTAMs", self.status_labels["local_regional_count"])
        status_layout.addRow("Large-area NOTAMs", self.status_labels["large_area_count"])
        status_layout.addRow("Activity groups", self.status_labels["activity_group_count"])
        status_layout.addRow("Permanent airspace records", self.status_labels["permanent_airspace_count"])
        status_layout.addRow("Permanent polygon records", self.status_labels["permanent_polygon_count"])
        status_layout.addRow("Permanent text-only records", self.status_labels["permanent_text_only_count"])
        status_layout.addRow("Permanent categories", self.status_labels["permanent_category_count"])
        status_layout.addRow("Number of parse warnings/errors", self.status_labels["warning_count"])
        layout.addWidget(status_group)

        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout(details_group)
        self.details_title = QLabel("No airspace selected")
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(140)
        self.details_text.setMaximumHeight(260)
        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.details_text)
        outer_layout.addWidget(scroll_area, 1)
        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(details_group, 0)

        self.setWidget(container)
        self._connect_signals()
        self.set_layer_action_state(has_notams=False, has_static_airspace=False)

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refreshRequested.emit)
        self.refresh_permanent_button.clicked.connect(self.permanentRefreshRequested.emit)
        self.load_file_button.clicked.connect(self._choose_file)
        self.load_aip_file_button.clicked.connect(self._choose_aip_file)
        self.clear_button.clicked.connect(self.clearRequested.emit)
        self.clear_permanent_button.clicked.connect(self.clearPermanentRequested.emit)
        self.clear_isolation_button.clicked.connect(self.clearIsolationRequested.emit)
        self.zoom_button.clicked.connect(self.zoomRequested.emit)
        self.inspect_notams_button.clicked.connect(self.inspectNotamsRequested.emit)
        self.inspect_airspace_button.clicked.connect(self.inspectAirspaceRequested.emit)
        self.cancel_refresh_button.clicked.connect(self.cancelRefreshRequested.emit)
        self.review_warnings_button.clicked.connect(self.warningsRequested.emit)
        self.time_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.start_date_filter.dateChanged.connect(self.filtersChanged.emit)
        self.end_date_filter.dateChanged.connect(self.filtersChanged.emit)
        self.status_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.radius_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.altitude_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.min_altitude_filter.textChanged.connect(self.filtersChanged.emit)
        self.max_altitude_filter.textChanged.connect(self.filtersChanged.emit)
        self.activity_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.fir_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.scope_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.qcode_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.static_category_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.static_type_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.static_altitude_filter.currentIndexChanged.connect(self.filtersChanged.emit)
        self.static_min_altitude_filter.textChanged.connect(self.filtersChanged.emit)
        self.static_max_altitude_filter.textChanged.connect(self.filtersChanged.emit)
        self.keyword_filter.textChanged.connect(self.filtersChanged.emit)
        self.static_keyword_filter.textChanged.connect(self.filtersChanged.emit)
        for checkbox in [
            self.show_polygon_notams,
            self.show_point_notams,
            self.show_text_only_notams,
            self.show_expired_notams,
            self.show_permanent_airspace,
        ]:
            checkbox.stateChanged.connect(self.filtersChanged.emit)

    def _choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load NOTAM XML File",
            "",
            "XML files (*.xml);;All files (*.*)",
        )
        if file_path:
            self.source_selector.setCurrentIndex(1)
            self.localFileRequested.emit(file_path)

    def _choose_aip_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load AIP Dataset File",
            "",
            "AIP dataset files (*.zip *.xml *.kml *.kmz);;All files (*.*)",
        )
        if file_path:
            self.localAipFileRequested.emit(file_path)

    @staticmethod
    def _add_altitude_items(combo) -> None:
        combo.addItem("All altitudes", "all")
        combo.addItem("Surface to 1,000 ft", "sfc_1000")
        combo.addItem("Surface to 5,000 ft", "sfc_5000")
        combo.addItem("Surface to FL100", "sfc_fl100")
        combo.addItem("FL100 to FL200", "fl100_fl200")
        combo.addItem("Above FL200", "above_fl200")
        combo.addItem("Custom ft range", "custom")

    @staticmethod
    def _set_combo_items(combo, items: list[tuple[str, str]]) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for label, value in items:
            combo.addItem(label, value)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)
