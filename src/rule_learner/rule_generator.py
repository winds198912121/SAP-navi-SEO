"""ルール生成モジュール — CandidatePattern から正式な Rule オブジェクトを生成."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.common.models import (
    ExtractionPattern,
    PostProcessConfig,
    Rule,
    RuleMetadata,
    RuleStatus,
    ValidationConfig,
)
from src.rule_learner.pattern_discovery import CandidatePattern

# フィールドごとのデフォルト後処理設定
FIELD_POSTPROCESS: dict[str, dict[str, Any]] = {
    "skill_requirement": {
        "split": ["、", "・", "/", "\\s+"],
        "trim": True,
        "filter_empty": True,
        "deduplicate": True,
        "map_to_canonical": True,
    },
    "preferred_skills": {
        "split": ["、", "・", "/", "\\s+"],
        "trim": True,
        "filter_empty": True,
        "deduplicate": True,
    },
    "location": {
        "trim": True,
    },
    "rate": {
        "trim": True,
    },
}

# フィールドごとのデフォルトバリデーション
FIELD_VALIDATION: dict[str, dict[str, Any]] = {
    "project_name": {"required": True, "min_length": 2},
    "skill_requirement": {"required": True, "min_items": 1},
    "location": {"required": True},
    "rate": {"required": True},
}


class RuleGenerator:
    """CandidatePattern から正式な Rule を生成。"""

    def generate(
        self,
        candidates: list[CandidatePattern],
        field: str,
        format_types: list[str] | None = None,
        priority: int | None = None,
    ) -> list[Rule]:
        """パターン候補からルールを生成。"""
        if not candidates:
            return []

        rules = []
        for idx, candidate in enumerate(candidates):
            patterns = self._build_patterns(candidate, field)

            rule = Rule(
                rule_id=self._generate_rule_id(field, idx),
                field=field,
                format_type=format_types or ["*"],
                priority=priority or self._suggest_priority(candidate),
                status=RuleStatus.TESTING,
                description=candidate.description,
                patterns=patterns,
                post_process=PostProcessConfig(
                    **FIELD_POSTPROCESS.get(field, {"trim": True})
                ),
                validation=ValidationConfig(
                    **FIELD_VALIDATION.get(field, {})
                ),
                metadata=RuleMetadata(
                    created_by="learner_auto",
                    created_at=datetime.now(),
                    accuracy=candidate.confidence,
                    sample_count=candidate.sample_count,
                ),
            )
            rules.append(rule)

        return rules

    def _build_patterns(
        self, candidate: CandidatePattern, field: str
    ) -> list[ExtractionPattern]:
        """候補から ExtractionPattern を構築。"""
        pattern = ExtractionPattern(
            type=candidate.type,
            value=candidate.value,
            confidence=candidate.confidence,
        )

        if candidate.type == "position":
            import json
            pos_data = json.loads(candidate.value)
            pattern.section = pos_data.get("section")
            pattern.line_offset = pos_data.get("lineOffset")
            pattern.direction = pos_data.get("direction", "below")

        return [pattern]

    def _generate_rule_id(self, field: str, idx: int) -> str:
        """ルールIDを生成。"""
        from src.common.utils import generate_document_id
        return f"auto_{field}_{idx:03d}_{generate_document_id()[-6:]}"

    def _suggest_priority(self, candidate: CandidatePattern) -> int:
        """パターンの品質から優先度を推定。"""
        base = int(candidate.confidence * 100)
        # 高信頼度かつ高サポート数なら高優先度
        if candidate.confidence >= 0.9 and candidate.support_count >= 3:
            return min(base + 10, 95)
        elif candidate.confidence >= 0.8:
            return min(base, 85)
        else:
            return min(base - 10, 70)
