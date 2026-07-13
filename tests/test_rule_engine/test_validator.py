"""フィールドバリデーターのテスト."""

import pytest
from src.common.models import ValidationConfig
from src.rule_engine.validator import FieldValidator


class TestFieldValidator:
    def setup_method(self):
        self.validator = FieldValidator()

    def test_required_field(self):
        config = ValidationConfig(required=True)
        assert not self.validator.validate(None, config)
        assert self.validator.validate("value", config)

    def test_min_length(self):
        config = ValidationConfig(min_length=3)
        assert not self.validator.validate("ab", config)
        assert self.validator.validate("abc", config)

    def test_min_items(self):
        config = ValidationConfig(min_items=2)
        assert not self.validator.validate(["a"], config)
        assert self.validator.validate(["a", "b"], config)

    def test_combined_rules(self):
        config = ValidationConfig(required=True, min_length=2, max_length=100)
        assert not self.validator.validate(None, config)
        assert not self.validator.validate("a", config)
        assert self.validator.validate("valid value", config)
