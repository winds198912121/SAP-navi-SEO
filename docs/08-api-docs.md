# 08 — API 文档 (API Documentation)

> **文档版本**: v1.0
> **更新日期**: 2025-06-28
> **ベースURL**: `http://localhost:8000`

## 1. 概要

JP Recruit Extractor は RESTful API を提供します。全エンドポイントは JSON 形式でリクエスト/レスポンスを行います。

### 認証

現在のバージョンでは API Key による認証を推奨：

```bash
Authorization: Bearer <api-key>
```

### 共通エラーレスポンス

```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "サポートされていないファイル形式です",
    "details": {
      "supported_formats": ["pdf", "docx", "xlsx", "html", "eml", "png", "jpg", "txt"]
    }
  },
  "request_id": "req_20250628_001234"
}
```

---

## 2. エンドポイント一覧

| Method | Path | 説明 |
|---|---|---|
| POST | `/extract` | 単一ファイルの案件データ抽出 |
| POST | `/batch` | 複数ファイルの一括抽出（非同期） |
| GET | `/batch/{job_id}` | バッチ処理の進捗確認 |
| GET | `/batch/{job_id}/results` | バッチ結果の取得 |
| PUT | `/feedback` | 抽出結果の修正フィードバック送信 |
| GET | `/rules` | ルール一覧の取得 |
| GET | `/rules/{rule_id}` | ルール詳細の取得 |
| PUT | `/rules/{rule_id}` | ルールの更新（enable/disable等） |
| POST | `/rules/learn` | ルール学習の手動トリガー |
| POST | `/formats` | 新フォーマットの登録 |
| GET | `/formats` | 登録済フォーマット一覧 |
| GET | `/stats` | システム統計情報 |
| GET | `/health` | ヘルスチェック |

---

## 3. 詳細リファレンス

### 3.1 POST /extract — 単一ファイル抽出

#### リクエスト

```
POST /extract
Content-Type: multipart/form-data
```

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `file` | File | ✓ | 案件ドキュメントファイル（任意の対応形式） |
| `mode` | string | | 抽出モード: `auto`(default), `rule`, `llm`, `hybrid` |
| `fields` | string | | カンマ区切りで抽出対象フィールドを指定（省略時は全フィールド） |
| `sandbox` | boolean | | Sandbox モード（新ルールのテストに利用） |

#### レスポンス 200

```json
{
  "document_id": "doc_20250628_001234",
  "extraction_mode": "hybrid",
  "fields": {
    "project_name": {
      "value": "某証券会社向け基幹システム開発",
      "confidence": 0.98,
      "source": "rule",
      "rule_id": "field_project_name_regex_001"
    },
    "skill_requirement": {
      "value": ["Java", "Spring Boot", "AWS", "PostgreSQL"],
      "confidence": 0.95,
      "source": "rule",
      "rule_id": "field_skill_regex_003"
    },
    "location": {
      "value": {
        "city": "東京都品川区",
        "station": "品川駅",
        "remote_policy": "office_only"
      },
      "confidence": 0.92,
      "source": "hybrid",
      "note": "location.remote_policy from LLM"
    },
    "rate": {
      "value": {
        "min": 70,
        "max": 80,
        "unit": "monthly",
        "currency": "JPY"
      },
      "confidence": 0.96,
      "source": "rule",
      "rule_id": "field_rate_regex_002"
    },
    ...
  },
  "metadata": {
    "filename": "案件概要書_20250601.pdf",
    "format_type": "template_a",
    "processing_time_ms": 1520,
    "llm_calls": 1,
    "estimated_cost_usd": 0.008
  }
}
```

#### レスポンス 400

```json
{
  "error": {
    "code": "INVALID_FILE",
    "message": "ファイルが読み込めません",
    "details": {"reason": "ファイルがパスワード保護されています"}
  }
}
```

#### レスポンス 413

```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "ファイルサイズは 50MB を超えることはできません"
  }
}
```

#### コード例

```python
import requests

response = requests.post(
    "http://localhost:8000/extract",
    files={"file": open("sample.pdf", "rb")},
    data={"mode": "auto"},
    headers={"Authorization": "Bearer <api-key>"}
)
data = response.json()
print(data["fields"]["project_name"]["value"])
```

---

### 3.2 POST /batch — 一括抽出

#### リクエスト

```
POST /batch
Content-Type: multipart/form-data
```

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `files` | File[] | ✓ | 案件ドキュメントファイル（複数可） |
| `callback_url` | string | | 完了時に結果を POST する Webhook URL |
| `mode` | string | | 抽出モード（全ファイル共通） |
| `output_format` | string | | 出力形式: `json`(default), `csv`, `excel` |

#### レスポンス 202

