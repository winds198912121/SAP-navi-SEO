"""プロンプトビルダー — LLM用プロンプトの生成と管理."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.schema import get_schema_as_json

# デフォルトのシステムプロンプト
DEFAULT_SYSTEM_PROMPT = """You are a specialized data extraction assistant for Japanese IT recruitment documents.

## Your Task
Extract structured information from the provided Japanese recruitment case document.
The document may contain: project name, skills required, location, rate/salary, period,
headcount, industry, trade flow, language requirements, working hours, and other details.

## Output Format
You MUST respond with a valid JSON object matching the provided schema.
If a field's value is not found in the document, use null.

## Quality Guidelines
- Be precise: extract EXACTLY what the document says, do not infer
- For skill requirements: list each skill separately, split by 、・/
- Japanese level: map to standard levels (native/business/n2/n3/n4)
- Contract type: map to (jun_inin/ukeoi/haken/ses/other)
- Do NOT merge preferred skills into required skills
"""

# デフォルトのユーザープロンプト
DEFAULT_USER_PROMPT = """以下の日本IT招聘案件の文書から、JSONスキーマに従って構造化データを抽出してください。

## 文書内容
{text}

## 出力JSONスキーマ
{schema}

## 重要
- 該当する値が文書にない場合は null を設定してください
- 日付は YYYY-MM-DD 形式に統一
- 金額は数値のみ抽出、単位は unit フィールド指定
- スキルは個別要素として配列で出力
- 推測や補完はしないでください

## 出力 (JSON only)
"""


class PromptBuilder:
    """LLM用プロンプトの構築を管理。"""

    def __init__(self, template_dir: str | Path | None = None):
        self._system_templates: dict[str, str] = {
            "extraction_system": DEFAULT_SYSTEM_PROMPT,
        }
        self._user_templates: dict[str, str] = {
            "extraction_user": DEFAULT_USER_PROMPT,
        }

        if template_dir:
            self._load_from_dir(template_dir)

    def register(
        self,
        name: str,
        system: str | None = None,
        user: str | None = None,
    ) -> None:
        """テンプレートを登録。"""
        if system:
            self._system_templates[name] = system
        if user:
            self._user_templates[name] = user

    def build(
        self,
        system_key: str = "extraction_system",
        user_key: str = "extraction_user",
        context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """プロンプトを構築して返す。"""
        ctx = context or {}
        system = self._system_templates.get(system_key, "")
        user = self._user_templates.get(user_key, "")

        for key, value in ctx.items():
            placeholder = "{" + key + "}"
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            system = system.replace(placeholder, str(value))
            user = user.replace(placeholder, str(value))

        # スキーマがcontextになければデフォルトを注入
        if "{schema}" in user and "schema" not in ctx:
            user = user.replace("{schema}", get_schema_as_json())

        return {"system": system, "user": user}

    def _load_from_dir(self, template_dir: str | Path) -> None:
        """テンプレートディレクトリから読み込み。"""
        dir_path = Path(template_dir)
        if not dir_path.is_dir():
            return
        for f in dir_path.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            name = f.stem
            if name.endswith("_system"):
                self._system_templates[name] = content
            elif name.endswith("_user"):
                self._user_templates[name] = content
