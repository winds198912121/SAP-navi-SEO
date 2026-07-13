"""JapaneseTextNormalizer のテスト."""

import pytest
from src.preprocessor.text_normalizer import JapaneseTextNormalizer


class TestJapaneseTextNormalizer:
    def setup_method(self):
        self.normalizer = JapaneseTextNormalizer()

    def test_ruby_removal(self):
        text = "本日は｜晴天《せいてん》なり"
        result = self.normalizer._remove_ruby(text)
        assert result == "本日は晴天なり"

    def test_ruby_removal_simple(self):
        text = "本日は《けっこう》なお天気"
        result = self.normalizer._remove_ruby(text)
        assert result == "本日はなお天気"

    def test_kigou_normalization(self):
        text = "株式会社①です"
        result = self.normalizer._normalize_kigou(text)
        assert result == "株式会社(1)です"

    def test_zenkaku_to_hankaku(self):
        text = "ＡＢＣ１２３"
        result = self.normalizer._unify_width(text)
        assert result == "ABC123"

    def test_full_pipeline(self):
        text = "【案件名】《あんけんめい》　テスト"
        result = self.normalizer.normalize(text)
        assert "【案件名】" in result
        assert "《あんけんめい》" not in result
