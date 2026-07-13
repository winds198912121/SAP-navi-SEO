"""ルールマッチャーのテスト."""

import pytest
from src.common.models import ExtractionPattern, PatternType
from src.rule_engine.matcher import RegexMatcher, PositionMatcher


class TestRegexMatcher:
    def setup_method(self):
        self.matcher = RegexMatcher()

    def test_simple_keyword_match(self):
        pattern = ExtractionPattern(
            type=PatternType.REGEX,
            value=r"(?:案件名|件名)[：:]([^\n]+)",
        )
        text = "【案件名】某証券会社向け基幹システム\n【スキル】Java"
        result = self.matcher.match(pattern, text)
        assert result is not None
        value, conf = result
        assert "某証券会社向け基幹システム" in value
        assert conf > 0

    def test_no_match(self):
        pattern = ExtractionPattern(
            type=PatternType.REGEX,
            value=r"単価[：:](\d+)",
        )
        text = "【案件名】テスト"
        result = self.matcher.match(pattern, text)
        assert result is None

    def test_skill_extraction(self):
        pattern = ExtractionPattern(
            type=PatternType.REGEX,
            value=r"(?:スキル|必須スキル)[：:]([^\n]+)",
        )
        text = "【必須スキル】Java、Spring Boot、AWS"
        result = self.matcher.match(pattern, text)
        assert result is not None
        value, _ = result
        assert "Java" in value
        assert "Spring Boot" in value
