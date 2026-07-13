"""ルールマッチャー — 各パターンタイプのマッチング実装."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from src.common.models import ExtractionPattern, PatternType


class PatternMatcher(ABC):
    """パターンマッチャーの抽象基底。"""

    @abstractmethod
    def match(
        self,
        pattern: ExtractionPattern,
        text: str,
        context: dict[str, Any],
    ) -> tuple[Any, float] | None:
        """パターンでテキストをマッチング。

        Returns:
            (抽出値, 信頼度) or None（マッチなし）
        """
        ...


class RegexMatcher(PatternMatcher):
    """正規表現パターンマッチャー。"""

    def match(
        self,
        pattern: ExtractionPattern,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[Any, float] | None:
        flags = 0
        flag_map = {
            "MULTILINE": re.MULTILINE,
            "DOTALL": re.DOTALL,
            "IGNORECASE": re.IGNORECASE,
            "UNICODE": re.UNICODE,
        }
        for flag in pattern.flags:
            flags |= flag_map.get(flag.upper(), 0)

        try:
            m = re.search(pattern.value, text, flags)
            if m:
                # キャプチャグループがあれば最初のグループを使用
                if m.lastindex and m.lastindex >= 1:
                    value = m.group(1)
                else:
                    value = m.group(0)
                return value, pattern.confidence
        except re.error as e:
            raise ValueError(f"Regex error in pattern '{pattern.value[:50]}...': {e}")

        return None


class PositionMatcher(PatternMatcher):
    """位置ベースパターンマッチャー。

    セクションタイトル＋行オフセットで値を抽出。
    """

    def match(
        self,
        pattern: ExtractionPattern,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[Any, float] | None:
        lines = text.split("\n")

        # セクションの位置を検索
        section_idx = None
        if pattern.section:
            for i, line in enumerate(lines):
                if pattern.section in line:
                    section_idx = i
                    break

        if section_idx is None:
            # キーワードでフォールバック検索
            if pattern.table_anchor:
                keyword = pattern.table_anchor.get("rowKeyword", "")
                for i, line in enumerate(lines):
                    if keyword in line:
                        section_idx = i
                        break

        if section_idx is None:
            return None

        # 行オフセットを計算
        offset = pattern.line_offset or 0
        if pattern.direction == "below":
            target_idx = section_idx + offset
        elif pattern.direction == "above":
            target_idx = section_idx - offset
        else:
            target_idx = section_idx

        # 範囲外チェック
        if target_idx < 0 or target_idx >= len(lines):
            return None

        # 範囲を取得
        if pattern.span_lines and pattern.span_lines > 1:
            end_idx = min(target_idx + pattern.span_lines, len(lines))
            span_lines = lines[target_idx:end_idx]

            # stop_pattern まで
            if pattern.stop_pattern:
                stop_re = re.compile(pattern.stop_pattern)
                filtered = []
                for line in span_lines:
                    if stop_re.search(line):
                        break
                    filtered.append(line)
                value = "\n".join(filtered).strip()
            else:
                value = "\n".join(span_lines).strip()
        else:
            value = lines[target_idx].strip()

        return value if value else None, pattern.confidence


class MatcherRegistry:
    """マッチャーのレジストリとディスパッチ。"""

    def __init__(self):
        self._matchers: dict[PatternType, PatternMatcher] = {
            PatternType.REGEX: RegexMatcher(),
            PatternType.POSITION: PositionMatcher(),
        }

    def register(self, pattern_type: PatternType, matcher: PatternMatcher) -> None:
        """カスタムマッチャーを登録。"""
        self._matchers[pattern_type] = matcher

    def match(
        self,
        pattern: ExtractionPattern,
        text: str,
        context: dict[str, Any],
    ) -> tuple[Any, float] | None:
        """適切なマッチャーでパターンを実行。"""
        matcher = self._matchers.get(pattern.type)
        if matcher is None:
            raise ValueError(f"Unsupported pattern type: {pattern.type}")
        return matcher.match(pattern, text, context)
