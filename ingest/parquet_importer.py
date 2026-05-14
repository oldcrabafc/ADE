from __future__ import annotations

from pathlib import Path

from ingest.duckdb_cleaning_service import preview_source


def load_parquet(path: Path, row_limit: int | None = None) -> dict[str, object]:
    columns, rows = preview_source("parquet", path, row_limit=row_limit or 10)
    return {"columns": columns, "rows": rows}
