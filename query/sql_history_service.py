from __future__ import annotations

from datetime import datetime
from pathlib import Path

import tomllib

from shared.constants import DATA_DIR


SQL_HISTORY_PATH = DATA_DIR / "sql_history.toml"


def built_in_sql_templates() -> dict[str, str]:
    return {
        "浏览前 200 行": "SELECT * FROM ledger LIMIT 200",
        "按科目汇总": """
SELECT
    ac_code,
    ac_caption,
    COUNT(*) AS entry_count,
    SUM(rc_amount) AS total_amount
FROM ledger
GROUP BY ac_code, ac_caption
ORDER BY ABS(total_amount) DESC
LIMIT 200
""".strip(),
        "按月汇总发生额": """
SELECT
    strftime(posting_date, '%Y-%m') AS posting_month,
    COUNT(*) AS entry_count,
    SUM(rc_amount) AS total_amount
FROM ledger
GROUP BY posting_month
ORDER BY posting_month
""".strip(),
        "凭证借贷不平衡检查": """
SELECT
    voucher_id,
    COUNT(*) AS entry_count,
    SUM(rc_amount) AS voucher_amount
FROM ledger
GROUP BY voucher_id
HAVING ABS(SUM(rc_amount)) > 0.01
ORDER BY ABS(voucher_amount) DESC
LIMIT 1000
""".strip(),
        "旧 journal 兼容示例": "SELECT voucher_no, ac_name, summary, rc_amount FROM journal LIMIT 200",
    }


def list_sql_history() -> list[dict[str, str]]:
    if not SQL_HISTORY_PATH.exists():
        return []
    with SQL_HISTORY_PATH.open("rb") as file:
        data = tomllib.load(file)
    raw_entries = data.get("history", [])
    if not isinstance(raw_entries, list):
        return []
    return [{str(key): str(value) for key, value in entry.items()} for entry in raw_entries if isinstance(entry, dict)]


def record_sql_history(sql_text: str, dataset_path: Path | None = None, *, limit: int = 30) -> None:
    normalized_sql = sql_text.strip()
    if not normalized_sql:
        return
    dataset_text = str(dataset_path) if dataset_path is not None else ""
    entries = list_sql_history()
    entries = [
        entry
        for entry in entries
        if not (entry.get("sql_text", "").strip() == normalized_sql and entry.get("dataset_path", "") == dataset_text)
    ]
    entries.insert(
        0,
        {
            "executed_at": datetime.now().isoformat(timespec="seconds"),
            "dataset_path": dataset_text,
            "sql_text": normalized_sql,
        },
    )
    _write_history(entries[: max(1, limit)])


def _write_history(entries: list[dict[str, str]]) -> None:
    SQL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for entry in entries:
        lines.append("[[history]]")
        for key, value in entry.items():
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        lines.append("")
    SQL_HISTORY_PATH.write_text("\n".join(lines), encoding="utf-8")
