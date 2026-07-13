"""ルールエンジンコア — ルールの実行と結果統合."""

from __future__ import annotations

import logging
from typing import Any

from src.common.models import (
    ExtractionPattern,
    FieldResult,
    PatternType,
    PostProcessConfig,
    Rule,
    RuleStatus,
    ValidationConfig,
)
from src.rule_engine.matcher import MatcherRegistry
from src.rule_engine.validator import FieldValidator

logger = logging.getLogger(__name__)


class ExtractionCandidate:
    """抽出候補（ルール1パターンの結果）。"""
    def __init__(self, value: Any, confidence: float, rule_id: str, pattern_idx: int = 0):
        self.value = value
        self.confidence = confidence
        self.rule_id = rule_id
        self.pattern_idx = pattern_idx


class RuleEngine:
    """ルールエンジン — ルールのロード・マッチング・結果選択を担当。"""

    def __init__(self, matcher_registry: MatcherRegistry | None = None):
        self.matchers = matcher_registry or MatcherRegistry()
        self.validator = FieldValidator()

    def extract_field(
        self,
        field: str,
        text: str,
        rules: list[Rule],
        context: dict[str, Any] | None = None,
    ) -> FieldResult:
        """ルールを使って単一フィールドを抽出。

        Args:
            field: 抽出対象フィールド名
            text: 前処理済みテキスト
            rules: 適用するルールのリスト
            context: 追加コンテキスト（書式情報など）

        Returns:
            FieldResult: 抽出結果
        """
        if not rules:
            return FieldResult(field=field, value=None, confidence=0.0, source="no_rule")

        # 有効なルールのみフィルタ
        active_rules = [r for r in rules if r.enabled and r.status == RuleStatus.ACTIVE]
        if not active_rules:
            return FieldResult(field=field, value=None, confidence=0.0, source="no_active_rule")

        # 優先順位でソート
        active_rules.sort(key=lambda r: r.priority, reverse=True)

        candidates: list[ExtractionCandidate] = []

        for rule in active_rules:
            for idx, pattern in enumerate(rule.patterns):
                try:
                    match_result = self.matchers.match(pattern, text, context or {})

                    if match_result is not None:
                        value, match_conf = match_result

                        # 後処理
                        value = self._apply_post_process(value, rule.post_process)

                        # 検証
                        if self.validator.validate(value, rule.validation):
                            effective_conf = match_conf * (rule.priority / 100.0)
                            candidates.append(ExtractionCandidate(
                                value=value,
                                confidence=effective_conf,
                                rule_id=rule.rule_id,
                                pattern_idx=idx,
                            ))
                except Exception as e:
                    logger.warning(f"Rule {rule.rule_id} pattern {idx} failed: {e}")
                    continue

        if not candidates:
            return FieldResult(field=field, value=None, confidence=0.0, source="rule_no_match")

        # 最良の候補を選択
        best = max(candidates, key=lambda c: c.confidence)
        return FieldResult(
            field=field,
            value=best.value,
            confidence=best.confidence,
            source="rule",
            rule_id=best.rule_id,
        )

    def _apply_post_process(self, value: Any, config: PostProcessConfig) -> Any:
        """後処理を適用。"""
        if value is None:
            return None

        if config.trim and isinstance(value, str):
            value = value.strip()

        if config.split and isinstance(value, str):
            import re
            delimiters = "|".join(
                re.escape(d) if len(d) == 1 else d
                for d in config.split
            )
            value = re.split(delimiters, value)
            value = [item.strip() for item in value if item.strip()]

        if config.filter_empty and isinstance(value, list):
            value = [item for item in value if item]

        if config.deduplicate and isinstance(value, list):
            seen = set()
            value = [x for x in value if not (x in seen or seen.add(x))]

        return value
