#!/usr/bin/env python3
"""
DeepSeek LLM 抽出パイプライン

3つのファイルを DeepSeek LLM で処理:
1. 案件1.txt
2. 案件List.md
3. 7月SAP案件一覧_0610.xlsx
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# src をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.llm_engine.deepseek_client import DeepSeekClient
from src.common.schema import get_schema_as_json
from src.common.utils import safe_json_parse, generate_document_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a specialized data extraction assistant for Japanese IT recruitment documents (日本IT招聘案件).

## Your Task
Extract structured information from the provided Japanese recruitment case document(s).
The document contains one or more recruitment cases with fields like:
- project_name: 案件名 / プロジェクト名
- project_description: 案件概要
- skill_requirement: 必須スキル（array of strings）
- preferred_skills: 歓迎スキル（array of strings）
- location: 勤務地 {city, station, remote_policy}
- rate: 単価 {min, max, unit, currency, note}
- period: 期間 {start_date, end_date, duration_months, long_term, note}
- headcount: 募集人数（integer）
- industry: 業種
- trade_flow: 商流 {contract_type, layers, end_client}
- japanese_level: 日本語レベル {level, detail}
- english_level: 英語レベル {level, detail}
- working_hours: 勤務時間
- interviews: 面接回数（integer）
- immediate_start: 即日参画可否（boolean）
- remarks: 備考

## Output Rules
1. Output VALID JSON ONLY — no markdown, no commentary.
2. If the document contains MULTIPLE cases, output a JSON array: [{...}, {...}].
3. If single case, output a JSON object: {...}.
4. For fields not found, use null (do NOT fabricate data).
5. Dates: convert to YYYY-MM-DD format. Convert 令和/平成 years to Gregorian.
   **RULE: 月のみで年が明示されていない場合、現在年（2026年）をデフォルトとして使用する。**
   **RULE: 月が現在月（6月）より前の月（1月〜5月）の場合は翌年扱いとする。**
   **RULE: 「即日」「Immediate」「随時」は本日（2026-06-28）を開始日として設定する。**
6. Rate:
   - "130K JPY/month" → {"min": 13.0, "max": 13.0, "unit": "monthly", "note": "130K JPY/月", "currency": "JPY"}
   - "70-80万円/月額" → {"min": 70, "max": 80, "unit": "monthly", "currency": "JPY"}
7. Skills: list individually. Split on 、・/ and bullet points.
8. remote_policy: "full_remote" | "hybrid" | "office_only" | "not_specified"
9. contract_type: "jun_inin" | "ukeoi" | "haken" | "ses" | "other"
10. japanese_level.level: "native" | "business" | "n2" | "n3" | "n4" | "not_specified"
11. Be precise — extract EXACTLY what the document says, do not infer.
12. Separate "must have" skills (必須) from "nice to have" (歓迎/尚可)."""


def read_document(file_path: Path) -> str:
    """Read document and return text content."""
    ext = file_path.suffix.lower()

    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(str(file_path))
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c else "" for c in row]
            rows.append(" | ".join(cells))
        wb.close()
        return "\n".join(rows)

    elif ext == ".pdf":
        import fitz
        doc = fitz.open(str(file_path))
        text = "\n\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text

    else:
        return file_path.read_text(encoding="utf-8")


def extract_with_llm(client: DeepSeekClient, text: str, max_retries: int = 2, _depth: int = 0) -> list[dict]:
    """Use DeepSeek to extract structured data from text.

    For large documents, splits into chunks to avoid token limit issues.
    _depth tracks recursion level to prevent infinite loops.
    """
    if _depth > 2:
        logger.warning("Max recursion depth reached, returning empty")
        return []

    # For large documents, split into manageable chunks
    MAX_CHARS = 2500

    if len(text) > MAX_CHARS:
        logger.info(f"Large document ({len(text)} chars), splitting into chunks (depth={_depth})")
        return extract_large_document(client, text, max_retries, _depth)

    schema_str = get_schema_as_json()

    user_prompt = f"""以下の日本IT招聘案件の文書から構造化データを抽出してください。

## 文書内容
{text}

## 出力JSONスキーマ（参考）
{schema_str[:2000]}

## 注意
- 複数の案件がある場合は配列として出力してください
- 単一案件の場合はオブジェクトとして出力してください
- 該当する値がないフィールドは null にしてください
- 日付は YYYY-MM-DD 形式に統一
- 金額は数値のみ（万円単位）
- 推測や補完はしないでください

## 出力（JSON only）
"""

    for attempt in range(max_retries):
        try:
            response = client.chat_completion(
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                response_format={"type": "json_object"},
                temperature=0.05,
                max_tokens=8192,
            )

            content = response["content"]
            finish_reason = response.get("finish_reason", "")
            usage = response.get("usage", {})

            logger.info(f"LLM response: {usage.get('total_tokens', '?')} tokens, "
                        f"content length={len(content)}, finish={finish_reason}")

            if finish_reason == "length":
                logger.warning(f"Response truncated (length). Attempt {attempt+1}")
                if attempt < max_retries - 1:
                    continue

            parsed = safe_json_parse(content)
            if parsed is None:
                logger.warning(f"Attempt {attempt+1}: JSON parse failed, retrying...")
                continue

            # Normalize to list of cases
            cases = normalize_cases(parsed)
            if cases:
                # 各ケースに抽出元の原文を注入
                for c in cases:
                    c["original_text"] = text
                return cases

        except Exception as e:
            logger.error(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)

    return []


