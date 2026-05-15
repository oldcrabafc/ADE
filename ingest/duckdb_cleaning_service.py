from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from dataset.manifest_service import write_manifest
from dataset.registry_service import register_dataset
from shared.client_router import resolve_client_dir
from shared.errors import validation_error
from shared.schema import AmountRules, DatasetManifest, FieldRule, ImportResult, IngestProfile, LedgerFieldMapping


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def ensure_excel_extension(connection: duckdb.DuckDBPyConnection) -> None:
    try:
        connection.execute("LOAD excel")
        return
    except duckdb.Error:
        connection.execute("INSTALL excel")
        connection.execute("LOAD excel")


def list_excel_sheets(path: Path) -> list[str]:
    connection = duckdb.connect(database=":memory:")
    try:
        ensure_excel_extension(connection)
        try:
            rows = connection.execute("SELECT sheet_name FROM sheet_names(?)", [str(path)]).fetchall()
            return [str(row[0]) for row in rows]
        except duckdb.Error:
            return ["Sheet1"]
    finally:
        connection.close()


def preview_source(
    source_type: str,
    source_path: Path,
    *,
    source_sheet: str | None = None,
    source_table: str = "journal",
    row_limit: int = 10,
) -> tuple[list[str], list[tuple[object, ...]]]:
    connection = duckdb.connect(database=":memory:")
    try:
        table = load_source_to_temp_table(connection, source_type, source_path, source_sheet=source_sheet, source_table=source_table)
        cursor = connection.execute(f"SELECT * FROM {quote_ident(table)} LIMIT ?", [max(0, int(row_limit))])
        columns = [item[0] for item in (cursor.description or [])]
        rows = cursor.fetchall()
        return columns, rows
    finally:
        connection.close()


def load_source_to_temp_table(
    connection: duckdb.DuckDBPyConnection,
    source_type: str,
    source_path: Path,
    *,
    source_sheet: str | None = None,
    source_table: str = "journal",
) -> str:
    if source_type == "excel":
        ensure_excel_extension(connection)
        sheet_sql = f", sheet = {sql_literal(source_sheet)}" if source_sheet else ""
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE source_data AS
            SELECT * FROM read_xlsx({sql_literal(source_path)} , header = true{sheet_sql})
            """
        )
        return "source_data"
    if source_type == "csv":
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE source_data AS
            SELECT * FROM read_csv_auto({sql_literal(source_path)}, header = true)
            """
        )
        return "source_data"
    raise validation_error(f"不支持的来源类型: {source_type}")


