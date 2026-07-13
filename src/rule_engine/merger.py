"""結果融合モジュール — ルール抽出 + LLM抽出の結果を統合."""

from __future__ import annotations

from typing import Any

from src.common.models import FieldResult


class FinalField:
    """最終的なフィールド値。"""
    def __init__(
        self,
        value: Any = None,
        confidence: float = 0.0,
        source: str = "none",
        conflict_note: str | None = None,
    ):
        self.value = value
        self.confidence = confidence
        self.source = source
        self.conflict_note = conflict_note


class ResultMerger:
    """ルールエンジンとLLMエンジンの結果を融合。"""

    def merge(
        self,
        rule_results: dict[str, FieldResult],
        llm_results: dict[str, FieldResult],
        confidence_threshold_high: float = 0.9,
    ) -> dict[str, FinalField]:
        """ルール結果とLLM結果を統合。

        戦略:
        - ルールが高信頼度（>0.9）→ ルール採用
        - 両方一致 → 高い方の信頼度
        - 両方不一致 → 高い信頼度を採用、注釈付き
        - LLMのみ → LLM採用
        - ルールのみ（低信頼度）→ ルール採用＋注釈
        """
        all_fields = set(rule_results.keys()) | set(llm_results.keys())
        final: dict[str, FinalField] = {}

        for field in all_fields:
            rule = rule_results.get(field)
            llm = llm_results.get(field)

            if rule and rule.confidence > confidence_threshold_high:
                # ルール高信頼度 → ルール優先
                final[field] = FinalField(
                    value=rule.value,
                    confidence=rule.confidence,
                    source="rule",
                )
            elif rule and llm:
                if self._values_agree(rule.value, llm.value):
                    final[field] = FinalField(
                        value=rule.value,
                        confidence=max(rule.confidence, llm.confidence),
                        source="both_agree",
                    )
                else:
                    if rule.confidence >= llm.confidence:
                        final[field] = FinalField(
                            value=rule.value,
                            confidence=rule.confidence,
                            source="rule",
                            conflict_note=f"LLM disagrees: {llm.value}",
                        )
                    else:
                        final[field] = FinalField(
                            value=llm.value,
                            confidence=llm.confidence,
                            source="llm",
                            conflict_note=f"Rule disagrees: {rule.value}",
                        )
            elif llm:
                final[field] = FinalField(
                    value=llm.value,
                    confidence=llm.confidence,
                    source="llm",
                )
            elif rule:
                final[field] = FinalField(
                    value=rule.value,
                    confidence=rule.confidence,
                    source="rule",
                    conflict_note="low confidence, no LLM result",
                )
            else:
                final[field] = FinalField()

        return final

    def _values_agree(self, a: Any, b: Any) -> bool:
        """2つの値が実質的に一致するか判定。"""
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if isinstance(a, list) and isinstance(b, list):
            return set(a) == set(b)
        if isinstance(a, dict) and isinstance(b, dict):
            shared_keys = set(a.keys()) & set(b.keys())
            if not shared_keys:
                return False
            return all(a[k] == b[k] for k in shared_keys)
        return str(a).strip() == str(b).strip()
