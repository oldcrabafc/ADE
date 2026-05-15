from __future__ import annotations

from dataclasses import asdict

from shared.constants import COMMON_FIELD_ALIASES
from shared.schema import FieldMapping, LedgerFieldMapping


def auto_detect_mapping(columns: list[str]) -> FieldMapping:
    lowered = {column.lower(): column for column in columns}

    def find(alias_key: str) -> str | None:
        for alias in COMMON_FIELD_ALIASES[alias_key]:
            match = lowered.get(alias.lower())
            if match:
                return match
        return None

    return FieldMapping(
        book_date=find("book_date") or "",
        voucher_no=find("voucher_no") or "",
        ac_name=find("ac_name") or "",
        ac_code=find("ac_code"),
        summary=find("summary"),
        debit_field=find("debit"),
        credit_field=find("credit"),
        direct_amount_field=find("direct_amount"),
    )


def build_field_mapping_report(mapping: FieldMapping | LedgerFieldMapping) -> list[dict[str, str]]:
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
