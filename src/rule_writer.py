"""
ルール自動生成モジュール — LLM修正結果から新しい抽出ルールを生成・書き込み。

ユーザーが修正を確認した後、どのようなパターンでルールが抽出に失敗したかを
分析し、新しいルールを data/rules/field_rules.json に追加する。
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_engine.deepseek_client import DeepSeekClient

RULES_PATH = Path(__file__).parent.parent / "data" / "rules" / "field_rules.json"

# ── フィールド名マッピング ──
# RecruitmentCase のモデルフィールド名 → ルールライブラリのフィールド名
MODEL_FIELD_TO_RULE_FIELD: dict[str, str] = {
    "skill_requirement": "skill_must",
    "preferred_skills": "skill_preferred",
    "project_name": "project_name",
    "project_description": None,  # ルールなし（LLM専用）
    "japanese_level": "japanese_level",
    "english_level": "english_level",
    "experience_years": "experience_years",
    "location": "location",
    "trade_flow": "trade_flow",
    "working_hours": None,  # ルールなし
    "period": "period",
    "rate": "rate",
    "headcount": "headcount",
    "interviews": "interviews",
    "industry": "industry",
    "immediate_start": "immediate_start",
    "screening_flow": None,
    "remarks": "remarks",
    "source": None,
    "original_text": None,
}
# 逆マッピング（表示用）
RULE_FIELD_TO_MODEL_FIELD: dict[str, str] = {
    v: k for k, v in MODEL_FIELD_TO_RULE_FIELD.items() if v
}
# 定義済みマッピングにないフィールド名はそのまま使う（フォールバック）


def resolve_rule_field(model_field: str) -> str:
    """モデルフィールド名 → ルールライブラリのフィールド名に変換。"""
    mapped = MODEL_FIELD_TO_RULE_FIELD.get(model_field)
    if mapped is None and model_field in MODEL_FIELD_TO_RULE_FIELD:
        return None  # ルール対象外フィールド
    if mapped:
        if mapped != model_field:
            print(f"   ℹ️  フィールド名マッピング: {model_field} → {mapped}")
        return mapped
    return model_field  # 未定義のフィールドはそのまま


def describe_field(field: str) -> str:
    """フィールド名の説明を返す（ユーザー向け）。"""
    descriptions = {
        "skill_must": "必須スキル",
        "skill_preferred": "歓迎スキル",
        "skill_requirement": "必須スキル（ルール上は skill_must）",
        "preferred_skills": "歓迎スキル（ルール上は skill_preferred）",
        "period": "期間",
        "rate": "単価",
        "project_name": "案件名",
        "location": "勤務地",
        "japanese_level": "日本語レベル",
        "english_level": "英語レベル",
        "industry": "業種",
        "trade_flow": "商流",
        "headcount": "募集人数",
        "interviews": "面接回数",
        "immediate_start": "即日参画",
        "experience_years": "経験年数",
        "remarks": "備考",
    }
    return descriptions.get(field, field)


def get_existing_rules() -> dict[str, list[dict]]:
    """既存のルールライブラリを読み込む。"""
    if not RULES_PATH.exists():
        return {}
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f).get("rules", {})


def save_rules(rules: dict[str, list[dict]]):
    """ルールライブラリを保存する。"""
    with open(RULES_PATH, encoding="utf-8") as f:
        existing = json.load(f)
    existing["rules"] = rules
    existing["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"   ✅ ルール更新完了: {RULES_PATH}")


def next_rule_id(field: str, existing: list[dict]) -> str:
    """フィールド内の次のルールIDを生成する。

    通常: field_001, field_002, ...
    rowtext専用: field_rowtext_001, field_rowtext_002, ...
    両方のIDパターンを考慮して最大値+1を返す。
    """
    max_num = 0
    prefix_pattern = re.escape(field)
    for rule in existing:
        rid = rule.get("id", "")
        # 通常パターン: field_NNN
        m = re.search(rf"^{prefix_pattern}_(\d+)$", rid)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
        # rowtextパターンもチェック（別カウントだが最大値を考える）
        m2 = re.search(rf"{prefix_pattern}_rowtext_(\d+)", rid)
        if m2:
            pass  # rowtextは別命名なので無視
    return f"{field}_{max_num + 1:03d}"


def generate_rules_from_correction(
    original_text: str,
    user_feedback: str,
    llm_analysis: str,
    corrections: dict,
    target_field: str | None = None,
) -> list[dict]:
    """LLM修正結果から新しいルールを生成する。

    Args:
        original_text: 案件原文
        user_feedback: ユーザーフィードバック
        llm_analysis: LLMの問題分析
        corrections: LLM修正結果
        target_field: 修正対象フィールド

    Returns:
        list[dict]: 新しいルール定義のリスト
    """
    existing_rules = get_existing_rules()

    system_prompt = """あなたは日本IT招聘案件のルール生成専門家です。
LLMの分析結果とユーザーフィードバックから、新しい抽出ルールを生成してください。

既存のルールライブラリを分析し、不足しているパターンを特定して
新しいルールを提案します。

各ルールは以下の形式:
{
  "id": "field_001",
  "description": "ルールの説明（日本語）",
  "pattern": "正規表現パターン"
}

ルール生成の原則:
- 新しいルールは既存ルールと重複しないこと
- 正規表現は具体的すぎず汎用的すぎないバランス
- ルールIDのプレフィックスはルールライブラリに存在するフィールド名に従うこと
  （例: skill_requirement → skill_must, preferred_skills → skill_preferred）
- 説明は日本語でわかりやすく

