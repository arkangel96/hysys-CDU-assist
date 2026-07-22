"""
Separate PE Intelligence window for Simple Column Assist v1 — New Intelligence.
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
    stripper_priority_add_types,
)
from ui_style import style_table_headers


CODED_CHECKLIST = """
SIMPLE COLUMN ASSIST v1 — New Intelligence (what's coded)
---------------------------------
Canonical inventory: docs/INTELLIGENCE_INVENTORY_V1.md
Scope: simple distillation / stripping only (NOT CDU/VDU).

LAYER 1
[x] Read Specs table (Active, Goal, Current, Error)
[x] Set Active / GoalValue / 1-for-1 Active swap
[x] Snapshot keep/reverse trials
[x] Trial Map path / strategy board

LAYER 2+ (2026-07-22 multi-variable integration)
[x] States A–F (State F with flat/exhausted-family evidence)
[x] FINAL_TARGET lock (NH3) — plant default 50 ppmw
[x] Keep/reverse on FINAL_TARGET + operability (not score alone)
[x] Multi-family chooser: A_init / B_energy / C_split (not RR-only)
[x] HYSYS popup clues: detect + log + feed into PE board; auto-OK so multi-run continues
[x] PE board shows family + hypothesis
[x] Stream product NH3 + worksheet kgmole/h
[x] Estimates refresh (COM)
[x] Bottoms/duty/T operability gates
[x] Connections READ + Specs Summary APPLY / click tips
[x] Connections STRUCTURAL intelligence (Family F) — recommend + approval-gated write
[x] Simple optimize — min RR / RebQ / CondQ / stages (product locked; thin layer)
[x] Multi-variable families A_init / B_energy / C_split (not RR-only)
[x] Add Spec catalog (recommend only — no auto Add)

PARTIAL / NEXT
[ ] Condenser-aware Active policy beyond NH3→Ovhd recipe
[ ] Optional H2S FINAL_TARGET table entry
[ ] Learning/memory from new_intelligence (held)

NOT CODED YET (by design)
-------------------------
[ ] Auto HYSYS "Add Spec" via Specs.Add
[ ] Auto feed stage / stage count / pressure
[ ] Auto-save .hsc
[ ] Full 2x2 multivariable solver
[ ] Hydraulic flooding validation
[ ] CDU / VDU tools (separate products)

DOCS (repo)
-----------
docs/INTELLIGENCE_INVENTORY_V1.md
docs/MULTI_VARIABLE_ITERATION_MAP.md
new_intelligence/00_COMPLEMENTARY_INTRO.md
docs/SCOPE_SIMPLE_COLUMN_ASSIST.md
docs/expert_decision_workflow.md
docs/column_convergence_playbook.md
docs/intelligence_improvement_notes.md
docs/hysys_add_spec_catalog.md
"""


class IntelligenceWindow(QMainWindow):
    def __init__(self, assistant: ConvergenceAssistant, parent=None) -> None:
        super().__init__(parent)
        self.assistant = assistant
        self.column_name = "SW Stripper"
        self.setWindowTitle("PE Intelligence — Simple Column Assist v1")
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
            "Simple Column Assist v1 — New Intelligence only (not CDU/VDU). "
            "Add Spec actions are recommendations — does not auto-create specs yet. "
            "See docs/SCOPE_SIMPLE_COLUMN_ASSIST.md"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b949e;")
        layout.addWidget(hint)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # Tab 1 — live PE board
        board_tab = QWidget()
        board_layout = QVBoxLayout(board_tab)
        self.board_text = QTextEdit()
        self.board_text.setReadOnly(True)
        self.board_text.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 12px;"
        )
        board_layout.addWidget(self.board_text)
        tabs.addTab(board_tab, "Live PE Board")

        # Tab 2 — Add Spec catalog
        catalog_tab = QWidget()
        catalog_layout = QVBoxLayout(catalog_tab)
        self.catalog_table = QTableWidget(0, 5)
        style_table_headers(
            self.catalog_table,
            ("HYSYS Add Spec type", "Family", "Policy", "When to add", "SW Stripper?"),
        )
        self.catalog_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.horizontalHeader().setStretchLastSection(True)
        catalog_layout.addWidget(self.catalog_table)
        priority = QLabel(
            "Stripper priority types: "
            + ", ".join(s.hysys_name for s in stripper_priority_add_types()[:6])
            + ", …"
        )
        priority.setWordWrap(True)
        priority.setStyleSheet("color: #8b949e;")
        catalog_layout.addWidget(priority)
        tabs.addTab(catalog_tab, "Add Spec Catalog")

        # Tab 3 — what's coded
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
                "Yes" if spec.typical_for_sw_stripper else "—",
            )
            for col, value in enumerate(values):
                self.catalog_table.setItem(row, col, QTableWidgetItem(value))
            if spec.policy == AddPolicy.NOT_FOR_STRIPPER:
                for col in range(5):
                    item = self.catalog_table.item(row, col)
                    if item is not None:
                        item.setForeground(Qt.gray)

    def refresh(self, column_name: str | None = None) -> None:
        if column_name:
            self.column_name = column_name
        name = self.column_name or "SW Stripper"
        self.title.setText(f"PE Intelligence — {name}")
        try:
            if not self.assistant.columns.hysys.connected:
                self.board_text.setPlainText(
                    "Not connected to HYSYS.\nConnect in Studio, then Refresh."
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
