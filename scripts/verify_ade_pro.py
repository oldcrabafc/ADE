from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import duckdb

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataset.manifest_service import read_manifest, write_manifest
from dataset.package_service import package_dataset
from dataset.query_dataset import inspect_ledger_parquet
from ingest.client_profile_service import find_profile, save_profile
from ingest.import_service import ImportService
from query.query_service import QueryService
from query.sql_history_service import SQL_HISTORY_PATH, list_sql_history, record_sql_history
from shared.client_router import resolve_client_dir
from shared.schema import AmountRules, DatasetManifest, FieldMapping, ImportRequest, IngestProfile, LedgerFieldMapping


TMP_DIR = ROOT / "data" / "_tmp_verify_ade_pro"
CLIENTS = [
    "VerifyDirectClient",
    "VerifyDrcrClient",
    "VerifyDebitCreditClient",
    "VerifyErrorsClient",
    "VerifyProfileClient",
]


def main() -> None:
    cleanup()
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        verify_direct_import_dataset_query_and_package()
        verify_amount_with_drcr()
        verify_debit_credit_columns()
        verify_import_errors()
        verify_profile_save_and_match()
        verify_sql_history()
        verify_bare_parquet_inspect_and_query()
        print("ADE Pro verification passed.")
    finally:
        cleanup()


def verify_direct_import_dataset_query_and_package() -> None:
    source = TMP_DIR / "direct.csv"
    source.write_text(
        "posting_date,voucher_id,ac_code,ac_caption,description,amount\n"
        "2024-01-02,V001,1001,Cash,Opening balance,100.50\n"
        "2024-01-03,V002,6001,Expense,Office supplies,-25.25\n",
        encoding="utf-8",
    )
    profile = _profile_direct()
    result = ImportService().import_to_client_db(
        _request("VerifyDirectClient", source, profile, "Verify Direct Dataset")
    )
    manifest = read_manifest(Path(result.manifest_path))
    query_result = QueryService().run_sql(Path(result.manifest_path), "SELECT COUNT(*) AS n, SUM(rc_amount) AS total FROM ledger")
    journal_result = QueryService().run_sql(Path(result.manifest_path), "SELECT voucher_no, ac_name FROM journal ORDER BY voucher_no")
    package_path = TMP_DIR / "direct_dataset.zip"
    package_dataset(Path(result.manifest_path), package_path)
    with ZipFile(package_path) as archive:
        names = sorted(archive.namelist())

    assert Path(result.dataset_path).parent.name == "Verify_Direct_Dataset"
    assert manifest.dataset_name == "Verify Direct Dataset"
    assert result.success_rows == 2 and result.failed_rows == 0
    assert query_result.rows[0][0] == 2
    assert str(query_result.rows[0][1]) in {"75.25", "75.2500"}
    assert journal_result.rows == [("V001", "Cash"), ("V002", "Expense")]
    assert names == ["README.txt", "dataset.toml", "ledger.parquet"]


def verify_amount_with_drcr() -> None:
    source = TMP_DIR / "drcr.csv"
    source.write_text(
        "posting_date,voucher_id,ac_code,ac_caption,description,drcr,amount\n"
        "2024-01-02,V001,1001,Cash,debit,借,100\n"
        "2024-01-03,V002,1001,Cash,credit,贷,200\n",
        encoding="utf-8",
    )
    profile = IngestProfile(
        profile_name="verify-drcr",
        source_type="csv",
        field_mapping=LedgerFieldMapping(
            posting_date="posting_date",
            voucher_id="voucher_id",
            ac_code="ac_code",
            ac_caption="ac_caption",
            description="description",
            drcr="drcr",
            rc_amount="amount",
        ),
        amount_rules=AmountRules(mode="amount_with_drcr", amount_field="amount", drcr_field="drcr", debit_values=["借"], credit_values=["贷"]),
    )
    result = ImportService().import_to_client_db(_request("VerifyDrcrClient", source, profile, "Verify Drcr Dataset"))
    rows = QueryService().run_sql(Path(result.manifest_path), "SELECT voucher_id, rc_amount FROM ledger ORDER BY voucher_id").rows
    assert [(row[0], str(row[1])) for row in rows] == [("V001", "100.00"), ("V002", "-200.00")]


def verify_debit_credit_columns() -> None:
    source = TMP_DIR / "debit_credit.csv"
    source.write_text(
        "posting_date,voucher_id,ac_code,ac_caption,description,debit,credit\n"
        "2024-01-02,V001,1001,Cash,debit,300,\n"
        "2024-01-03,V002,1001,Cash,credit,,80\n",
        encoding="utf-8",
    )
    profile = IngestProfile(
        profile_name="verify-debit-credit",
        source_type="csv",
        field_mapping=LedgerFieldMapping(
            posting_date="posting_date",
            voucher_id="voucher_id",
            ac_code="ac_code",
            ac_caption="ac_caption",
            description="description",
        ),
        amount_rules=AmountRules(mode="debit_credit_columns", debit_field="debit", credit_field="credit"),
    )
    result = ImportService().import_to_client_db(_request("VerifyDebitCreditClient", source, profile, "Verify Debit Credit Dataset"))
    total = QueryService().run_sql(Path(result.manifest_path), "SELECT SUM(rc_amount) FROM ledger").rows[0][0]
    assert str(total) in {"220.00", "220.0000"}


