from __future__ import annotations

import json

from shared.schema import ImportResult


def import_result_to_json(result: ImportResult) -> str:
    return json.dumps(
        {
            "task_id": result.task_id,
            "client_name": result.client_name,
            "source_type": result.source_type,
            "source_path": result.source_path,
            "source_table": result.source_table,
            "target_table": result.target_table,
            "fiscal_year": result.fiscal_year,
            "import_batch_id": result.import_batch_id,
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
            "status": result.status,
            "error_code": result.error_code,
            "error_message": result.error_message,
        },
        ensure_ascii=False,
        indent=2,
    )
