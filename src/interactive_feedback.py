#!/usr/bin/env python3
"""
インタラクティブフィードバックループ — ルール抽出 → ユーザー確認 → LLM修正 → ルール書き込み

フロー:
  1. ルール抽出パイプライン実行 (LLM不使用)
  2. JSON + Excel 出力
  3. ユーザーに結果確認
  4. OK → 必要に応じてルール書き込み → 終了
  5. NG → ユーザーが問題を入力 → LLM分析 → 修正結果表示 → 3に戻る
  7. ユーザーが満足 → ルール自動生成 → ルールライブラリに書き込み
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_fix import analyze_and_fix, explain_correction
from src.rule_writer import (
    write_rules_from_feedback,
    describe_field,
    resolve_rule_field,
    MODEL_FIELD_TO_RULE_FIELD,
)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
RULES_PATH = DATA_DIR / "rules" / "field_rules.json"


def print_header(text: str):
    """整形済みヘッダー表示。"""
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def run_pipeline() -> tuple[bool, str]:
    """ルール抽出パイプラインを実行する (LLM不使用)。"""
    import subprocess
    print_header("📊 ルール抽出パイプライン実行")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py")],
        capture_output=False,
        cwd=str(PROJECT_ROOT),
    )
    success = result.returncode == 0

    # 最新のJSON結果を取得
    json_files = sorted(OUTPUT_DIR.glob("extraction_result_*.json"))
    latest_json = str(json_files[-1]) if json_files else ""

    if success and latest_json:
        print(f"  ✅ 抽出完了 → {latest_json}")
        # Excelも出力
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "src" / "export_excel.py")],
            capture_output=False,
            cwd=str(PROJECT_ROOT),
        )
    else:
        print("  ❌ パイプライン実行に失敗しました")
        if not latest_json:
            print("  ⚠ 出力ファイルが見つかりません")

    return success, latest_json


def load_latest_result(json_path: str) -> dict:
    """最新の抽出結果JSONを読み込む。"""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def show_case_list(data: dict):
    """案件一覧を表示する。"""
    results = data.get("results", {})
    total = data.get("stats", {}).get("total_cases", 0)
    print(f"\n📋 全 {total} 件の案件:")
    print(f"   {'#':<4} {'案件名':<40} {'ファイル':<25} {'スキル数':<8}")
    print(f"   {'-'*4} {'-'*40} {'-'*25} {'-'*8}")

    idx = 0
    for fname, result in results.items():
        fname_short = Path(fname).name
        for case in result.get("cases", []):
            idx += 1
            name = (case.get("project_name") or "?")[:38]
            sk_count = len(case.get("skill_requirement") or [])
            print(f"   {idx:<4} {name:<40} {fname_short:<25} {sk_count:<8}")


def show_case_detail(case: dict):
    """案件の詳細を表示する。"""
    loc = case.get("location") or {}
    rate = case.get("rate") or {}
    period = case.get("period") or {}
    jl = case.get("japanese_level") or {}
    trade = case.get("trade_flow") or {}

    print(f"\n{'─' * 60}")
    print(f"  案件名: {case.get('project_name', '?')}")
    print(f"  概要: {(case.get('project_description') or '')[:100]}")
    print(f"{'─' * 60}")
    print(f"  必須スキル: {', '.join(case.get('skill_requirement', []) or []) or '-'}")
    print(f"  歓迎スキル: {', '.join(case.get('preferred_skills', []) or []) or '-'}")
    print(f"  経験年数: {case.get('experience_years', {}).get('description', '-')}")
    print(f"  勤務地: {loc.get('city', '?')} / {loc.get('station', '?')} / {loc.get('remote_policy', '?')}")
    print(f"  単価: {rate.get('min', '?')} ~ {rate.get('max', '?')} 万円/月")
    print(f"  期間: {period.get('start_date', '?')} ~ {period.get('end_date', '?')} (長期:{period.get('long_term', '?')})")
    print(f"  募集人数: {case.get('headcount', '?')}")
    print(f"  業種: {case.get('industry', '-')}")
    print(f"  契約形態: {trade.get('contract_type_jp', trade.get('contract_type', '?'))}")
    print(f"  日本語レベル: {jl.get('level', '?')} ({jl.get('level_jp', '')})")
    print(f"  面接回数: {case.get('interviews', '?')}")
    print(f"  即日参画: {'✓' if case.get('immediate_start') else '-'}")
    if case.get("remarks"):
        print(f"  備考: {case.get('remarks', '')[:200]}")
    print(f"{'─' * 60}")


def select_case(data: dict) -> tuple[str, dict] | None:
    """ユーザーに案件を選択させる。"""
    results = data.get("results", {})
    all_cases = []
    case_map = {}  # idx → (filename, case_dict)

    idx = 0
    for fname, result in results.items():
        for case in result.get("cases", []):
            idx += 1
            case_map[idx] = (fname, case)
            all_cases.append(case)

    if not all_cases:
        print("  案件データがありません。")
        return None

    show_case_list(data)

    while True:
        choice = input("\n確認したい案件番号を入力 (1-{})、または 'all' で全件表示、 Enter でスキップ: ".format(len(all_cases))).strip()
        if not choice:
            return None
        if choice.lower() == "all":
            for idx, case in enumerate(all_cases, 1):
                show_case_detail(case)
            continue
        try:
            idx = int(choice)
            if 1 <= idx <= len(all_cases):
                fname, case = case_map[idx]
                show_case_detail(case)
                return (fname, case)
        except ValueError:
            pass
        print("  無効な入力です。")



def feedback_loop():
    """メインフィードバックループ。"""
    print_header("🔄 JP Recruit Extractor - インタラクティブフィードバックループ")
    print("  ルール抽出 → 確認 → LLM修正 → ルール書き込み")
    print("  (LLM使用時は DeepSeek API が必要)")

    latest_json = ""

    while True:
        print("\n  1. ルール抽出を実行 (LLM不使用)")
        print("  2. 既存の最新結果を確認")
        print("  3. 終了")
        choice = input("\n選択 (1-3): ").strip()

        if choice == "1":
            success, latest_json = run_pipeline()
            if not success:
                continue
            break
        elif choice == "2":
            json_files = sorted(OUTPUT_DIR.glob("extraction_result_*.json"))
            if json_files:
                latest_json = str(json_files[-1])
                print(f"   📄 最新結果: {latest_json}")
                break
            else:
                print("  ⚠ 抽出結果が見つかりません。先に [1] を実行してください。")
        elif choice == "3":
            print("\n  終了します。")
            return
        else:
            print("  無効な入力です。")

    data = load_latest_result(latest_json)

    # メインフィードバックループ
    round_num = 0
    rule_written = False

    while True:
        round_num += 1
        print_header(f"🔄 フィードバックラウンド {round_num}")

        # 案件選択
        selected = select_case(data)
        if selected is None:
            # 全体的な確認
            answer = input("\nすべての結果に満足していますか？ (y/n): ").strip().lower()
            if answer == "y":
                print_header("✅ 全件OK - 終了")
                print("  すべての抽出結果が確認されました。")
                return
            else:
                print("\nどの案件に問題がありますか？ 案件番号を入力してください。")
                continue

        fname, case = selected

        # この案件に満足しているか確認
        answer = input(f"\nこの案件「{case.get('project_name','?')[:30]}」の抽出結果は正しいですか？ (y/n): ").strip().lower()

        if answer == "y":
            print("  ✅ OK、次の案件に進みます。")
            continue

        # --- ここからLLM修正フロー ---
        original_text = case.get("original_text", "")
        if not original_text:
            print("  ⚠ この案件の原文がありません。LLM分析できません。")
            continue

        print_header("🤖 LLM分析")

        # 対象フィールドを尋ねる（マッピング情報付き）
        print("\n問題があるフィールド名を入力してください:")
        print("  フィールド名一覧 (モデル → ルールライブラリ):")
        for model_field in ["skill_requirement", "preferred_skills", "period", "rate", "project_name",
                            "location", "japanese_level", "english_level", "industry", "headcount",
                            "interviews", "immediate_start", "experience_years", "trade_flow", "remarks"]:
            rule_field = resolve_rule_field(model_field)
            rule_fname = describe_field(model_field)
            if rule_field and rule_field != model_field:
                print(f"    {model_field:25s} → {rule_field:20s} ({rule_fname})")
            elif rule_field:
                print(f"    {model_field:25s} → ({rule_fname})")
        target_field = input("\n  入力 (空Enter=全体分析): ").strip() or None
        if target_field:
            rule_field = resolve_rule_field(target_field)
            rule_fname = describe_field(target_field)
            if rule_field and rule_field != target_field:
                print(f"      → ルールライブラリのフィールド: {rule_field} ({rule_fname})")
            elif rule_field:
                print(f"      → フィールド説明: {rule_fname}")

        # 問題の説明
        print("\n何が問題ですか？ 具体的に教えてください。")
        print("  例: 「スキルにPythonが抜けている」「期間が8月ではなく7月から」「単価が間違っている」")
        user_feedback = input("  問題の説明: ").strip()

        if not user_feedback:
            print("  ⚠ 入力が空です。スキップします。")
            continue

        print("\n  🔍 LLMで分析中...（DeepSeek API呼び出し）")

        result = analyze_and_fix(
            original_text=original_text,
            rule_result=case,
            user_feedback=user_feedback,
            target_field=target_field,
        )

        explanations = result.get("analysis", "")
        corrections = result.get("corrections", {})

        # LLM分析結果の表示
        print("\n" + "=" * 60)
        print("  📋 LLM分析:")
        print("=" * 60)
        print(f"  {explanations}")

        if corrections:
            print(f"\n{'─' * 60}")
            print("  🔧 修正提案:")
            print(f"{'─' * 60}")
            for field, value in corrections.items():
                if isinstance(value, list):
                    val_str = ", ".join(str(v) for v in value)
                else:
                    val_str = str(value)
                print(f"    {field}: {val_str}")
            print(f"  確信度: {result.get('confidence', 0):.0%}")

        new_rule_hint = result.get("new_rule_hint", "")

        # ユーザー確認
        print(f"\n{'─' * 60}")
        accept = input("この修正で正しいですか？ (y/n): ").strip().lower()

        if accept == "y":
            print("  ✅ 修正を確認しました。")

            # ルール生成
            if new_rule_hint:
                # フィールド名をルールライブラリ用にマッピング
                llm_rule_field = resolve_rule_field(target_field) if target_field else None
                if llm_rule_field and llm_rule_field != target_field:
                    print(f"   ℹ️  LLM用フィールド名: {target_field} → {llm_rule_field}")

                print("\n  📝 新しいルール生成中...（DeepSeek API呼び出し）")
                write_rules_from_feedback(
                    original_text=original_text,
                    user_feedback=user_feedback,
                    llm_analysis=explanations,
                    corrections=corrections,
                    target_field=llm_rule_field or target_field,  # ルールライブラリのフィールド名を使用
                    auto_confirm=False,
                )

            # 続けるかどうか
            cont = input("\n続けて他の案件を確認しますか？ (y/n): ").strip().lower()
            if cont == "n":
                print_header("👋 終了")
                print("  お疲れ様でした。")
                return
            # パイプライン再実行（ルール追加後）
            if new_rule_hint:
                rerun = input("ルールを反映するため再実行しますか？ (y/n): ").strip().lower()
                if rerun == "y":
                    success, latest_json = run_pipeline()
                    if success:
                        data = load_latest_result(latest_json)
            continue
        else:
            # 修正を拒否 → 再度フィードバックを受ける
            print("  ⏭ 修正をスキップしました。")
            retry = input("問題を修正して再度送信しますか？ (y/n): ").strip().lower()
            if retry == "n":
                continue
            # ループ継続 → 再度ユーザーの問題説明を受ける


def main():
    try:
        feedback_loop()
    except KeyboardInterrupt:
        print("\n\n👋 中断されました。")
        sys.exit(0)


if __name__ == "__main__":
    main()
