from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
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
        self.resize(520, 220)

        self.next_window: QMainWindow | None = None

        self.module_combo = QComboBox()
        self.module_combo.addItem("导入模块", "ingest")
        self.module_combo.addItem("查询模块", "query")

        self.next_button = QPushButton("下一步")
        self.next_button.clicked.connect(self.on_next)

        title = QLabel("请选择下一步进入的模块")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1f2a37;")

        row = QHBoxLayout()
        row.addWidget(QLabel("模块"))
        row.addWidget(self.module_combo)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(title)
        layout.addLayout(row)
        layout.addStretch(1)
        layout.addWidget(self.next_button)
        self.setCentralWidget(root)

    def on_next(self) -> None:
        choice = self.module_combo.currentData()
        if choice == "ingest":
            self.next_window = IngestWindow(on_back_to_main=self.show)
        elif choice == "query":
            self.next_window = QueryWindow(on_back_to_main=self.show)
        else:
            QMessageBox.warning(self, "选择无效", "请选择有效模块。")
            return

        self.next_window.show()
        self.hide()



def main() -> int:
    app = QApplication(sys.argv)
    window = EntryWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
