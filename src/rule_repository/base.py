"""ルールリポジトリの抽象基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.common.models import FormatTemplate, Rule, RuleStats


class RuleRepository(ABC):
    """ルールリポジトリ抽象基底クラス。"""

    @abstractmethod
    def get_rules(
        self,
        field: str | None = None,
        format_type: str | None = None,
        status: str | None = None,
    ) -> list[Rule]:
        """条件に合致するルールを取得。"""
        ...

    @abstractmethod
    def get_rule(self, rule_id: str) -> Rule | None:
        """ルールIDでルールを取得。"""
        ...

    @abstractmethod
    def save_rule(self, rule: Rule) -> str:
        """新規ルールを保存。IDを返す。"""
        ...

    @abstractmethod
    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> bool:
        """ルールを更新。"""
        ...

    @abstractmethod
    def delete_rule(self, rule_id: str) -> bool:
        """ルールを削除。"""
        ...

    @abstractmethod
    def get_format_templates(self) -> list[FormatTemplate]:
        """全フォーマットテンプレートを取得。"""
        ...

    @abstractmethod
    def save_format_template(self, template: FormatTemplate) -> str:
        """フォーマットテンプレートを保存。"""
        ...

    @abstractmethod
    def get_dictionary(self, name: str) -> list[dict]:
        """辞書データを取得。"""
        ...

    @abstractmethod
    def save_dictionary(self, name: str, entries: list[dict]) -> None:
        """辞書データを保存。"""
        ...

    @abstractmethod
    def log_hit(
        self,
        rule_id: str,
        document_id: str,
        matched: bool,
        confidence: float,
        value: str | None = None,
    ) -> None:
        """ルールの使用履歴を記録。"""
        ...

    @abstractmethod
    def get_rule_stats(self, rule_id: str) -> RuleStats | None:
        """ルールの統計情報を取得。"""
        ...

    @abstractmethod
    def get_coverage_stats(self) -> dict[str, Any]:
        """ルールカバレッジ統計を取得。"""
        ...
