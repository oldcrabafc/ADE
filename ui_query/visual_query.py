from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget


class VisualQueryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.ac_name_edit = QLineEdit()
        self.voucher_no_edit = QLineEdit()
        self.summary_edit = QLineEdit()
        self.min_amount_edit = QLineEdit()
        self.date_from_edit = QLineEdit()
        self.date_to_edit = QLineEdit()
        self.build_button = QPushButton("生成 SQL")
        self.date_from_edit.setPlaceholderText("YYYY-MM-DD")
        self.date_to_edit.setPlaceholderText("YYYY-MM-DD")

        layout = QFormLayout(self)
        layout.addRow("科目名称", self.ac_name_edit)
        layout.addRow("凭证号", self.voucher_no_edit)
        layout.addRow("摘要关键词", self.summary_edit)
        layout.addRow("最小金额", self.min_amount_edit)
        layout.addRow("开始日期", self.date_from_edit)
        layout.addRow("结束日期", self.date_to_edit)

        actions = QHBoxLayout()
        actions.addWidget(self.build_button)
        layout.addRow(actions)

    def filters(self) -> dict[str, str]:
        return {
            "ac_name": self.ac_name_edit.text(),
            "voucher_no": self.voucher_no_edit.text(),
            "summary": self.summary_edit.text(),
            "min_amount": self.min_amount_edit.text(),
            "date_from": self.date_from_edit.text().strip(),
            "date_to": self.date_to_edit.text().strip(),
        }
