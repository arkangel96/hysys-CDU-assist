from __future__ import annotations

from datetime import datetime

import pyqtgraph as pg
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QCursor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from trial_map import manual_map_event
from trial_map_window import TrialMapWindow
from intelligence_window import IntelligenceWindow
from column_api import ColumnController
from column_engine import ConvergenceAssistant, diagnose, format_connections_block, format_pe_board, score_state
from cdu_monitor import format_monitor_block
from cdu_specs import format_specs_page_block, format_specs_summary_block
from cdu_subcooling import format_subcooling_block
from cdu_side_ops import format_side_ops_block
from cdu_rating import format_rating_block
from column_models import ConvergenceLimits
from exporter import export_workbook
from column_spec_catalog import format_add_spec_hysys_steps, list_add_spec_names
from hysys_api import HysysController, HysysError
from ui_style import style_table_headers


DARK_THEME = """
QMainWindow, QWidget {
  background: #0d1117;
  color: #c9d1d9;
  font-family: "Segoe UI";
  font-size: 9pt;
}
QLabel { font-size: 9pt; }
QFrame {
  border: 1px solid #21262d;
  border-radius: 2px;
  padding: 0px;
  background: #161b22;
}
QFrame#metricCard, QFrame#statusChip {
  border: 1px solid #30363d;
  background: #161b22;
}
QGroupBox {
  border: 1px solid #30363d;
  border-radius: 2px;
  margin-top: 8px;
  padding: 4px 6px 4px 6px;
  font-weight: 600;
  font-size: 9pt;
}
QGroupBox#compactBox {
  margin-top: 6px;
  padding: 4px 6px 4px 6px;
  font-size: 8pt;
}
QGroupBox::title {
  subcontrol-origin: margin;
  subcontrol-position: top left;
  left: 8px;
  padding: 0 4px;
  color: #c9d1d9;
  background: #0d1117;
  font-size: 8pt;
}
QPushButton {
  background: #21262d;
  border: 1px solid #30363d;
  border-radius: 2px;
  padding: 2px 8px;
  min-height: 18px;
  min-width: 64px;
  font-size: 8pt;
}
QPushButton:hover { background: #30363d; border-color: #484f58; }
QPushButton:pressed { background: #161b22; }
QPushButton#primaryAction {
  background: #1f6feb;
  border: 1px solid #388bfd;
  color: #ffffff;
  font-weight: 600;
}
QPushButton#primaryAction:hover { background: #388bfd; }
QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QTableWidget {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 2px;
  padding: 2px 4px;
  min-height: 16px;
  font-size: 8pt;
}
QComboBox QAbstractItemView {
  font-size: 8pt;
}
QHeaderView {
  background-color: #21262d;
}
QHeaderView::section {
  background-color: #21262d;
  color: #ffffff;
  padding: 4px 6px;
  border: none;
  border-right: 1px solid #30363d;
  border-bottom: 1px solid #58a6ff;
  font-size: 8pt;
  font-weight: 700;
  min-height: 22px;
}
QTableWidget {
  gridline-color: #30363d;
  selection-background-color: #1f6feb;
  color: #e6edf3;
  alternate-background-color: #12171e;
  font-size: 8pt;
}
QTableWidget::item {
  padding: 2px 4px;
  color: #e6edf3;
}
QTableWidget::item:selected {
  background-color: #1f6feb;
  color: #ffffff;
}
QTabWidget::pane {
  border: 1px solid #30363d;
  border-radius: 2px;
  top: -1px;
  padding: 4px;
}
QTabBar::tab {
  background: #161b22;
  border: 1px solid #30363d;
  padding: 3px 8px;
  margin-right: 1px;
  font-size: 8pt;
  min-height: 18px;
}
QTabBar::tab:selected {
  background: #21262d;
  border-bottom-color: #21262d;
  color: #58a6ff;
}
QSplitter::handle { background: #21262d; width: 3px; }
QTextEdit {
  font-family: Consolas, "Courier New", monospace;
  font-size: 8pt;
}
"""


