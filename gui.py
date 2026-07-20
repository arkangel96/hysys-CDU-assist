from __future__ import annotations

from datetime import datetime

import pyqtgraph as pg
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from column_api import ColumnController
from column_engine import ConvergenceAssistant, diagnose, score_state
from column_models import ConvergenceLimits
from exporter import export_workbook
from hysys_api import HysysController, HysysError


DARK_THEME = """
QMainWindow, QWidget { background: #0d1117; color: #c9d1d9; }
QFrame {
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 8px;
  background: #161b22;
}
QGroupBox {
  border: 1px solid #30363d;
  border-radius: 6px;
  margin-top: 14px;
  padding: 14px 10px 10px 10px;
  font-weight: 600;
}
QGroupBox::title {
  subcontrol-origin: margin;
  subcontrol-position: top left;
  left: 12px;
  padding: 0 6px;
  color: #c9d1d9;
  background: #0d1117;
}
QPushButton {
  background: #21262d;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 8px 14px;
  min-height: 18px;
}
QPushButton:hover { background: #30363d; }
QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QTableWidget {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 6px;
  min-height: 18px;
}
QHeaderView::section {
  background: #161b22;
  padding: 10px 8px;
  border: 0;
  border-right: 1px solid #30363d;
  border-bottom: 1px solid #30363d;
  font-weight: 600;
  color: #c9d1d9;
}
QTableWidget {
  gridline-color: #30363d;
  selection-background-color: #1f6feb;
}
QTableWidget::item { padding: 6px; }
QTabWidget::pane {
  border: 1px solid #30363d;
  border-radius: 4px;
  top: -1px;
  padding: 6px;
}
QTabBar::tab {
  background: #161b22;
  border: 1px solid #30363d;
  padding: 8px 14px;
  margin-right: 2px;
}
QTabBar::tab:selected {
  background: #21262d;
  border-bottom-color: #21262d;
  color: #58a6ff;
}
QSplitter::handle { background: #21262d; width: 4px; }
"""


class MetricCard(QFrame):
    def __init__(self, title: str, unit: str, color: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        title_label = QLabel(title.upper())
        title_label.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        self.value = QLabel("—")
        self.value.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {color}; border: none; background: transparent;"
        )
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        self.unit_label = unit_label
        layout.addWidget(title_label)
        layout.addWidget(self.value)
        layout.addWidget(unit_label)

    def update_value(self, value: float | None) -> None:
        self.value.setText("—" if value is None else f"{value:,.4g}")

    def set_unit(self, unit: str) -> None:
        self.unit_label.setText(unit)


class StatusChip(QFrame):
    """Small labeled status block for column overview."""

    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        self.title = QLabel(title)
        self.title.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        self.value = QLabel("—")
        self.value.setStyleSheet(
            "color: #c9d1d9; font-size: 16px; font-weight: 700; border: none; background: transparent;"
        )
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, text: str, color: str | None = None) -> None:
        self.value.setText(text)
        color = color or "#c9d1d9"
        self.value.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 700; border: none; background: transparent;"
        )


class HysysStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.controller = HysysController()
        self.column_api = ColumnController(self.controller)
        self.assistant = ConvergenceAssistant(self.column_api, ConvergenceLimits())
        self.streams = {}
        self.stream_data = []
        self.operations = []
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh_data)
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self) -> None:
        self.setWindowTitle("Aspen HYSYS Studio")
        self.setMinimumSize(1280, 820)
        self.setStyleSheet(DARK_THEME)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 4)
        logo = QLabel("HYSYS STUDIO")
        logo.setStyleSheet("font-size: 22px; font-weight: 700; color: #58a6ff;")
        self.status = QLabel("● DISCONNECTED")
        self.status.setStyleSheet("color: #f85149; font-weight: 600;")
        top.addWidget(logo)
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
        component_layout = QHBoxLayout(components)
        component_layout.setContentsMargins(12, 8, 12, 10)
        component_layout.setSpacing(10)
        self.component_input = QLineEdit()
        self.component_input.setPlaceholderText("Methane, Ethane, Propane …")
        self.apply_components_button = QPushButton("Apply Components")
        component_layout.addWidget(self.component_input)
        component_layout.addWidget(self.apply_components_button)
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
        self.composition_table.setHorizontalHeaderLabels(("Component", "Mole Fraction"))
        self.composition_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.composition_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.composition_table, 1)

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
        self.operations_table.setHorizontalHeaderLabels(("Operation", "Type", "Solved"))
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
        column_layout.setSpacing(10)

        col_select = QHBoxLayout()
        col_select.setSpacing(8)
        col_select.addWidget(QLabel("Column"))
        self.column_combo = QComboBox()
        col_select.addWidget(self.column_combo, 1)
        column_layout.addLayout(col_select)

        col_actions = QHBoxLayout()
        col_actions.setSpacing(8)
        self.inspect_column_button = QPushButton("Inspect")
        self.diagnose_column_button = QPushButton("Diagnose")
        self.dry_run_button = QPushButton("Dry-Run Trial")
        self.one_trial_button = QPushButton("One Trial")
        self.assist_button = QPushButton("Assist Loop")
        self.assist_button.setObjectName("assistBtn")
        self.assist_button.setStyleSheet(
            "QPushButton#assistBtn { background: #238636; border: 1px solid #2ea043; }"
            "QPushButton#assistBtn:hover { background: #2ea043; }"
        )
        for button in (
            self.inspect_column_button,
            self.diagnose_column_button,
            self.dry_run_button,
            self.one_trial_button,
            self.assist_button,
        ):
            col_actions.addWidget(button)
        col_actions.addStretch()
        column_layout.addLayout(col_actions)

        # Clear status chips instead of one cramped line
        chips = QHBoxLayout()
        chips.setSpacing(8)
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

        self.column_summary = QLabel(
            "How to use: Connect → choose column → Inspect.\n"
            "Diagnose explains the problem. Dry-Run shows the planned change. "
            "One Trial / Assist Loop run keep-or-reverse trials in HYSYS."
        )
        self.column_summary.setWordWrap(True)
        self.column_summary.setStyleSheet(
            "color: #8b949e; padding: 10px; background: #161b22; "
            "border: 1px solid #30363d; border-radius: 6px;"
        )
        column_layout.addWidget(self.column_summary)

        specs_group = QGroupBox("Column specifications (from HYSYS Monitor / Specs)")
        specs_layout = QVBoxLayout(specs_group)
        specs_layout.setContentsMargins(10, 8, 10, 10)
        specs_layout.setSpacing(6)

        legend = QLabel(
            "Active Spec = used to solve (must match DOF).   "
            "Estimate only = starting guess, not a constraint.   "
            "Goal = target you set.   Current = HYSYS result.   "
            "Residual = how far Current is from Goal (near 0 is good)."
        )
        legend.setWordWrap(True)
        legend.setStyleSheet("color: #8b949e; border: none; background: transparent;")
        specs_layout.addWidget(legend)

        self.column_specs_table = QTableWidget(0, 5)
        self.column_specs_table.setHorizontalHeaderLabels(
            (
                "Specification name",
                "What it is",
                "Goal (target)",
                "Current (result)",
                "Residual (error)",
            )
        )
        self.column_specs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.column_specs_table.setAlternatingRowColors(True)
        self.column_specs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.column_specs_table.setWordWrap(True)
        self.column_specs_table.verticalHeader().setVisible(False)
        header = self.column_specs_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setMinimumHeight(36)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.column_specs_table.setMinimumHeight(180)
        specs_layout.addWidget(self.column_specs_table)
        column_layout.addWidget(specs_group, 2)

        self.column_temp_plot = pg.PlotWidget(title="Stage temperatures — Main TS (top → bottom)")
        self.column_temp_plot.setBackground("#0d1117")
        self.column_temp_plot.setLabel("left", "Temperature", units="C")
        self.column_temp_plot.setLabel("bottom", "Stage")
        self.column_temp_plot.setMinimumHeight(160)
        column_layout.addWidget(self.column_temp_plot, 1)

        log_group = QGroupBox("Assistant activity")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 6, 8, 8)
        self.column_assist_log = QTextEdit()
        self.column_assist_log.setReadOnly(True)
        self.column_assist_log.setMinimumHeight(80)
        self.column_assist_log.setMaximumHeight(120)
        log_layout.addWidget(self.column_assist_log)
        column_layout.addWidget(log_group)

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

        if state.appears_converged:
            self.chip_converged.set_value("Converged", "#3fb950")
        else:
            self.chip_converged.set_value("Not converged", "#f0883e")

        self.chip_error.set_value(f"{state.max_active_spec_error:.3g}")

        if diagnosis is not None:
            detail = diagnosis.summary
            if diagnosis.details:
                detail += "\n• " + "\n• ".join(diagnosis.details)
            self.column_summary.setText(f"{diagnosis.severity.upper()}: {detail}")
            color = {"info": "#3fb950", "warn": "#f0883e", "critical": "#f85149"}.get(
                diagnosis.severity, "#8b949e"
            )
            self.column_summary.setStyleSheet(
                f"color: {color}; padding: 10px; background: #161b22; "
                "border: 1px solid #30363d; border-radius: 6px;"
            )
        else:
            self.column_summary.setText(
                f"{state.name} ({state.flowsheet_tag})  ·  score {score_state(state):.4g}\n"
                "Active specs drive the solve. Inactive rows are estimates only."
            )
            self.column_summary.setStyleSheet(
                "color: #8b949e; padding: 10px; background: #161b22; "
                "border: 1px solid #30363d; border-radius: 6px;"
            )

        self.column_specs_table.setRowCount(len(state.specs))
        for row, spec in enumerate(state.specs):
            if spec.is_active:
                what = "Active spec (used to solve)"
            else:
                what = "Estimate only (not a constraint)"

            if spec.error is None:
                residual = "—"
            elif abs(spec.error) >= 1e4:
                residual = "n/a (inactive)"
            else:
                residual = f"{spec.error:.4g}"

            values = (
                spec.name,
                what,
                "—" if spec.goal_value is None else f"{spec.goal_value:.6g}",
                "—" if spec.current_value is None else f"{spec.current_value:.6g}",
                residual,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 1 and spec.is_active:
                    item.setForeground(QColor("#3fb950"))
                elif column == 1:
                    item.setForeground(QColor("#8b949e"))
                self.column_specs_table.setItem(row, column, item)
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

    def inspect_column(self) -> None:
        try:
            state = self.assistant.inspect(self._selected_column())
            self._show_column_state(state)
            self._column_assist_log(f"Inspected {state.name}: DOF={state.degrees_of_freedom}")
        except Exception as exc:
            self._show_error(exc)

    def diagnose_column(self) -> None:
        try:
            state, diagnosis = self.assistant.diagnose_column(self._selected_column())
            self._show_column_state(state, diagnosis)
            self._column_assist_log(
                f"Diagnosis [{diagnosis.recommended_strategy}]: {diagnosis.summary}"
            )
        except Exception as exc:
            self._show_error(exc)

    def run_column_trial(self, dry_run: bool = True) -> None:
        try:
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
                self._show_column_state(result.after_state, diagnose(result.after_state))
            self._column_assist_log(result.message)
        except Exception as exc:
            self._show_error(exc)

    def run_assist_loop(self) -> None:
        try:
            name = self._selected_column()
            answer = QMessageBox.question(
                self,
                "Column Assistant",
                (
                    "Run the automatic assist loop?\n\n"
                    "Sequence: diagnose → one bounded change → solve → keep/reverse → repeat.\n"
                    "Stops when converged, DOF blocked, or no progress."
                ),
            )
            if answer != QMessageBox.Yes:
                return
            results = self.assistant.assist(name, dry_run=False)
            if results and results[-1].after_state is not None:
                self._show_column_state(results[-1].after_state, diagnose(results[-1].after_state))
            for result in results:
                self._column_assist_log(result.message)
        except Exception as exc:
            self._show_error(exc)

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
        QMessageBox.critical(self, "HYSYS Studio", str(error))

