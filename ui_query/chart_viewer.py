from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ChartViewer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("当前版本未实现图表中心，后续可在此接入 Plotly 图表。"))
