from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FieldMapping:
    book_date: str
    voucher_no: str
    ac_name: str
    ac_code: str | None = None
    summary: str | None = None
    debit_field: str | None = None
    credit_field: str | None = None
    direct_amount_field: str | None = None


@dataclass(slots=True)
class AmountRules:
    mode: str = "direct_signed_amount"
    direct_amount_field: str | None = None
    amount_field: str | None = None
    debit_field: str | None = None
    credit_field: str | None = None
    drcr_field: str | None = None
    debit_values: list[str] = field(default_factory=lambda: ["借", "D", "Debit", "S"])
    credit_values: list[str] = field(default_factory=lambda: ["贷", "C", "Credit", "H"])
    sign_rule: str = "debit_positive"


@dataclass(slots=True)
class LedgerFieldMapping:
    posting_date: str = ""
    voucher_id: str = ""
    ac_code: str = ""
    ac_caption: str = ""
    description: str = ""
    voucher_header: str | None = None
    company_id: str | None = None
    drcr: str | None = None
    rc_amount: str | None = None
    lc_amount: str | None = None
    vendor_id: str | None = None
    vendor_name: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    department: str | None = None
    employee_id: str | None = None
    employee_name: str | None = None
    currency: str | None = None
    document_type: str | None = None
    posting_period: str | None = None
    source_system: str | None = None


@dataclass(slots=True)
class IngestProfile:
    profile_name: str
    field_mapping: LedgerFieldMapping
    amount_rules: AmountRules
    source_type: str = "excel"
    source_sheet: str | None = None


@dataclass(slots=True)
class DatasetManifest:
    schema_version: int
    dataset_name: str
    client_name: str
    fiscal_year: int
    row_count: int
    posting_date_min: str | None
    posting_date_max: str | None
    created_at: str
    import_batch_id: str
    profile_name: str
    ledger_parquet: str
    source_file: str | None = None


@dataclass(slots=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]

    def __len__(self) -> int:
        return len(self.rows)


@dataclass(slots=True)
class ImportRequest:
    client_name: str
    source_type: str
    source_path: Path
    fiscal_year: int
    field_mapping: FieldMapping
    import_mode: str = "append"
    duplicate_mode: str = "mark"
    import_batch_id: str | None = None
    source_sheet: str | None = None
    source_table: str = "journal"
    target_table: str = "journal"
    profile: IngestProfile | None = None
    dataset_name: str | None = None


@dataclass(slots=True)
class ImportResult:
    task_id: str
    client_name: str
    source_type: str
    source_path: str
    source_table: str | None
    target_table: str
    fiscal_year: int
    import_batch_id: str | None
    import_mode: str
    total_rows: int
    success_rows: int
    failed_rows: int
    duplicate_rows: int
    positive_rc_amount_rows: int
    negative_rc_amount_rows: int
    zero_rc_amount_rows: int
    dataset_path: str | None = None
    manifest_path: str | None = None
    posting_date_min: str | None = None
    posting_date_max: str | None = None
    field_mapping_report: list[dict[str, Any]] = field(default_factory=list)
    import_errors: list[dict[str, Any]] = field(default_factory=list)
    amount_sign_rule: str = "debit_positive"
    status: str = "success"
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class RollbackResult:
    client_name: str
    fiscal_year: int
    import_batch_id: str
    deleted_journal_rows: int
    deleted_error_rows: int
    deleted_report_rows: int
    deleted_batch_rows: int
    status: str = "success"
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class ExportRequest:
    client_name: str
    sql_text: str
    output_path: Path
    max_rows_per_sheet: int = 10_000


@dataclass(slots=True)
class ExportResult:
    client_name: str
    file_path: str
    sheet_count: int
    total_rows: int
    split_applied: bool
    status: str = "success"
    error_code: str | None = None
    error_message: str | None = None


JOURNAL_DDL = """
CREATE TABLE IF NOT EXISTS journal (
    row_id BIGINT,
    fiscal_year INTEGER NOT NULL,
    month INTEGER,
    book_date DATE NOT NULL,
    voucher_no TEXT NOT NULL,
    ac_code TEXT,
    ac_name TEXT NOT NULL,
    rc_amount DECIMAL(18, 2) NOT NULL,
    lc_amount DECIMAL(18, 2),
    local_currency TEXT,
    summary TEXT,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    source_file TEXT NOT NULL,
    client_name TEXT NOT NULL,
    import_batch_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

IMPORT_BATCHES_DDL = """
CREATE TABLE IF NOT EXISTS import_batches (
    batch_key TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    import_batch_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_table TEXT,
    total_rows INTEGER NOT NULL,
    success_rows INTEGER NOT NULL,
    failed_rows INTEGER NOT NULL,
    duplicate_rows INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

IMPORT_ERRORS_DDL = """
CREATE TABLE IF NOT EXISTS import_errors (
    error_id BIGINT,
    import_batch_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    source_row INTEGER,
    error_code TEXT NOT NULL,
    error_message TEXT NOT NULL,
    raw_payload TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

IMPORT_REPORTS_DDL = """
CREATE TABLE IF NOT EXISTS import_reports (
    task_id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    import_batch_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_table TEXT,
    total_rows INTEGER NOT NULL,
    success_rows INTEGER NOT NULL,
    failed_rows INTEGER NOT NULL,
    duplicate_rows INTEGER NOT NULL,
    positive_rows INTEGER NOT NULL,
    negative_rows INTEGER NOT NULL,
    zero_rows INTEGER NOT NULL,
    report_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""
