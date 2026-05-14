from __future__ import annotations

from pathlib import Path

from query.export_service import export_query_result_to_excel
from query.query_builder import build_ledger_query
from query.sql_history_service import built_in_sql_templates, list_sql_history, record_sql_history
from query.sql_runner import execute_query_on_dataset
from shared.schema import ExportRequest, ExportResult, QueryResult


class QueryService:
    def sql_templates(self) -> dict[str, str]:
        return built_in_sql_templates()

    def sql_history(self) -> list[dict[str, str]]:
        return list_sql_history()

    def record_sql_history(self, dataset_path: Path, sql_text: str) -> None:
        record_sql_history(sql_text, dataset_path)

    def build_visual_query(self, filters: dict[str, str]) -> str:
        return build_ledger_query(filters)

    def run_sql(self, dataset_path: Path, sql_text: str) -> QueryResult:
        return execute_query_on_dataset(dataset_path, sql_text)

    def export_sql_result(
        self,
        dataset_path: Path,
        sql_text: str,
        output_path: Path,
        max_rows_per_sheet: int = 10_000,
    ) -> ExportResult:
        result = self.run_sql(dataset_path, sql_text)
        return export_query_result_to_excel(
            result,
            ExportRequest(
                client_name=dataset_path.stem,
                sql_text=sql_text,
                output_path=output_path,
                max_rows_per_sheet=max_rows_per_sheet,
            ),
        )
