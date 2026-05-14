from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from dataset.manifest_service import read_manifest
from dataset.registry_service import register_dataset
from shared.errors import validation_error


REQUIRED_LEDGER_FIELDS = {
    "posting_date",
    "voucher_id",
    "ac_code",
    "ac_caption",
    "rc_amount",
    "description",
}


def resolve_ledger_parquet(path: Path) -> Path:
    if path.suffix.lower() == ".toml":
        manifest = read_manifest(path)
        parquet_path = Path(manifest.ledger_parquet)
        if not parquet_path.is_absolute():
            parquet_path = path.parent / parquet_path
        return parquet_path
    return path


def resolve_manifest_path(path: Path) -> Path | None:
    if path.suffix.lower() == ".toml":
        return path
    candidate = path.parent / "dataset.toml"
    return candidate if candidate.exists() else None


def inspect_ledger_parquet(path: Path) -> dict[str, str]:
    parquet_path = resolve_ledger_parquet(path)
    if not parquet_path.exists():
        raise validation_error("ledger parquet 文件不存在。")
    connection = duckdb.connect(database=":memory:")
    try:
        _create_ledger_views(connection, parquet_path)
        columns = {row[1] for row in connection.execute("PRAGMA table_info('ledger')").fetchall()}
        row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS row_count,
                CAST(MIN(posting_date) AS VARCHAR) AS posting_date_min,
                CAST(MAX(posting_date) AS VARCHAR) AS posting_date_max,
                CAST(ANY_VALUE({_optional_value_expr(columns, "client_name", "VARCHAR")}) AS VARCHAR) AS client_name,
                CAST(ANY_VALUE({_optional_value_expr(columns, "fiscal_year", "INTEGER")}) AS VARCHAR) AS fiscal_year
            FROM ledger
            """
        ).fetchone()
        return {
            "dataset_name": parquet_path.stem,
            "dataset_path": str(parquet_path),
            "row_count": str(row[0] or 0),
            "posting_date_min": str(row[1]) if row[1] is not None else "",
            "posting_date_max": str(row[2]) if row[2] is not None else "",
            "client_name": str(row[3]) if row[3] is not None else "",
            "fiscal_year": str(row[4]) if row[4] is not None else "",
        }
    finally:
        connection.close()


def connect_dataset(path: Path) -> duckdb.DuckDBPyConnection:
    parquet_path = resolve_ledger_parquet(path)
    if not parquet_path.exists():
        raise validation_error("ledger parquet 文件不存在。")
    connection = duckdb.connect(database=":memory:")
    _create_ledger_views(connection, parquet_path)
    manifest_path = resolve_manifest_path(path)
    if manifest_path is not None:
        register_dataset(manifest_path)
    return connection


def _create_ledger_views(connection: duckdb.DuckDBPyConnection, parquet_path: Path) -> None:
    parquet_literal = "'" + str(parquet_path).replace("'", "''") + "'"
    connection.execute(f"CREATE OR REPLACE VIEW ledger_source AS SELECT * FROM read_parquet({parquet_literal})")
    table_info = connection.execute("PRAGMA table_info('ledger_source')").fetchall()
    columns = {row[1] for row in table_info}
    missing = sorted(REQUIRED_LEDGER_FIELDS - columns)
    if missing:
        raise validation_error(f"ledger parquet 缺少 required 字段: {', '.join(missing)}")
    select_exprs = []
    for row in table_info:
        column_name = row[1]
        column_type = str(row[2]).upper()
        if column_name == "created_at" and "WITH TIME ZONE" in column_type:
            select_exprs.append('"created_at"::TIMESTAMP AS "created_at"')
        else:
            select_exprs.append('"' + str(column_name).replace('"', '""') + '"')
    connection.execute(f"CREATE OR REPLACE VIEW ledger AS SELECT {', '.join(select_exprs)} FROM ledger_source")
    lc_amount_expr = "lc_amount" if "lc_amount" in columns else "CAST(NULL AS DECIMAL(18, 2)) AS lc_amount"
    connection.execute(
        f"""
        CREATE OR REPLACE VIEW journal AS
        SELECT
            posting_date AS book_date,
            voucher_id AS voucher_no,
            ac_code,
            ac_caption AS ac_name,
            description AS summary,
            rc_amount,
            {lc_amount_expr},
            {_optional_column_expr(columns, "client_name", "VARCHAR")},
            {_optional_column_expr(columns, "fiscal_year", "INTEGER")},
            {_optional_column_expr(columns, "source_file", "VARCHAR")},
            {_optional_column_expr(columns, "import_batch_id", "VARCHAR")},
            {_optional_column_expr(columns, "created_at", "TIMESTAMP")}
        FROM ledger
        """
    )


def _optional_column_expr(columns: set[Any], column: str, sql_type: str) -> str:
    if column in columns:
        return quote_ident(column)
    return f"CAST(NULL AS {sql_type}) AS {quote_ident(column)}"


def _optional_value_expr(columns: set[Any], column: str, sql_type: str) -> str:
    if column in columns:
        return quote_ident(column)
    return f"CAST(NULL AS {sql_type})"


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'
