from __future__ import annotations

from pathlib import Path

from ingest.duckdb_cleaning_service import DuckDBCleaningService, list_excel_sheets, preview_source
from shared.errors import ADEError, validation_error
from shared.schema import ImportRequest, ImportResult, RollbackResult


class ImportService:
    _SUPPORTED_SOURCE_TYPES = {"excel", "csv"}

    def __init__(self) -> None:
        self.cleaning_service = DuckDBCleaningService()

    def preview_columns(
        self,
        source_type: str,
        source_path: Path,
        source_table: str = "journal",
        source_sheet: str | None = None,
    ) -> list[str]:
        self._validate_source_type(source_type)
        columns, _ = preview_source(
            source_type,
            source_path,
            source_table=source_table,
            source_sheet=source_sheet,
            row_limit=0,
        )
        return [str(column) for column in columns]

    def list_source_sheets(self, source_type: str, source_path: Path) -> list[str]:
        self._validate_source_type(source_type)
        if source_type != "excel":
            return []
        return list_excel_sheets(source_path)

    def preview_rows(
        self,
        source_type: str,
        source_path: Path,
        source_table: str = "journal",
        source_sheet: str | None = None,
        row_limit: int = 10,
    ) -> dict[str, object]:
        self._validate_source_type(source_type)
        columns, rows = preview_source(
            source_type,
            source_path,
            source_table=source_table,
            source_sheet=source_sheet,
            row_limit=row_limit,
        )
        return {
            "columns": [str(column) for column in columns],
            "rows": [["" if value is None else str(value) for value in row] for row in rows],
        }

    def import_to_client_db(self, request: ImportRequest) -> ImportResult:
        self._validate_source_type(request.source_type)
        if request.profile is None:
            raise validation_error("缺少最终导入配置：profile。请先确认字段映射与金额规则。")
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise validation_error("来源文件不存在。")
        if request.import_mode not in {"new", "append"}:
            raise validation_error("导入模式仅支持 new 或 append。")

        return self.cleaning_service.build_dataset(
            source_type=request.source_type,
            source_path=source_path,
            client_name=request.client_name,
            fiscal_year=request.fiscal_year,
            profile=request.profile,
            import_batch_id=request.import_batch_id,
            source_sheet=request.source_sheet,
            source_table=request.source_table,
            dataset_name=request.dataset_name,
        )

    def rollback_import_batch(self, client_name: str, fiscal_year: int, import_batch_id: str) -> RollbackResult:
        raise ADEError("ADE-IMP-008", "当前 Parquet 数据集导入模式暂不支持按批次回滚。")

    def _validate_source_type(self, source_type: str) -> None:
        if source_type not in self._SUPPORTED_SOURCE_TYPES:
            raise validation_error("当前仅支持 Excel 和 CSV 导入。")
