"""
JP Recruit Extractor — Web UI 共通ユーティリティ

データ読み込み、パイプライン実行、品質集計の共通関数。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
RULES_PATH = DATA_DIR / "rules" / "field_rules.json"


# ── 結果読み込み ──


def load_latest_result() -> dict[str, Any] | None:
    """最新のルール抽出結果 JSON を読み込む。"""
    files = sorted(OUTPUT_DIR.glob("extraction_result_*.json"))
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_llm_result() -> dict[str, Any] | None:
    """最新の LLM 抽出結果を読み込む。"""
    files = sorted(OUTPUT_DIR.glob("llm_extraction_result_*.json"))
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ── 品質集計 ──


def compute_quality_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """抽出結果から品質メトリクスを計算。"""
    results = data.get("results", {})
    stats = data.get("stats", {})
    total = stats.get("total_cases", 0)

    metrics = {
        "total_cases": total,
        "files_processed": stats.get("files_processed", 0),
        "extraction_date": data.get("extraction_date", ""),
        "extraction_mode": stats.get("extraction_mode", ""),
        "rule_count": data.get("rule_library", {}).get("total_rules", 0),
    }

    # フィールド別カバー率
    counts: dict[str, int] = {}
    for result in results.values():
        for case in result.get("cases", []):
            for key, condition in _FIELD_CONDITIONS.items():
                if condition(case):
                    counts[key] = counts.get(key, 0) + 1

    metrics["field_coverage"] = {
        k: {"count": v, "total": total, "pct": round(v * 100 / total, 1) if total else 0}
        for k, v in counts.items()
    }

    # ファイル別件数
    metrics["per_file"] = {
        fname: res.get("case_count", 0) for fname, res in results.items()
    }

    return metrics


_FIELD_CONDITIONS: dict[str, callable] = {
    "案件名": lambda c: bool(c.get("project_name")),
    "必須スキル": lambda c: bool(c.get("skill_requirement")),
    "期間": lambda c: bool(c.get("period", {}).get("start_date")),
    "勤務地": lambda c: bool(c.get("location", {}).get("city")),
    "日本語レベル": lambda c: (
        c.get("japanese_level", {}).get("level", "not_specified") != "not_specified"
    ),
    "単価": lambda c: bool(c.get("rate", {}).get("min")),
    "全文保持": lambda c: bool(c.get("original_text")),
    "面接回数": lambda c: c.get("interviews") is not None,
    "募集人数": lambda c: c.get("headcount") is not None,
}


def get_all_cases(data: dict[str, Any]) -> list[dict[str, Any]]:
    """全案件をフラットリストで取得（ファイル名付き）。"""
    cases = []
    for fname, result in data.get("results", {}).items():
        for case in result.get("cases", []):
            case["_source_file"] = fname
            cases.append(case)
    return cases


def flatten_case(case: dict[str, Any]) -> dict[str, Any]:
    """案件を表示用フラット dict に変換。"""
    loc = case.get("location") or {}
    rate = case.get("rate") or {}
    period = case.get("period") or {}
    jl = case.get("japanese_level") or {}
    el = case.get("english_level") or {}
    trade = case.get("trade_flow") or {}

    def fmt_skills(skills):
        if not skills:
            return []
        return [s.strip() for s in skills if s.strip()]

    def jp_label(level):
        return {
            "native": "ネイティブ",
            "business": "ビジネス",
            "n2": "N2以上",
            "n3": "N3以上",
            "n4": "N4以上",
            "not_specified": "未設定",
        }.get(level, level or "未設定")

    def remote_label(policy):
        return {
            "full_remote": "フルリモート",
            "hybrid": "ハイブリッド",
            "office_only": "出社",
            "not_specified": "未設定",
        }.get(policy, policy or "未設定")

    return {
        "案件名": case.get("project_name", ""),
        "ファイル": case.get("_source_file", ""),
        "必須スキル": fmt_skills(case.get("skill_requirement")),
        "スキル数": len(fmt_skills(case.get("skill_requirement"))),
        "歓迎スキル": fmt_skills(case.get("preferred_skills")),
        "勤務地": loc.get("city", ""),
        "最寄駅": loc.get("station", ""),
        "リモート": remote_label(loc.get("remote_policy")),
        "単価(下限)": rate.get("min"),
        "単価(上限)": rate.get("max"),
        "単価単位": rate.get("unit", ""),
        "開始日": str(period.get("start_date") or "")[:10],
        "終了日": str(period.get("end_date") or "")[:10],
        "長期": "✓" if period.get("long_term") else "",
        "募集人数": case.get("headcount"),
        "業種": case.get("industry", ""),
        "契約形態": trade.get("contract_type_jp", trade.get("contract_type", "")),
        "日本語レベル": jp_label(jl.get("level")),
        "英語レベル": el.get("level", ""),
        "面接回数": case.get("interviews"),
        "即日参画": "✓" if case.get("immediate_start") else "",
        "備考": (case.get("remarks") or "")[:100],
        "original_text": case.get("original_text", ""),
    }


# ── パイプライン実行 ──


def run_rule_pipeline() -> bool:
    """ルール抽出パイプラインを実行。"""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py")],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        text=True,
    )
    return result.returncode == 0


def run_excel_export() -> bool:
    """Excel 出力を実行。"""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "export_excel.py")],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        text=True,
    )
    return result.returncode == 0


def run_llm_pipeline() -> tuple[bool, str]:
    """LLM 抽出パイプラインを実行。"""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "run_llm_pipeline.py")],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        text=True,
    )
    return result.returncode == 0, result.stdout + result.stderr


# ── ルール読み込み ──


def load_rules() -> dict[str, list[dict[str, Any]]]:
    """ルールライブラリを読み込む。"""
    if not RULES_PATH.exists():
        return {}
    try:
        with open(RULES_PATH, encoding="utf-8") as f:
            return json.load(f).get("rules", {})
    except (json.JSONDecodeError, OSError):
        return {}


def output_files() -> list[dict[str, Any]]:
    """出力ファイル一覧を返す。"""
    files = []
    for p in sorted(OUTPUT_DIR.glob("*"), reverse=True):
        files.append({
            "name": p.name,
            "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime),
            "suffix": p.suffix,
        })
    return files
