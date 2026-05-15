from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui_ingest.ingest_window import IngestWindow
from ui_query.query_window import QueryWindow


class EntryWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ADE 统一入口")
        self.resize(720, 320)

        self.next_window: QMainWindow | None = None

        title = QLabel("请选择要进入的模块")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1f2a37;")

        self.ingest_button = QPushButton("进入数据导入模块")
        self.query_button = QPushButton("进入数据查询模块")
        self.ingest_button.setMinimumHeight(64)
        self.query_button.setMinimumHeight(64)
        self.ingest_button.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.query_button.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.ingest_button.clicked.connect(self.open_ingest)
        self.query_button.clicked.connect(self.open_query)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(self.ingest_button)
        layout.addWidget(self.query_button)
        layout.addStretch(1)
        self.setCentralWidget(root)

    def open_ingest(self) -> None:
        self.next_window = IngestWindow(on_back_to_main=self.show)
        self.next_window.show()
        self.hide()

    def open_query(self) -> None:
        self.next_window = QueryWindow(on_back_to_main=self.show)
        self.next_window.show()
        self.hide()



def main() -> int:
    app = QApplication(sys.argv)
    window = EntryWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
