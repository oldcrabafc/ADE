from __future__ import annotations

from pathlib import Path

from ingest.duckdb_cleaning_service import list_excel_sheets, preview_source


def load_excel(path: Path, sheet_name: str | int = 0, row_limit: int | None = None) -> dict[str, object]:
    sheet = None if isinstance(sheet_name, int) else sheet_name
    columns, rows = preview_source("excel", path, source_sheet=sheet, row_limit=row_limit or 10)
    return {"columns": columns, "rows": rows}