```json
{
  "job_id": "batch_20250628_001",
  "status": "queued",
  "total_files": 15,
  "estimated_time_seconds": 45,
  "status_url": "/batch/batch_20250628_001",
  "results_url": "/batch/batch_20250628_001/results"
}
```

---

### 3.3 GET /batch/{job_id} — 進捗確認

#### リクエスト

```
GET /batch/batch_20250628_001
```

#### レスポンス

```json
{
  "job_id": "batch_20250628_001",
  "status": "processing",
  "created_at": "2025-06-28T10:00:00Z",
  "progress": {
    "total": 15,
    "completed": 8,
    "failed": 1,
    "skipped": 0
  },
  "failed_files": [
    {
      "filename": "corrupt_doc.pdf",
      "error": "PDF parsing error: file appears to be corrupted"
    }
  ],
  "estimated_remaining_seconds": 20,
  "results_url": "/batch/batch_20250628_001/results"
}
```

---

### 3.4 GET /batch/{job_id}/results — 結果取得

#### リクエスト

```
GET /batch/batch_20250628_001/results?format=json
```

| パラメータ | 型 | 説明 |
|---|---|---|
| `format` | string | `json`(default), `csv`, `excel` |
| `include_raw` | boolean | LLMの生出力を含めるか |

#### レスポンス 200

```json
{
  "job_id": "batch_20250628_001",
  "completed_at": "2025-06-28T10:01:30Z",
  "results": [
    {
      "filename": "案件A.pdf",
      "extraction": {
        "project_name": "...",
        ...
      },
      "metadata": {
        "mode": "rule",
        "confidence_avg": 0.94,
        "processing_time_ms": 850
      }
    },
    ...
  ],
  "summary": {
    "total": 15,
    "success": 14,
    "failed": 1,
    "avg_confidence": 0.91,
    "rule_coverage": 0.78,
    "total_llm_calls": 12,
    "total_cost_usd": 0.095
  }
}
```

---

### 3.5 PUT /feedback — 修正フィードバック

#### リクエスト

```
PUT /feedback
Content-Type: application/json
```

