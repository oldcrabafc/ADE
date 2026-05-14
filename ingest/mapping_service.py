from __future__ import annotations

from dataclasses import asdict

from shared.constants import COMMON_FIELD_ALIASES
from shared.errors import validation_error
from shared.schema import AmountRules, FieldMapping, IngestProfile, LedgerFieldMapping


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


def validate_mapping(mapping: FieldMapping) -> None:
    if not mapping.book_date:
        raise validation_error("必须映射记账日期字段。")
    if not mapping.voucher_no:
        raise validation_error("必须映射凭证号字段。")
    if not mapping.ac_name:
        raise validation_error("必须映射科目名称字段。")
    if not mapping.ac_code:
        raise validation_error("必须映射科目编码字段。")
    if not mapping.summary:
        raise validation_error("必须映射摘要字段。")
    if not mapping.direct_amount_field and not (mapping.debit_field and mapping.credit_field):
        raise validation_error("必须提供直接金额字段，或同时提供借方与贷方字段。")


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


def legacy_mapping_to_profile(mapping: FieldMapping) -> IngestProfile:
    validate_mapping(mapping)
    ledger_mapping = LedgerFieldMapping(
        posting_date=mapping.book_date,
        voucher_id=mapping.voucher_no,
        ac_code=mapping.ac_code or "",
        ac_caption=mapping.ac_name,
        description=mapping.summary or "",
        rc_amount=mapping.direct_amount_field,
    )
    if mapping.direct_amount_field:
        amount_rules = AmountRules(
            mode="direct_signed_amount",
            direct_amount_field=mapping.direct_amount_field,
        )
    else:
        amount_rules = AmountRules(
            mode="debit_credit_columns",
            debit_field=mapping.debit_field,
            credit_field=mapping.credit_field,
        )
    return IngestProfile(
        profile_name="legacy-ui",
        field_mapping=ledger_mapping,
        amount_rules=amount_rules,
    )
