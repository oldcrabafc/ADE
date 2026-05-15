from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ingest.mapping_service import auto_detect_mapping
from shared.schema import AmountRules, IngestProfile, LedgerFieldMapping


class LockedWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if self.view().isVisible():
            super().wheelEvent(event)
            return
        event.ignore()


class MappingDialog(QDialog):
    _DEFAULT_REQUIRED_FIELDS = ["posting_date", "voucher_id", "ac_code", "ac_caption", "description"]

    def __init__(
        self,
        columns: list[str],
        parent=None,
        initial_profile: IngestProfile | None = None,
        preview_rows: list[list[str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ledger 字段映射与金额规则")
        self.resize(900, 680)
        self._initial_profile = initial_profile
        self.columns = [""] + columns
        self.source_columns = columns
        self.preview_rows = preview_rows or []
        detected = auto_detect_mapping(columns)
        initial_mapping = initial_profile.field_mapping if initial_profile else None
        initial_amount = initial_profile.amount_rules if initial_profile else None

        self.profile_name_edit = QLineEdit(initial_profile.profile_name if initial_profile else "default")
        self.posting_date_combo = self._build_combo(initial_mapping.posting_date if initial_mapping else detected.book_date)
        self.voucher_id_combo = self._build_combo(initial_mapping.voucher_id if initial_mapping else detected.voucher_no)
        self.ac_code_combo = self._build_combo(initial_mapping.ac_code if initial_mapping else detected.ac_code)
        self.ac_caption_combo = self._build_combo(initial_mapping.ac_caption if initial_mapping else detected.ac_name)
        self.description_combo = self._build_combo(initial_mapping.description if initial_mapping else detected.summary)
        self.voucher_header_combo = self._build_combo(initial_mapping.voucher_header if initial_mapping else None)
        self.company_id_combo = self._build_combo(initial_mapping.company_id if initial_mapping else None)
        self.lc_amount_combo = self._build_combo(initial_mapping.lc_amount if initial_mapping else None)
        self.vendor_id_combo = self._build_combo(initial_mapping.vendor_id if initial_mapping else None)
        self.vendor_name_combo = self._build_combo(initial_mapping.vendor_name if initial_mapping else None)
        self.customer_id_combo = self._build_combo(initial_mapping.customer_id if initial_mapping else None)
        self.customer_name_combo = self._build_combo(initial_mapping.customer_name if initial_mapping else None)
        self._field_order = [
            "posting_date",
            "voucher_id",
            "ac_code",
            "ac_caption",
            "description",
            "voucher_header",
            "company_id",
            "lc_amount",
            "vendor_id",
            "vendor_name",
            "customer_id",
            "customer_name",
        ]
        self._field_widgets = {
            "posting_date": self.posting_date_combo,
            "voucher_id": self.voucher_id_combo,
            "ac_code": self.ac_code_combo,
            "ac_caption": self.ac_caption_combo,
            "description": self.description_combo,
            "voucher_header": self.voucher_header_combo,
            "company_id": self.company_id_combo,
            "lc_amount": self.lc_amount_combo,
            "vendor_id": self.vendor_id_combo,
            "vendor_name": self.vendor_name_combo,
            "customer_id": self.customer_id_combo,
            "customer_name": self.customer_name_combo,
        }
        initial_required = list(initial_profile.required_field) if initial_profile and initial_profile.required_field else []
        self._required_fields = initial_required or list(self._DEFAULT_REQUIRED_FIELDS)

        amount_mode = initial_amount.mode if initial_amount else (
            "direct_signed_amount" if detected.direct_amount_field else "debit_credit_columns"
        )
        self.amount_mode_combo = LockedWheelComboBox()
        self.amount_mode_combo.addItem("已是借正贷负净额", "direct_signed_amount")
        self.amount_mode_combo.addItem("借贷标识 + 正数金额", "amount_with_drcr")
        self.amount_mode_combo.addItem("借方金额列 + 贷方金额列", "debit_credit_columns")
        index = self.amount_mode_combo.findData(amount_mode)
        self.amount_mode_combo.setCurrentIndex(max(index, 0))

        self.direct_amount_combo = self._build_combo((initial_amount.direct_amount_field if initial_amount else None) or detected.direct_amount_field)
        self.amount_combo = self._build_combo(initial_amount.amount_field if initial_amount else detected.direct_amount_field)
        self.drcr_combo = self._build_combo((initial_amount.drcr_field if initial_amount else None) or (initial_mapping.drcr if initial_mapping else None))
        self.debit_combo = self._build_combo((initial_amount.debit_field if initial_amount else None) or detected.debit_field)
        self.credit_combo = self._build_combo((initial_amount.credit_field if initial_amount else None) or detected.credit_field)
        self.debit_values_edit = QLineEdit(", ".join((initial_amount.debit_values if initial_amount else ["借", "D", "Debit", "S"])))
        self.credit_values_edit = QLineEdit(", ".join((initial_amount.credit_values if initial_amount else ["贷", "C", "Credit", "H"])))
        self.amount_preview_table = QTableWidget()
        self.amount_preview_table.setColumnCount(5)
        self.amount_preview_table.setHorizontalHeaderLabels(["源借贷标识", "源金额", "借方金额", "贷方金额", "转换后 rc_amount"])
        self.amount_preview_table.verticalHeader().setVisible(False)
        self.amount_preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.amount_preview_table.setMaximumHeight(180)
        self.amount_preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.amount_preview_table.horizontalHeader().setStretchLastSection(True)

        content = QVBoxLayout()
        content.addWidget(self._profile_box())
        content.addWidget(self._required_box())
        content.addWidget(self._optional_box())
        content.addWidget(self._amount_box())
        content.addWidget(self._amount_preview_box())

        content_widget = QGroupBox()
        content_widget.setFlat(True)
        content_widget.setLayout(content)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setWidget(content_widget)
        scroll.setStyleSheet(
            "QScrollBar:vertical { width: 24px; }"
            "QScrollBar::handle:vertical { min-height: 36px; }"
        )

        root = QVBoxLayout(self)
        root.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_h = screen.availableGeometry().height()
            self.setMaximumHeight(max(520, int(screen_h * 0.9)))
        self._connect_preview_refresh()
        self.refresh_amount_preview()

    def _build_combo(self, current: str | None) -> QComboBox:
        combo = LockedWheelComboBox()
        combo.addItems(self.columns)
        if current and current in self.columns:
            combo.setCurrentText(current)
        return combo

    def _profile_box(self) -> QGroupBox:
        box = QGroupBox("Profile")
        form = QFormLayout(box)
        form.addRow("名称", self.profile_name_edit)
        return box

    def _required_box(self) -> QGroupBox:
        box = QGroupBox("Required ledger 字段")
        form = QFormLayout(box)
        shown: set[str] = set()
        for field_name in self._required_fields:
            widget = self._field_widgets.get(field_name)
            if widget is None:
                continue
            form.addRow(field_name, widget)
            shown.add(field_name)
        for field_name in self._required_fields:
            if field_name in shown:
                continue
            widget = self._field_widgets.get(field_name)
            if widget is None:
                continue
            form.addRow(field_name, widget)
        return box

    def _optional_box(self) -> QGroupBox:
        box = QGroupBox("Optional ledger 字段")
        form = QFormLayout(box)
        optional_fields = [field for field in self._field_order if field not in self._required_fields]
        for index in range(0, len(optional_fields), 2):
            row = QHBoxLayout()
            for field_name in optional_fields[index : index + 2]:
                widget = self._field_widgets.get(field_name)
                if widget is None:
                    continue
                row.addWidget(QLabel(field_name))
                row.addWidget(widget)
            form.addRow(row)
        return box

    def _amount_box(self) -> QGroupBox:
        box = QGroupBox("金额规则：转换后 rc_amount 借方为正、贷方为负")
        form = QFormLayout(box)
        form.addRow("规则说明", QLabel("amount + drcr -> rc_amount"))
        form.addRow("处理方式", self.amount_mode_combo)
        form.addRow("净额金额列", self.direct_amount_combo)
        form.addRow("借贷标识列", self.drcr_combo)
        form.addRow("正数金额列（amount）", self.amount_combo)
        form.addRow("借方金额列", self.debit_combo)
        form.addRow("贷方金额列", self.credit_combo)
        form.addRow("借方值", self.debit_values_edit)
        form.addRow("贷方值", self.credit_values_edit)
        return box

    def _amount_preview_box(self) -> QGroupBox:
        box = QGroupBox("金额转换预览（前几行）")
        layout = QVBoxLayout(box)
        layout.addWidget(self.amount_preview_table)
        return box

    def _connect_preview_refresh(self) -> None:
        widgets = [
            self.amount_mode_combo,
            self.direct_amount_combo,
            self.amount_combo,
            self.drcr_combo,
            self.debit_combo,
            self.credit_combo,
        ]
        for widget in widgets:
            widget.currentTextChanged.connect(self.refresh_amount_preview)
        self.debit_values_edit.textChanged.connect(self.refresh_amount_preview)
        self.credit_values_edit.textChanged.connect(self.refresh_amount_preview)

    def refresh_amount_preview(self) -> None:
        rows = self.preview_rows[:10]
        self.amount_preview_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            row_dict = {
                column: row[col_index] if col_index < len(row) else ""
                for col_index, column in enumerate(self.source_columns)
            }
            drcr_value, amount_value, debit_value, credit_value, rc_amount = self._preview_amount(row_dict)
            values = [drcr_value, amount_value, debit_value, credit_value, rc_amount]
            for col_index, value in enumerate(values):
                self.amount_preview_table.setItem(row_index, col_index, QTableWidgetItem(value))

    def _preview_amount(self, row: dict[str, str]) -> tuple[str, str, str, str, str]:
        mode = str(self.amount_mode_combo.currentData())
        if mode == "direct_signed_amount":
            amount_value = row.get(self.direct_amount_combo.currentText(), "")
            return "", amount_value, "", "", _format_number(_parse_number(amount_value))
        if mode == "amount_with_drcr":
            drcr_value = row.get(self.drcr_combo.currentText(), "")
            amount_value = row.get(self.amount_combo.currentText(), "")
            number = _parse_number(amount_value)
            if number is None:
                rc_amount = ""
            elif drcr_value in _split_values(self.debit_values_edit.text()):
                rc_amount = _format_number(abs(number))
            elif drcr_value in _split_values(self.credit_values_edit.text()):
                rc_amount = _format_number(-abs(number))
            else:
                rc_amount = "无法识别借贷"
            return drcr_value, amount_value, "", "", rc_amount
        if mode == "debit_credit_columns":
            debit_value = row.get(self.debit_combo.currentText(), "")
            credit_value = row.get(self.credit_combo.currentText(), "")
            debit = _parse_number(debit_value) or 0
            credit = _parse_number(credit_value) or 0
            return "", "", debit_value, credit_value, _format_number(abs(debit) - abs(credit))
        return "", "", "", "", ""

    def profile(self, source_type: str = "excel", source_sheet: str | None = None) -> IngestProfile:
        amount_rules = AmountRules(
            mode=str(self.amount_mode_combo.currentData()),
            direct_amount_field=self.direct_amount_combo.currentText() or None,
            amount_field=self.amount_combo.currentText() or None,
            debit_field=self.debit_combo.currentText() or None,
            credit_field=self.credit_combo.currentText() or None,
            drcr_field=self.drcr_combo.currentText() or None,
            debit_values=_split_values(self.debit_values_edit.text()),
            credit_values=_split_values(self.credit_values_edit.text()),
        )
        mapping = LedgerFieldMapping(
            posting_date=self.posting_date_combo.currentText(),
            voucher_id=self.voucher_id_combo.currentText(),
            ac_code=self.ac_code_combo.currentText(),
            ac_caption=self.ac_caption_combo.currentText(),
            description=self.description_combo.currentText(),
            voucher_header=self.voucher_header_combo.currentText() or None,
            company_id=self.company_id_combo.currentText() or None,
            drcr=self.drcr_combo.currentText() or None,
            rc_amount=self.direct_amount_combo.currentText() or self.amount_combo.currentText() or None,
            lc_amount=self.lc_amount_combo.currentText() or None,
            vendor_id=self.vendor_id_combo.currentText() or None,
            vendor_name=self.vendor_name_combo.currentText() or None,
            customer_id=self.customer_id_combo.currentText() or None,
            customer_name=self.customer_name_combo.currentText() or None,
        )
        field_rules = {}
        if hasattr(self, "_initial_profile") and self._initial_profile is not None:
            field_rules = dict(self._initial_profile.field_rules)
        return IngestProfile(
            profile_name=self.profile_name_edit.text().strip() or "default",
            field_mapping=mapping,
            amount_rules=amount_rules,
            required_field=list(self._required_fields),
            field_rules=field_rules,
            source_type=source_type,
            source_sheet=source_sheet,
        )

def _split_values(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def _parse_number(value: str) -> float | None:
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"
