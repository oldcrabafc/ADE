from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableView, QVBoxLayout, QWidget

from shared.schema import QueryResult


class QueryResultTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._columns: list[str] = []
        self._rows: list[tuple[Any, ...]] = []
        self._row_offset = 0

    def set_page(self, columns: list[str], rows: list[tuple[Any, ...]], row_offset: int) -> None:
        self.beginResetModel()
        self._columns = list(columns)
        self._rows = list(rows)
        self._row_offset = row_offset
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        value = self._rows[index.row()][index.column()]
        return "" if value is None else str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._columns[section] if section < len(self._columns) else ""
        return str(self._row_offset + section + 1)


class TableViewer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._result = QueryResult(columns=[], rows=[])
        self._filtered_rows: list[tuple[Any, ...]] = []
        self._page_index = 0
        self._sort_column: int | None = None
        self._sort_order = Qt.SortOrder.AscendingOrder

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("结果内筛选")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500", "全部"])
        self.prev_button = QPushButton("上一页")
        self.next_button = QPushButton("下一页")
        self.page_label = QLabel("0 / 0")
        self.row_count_label = QLabel("0 行")

        self.table = QTableView()
        self._model = QueryResultTableModel()
        self.table.setModel(self._model)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().sectionClicked.connect(self.on_sort_column)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("筛选"))
        controls.addWidget(self.filter_edit)
        controls.addWidget(QLabel("每页"))
        controls.addWidget(self.page_size_combo)
        controls.addWidget(self.prev_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.page_label)
        controls.addWidget(self.row_count_label)

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.table)

        self.filter_edit.textChanged.connect(self.on_filter_changed)
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        self.prev_button.clicked.connect(self.on_prev_page)
        self.next_button.clicked.connect(self.on_next_page)
        self._refresh_view()

    def set_result(self, result: QueryResult) -> None:
        self._result = QueryResult(columns=list(result.columns), rows=list(result.rows))
        self._page_index = 0
        self._sort_column = None
        self._apply_filter_and_sort()
        self._refresh_view()
        self.table.resizeColumnsToContents()

    def set_dataframe(self, result: QueryResult) -> None:
        self.set_result(result)

    def on_filter_changed(self) -> None:
        self._page_index = 0
        self._apply_filter_and_sort()
        self._refresh_view()

    def on_page_size_changed(self) -> None:
        self._page_index = 0
        self._refresh_view()

    def on_prev_page(self) -> None:
        if self._page_index > 0:
            self._page_index -= 1
            self._refresh_view()

    def on_next_page(self) -> None:
        if self._page_index + 1 < self._page_count():
            self._page_index += 1
            self._refresh_view()

    def on_sort_column(self, column: int) -> None:
        if self._sort_column == column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        self._page_index = 0
        self._apply_filter_and_sort()
        self._refresh_view()

    def _apply_filter_and_sort(self) -> None:
        needle = self.filter_edit.text().strip().casefold()
        if needle:
            self._filtered_rows = [
                row
                for row in self._result.rows
                if needle in " ".join("" if value is None else str(value) for value in row).casefold()
            ]
        else:
            self._filtered_rows = list(self._result.rows)

        if self._sort_column is not None:
            column = self._sort_column
            reverse = self._sort_order == Qt.SortOrder.DescendingOrder
            self._filtered_rows.sort(key=lambda row: _sort_key(row[column] if column < len(row) else None), reverse=reverse)

    def _refresh_view(self) -> None:
        page_size = self._page_size()
        total_rows = len(self._filtered_rows)
        page_count = self._page_count()
        if page_count == 0:
            self._page_index = 0
        else:
            self._page_index = min(self._page_index, page_count - 1)

        if page_size is None:
            start = 0
            end = total_rows
        else:
            start = self._page_index * page_size
            end = min(start + page_size, total_rows)

        self._model.set_page(self._result.columns, self._filtered_rows[start:end], start)
        current_page = 0 if total_rows == 0 else self._page_index + 1
        self.page_label.setText(f"{current_page} / {page_count}")
        source_total = len(self._result.rows)
        if total_rows == source_total:
            self.row_count_label.setText(f"{total_rows} 行")
        else:
            self.row_count_label.setText(f"{total_rows} / {source_total} 行")
        self.prev_button.setEnabled(self._page_index > 0)
        self.next_button.setEnabled(self._page_index + 1 < page_count)

    def _page_size(self) -> int | None:
        text = self.page_size_combo.currentText()
        if text == "全部":
            return None
        return max(1, int(text))

    def _page_count(self) -> int:
        total_rows = len(self._filtered_rows)
        if total_rows == 0:
            return 0
        page_size = self._page_size()
        if page_size is None:
            return 1
        return (total_rows + page_size - 1) // page_size


def _sort_key(value: Any) -> tuple[int, Any]:
    if value is None:
        return (1, "")
    if isinstance(value, (int, float, Decimal)):
        return (0, value)
    return (0, str(value).casefold())
