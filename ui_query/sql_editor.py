from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidget


class SqlEditorWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.template_combo = QComboBox()
        self.apply_template_button = QPushButton("插入模板")
        self.history_combo = QComboBox()
        self.apply_history_button = QPushButton("载入历史")
        self.editor = QTextEdit()
        self.run_button = QPushButton("执行 SQL")

        layout = QVBoxLayout(self)
        template_row = QHBoxLayout()
        template_row.addWidget(self.template_combo)
        template_row.addWidget(self.apply_template_button)
        layout.addLayout(template_row)

        history_row = QHBoxLayout()
        history_row.addWidget(self.history_combo)
        history_row.addWidget(self.apply_history_button)
        layout.addLayout(history_row)

        layout.addWidget(self.editor)
        layout.addWidget(self.run_button)

    def sql_text(self) -> str:
        return self.editor.toPlainText().strip()

    def set_sql_text(self, sql_text: str) -> None:
        self.editor.setPlainText(sql_text)

    def set_templates(self, templates: dict[str, str]) -> None:
        self.template_combo.clear()
        for name, sql_text in templates.items():
            self.template_combo.addItem(name, sql_text)

    def set_history(self, entries: list[dict[str, str]]) -> None:
        self.history_combo.clear()
        for entry in entries:
            sql_text = entry.get("sql_text", "")
            if not sql_text.strip():
                continue
            label = _history_label(entry)
            self.history_combo.addItem(label, sql_text)

    def selected_template_sql(self) -> str:
        return str(self.template_combo.currentData() or "")

    def selected_history_sql(self) -> str:
        return str(self.history_combo.currentData() or "")


def _history_label(entry: dict[str, str]) -> str:
    executed_at = entry.get("executed_at", "")
    first_line = entry.get("sql_text", "").strip().splitlines()[0] if entry.get("sql_text", "").strip() else ""
    if len(first_line) > 80:
        first_line = first_line[:77] + "..."
    return f"{executed_at}  {first_line}".strip()
