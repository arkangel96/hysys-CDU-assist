"""
Separate PE Intelligence window for CDU Assist v1 — New Intelligence.
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
CDU ASSIST v1 — New Intelligence (what's coded)
---------------------------------
Canonical inventory: docs/INTELLIGENCE_INVENTORY_V1.md
Scope: CDU / atmospheric crude distillation (not simple column / VDU).
Complementary: cdu_intel/ + docs/CDU_INTEL_COMPLEMENTARY.md

LAYER 1
[x] Read Specs table (Active, Goal, Current, Error)
[x] Set Active / GoalValue / 1-for-1 Active swap
[x] Snapshot keep/reverse trials
[x] Trial Map path / strategy board

LAYER 2+ (2026-07-22 multi-variable integration)
[x] States A–F (State F with flat/exhausted-family evidence)
[x] FINAL_TARGET lock — plant targets from cdu_final_targets.json (empty until configured)
[x] Keep/reverse on FINAL_TARGET + operability (not score alone)
[x] Multi-family chooser: A_init / B_energy / C_split / C2_steam (+ PA/draw strategies)
[x] HYSYS popup clues: detect + log + feed into PE board; auto-OK so multi-run continues
[x] PE board shows family + hypothesis + complementary cdu_intel D1/D6/D8 cues
[x] Stream product checks + HYSYS worksheet units (copied from case)
[x] Estimates refresh (COM)
[x] Bottoms/duty/T operability gates
[x] Subcooling READ (condenser Degrees / Subcool To — T-100 empty)
[x] Side Ops READ (strippers / PAs / side draws — T-100 shape)
[x] Rating READ (Towers / Vessels / Equipment / Pressure Drop — T-100 shape)
[x] Specs Summary READ (Active/Current/Fixed/Prim — T-100 shape)
[x] Specs page READ (list + Active/Est/Current/Fixed-Ranged/tolerances)
[x] Monitor READ (Active draws/PAs + worksheet units USGPM/Btu/hr)
[x] Connections READ (inlet/outlet table + CDU roles) + Specs Summary APPLY / click tips
[x] Connections STRUCTURAL intelligence (Family F) — recommend + approval-gated write
[x] Simple optimize — min RR / RebQ / CondQ / stages (product locked; thin layer)
[x] Multi-variable families A_init / B_energy / C_split (not RR-only)
[x] Add Spec catalog (full HYSYS types + CDU when-to-add + T-100 examples)
[x] Add Spec: HYSYS Add… steps + approval-gated COM try (no silent Add)

PARTIAL / NEXT
[ ] Condenser-aware Active policy (CDU draw/PA vs RR)
[ ] Optional H2S FINAL_TARGET table entry
[ ] Learning/memory from new_intelligence (held)

NOT CODED YET (by design / Phase 1+)
-------------------------
[ ] Auto HYSYS "Add Spec" via Specs.Add (silent) — blocked by design
[ ] Auto feed stage / stage count / pressure
[ ] Auto-save .hsc
[ ] Full 2x2 multivariable solver
[ ] Hydraulic flooding validation
[ ] VDU Assist (separate product)

DOCS (repo)
-----------
docs/INTELLIGENCE_INVENTORY_V1.md
docs/MULTI_VARIABLE_ITERATION_MAP.md
new_intelligence/00_COMPLEMENTARY_INTRO.md
docs/SCOPE_SIMPLE_COLUMN_ASSIST.md
docs/expert_decision_workflow.md
docs/cdu_convergence_playbook.md
docs/intelligence_improvement_notes.md
docs/hysys_add_spec_catalog.md
"""


class IntelligenceWindow(QMainWindow):
    def __init__(self, assistant: ConvergenceAssistant, parent=None) -> None:
        super().__init__(parent)
        self.assistant = assistant
        self.column_name = "T-100"
        self.setWindowTitle("PE Intelligence — CDU Assist v1")
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
            "CDU Assist v1 — New Intelligence (atmospheric crude). "
            "Add Spec actions are recommendations — does not auto-create specs yet. "
            "See docs/SCOPE_CDU_ASSIST.md and docs/CDU_INTEL_COMPLEMENTARY.md"
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

        # Tab 2 — Add Spec catalog (HYSYS Add Specs - T-100 types)
        catalog_tab = QWidget()
        catalog_layout = QVBoxLayout(catalog_tab)
        self.catalog_table = QTableWidget(0, 6)
        style_table_headers(
            self.catalog_table,
            (
                "HYSYS Add Spec type",
                "Family",
                "Policy",
                "When to add (CDU)",
                "CDU?",
                "T-100 example",
            ),
        )
        self.catalog_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.setWordWrap(True)
        self.catalog_table.horizontalHeader().setStretchLastSection(True)
        catalog_layout.addWidget(self.catalog_table)
        priority = QLabel(
            "CDU priority Add types (T-100): "
            + ", ".join(s.hysys_name for s in cdu_priority_add_types()[:8])
            + ", …  |  Source: HYSYS Add Specs dialog — recommend only, no auto Add."
        )
        priority.setWordWrap(True)
        priority.setStyleSheet("color: #8b949e;")
        catalog_layout.addWidget(priority)
        pe_hint = QLabel(
            "Tip: open HYSYS Design → Monitor → Add Spec… to see the same type list. "
            "Assist maps existing Monitor names (PA_*, Kero_SS Prod Flow, …) to these types."
        )
        pe_hint.setWordWrap(True)
        pe_hint.setStyleSheet("color: #8b949e; font-size: 8pt;")
        catalog_layout.addWidget(pe_hint)
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
                spec.t100_example or "—",
            )
            for col, value in enumerate(values):
                self.catalog_table.setItem(row, col, QTableWidgetItem(value))
            if spec.policy == AddPolicy.RARE:
                for col in range(6):
                    item = self.catalog_table.item(row, col)
                    if item is not None:
                        item.setForeground(Qt.gray)
            self.catalog_table.setRowHeight(row, 36)

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
            text = format_pe_board(state, diagnosis, columns=self.assistant.columns)
            text += "\n\n--- FINAL_TARGET detail ---\n"
            for tid, info in diagnosis.final_target_status.items():
                text += (
                    f"{tid}: measured={info['measured']} target={info['target']} "
                    f"met={info['met']} locked={info['locked']}\n"
                )
            self.board_text.setPlainText(text)
        except Exception as exc:
            self.board_text.setPlainText(f"Could not refresh intelligence:\n{exc}")