def extract_large_document(client: DeepSeekClient, text: str, max_retries: int = 2, _depth: int = 0) -> list[dict]:
    """Split a large document into sections and extract each separately."""
    lines = text.split("\n")

    # Check if this looks like a table (many lines with | separator)
    pipe_count = sum(1 for l in lines if "|" in l)
    is_table = pipe_count > len(lines) * 0.3

    if is_table:
        logger.info("Detected table format, splitting by rows")
        sections = [line for line in lines if line.strip() and "|" in line and len(line) > 20 and not line.startswith("No |")]
        sections = [s for s in sections if len(s) > 30]
    else:
        # Try to split by case boundaries
        sections = []
        current = []

        case_markers = [
            "案件名", "■案件名", "■ 案件名", "案件1️⃣", "案件2️⃣",
            "\U0001f525", "!!", "❗", "❗️", "‼️",
            "直接客户", "Need candidates",
        ]

        for line in lines:
            is_start = any(line.strip().startswith(m) for m in case_markers) and len(line.strip()) > 5
            is_numbered = bool(re.match(r'^[①②③④⑤]\s', line.strip()))

            if (is_start or is_numbered) and current:
                sections.append("\n".join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            sections.append("\n".join(current))

    # Filter very short sections
    sections = [s for s in sections if len(s.strip()) > 30]

    logger.info(f"Document split into {len(sections)} sections (table={is_table})")

    all_cases = []
    for idx, section in enumerate(sections):
        logger.info(f"Processing section {idx+1}/{len(sections)} ({len(section)} chars)")
        cases = extract_with_llm(client, section, max_retries, _depth + 1)
        all_cases.extend(cases)
        if cases:
            logger.info(f"  → {len(cases)} cases found")
        time.sleep(0.3)

    return all_cases


def normalize_cases(parsed) -> list[dict]:
    """Normalize parsed JSON into a list of case dicts."""
    if isinstance(parsed, list):
        cases = parsed
    elif isinstance(parsed, dict):
        if "cases" in parsed and isinstance(parsed["cases"], list):
            cases = parsed["cases"]
        elif "results" in parsed and isinstance(parsed["results"], list):
            cases = parsed["results"]
        else:
            cases = [parsed]
    else:
        return []

    # More lenient filtering: accept any dict with at least 2 informative fields
    valid = []
    for c in cases:
        if not isinstance(c, dict) or len(c) == 0:
            continue
        if c.get("project_name"):
            valid.append(c)
        else:
            # Count non-null fields as a heuristic
            filled = sum(1 for v in c.values() if v is not None and v != "" and v != [])
            if filled >= 2:
                valid.append(c)
    return valid


def run():
    """メイン実行"""
    data_dir = Path(__file__).parent.parent / "data"
    output_dir = data_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # DeepSeek クライアント初期化
    try:
        client = DeepSeekClient()
        logger.info(f"DeepSeek client initialized: model={client.model}, base_url={client.base_url}")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    files_to_process = [
        ("案件1.txt", "text"),
        ("案件List.md", "text"),
        ("7月SAP案件一覧_0610.xlsx", "excel"),
    ]

    all_results = {}
    stats = {
        "total_cases": 0,
        "files_processed": 0,
        "errors": 0,
        "extraction_mode": "llm_deepseek",
        "model": client.model,
    }

    for filename, fmt in files_to_process:
        file_path = data_dir / filename
        if not file_path.exists():
            logger.warning(f"ファイルが見つかりません: {file_path}")
            all_results[filename] = {"error": "file not found"}
            stats["errors"] += 1
            continue

        print(f"\n{'='*60}")
        print(f"📄 LLM処理中: {filename}")
        print(f"{'='*60}")

        try:
            # Read document
            text = read_document(file_path)
            print(f"   文書サイズ: {len(text)} 文字")

            # LLM extraction
            start_time = time.time()
            cases = extract_with_llm(client, text)
            elapsed = time.time() - start_time

            if not cases:
                print(f"   ⚠ 抽出結果が空でした")
                all_results[filename] = {"file": filename, "format": fmt, "case_count": 0, "cases": [], "error": "empty result"}
                continue

            # Save result
            all_results[filename] = {
                "file": filename,
                "format": fmt,
                "case_count": len(cases),
                "llm_time_seconds": round(elapsed, 1),
                "cases": cases,
            }

            stats["total_cases"] += len(cases)
            stats["files_processed"] += 1

            print(f"   ✓ 抽出完了: {len(cases)} 件の案件 ({elapsed:.1f}秒)")
            for i, case in enumerate(cases):
                name = case.get("project_name", "") or "名称なし"
                skills = case.get("skill_requirement", []) or []
                sk_preview = ", ".join(skills[:3])
                if len(skills) > 3:
                    sk_preview += f"... (+{len(skills)-3})"
                loc = case.get("location", {}) or {}
                loc_str = loc.get("city", "") or "?"
                rate = case.get("rate", {}) or {}
                rate_str = f"{rate.get('min', '?')}~{rate.get('max', '?')}万円/月" if rate.get("min") else "未設定"
                print(f"     [{i+1}] {name[:65]}")
                print(f"          場所:{loc_str} | 単価:{rate_str} | スキル:{sk_preview}")

        except Exception as e:
            import traceback
            logger.exception(f"Error processing {filename}")
            print(f"   ✗ エラー: {e}")
            all_results[filename] = {"file": filename, "format": fmt, "error": str(e)}
            stats["errors"] += 1

    # 結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output = {
        "extraction_date": datetime.now().isoformat(),
        "stats": stats,
        "results": all_results,
    }

    json_path = output_dir / f"llm_extraction_result_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ LLM抽出完了")
    print(f"   処理ファイル数: {stats['files_processed']}/{len(files_to_process)}")
    print(f"   全案件数: {stats['total_cases']}")
    print(f"   モデル: {stats['model']}")
    print(f"   結果保存先: {json_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run()
