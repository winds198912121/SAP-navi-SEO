"""パターン発見モジュール — アノテーションデータから抽出パターンを発見."""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Annotation:
    """1サンプルのアノテーションデータ。"""
    field: str
    value: Any
    text: str                     # 元文書全文
    format_type: str = "unknown"
    document_id: str = ""


@dataclass
class CandidatePattern:
    """発見されたパターン候補。"""
    type: str                     # regex | position | keyword
    value: str                    # パターン文字列（正規表現等）
    confidence: float
    score: float = 0.0
    support_count: int = 0        # このパターンがマッチしたサンプル数
    sample_count: int = 0         # 総サンプル数
    description: str = ""


class PatternDiscovery:
    """アノテーションデータから抽出パターンを発見。"""

    def discover(
        self,
        annotations: list[Annotation],
        texts: list[str] | None = None,
    ) -> list[CandidatePattern]:
        """アノテーションからパターンを発見。

        3つの方法を試行し、結果をマージ:
        1. キーワードベース（前後のN-gram）
        2. 位置ベース（同フォーマット内の相対位置）
        """
        patterns: list[CandidatePattern] = []

        # 方法1: キーワードパターン発見
        kw_patterns = self._discover_keyword_patterns(annotations)
        patterns.extend(kw_patterns)

        # 方法2: 位置パターン発見（同フォーマットのみ可能）
        pos_patterns = self._discover_position_patterns(annotations)
        patterns.extend(pos_patterns)

        return patterns

    def _discover_keyword_patterns(
        self, annotations: list[Annotation]
    ) -> list[CandidatePattern]:
        """キーワードパターンを発見。

        各アノテーションのフィールド値の前後テキストから
        頻出するN-gramを抽出し、正規表現パターンを生成。
        """
        if not annotations:
            return []

        prefixes = []
        suffixes = []

        for ann in annotations:
            if isinstance(ann.value, str) and ann.value:
                pos = ann.text.find(ann.value)
                if pos > 0:
                    prefix = ann.text[max(0, pos - 30):pos]
                    suffix = ann.text[
                        pos + len(ann.value):
                        pos + len(ann.value) + 20
                    ]
                    prefixes.append(prefix.strip())
                    suffixes.append(suffix.strip())

        if not prefixes:
            return []

        # 前方の頻出名詞句を分析
        prefix_ngrams = Counter()
        for pref in prefixes:
            for n in range(1, 6):
                for i in range(len(pref) - n + 1):
                    ngram = pref[i:i + n]
                    if len(ngram.strip()) >= 2:
                        prefix_ngrams[ngram] += 1

        # 高頻度N-gramを抽出
        threshold = max(2, len(annotations) * 0.4)
        significant = [
            (ngram, count)
            for ngram, count in prefix_ngrams.most_common(30)
            if count >= threshold
        ]

        # N-gramから正規表現を生成
        field = annotations[0].field
        patterns = []
        for ngram, count in significant:
            escaped = re.escape(ngram)
            if self._is_field_prefix(ngram, field):
                regex = f"(?:{escaped})[：:]([^\\n]+)"
                patterns.append(CandidatePattern(
                    type="regex",
                    value=regex,
                    confidence=min(0.6 + count / len(annotations) * 0.3, 0.95),
                    score=count / len(annotations),
                    support_count=count,
                    sample_count=len(annotations),
                    description=f"キーワード'{ngram}'に続く内容を抽出",
                ))

        return patterns

    def _discover_position_patterns(
        self, annotations: list[Annotation]
    ) -> list[CandidatePattern]:
        """位置ベースのパターンを発見。

        アノテーションのフィールド値が出現する相対位置が
        サンプル間で一貫している場合に位置ルールを生成。
        """
        if len(annotations) < 2:
            return []

        # 全サンプルが同一フォーマットか確認
        formats = set(ann.format_type for ann in annotations)
        if len(formats) > 1:
            return []  # 異なるフォーマット → 位置ルールは不適切

        # 各行にセクションキーワードがあるか探索
        common_prefixes = self._find_common_sections(
            [ann.text for ann in annotations]
        )
        if not common_prefixes:
            return []

        patterns = []
        for section_word in common_prefixes[:3]:
            # セクションからのオフセットを計算
            offsets = []
            for ann in annotations:
                pos_section = ann.text.find(section_word)
                pos_value = ann.text.find(str(ann.value)) if isinstance(ann.value, str) else -1
                if pos_section >= 0 and pos_value > pos_section:
                    line_before = ann.text[:pos_section].count("\n")
                    line_of_value = ann.text[:pos_value].count("\n")
                    offsets.append(line_of_value - line_before)

            if offsets and max(offsets) - min(offsets) <= 1:
                avg_offset = sum(offsets) / len(offsets)
                patterns.append(CandidatePattern(
                    type="position",
                    value=json.dumps({
                        "section": section_word,
                        "lineOffset": int(round(avg_offset)),
                        "direction": "below",
                    }),
                    confidence=0.8,
                    score=len(offsets) / len(annotations),
                    support_count=len(offsets),
                    sample_count=len(annotations),
                    description=f"セクション'{section_word}'から{int(round(avg_offset))}行目",
                ))

        return patterns

    def _is_field_prefix(self, ngram: str, field: str) -> bool:
        """N-gramがフィールドの接頭辞として適切か判定。"""
        field_keywords = {
            "project_name": ["案件名", "件名", "タイトル", "プロジェクト名"],
            "skill_requirement": ["スキル", "必須スキル", "求めるスキル", "必要スキル", "応募資格"],
            "location": ["勤務地", "場所", "作業場所", "拠点"],
            "rate": ["単価", "金額", "報酬", "給与", "月額", "日額"],
            "period": ["期間", "契約期間", "作業期間", "予定期間"],
            "headcount": ["募集人数", "人数", "募集"],
            "industry": ["業種", "案件区分", "業界"],
            "trade_flow": ["商流", "契約形態", "契約種別"],
            "japanese_level": ["日本語", "日本語レベル"],
            "english_level": ["英語", "英語レベル"],
        }
        keywords = field_keywords.get(field, [field])
        return any(kw in ngram for kw in keywords)

    def _find_common_sections(self, texts: list[str], top_n: int = 10) -> list[str]:
        """テキスト群に共通して出現するセクションキーワードを検出。"""
        if not texts:
            return []

        section_pattern = re.compile(r"(【[^】]+】|■[^\n]+|●[^\n]+)")
        all_sections = []
        for text in texts:
            all_sections.extend(section_pattern.findall(text))

        counter = Counter(all_sections)
        return [s for s, _ in counter.most_common(top_n) if counter[s] >= len(texts) * 0.5]


# `patterns.discover`で使うために
import json  # noqa: E402 （_discover_position_patterns内で使う）
