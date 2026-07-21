"""Shared Qt table styling — Windows dark Fusion headers need explicit colors."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem


def style_table_headers(table: QTableWidget, labels: tuple[str, ...] | list[str]) -> None:
    """Force readable header text on Windows dark Fusion themes."""
    table.setHorizontalHeaderLabels(list(labels))
    header = table.horizontalHeader()
    header.setVisible(True)
    header.setMinimumHeight(40)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    header.setMinimumSectionSize(80)
    font = QFont("Segoe UI")
    font.setPointSize(11)
    font.setBold(True)
    header.setFont(font)
    header.setStyleSheet(
        "QHeaderView::section {"
        " background-color: #21262d;"
        " color: #ffffff;"
        " padding: 12px 10px;"
        " border: none;"
        " border-right: 1px solid #30363d;"
        " border-bottom: 2px solid #58a6ff;"
        " font-size: 13px;"
        " font-weight: 700;"
        "}"
    )
    for index, text in enumerate(labels):
        item = table.horizontalHeaderItem(index)
        if item is None:
            item = QTableWidgetItem(text)
            table.setHorizontalHeaderItem(index, item)
        item.setText(text)
        item.setForeground(QColor("#ffffff"))