def verify_import_errors() -> None:
    source = TMP_DIR / "errors.csv"
    source.write_text(
        "posting_date,voucher_id,ac_code,ac_caption,description,amount\n"
        "2024-01-02,V001,1001,Cash,valid,100\n"
        "bad-date,V002,1001,Cash,bad date,200\n"
        "2024-01-03,,1001,Cash,missing voucher,300\n"
        "2024-01-04,V004,1001,Cash,,400\n"
        "2024-01-05,V005,1001,Cash,bad amount,not-a-number\n",
        encoding="utf-8",
    )
    result = ImportService().import_to_client_db(
        _request("VerifyErrorsClient", source, _profile_direct(), "Verify Errors Dataset")
    )
    messages = "\n".join(str(item["error_message"]) for item in result.import_errors)
    assert result.total_rows == 5 and result.success_rows == 1 and result.failed_rows == 4
    assert "posting_date" in messages and "voucher_id" in messages and "description" in messages and "rc_amount" in messages


def verify_profile_save_and_match() -> None:
    profile = _profile_direct()
    profile.profile_name = "verify-profile"
    save_profile("VerifyProfileClient", profile)
    matched = find_profile(
        "VerifyProfileClient",
        "csv",
        None,
        ["posting_date", "voucher_id", "ac_code", "ac_caption", "description", "amount"],
    )
    assert matched is not None and matched.profile_name == "verify-profile"


def verify_sql_history() -> None:
    if SQL_HISTORY_PATH.exists():
        SQL_HISTORY_PATH.unlink()
    sql = "SELECT * FROM ledger LIMIT 1"
    record_sql_history(sql, TMP_DIR / "dataset.toml")
    entries = list_sql_history()
    assert len(entries) == 1
    assert entries[0]["sql_text"] == sql


def verify_bare_parquet_inspect_and_query() -> None:
    parquet_path = TMP_DIR / "bare_ledger.parquet"
    connection = duckdb.connect(database=":memory:")
    try:
        connection.execute(
            """
            CREATE TABLE ledger AS
            SELECT * FROM (VALUES
                (DATE '2024-07-01', 'V001', '1001', 'Cash', CAST(10.00 AS DECIMAL(18,2)), 'bare row')
            ) AS t(posting_date, voucher_id, ac_code, ac_caption, rc_amount, description)
            """
        )
        connection.execute(f"COPY ledger TO '{str(parquet_path).replace(chr(39), chr(39) * 2)}' (FORMAT PARQUET)")
    finally:
        connection.close()
    summary = inspect_ledger_parquet(parquet_path)
    query_result = QueryService().run_sql(parquet_path, "SELECT voucher_no, client_name FROM journal")
    package_path = TMP_DIR / "bare.zip"
    package_dataset(parquet_path, package_path)
    with ZipFile(package_path) as archive:
        names = sorted(archive.namelist())
    assert summary["row_count"] == "1"
    assert summary["client_name"] == ""
    assert query_result.rows == [("V001", None)]
    assert names == ["README.txt", "bare_ledger.parquet"]


def _profile_direct() -> IngestProfile:
    return IngestProfile(
        profile_name="verify-direct",
        source_type="csv",
        field_mapping=LedgerFieldMapping(
            posting_date="posting_date",
            voucher_id="voucher_id",
            ac_code="ac_code",
            ac_caption="ac_caption",
            description="description",
            rc_amount="amount",
        ),
        amount_rules=AmountRules(mode="direct_signed_amount", direct_amount_field="amount"),
    )


def _request(client_name: str, source: Path, profile: IngestProfile, dataset_name: str) -> ImportRequest:
    return ImportRequest(
        client_name=client_name,
        source_type="csv",
        source_path=source,
        fiscal_year=2024,
        field_mapping=FieldMapping(
            book_date="posting_date",
            voucher_no="voucher_id",
            ac_name="ac_caption",
            ac_code="ac_code",
            summary="description",
            direct_amount_field="amount",
        ),
        import_mode="new",
        profile=profile,
        dataset_name=dataset_name,
    )


def cleanup() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    for client_name in CLIENTS:
        client_dir = resolve_client_dir(client_name)
        if client_dir.exists():
            shutil.rmtree(client_dir)
    if SQL_HISTORY_PATH.exists():
        SQL_HISTORY_PATH.unlink()
    registry_path = ROOT / "data" / "registry.toml"
    if registry_path.exists():
        registry_path.unlink()
    (ROOT / "data" / "clients").mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
