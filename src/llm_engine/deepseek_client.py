"""DeepSeek API クライアント（OpenAI互換APIを使用）."""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API クライアント.

    DeepSeek は OpenAI 互換 API を提供しているため、openai パッケージを
    base_url と api_key を差し替えて利用します。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.model = model or settings.llm_model

        if not self.api_key:
            raise ValueError(
                "DeepSeek API Key が設定されていません。"
                ".env ファイルに DEEPSEEK_API_KEY=sk-... を設定してください。"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat_completion(
        self,
        system: str,
        messages: list[dict[str, str]],
        response_format: dict | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """LLM チャット完了 API を呼び出す。

        Args:
            system: システムプロンプト
            messages: ユーザーメッセージのリスト
            response_format: レスポンスフォーマット（DeepSeekはJSON mode対応）
            temperature: 生成温度
            max_tokens: 最大トークン数

        Returns:
            dict: API応答、{"content": str, "usage": {...}} 形式
        """
        api_messages = [{"role": "system", "content": system}]
        api_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # JSON mode（DeepSeekはベータ対応）
        if response_format and response_format.get("type") == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            result = {
                "content": choice.message.content or "",
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            logger.info(
                f"DeepSeek API call: model={self.model}, "
                f"tokens={result['usage']['total_tokens']}, "
                f"finish_reason={choice.finish_reason}"
            )

            return result

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """トークン数の概算（文字数ベースの推定）。"""
        # DeepSeekは中国語/日本語混在のため文字数/2 程度で概算
        return len(text) // 2
