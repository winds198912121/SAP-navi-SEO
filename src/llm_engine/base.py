"""LLM 抽出エンジンの基底クラスと実装."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from src.common.models import ExtractionResult, FieldResult, ExtractionMode
from src.common.schema import EXTRACTION_SCHEMA
from src.common.utils import safe_json_parse

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM API クライアントの抽象基底クラス。"""

    @abstractmethod
    async def chat_completion(
        self,
        system: str,
        messages: list[dict[str, str]],
        response_format: dict | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        """LLM チャット完了 API を呼び出す。"""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """テキストのトークン数を推定。"""
        ...


class PromptBuilder:
    """LLM 用プロンプトを構築する。"""

    def __init__(self):
        self._system_templates: dict[str, str] = {}
        self._user_templates: dict[str, str] = {}

    def register_template(self, name: str, system: str | None = None, user: str | None = None) -> None:
        """テンプレートを登録。"""
        if system:
            self._system_templates[name] = system
        if user:
            self._user_templates[name] = user

    def build(
        self,
        system_template: str,
        user_template: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """プロンプトを構築。"""
        ctx = context or {}
        system = self._system_templates.get(system_template, "")
        user = self._user_templates.get(user_template, "")

        # テンプレート変数を置換
        for key, value in ctx.items():
            placeholder = "{" + key + "}"
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            system = system.replace(placeholder, str(value))
            user = user.replace(placeholder, str(value))

        return {"system": system, "user": user}


class LLMExtractor:
    """LLM ベースの案件データ抽出エンジン。"""

    def __init__(
        self,
        client: LLMClient,
        prompt_builder: PromptBuilder,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4000,
    ):
        self.client = client
        self.prompt_builder = prompt_builder
        self.model = model
        self.max_tokens = max_tokens

    async def extract(
        self,
        text: str,
        fields: list[str] | None = None,
    ) -> ExtractionResult:
        """LLM を使ってテキストから案件データを抽出。

        Args:
            text: 前処理済みドキュメントテキスト
            fields: 抽出対象フィールド（None=全フィールド）

        Returns:
            ExtractionResult: 抽出結果
        """
        # テキストをトークン制限内に収める
        truncated_text = self._truncate(text)

        # プロンプト構築
        prompt = self.prompt_builder.build(
            system_template="extraction_system",
            user_template="extraction_user",
            context={
                "text": truncated_text,
                "schema": json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False, indent=2),
                "fields": json.dumps(fields) if fields else "all fields",
            },
        )

        # API 呼び出し
        response = await self.client.chat_completion(
            system=prompt["system"],
            messages=[{"role": "user", "content": prompt["user"]}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=self.max_tokens,
        )

        # 応答をパース
        return self._parse_response(response, fields)

    def _truncate(self, text: str, max_chars: int = 60000) -> str:
        """テキストを制限文字数内に収める。

        文書の先頭と末尾を優先（キーワードが両端に多いため）。
        """
        if len(text) <= max_chars:
            return text

        head_len = max_chars * 3 // 4
        tail_len = max_chars - head_len
        return (
            text[:head_len]
            + "\n\n... [中略] ...\n\n"
            + text[-tail_len:]
        )

    def _parse_response(
        self,
        response: dict[str, Any],
        fields: list[str] | None = None,
    ) -> ExtractionResult:
        """LLM 応答をパースして ExtractionResult を生成。"""
        content = response.get("content", "")
        if isinstance(content, list):
            content = " ".join(block.get("text", "") for block in content if block.get("type") == "text")

        parsed = safe_json_parse(content)
        if parsed is None:
            return ExtractionResult(
                document_id="",
                extraction_mode=ExtractionMode.LLM,
                errors=["LLM response is not valid JSON"],
            )

        field_results = {}
        for field_name in (fields or parsed.keys()):
            if field_name in parsed:
                field_results[field_name] = FieldResult(
                    field=field_name,
                    value=parsed[field_name],
                    confidence=0.85,
                    source="llm",
                )

        return ExtractionResult(
            document_id="",
            extraction_mode=ExtractionMode.LLM,
            fields=field_results,
        )
