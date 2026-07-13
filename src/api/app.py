"""FastAPI アプリケーションエントリーポイント."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.common.models import (
    ExtractionMode,
    ExtractionResult,
    FeedbackSubmission,
    FieldResult,
    RecruitmentCase,
    Rule,
    RuleStatus,
)
from src.common.schema import get_extraction_schema
from src.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="JP Recruit Extractor API",
    description="日本招聘案件データ抽出システム API",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# Health
# ─────────────────────────────────────────

@app.get("/health")
async def health():
    """ヘルスチェック。"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────
# Extract
# ─────────────────────────────────────────

@app.post("/extract")
async def extract(
    file: UploadFile = File(...),
    mode: str = Form("auto"),
    fields: str | None = Form(None),
):
    """単一ファイルの案件データを抽出。"""
    # ファイル形式の検証
    ext = Path(file.filename or "").suffix.lower()
    supported = {".pdf", ".docx", ".xlsx", ".html", ".eml", ".png", ".jpg", ".jpeg", ".txt"}
    if ext not in supported:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_FORMAT",
                "message": f"未対応のファイル形式です: {ext}",
                "supported": list(supported),
            },
        )

    # ファイル読み込み
    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"ファイルサイズは {settings.max_file_size_mb}MB を超えることはできません",
            },
        )

    # TODO: 実際の抽出処理を呼び出す
    # 現時点ではモックレスポンス
    field_list = fields.split(",") if fields else None

    result = ExtractionResult(
        document_id=f"doc_{uuid.uuid4().hex[:12]}",
        extraction_mode=ExtractionMode(mode),
        metadata={
            "filename": file.filename,
            "file_size_bytes": len(content),
            "format_type": "unknown",
            "processing_time_ms": 0,
        },
    )

    return JSONResponse(
        content=result.model_dump(),
        status_code=200,
    )


# ─────────────────────────────────────────
# Batch
# ─────────────────────────────────────────

_batch_jobs: dict[str, dict] = {}


@app.post("/batch")
async def batch_extract(
    files: list[UploadFile] = File(...),
    mode: str = Form("auto"),
    callback_url: str | None = Form(None),
):
    """複数ファイルの一括抽出（非同期）。"""
    job_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    _batch_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "total_files": len(files),
        "completed": 0,
        "failed": 0,
        "created_at": datetime.now().isoformat(),
    }

    return JSONResponse(
        content={
            "job_id": job_id,
            "status": "queued",
            "total_files": len(files),
            "status_url": f"/batch/{job_id}",
            "results_url": f"/batch/{job_id}/results",
        },
        status_code=202,
    )


@app.get("/batch/{job_id}")
async def batch_status(job_id: str):
    """バッチ処理の進捗を確認。"""
    job = _batch_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "ジョブが見つかりません"})
    return job


@app.get("/batch/{job_id}/results")
async def batch_results(job_id: str, format: str = Query("json")):
    """バッチ結果を取得。"""
    job = _batch_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "ジョブが見つかりません"})
    return {"job_id": job_id, "results": [], "summary": {}}


# ─────────────────────────────────────────
# Feedback
# ─────────────────────────────────────────

@app.put("/feedback")
async def submit_feedback(feedback: FeedbackSubmission):
    """抽出結果の修正フィードバックを送信。"""
    # TODO: フィードバックを記録し、ルール学習をトリガー
    return {
        "feedback_id": f"fb_{uuid.uuid4().hex[:12]}",
        "status": "accepted",
        "will_trigger_learning": True,
    }


# ─────────────────────────────────────────
# Rules
# ─────────────────────────────────────────

@app.get("/rules")
async def list_rules(
    field: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """ルール一覧を取得。"""
    # TODO: 実際のルールリポジトリから取得
    return {
        "total": 0,
        "page": page,
        "per_page": per_page,
        "rules": [],
    }


@app.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """ルール詳細を取得。"""
    raise HTTPException(status_code=404, detail={"code": "RULE_NOT_FOUND", "message": "ルールが見つかりません"})


# ─────────────────────────────────────────
# Formats
# ─────────────────────────────────────────

@app.post("/formats")
async def register_format(data: dict[str, Any]):
    """新フォーマットを登録。"""
    return {
        "format_type": data.get("name", "unknown"),
        "status": "registered",
        "message": "フォーマットが登録されました（自動抽出開始）",
    }


@app.get("/formats")
async def list_formats():
    """登録済フォーマット一覧。"""
    return {"formats": []}


# ─────────────────────────────────────────
# Stats
# ─────────────────────────────────────────

@app.get("/stats")
async def get_stats(period: str = Query("7d")):
    """システム統計情報を取得。"""
    return {
        "period": period,
        "extraction": {
            "total_documents": 0,
            "success_rate": 0.0,
            "avg_confidence": 0.0,
        },
        "rules": {
            "total": 0,
            "active": 0,
            "coverage": 0.0,
        },
        "llm": {
            "total_calls": 0,
            "estimated_cost_usd": 0.0,
        },
    }


# ─────────────────────────────────────────
# Schema
# ─────────────────────────────────────────

@app.get("/schema")
async def get_schema():
    """抽出スキーマを取得。"""
    return get_extraction_schema()


# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────

def main():
    """APIサーバーを起動。"""
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
