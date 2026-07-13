"""フィールドバリデーター — 抽出値の検証."""

from __future__ import annotations

import re
from typing import Any

from src.common.models import ValidationConfig


class FieldValidator:
    """抽出されたフィールド値を検証。"""

    def validate(self, value: Any, config: ValidationConfig) -> bool:
        """値がバリデーションルールを満たすかチェック。"""
        if config.required and value is None:
            return False
        if value is None:
            return True

        if isinstance(value, str):
            if config.min_length and len(value) < config.min_length:
                return False
            if config.max_length and len(value) > config.max_length:
                return False
            if config.must_contain_pattern:
                if not re.search(config.must_contain_pattern, value):
                    return False

        if isinstance(value, list):
            if config.min_items and len(value) < config.min_items:
                return False

        # カスタム検証ルール
        for rule in (config.rules or []):
            if not self._apply_rule(value, rule):
                return False

        return True

    def _apply_rule(self, value: Any, rule: dict[str, Any]) -> bool:
        """単一のカスタム検証ルールを適用。"""
        rule_type = rule.get("type", "")
        rule_value = rule.get("value")

        if rule_type == "notEmpty":
            return value is not None and value != "" and value != []
        elif rule_type == "pattern" and isinstance(value, str):
            return bool(re.search(rule_value, value))
        elif rule_type == "range" and isinstance(value, (int, float)):
            return (rule_value.get("min", float("-inf")) <= value <=
                    rule_value.get("max", float("inf")))
        elif rule_type == "enum":
            return value in rule_value
        elif rule_type == "type":
            type_map = {"string": str, "number": (int, float), "list": list, "dict": dict}
            expected = type_map.get(rule_value)
            return expected is not None and isinstance(value, expected)

        return True