class MetricCard(QFrame):
    """Stream property tile — compact Aspen-like density."""

    def __init__(self, title: str, unit: str, color: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.setMinimumHeight(44)
        self.setMaximumHeight(52)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(1)

        title_label = QLabel(title.upper())
        title_label.setFont(QFont("Segoe UI", 7))
        title_label.setStyleSheet("color: #8b949e; border: none; background: transparent;")

        self.value = QLabel("—")
        value_font = QFont("Segoe UI", 10)
        value_font.setBold(True)
        self.value.setFont(value_font)
        self.value.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.unit_label = QLabel(unit)
        self.unit_label.setFont(QFont("Segoe UI", 7))
        self.unit_label.setStyleSheet("color: #8b949e; border: none; background: transparent;")

        layout.addWidget(title_label)
        layout.addWidget(self.value)
        layout.addWidget(self.unit_label)

    def update_value(self, value: float | None) -> None:
        self.value.setText("—" if value is None else f"{value:,.4g}")

    def set_unit(self, unit: str) -> None:
        self.unit_label.setText(unit)


class StatusChip(QFrame):
    """Compact labeled status block for column overview."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("statusChip")
        self.setMinimumHeight(34)
        self.setMaximumHeight(40)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(0)

        self.title = QLabel(title)
        self.title.setFont(QFont("Segoe UI", 7))
        self.title.setStyleSheet("color: #8b949e; border: none; background: transparent;")

        self.value = QLabel("—")
        value_font = QFont("Segoe UI", 9)
        value_font.setBold(True)
        self.value.setFont(value_font)
        self.value.setStyleSheet("color: #c9d1d9; border: none; background: transparent;")
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, text: str, color: str | None = None) -> None:
        self.value.setText(text)
        color = color or "#c9d1d9"
        self.value.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )


class SimpleColumnAssist(QMainWindow):
    """Desktop assist for CDU / atmospheric crude distillation in HYSYS."""

    def __init__(self) -> None:
        super().__init__()
        self.controller = HysysController()
        self.column_api = ColumnController(self.controller)
        self.assistant = ConvergenceAssistant(self.column_api, ConvergenceLimits())
        self.trial_map_window: TrialMapWindow | None = None
        self.intelligence_window: IntelligenceWindow | None = None
        self._column_job_busy = False
        self._last_column_state = None
        self._last_specs_clicks: list[str] = []
        self.streams = {}
        self.stream_data = []
        self.operations = []
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh_data)
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        self.setWindowTitle("CDU Assist v1 — New Intelligence")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(DARK_THEME)
        app_font = QFont("Segoe UI", 8)
        QApplication.setFont(app_font)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 2)
        logo = QLabel("CDU ASSIST v1")
        logo.setStyleSheet("font-size: 12pt; font-weight: 700; color: #58a6ff;")
        subtitle = QLabel("New Intelligence · atmospheric crude distillation · Tower Assist")
        subtitle.setStyleSheet("color: #8b949e; font-size: 8pt;")
        self.status = QLabel("● DISCONNECTED")
        self.status.setStyleSheet("color: #f85149; font-weight: 600; font-size: 8pt;")
        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(logo)
        brand.addWidget(subtitle)
        top.addLayout(brand)
        top.addStretch()
        top.addWidget(self.status)
        root.addLayout(top)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setContentsMargins(0, 0, 0, 4)
        self.connect_button = QPushButton("Connect")
        self.open_button = QPushButton("Open Case")
        self.refresh_button = QPushButton("Refresh")
        self.solve_button = QPushButton("Solve (F5)")
        self.auto_refresh = QCheckBox("Auto-refresh")
        self.export_button = QPushButton("Export Excel")
        for widget in (
            self.connect_button, self.open_button, self.refresh_button,
            self.solve_button, self.auto_refresh, self.export_button,
        ):
            toolbar.addWidget(widget)
        toolbar.addStretch()
        root.addLayout(toolbar)

        components = QGroupBox("Component Setup")
        components.setObjectName("compactBox")
        components.setMaximumHeight(58)
        component_layout = QHBoxLayout(components)
        component_layout.setContentsMargins(8, 2, 8, 6)
        component_layout.setSpacing(8)
        self.component_input = QLineEdit()
        self.component_input.setPlaceholderText("Methane, Ethane, Propane …")
        self.component_input.setMaximumWidth(420)
        self.apply_components_button = QPushButton("Apply")
        self.apply_components_button.setMinimumWidth(72)
        component_layout.addWidget(self.component_input, 1)
        component_layout.addWidget(self.apply_components_button)
        component_layout.addStretch(2)
        root.addWidget(components)

        splitter = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 8, 4)
        left_layout.setSpacing(10)
        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        selector_row.addWidget(QLabel("Stream"))
        self.stream_combo = QComboBox()
        selector_row.addWidget(self.stream_combo, 1)
        left_layout.addLayout(selector_row)

        cards = QGridLayout()
        cards.setHorizontalSpacing(8)
        cards.setVerticalSpacing(8)
        self.temperature_card = MetricCard("Temperature", "C", "#f0883e")
        self.pressure_card = MetricCard("Pressure", "bar", "#58a6ff")
        self.molar_card = MetricCard("Molar Flow", "kgmole/h", "#3fb950")
        self.mass_card = MetricCard("Mass Flow", "kg/h", "#d2a8ff")
        for index, card in enumerate((self.temperature_card, self.pressure_card, self.molar_card, self.mass_card)):
            cards.addWidget(card, index // 2, index % 2)
        left_layout.addLayout(cards)

        edit_group = QGroupBox("Edit Stream Specification")
        edit_form = QFormLayout(edit_group)
        edit_form.setContentsMargins(12, 8, 12, 10)
        edit_form.setHorizontalSpacing(10)
        edit_form.setVerticalSpacing(8)
        self.property_combo = QComboBox()
        self.property_combo.addItems(("Temperature", "Pressure", "Molar Flow", "Mass Flow"))
        self.property_value = QDoubleSpinBox()
        self.property_value.setRange(-1e12, 1e12)
        self.property_value.setDecimals(6)
        self.apply_value_button = QPushButton("Apply Value")
        edit_form.addRow("Property", self.property_combo)
        edit_form.addRow("Value", self.property_value)
        edit_form.addRow(self.apply_value_button)
        left_layout.addWidget(edit_group)

        self.composition_table = QTableWidget(0, 2)
        style_table_headers(self.composition_table, ("Component", "Mole Fraction"))
        self.composition_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.composition_table.horizontalHeader().setStretchLastSection(True)
        self.composition_table.verticalHeader().setVisible(False)
        self.composition_table.setMaximumHeight(160)
        left_layout.addWidget(self.composition_table, 0)

        right = QTabWidget()
        charts = QWidget()
        chart_layout = QVBoxLayout(charts)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        chart_layout.setSpacing(8)
        self.temperature_plot = pg.PlotWidget(title="Stream Temperatures")
        self.pressure_plot = pg.PlotWidget(title="Stream Pressures")
        self.flow_plot = pg.PlotWidget(title="Stream Molar Flows")
        for plot in (self.temperature_plot, self.pressure_plot, self.flow_plot):
            plot.setBackground("#0d1117")
            chart_layout.addWidget(plot)
        right.addTab(charts, "Analytics")

        operations_tab = QWidget()
        operations_layout = QVBoxLayout(operations_tab)
        operations_layout.setContentsMargins(8, 8, 8, 8)
        self.operations_table = QTableWidget(0, 3)
        style_table_headers(self.operations_table, ("Operation", "Type", "Solved"))
        self.operations_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.operations_table.horizontalHeader().setStretchLastSection(True)
        operations_layout.addWidget(self.operations_table)
        right.addTab(operations_tab, "Operations")

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        right.addTab(self.log_widget, "Activity Log")

        column_tab = QWidget()
        column_layout = QVBoxLayout(column_tab)
        column_layout.setContentsMargins(10, 10, 10, 10)
        column_layout.setSpacing(8)

        # --- Toolbar (HYSYS-like: one row of equal actions) ---
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(8)
        toolbar_row.addWidget(QLabel("Column"))
        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(160)
        toolbar_row.addWidget(self.column_combo, 1)

        self.inspect_column_button = QPushButton("Inspect")
        self.diagnose_column_button = QPushButton("Diagnose")
        self.dry_run_button = QPushButton("Dry-Run")
        self.one_trial_button = QPushButton("One Trial")
        self.assist_button = QPushButton("Assist Loop")
        self.assist_button.setObjectName("primaryAction")
        self.trial_map_button = QPushButton("Trial Map")
        self.intelligence_button = QPushButton("PE Board")
        toolbar_row.addWidget(QLabel("Optimize"))
        self.optimize_combo = QComboBox()
        self.optimize_combo.addItem("Min RR", "min_reflux_ratio")
        self.optimize_combo.addItem("Min Reb Q", "min_reboiler_duty")
        self.optimize_combo.addItem("Min Cond Q", "min_condenser_duty")
        self.optimize_combo.addItem("Min stages", "min_stage_count")
        self.optimize_combo.setMinimumWidth(110)
        self.optimize_combo.setToolTip(
            "What Optimize 1 minimizes:\n"
            "• Min RR — lower Active Reflux Ratio\n"
            "• Min Reb Q — lower reboiler duty (usually via RR)\n"
            "• Min Cond Q — lower condenser duty (usually via RR)\n"
            "• Min stages — propose fewer stages (needs your approval)\n"
            "Only runs if NH3 FINAL_TARGET already met."
        )
        toolbar_row.addWidget(self.optimize_combo)
        self.optimize_one_button = QPushButton("Optimize 1")
        self.optimize_one_button.setToolTip(
            "One clear optimize step: shows objective, what knob changed, "
            "before/after numbers, and KEEP or REVERSE."
        )
        self.optimize_loop_button = QPushButton("Optimize Loop")
        for button in (
            self.inspect_column_button,
            self.diagnose_column_button,
            self.dry_run_button,
            self.one_trial_button,
            self.assist_button,
            self.trial_map_button,
            self.intelligence_button,
            self.optimize_one_button,
            self.optimize_loop_button,
        ):
            button.setMinimumHeight(22)
            toolbar_row.addWidget(button)
        column_layout.addLayout(toolbar_row)

        # --- Status chips (fixed height strip) ---
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self.chip_name = StatusChip("Column")
        self.chip_stages = StatusChip("Stages")
        self.chip_feed = StatusChip("Feed stage")
        self.chip_dof = StatusChip("Degrees of freedom")
        self.chip_converged = StatusChip("Status")
        self.chip_error = StatusChip("Max spec error")
        for chip in (
            self.chip_name, self.chip_stages, self.chip_feed,
            self.chip_dof, self.chip_converged, self.chip_error,
        ):
            chips.addWidget(chip)
        column_layout.addLayout(chips)

        # --- Sub-pages like HYSYS Design → Monitor / Specs / Profile ---
        self.column_pages = QTabWidget()
        self.column_pages.setDocumentMode(True)

        # Page 1: Diagnosis
        diagnosis_page = QWidget()
        diagnosis_layout = QVBoxLayout(diagnosis_page)
        diagnosis_layout.setContentsMargins(8, 8, 8, 8)
        diagnosis_layout.setSpacing(6)
        how_to = QLabel(
            "Workflow: Inspect → Diagnose → Dry-Run → One Trial / Assist Loop. "
            "FINAL_TARGET (NH₃) stays locked unless you change it in HYSYS."
        )
        how_to.setWordWrap(True)
        how_to.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        diagnosis_layout.addWidget(how_to)
        self.column_summary = QLabel(
            "Connect, choose a column, then Inspect. Diagnosis text appears here."
        )
        self.column_summary.setWordWrap(True)
        self.column_summary.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.column_summary.setStyleSheet(
            "color: #c9d1d9; padding: 6px; background: #161b22; "
            "border: 1px solid #30363d; border-radius: 2px; font-size: 8pt;"
        )
        diagnosis_layout.addWidget(self.column_summary, 1)
        self.column_pages.addTab(diagnosis_page, "Diagnosis")

        # Page: Connections (HYSYS Design → Connections READ + F structural)
        connections_page = QWidget()
        connections_layout = QVBoxLayout(connections_page)
        connections_layout.setContentsMargins(8, 8, 8, 8)
        conn_hint = QLabel(
            "HYSYS Design → Connections. Intelligence READs this window and can RECOMMEND "
            "mechanical changes (feed stage, stages, P_cond/P_reb). "
            "Writes need your explicit approval — never silent."
        )
        conn_hint.setWordWrap(True)
        conn_hint.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        connections_layout.addWidget(conn_hint)
        self.structural_label = QLabel("Diagnose to see Connections structural recommendations.")
        self.structural_label.setWordWrap(True)
        self.structural_label.setStyleSheet(
            "color: #f0883e; border: none; background: transparent;"
        )
        connections_layout.addWidget(self.structural_label)
        conn_btns = QHBoxLayout()
        self.apply_structural_button = QPushButton("Apply First COM Proposal (requires confirm)")
        self.apply_structural_button.setObjectName("primaryAction")
        conn_btns.addWidget(self.apply_structural_button)
        conn_btns.addStretch()
        connections_layout.addLayout(conn_btns)
        self.connections_text = QTextEdit()
        self.connections_text.setReadOnly(True)
        self.connections_text.setPlainText("Inspect a column to load Connections.")
        self.connections_text.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 8pt;"
        )
        connections_layout.addWidget(self.connections_text, 1)
        self.column_pages.addTab(connections_page, "Connections")
        self._last_structural_recs: list[str] = []
        self._last_structural_payload: dict | None = None

        # Page: Specs Summary (HYSYS Design → Specs Summary)
        specs_page = QWidget()
        specs_layout = QVBoxLayout(specs_page)
        specs_layout.setContentsMargins(8, 8, 8, 8)
        specs_layout.setSpacing(6)
        specs_hint = QLabel(
            "HYSYS Design → Specs Summary (T-100): Specified | Active | Current | "
            "Fixed/Range | Prim/Alt. Est = Monitor Estimate (COM). "
            "Toggle Active/Est, then Apply. Keep Reflux Ratio Active OFF on T-100."
        )
        specs_hint.setWordWrap(True)
        specs_hint.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        specs_layout.addWidget(specs_hint)

        self.specs_clicks_label = QLabel("Diagnose to see recommended Specs Summary clicks.")
        self.specs_clicks_label.setWordWrap(True)
        self.specs_clicks_label.setStyleSheet(
            "color: #58a6ff; border: none; background: transparent;"
        )
        specs_layout.addWidget(self.specs_clicks_label)

        specs_btns = QHBoxLayout()
        self.apply_specs_button = QPushButton("Apply Active/Est → HYSYS")
        self.apply_specs_button.setObjectName("primaryAction")
        self.apply_recommended_specs_button = QPushButton("Apply Recommended Clicks")
        self.sync_spec_current_button = QPushButton("Sync Selected: Current → Goal")
        self.refresh_specs_button = QPushButton("Re-Inspect Specs")
        for b in (
            self.apply_specs_button,
            self.apply_recommended_specs_button,
            self.sync_spec_current_button,
            self.refresh_specs_button,
        ):
            specs_btns.addWidget(b)
        specs_btns.addStretch()
        specs_layout.addLayout(specs_btns)

        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Add Spec type"))
        self.add_spec_combo = QComboBox()
        self.add_spec_combo.addItems(list_add_spec_names())
        # Prefer CDU-common types near top of combo for convenience — keep HYSYS order
        idx = self.add_spec_combo.findText("Column Draw Rate")
        if idx >= 0:
            self.add_spec_combo.setCurrentIndex(idx)
        add_row.addWidget(self.add_spec_combo, 1)
        self.show_add_spec_steps_button = QPushButton("Show HYSYS Add… Steps")
        self.try_add_spec_button = QPushButton("Try COM Add Spec (approve)")
        self.try_add_spec_button.setObjectName("primaryAction")
        add_row.addWidget(self.show_add_spec_steps_button)
        add_row.addWidget(self.try_add_spec_button)
        specs_layout.addLayout(add_row)
        self.add_spec_steps_label = QLabel(
            "Pick a Column Specification Type (same list as HYSYS Add Specs), "
            "then Show Steps or Try COM Add with approval. "
            "On T-100 DOF=0: deactivate one Active first or leave new spec Estimate-only."
        )
        self.add_spec_steps_label.setWordWrap(True)
        self.add_spec_steps_label.setStyleSheet(
            "color: #8b949e; border: none; background: transparent; font-size: 8pt;"
        )
        specs_layout.addWidget(self.add_spec_steps_label)

        self.specs_empty_hint = QLabel(
            "No specs loaded yet — click Inspect."
        )
        self.specs_empty_hint.setAlignment(Qt.AlignCenter)
        self.specs_empty_hint.setMinimumHeight(40)
        self.specs_empty_hint.setStyleSheet(
            "color: #f0883e; padding: 10px; background: #12171e; "
            "border: 1px dashed #30363d; border-radius: 2px; font-size: 8pt;"
        )
        specs_layout.addWidget(self.specs_empty_hint)

        self.column_specs_table = QTableWidget(0, 8)
        style_table_headers(
            self.column_specs_table,
            (
                "Specification",
                "Specified",
                "Active",
                "Current",
                "Est",
                "Fixed/Range",
                "Prim/Alt",
                "Family",
            ),
        )
        self.column_specs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.column_specs_table.setAlternatingRowColors(True)
        self.column_specs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.column_specs_table.setWordWrap(True)
        self.column_specs_table.verticalHeader().setVisible(False)
        header = self.column_specs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.column_specs_table.setVisible(False)
        specs_layout.addWidget(self.column_specs_table, 1)
        self.column_pages.addTab(specs_page, "Specs Summary")
        self._last_specs_clicks: list[str] = []
        self._last_column_state = None

        # Page 3: Temperature profile
        profile_page = QWidget()
        profile_layout = QVBoxLayout(profile_page)
        profile_layout.setContentsMargins(8, 8, 8, 8)
        self.column_temp_plot = pg.PlotWidget(title="Stage temperatures — Main TS (top → bottom)")
        self.column_temp_plot.setBackground("#0d1117")
        self.column_temp_plot.setLabel("left", "Temperature", units="C")
        self.column_temp_plot.setLabel("bottom", "Stage")
        profile_layout.addWidget(self.column_temp_plot, 1)
        self.column_pages.addTab(profile_page, "Profile")

        # Page 4: Activity log
        activity_page = QWidget()
        activity_layout = QVBoxLayout(activity_page)
        activity_layout.setContentsMargins(8, 8, 8, 8)
        self.column_assist_log = QTextEdit()
        self.column_assist_log.setReadOnly(True)
        activity_layout.addWidget(self.column_assist_log, 1)
        self.column_pages.addTab(activity_page, "Activity")

        column_layout.addWidget(self.column_pages, 1)

        right.addTab(column_tab, "Column Assistant")
        right.setCurrentIndex(right.count() - 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes((420, 860))
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

    def setup_connections(self) -> None:
        self.connect_button.clicked.connect(self.toggle_connection)
        self.open_button.clicked.connect(self.open_case)
        self.refresh_button.clicked.connect(self.refresh_data)
        self.solve_button.clicked.connect(self.solve_case)
        self.auto_refresh.toggled.connect(self.timer.setActive if hasattr(self.timer, "setActive") else self._toggle_timer)
        self.export_button.clicked.connect(self.export_excel)
        self.apply_components_button.clicked.connect(self.apply_components)
        self.stream_combo.currentTextChanged.connect(self.load_stream_detail)
        self.apply_value_button.clicked.connect(self.apply_stream_value)
        self.inspect_column_button.clicked.connect(self.inspect_column)
        self.diagnose_column_button.clicked.connect(self.diagnose_column)
        self.dry_run_button.clicked.connect(lambda: self.run_column_trial(dry_run=True))
        self.one_trial_button.clicked.connect(lambda: self.run_column_trial(dry_run=False))
        self.assist_button.clicked.connect(self.run_assist_loop)
        self.optimize_one_button.clicked.connect(lambda: self.run_optimize_trial(loop=False))
        self.optimize_loop_button.clicked.connect(lambda: self.run_optimize_trial(loop=True))
        self.optimize_combo.currentIndexChanged.connect(self._on_optimize_objective_changed)
        self.trial_map_button.clicked.connect(self.open_trial_map)
        self.intelligence_button.clicked.connect(self.open_intelligence)
        self.apply_specs_button.clicked.connect(self.apply_specs_summary_to_hysys)
        self.apply_recommended_specs_button.clicked.connect(self.apply_recommended_specs_clicks)
        self.sync_spec_current_button.clicked.connect(self.sync_selected_spec_current_to_goal)
        self.refresh_specs_button.clicked.connect(self.inspect_column)
        self.apply_structural_button.clicked.connect(self.apply_structural_with_approval)
        self.show_add_spec_steps_button.clicked.connect(self.show_add_spec_steps)
        self.try_add_spec_button.clicked.connect(self.try_add_spec_with_approval)

    def _toggle_timer(self, enabled: bool) -> None:
        self.timer.start() if enabled else self.timer.stop()

    def log(self, message: str) -> None:
        self.log_widget.append(f"[{datetime.now():%H:%M:%S}] {message}")

    def toggle_connection(self) -> None:
        if self.controller.connected:
            self.controller.disconnect()
            self.timer.stop()
            self.stream_combo.clear()
            self.column_combo.clear()
            self.status.setText("● DISCONNECTED")
            self.status.setStyleSheet("color: #f85149;")
            self.connect_button.setText("Connect")
            self.log("Disconnected")
            return
        self._connect(None)

    def open_case(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open HYSYS Case", "", "HYSYS Case (*.hsc);;All Files (*)")
        if path:
            self._connect(path)

    def _connect(self, path: str | None) -> None:
        try:
            self.controller.connect(path)
            self.status.setText("● CONNECTED")
            self.status.setStyleSheet("color: #3fb950;")
            self.connect_button.setText("Disconnect")
            self.component_input.setText(", ".join(self.controller.component_names))
            self.log("Connected to HYSYS")
            self.refresh_data()
        except Exception as exc:
            self._show_error(exc)

    def refresh_data(self) -> None:
        if not self.controller.connected:
            return
        if getattr(self, "_column_job_busy", False):
            return
        try:
            self.streams = self.controller.get_stream_objects()
            selected = self.stream_combo.currentText()
            self.stream_combo.blockSignals(True)
            self.stream_combo.clear()
            self.stream_combo.addItems(sorted(self.streams))
            index = self.stream_combo.findText(selected)
            if index >= 0:
                self.stream_combo.setCurrentIndex(index)
            self.stream_combo.blockSignals(False)
            self.stream_data = [self.controller.get_stream_data(item) for item in self.streams.values()]
            self.operations = self.controller.get_operations()
            self._update_plots()
            self._update_operations()
            self._refresh_column_list()
            self.load_stream_detail(self.stream_combo.currentText())
            self.log(f"Synchronized {len(self.stream_data)} streams and {len(self.operations)} operations")
        except Exception as exc:
            self._show_error(exc)

    def _refresh_column_list(self) -> None:
        selected = self.column_combo.currentText()
        self.column_combo.blockSignals(True)
        self.column_combo.clear()
        try:
            names = self.column_api.list_columns()
        except Exception:
            names = []
        self.column_combo.addItems(names)
        index = self.column_combo.findText(selected)
        if index >= 0:
            self.column_combo.setCurrentIndex(index)
        self.column_combo.blockSignals(False)

    def _selected_column(self) -> str:
        name = self.column_combo.currentText().strip()
        if not name:
            raise HysysError("No distillation column selected.")
        return name

    def _column_assist_buttons(self) -> list:
        return [
            self.inspect_column_button,
            self.diagnose_column_button,
            self.dry_run_button,
            self.one_trial_button,
            self.assist_button,
            self.optimize_one_button,
            self.optimize_loop_button,
            self.trial_map_button,
            self.intelligence_button,
            self.apply_specs_button,
            self.apply_recommended_specs_button,
            self.sync_spec_current_button,
            self.refresh_specs_button,
            self.apply_structural_button,
            self.show_add_spec_steps_button,
            self.try_add_spec_button,
        ]

    def _set_column_busy(self, busy: bool, message: str = "") -> None:
        self._column_job_busy = busy
        for btn in self._column_assist_buttons():
            btn.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            if message:
                self._column_assist_log(message)
                self.column_summary.setText(message)
                self.column_summary.setStyleSheet(
                    "color: #58a6ff; padding: 6px; background: #161b22; "
                    "border: 1px solid #30363d; border-radius: 2px; font-size: 8pt;"
                )
            QApplication.processEvents()
        else:
            QApplication.restoreOverrideCursor()

    def _run_column_job(self, label: str, work) -> None:
        """Defer HYSYS COM so the click paints; show busy state while COM runs."""
        if self._column_job_busy:
            self._column_assist_log(f"Busy — ignore '{label}' (wait for current HYSYS action).")
            return

        def _execute() -> None:
            self._set_column_busy(True, f"Working: {label}... (HYSYS COM — UI may pause briefly)")
            auto_was_on = self.timer.isActive()
            if auto_was_on:
                self.timer.stop()
            try:
                work()
            except Exception as exc:
                self._show_error(exc)
            finally:
                if auto_was_on and self.auto_refresh.isChecked():
                    self.timer.start()
                self._set_column_busy(False)

        QTimer.singleShot(0, _execute)

    def _column_assist_log(self, message: str) -> None:
        self.column_assist_log.append(f"[{datetime.now():%H:%M:%S}] {message}")
        self.log(message)

    def _show_column_state(self, state, diagnosis=None) -> None:
        self.chip_name.set_value(f"{state.name}")
        self.chip_stages.set_value("—" if state.number_of_stages is None else str(state.number_of_stages))
        self.chip_feed.set_value("—" if state.feed_stage is None else str(state.feed_stage))

        dof = state.degrees_of_freedom
        if dof is None:
            self.chip_dof.set_value("—")
        elif dof == 0:
            self.chip_dof.set_value("0 (OK)", "#3fb950")
        else:
            self.chip_dof.set_value(str(dof), "#f85149")

        if state.appears_converged and getattr(state, "physical_solution", False):
            self.chip_converged.set_value("Converged", "#3fb950")
        elif getattr(state, "physical_solution", True) is False:
            self.chip_converged.set_value("State B (numerical)", "#f85149")
        else:
            self.chip_converged.set_value("Not converged", "#f0883e")

        self.chip_error.set_value(f"{state.max_active_spec_error:.3g}")

        if diagnosis is not None:
            eng = getattr(diagnosis, "engineering_state", None)
            pe = getattr(diagnosis, "pe_read", "")
            pot = getattr(diagnosis, "potential", "")
            fam = getattr(diagnosis, "preferred_family", "") or "-"
            hyp = getattr(diagnosis, "pe_hypothesis", "") or "-"
            detail = diagnosis.summary
            if eng is not None:
                detail = (
                    f"[{eng.value}] potential={pot}\n"
                    f"Family: {fam}\n"
                    f"Hypothesis: {hyp}\n"
                    f"{pe}\n{detail}"
                )
            popup_clues = getattr(diagnosis, "hysys_dialog_clues", None) or []
            if popup_clues:
                detail += "\nHYSYS POPUP CLUES:\n• " + "\n• ".join(popup_clues[:4])
            msg_clues = getattr(diagnosis, "hysys_message_clues", None) or []
            if msg_clues:
                detail += "\nHYSYS MESSAGES:\n• " + "\n• ".join(msg_clues[:6])
            if diagnosis.details:
                detail += "\n• " + "\n• ".join(diagnosis.details[:8])
            if getattr(state, "bottoms_nh3_mass_frac", None) is not None:
                detail += f"\n• Bottoms NH3 (stream)={state.bottoms_nh3_mass_frac:.4g}"
            mu = getattr(state, "molar_flow_unit", "kgmole/h")
            if getattr(state, "overhead_molar_flow_kgmole_h", None) is not None:
                detail += f"\n• Ovhd={state.overhead_molar_flow_kgmole_h:.4g} {mu}"
            if getattr(state, "bottoms_molar_flow_kgmole_h", None) is not None:
                detail += f"\n• Btms={state.bottoms_molar_flow_kgmole_h:.4g} {mu}"
            self.column_summary.setText(f"{diagnosis.severity.upper()}: {detail}")
            color = {"info": "#3fb950", "warn": "#f0883e", "critical": "#f85149"}.get(
                diagnosis.severity, "#8b949e"
            )
            self.column_summary.setStyleSheet(
                f"color: {color}; padding: 6px; background: #161b22; "
                "border: 1px solid #30363d; border-radius: 2px; font-size: 8pt;"
            )
        else:
            self.column_summary.setText(
                f"{state.name} ({state.flowsheet_tag})  ·  score {score_state(state):.4g}\n"
                "Active specs drive the solve. Inactive rows are estimates only.\n"
                "FINAL_TARGET (NH3) is locked — Assist will not auto-relax product GoalValue.\n"
                "Click Diagnose to see Family + Hypothesis (multi-variable PE choice)."
            )
            self.column_summary.setStyleSheet(
                "color: #8b949e; padding: 6px; background: #161b22; "
                "border: 1px solid #30363d; border-radius: 2px; font-size: 8pt;"
            )

        self.connections_text.setPlainText(
            format_connections_block(state)
            + "\n\n"
            + format_monitor_block(state)
            + "\n\n"
            + format_specs_page_block(state)
            + "\n\n"
            + format_specs_summary_block(state)
            + "\n\n"
            + format_subcooling_block(state)
            + "\n\n"
            + format_side_ops_block(state)
            + "\n\n"
            + format_rating_block(state)
        )
        self._last_column_state = state

        if diagnosis is not None:
            struct = getattr(diagnosis, "structural_recommendations", []) or []
            self._last_structural_recs = list(struct)
            from column_connections import pick_primary_structural_action, recommend_connections_moves

            moves = recommend_connections_moves(
                state,
                diagnosis.engineering_state,
                preferred_family=diagnosis.preferred_family,
                infeasible_evidence=diagnosis.engineering_state.value.startswith("F"),
            )
            self._last_structural_payload = pick_primary_structural_action(moves)
            if struct:
                self.structural_label.setText(
                    "STRUCTURAL (mechanical) — approval required:\n• " + "\n• ".join(struct)
                )
            else:
                self.structural_label.setText(
                    "No Connections structural change recommended right now "
                    "(operating families still preferred)."
                )
            clicks = getattr(diagnosis, "specs_summary_clicks", []) or []
            self._last_specs_clicks = list(clicks)
            if clicks:
                self.specs_clicks_label.setText(
                    "Recommended Specs Summary clicks:\n• " + "\n• ".join(clicks)
                )
            else:
                self.specs_clicks_label.setText("No Specs Summary click changes recommended.")
        elif not getattr(self, "_last_specs_clicks", None):
            self.specs_clicks_label.setText("Diagnose to see recommended Specs Summary clicks.")
            if not getattr(self, "_last_structural_recs", None):
                self.structural_label.setText(
                    "Diagnose to see Connections structural recommendations."
                )

        if not state.specs:
            self.specs_empty_hint.setText(
                "Inspect ran, but HYSYS returned no Specs for this column."
            )
            self.specs_empty_hint.setVisible(True)
            self.column_specs_table.setVisible(False)
            self.column_specs_table.setRowCount(0)
        else:
            self.specs_empty_hint.setVisible(False)
            self.column_specs_table.setVisible(True)
            self.column_specs_table.setRowCount(len(state.specs))
            for row, spec in enumerate(state.specs):
                unit = getattr(spec, "display_unit", "") or ""
                goal_v = getattr(spec, "goal_display", None)
                if goal_v is None:
                    goal_v = spec.goal_value
                cur_v = getattr(spec, "current_display", None)
                if cur_v is None:
                    cur_v = spec.current_value

                def _fmt(val: float | None) -> str:
                    if val is None:
                        return "—"
                    text = f"{val:.6g}"
                    return f"{text} {unit}".strip() if unit else text

                if spec.error is None:
                    residual = "—"
                elif abs(spec.error) >= 1e4:
                    residual = "n/a"
                else:
                    residual = f"{spec.error:.4g}"

                name_item = QTableWidgetItem(spec.name)
                goal_item = QTableWidgetItem(_fmt(goal_v))
                active_item = QTableWidgetItem("")
                active_item.setFlags(
                    Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
                )
                active_item.setCheckState(Qt.Checked if spec.is_active else Qt.Unchecked)
                # Specs Summary "Current" checkbox (HYSYS)
                current_chk = QTableWidgetItem("")
                current_chk.setFlags(
                    Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
                )
                cur_on = bool(spec.summary_current or spec.use_as_current or spec.is_active)
                if not spec.is_active and "reflux ratio" in spec.name.lower():
                    cur_on = bool(spec.summary_current or spec.use_as_current)
                current_chk.setCheckState(Qt.Checked if cur_on else Qt.Unchecked)
                # Monitor Estimate (COM) — not on Specs Summary UI but useful to write
                est_item = QTableWidgetItem("")
                est_item.setFlags(
                    Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
                )
                est_on = spec.use_as_estimate is not False
                est_item.setCheckState(Qt.Checked if est_on else Qt.Unchecked)
                fixed_item = QTableWidgetItem(spec.fixed_or_ranged or ("Fixed" if spec.is_active else "—"))
                prim_item = QTableWidgetItem(
                    spec.primary_or_alternate or ("Primary" if spec.is_active else "—")
                )
                fam_item = QTableWidgetItem(getattr(spec, "mv_family", "") or "—")
                if spec.is_active:
                    name_item.setForeground(QColor("#3fb950"))
                self.column_specs_table.setItem(row, 0, name_item)
                self.column_specs_table.setItem(row, 1, goal_item)
                self.column_specs_table.setItem(row, 2, active_item)
                self.column_specs_table.setItem(row, 3, current_chk)
                self.column_specs_table.setItem(row, 4, est_item)
                self.column_specs_table.setItem(row, 5, fixed_item)
                self.column_specs_table.setItem(row, 6, prim_item)
                self.column_specs_table.setItem(row, 7, fam_item)
                self.column_specs_table.setRowHeight(row, 28)

        self.column_temp_plot.clear()
        temps = state.profile.temperatures
        if temps:
            self.column_temp_plot.plot(
                list(range(1, len(temps) + 1)),
                temps,
                pen=pg.mkPen("#f0883e", width=2),
                symbol="o",
            )
        QApplication.processEvents()

    def _specs_summary_rows_from_table(self) -> list[dict]:
        rows = []
        for row in range(self.column_specs_table.rowCount()):
            name_item = self.column_specs_table.item(row, 0)
            active_item = self.column_specs_table.item(row, 2)
            est_item = self.column_specs_table.item(row, 4)
            if name_item is None or active_item is None:
                continue
            rows.append(
                {
                    "name": name_item.text(),
                    "is_active": active_item.checkState() == Qt.Checked,
                    "is_estimate": (
                        est_item.checkState() == Qt.Checked if est_item is not None else True
                    ),
                }
            )
        return rows

    def show_add_spec_steps(self) -> None:
        typ = self.add_spec_combo.currentText().strip()
        col = self.column_combo.currentText().strip() or "T-100"
        steps = format_add_spec_hysys_steps(typ, column_hint=col)
        self.add_spec_steps_label.setText(steps)
        self.add_spec_steps_label.setStyleSheet(
            "color: #58a6ff; border: none; background: transparent; font-size: 8pt;"
        )
        self._column_assist_log(steps)

    def try_add_spec_with_approval(self) -> None:
        """Approval-gated COM Add Spec — falls back to HYSYS UI steps if COM fails."""
        typ = self.add_spec_combo.currentText().strip()
        try:
            name = self._selected_column()
        except Exception as exc:
            self._show_error(exc)
            return

        state = getattr(self, "_last_column_state", None)
        dof = getattr(state, "degrees_of_freedom", None) if state else None
        warn_dof = ""
        allow_zero = False
        if dof == 0:
            warn_dof = (
                "\n\nWARNING: DOF is already 0. Adding an Active spec over-specifies.\n"
                "Prefer: deactivate one Active (1-for-1), or leave the new spec Estimate-only.\n"
            )
            reply0 = QMessageBox.question(
                self,
                "DOF already 0",
                "Column DOF is 0 (like T-100).\n\n"
                "Continue and allow COM Add anyway?\n"
                "(You must keep DOF healthy — Estimate-only or 1-for-1 swap.)"
                + warn_dof,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply0 != QMessageBox.Yes:
                self.show_add_spec_steps()
                return
            allow_zero = True

        steps = format_add_spec_hysys_steps(typ, column_hint=name)
        reply = QMessageBox.question(
            self,
            "Approve Add Spec?",
            "Create a new column specification in HYSYS?\n\n"
            f"Column: {name}\n"
            f"Type: {typ}\n"
            f"{warn_dof}\n"
            "This is approval-gated (not silent). If COM Add is unsupported on your "
            "HYSYS build, Assist will show the exact Specs → Add… click steps.\n\n"
            f"{steps}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        def work() -> None:
            try:
                notes = self.column_api.add_specification(
                    name,
                    typ,
                    approved=True,
                    allow_when_dof_zero=allow_zero,
                )
                self._column_assist_log("Add Spec:\n  " + "\n  ".join(notes))
                self.add_spec_steps_label.setText("Add Spec OK:\n" + "\n".join(notes))
                self.add_spec_steps_label.setStyleSheet(
                    "color: #3fb950; border: none; background: transparent; font-size: 8pt;"
                )
                self.inspect_column()
            except Exception as exc:
                text = str(exc)
                self.add_spec_steps_label.setText(text)
                self.add_spec_steps_label.setStyleSheet(
                    "color: #f0883e; border: none; background: transparent; font-size: 8pt;"
                )
                raise

        self._run_column_job("Add Spec (approved)", work)

    def apply_structural_with_approval(self) -> None:
        """Mechanical Connections write — QMessageBox confirm required."""
        payload = getattr(self, "_last_structural_payload", None)
        if not payload:
            QMessageBox.information(
                self,
                "No structural proposal",
                "Diagnose first. Structural proposals appear when Family F / State F "
                "or operating families are exhausted.",
            )
            return
        if not payload.get("com_writable", True):
            QMessageBox.warning(
                self,
                "Manual in HYSYS",
                f"This proposal is MANUAL:\n\n{payload.get('description')}\n\n"
                "Change it on Design → Connections in HYSYS, then Inspect again.",
            )
            return
        msg = (
            "MECHANICAL CHANGE — you are about to edit Design → Connections.\n\n"
            f"{payload.get('description')}\n\n"
            f"parameter: {payload.get('parameter')}\n"
            f"current → proposed: {payload.get('current')} → {payload.get('proposed')}\n\n"
            "This is not a GoalValue nudge. Confirm to apply via COM (no auto-save .hsc)."
        )
        reply = QMessageBox.question(
            self,
            "Approve structural Connections change?",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            self._column_assist_log("Structural change cancelled by user (no write).")
            return

        def work() -> None:
            name = self._selected_column()
            notes = self.column_api.apply_structural_move(
                name,
                str(payload["parameter"]),
                payload["proposed"],
                approved=True,
                run_after=True,
            )
            state, diagnosis = self.assistant.diagnose_column(name)
            self._show_column_state(state, diagnosis)
            self._column_assist_log(
                "Applied APPROVED structural Connections change:\n  " + "\n  ".join(notes)
            )

        self._run_column_job("Apply structural (approved)", work)

    def apply_specs_summary_to_hysys(self) -> None:
        def work() -> None:
            name = self._selected_column()
            rows = self._specs_summary_rows_from_table()
            if not rows:
                raise HysysError("No specs in table — Inspect first.")
            notes = self.column_api.apply_specs_summary(name, rows)
            self.column_api.run_column(name)
            state = self.assistant.inspect(name)
            self._show_column_state(state)
            self._column_assist_log("Applied Specs Summary -> HYSYS:\n  " + "\n  ".join(notes))
            self.column_pages.setCurrentIndex(2)

        self._run_column_job("Apply Specs Summary", work)

    def apply_recommended_specs_clicks(self) -> None:
        def work() -> None:
            from column_spec_catalog import recommend_specs_summary_clicks

            name = self._selected_column()
            state = self.assistant.inspect(name)
            _, diagnosis = self.assistant.diagnose_column(name)
            clicks = recommend_specs_summary_clicks(
                spec_rows=[
                    {
                        "name": s.name,
                        "is_active": s.is_active,
                        "is_estimate": s.use_as_estimate,
                    }
                    for s in state.specs
                ],
                engineering_state=diagnosis.engineering_state.value,
                bottoms_flow_kgmole_h=state.bottoms_molar_flow_kgmole_h,
                min_bottoms_flow_kgmole_h=self.assistant.limits.min_bottoms_flow_kgmole_h,
            )
            if not clicks:
                self._column_assist_log("No recommended Specs Summary clicks.")
                return
            notes: list[str] = []
            for click in clicks:
                if click.sync_goal_from_current:
                    val = self.column_api.sync_spec_goal_from_current(name, click.spec_name)
                    notes.append(f"{click.spec_name}: Goal<-Current ({val:.6g})")
                row: dict = {"name": click.spec_name}
                if click.set_active is not None:
                    row["is_active"] = click.set_active
                if click.set_estimate is not None:
                    row["is_estimate"] = click.set_estimate
                if len(row) > 1:
                    notes.extend(self.column_api.apply_specs_summary(name, [row]))
            self.column_api.run_column(name)
            state2, diagnosis2 = self.assistant.diagnose_column(name)
            self._show_column_state(state2, diagnosis2)
            self._column_assist_log(
                "Applied recommended Specs Summary clicks:\n  "
                + "\n  ".join(notes)
                + "\n"
                + format_pe_board(state2, diagnosis2)
            )
            self.column_pages.setCurrentIndex(2)

        self._run_column_job("Apply recommended clicks", work)

    def sync_selected_spec_current_to_goal(self) -> None:
        def work() -> None:
            name = self._selected_column()
            row = self.column_specs_table.currentRow()
            if row < 0:
                raise HysysError("Select a specification row first.")
            item = self.column_specs_table.item(row, 0)
            if item is None:
                raise HysysError("Invalid selection.")
            spec_name = item.text()
            val = self.column_api.sync_spec_goal_from_current(name, spec_name)
            state = self.assistant.inspect(name)
            self._show_column_state(state)
            self._column_assist_log(f"Synced {spec_name}: Goal <- Current ({val:.6g})")

        self._run_column_job("Sync Goal from Current", work)

    def inspect_column(self) -> None:
        def work() -> None:
            state = self.assistant.inspect(self._selected_column())
            self._show_column_state(state)
            self._column_assist_log(f"Inspected {state.name}: DOF={state.degrees_of_freedom}")
            self.column_pages.setCurrentIndex(2)

        self._run_column_job("Inspect", work)

    def diagnose_column(self) -> None:
        def work() -> None:
            state, diagnosis = self.assistant.diagnose_column(self._selected_column())
            self._show_column_state(state, diagnosis)
            self._column_assist_log(format_pe_board(state, diagnosis))
            self.column_pages.setCurrentIndex(2)

        self._run_column_job("Diagnose", work)

    def open_trial_map(self) -> None:
        def work() -> None:
            name = self.column_combo.currentText().strip() or "SW Stripper"
            if self.trial_map_window is None or not isinstance(self.trial_map_window, TrialMapWindow):
                self.trial_map_window = TrialMapWindow(self.assistant)
            self.trial_map_window.refresh(name)
            self.trial_map_window.show()
            self.trial_map_window.showMaximized()
            self.trial_map_window.raise_()
            self.trial_map_window.activateWindow()
            self._column_assist_log(f"Opened Trial Map for {name}")

        self._run_column_job("Trial Map", work)

    def open_intelligence(self) -> None:
        def work() -> None:
            name = self.column_combo.currentText().strip() or "SW Stripper"
            if self.intelligence_window is None:
                self.intelligence_window = IntelligenceWindow(self.assistant)
            self.intelligence_window.refresh(name)
            self.intelligence_window.show()
            self.intelligence_window.raise_()
            self.intelligence_window.activateWindow()
            self._column_assist_log(f"Opened PE Intelligence for {name}")

        self._run_column_job("PE Board", work)

    def log_feed_change_on_map(self, description: str) -> None:
        """Optional: record an external feed/case change onto the trial map history."""
        self.assistant.history.append(manual_map_event(description))
        if self.trial_map_window is not None and self.trial_map_window.isVisible():
            self.trial_map_window.refresh(self.column_combo.currentText().strip())

    def run_column_trial(self, dry_run: bool = True) -> None:
        label = "Dry-Run" if dry_run else "One Trial"

        def work() -> None:
            name = self._selected_column()
            if not dry_run:
                answer = QMessageBox.question(
                    self,
                    "Column Assistant",
                    (
                        "Run one live trial on the HYSYS column?\n\n"
                        "This may change an active GoalValue, solve, then keep or reverse."
                    ),
                )
                if answer != QMessageBox.Yes:
                    return
            result = self.assistant.run_one_trial(name, dry_run=dry_run)
            if result.after_state is not None:
                _, diagnosis = self.assistant.diagnose_column(name)
                self._show_column_state(result.after_state, diagnosis)
            self._column_assist_log(result.message)
            if self.trial_map_window is not None and self.trial_map_window.isVisible():
                self.trial_map_window.refresh(name)

        self._run_column_job(label, work)

    def _on_optimize_objective_changed(self) -> None:
        key = self.optimize_combo.currentData()
        if key:
            self.assistant.set_optimize_objective(str(key))

    def run_optimize_trial(self, loop: bool = False) -> None:
        label = "Optimize Loop" if loop else "Optimize 1"

        def work() -> None:
            name = self._selected_column()
            key = self.optimize_combo.currentData()
            if key:
                self.assistant.set_optimize_objective(str(key))
            if loop:
                answer = QMessageBox.question(
                    self,
                    "Simple Optimize",
                    (
                        "Run simple optimize loop?\n\n"
                        "Requires FINAL_TARGET already met. Minimizes selected objective "
                        "(RR / duty / stages). Stages need separate approval. "
                        "Never relaxes product specs."
                    ),
                )
                if answer != QMessageBox.Yes:
                    return
                results = self.assistant.assist_optimize(name, dry_run=False)
            else:
                results = [self.assistant.run_one_optimize_trial(name, dry_run=False)]
            if results and results[-1].after_state is not None:
                _, diagnosis = self.assistant.diagnose_column(name)
                self._show_column_state(results[-1].after_state, diagnosis)
            for result in results:
                self._column_assist_log(result.message)
                if result.action.kind == "structural_approval":
                    self._last_structural_payload = dict(result.action.payload)
                    self.structural_label.setText(
                        "OPTIMIZE structural proposal (approve on Connections tab):\n• "
                        + result.action.description
                    )
            # Clear popup so Optimize 1 is obvious
            if results and not loop:
                obj_name = self.optimize_combo.currentText()
                header = (
                    f"You asked Optimize 1 with objective: {obj_name}\n"
                    f"(dropdown Optimize = what we minimize)\n\n"
                )
                QMessageBox.information(
                    self,
                    f"Optimize 1 — {obj_name}",
                    header + results[-1].message,
                )

        self._run_column_job(label, work)

    def run_assist_loop(self) -> None:
        def work() -> None:
            name = self._selected_column()
            answer = QMessageBox.question(
                self,
                "Column Assistant",
                (
                    "Run the automatic assist loop?\n\n"
                    "Sequence: diagnose -> one bounded change -> solve -> keep/reverse -> repeat.\n"
                    "Stops when converged, DOF blocked, or no progress."
                ),
            )
            if answer != QMessageBox.Yes:
                return
            results = self.assistant.assist(name, dry_run=False)
            if results and results[-1].after_state is not None:
                _, diagnosis = self.assistant.diagnose_column(name)
                self._show_column_state(results[-1].after_state, diagnosis)
            for result in results:
                self._column_assist_log(result.message)
            if self.trial_map_window is not None and self.trial_map_window.isVisible():
                self.trial_map_window.refresh(name)

        self._run_column_job("Assist Loop", work)

    def load_stream_detail(self, name: str) -> None:
        stream = self.streams.get(name)
        if stream is None:
            return
        try:
            data = self.controller.get_stream_data(stream)
            self.temperature_card.update_value(data.temperature)
            self.pressure_card.update_value(data.pressure)
            self.molar_card.update_value(data.molar_flow)
            self.mass_card.update_value(data.mass_flow)
            self.temperature_card.set_unit(data.temperature_unit)
            self.pressure_card.set_unit(data.pressure_unit)
            self.molar_card.set_unit(data.molar_flow_unit)
            self.mass_card.set_unit(data.mass_flow_unit)
            self.composition_table.setRowCount(len(data.composition))
            for row, (component, value) in enumerate(data.composition.items()):
                self.composition_table.setItem(row, 0, QTableWidgetItem(component))
                self.composition_table.setItem(row, 1, QTableWidgetItem(f"{value:.8g}"))
        except Exception as exc:
            self._show_error(exc)

    def apply_components(self) -> None:
        names = self.controller.set_components_manually(self.component_input.text())
        self.log(f"Applied {len(names)} manual component names")
        self.load_stream_detail(self.stream_combo.currentText())

    def apply_stream_value(self) -> None:
        try:
            self.controller.set_stream_value(
                self.stream_combo.currentText(),
                self.property_combo.currentText(),
                self.property_value.value(),
            )
            self.log("Stream specification updated")
            self.refresh_data()
        except Exception as exc:
            self._show_error(exc)

    def solve_case(self) -> None:
        try:
            self.controller.solve()
            self.log("Solve requested")
            QTimer.singleShot(500, self.refresh_data)
        except Exception as exc:
            self._show_error(exc)

    def _update_plots(self) -> None:
        units = self.controller.display_units if self.controller.connected else None
        if units is not None:
            self.temperature_plot.setTitle(f"Stream Temperatures ({units.temperature})")
            self.pressure_plot.setTitle(f"Stream Pressures ({units.pressure})")
            self.flow_plot.setTitle(f"Stream Molar Flows ({units.molar_flow})")
        specs = (
            (self.temperature_plot, [x.temperature for x in self.stream_data], "#f0883e"),
            (self.pressure_plot, [x.pressure for x in self.stream_data], "#58a6ff"),
            (self.flow_plot, [x.molar_flow for x in self.stream_data], "#3fb950"),
        )
        for plot, values, color in specs:
            plot.clear()
            x_values, y_values = zip(*((i, value) for i, value in enumerate(values) if value is not None), strict=False) if any(value is not None for value in values) else ((), ())
            if y_values:
                plot.plot(x_values, y_values, pen=pg.mkPen(color, width=2), symbol="o")

    def _update_operations(self) -> None:
        self.operations_table.setRowCount(len(self.operations))
        for row, operation in enumerate(self.operations):
            values = (operation.name, operation.operation_type, "Unknown" if operation.is_solved is None else str(operation.is_solved))
            for column, value in enumerate(values):
                self.operations_table.setItem(row, column, QTableWidgetItem(value))

    def export_excel(self) -> None:
        if not self.stream_data:
            self._show_error(HysysError("Refresh HYSYS data before exporting."))
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export HYSYS Data", "HYSYS_Export.xlsx", "Excel Workbook (*.xlsx)")
        if not path:
            return
        try:
            export_workbook(path, self.stream_data, self.operations)
            self.log(f"Exported {path}")
        except Exception as exc:
            self._show_error(exc)

    def _show_error(self, error: Exception) -> None:
        self.log(f"ERROR: {error}")
        QMessageBox.critical(self, "CDU Assist v1", str(error))


# Backward-compatible alias
HysysStudio = CduAssist
SimpleColumnAssist = CduAssist  # backward-compatible alias

