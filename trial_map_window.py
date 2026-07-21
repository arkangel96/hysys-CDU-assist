"""Separate Trial Map window: path trail + remaining combinations board."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from column_engine import ConvergenceAssistant
from trial_map import StrategyStatus, TrialMapSnapshot, build_trial_map
from ui_style import style_table_headers


MAP_STYLE = """
QMainWindow, QWidget#TrialMapCentral {
  background: #0d1117;
  color: #c9d1d9;
}
QLabel { color: #c9d1d9; background: transparent; border: none; }
QPushButton {
  background: #21262d;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 8px 14px;
  color: #c9d1d9;
  font-size: 13px;
  min-height: 28px;
}
QPushButton:hover { background: #30363d; }
QPushButton#maxBtn {
  background: #1f6feb;
  border: 1px solid #388bfd;
}
QPushButton#maxBtn:hover { background: #388bfd; }
QTableWidget {
  background: #161b22;
  alternate-background-color: #1c2128;
  border: 1px solid #30363d;
  gridline-color: #30363d;
  color: #c9d1d9;
  font-size: 13px;
  selection-background-color: #1f6feb;
}
QHeaderView::section {
  background-color: #21262d;
  color: #ffffff;
  padding: 12px 10px;
  border: none;
  border-right: 1px solid #30363d;
  border-bottom: 2px solid #58a6ff;
  font-size: 13px;
  font-weight: 700;
  min-height: 36px;
}
QTextEdit {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 8px;
  color: #c9d1d9;
  font-size: 13px;
}
"""

STATUS_COLORS = {
    StrategyStatus.OPEN: "#8b949e",
    StrategyStatus.HELPED: "#3fb950",
    StrategyStatus.FAILED: "#f85149",
    StrategyStatus.NEXT: "#58a6ff",
    StrategyStatus.LOCKED: "#f0883e",
    StrategyStatus.DONE_OK: "#3fb950",
}


def _setup_table_header(table: QTableWidget, labels: tuple[str, ...]) -> None:
    table.setColumnCount(len(labels))
    style_table_headers(table, labels)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setMinimumSectionSize(90)


class TrialMapWindow(QMainWindow):
    """Independent window so it can maximize on the monitor."""

    def __init__(self, assistant: ConvergenceAssistant, parent=None) -> None:
        super().__init__(None)  # no parent -> avoid Studio stylesheet hiding headers
        self.assistant = assistant
        self.column_name = ""
        self.setWindowTitle("Trial Map - iteration path and remaining combinations")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 860)
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.setStyleSheet(MAP_STYLE)
        self._board_rows: list = []
        self._build()

    def _build(self) -> None:
        central = QWidget()
        central.setObjectName("TrialMapCentral")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("TRIAL MAP")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #58a6ff;")
        top.addWidget(title)
        top.addStretch()
        self.maximize_button = QPushButton("Fill Monitor")
        self.maximize_button.setObjectName("maxBtn")
        self.maximize_button.clicked.connect(self.showMaximized)
        self.restore_button = QPushButton("Restore Size")
        self.restore_button.clicked.connect(self.showNormal)
        top.addWidget(self.maximize_button)
        top.addWidget(self.restore_button)
        root.addLayout(top)

        self.here_label = QLabel("You are here: -")
        self.here_label.setWordWrap(True)
        self.here_label.setStyleSheet(
            "padding: 12px; background: #161b22; border: 1px solid #30363d; "
            "border-radius: 6px; font-size: 13px;"
        )
        root.addWidget(self.here_label)

        self.next_label = QLabel("Next suggested: -")
        self.next_label.setWordWrap(True)
        self.next_label.setStyleSheet(
            "padding: 12px; background: #161b22; border: 1px solid #1f6feb; "
            "border-radius: 6px; color: #58a6ff; font-weight: 600; font-size: 13px;"
        )
        root.addWidget(self.next_label)

        path_caption = QLabel("1) PATH - where I have been")
        path_caption.setStyleSheet("font-size: 14px; font-weight: 700; color: #f0883e;")
        root.addWidget(path_caption)

        self.path_strip = QLabel("Start -> YOU ARE HERE")
        self.path_strip.setWordWrap(True)
        self.path_strip.setStyleSheet(
            "padding: 14px; background: #0d1117; border: 1px dashed #30363d; "
            "border-radius: 6px; color: #f0883e; font-size: 13px;"
        )
        root.addWidget(self.path_strip)

        trail_caption = QLabel("Trial history table")
        trail_caption.setStyleSheet("font-size: 12px; color: #8b949e;")
        root.addWidget(trail_caption)

        self.trail_table = QTableWidget()
        _setup_table_header(
            self.trail_table,
            ("#", "Strategy", "What changed", "Outcome", "Scores"),
        )
        self.trail_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trail_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trail_table.setAlternatingRowColors(True)
        self.trail_table.verticalHeader().setVisible(False)
        th = self.trail_table.horizontalHeader()
        th.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(2, QHeaderView.Stretch)
        th.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.trail_table.setMinimumHeight(160)
        self.trail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        root.addWidget(self.trail_table, 1)

        board_caption = QLabel("2) COMBINATION BOARD - remaining mix")
        board_caption.setStyleSheet("font-size: 14px; font-weight: 700; color: #58a6ff;")
        root.addWidget(board_caption)

        legend = QLabel(
            "Grey = open/not tried   |   Green = helped   |   Red = failed   |   "
            "Blue = next   |   Orange = last resort"
        )
        legend.setStyleSheet("color: #8b949e; font-size: 12px;")
        root.addWidget(legend)

        self.board_table = QTableWidget()
        _setup_table_header(
            self.board_table,
            ("Family", "Combination / strategy", "Status", "Meaning"),
        )
        self.board_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.board_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.board_table.setAlternatingRowColors(True)
        self.board_table.verticalHeader().setVisible(False)
        self.board_table.itemSelectionChanged.connect(self._on_board_select)
        bh = self.board_table.horizontalHeader()
        bh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        bh.setSectionResizeMode(1, QHeaderView.Stretch)
        bh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        bh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.board_table.setMinimumHeight(260)
        self.board_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.board_table, 2)

        detail_caption = QLabel("Detail (click a combination row)")
        detail_caption.setStyleSheet("font-size: 12px; color: #8b949e;")
        root.addWidget(detail_caption)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(90)
        self.detail.setMaximumHeight(140)
        self.detail.setPlaceholderText("Select a combination row to see what it means.")
        root.addWidget(self.detail)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Map")
        self.refresh_button.clicked.connect(lambda: self.refresh(self.column_name))
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        root.addLayout(buttons)

    def refresh(self, column_name: str) -> None:
        self.column_name = column_name or self.column_name or "Column"
        state = None
        diagnosis = None
        try:
            if self.column_name and self.assistant.columns.hysys.connected:
                state, diagnosis = self.assistant.diagnose_column(self.column_name)
        except Exception as exc:
            self.here_label.setText(f"You are here: could not inspect ({exc})")
            snap = build_trial_map(self.column_name, self.assistant.history)
            self._apply(snap)
            return

        snap = build_trial_map(
            self.column_name,
            self.assistant.history,
            state=state,
            diagnosis=diagnosis,
        )
        self._apply(snap)

    def _apply(self, snap: TrialMapSnapshot) -> None:
        self.here_label.setText(f"You are here: {snap.you_are_here}")
        self.next_label.setText(f"Next suggested: {snap.next_suggested}")
        self.path_strip.setText(snap.path_text)

        if not snap.path:
            self.trail_table.setRowCount(1)
            for col in range(5):
                self.trail_table.setItem(0, col, QTableWidgetItem(""))
            empty = QTableWidgetItem("(No trials yet - run Dry-Run / One Trial / Assist Loop)")
            empty.setForeground(QColor("#8b949e"))
            self.trail_table.setItem(0, 2, empty)
        else:
            self.trail_table.setRowCount(len(snap.path))
            for row, node in enumerate(snap.path):
                if node.dry_run:
                    outcome = "Dry-run"
                    color = "#8b949e"
                elif node.kept:
                    outcome = "Kept"
                    color = "#3fb950"
                else:
                    outcome = "Reversed"
                    color = "#f85149"
                values = (
                    str(node.index),
                    node.label,
                    node.summary,
                    outcome,
                    f"{node.before_score:.3g} -> {node.after_score:.3g}",
                )
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setForeground(QColor("#c9d1d9"))
                    if col == 3:
                        item.setForeground(QColor(color))
                    self.trail_table.setItem(row, col, item)
                self.trail_table.setRowHeight(row, 30)

        self._board_rows = list(snap.board)
        self.board_table.setRowCount(len(snap.board))
        for row, board in enumerate(snap.board):
            values = (board.family, board.label, board.status_text, board.description)
            color = STATUS_COLORS.get(board.status, "#c9d1d9")
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setForeground(QColor("#c9d1d9"))
                if col in (1, 2):
                    item.setForeground(QColor(color))
                    if board.status == StrategyStatus.NEXT:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                self.board_table.setItem(row, col, item)
            self.board_table.setRowHeight(row, 34)

        _setup_table_header(
            self.trail_table,
            ("#", "Strategy", "What changed", "Outcome", "Scores"),
        )
        _setup_table_header(
            self.board_table,
            ("Family", "Combination / strategy", "Status", "Meaning"),
        )

    def _on_board_select(self) -> None:
        rows = self.board_table.selectionModel().selectedRows()
        if not rows or not self._board_rows:
            return
        board = self._board_rows[rows[0].row()]
        self.detail.setText(
            f"{board.label}\n"
            f"Family: {board.family}\n"
            f"Status: {board.status_text}\n\n"
            f"{board.description}"
        )
