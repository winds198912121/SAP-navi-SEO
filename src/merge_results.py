#!/usr/bin/env python3
"""
結果マージスクリプト — LLM抽出結果とルール抽出結果を統合・重複除去。
"""

import json
import glob
from pathlib import Path
from datetime import datetime


def deduplicate_cases(cases: list[dict]) -> list[dict]:
    """重複案件を除去（プロジェクト名 + スキルの類似度で判定）。"""
    seen = set()
    unique = []

    for case in cases:
        name = (case.get("project_name") or "").strip().lower()
        skills = tuple(sorted(case.get("skill_requirement", []) or []))
        loc = (case.get("location", {}) or {}).get("city", "") or ""

        key = (name[:30], skills[:5], loc[:10])

        if key not in seen:
            seen.add(key)
            unique.append(case)

    return unique


def merge_rule_and_llm(rule_path: str, llm_path: str, output_path: str):
    """ルール結果とLLM結果をマージして最終出力を生成。"""
    with open(rule_path) as f:
        rule_data = json.load(f)

    with open(llm_path) as f:
        llm_data = json.load(f)

    merged_results = {}
    total_cases = 0

    for filename in ["案件1.txt", "案件List.md", "7月SAP案件一覧_0610.xlsx"]:
        rule_result = rule_data["results"].get(filename, {})
        llm_result = llm_data["results"].get(filename, {})

        rule_cases = rule_result.get("cases", []) if "cases" in rule_result else []
        llm_cases = llm_result.get("cases", []) if "cases" in llm_result else []

        # LLM結果を重複除去
        llm_cases = deduplicate_cases(llm_cases)

        # マージ戦略:
        # - 案件List.md → LLM結果優先（セクション分割が正確）
        # - SAP Excel → LLM結果優先（行ごとに正確に分割）
        # - 案件1.txt → LLM結果優先（スキル抽出が正確）
        if filename == "案件List.md":
            # LLMの結果を基本に、ルールベースの情報で補完
            merged = merge_cases(llm_cases, rule_cases)
        elif filename == "7月SAP案件一覧_0610.xlsx":
            # LLM結果の重複除去版
            merged = llm_cases
        else:
            # 案件1.txt: LLM結果（スキルが正確）
            merged = llm_cases

        merged_results[filename] = {
            "file": filename,
            "case_count": len(merged),
            "rule_count": len(rule_cases),
            "llm_count": len(llm_cases),
            "cases": merged,
        }
        total_cases += len(merged)

    output = {
        "extraction_date": datetime.now().isoformat(),
        "stats": {
            "total_cases": total_cases,
            "files_processed": 3,
            "extraction_mode": "hybrid",
            "model": llm_data.get("stats", {}).get("model", "unknown"),
        },
        "results": merged_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ マージ結果を保存: {output_path}")
    print(f"   全案件数: {total_cases}")
    for fname, r in merged_results.items():
        print(f"   {fname}: {r['case_count']}件 (ルール:{r['rule_count']} → LLM:{r['llm_count']} → 統合:{r['case_count']})")

    return output


def merge_cases(primary: list[dict], secondary: list[dict]) -> list[dict]:
    """LLM結果を主に、ルール結果で不足フィールドを補完。"""
    if not primary:
        return secondary

    # 案件名をインデックスに
    primary_names = {}
    for i, case in enumerate(primary):
        name = case.get("project_name", "") or ""
        if name:
            primary_names[name[:30]] = i

    for rule_case in secondary:
        rule_name = rule_case.get("project_name", "") or ""
        if not rule_name:
            continue

        # 既存LLM結果にルールのフィールドを補完
        match_key = rule_name[:30]
        if match_key in primary_names:
            idx = primary_names[match_key]
            existing = primary[idx]
            for field in ["rate", "period", "headcount", "industry", "location", "interviews"]:
                if field not in existing or not existing.get(field, {}):
                    existing[field] = rule_case.get(field)
                elif isinstance(existing[field], dict) and isinstance(rule_case.get(field), dict):
                    for k, v in rule_case[field].items():
                        if v is not None and v != "" and v != [] and v != "not_specified":
                            if existing[field].get(k) in (None, "", "not_specified"):
                                existing[field][k] = v

            # original_text が LLM 結果にない場合、ルール結果で補完
            if not existing.get("original_text"):
                existing["original_text"] = rule_case.get("original_text")

    # 第2パス: まだ original_text がないケースをルール結果から補完
    rule_texts = {case.get("project_name", ""): case.get("original_text", "") for case in secondary}
    for case in primary:
        if not case.get("original_text"):
            name = case.get("project_name") or ""
            if name in rule_texts and rule_texts[name]:
                case["original_text"] = rule_texts[name]
            else:
                for rn, ot in rule_texts.items():
                    if ot and (rn in name or name in rn):
                        case["original_text"] = ot
                        break


    return primary
if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent / "data" / "output"

    # Find latest files
    rule_files = sorted(glob.glob(str(data_dir / "extraction_result_*.json")))
    llm_files = sorted(glob.glob(str(data_dir / "llm_extraction_result_*.json")))

    if not rule_files or not llm_files:
        print("ルール or LLM結果ファイルが見つかりません")
        exit(1)

    latest_rule = rule_files[-1]
    latest_llm = llm_files[-1]
    output_path = str(data_dir / f"final_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    print(f"ルール結果: {latest_rule}")
    print(f"LLM結果:   {latest_llm}")

    merge_rule_and_llm(latest_rule, latest_llm, output_path)
