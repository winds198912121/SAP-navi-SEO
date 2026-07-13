"""共有データモデル定義."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════
# 列挙型
# ═══════════════════════════════════════════

class ExtractionMode(str, Enum):
    AUTO = "auto"
    RULE = "rule"
    LLM = "llm"
    HYBRID = "hybrid"


class RuleStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class PatternType(str, Enum):
    REGEX = "regex"
    POSITION = "position"
    XPATH = "xpath"
    CSS = "css"
    KEYWORD = "keyword"
    LAYOUT = "layout"
    ML = "ml"


class RemotePolicy(str, Enum):
    FULL_REMOTE = "full_remote"
    HYBRID = "hybrid"
    OFFICE_ONLY = "office_only"
    NOT_SPECIFIED = "not_specified"


class RateUnit(str, Enum):
    MONTHLY = "monthly"
    DAILY = "daily"
    HOURLY = "hourly"
    YEARLY = "yearly"


class ContractType(str, Enum):
    JUN_ININ = "jun_inin"
    UKEOI = "ukeoi"
    HAKEN = "haken"
    SES = "ses"
    OTHER = "other"


class JapaneseLevel(str, Enum):
    NATIVE = "native"
    BUSINESS = "business"
    N2 = "n2"
    N3 = "n3"
    N4 = "n4"
    NOT_SPECIFIED = "not_specified"


class FeedbackType(str, Enum):
    MISSING_VALUE = "missing_value"
    WRONG_VALUE = "wrong_value"
    EXTRA_VALUE = "extra_value"
    FORMAT_ERROR = "format_error"


# ═══════════════════════════════════════════
# データモデル
# ═══════════════════════════════════════════

class Location(BaseModel):
    city: str | None = None
    station: str | None = None
    remote_policy: RemotePolicy = RemotePolicy.NOT_SPECIFIED
    remote_detail: str | None = None


class Rate(BaseModel):
    min: float | None = None
    max: float | None = None
    unit: RateUnit = RateUnit.MONTHLY
    unit_jp: str | None = None
    currency: str = "JPY"
    note: str | None = None


class Period(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = None
    long_term: bool | None = None
    note: str | None = None


class TradeFlow(BaseModel):
    contract_type: ContractType | None = None
    contract_type_jp: str | None = None
    layers: int | None = None
    end_client: str | None = None
    intermediaries: list[str] | None = None


class JapaneseLevelInfo(BaseModel):
    level: JapaneseLevel = JapaneseLevel.NOT_SPECIFIED
    level_jp: str | None = None
    detail: str | None = None


class EnglishLevelInfo(BaseModel):
    level: str = "not_specified"
    detail: str | None = None


class WorkingHours(BaseModel):
    start: str | None = None
    end: str | None = None
    flex_time: bool | None = None
    overtime: str | None = None


class SourceInfo(BaseModel):
    original_format: str = "unknown"
    filename: str | None = None
    source_url: str | None = None
    received_date: date | None = None
    sender: str | None = None
    extraction_date: datetime | None = None
    extraction_mode: ExtractionMode = ExtractionMode.AUTO


class ExperienceYears(BaseModel):
    min: int | None = None
    max: int | None = None
    description: str | None = None


class RecruitmentCase(BaseModel):
    """日本IT招聘案件の完全な構造化データ."""
    project_name: str | None = None
    project_description: str | None = None
    skill_requirement: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years: ExperienceYears | None = None
    location: Location = Field(default_factory=Location)
    rate: Rate = Field(default_factory=Rate)
    period: Period = Field(default_factory=Period)
    headcount: int | None = None
    industry: str | None = None
    trade_flow: TradeFlow = Field(default_factory=TradeFlow)
    japanese_level: JapaneseLevelInfo = Field(default_factory=JapaneseLevelInfo)
    english_level: EnglishLevelInfo = Field(default_factory=EnglishLevelInfo)
    working_hours: WorkingHours = Field(default_factory=WorkingHours)
    interviews: int | None = None
    immediate_start: bool | None = None
    screening_flow: str | None = None
    remarks: str | None = None
    original_text: str | None = None
    """案件の全文（抽出元の生テキスト）. デバッグ・確認用。"""
    source: SourceInfo = Field(default_factory=SourceInfo)


class FieldResult(BaseModel):
    """単一フィールドの抽出結果."""
    field: str
    value: Any = None
    confidence: float = 0.0
    source: str = "none"           # rule | llm | hybrid | both_agree | no_rule | none
    rule_id: str | None = None
    conflict_note: str | None = None


class ExtractionResult(BaseModel):
    """抽出パイプライン全体の結果."""
    document_id: str
    extraction_mode: ExtractionMode
    fields: dict[str, FieldResult] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class PreprocessingResult(BaseModel):
    """ドキュメント前処理の結果."""
    raw_text: str = ""
    structured_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    pages: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


# ═══════════════════════════════════════════
# ルールモデル
# ═══════════════════════════════════════════

class ExtractionPattern(BaseModel):
    type: PatternType = PatternType.REGEX
    value: str
    flags: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    weight: float = 1.0
    # position 専用
    section: str | None = None
    line_offset: int | None = None
    direction: str = "below"
    span_lines: int | None = None
    stop_pattern: str | None = None
    # table 専用
    table_anchor: dict[str, Any] | None = None
    # keyword 専用
    dictionary: str | None = None
    scope: str = "full_text"
    match_strategy: str = "overlap"


class PostProcessStep(BaseModel):
    operation: str
    delimiters: list[str] | None = None
    dictionary: str | None = None


class PostProcessConfig(BaseModel):
    trim: bool = True
    split: list[str] | None = None
    filter_empty: bool = True
    deduplicate: bool = True
    map_to_canonical: bool = False
    steps: list[PostProcessStep] = Field(default_factory=list)


class ValidationConfig(BaseModel):
    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    must_contain_pattern: str | None = None
    min_items: int | None = None
    rules: list[dict[str, Any]] = Field(default_factory=list)


class RuleMetadata(BaseModel):
    created_by: str = "manual"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    hit_count: int = 0
    accuracy: float = 0.0
    source_template: str | None = None
    sample_count: int = 0


class Rule(BaseModel):
    rule_id: str
    version: int = 1
    field: str
    format_type: list[str] = Field(default_factory=lambda: ["*"])
    priority: int = 50
    enabled: bool = True
    status: RuleStatus = RuleStatus.DRAFT
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    patterns: list[ExtractionPattern] = Field(default_factory=list)
    post_process: PostProcessConfig = Field(default_factory=PostProcessConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    metadata: RuleMetadata = Field(default_factory=RuleMetadata)


class FormatTemplate(BaseModel):
    template_id: str
    description: str = ""
    patterns: list[dict[str, Any]] = Field(default_factory=list)
    sample_count: int = 0
    accuracy: float = 0.0


# ═══════════════════════════════════════════
# フィードバックモデル
# ═══════════════════════════════════════════

class FieldCorrection(BaseModel):
    field: str
    extracted_value: Any = None
    corrected_value: Any = None
    correction_type: FeedbackType
    notes: str | None = None


class FeedbackSubmission(BaseModel):
    document_id: str
    corrections: list[FieldCorrection]
