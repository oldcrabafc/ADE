from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from dataset.manifest_service import read_manifest
from shared.schema import ImportResult


class ImportReportView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)

    def show_result(self, result: ImportResult) -> None:
        payload = {
            "task_id": result.task_id,
            "client_name": result.client_name,
            "source_type": result.source_type,
            "source_path": result.source_path,
            "fiscal_year": result.fiscal_year,
            "import_mode": result.import_mode,
            "total_rows": result.total_rows,
            "success_rows": result.success_rows,
            "failed_rows": result.failed_rows,
            "duplicate_rows": result.duplicate_rows,
            "positive_rows": result.positive_rc_amount_rows,
            "negative_rows": result.negative_rc_amount_rows,
            "zero_rows": result.zero_rc_amount_rows,
            "field_mapping_report": result.field_mapping_report,
            "import_errors": result.import_errors,
            "dataset_path": result.dataset_path,
            "manifest_path": result.manifest_path,
            "dataset_name": _dataset_name_from_manifest(result.manifest_path),
            "posting_date_min": result.posting_date_min,
            "posting_date_max": result.posting_date_max,
        }
        self.editor.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))


def _dataset_name_from_manifest(manifest_path: str | None) -> str | None:
    if not manifest_path:
        return None
    try:
        return read_manifest(Path(manifest_path)).dataset_name
    except Exception:
        return None
