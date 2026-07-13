"""
LLM 分析モジュール — ユーザーフィードバックから問題を分析し修正結果を生成。

ユーザーが「この案件のスキルが足りない」「期間が間違ってる」などと
フィードバックを入力したときに、元のテキストとルール抽出結果をLLMが
分析して修正提案を出力する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.llm_engine.deepseek_client import DeepSeekClient


def analyze_and_fix(
    original_text: str,
    rule_result: dict | None,
    user_feedback: str,
    target_field: str | None = None,
) -> dict[str, Any]:
    """LLMで問題を分析し、修正案を生成する。

    Args:
        original_text: 案件の原文テキスト
        rule_result: ルール抽出結果（該当件の全フィールド値）
        user_feedback: ユーザーのフィードバック記述
        target_field: 対象フィールド（Noneの場合は全フィールド対象）

    Returns:
        dict: {
            "analysis": str,        # LLMの問題分析
            "corrections": dict,    # 修正後のフィールド値
            "new_rule_hint": str,   # 新ルール作成のヒント
            "confidence": float,    # 修正の確信度 (0-1)
        }
    """
    system_prompt = """あなたは日本IT招聘案件のデータ抽出専門家です。
ルールベースの抽出結果に対して、ユーザーからのフィードバックを分析し、
正確な抽出結果を提供してください。

期待される出力は以下のJSON形式:
{
  "analysis": "問題の分析と、元テキストから読み取れる正しい情報の説明を日本語で",
  "corrections": {
    "field_name": "修正後の値（文字列または配列）"
  },
  "new_rule_hint": "この修正から学べる新しいルールのパターンを日本語で簡潔に説明",
  "confidence": 0.95
}

注意:
- 案件原文から正確に読み取れる情報のみを使用すること
- 原文にない情報は推測しないこと
- スキルは配列形式で出力すること
- 日付は YYYY-MM-DD 形式で出力すること
- 日本語レベルは native / business / n2 / n3 / n4 のいずれか
- 契約形態は jun_inin / ukeoi / haken / ses のいずれか
"""

    user_msgs = [
        {
            "role": "user",
            "content": f"## 案件原文\n{original_text[:5000]}"
        }
    ]
    if rule_result:
        user_msgs.append({
            "role": "user",
            "content": f"## 現在のルール抽出結果\n{json.dumps(rule_result, ensure_ascii=False, indent=2)[:2000]}"
        })
    if target_field:
        user_msgs.append({
            "role": "user",
            "content": f"## 対象フィールド\n{target_field}"
        })
    user_msgs.append({
        "role": "user",
        "content": f"## ユーザーフィードバック\n{user_feedback}\n\n上記のフィードバックを分析し、修正結果をJSON形式で出力してください。"
    })

    client = DeepSeekClient()
    response = client.chat_completion(
        system=system_prompt,
        messages=user_msgs,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4096,
    )

    try:
        result = json.loads(response["content"])
    except json.JSONDecodeError:
        result = {
            "analysis": "LLM応答のパースに失敗しました。再試行してください。",
            "corrections": {},
            "new_rule_hint": "",
            "confidence": 0.0,
        }

    return result


def explain_correction(corrections: dict, analysis: str) -> str:
    """修正内容をユーザー向けに説明する文章を生成。"""
    lines = ["📋 LLM分析結果:\n", analysis, "\n"]
    if corrections:
        lines.append("🔧 修正提案:\n")
        for field, value in corrections.items():
            if isinstance(value, list):
                val_str = "\n  - " + "\n  - ".join(str(v) for v in value)
            else:
                val_str = str(value)
            lines.append(f"  • {field}: {val_str}")
    return "\n".join(lines)
