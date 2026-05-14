from __future__ import annotations

from shared.errors import validation_error


def _escape(value: str) -> str:
    return value.replace("'", "''")


def build_ledger_query(filters: dict[str, str]) -> str:
    conditions: list[str] = []

    account_name = filters.get("ac_name", "").strip()
    if account_name:
        conditions.append(f"ac_caption LIKE '%{_escape(account_name)}%'")

    voucher_no = filters.get("voucher_no", "").strip()
    if voucher_no:
        conditions.append(f"voucher_id = '{_escape(voucher_no)}'")

    summary = filters.get("summary", "").strip()
    if summary:
        conditions.append(f"description LIKE '%{_escape(summary)}%'")

    min_amount = filters.get("min_amount", "").strip()
    if min_amount:
        try:
            amount_value = float(min_amount)
        except ValueError as exc:
            raise validation_error("最小金额必须是数字。") from exc
        conditions.append(f"ABS(rc_amount) >= {amount_value}")

    date_from = filters.get("date_from", "").strip()
    if date_from:
        conditions.append(f"posting_date >= DATE '{_escape(date_from)}'")

    date_to = filters.get("date_to", "").strip()
    if date_to:
        conditions.append(f"posting_date <= DATE '{_escape(date_to)}'")

    sql = "SELECT * FROM ledger"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY posting_date DESC, voucher_id DESC LIMIT 1000"
    return sql


def build_journal_query(filters: dict[str, str]) -> str:
    return build_ledger_query(filters)
