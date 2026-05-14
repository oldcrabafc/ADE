from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CLIENTS_DIR = DATA_DIR / "clients"
DEFAULT_DB_NAME = "main.duckdb"
JOURNAL_TABLE = "journal"
READ_ONLY_SAMPLE_LIMIT = 500
EXPORT_ROWS_PER_SHEET = 10_000

COMMON_FIELD_ALIASES = {
    "book_date": ["book_date", "记账日期", "日期", "凭证日期", "业务日期"],
    "voucher_no": ["voucher_no", "凭证号", "凭证编号", "voucher"],
    "ac_code": ["ac_code", "科目编码", "科目代码", "account_code"],
    "ac_name": ["ac_name", "科目名称", "account_name", "科目"],
    "summary": ["summary", "摘要", "备注", "description"],
    "debit": ["debit", "借方", "借方发生额", "debit_amount"],
    "credit": ["credit", "贷方", "贷方发生额", "credit_amount"],
    "direct_amount": ["rc_amount", "amount", "发生额", "本位币金额", "金额"],
}
