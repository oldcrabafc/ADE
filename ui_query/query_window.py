from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analysis.rule_service import RuleService
from dataset.manifest_service import read_manifest
from dataset.package_service import default_package_name, package_dataset
from dataset.registry_service import list_recent_dataset_summaries, register_dataset
from dataset.query_dataset import inspect_ledger_parquet, resolve_manifest_path
from query.query_service import QueryService
from ui_query.chart_viewer import ChartViewer
from ui_query.sql_editor import SqlEditorWidget
from ui_query.table_viewer import TableViewer
from ui_query.visual_query import VisualQueryWidget


class QueryWindow(QMainWindow):
    def __init__(self, on_back_to_main: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.setWindowTitle("ADE Pro Query")
        self.resize(1280, 800)

        self.on_back_to_main = on_back_to_main
        self.entry_window = None

        self.query_service = QueryService()
        self.rule_service = RuleService()

        self.db_path_edit = QLineEdit()
        self.db_path_edit.setPlaceholderText("请选择 dataset.toml 或 ledger.parquet")
        self.db_path_edit.setReadOnly(True)
        self.select_db_button = QPushButton("打开数据集")
        self.refresh_recent_button = QPushButton("刷新最近")
        self.back_button = QPushButton("退回主界面")
        self.export_button = QPushButton("导出当前结果")
        self.package_button = QPushButton("分享数据集")
        self.rule_combo = QComboBox()
        self.run_rule_button = QPushButton("运行基础规则")
        self.dataset_info_label = QLabel("当前未打开数据集")
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(7)
        self.recent_table.setHorizontalHeaderLabels(["数据集", "客户", "年度", "行数", "期间", "状态", "Manifest"])
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setMaximumHeight(150)
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.horizontalHeader().setStretchLastSection(True)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("数据源"))
        top_bar.addWidget(self.db_path_edit)
        top_bar.addWidget(self.select_db_button)
        top_bar.addWidget(self.refresh_recent_button)
        top_bar.addWidget(self.back_button)
        top_bar.addWidget(self.rule_combo)
        top_bar.addWidget(self.run_rule_button)
        top_bar.addWidget(self.package_button)
        top_bar.addWidget(self.export_button)

        self.visual_query = VisualQueryWidget()
        self.sql_editor = SqlEditorWidget()
        self.table_viewer = TableViewer()
        self.chart_viewer = ChartViewer()

        tabs = QTabWidget()
        tabs.addTab(self.visual_query, "可视化查询")
        tabs.addTab(self.sql_editor, "SQL 编辑器")
        tabs.addTab(self.chart_viewer, "图表")

        splitter = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(tabs)
        splitter.addWidget(left)
        splitter.addWidget(self.table_viewer)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addLayout(top_bar)
        root_layout.addWidget(self.dataset_info_label)
        root_layout.addWidget(QLabel("最近数据集"))
        root_layout.addWidget(self.recent_table)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self.current_sql = "SELECT * FROM ledger LIMIT 200"
        self.current_result = None
        self._load_rule_options()

        self.select_db_button.clicked.connect(self.on_select_db)
        self.refresh_recent_button.clicked.connect(self.refresh_recent_datasets)
        self.recent_table.itemDoubleClicked.connect(self.on_recent_dataset_double_clicked)
        self.back_button.clicked.connect(self.on_back)
        self.visual_query.build_button.clicked.connect(self.on_build_query)
        self.sql_editor.run_button.clicked.connect(self.on_run_sql)
        self.sql_editor.apply_template_button.clicked.connect(self.on_apply_sql_template)
        self.sql_editor.apply_history_button.clicked.connect(self.on_apply_sql_history)
        self.run_rule_button.clicked.connect(self.on_run_rule)
        self.package_button.clicked.connect(self.on_package_dataset)
        self.export_button.clicked.connect(self.on_export)
        self.sql_editor.set_templates(self.query_service.sql_templates())
        self.refresh_sql_history()
        self.sql_editor.set_sql_text(self.current_sql)
        self.refresh_recent_datasets()

    def _load_rule_options(self) -> None:
        self.rule_combo.clear()
        self.rule_combo.addItems(self.rule_service.list_rules().keys())

    def _selected_db_path(self) -> Path | None:
        text = self.db_path_edit.text().strip()
        if not text:
            return None
        return Path(text)

    def refresh_sql_history(self) -> None:
        self.sql_editor.set_history(self.query_service.sql_history())

    def on_select_db(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开 ADE Pro 数据集",
            str(Path.cwd()),
            "ADE Pro Dataset (*.toml *.parquet);;TOML Manifest (*.toml);;Parquet (*.parquet)",
        )
        if not file_path:
            return
        self.open_dataset(Path(file_path))

    def open_dataset(self, path: Path) -> None:
        self.db_path_edit.setText(str(path))
        manifest_path = resolve_manifest_path(path)
        if manifest_path is not None:
            register_dataset(manifest_path)
            self._show_manifest(manifest_path)
        else:
            self._show_parquet_summary(path)
        self.refresh_recent_datasets()
        self.statusBar().showMessage("数据源已选择。")

    def refresh_recent_datasets(self) -> None:
        summaries = list_recent_dataset_summaries()
        self.recent_table.setRowCount(len(summaries))
        for row_index, item in enumerate(summaries):
            values = [
                item.get("dataset_name", ""),
                item.get("client_name", ""),
                item.get("fiscal_year", ""),
                item.get("row_count", ""),
                item.get("period", ""),
                item.get("status", ""),
                item.get("dataset_manifest", ""),
            ]
            for col_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                self.recent_table.setItem(row_index, col_index, table_item)

    def on_recent_dataset_double_clicked(self, *args) -> None:
        selected = self.recent_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        manifest_item = self.recent_table.item(row, 6)
        if manifest_item is None:
            return
        manifest_path = Path(manifest_item.text())
        if not manifest_path.exists():
            QMessageBox.warning(self, "数据集缺失", "该最近数据集的 manifest 文件不存在。")
            return
        self.open_dataset(manifest_path)

    def _show_manifest(self, manifest_path: Path) -> None:
        try:
            manifest = read_manifest(manifest_path)
            period = f"{manifest.posting_date_min or '?'} 至 {manifest.posting_date_max or '?'}"
            self.dataset_info_label.setText(
                f"当前数据集：{manifest.dataset_name} | 客户：{manifest.client_name} | "
                f"年度：{manifest.fiscal_year} | 行数：{manifest.row_count} | 期间：{period}"
            )
        except Exception as exc:
            self.dataset_info_label.setText(f"当前数据集：{manifest_path} | manifest 读取失败：{exc}")

    def _show_parquet_summary(self, parquet_path: Path) -> None:
        try:
            summary = inspect_ledger_parquet(parquet_path)
            period = f"{summary.get('posting_date_min') or '?'} 至 {summary.get('posting_date_max') or '?'}"
            client = summary.get("client_name") or "未知客户"
            fiscal_year = summary.get("fiscal_year") or "未知年度"
            self.dataset_info_label.setText(
                f"当前数据集：{summary.get('dataset_name') or parquet_path.name} | 客户：{client} | "
                f"年度：{fiscal_year} | 行数：{summary.get('row_count') or '0'} | 期间：{period} | 未发现 dataset.toml"
            )
        except Exception as exc:
            self.dataset_info_label.setText(f"当前数据集：{parquet_path.name} | Parquet 读取失败：{exc}")

    def on_back(self) -> None:
        if self.on_back_to_main is not None:
            self.on_back_to_main()
            self.close()
            return
        from apps.main_app import EntryWindow

        self.entry_window = EntryWindow()
        self.entry_window.show()
        self.close()

    def on_build_query(self) -> None:
        sql_text = self.query_service.build_visual_query(self.visual_query.filters())
        self.current_sql = sql_text
        self.sql_editor.set_sql_text(sql_text)
        self.on_run_sql()

    def on_apply_sql_template(self) -> None:
        sql_text = self.sql_editor.selected_template_sql()
        if sql_text:
            self.sql_editor.set_sql_text(sql_text)

    def on_apply_sql_history(self) -> None:
        sql_text = self.sql_editor.selected_history_sql()
        if sql_text:
            self.sql_editor.set_sql_text(sql_text)

    def on_run_sql(self) -> None:
        db_path = self._selected_db_path()
        if db_path is None:
            QMessageBox.warning(self, "缺少数据源", "请先打开 dataset.toml 或 ledger.parquet。")
            return
        try:
            sql_text = self.sql_editor.sql_text()
            result = self.query_service.run_sql(db_path, sql_text)
            self.current_sql = sql_text
            self.current_result = result
            self.table_viewer.set_result(result)
            self.query_service.record_sql_history(db_path, sql_text)
            self.refresh_sql_history()
            self.statusBar().showMessage(f"返回 {len(result)} 行")
        except Exception as exc:
            QMessageBox.critical(self, "执行失败", str(exc))

    def on_run_rule(self) -> None:
        db_path = self._selected_db_path()
        if db_path is None:
            QMessageBox.warning(self, "缺少数据源", "请先打开 dataset.toml 或 ledger.parquet。")
            return
        try:
            rule_name = self.rule_combo.currentText()
            if not rule_name:
                QMessageBox.information(self, "无规则", "当前没有可运行的基础规则。")
                return
            result = self.rule_service.run_rule(db_path, rule_name)
            self.current_sql = self.rule_service.list_rules()[rule_name]
            self.sql_editor.set_sql_text(self.current_sql)
            self.current_result = result
            self.table_viewer.set_result(result)
            self.statusBar().showMessage(f"{rule_name} 返回 {len(result)} 行")
        except Exception as exc:
            QMessageBox.critical(self, "规则执行失败", str(exc))

    def on_export(self) -> None:
        db_path = self._selected_db_path()
        if db_path is None:
            QMessageBox.warning(self, "缺少数据源", "请先打开 dataset.toml 或 ledger.parquet。")
            return
        if self.current_result is None:
            QMessageBox.information(self, "无结果", "请先执行查询。")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出 Excel", str(Path.cwd() / "query_export.xlsx"), "Excel Files (*.xlsx)")
        if not file_path:
            return
        try:
            result = self.query_service.export_sql_result(db_path, self.current_sql, Path(file_path))
            QMessageBox.information(self, "导出完成", f"已导出 {result.total_rows} 行到\n{result.file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def on_package_dataset(self) -> None:
        db_path = self._selected_db_path()
        if db_path is None:
            QMessageBox.warning(self, "缺少数据源", "请先打开 dataset.toml 或 ledger.parquet。")
            return
        default_path = Path.cwd() / default_package_name(db_path)
        file_path, _ = QFileDialog.getSaveFileName(self, "分享 ADE Pro 数据集", str(default_path), "Zip Files (*.zip)")
        if not file_path:
            return
        output_path = Path(file_path)
        if output_path.suffix.lower() != ".zip":
            output_path = output_path.with_suffix(".zip")
        try:
            package_path = package_dataset(db_path, output_path)
            QMessageBox.information(self, "打包完成", f"已生成数据集包：\n{package_path}")
        except Exception as exc:
            QMessageBox.critical(self, "打包失败", str(exc))