class DuckDBCleaningService:
    def build_dataset(
        self,
        *,
        source_type: str,
        source_path: Path,
        client_name: str,
        fiscal_year: int,
        profile: IngestProfile,
        import_batch_id: str | None = None,
        source_sheet: str | None = None,
        source_table: str = "journal",
        dataset_name: str | None = None,
    ) -> ImportResult:
        source_path = Path(source_path)
        if not source_path.exists():
            raise validation_error("来源文件不存在。")
        import_batch_id = import_batch_id or f"auto-{uuid4().hex[:12]}"
        dataset_name = dataset_name or f"{client_name}_{fiscal_year}_{import_batch_id}"
        dataset_dir = resolve_client_dir(client_name) / "datasets" / _safe_name(dataset_name)
        parquet_path = dataset_dir / "ledger.parquet"

        connection = duckdb.connect(database=":memory:")
        try:
            source_table_name = load_source_to_temp_table(
                connection,
                source_type,
                source_path,
                source_sheet=source_sheet,
                source_table=source_table,
            )
            total_rows = int(connection.execute(f"SELECT COUNT(*) FROM {quote_ident(source_table_name)}").fetchone()[0])
            self._create_ledger_table(
                connection,
                source_table_name,
                profile.field_mapping,
                profile.amount_rules,
                profile.field_rules,
                client_name,
                fiscal_year,
                import_batch_id,
                source_path.name,
            )
            stats = self._stats(connection)
            import_errors = self._row_errors(connection)
            dataset_dir.mkdir(parents=True, exist_ok=True)
            connection.execute(f"COPY ledger TO {sql_literal(parquet_path)} (FORMAT PARQUET)")
            manifest = DatasetManifest(
                schema_version=1,
                dataset_name=dataset_name,
                client_name=client_name,
                fiscal_year=fiscal_year,
                row_count=stats["row_count"],
                posting_date_min=stats["posting_date_min"],
                posting_date_max=stats["posting_date_max"],
                created_at=datetime.now().isoformat(timespec="seconds"),
                import_batch_id=import_batch_id,
                profile_name=profile.profile_name,
                ledger_parquet="ledger.parquet",
                source_file=str(source_path),
            )
            manifest_path = write_manifest(manifest, dataset_dir)
            register_dataset(manifest_path)
            return ImportResult(
                task_id=import_batch_id,
                client_name=client_name,
                source_type=source_type,
                source_path=str(source_path),
                source_table=source_table if source_type == "duckdb" else None,
                target_table="ledger",
                fiscal_year=fiscal_year,
                import_batch_id=import_batch_id,
                import_mode="dataset",
                total_rows=total_rows,
                success_rows=stats["row_count"],
                failed_rows=max(0, total_rows - stats["row_count"]),
                duplicate_rows=0,
                positive_rc_amount_rows=stats["positive_rows"],
                negative_rc_amount_rows=stats["negative_rows"],
                zero_rc_amount_rows=stats["zero_rows"],
                field_mapping_report=_field_mapping_report(profile.field_mapping),
                import_errors=import_errors,
                dataset_path=str(parquet_path),
                manifest_path=str(manifest_path),
                posting_date_min=stats["posting_date_min"],
                posting_date_max=stats["posting_date_max"],
                status="success",
            )
        finally:
            connection.close()

    def _create_ledger_table(
        self,
        connection: duckdb.DuckDBPyConnection,
        source_table_name: str,
        mapping: LedgerFieldMapping,
        amount_rules: AmountRules,
        field_rules: dict[str, FieldRule],
        client_name: str,
        fiscal_year: int,
        import_batch_id: str,
        source_file: str,
    ) -> None:
        self._validate_required_columns(connection, source_table_name, mapping, amount_rules)
        raw_select_exprs = [
            "ROW_NUMBER() OVER () AS __source_row",
            f"TRY_CAST({quote_ident(mapping.posting_date)} AS DATE) AS posting_date",
            _prefixed_expr(field_rules, "voucher_id", f"CAST({quote_ident(mapping.voucher_id)} AS VARCHAR)", "voucher_id"),
            _optional_expr(mapping.voucher_header, "voucher_header"),
            _optional_expr(mapping.company_id, "company_id"),
            _prefixed_expr(field_rules, "ac_code", f"CAST({quote_ident(mapping.ac_code)} AS VARCHAR)", "ac_code"),
            f"CAST({quote_ident(mapping.ac_caption)} AS VARCHAR) AS ac_caption",
            _drcr_expr(mapping, amount_rules),
            _amount_expr(amount_rules),
            _optional_numeric_expr(mapping.lc_amount, "lc_amount"),
            _optional_prefixed_expr(field_rules, "vendor_id", mapping.vendor_id, "vendor_id"),
            _optional_expr(mapping.vendor_name, "vendor_name"),
            _optional_prefixed_expr(field_rules, "customer_id", mapping.customer_id, "customer_id"),
            _optional_expr(mapping.customer_name, "customer_name"),
            _prefixed_expr(field_rules, "description", f"CAST({quote_ident(mapping.description)} AS VARCHAR)", "description"),
            f"{sql_literal(client_name)} AS client_name",
            f"{int(fiscal_year)} AS fiscal_year",
            f"{sql_literal(source_file)} AS source_file",
            f"{sql_literal(import_batch_id)} AS import_batch_id",
            "CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS created_at",
        ]
        select_exprs = [
            "posting_date",
            "voucher_id",
            "voucher_header",
            "company_id",
            "ac_code",
            "ac_caption",
            "drcr",
            "rc_amount",
            "lc_amount",
            "vendor_id",
            "vendor_name",
            "customer_id",
            "customer_name",
            "description",
            "client_name",
            "fiscal_year",
            "source_file",
            "import_batch_id",
            "created_at",
        ]
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE ledger_raw AS
            SELECT {", ".join(raw_select_exprs)}
            FROM {quote_ident(source_table_name)}
            """
        )
        invalid_condition = _invalid_row_condition()
        error_message_expr = _error_message_expr()
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE ledger_errors AS
            SELECT
                __source_row AS source_row,
                'ADE-INGEST-ROW' AS error_code,
                {error_message_expr} AS error_message,
                CAST(posting_date AS VARCHAR) AS posting_date,
                voucher_id,
                ac_code,
                ac_caption,
                description,
                CAST(rc_amount AS VARCHAR) AS rc_amount
            FROM ledger_raw
            WHERE {invalid_condition}
            ORDER BY __source_row
            """
        )
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE ledger AS
            SELECT {", ".join(quote_ident(column) for column in select_exprs)}
            FROM ledger_raw
            WHERE NOT ({invalid_condition})
            """
        )

    def _validate_required_columns(
        self,
        connection: duckdb.DuckDBPyConnection,
        source_table_name: str,
        mapping: LedgerFieldMapping,
        amount_rules: AmountRules,
    ) -> None:
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({quote_ident(source_table_name)})").fetchall()}
        required = [mapping.posting_date, mapping.voucher_id, mapping.ac_code, mapping.ac_caption, mapping.description]
        if amount_rules.mode == "direct_signed_amount":
            required.append(amount_rules.direct_amount_field or mapping.rc_amount or "")
        elif amount_rules.mode == "amount_with_drcr":
            required.extend([amount_rules.amount_field or "", amount_rules.drcr_field or mapping.drcr or ""])
        elif amount_rules.mode == "debit_credit_columns":
            required.extend([amount_rules.debit_field or "", amount_rules.credit_field or ""])
        else:
            raise validation_error(f"不支持的金额处理模式: {amount_rules.mode}")
        missing = [column for column in required if column and column not in columns]
        if missing:
            raise validation_error(f"来源文件缺少映射字段: {', '.join(missing)}")

    def _stats(self, connection: duckdb.DuckDBPyConnection) -> dict[str, int | str | None]:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN rc_amount > 0 THEN 1 ELSE 0 END) AS positive_rows,
                SUM(CASE WHEN rc_amount < 0 THEN 1 ELSE 0 END) AS negative_rows,
                SUM(CASE WHEN rc_amount = 0 THEN 1 ELSE 0 END) AS zero_rows,
                CAST(MIN(posting_date) AS VARCHAR) AS posting_date_min,
                CAST(MAX(posting_date) AS VARCHAR) AS posting_date_max
            FROM ledger
            """
        ).fetchone()
        return {
            "row_count": int(row[0] or 0),
            "positive_rows": int(row[1] or 0),
            "negative_rows": int(row[2] or 0),
            "zero_rows": int(row[3] or 0),
            "posting_date_min": row[4],
            "posting_date_max": row[5],
        }

    def _row_errors(self, connection: duckdb.DuckDBPyConnection, limit: int = 200) -> list[dict[str, object]]:
        rows = connection.execute(
            """
            SELECT
                source_row,
                error_code,
                error_message,
                posting_date,
                voucher_id,
                ac_code,
                ac_caption,
                description,
                rc_amount
            FROM ledger_errors
            ORDER BY source_row
            LIMIT ?
            """,
            [max(0, int(limit))],
        ).fetchall()
        columns = [
            "source_row",
            "error_code",
            "error_message",
            "posting_date",
            "voucher_id",
            "ac_code",
            "ac_caption",
            "description",
            "rc_amount",
        ]
        return [
            {column: value for column, value in zip(columns, row)}
            for row in rows
        ]


