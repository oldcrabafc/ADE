from __future__ import annotations

from datetime import datetime
from pathlib import Path

import tomllib

from shared.constants import DATA_DIR
from dataset.manifest_service import read_manifest


REGISTRY_PATH = DATA_DIR / "registry.toml"


def register_dataset(manifest_path: Path) -> None:
    manifest_path = manifest_path.resolve()
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = list_recent_datasets()
    manifest_text = str(manifest_path)
    entries = [entry for entry in entries if entry.get("dataset_manifest") != manifest_text]
    entries.insert(
        0,
        {
            "dataset_manifest": manifest_text,
            "last_opened_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    _write_entries(entries[:20])


def list_recent_datasets() -> list[dict[str, str]]:
    if not REGISTRY_PATH.exists():
        return []
    with REGISTRY_PATH.open("rb") as file:
        data = tomllib.load(file)
    raw_entries = data.get("datasets", [])
    if not isinstance(raw_entries, list):
        return []
    return [{str(k): str(v) for k, v in entry.items()} for entry in raw_entries if isinstance(entry, dict)]


def list_recent_dataset_summaries() -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    for entry in list_recent_datasets():
        manifest_path = Path(entry.get("dataset_manifest", ""))
        if not manifest_path.exists():
            summaries.append(
                {
                    "dataset_manifest": str(manifest_path),
                    "dataset_name": manifest_path.stem or "(missing)",
                    "client_name": "",
                    "fiscal_year": "",
                    "row_count": "",
                    "period": "",
                    "last_opened_at": entry.get("last_opened_at", ""),
                    "status": "文件缺失",
                }
            )
            continue
        try:
            manifest = read_manifest(manifest_path)
            parquet_path = Path(manifest.ledger_parquet)
            if not parquet_path.is_absolute():
                parquet_path = manifest_path.parent / parquet_path
            status = "可查询" if parquet_path.exists() else "Parquet 缺失"
            period = ""
            if manifest.posting_date_min or manifest.posting_date_max:
                period = f"{manifest.posting_date_min or '?'} 至 {manifest.posting_date_max or '?'}"
            summaries.append(
                {
                    "dataset_manifest": str(manifest_path),
                    "dataset_name": manifest.dataset_name,
                    "client_name": manifest.client_name,
                    "fiscal_year": str(manifest.fiscal_year),
                    "row_count": str(manifest.row_count),
                    "period": period,
                    "last_opened_at": entry.get("last_opened_at", ""),
                    "status": status,
                }
            )
        except Exception as exc:
            summaries.append(
                {
                    "dataset_manifest": str(manifest_path),
                    "dataset_name": manifest_path.stem,
                    "client_name": "",
                    "fiscal_year": "",
                    "row_count": "",
                    "period": "",
                    "last_opened_at": entry.get("last_opened_at", ""),
                    "status": f"Manifest 错误: {exc}",
                }
            )
    return summaries


def _write_entries(entries: list[dict[str, str]]) -> None:
    lines: list[str] = []
    for entry in entries:
        lines.append("[[datasets]]")
        for key, value in entry.items():
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        lines.append("")
    REGISTRY_PATH.write_text("\n".join(lines), encoding="utf-8")
