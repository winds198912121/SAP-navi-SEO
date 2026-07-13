"""グローバル設定モジュール."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EXTRACTOR_",
    )

    # ── LLM API Keys ──
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None

    # ── LLM Settings ──
    llm_provider: Literal["anthropic", "openai", "deepseek"] = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
    deepseek_base_url: str = "https://api.deepseek.com"

    # ── Extraction Settings ──
    default_mode: Literal["auto", "rule", "llm", "hybrid"] = "auto"
    rule_confidence_threshold_high: float = 0.9
    rule_confidence_threshold_medium: float = 0.7
    max_file_size_mb: int = 50

    # ── Paths ──
    rule_db_path: Path = Path("data/rules/rules.db")
    cache_dir: Path = Path("data/cache")
    sample_dir: Path = Path("data/samples")
    output_dir: Path = Path("data/output")

    # ── Processing ──
    max_workers: int = 4
    ocr_language: str = "jap"
    tesseract_cmd: str = "tesseract"

    # ── Logging ──
    log_level: str = "INFO"
    log_file: str = "data/extractor.log"

    # ── API Settings ──
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str | None = None

    # ── Rate Limits ──
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 200


settings = Settings()

# パスの自動生成
settings.rule_db_path.parent.mkdir(parents=True, exist_ok=True)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
