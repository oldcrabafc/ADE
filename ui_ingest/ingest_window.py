from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ingest.import_service import ImportService
from ingest.client_profile_service import find_profile, save_profile
from ingest.mapping_service import auto_detect_mapping
from shared.schema import AmountRules, ImportRequest, IngestProfile, LedgerFieldMapping
from ui_ingest.import_report_view import ImportReportView
from ui_ingest.mapping_dialog import MappingDialog


class PreviewWorker(QObject):
    finished = Signal(object, object)

    def __init__(
        self,
        import_service: ImportService,
        source_type: str,
        source_path: Path,
        source_table: str,
        source_sheet: str | None,
        row_limit: int,
    ) -> None:
        super().__init__()
        self.import_service = import_service
        self.source_type = source_type
        self.source_path = source_path
        self.source_table = source_table
        self.source_sheet = source_sheet
        self.row_limit = row_limit

    def run(self) -> None:
        try:
            payload = self.import_service.preview_rows(
                self.source_type,
                self.source_path,
                self.source_table,
                self.source_sheet,
                row_limit=self.row_limit,
            )
            self.finished.emit(payload, None)
        except Exception as exc:
            self.finished.emit(None, str(exc))


class IngestWindow(QMainWindow):
    def __init__(self, on_back_to_main: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.setWindowTitle("ADE Pro Ingest · 数据集转换")
        self.resize(1020, 760)

        self.on_back_to_main = on_back_to_main
        self.entry_window = None

        self.import_service = ImportService()
        self.field_mapping = None
        self.ingest_profile = None
        self.inline_mapping_combos: list[QComboBox] = []
        self.preview_columns: list[str] = []
        self.preview_rows: list[list[str]] = []
        self.preview_loaded = False
        self.preview_thread: QThread | None = None
        self.preview_worker: PreviewWorker | None = None

        self.client_name_edit = QLineEdit()
        self.client_name_edit.setPlaceholderText("如：某某有限公司")
        self.dataset_name_edit = QLineEdit()
        self.dataset_name_edit.setPlaceholderText("如：ABC 2024 Ledger")
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(["excel", "csv", "duckdb", "parquet"])
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("选择文件")
        self.sheet_combo = QComboBox()
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.addItem("请先选择 Excel 文件")
        self.mapping_button = QPushButton("确认字段与金额规则")
        self.mapping_button.setEnabled(False)
        self.save_profile_checkbox = QCheckBox("保存为客户导入 profile")
        self.save_profile_checkbox.setChecked(True)
        self.fiscal_year_spin = QSpinBox()
        self.fiscal_year_spin.setRange(2000, 2100)
        self.fiscal_year_spin.setValue(datetime.now().year)
        self.import_mode_combo = QComboBox()
        self.import_mode_combo.addItem("新导入（覆盖该客户该年度）", "new")
        self.import_mode_combo.addItem("追加导入（保留原数据）", "append")
        self.duplicate_mode_combo = QComboBox()
        self.duplicate_mode_combo.addItems(["mark", "skip", "strict"])
        self.mapping_status_label = QLabel("尚未确认字段映射；可先在预览表第一行选择目标字段")
        self.profile_status_label = QLabel("未匹配客户 profile")
        self.import_button = QPushButton("确认无误后导入全部")
        self.back_button = QPushButton("退回主界面")
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setMinimumHeight(230)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.report_view = ImportReportView()

        hero_title = QLabel("生成标准 Ledger 数据集")
        hero_title.setObjectName("HeroTitle")
        hero_subtitle = QLabel("1. 选择文件  2. 输入导入信息  3. 预览10行并映射，确认后生成 ledger.parquet")
        hero_subtitle.setObjectName("HeroSubTitle")

        step1_form = QFormLayout()
        step1_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        step1_form.addRow("来源类型", self.source_type_combo)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_path_edit)
        file_row.addWidget(self.browse_button)
        step1_form.addRow("来源文件", file_row)
        step1_form.addRow("工作表", self.sheet_combo)

        step2_form = QFormLayout()
        step2_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        step2_form.addRow("客户全称", self.client_name_edit)
        step2_form.addRow("会计年度", self.fiscal_year_spin)
        step2_form.addRow("数据集名称", self.dataset_name_edit)
        step2_form.addRow("导入方式", self.import_mode_combo)
        step2_form.addRow("重复处理", self.duplicate_mode_combo)

        step3_form = QFormLayout()
        step3_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        step3_form.addRow("字段映射", self.mapping_button)
        step3_form.addRow("保存配置", self.save_profile_checkbox)
        step3_form.addRow("映射状态", self.mapping_status_label)
        step3_form.addRow("Profile", self.profile_status_label)

        step1_box = self._build_step_box("Step 1 · 选择文件", step1_form)
        step2_box = self._build_step_box("Step 2 · 输入导入信息", step2_form)
        step3_box = self._build_step_box("Step 3 · 预览与映射", step3_form)

        preview_box = QGroupBox("预览面板（前10行）")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview_table)

        action_row = QHBoxLayout()
        action_row.addWidget(self.back_button)
        action_row.addWidget(self.import_button)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(hero_title)
        layout.addWidget(hero_subtitle)
        layout.addWidget(step1_box)
        layout.addWidget(step2_box)
        layout.addWidget(step3_box)
        layout.addWidget(preview_box)
        layout.addLayout(action_row)
        layout.addWidget(QLabel("导入报告"))
        layout.addWidget(self.report_view)
        self.setCentralWidget(root)

        self._apply_style()

        self.browse_button.clicked.connect(self.on_browse)
        self.client_name_edit.textChanged.connect(self._sync_default_dataset_name)
        self.fiscal_year_spin.valueChanged.connect(self._sync_default_dataset_name)
        self.source_type_combo.currentTextChanged.connect(self.on_source_type_changed)
        self.sheet_combo.currentTextChanged.connect(self.on_sheet_changed)
        self.mapping_button.clicked.connect(self.on_mapping)
        self.import_button.clicked.connect(self.on_import)
        self.back_button.clicked.connect(self.on_back)

    def _sync_default_dataset_name(self) -> None:
        if self.dataset_name_edit.text().strip():
            return
        client_name = self.client_name_edit.text().strip()
        if not client_name:
            return
        self.dataset_name_edit.setPlaceholderText(f"{client_name} {self.fiscal_year_spin.value()} Ledger")

    def on_back(self) -> None:
        if self.on_back_to_main is not None:
            self.on_back_to_main()
            self.close()
            return
        from apps.main_app import EntryWindow

        self.entry_window = EntryWindow()
        self.entry_window.show()
        self.close()

    def _build_step_box(self, title: str, form: QFormLayout) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("StepCard")
        wrapper = QVBoxLayout(box)
        wrapper.addLayout(form)
        return box

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f4f6f8;
            }
            QLabel#HeroTitle {
                font-size: 22px;
                font-weight: 700;
                color: #1f2a37;
                margin-top: 6px;
            }
            QLabel#HeroSubTitle {
                color: #4b5563;
                margin-bottom: 8px;
            }
            QGroupBox#StepCard,
            QGroupBox {
                border: 1px solid #d3dae3;
                border-radius: 10px;
                margin-top: 8px;
                background: #ffffff;
                font-weight: 600;
                color: #1f2a37;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
            }
            QLineEdit, QComboBox, QSpinBox, QTableWidget {
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 5px;
                background: #fbfdff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 28px;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 14px;
                height: 14px;
            }
            QTableWidget QScrollBar:vertical {
                width: 24px;
                background: #eef2f7;
                border-radius: 6px;
            }
            QTableWidget QScrollBar::handle:vertical {
                background: #9aa9bd;
                min-height: 36px;
                border-radius: 6px;
            }
            QTableWidget QScrollBar:horizontal {
                height: 24px;
                background: #eef2f7;
                border-radius: 6px;
            }
            QTableWidget QScrollBar::handle:horizontal {
                background: #9aa9bd;
                min-width: 36px;
                border-radius: 6px;
            }
            QPushButton {
                border: 0;
                border-radius: 8px;
                padding: 8px 14px;
                background: #0f6cbd;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton:disabled {
                background: #a7b3c5;
            }
            """
        )

    def _reset_preview_and_mapping(self) -> None:
        self.preview_loaded = False
        self.preview_columns = []
        self.preview_rows = []
        self.field_mapping = None
        self.ingest_profile = None
        self.inline_mapping_combos = []
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        self.mapping_button.setEnabled(False)
        self.mapping_status_label.setText("尚未确认字段映射；可先在预览表第一行选择目标字段")
        self.profile_status_label.setText("未匹配客户 profile")

    def _set_preview_busy(self, busy: bool) -> None:
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.statusBar().showMessage("正在加载预览...", 0)
            return

        if QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    def _on_preview_finished(self, payload: object, error_message: object) -> None:
        self._set_preview_busy(False)

        if error_message:
            QMessageBox.critical(self, "预览失败", str(error_message))
            return
        if not isinstance(payload, dict):
            QMessageBox.critical(self, "预览失败", "预览结果无效。")
            return

        self.preview_columns = [str(column) for column in payload.get("columns", [])]
        rows = payload.get("rows", [])
        self.preview_rows = [[str(value) for value in row] for row in rows] if isinstance(rows, list) else []
        self._load_preview_table(self.preview_columns, self.preview_rows)
        self._apply_initial_inline_mapping()
        self.preview_loaded = True
        self.mapping_button.setEnabled(True)
        self.statusBar().showMessage("预览完成，可在第一行下拉框调整字段映射。")

    def _on_preview_thread_finished(self) -> None:
        self.preview_worker = None
        self.preview_thread = None

    def _is_excel_source(self) -> bool:
        return self.source_type_combo.currentText() == "excel"

    def _selected_sheet(self) -> str | None:
        if not self._is_excel_source():
            return None
        if self.sheet_combo.count() == 0:
            return None
        sheet_name = self.sheet_combo.currentText().strip()
        if not sheet_name or sheet_name == "请先选择 Excel 文件":
            return None
        return sheet_name

    def _selected_import_mode(self) -> str:
        mode = self.import_mode_combo.currentData()
        if isinstance(mode, str) and mode in {"new", "append"}:
            return mode
        return "append"

    def _sync_import_mode_by_source(self) -> None:
        if self.source_type_combo.currentText() == "duckdb":
            self.import_mode_combo.setCurrentIndex(self.import_mode_combo.findData("append"))
            self.import_mode_combo.setEnabled(False)
            self.statusBar().showMessage("DuckDB 仅支持追加导入。")
            return
        self.import_mode_combo.setEnabled(True)

    def _reset_sheet_selector(self, placeholder: str) -> None:
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItem(placeholder)
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.blockSignals(False)

    def on_source_type_changed(self) -> None:
        self._reset_preview_and_mapping()
        self._sync_import_mode_by_source()
        if self._is_excel_source() and self.file_path_edit.text():
            self._load_excel_sheets(Path(self.file_path_edit.text()))
            return
        if self._is_excel_source():
            self._reset_sheet_selector("请先选择 Excel 文件")
        else:
            self._reset_sheet_selector("非 Excel 来源无需选择工作表")

    def _load_excel_sheets(self, path: Path) -> None:
        try:
            sheets = self.import_service.list_source_sheets("excel", path)
            self.sheet_combo.blockSignals(True)
            self.sheet_combo.clear()
            self.sheet_combo.addItems(sheets)
            self.sheet_combo.setEnabled(True)
            self.sheet_combo.blockSignals(False)
            if sheets:
                self.on_preview()
        except Exception as exc:
            self._reset_sheet_selector("读取工作表失败")
            QMessageBox.critical(self, "读取失败", str(exc))

    def on_sheet_changed(self) -> None:
        if not self._is_excel_source():
            return
        if self._selected_sheet() is None:
            return
        self.on_preview()

    def _load_preview_table(self, headers: list[str], rows: list[list[str]]) -> None:
        self.preview_table.clear()
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        self.preview_table.setRowCount(len(rows) + 1)
        self.inline_mapping_combos = []

        for col_index, _header in enumerate(headers):
            combo = QComboBox()
            combo.addItems(_mapping_options())
            self.preview_table.setCellWidget(0, col_index, combo)
            self.inline_mapping_combos.append(combo)

        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                self.preview_table.setItem(row_index + 1, col_index, item)

        self.preview_table.setVerticalHeaderLabels(["映射"] + [str(index + 1) for index in range(len(rows))])
        self.preview_table.verticalHeader().setVisible(True)

        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setStretchLastSection(True)

    def _apply_initial_inline_mapping(self) -> None:
        profile = None
        client_name = self.client_name_edit.text().strip()
        if client_name:
            profile = find_profile(
                client_name,
                self.source_type_combo.currentText(),
                self._selected_sheet(),
                self.preview_columns,
            )
        if profile is not None:
            self._set_inline_mapping_from_profile(profile)
            self.mapping_status_label.setText(f"已自动匹配 profile：{profile.profile_name}")
            self.profile_status_label.setText(f"已匹配：{profile.profile_name}")
            return

        detected = auto_detect_mapping(self.preview_columns)
        source_to_target = {
            detected.book_date: "posting_date",
            detected.voucher_no: "voucher_id",
            detected.ac_code: "ac_code",
            detected.ac_name: "ac_caption",
            detected.summary: "description",
            detected.direct_amount_field: "rc_amount",
            detected.debit_field: "debit_amount",
            detected.credit_field: "credit_amount",
        }
        for column, combo in zip(self.preview_columns, self.inline_mapping_combos):
            target = source_to_target.get(column)
            if target:
                combo.setCurrentText(target)
        self.profile_status_label.setText("未匹配 profile，已按字段别名自动识别")

    def _set_inline_mapping_from_profile(self, profile: IngestProfile) -> None:
        source_to_target: dict[str, str] = {}
        for target, source in profile.field_mapping.__dict__.items():
            if isinstance(source, str) and source:
                source_to_target[source] = target
        rules = profile.amount_rules
        if rules.direct_amount_field:
            source_to_target[rules.direct_amount_field] = "rc_amount"
        if rules.amount_field:
            source_to_target[rules.amount_field] = "amount"
        if rules.drcr_field:
            source_to_target[rules.drcr_field] = "drcr"
        if rules.debit_field:
            source_to_target[rules.debit_field] = "debit_amount"
        if rules.credit_field:
            source_to_target[rules.credit_field] = "credit_amount"
        for column, combo in zip(self.preview_columns, self.inline_mapping_combos):
            target = source_to_target.get(column)
            if target and target in _mapping_options():
                combo.setCurrentText(target)

    def _profile_from_inline_mapping(self, initial_profile: IngestProfile | None = None) -> IngestProfile:
        target_to_source: dict[str, str] = {}
        for column, combo in zip(self.preview_columns, self.inline_mapping_combos):
            target = combo.currentText()
            if target and target != "不导入":
                target_to_source[target] = column

        mapping = LedgerFieldMapping(
            posting_date=target_to_source.get("posting_date", ""),
            voucher_id=target_to_source.get("voucher_id", ""),
            ac_code=target_to_source.get("ac_code", ""),
            ac_caption=target_to_source.get("ac_caption", ""),
            description=target_to_source.get("description", ""),
            voucher_header=target_to_source.get("voucher_header"),
            company_id=target_to_source.get("company_id"),
            drcr=target_to_source.get("drcr"),
            rc_amount=target_to_source.get("rc_amount") or target_to_source.get("amount"),
            lc_amount=target_to_source.get("lc_amount"),
            vendor_id=target_to_source.get("vendor_id"),
            vendor_name=target_to_source.get("vendor_name"),
            customer_id=target_to_source.get("customer_id"),
            customer_name=target_to_source.get("customer_name"),
            department=target_to_source.get("department"),
            employee_id=target_to_source.get("employee_id"),
            employee_name=target_to_source.get("employee_name"),
            currency=target_to_source.get("currency"),
            document_type=target_to_source.get("document_type"),
            posting_period=target_to_source.get("posting_period"),
            source_system=target_to_source.get("source_system"),
        )
        if initial_profile is not None:
            amount_rules = initial_profile.amount_rules
            profile_name = initial_profile.profile_name
        elif target_to_source.get("drcr") and target_to_source.get("amount"):
            amount_rules = AmountRules(
                mode="amount_with_drcr",
                amount_field=target_to_source.get("amount"),
                drcr_field=target_to_source.get("drcr"),
            )
            profile_name = "default"
        elif target_to_source.get("debit_amount") and target_to_source.get("credit_amount"):
            amount_rules = AmountRules(
                mode="debit_credit_columns",
                debit_field=target_to_source.get("debit_amount"),
                credit_field=target_to_source.get("credit_amount"),
            )
            profile_name = "default"
        else:
            amount_rules = AmountRules(
                mode="direct_signed_amount",
                direct_amount_field=target_to_source.get("rc_amount"),
            )
            profile_name = "default"
        return IngestProfile(
            profile_name=profile_name,
            field_mapping=mapping,
            amount_rules=amount_rules,
            source_type=self.source_type_combo.currentText(),
            source_sheet=self._selected_sheet(),
        )

    def on_browse(self) -> None:
        filters = "All Supported (*.xlsx *.csv *.duckdb);;Excel (*.xlsx);;CSV (*.csv);;DuckDB (*.duckdb)"
        file_path, _ = QFileDialog.getOpenFileName(self, "选择来源文件", str(Path.cwd()), filters)
        if not file_path:
            return
        self.file_path_edit.setText(file_path)
        self._reset_preview_and_mapping()
        if self._is_excel_source():
            self._load_excel_sheets(Path(file_path))
            self.statusBar().showMessage("已选择文件，请确认工作表。")
            return
        self._reset_sheet_selector("非 Excel 来源无需选择工作表")
        self.on_preview()

    def on_preview(self) -> None:
        if not self.file_path_edit.text():
            QMessageBox.warning(self, "缺少文件", "请先选择来源文件。")
            return
        if self._is_excel_source() and self._selected_sheet() is None:
            QMessageBox.warning(self, "缺少工作表", "请先确认要导入的 worksheet。")
            return
        if self.preview_thread is not None:
            return

        self.preview_loaded = False
        self.field_mapping = None
        self.mapping_button.setEnabled(False)
        self.mapping_status_label.setText("尚未确认字段映射")

        self.preview_thread = QThread(self)
        self.preview_worker = PreviewWorker(
            self.import_service,
            self.source_type_combo.currentText(),
            Path(self.file_path_edit.text()),
            "journal",
            self._selected_sheet(),
            10,
        )
        self.preview_worker.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.preview_worker.run)
        self.preview_worker.finished.connect(self._on_preview_finished)
        self.preview_worker.finished.connect(self.preview_thread.quit)
        self.preview_worker.finished.connect(self.preview_worker.deleteLater)
        self.preview_thread.finished.connect(self.preview_thread.deleteLater)
        self.preview_thread.finished.connect(self._on_preview_thread_finished)

        self._set_preview_busy(True)
        self.preview_thread.start()

    def on_mapping(self) -> None:
        if not self.preview_loaded:
            QMessageBox.warning(self, "缺少预览", "请先读取前10行预览。")
            return
        try:
            initial_profile = None
            client_name = self.client_name_edit.text().strip()
            if client_name:
                initial_profile = find_profile(
                    client_name,
                    self.source_type_combo.currentText(),
                    self._selected_sheet(),
                    self.preview_columns,
                )
            inline_profile = self._profile_from_inline_mapping(initial_profile)
            dialog = MappingDialog(
                self.preview_columns,
                self,
                initial_profile=inline_profile,
                preview_rows=self.preview_rows,
            )
            if dialog.exec():
                self.ingest_profile = dialog.profile(
                    self.source_type_combo.currentText(),
                    self._selected_sheet(),
                )
                self.field_mapping = dialog.mapping()
                self._save_profile_if_requested(client_name, self.ingest_profile)
                self.mapping_status_label.setText(f"已确认字段映射：{self.ingest_profile.profile_name}")
                self.statusBar().showMessage("字段映射与金额规则已确认，可生成标准数据集。")
        except Exception as exc:
            QMessageBox.critical(self, "读取失败", str(exc))

    def _save_profile_if_requested(self, client_name: str, profile: IngestProfile) -> None:
        if not self.save_profile_checkbox.isChecked():
            self.profile_status_label.setText("本次未保存 profile")
            return
        if not client_name:
            self.profile_status_label.setText("未保存 profile：缺少客户全称")
            return
        path = save_profile(client_name, profile)
        self.profile_status_label.setText(f"已保存：{profile.profile_name} -> {path}")

    def on_import(self) -> None:
        if not self.client_name_edit.text().strip():
            QMessageBox.warning(self, "缺少客户", "请输入客户全称。")
            return
        if not self.file_path_edit.text():
            QMessageBox.warning(self, "缺少文件", "请选择来源文件。")
            return
        if self._is_excel_source() and self._selected_sheet() is None:
            QMessageBox.warning(self, "缺少工作表", "请先确认要导入的 worksheet。")
            return
        if not self.preview_loaded:
            QMessageBox.warning(self, "缺少预览", "请先读取前10行预览。")
            return
        if self.field_mapping is None:
            QMessageBox.warning(self, "缺少字段映射", "请先完成字段映射。")
            return
        if self.ingest_profile is None:
            QMessageBox.warning(self, "缺少金额规则", "请先完成字段映射与金额规则。")
            return

        import_mode = self._selected_import_mode()
        if self.source_type_combo.currentText() == "duckdb" and import_mode != "append":
            QMessageBox.warning(self, "导入方式不支持", "DuckDB 来源仅支持追加导入。")
            return
        mode_label = "新导入（覆盖）" if import_mode == "new" else "追加导入"
        confirm_message = (
            "即将按当前配置执行全量转换并生成标准数据集。\n"
            f"客户: {self.client_name_edit.text().strip()}\n"
            f"会计年度: {self.fiscal_year_spin.value()}\n"
            f"数据集: {self._dataset_name()}\n"
            f"导入方式: {mode_label}\n"
            f"工作表: {self._selected_sheet() or 'N/A'}\n"
            "已完成: 文件选择、前10行预览、字段映射\n\n"
        )
        if import_mode == "new":
            confirm_message += "注意: 新导入会先清空该客户该年度已有数据。\n\n"
        confirm_message += "是否继续？"

        confirmed = QMessageBox.question(
            self,
            "确认导入",
            confirm_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.import_service.import_to_client_db(
                ImportRequest(
                    client_name=self.client_name_edit.text().strip(),
                    source_type=self.source_type_combo.currentText(),
                    source_path=Path(self.file_path_edit.text()),
                    fiscal_year=self.fiscal_year_spin.value(),
                    field_mapping=self.field_mapping,
                    import_mode=import_mode,
                    duplicate_mode=self.duplicate_mode_combo.currentText(),
                    source_sheet=self._selected_sheet(),
                    profile=self.ingest_profile,
                    dataset_name=self._dataset_name(),
                )
            )
            self.report_view.show_result(result)
            QMessageBox.information(
                self,
                "转换完成",
                f"成功生成 {result.success_rows} 行 ledger 数据。\n{result.dataset_path or ''}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def _dataset_name(self) -> str:
        explicit_name = self.dataset_name_edit.text().strip()
        if explicit_name:
            return explicit_name
        client_name = self.client_name_edit.text().strip()
        return f"{client_name} {self.fiscal_year_spin.value()} Ledger"


def _mapping_options() -> list[str]:
    return [
        "不导入",
        "posting_date",
        "voucher_id",
        "ac_code",
        "ac_caption",
        "description",
        "rc_amount",
        "amount",
        "drcr",
        "debit_amount",
        "credit_amount",
        "voucher_header",
        "company_id",
        "lc_amount",
        "vendor_id",
        "vendor_name",
        "customer_id",
        "customer_name",
        "department",
        "employee_id",
        "employee_name",
        "currency",
        "document_type",
        "posting_period",
        "source_system",
    ]
