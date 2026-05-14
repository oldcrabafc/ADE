from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import tomllib

from shared.client_router import resolve_client_dir
from shared.schema import AmountRules, IngestProfile, LedgerFieldMapping


def profile_path(client_name: str) -> Path:
    return resolve_client_dir(client_name) / "ingest_profiles.toml"


def load_client_profiles(client_name: str) -> list[IngestProfile]:
    path = profile_path(client_name)
    if not path.exists():
        return []
    with path.open("rb") as file:
        data = tomllib.load(file)
    profiles: list[IngestProfile] = []
    for raw_profile in data.get("profiles", []):
        if not isinstance(raw_profile, dict):
            continue
        field_mapping = LedgerFieldMapping(**_clean_mapping(raw_profile.get("field_mapping", {})))
        amount_rules = AmountRules(**_clean_mapping(raw_profile.get("amount_rules", {})))
        match = raw_profile.get("match", {}) if isinstance(raw_profile.get("match", {}), dict) else {}
        profiles.append(
            IngestProfile(
                profile_name=str(raw_profile.get("profile_name", "default")),
                field_mapping=field_mapping,
                amount_rules=amount_rules,
                source_type=str(match.get("source_type", "excel")),
                source_sheet=str(match["source_sheet"]) if match.get("source_sheet") else None,
            )
        )
    return profiles


def save_profile(client_name: str, profile: IngestProfile) -> Path:
    profiles = [item for item in load_client_profiles(client_name) if item.profile_name != profile.profile_name]
    profiles.append(profile)
    path = profile_path(client_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_profiles_to_toml(profiles), encoding="utf-8")
    return path


def find_profile(
    client_name: str,
    source_type: str,
    source_sheet: str | None,
    columns: list[str],
) -> IngestProfile | None:
    column_set = {str(column) for column in columns}
    candidates: list[tuple[int, IngestProfile]] = []
    for profile in load_client_profiles(client_name):
        if profile.source_type != source_type:
            continue
        if source_type == "excel" and profile.source_sheet and profile.source_sheet != source_sheet:
            continue
        mapping = profile.field_mapping
        required_sources = [
            mapping.posting_date,
            mapping.voucher_id,
            mapping.ac_code,
            mapping.ac_caption,
            mapping.description,
        ]
        rules = profile.amount_rules
        if rules.mode == "direct_signed_amount":
            required_sources.append(rules.direct_amount_field or mapping.rc_amount or "")
        elif rules.mode == "amount_with_drcr":
            required_sources.extend([rules.amount_field or "", rules.drcr_field or mapping.drcr or ""])
        elif rules.mode == "debit_credit_columns":
            required_sources.extend([rules.debit_field or "", rules.credit_field or ""])
        required_sources = [source for source in required_sources if source]
        missing = [source for source in required_sources if source not in column_set]
        if missing:
            continue
        candidates.append((len(required_sources), profile))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def _clean_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): (None if raw_value == "" else raw_value) for key, raw_value in value.items()}


def _profiles_to_toml(profiles: list[IngestProfile]) -> str:
    lines = ["version = 2", ""]
    for profile in profiles:
        lines.append("[[profiles]]")
        lines.append(f'profile_name = "{_escape(profile.profile_name)}"')
        lines.append("")
        lines.append("[profiles.match]")
        lines.append(f'source_type = "{_escape(profile.source_type)}"')
        lines.append(f'source_sheet = "{_escape(profile.source_sheet or "")}"')
        lines.append("")
        lines.append("[profiles.field_mapping]")
        for key, value in asdict(profile.field_mapping).items():
            lines.append(f'{key} = "{_escape(value or "")}"')
        lines.append("")
        lines.append("[profiles.amount_rules]")
        for key, value in asdict(profile.amount_rules).items():
            if isinstance(value, list):
                items = ", ".join(f'"{_escape(item)}"' for item in value)
                lines.append(f"{key} = [{items}]")
            else:
                lines.append(f'{key} = "{_escape(value or "")}"')
        lines.append("")
    return "\n".join(lines)


def _escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')
