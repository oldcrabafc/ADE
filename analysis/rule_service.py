from __future__ import annotations

from pathlib import Path

from analysis.anomaly_detection import built_in_rules
from query.sql_runner import execute_query_on_dataset


class RuleService:
    def list_rules(self) -> dict[str, str]:
        return built_in_rules()

    def run_rule(self, dataset_path: Path, rule_name: str):
        sql_text = built_in_rules()[rule_name]
        return execute_query_on_dataset(dataset_path, sql_text)
