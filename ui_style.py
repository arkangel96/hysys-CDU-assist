"""Shared Qt table styling — compact Aspen-like density on Windows dark Fusion."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem


def style_table_headers(table: QTableWidget, labels: tuple[str, ...] | list[str]) -> None:
    """Force readable header text on Windows dark Fusion themes."""
    table.setHorizontalHeaderLabels(list(labels))
    header = table.horizontalHeader()
    header.setVisible(True)
    header.setMinimumHeight(24)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    header.setMinimumSectionSize(56)
    font = QFont("Segoe UI")
    font.setPointSize(8)
    font.setBold(True)
    header.setFont(font)
    header.setStyleSheet(
        "QHeaderView::section {"
        " background-color: #21262d;"
        " color: #ffffff;"
        " padding: 4px 6px;"
        " border: none;"
        " border-right: 1px solid #30363d;"
        " border-bottom: 1px solid #58a6ff;"
        " font-size: 8pt;"
        " font-weight: 700;"
        "}"
    )
    table.setFont(QFont("Segoe UI", 8))
    table.verticalHeader().setDefaultSectionSize(22)
    for index, text in enumerate(labels):
        item = table.horizontalHeaderItem(index)
        if item is None:
            item = QTableWidgetItem(text)
            table.setHorizontalHeaderItem(index, item)
        item.setText(text)
        item.setForeground(QColor("#ffffff"))