```json
{
  "document_id": "doc_20250628_001234",
  "corrections": [
    {
      "field": "skill_requirement",
      "extracted_value": ["Java", "AWS"],
      "corrected_value": ["Java", "Spring Boot", "AWS"],
      "correction_type": "missing_value",
      "notes": "Spring Boot が不足していた"
    },
    {
      "field": "rate.max",
      "extracted_value": 70,
      "corrected_value": 80,
      "correction_type": "wrong_value",
      "notes": "OCR で 8→7 に誤認識されていた"
    }
  ]
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `document_id` | string | ✓ | 抽出結果の document_id |
| `corrections[].field` | string | ✓ | 修正対象フィールド |
| `corrections[].extracted_value` | any | | 抽出された値 |
| `corrections[].corrected_value` | any | ✓ | 正しい値 |
| `corrections[].correction_type` | string | ✓ | `missing_value`, `wrong_value`, `extra_value`, `format_error` |
| `corrections[].notes` | string | | 修正理由 |

#### レスポンス 200

```json
{
  "feedback_id": "fb_20250628_001",
  "status": "accepted",
  "will_trigger_learning": true,
  "estimated_rule_update": "2025-06-29T00:00:00Z (next scheduled learning)"
}
```

---

### 3.6 GET /rules — ルール一覧

#### リクエスト

```
GET /rules?field=skill_requirement&status=active&page=1&per_page=20
```

| パラメータ | 型 | 説明 |
|---|---|---|
| `field` | string | フィールドで絞り込み |
| `format_type` | string | フォーマット種別で絞り込み |
| `status` | string | `active`, `testing`, `draft`, `deprecated` |
| `page` | integer | ページ番号（default: 1） |
| `per_page` | integer | 1ページあたりの件数（default: 20, max: 100） |

#### レスポンス 200

```json
{
  "total": 156,
  "page": 1,
  "per_page": 20,
  "rules": [
    {
      "rule_id": "field_skill_regex_001",
      "field": "skill_requirement",
      "format_type": ["template_a", "free_form"],
      "status": "active",
      "priority": 90,
      "description": "「スキル」キーワードに続く内容を抽出",
      "pattern_types": ["regex"],
      "accuracy": 0.97,
      "hit_count": 145,
      "created_at": "2025-06-01T10:30:00Z",
      "updated_at": "2025-06-15T14:22:00Z"
    },
    ...
  ]
}
```

---

### 3.7 POST /rules/learn — ルール学習トリガー

#### リクエスト

```
POST /rules/learn
Content-Type: application/json
```

```json
{
  "fields": ["skill_requirement", "rate"],
  "format_type": "abc_corporation_template_v1",
  "min_samples": 3
}
```

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `fields` | string[] | | 学習対象フィールド（省略時は全フィールド） |
| `format_type` | string | | 特定フォーマットに絞り込む |
| `min_samples` | integer | | 最低サンプル数（default: 3） |

#### レスポンス 202

```json
{
  "learning_job_id": "learn_20250628_001",
  "status": "started",
  "parameters": {
    "fields": ["skill_requirement", "rate"],
    "format_type": "abc_corporation_template_v1",
    "available_samples": 5
  },
  "estimated_completion": "2025-06-28T10:01:00Z"
}
```

---

### 3.8 POST /formats — フォーマット登録

#### リクエスト

```
POST /formats
Content-Type: application/json
```

```json
{
  "name": "abc_corporation_template_v1",
  "description": "ABC株式会社 案件案内メールフォーマット",
  "patterns": [
    {"type": "header_marker", "value": "【ABC社 案件案内】", "weight": 0.4},
    {"type": "keyword_present", "value": "ABC株式会社", "weight": 0.3},
    {"type": "table_structure", "rows": 10, "cols": 2, "weight": 0.3}
  ],
  "sample_files": ["sample_001.eml", "sample_002.eml"]
}
```

#### レスポンス 201

```json
{
  "format_type": "abc_corporation_template_v1",
  "status": "registered",
  "auto_extraction_started": true,
  "extraction_job_id": "extract_20250628_002",
  "next_step": "人工確認: 抽出結果を review してください",
  "review_url": "/formats/abc_corporation_template_v1/review"
}
```

---

### 3.9 GET /stats — システム統計

#### リクエスト

```
GET /stats?period=7d
```

| パラメータ | 型 | 説明 |
|---|---|---|
| `period` | string | 集計期間: `24h`, `7d`(default), `30d` |

#### レスポンス 200

```json
{
  "period": "7d",
  "extraction": {
    "total_documents": 234,
    "success_rate": 0.97,
    "avg_processing_time_ms": 1250,
    "avg_confidence": 0.92,
    "by_mode": {
      "rule": {"count": 178, "pct": 76.1, "avg_time_ms": 320},
      "hybrid": {"count": 38, "pct": 16.2, "avg_time_ms": 2100},
      "llm": {"count": 18, "pct": 7.7, "avg_time_ms": 8500}
    }
  },
  "rules": {
    "total": 156,
    "active": 132,
    "testing": 18,
    "draft": 6,
    "avg_accuracy": 0.94,
    "coverage": 0.78
  },
  "llm": {
    "total_calls": 74,
    "estimated_cost_usd": 0.59,
    "avg_tokens_per_call": 4200
  },
  "feedback": {
    "total_submitted": 28,
    "incorporated_into_rules": 22
  }
}
```

---

### 3.10 GET /health — ヘルスチェック

#### リクエスト

```
GET /health
```

#### レスポンス 200

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 86400,
  "components": {
    "rule_repository": {"status": "ok", "rule_count": 156},
    "llm_service": {"status": "ok", "provider": "anthropic", "model": "claude-sonnet-4"},
    "disk_space": {"status": "ok", "available_gb": 45}
  }
}
```

---

## 4. Webhook

バッチ処理完了時のコールバック（設定時）：

```json
POST <callback_url>
Content-Type: application/json

{
  "event": "batch_completed",
  "job_id": "batch_20250628_001",
  "status": "completed",
  "summary": {
    "total": 15,
    "success": 14,
    "failed": 1
  },
  "results_url": "/batch/batch_20250628_001/results"
}
```

---

## 5. エラーコード一覧

| コード | HTTP Status | 説明 |
|---|---|---|
| `INVALID_FILE_FORMAT` | 400 | サポート外のファイル形式 |
| `INVALID_FILE` | 400 | ファイルが読み込めない（破損/暗号化） |
| `FILE_TOO_LARGE` | 413 | ファイルサイズ超過（上限 50MB） |
| `VALIDATION_ERROR` | 422 | リクエストパラメータ不正 |
| `LLM_ERROR` | 502 | LLM API エラー |
| `RATE_LIMITED` | 429 | API レート制限超過 |
| `JOB_NOT_FOUND` | 404 | ジョブIDが見つからない |
| `RULE_NOT_FOUND` | 404 | ルールIDが見つからない |
| `UNAUTHORIZED` | 401 | 認証エラー |
| `INTERNAL_ERROR` | 500 | サーバー内部エラー |

---

## 6. レート制限

| プラン | 制限 | バースト |
|---|---|---|
| 開発 | 10 req/min | 20 |
| 本番（小規模） | 100 req/min | 200 |
| 本番（大規模） | 1000 req/min | 2000 |

制限超過時は `429 Too Many Requests` と `Retry-After` ヘッダーが返されます。

---

## 7. 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| v1.0 | 2025-06-28 | 初版 |
