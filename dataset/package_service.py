from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from dataset.manifest_service import read_manifest
from dataset.query_dataset import inspect_ledger_parquet, resolve_ledger_parquet, resolve_manifest_path
from shared.errors import validation_error


def package_dataset(dataset_path: Path, output_zip_path: Path) -> Path:
    dataset_path = Path(dataset_path)
    output_zip_path = Path(output_zip_path)
    parquet_path = resolve_ledger_parquet(dataset_path)
    if not parquet_path.exists():
        raise validation_error("ledger parquet 文件不存在。")
    inspect_ledger_parquet(parquet_path)

    manifest_path = resolve_manifest_path(dataset_path)
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip_path, "w", compression=ZIP_DEFLATED) as archive:
        if manifest_path is not None:
            manifest = read_manifest(manifest_path)
            archive.writestr("README.txt", _readme_text(manifest.dataset_name, has_manifest=True))
            archive.write(manifest_path, "dataset.toml")
            archive.write(parquet_path, manifest.ledger_parquet or "ledger.parquet")
        else:
            archive.writestr("README.txt", _readme_text(parquet_path.stem, has_manifest=False))
            archive.write(parquet_path, parquet_path.name)
    return output_zip_path


def default_package_name(dataset_path: Path) -> str:
    manifest_path = resolve_manifest_path(dataset_path)
    if manifest_path is not None:
        manifest = read_manifest(manifest_path)
        base_name = manifest.dataset_name
    else:
        base_name = Path(dataset_path).stem
    return f"{_safe_name(base_name)}.zip"


def _readme_text(dataset_name: str, *, has_manifest: bool) -> str:
    if has_manifest:
        return (
            f"ADE Pro dataset package: {dataset_name}\n\n"
            "Open dataset.toml in ADE Pro Query to use this dataset.\n"
        )
    return (
        f"ADE Pro parquet package: {dataset_name}\n\n"
        "This package contains a standalone ledger parquet file. "
        "Open the .parquet file in ADE Pro Query to use it.\n"
    )


def _safe_name(value: str) -> str:
    keep = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "ade_pro_dataset"