def _optional_expr(source: str | None, target: str) -> str:
    if not source:
        return f"CAST(NULL AS VARCHAR) AS {quote_ident(target)}"
    return f"CAST({quote_ident(source)} AS VARCHAR) AS {quote_ident(target)}"


def _optional_numeric_expr(source: str | None, target: str) -> str:
    if not source:
        return f"CAST(NULL AS DECIMAL(18, 2)) AS {quote_ident(target)}"
    return f"TRY_CAST({quote_ident(source)} AS DECIMAL(18, 2)) AS {quote_ident(target)}"


def _optional_prefixed_expr(
    field_rules: dict[str, FieldRule],
    field_name: str,
    source: str | None,
    target: str,
) -> str:
    if not source:
        return f"CAST(NULL AS VARCHAR) AS {quote_ident(target)}"
    base_expr = f"CAST({quote_ident(source)} AS VARCHAR)"
    return _prefixed_expr(field_rules, field_name, base_expr, target)


def _prefixed_expr(
    field_rules: dict[str, FieldRule],
    field_name: str,
    base_expr: str,
    target: str,
) -> str:
    rule = field_rules.get(field_name)
    if rule is None or not rule.prefix:
        return f"{base_expr} AS {quote_ident(target)}"
    prefix_literal = sql_literal(rule.prefix)
    return (
        "CASE "
        f"WHEN NULLIF(TRIM({base_expr}), '') IS NULL THEN NULL "
        f"ELSE {prefix_literal} || TRIM({base_expr}) "
        f"END AS {quote_ident(target)}"
    )