既存フィールド一覧: """ + str(list(existing_rules.keys())) + """
"""

    # 既存ルールのサマリー
    existing_summary = {}
    for field, rules in existing_rules.items():
        existing_summary[field] = {
            "count": len(rules),
            "patterns": [r.get("description", r.get("id", "")) for r in rules[-5:]],  # 最新5件
        }

    user_msgs = [
        {"role": "user", "content": f"## 既存ルールサマリー\n{json.dumps(existing_summary, ensure_ascii=False, indent=2)[:2000]}"},
        {"role": "user", "content": f"## 案件原文\n{original_text[:3000]}"},
        {"role": "user", "content": f"## ユーザーフィードバック\n{user_feedback}"},
        {"role": "user", "content": f"## LLM分析\n{llm_analysis}"},
        {"role": "user", "content": f"## 修正内容\n{json.dumps(corrections, ensure_ascii=False, indent=2)}"},
    ]

    if target_field:
        user_msgs.append({"role": "user", "content": f"## 対象フィールド\n{target_field}"})

    user_msgs.append({
        "role": "user",
        "content": """上記の分析から、既存ルールに不足しているパターンを特定し、
新しいルールをJSON配列形式で出力してください。

出力形式:
{
  "field": "対象フィールド名",
  "rules": [{ "id": "xxx", "description": "説明", "pattern": "正規表現" }],
  "explanation": "なぜこのルールが必要か"
}

ルールが不要と判断した場合は、rules を空配列にしてください。"""
    })

    client = DeepSeekClient()
    response = client.chat_completion(
        system=system_prompt,
        messages=user_msgs,
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=4096,
    )

    try:
        result = json.loads(response["content"])
        return result
    except json.JSONDecodeError:
        return {"field": target_field or "unknown", "rules": [], "explanation": "ルール生成に失敗しました"}


def apply_new_rules(
    field: str,
    new_rules: list[dict],
    explanation: str,
    original_model_field: str | None = None,
) -> int:
    """新しいルールをルールライブラリに書き込む。

    Args:
        field: 対象フィールド
        new_rules: 新ルールのリスト
        explanation: 説明

    Returns:
        int: 追加したルール数
    """
    if not new_rules:
        print("   ⚠ 追加するルールがありません。")
        return 0

    # フィールド名マッピング解決
    rule_field = resolve_rule_field(field)
    # 解決できなかった（ルール対象外フィールドとして定義されている）
    if rule_field is None:
        print(f"   ⚠ 「{field}」はルール対象外フィールドです。スキップします。")
        print(f"   💡 ルールが定義されているフィールド: skill_must, skill_preferred, period, rate, project_name, ...")
        return 0
    # 元のモデルフィールド名と異なる場合、ユーザーに表示上だけオリジナルを残す
    display_field = field
    if original_model_field:
        display_field = original_model_field
    if rule_field != field or (original_model_field and original_model_field != rule_field):
        print(f"   📍 ルール書き込み先: 「{rule_field}」（モデルフィールド: {display_field}）")
    field = rule_field  # ルールライブラリのフィールド名を使用

    with open(RULES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if field not in data["rules"]:
        data["rules"][field] = []

    existing_ids = {r.get("id") for r in data["rules"][field]}

    added = 0
    for rule in new_rules:
        rid = rule.get("id", "")
        if rid in existing_ids or not rid:
            # IDが重複または空の場合は自動採番
            rid = next_rule_id(field, data["rules"][field])
            rule["id"] = rid
        # 必要フィールドの確認
        if "description" not in rule:
            rule["description"] = f"LLM自動生成: {explanation[:80]}"
        if "priority" not in rule:
            rule["priority"] = 50
        if "field" not in rule:
            rule["field"] = field
        data["rules"][field].append(rule)
        existing_ids.add(rid)
        added += 1

    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return added


def write_rules_from_feedback(
    original_text: str,
    user_feedback: str,
    llm_analysis: str,
    corrections: dict,
    target_field: str | None = None,
    auto_confirm: bool = False,
) -> bool:
    """フィードバックループの結果からルールを生成・書き込む。

    Returns:
        bool: ルール書き込み成功
    """
    result = generate_rules_from_correction(
        original_text=original_text,
        user_feedback=user_feedback,
        llm_analysis=llm_analysis,
        corrections=corrections,
        target_field=target_field,
    )

    rules = result.get("rules", [])
    raw_field = result.get("field", target_field or "unknown")
    explanation = result.get("explanation", "")

    # フィールド名マッピング解決
    rule_field = resolve_rule_field(raw_field)
    if rule_field is None:
        print(f"\n   ⚠ 「{raw_field}」はルール対象外フィールドです。スキップします。")
        return False

    field = rule_field
    if rule_field != raw_field:
        print(f"\n   ℹ️  フィールド名変換: {raw_field} → {rule_field}")

    if not rules:
        print("\n   ℹ️  ルール生成結果: 新しいルールは不要（既存ルールで対応可能）")
        return False

    print(f"\n📝 新しいルール候補 ({field}):")
    for i, rule in enumerate(rules, 1):
        print(f"  [{i}] {rule.get('id', '?')}: {rule.get('description', '?')}")
        print(f"      パターン: {rule.get('pattern', '?')[:80]}")
    print(f"\n   💡 {explanation[:200]}")

    if not auto_confirm:
        answer = input("\n上記のルールをルールライブラリに追加しますか？ (y/n): ").strip().lower()
        if answer != "y":
            print("   ⏭ ルール追加をスキップしました。")
            return False

    count = apply_new_rules(field, rules, explanation, original_model_field=raw_field)
    print(f"   ✅ {count} 件のルールを追加しました。")

    # ルール追加後に再実行を促す
    print("\n   💡 次のコマンドで再実行してください:")
    print("      python3 src/run_pipeline.py && python3 src/export_excel.py")

    return True
