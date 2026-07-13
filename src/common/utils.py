"""共通ユーティリティ関数."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# ファイル操作
# ═══════════════════════════════════════════

def detect_file_format(file_path: str | Path) -> str:
    """ファイル拡張子からフォーマットを検出。"""
    ext = Path(file_path).suffix.lower()
    format_map = {
        ".pdf": "pdf",
        ".docx": "word",
        ".doc": "word",
        ".xlsx": "excel",
        ".xls": "excel",
        ".html": "html",
        ".htm": "html",
        ".eml": "email",
        ".msg": "email",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".tiff": "image",
        ".bmp": "image",
        ".txt": "text",
        ".md": "text",
        ".csv": "excel",
    }
    return format_map.get(ext, "unknown")


def generate_document_id() -> str:
    """ドキュメントIDを生成。"""
    now = datetime.now()
    suffix = hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:6]
    return f"doc_{now.strftime('%Y%m%d_%H%M%S')}_{suffix}"


def safe_filename(filename: str) -> str:
    """ファイル名から安全でない文字を除去。"""
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


# ═══════════════════════════════════════════
# 日本語文字列処理
# ═══════════════════════════════════════════

def normalize_whitespace(text: str) -> str:
    """連続する空白を1つにまとめる。"""
    return re.sub(r"\s+", " ", text).strip()


def extract_numbers(text: str) -> list[float]:
    """文字列から数値を抽出。"""
    return [float(x.replace(",", "")) for x in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)]


def split_japanese_list(text: str, delimiters: list[str] | None = None) -> list[str]:
    """日本語の区切り文字でテキストを分割。"""
    if delimiters is None:
        delimiters = ["、", "・", "/", "\\s+", ","]
    pattern = "|".join(re.escape(d) if len(d) == 1 else d for d in delimiters)
    items = re.split(pattern, text)
    return [item.strip() for item in items if item.strip()]


def clean_japanese_text(text: str) -> str:
    """日本語テキストをクリーニング。"""
    text = re.sub(r"[￥¥]", "円", text)
    text = re.sub(r"[‾〜~]", "〜", text)
    text = re.sub(r"[˘＾]", "^", text)
    text = text.replace("　", " ")  # 全角スペース→半角
    return text.strip()


# ═══════════════════════════════════════════
# 日付処理
# ═══════════════════════════════════════════

ERA_MAP = {
    "令和": (2019, 5, 1),
    "平成": (1989, 1, 8),
    "昭和": (1926, 12, 25),
}

ERA_PATTERN = re.compile(r"(令和|平成|昭和)(\d+)年(\d{1,2})月(\d{1,2})日")


def convert_jp_date(text: str) -> str | None:
    """和暦日付を YYYY-MM-DD に変換。

    Rules:
    - 和暦 → 西暦変換
    - 年が明示された標準形式 → そのまま
    - **月のみ（年なし） → 当前年をデフォルト、既に過ぎた月は翌年**
    """
    m = ERA_PATTERN.search(text)
    if m:
        era = m.group(1)
        year = int(m.group(2))
        month = int(m.group(3))
        day = int(m.group(4))
        base_year, base_month, base_day = ERA_MAP[era]
        if year == 1:
            if month < base_month or (month == base_month and day < base_day):
                year = 1
            gregorian_year = base_year
        else:
            gregorian_year = base_year + year - 1
        try:
            dt = datetime(gregorian_year, month, day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    # 標準形式 YYYY/MM/DD, YYYY-MM-DD
    m2 = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", text)
    if m2:
        try:
            dt = datetime(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    # YYYY年M月
    m3 = re.search(r"(\d{4})年(\d{1,2})月", text)
    if m3:
        try:
            dt = datetime(int(m3.group(1)), int(m3.group(2)), 1)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    # 🆕 M月（年なし）→ 当前年デフォルト、過ぎた月は翌年
    m4 = re.search(r"(?:^|\D)(\d{1,2})月(?!\d)", text)
    if m4:
        now = datetime.now()
        year = now.year
        month = int(m4.group(1))
        if month < now.month:
            year += 1
        try:
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


# ═══════════════════════════════════════════
# JSON ユーティリティ
# ═══════════════════════════════════════════

def safe_json_parse(text: str) -> dict | None:
    """JSON を安全にパース。失敗時は None を返す。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON抽出用の正規表現フォールバック
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return None


def deduplicate_by_key(items: list[Any], key_fn=None) -> list[Any]:
    """指定されたキー関数で重複を除去。"""
    seen = set()
    result = []
    for item in items:
        if key_fn:
            key = key_fn(item)
        else:
            key = item
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
