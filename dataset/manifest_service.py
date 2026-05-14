from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import tomllib

from shared.schema import DatasetManifest


def _format_toml_value(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def write_manifest(manifest: DatasetManifest, dataset_dir: Path) -> Path:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    path = dataset_dir / "dataset.toml"
    lines = [f"{key} = {_format_toml_value(value)}" for key, value in asdict(manifest).items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def read_manifest(path: Path) -> DatasetManifest:
    with path.open("rb") as file:
        data = tomllib.load(file)
    return DatasetManifest(
        schema_version=int(data.get("schema_version", 1)),
        dataset_name=str(data["dataset_name"]),
        client_name=str(data["client_name"]),
        fiscal_year=int(data["fiscal_year"]),
        row_count=int(data.get("row_count", 0)),
        posting_date_min=str(data["posting_date_min"]) if data.get("posting_date_min") else None,
        posting_date_max=str(data["posting_date_max"]) if data.get("posting_date_max") else None,
        created_at=str(data.get("created_at", "")),
        import_batch_id=str(data.get("import_batch_id", "")),
        profile_name=str(data.get("profile_name", "")),
        ledger_parquet=str(data.get("ledger_parquet", "ledger.parquet")),
        source_file=str(data["source_file"]) if data.get("source_file") else None,
    )