def _drcr_expr(mapping: LedgerFieldMapping, amount_rules: AmountRules) -> str:
    source = mapping.drcr or amount_rules.drcr_field
    if not source:
        return "CAST(NULL AS VARCHAR) AS drcr"
    return f"CAST({quote_ident(source)} AS VARCHAR) AS drcr"


def _amount_expr(amount_rules: AmountRules) -> str:
    if amount_rules.mode == "direct_signed_amount":
        source = amount_rules.direct_amount_field
        return f"TRY_CAST({quote_ident(source or '')} AS DECIMAL(18, 2)) AS rc_amount"
    if amount_rules.mode == "amount_with_drcr":
        amount = f"ABS(TRY_CAST({quote_ident(amount_rules.amount_field or '')} AS DECIMAL(18, 2)))"
        drcr = f"CAST({quote_ident(amount_rules.drcr_field or '')} AS VARCHAR)"
        debit_values = ", ".join(sql_literal(value) for value in amount_rules.debit_values)
        credit_values = ", ".join(sql_literal(value) for value in amount_rules.credit_values)
        return (
            "CASE "
            f"WHEN {drcr} IN ({debit_values}) THEN {amount} "
            f"WHEN {drcr} IN ({credit_values}) THEN -{amount} "
            "ELSE NULL END AS rc_amount"
        )
    if amount_rules.mode == "debit_credit_columns":
        debit = f"COALESCE(ABS(TRY_CAST({quote_ident(amount_rules.debit_field or '')} AS DECIMAL(18, 2))), 0)"
        credit = f"COALESCE(ABS(TRY_CAST({quote_ident(amount_rules.credit_field or '')} AS DECIMAL(18, 2))), 0)"
        return f"({debit} - {credit}) AS rc_amount"
    raise validation_error(f"不支持的金额处理模式: {amount_rules.mode}")


def _field_mapping_report(mapping: LedgerFieldMapping) -> list[dict[str, str]]:
    report: list[dict[str, str]] = []
    for key, value in asdict(mapping).items():
        report.append(
            {
                "source_field": value or "",
                "target_field": key,
                "rule": "direct_mapping" if value else "unmapped",
                "status": "success" if value else "optional_blank",
            }
        )
    return report


def _invalid_row_condition() -> str:
    return """
    NULLIF(TRIM(voucher_id), '') IS NULL
    OR NULLIF(TRIM(ac_code), '') IS NULL
    OR NULLIF(TRIM(ac_caption), '') IS NULL
    OR rc_amount IS NULL
    """.strip()


def _error_message_expr() -> str:
    return """
    TRIM(BOTH '; ' FROM
        (CASE WHEN NULLIF(TRIM(voucher_id), '') IS NULL THEN 'voucher_id 为空; ' ELSE '' END) ||
        (CASE WHEN NULLIF(TRIM(ac_code), '') IS NULL THEN 'ac_code 为空; ' ELSE '' END) ||
        (CASE WHEN NULLIF(TRIM(ac_caption), '') IS NULL THEN 'ac_caption 为空; ' ELSE '' END) ||
        (CASE WHEN rc_amount IS NULL THEN 'rc_amount 无法转换或借贷标识无法识别; ' ELSE '' END)
    )
    """.strip()


def _safe_name(value: str) -> str:
    keep = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "ledger_dataset"
