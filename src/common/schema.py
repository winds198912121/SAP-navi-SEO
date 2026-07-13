"""JSON Schema 定義 — フィールド定義と抽出スキーマ."""

import json

# 完全な抽出スキーマ（JSON Schema Draft-07）
# 詳細は docs/01-field-definition.md を参照

EXTRACTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "JapaneseRecruitmentCase",
    "type": "object",
    "required": ["project_name", "skill_requirement", "location", "rate"],
    "properties": {
        "project_name": {
            "type": "string",
            "description": "案件名 / プロジェクト名",
            "minLength": 1,
            "maxLength": 200,
        },
        "project_description": {
            "type": "string",
            "description": "案件概要",
            "maxLength": 2000,
        },
        "skill_requirement": {
            "type": "array",
            "description": "必須スキル",
            "items": {"type": "string"},
            "minItems": 1,
            "uniqueItems": True,
        },
        "preferred_skills": {
            "type": "array",
            "description": "歓迎スキル",
            "items": {"type": "string"},
            "uniqueItems": True,
        },
        "experience_years": {
            "type": "object",
            "description": "必要経験年数",
            "properties": {
                "min": {"type": "integer", "minimum": 0},
                "max": {"type": "integer", "minimum": 0},
                "description": {"type": "string"},
            },
        },
        "location": {
            "type": "object",
            "description": "勤務地",
            "required": ["city"],
            "properties": {
                "city": {"type": "string"},
                "station": {"type": "string"},
                "remote_policy": {
                    "type": "string",
                    "enum": ["full_remote", "hybrid", "office_only", "not_specified"],
                },
                "remote_detail": {"type": "string"},
            },
        },
        "rate": {
            "type": "object",
            "description": "単価",
            "required": ["unit"],
            "properties": {
                "min": {"type": "number", "minimum": 0},
                "max": {"type": "number", "minimum": 0},
                "unit": {"type": "string", "enum": ["monthly", "daily", "hourly", "yearly"]},
                "unit_jp": {"type": "string"},
                "currency": {"type": "string", "default": "JPY"},
                "note": {"type": "string"},
            },
        },
        "period": {
            "type": "object",
            "description": "期間",
            "properties": {
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
                "duration_months": {"type": "integer", "minimum": 1},
                "long_term": {"type": "boolean"},
                "note": {"type": "string"},
            },
        },
        "headcount": {"type": "integer", "minimum": 1, "maximum": 999},
        "industry": {"type": "string"},
        "trade_flow": {
            "type": "object",
            "description": "商流",
            "properties": {
                "contract_type": {
                    "type": "string",
                    "enum": ["jun_inin", "ukeoi", "haken", "ses", "other"],
                },
                "contract_type_jp": {"type": "string"},
                "layers": {"type": "integer", "minimum": 1, "maximum": 10},
                "end_client": {"type": "string"},
                "intermediaries": {"type": "array", "items": {"type": "string"}},
            },
        },
        "japanese_level": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["native", "business", "n2", "n3", "n4", "not_specified"],
                },
                "level_jp": {"type": "string"},
                "detail": {"type": "string"},
            },
        },
        "english_level": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["business", "daily", "none", "native", "not_specified"]},
                "detail": {"type": "string"},
            },
        },
        "working_hours": {
            "type": "object",
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "flex_time": {"type": "boolean"},
                "overtime": {"type": "string"},
            },
        },
        "interviews": {"type": "integer", "minimum": 0, "maximum": 10},
        "immediate_start": {"type": "boolean"},
        "screening_flow": {"type": "string"},
        "remarks": {"type": "string", "maxLength": 2000},
        "source": {
            "type": "object",
            "properties": {
                "original_format": {
                    "type": "string",
                    "enum": ["pdf", "word", "excel", "html", "email", "image", "text", "unknown"],
                },
                "filename": {"type": "string"},
                "source_url": {"type": "string"},
                "received_date": {"type": "string", "format": "date"},
                "sender": {"type": "string"},
            },
        },
    },
}


def get_extraction_schema() -> dict:
    """抽出スキーマを取得（コピーを返す）。"""
    return dict(EXTRACTION_SCHEMA)


def get_schema_as_json() -> str:
    """スキーマをJSON文字列として取得。"""
    return json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)


def get_required_fields() -> list[str]:
    """必須フィールド一覧を取得。"""
    return list(EXTRACTION_SCHEMA.get("required", []))


def get_all_fields() -> list[str]:
    """全フィールド名を取得。"""
    return list(EXTRACTION_SCHEMA.get("properties", {}).keys())
