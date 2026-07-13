"""API リクエスト/レスポンスの Pydantic スキーマ."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────
# Extract
# ─────────────────────────────────────────

class ExtractResponse(BaseModel):
    document_id: str
    extraction_mode: str
    fields: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────
# Batch
# ─────────────────────────────────────────

class BatchCreateResponse(BaseModel):
    job_id: str
    status: str = "queued"
    total_files: int
    status_url: str
    results_url: str


class BatchProgress(BaseModel):
    total: int = 0
    completed: int = 0
    failed: int = 0


class BatchStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str | None = None
    progress: BatchProgress = Field(default_factory=BatchProgress)


class BatchResultsResponse(BaseModel):
    job_id: str
    results: list[dict] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────
# Feedback
# ─────────────────────────────────────────

class CorrectionItem(BaseModel):
    field: str
    extracted_value: Any = None
    corrected_value: Any = None
    correction_type: str = "wrong_value"
    notes: str | None = None


class FeedbackRequest(BaseModel):
    document_id: str
    corrections: list[CorrectionItem]


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str = "accepted"
    will_trigger_learning: bool = True


# ─────────────────────────────────────────
# Rules
# ─────────────────────────────────────────

class RuleListItem(BaseModel):
    rule_id: str
    field: str
    format_type: list[str]
    status: str
    priority: int
    accuracy: float
    hit_count: int


class RuleListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    rules: list[RuleListItem]


# ─────────────────────────────────────────
# Error
# ─────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str | None = None
