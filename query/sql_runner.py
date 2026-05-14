from __future__ import annotations

from pathlib import Path

import duckdb

from dataset.query_dataset import connect_dataset
from shared.db import DatabaseManager
from shared.errors import validation_error
from shared.schema import QueryResult


def _validate_sql(sql_text: str) -> None:
    stripped = sql_text.strip().lower()
    if not stripped:
        raise validation_error("SQL 不能为空。")
    if not (stripped.startswith("select") or stripped.startswith("with") or stripped.startswith("show")):
        raise validation_error("当前版本仅允许执行查询类 SQL。")


def _fetch_query_result(connection: duckdb.DuckDBPyConnection, sql_text: str) -> QueryResult:
    cursor = connection.execute(sql_text)
    columns = [item[0] for item in (cursor.description or [])]
    rows = cursor.fetchall()
    return QueryResult(columns=columns, rows=rows)


def execute_query_on_dataset(dataset_path: Path, sql_text: str) -> QueryResult:
    _validate_sql(sql_text)
    connection = connect_dataset(dataset_path)
    try:
        return _fetch_query_result(connection, sql_text)
    except duckdb.Error as exc:
        raise validation_error(str(exc)) from exc
    finally:
        connection.close()


def execute_query_on_db(db_path: Path, sql_text: str) -> QueryResult:
    _validate_sql(sql_text)
    if not db_path.exists():
        raise validation_error("DuckDB 文件不存在。")

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        return _fetch_query_result(connection, sql_text)
    except duckdb.Error as exc:
        raise validation_error(str(exc)) from exc
    finally:
        connection.close()


def execute_query(client_name: str, sql_text: str) -> QueryResult:
    _validate_sql(sql_text)

    connection = DatabaseManager(client_name, read_only=False).connect()
    try:
        return _fetch_query_result(connection, sql_text)
    except duckdb.Error as exc:
        raise validation_error(str(exc)) from exc
    finally:
        connection.close()
