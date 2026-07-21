"""
Separate PE Intelligence window for CDU Assist.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from column_engine import ConvergenceAssistant, format_pe_board
from column_spec_catalog import (
    HYSYS_ADD_SPEC_TYPES,
    AddPolicy,
    cdu_priority_add_types,
)
from ui_style import style_table_headers


CODED_CHECKLIST = """
CDU ASSIST — what's coded (Layer 2 platform)
---------------------------------
Scope: atmospheric crude distillation (NOT simple stripper; NOT VDU).
See docs/SCOPE_CDU_ASSIST.md

[x] Read Specs table (Active, Goal, Current, Error)
[x] Set Active / GoalValue / 1-for-1 Active swap
[x] States A–F classification shell
[x] FINAL_TARGET lock layer (cuts / ASTM / TBP — configure per case)
[x] PE board + response classes (KEPT/REVERSED)
[x] Estimates refresh (COM)
[x] Add Spec catalog + when-to-add recommendations
[x] Trial Map path / CDU strategy board
[x] Expert process flow + hypothesis ranking (cdu_expert_engine)
[x] Hypothesis-driven experiment selection (State C/B)
[x] Connections READ + Specs worksheet-style display
[x] Specs Summary Active/Estimate APPLY + recommended clicks

NOT CODED YET (by design / Phase 1+)
-------------------------
[ ] Live COM discovery of draws / PAs / side strippers / cut specs
[x] Phase 2 scaffold: config/cdu_t100_case.json (objectives, targets, spec roles)
[x] Product quality state board (placeholders until targets filled)
[x] Spec philosophy audit (DOF, PA/OH conflicts)
[ ] CDU product-quality COM reads (D86 / flash — needs HYSYS path)
[ ] Auto HYSYS "Add Spec" via Specs.Add (recommend only for now)
[ ] Change column pressure automatically
[ ] Change number of stages / feed stage / PA location automatically
[ ] Parameters / Solver pages
[ ] Full multivariable solver
[ ] Hydraulic flooding validation
[ ] VDU Assist (separate product)

DOCS (repo)
-----------
docs/SCOPE_CDU_ASSIST.md
docs/expert_decision_workflow.md
docs/cdu_convergence_playbook.md
docs/intelligence_improvement_notes.md
docs/hysys_add_spec_catalog.md
"""


class IntelligenceWindow(QMainWindow):
    def __init__(self, assistant: ConvergenceAssistant, parent=None) -> None:
        super().__init__(parent)
        self.assistant = assistant
        self.column_name = ""
        self.setWindowTitle("PE Intelligence — CDU Assist")
        self.resize(1100, 720)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self.title = QLabel("PE Intelligence")
        self.title.setStyleSheet("font-size: 16px; font-weight: 600;")
        top.addWidget(self.title)
        top.addStretch()
        self.refresh_btn = QPushButton("Refresh from HYSYS")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)

        hint = QLabel(
            "CDU Assist — atmospheric crude tower. "
            "Add Spec actions are recommendations — does not auto-create specs yet. "
            "See docs/SCOPE_CDU_ASSIST.md"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b949e;")
        layout.addWidget(hint)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        board_tab = QWidget()
        board_layout = QVBoxLayout(board_tab)
        self.board_text = QTextEdit()
        self.board_text.setReadOnly(True)
        self.board_text.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 12px;"
        )
        board_layout.addWidget(self.board_text)
        tabs.addTab(board_tab, "Live PE Board")

        catalog_tab = QWidget()
        catalog_layout = QVBoxLayout(catalog_tab)
        self.catalog_table = QTableWidget(0, 5)
        style_table_headers(
            self.catalog_table,
            ("HYSYS Add Spec type", "Family", "Policy", "When to add", "Typical CDU?"),
        )
        self.catalog_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.horizontalHeader().setStretchLastSection(True)
        catalog_layout.addWidget(self.catalog_table)
        priority = QLabel(
            "CDU priority types: "
            + ", ".join(s.hysys_name for s in cdu_priority_add_types()[:6])
            + ", …"
        )
        priority.setWordWrap(True)
        priority.setStyleSheet("color: #8b949e;")
        catalog_layout.addWidget(priority)
        tabs.addTab(catalog_tab, "Add Spec Catalog")

        coded_tab = QWidget()
        coded_layout = QVBoxLayout(coded_tab)
        self.coded_text = QTextEdit()
        self.coded_text.setReadOnly(True)
        self.coded_text.setPlainText(CODED_CHECKLIST.strip())
        self.coded_text.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 12px;"
        )
        coded_layout.addWidget(self.coded_text)
        tabs.addTab(coded_tab, "What's Coded")

        self._fill_catalog()

    def _fill_catalog(self) -> None:
        self.catalog_table.setRowCount(len(HYSYS_ADD_SPEC_TYPES))
        for row, spec in enumerate(HYSYS_ADD_SPEC_TYPES):
            values = (
                spec.hysys_name,
                spec.family.value,
                spec.policy.value,
                spec.when_to_add,
                "Yes" if spec.typical_for_cdu else "—",
            )
            for col, value in enumerate(values):
                self.catalog_table.setItem(row, col, QTableWidgetItem(value))
            if spec.policy == AddPolicy.NOT_FOR_CDU:
                for col in range(5):
                    item = self.catalog_table.item(row, col)
                    if item is not None:
                        item.setForeground(Qt.gray)

    def refresh(self, column_name: str | None = None) -> None:
        if column_name:
            self.column_name = column_name
        name = self.column_name.strip()
        if not name:
            self.board_text.setPlainText(
                "Select a column in CDU Assist, then Refresh."
            )
            return
        self.title.setText(f"PE Intelligence — {name}")
        try:
            if not self.assistant.columns.hysys.connected:
                self.board_text.setPlainText(
                    "Not connected to HYSYS.\nConnect in CDU Assist, then Refresh."
                )
                return
            state, diagnosis = self.assistant.diagnose_column(name)
            text = format_pe_board(state, diagnosis)
            text += "\n\n--- FINAL_TARGET detail ---\n"
            for tid, info in diagnosis.final_target_status.items():
                text += (
                    f"{tid}: measured={info['measured']} target={info['target']} "
                    f"met={info['met']} locked={info['locked']}\n"
                )
            self.board_text.setPlainText(text)
        except Exception as exc:
            self.board_text.setPlainText(f"Could not refresh intelligence:\n{exc}")
