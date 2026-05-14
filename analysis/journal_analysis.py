from __future__ import annotations


def high_value_sql(threshold: float = 1_000_000) -> str:
    return f"""
    SELECT *
    FROM ledger
    WHERE ABS(rc_amount) >= {threshold}
    ORDER BY ABS(rc_amount) DESC, posting_date DESC
    LIMIT 1000
    """.strip()


def weekend_entry_sql() -> str:
    return """
    SELECT *
    FROM ledger
    WHERE dayofweek(posting_date) IN (0, 6)
    ORDER BY posting_date DESC, voucher_id DESC
    LIMIT 1000
    """.strip()


def empty_summary_sql() -> str:
    return """
    SELECT *
    FROM ledger
    WHERE description IS NULL OR trim(description) = ''
    ORDER BY posting_date DESC, voucher_id DESC
    LIMIT 1000
    """.strip()
