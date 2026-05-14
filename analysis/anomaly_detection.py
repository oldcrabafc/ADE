from __future__ import annotations

from analysis.journal_analysis import empty_summary_sql, high_value_sql, weekend_entry_sql


def built_in_rules() -> dict[str, str]:
    return {
        "大额凭证": high_value_sql(),
        "周末入账": weekend_entry_sql(),
        "摘要为空": empty_summary_sql(),
    }
