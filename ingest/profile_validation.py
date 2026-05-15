from __future__ import annotations

from shared.schema import IngestProfile


DEFAULT_REQUIRED_FIELDS = ["posting_date", "voucher_id", "ac_code", "ac_caption", "description"]


def validate_profile_mapping(profile: IngestProfile) -> tuple[list[str], list[str]]:
    required_missing: list[str] = []
    amount_missing: list[str] = []
    mapping = profile.field_mapping
    target_fields = profile.required_field or list(DEFAULT_REQUIRED_FIELDS)
    values = {
        "posting_date": mapping.posting_date,
        "voucher_id": mapping.voucher_id,
        "ac_code": mapping.ac_code,
        "ac_caption": mapping.ac_caption,
        "description": mapping.description,
        "voucher_header": mapping.voucher_header,
        "company_id": mapping.company_id,
        "drcr": mapping.drcr,
        "rc_amount": mapping.rc_amount,
        "lc_amount": mapping.lc_amount,
        "vendor_id": mapping.vendor_id,
        "vendor_name": mapping.vendor_name,
        "customer_id": mapping.customer_id,
        "customer_name": mapping.customer_name,
        "department": mapping.department,
        "employee_id": mapping.employee_id,
        "employee_name": mapping.employee_name,
        "currency": mapping.currency,
        "document_type": mapping.document_type,
        "posting_period": mapping.posting_period,
        "source_system": mapping.source_system,
    }
    for field_name in target_fields:
        if not values.get(field_name):
            required_missing.append(field_name)
    rules = profile.amount_rules
    if rules.mode == "direct_signed_amount":
        if not (rules.direct_amount_field or mapping.rc_amount):
            amount_missing.append("direct_amount_field")
    elif rules.mode == "amount_with_drcr":
        if not rules.amount_field:
            amount_missing.append("amount_field")
        if not (rules.drcr_field or mapping.drcr):
            amount_missing.append("drcr_field")
    elif rules.mode == "debit_credit_columns":
        if not rules.debit_field:
            amount_missing.append("debit_field")
        if not rules.credit_field:
            amount_missing.append("credit_field")
    else:
        amount_missing.append("amount_rules.mode")
    return required_missing, amount_missing
