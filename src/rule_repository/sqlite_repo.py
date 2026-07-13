"""SQLite ルールリポジトリ実装."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.models import FormatTemplate, Rule, RuleMetadata, RuleStatus
from src.common.utils import generate_document_id
from src.config import settings
from src.rule_repository.base import RuleRepository

logger = logging.getLogger(__name__)


class SQLiteRuleRepository(RuleRepository):
    """SQLite を使ったルールリポジトリ実装。"""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or settings.rule_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """データベースの初期化（テーブル作成）。"""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rules (
                    rule_id         TEXT PRIMARY KEY,
                    version         INTEGER NOT NULL DEFAULT 1,
                    field           TEXT NOT NULL,
                    format_type     TEXT NOT NULL,
                    priority        INTEGER DEFAULT 50,
                    enabled         INTEGER DEFAULT 1,
                    status          TEXT DEFAULT 'draft',
                    tags            TEXT DEFAULT '[]',
                    description     TEXT DEFAULT '',
                    patterns        TEXT NOT NULL DEFAULT '[]',
                    post_process    TEXT DEFAULT '{}',
                    validation      TEXT DEFAULT '{}',
                    created_by      TEXT DEFAULT 'manual',
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL,
                    hit_count       INTEGER DEFAULT 0,
                    accuracy        REAL DEFAULT 0.0,
                    sample_count    INTEGER DEFAULT 0,
                    superseded_by   TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_rules_field
                    ON rules(field);
                CREATE INDEX IF NOT EXISTS idx_rules_format
                    ON rules(format_type);
                CREATE INDEX IF NOT EXISTS idx_rules_status
                    ON rules(status);

                CREATE TABLE IF NOT EXISTS format_templates (
                    template_id     TEXT PRIMARY KEY,
                    description     TEXT DEFAULT '',
                    patterns        TEXT NOT NULL DEFAULT '[]',
                    sample_count    INTEGER DEFAULT 0,
                    accuracy        REAL DEFAULT 0.0,
                    created_at      TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dictionaries (
                    dict_name       TEXT PRIMARY KEY,
                    dict_type       TEXT NOT NULL DEFAULT 'synonym',
                    entries         TEXT NOT NULL DEFAULT '[]',
                    version         INTEGER DEFAULT 1,
                    updated_at      TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rule_hit_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id         TEXT NOT NULL,
                    document_id     TEXT DEFAULT '',
                    matched         INTEGER DEFAULT 1,
                    confidence      REAL DEFAULT 0.0,
                    extracted_value TEXT DEFAULT '',
                    feedback        TEXT,
                    created_at      TEXT DEFAULT (datetime('now'))
                );
            """)
            conn.commit()
        finally:
            conn.close()

    # ── Rules ──

    def get_rules(
        self,
        field: str | None = None,
        format_type: str | None = None,
        status: str | None = None,
    ) -> list[Rule]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM rules WHERE 1=1"
            params: list[Any] = []

            if field:
                query += " AND field = ?"
                params.append(field)
            if format_type:
                query += " AND (format_type LIKE ? OR format_type = '[\"*\"]')"
                params.append(f"%{format_type}%")
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY priority DESC, accuracy DESC"

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_rule(row) for row in rows]
        finally:
            conn.close()

    def get_rule(self, rule_id: str) -> Rule | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM rules WHERE rule_id = ?", (rule_id,)
            ).fetchone()
            return self._row_to_rule(row) if row else None
        finally:
            conn.close()

    def save_rule(self, rule: Rule) -> str:
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO rules
                   (rule_id, version, field, format_type, priority, enabled, status,
                    tags, description, patterns, post_process, validation,
                    created_by, created_at, updated_at, hit_count, accuracy, sample_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule.rule_id,
                    rule.version,
                    rule.field,
                    json.dumps(rule.format_type, ensure_ascii=False),
                    rule.priority,
                    1 if rule.enabled else 0,
                    rule.status.value,
                    json.dumps(rule.tags, ensure_ascii=False),
                    rule.description,
                    json.dumps([p.model_dump() for p in rule.patterns], ensure_ascii=False),
                    json.dumps(rule.post_process.model_dump(), ensure_ascii=False),
                    json.dumps(rule.validation.model_dump(), ensure_ascii=False),
                    rule.metadata.created_by,
                    now,
                    now,
                    rule.metadata.hit_count,
                    rule.metadata.accuracy,
                    rule.metadata.sample_count,
                ),
            )
            conn.commit()
            return rule.rule_id
        finally:
            conn.close()

    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> bool:
        conn = self._get_connection()
        try:
            set_clauses = []
            params: list[Any] = []

            simple_fields = {
                "priority": int, "enabled": bool, "status": str,
                "description": str, "hit_count": int, "accuracy": float,
            }
            for key, typ in simple_fields.items():
                if key in updates:
                    set_clauses.append(f"{key} = ?")
                    value = updates[key]
                    if key == "status" and isinstance(value, RuleStatus):
                        value = value.value
                    params.append(value)

            if "format_type" in updates:
                set_clauses.append("format_type = ?")
                params.append(json.dumps(updates["format_type"], ensure_ascii=False))
            if "patterns" in updates:
                set_clauses.append("patterns = ?")
                params.append(json.dumps(updates["patterns"], ensure_ascii=False))

            if not set_clauses:
                return False

            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(rule_id)

            conn.execute(
                f"UPDATE rules SET {', '.join(set_clauses)} WHERE rule_id = ?",
                params,
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def delete_rule(self, rule_id: str) -> bool:
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    # ── Format Templates ──

    def get_format_templates(self) -> list[FormatTemplate]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM format_templates").fetchall()
            return [
                FormatTemplate(
                    template_id=row["template_id"],
                    description=row["description"],
                    patterns=json.loads(row["patterns"]),
                    sample_count=row["sample_count"],
                    accuracy=row["accuracy"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def save_format_template(self, template: FormatTemplate) -> str:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO format_templates
                   (template_id, description, patterns, sample_count, accuracy, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    template.template_id,
                    template.description,
                    json.dumps(template.patterns, ensure_ascii=False),
                    template.sample_count,
                    template.accuracy,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return template.template_id
        finally:
            conn.close()

    # ── Dictionaries ──

    def get_dictionary(self, name: str) -> list[dict]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT entries FROM dictionaries WHERE dict_name = ?", (name,)
            ).fetchone()
            return json.loads(row["entries"]) if row else []
        finally:
            conn.close()

    def save_dictionary(self, name: str, entries: list[dict]) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO dictionaries
                   (dict_name, dict_type, entries, version, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    name,
                    "synonym",
                    json.dumps(entries, ensure_ascii=False),
                    1,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Logging ──

    def log_hit(
        self,
        rule_id: str,
        document_id: str,
        matched: bool,
        confidence: float,
        value: str | None = None,
    ) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO rule_hit_log
                   (rule_id, document_id, matched, confidence, extracted_value)
                   VALUES (?, ?, ?, ?, ?)""",
                (rule_id, document_id, 1 if matched else 0, confidence, value or ""),
            )
            conn.commit()
        finally:
            conn.close()

    def get_rule_stats(self, rule_id: str) -> dict[str, Any] | None:
        conn = self._get_connection()
        try:
            rule = self.get_rule(rule_id)
            if not rule:
                return None

            row = conn.execute(
                """SELECT
                    COUNT(*) as total_hits,
                    SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(confidence) as avg_confidence
                   FROM rule_hit_log WHERE rule_id = ?""",
                (rule_id,),
            ).fetchone()

            return {
                "rule_id": rule_id,
                "total_hits": row["total_hits"] if row else 0,
                "success_count": row["success_count"] if row else 0,
                "avg_confidence": row["avg_confidence"] if row else 0.0,
                "accuracy": rule.metadata.accuracy,
                "sample_count": rule.metadata.sample_count,
            }
        finally:
            conn.close()

    def get_coverage_stats(self) -> dict[str, Any]:
        conn = self._get_connection()
        try:
            total_rules = conn.execute(
                "SELECT COUNT(*) as cnt FROM rules WHERE status = 'active'"
            ).fetchone()["cnt"]

            fields_with_rules = conn.execute(
                "SELECT COUNT(DISTINCT field) as cnt FROM rules WHERE status = 'active'"
            ).fetchone()["cnt"]

            return {
                "total_active_rules": total_rules,
                "fields_covered": fields_with_rules,
                "total_fields": 18,  # 全フィールド数
            }
        finally:
            conn.close()

    # ── Helpers ──

    def _row_to_rule(self, row: sqlite3.Row) -> Rule:
        return Rule(
            rule_id=row["rule_id"],
            version=row["version"],
            field=row["field"],
            format_type=json.loads(row["format_type"]),
            priority=row["priority"],
            enabled=bool(row["enabled"]),
            status=RuleStatus(row["status"]),
            tags=json.loads(row["tags"]),
            description=row["description"],
            patterns=json.loads(row["patterns"]),
            post_process=json.loads(row["post_process"]),
            validation=json.loads(row["validation"]),
            metadata=RuleMetadata(
                created_by=row["created_by"],
                hit_count=row["hit_count"],
                accuracy=row["accuracy"],
                sample_count=row["sample_count"],
            ),
        )
