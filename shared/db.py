from __future__ import annotations

import duckdb

from .client_router import resolve_client_db_path
from .schema import IMPORT_BATCHES_DDL, IMPORT_ERRORS_DDL, IMPORT_REPORTS_DDL, JOURNAL_DDL


class DatabaseManager:
    def __init__(self, client_name: str, read_only: bool = False) -> None:
        self.client_name = client_name
        self.db_path = resolve_client_db_path(client_name)
        self.read_only = read_only

    def connect(self) -> duckdb.DuckDBPyConnection:
        connection = duckdb.connect(str(self.db_path), read_only=self.read_only)
        if not self.read_only:
            self.initialize(connection)
        return connection

    @staticmethod
    def initialize(connection: duckdb.DuckDBPyConnection) -> None:
        connection.execute(JOURNAL_DDL)
        connection.execute(IMPORT_BATCHES_DDL)
        connection.execute(IMPORT_ERRORS_DDL)
        connection.execute(IMPORT_REPORTS_DDL)
