# 05 — 用户操作手册 (User Manual)

> **文档版本**: v1.1
> **更新日期**: 2026-07-06
> **📗 推荐阅读**: [USER-MANUAL.md](USER-MANUAL.md)（完整版使用手册，涵盖交互式反馈循环、规则系统详解、Claude Code Skill 集成等全部功能）

## 1. 概述

JP Recruit Extractor 是一款面向日本 IT 招聘案件文档的智能数据提取工具。支持从 PDF / Word / Excel / HTML / 邮件 / 图片中提取结构化数据。

### 1.1 能力说明

| 功能 | 说明 |
|---|---|
| 单文件提取 | 输入一个文件，返回结构化 JSON |
| 批量提取 | 输入文件夹，批量处理并输出结果 |
| 规则管理 | 查看、启用、禁用提取规则 |
| 人工修正 | 对提取结果进行修正并反馈，用于规则优化 |
| 格式注册 | 注册新的文档模板，加速处理 |

---

## 2. 安装

### 2.1 系统要求

- Python 3.11+
- Tesseract OCR（图片处理需要）
- MeCab（日语分詞、可选但推荐）

### 2.2 安装步骤

```bash
# 1. Clone 项目
git clone <repository-url>
cd jp-recruit-extractor

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装可选依赖
pip install -e ".[ml,ocr]"  # ML 和 OCR 增强

# 5. 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填写 API Key
```

### 2.3 环境变量

```bash
# .env 文件配置

# LLM API Keys（至少设置一个）
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# 系统配置
EXTRACTOR_LOG_LEVEL=INFO
EXTRACTOR_RULE_DB_PATH=data/rules/rules.db
EXTRACTOR_CACHE_DIR=data/cache/
EXTRACTOR_MAX_WORKERS=4

# OCR 配置
TESSERACT_CMD=/usr/local/bin/tesseract
TESSERACT_LANG=jap

# API 服务配置
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 3. 快速开始

### 3.1 单文件提取

```bash
# 基本用法
python -m src.cli extract --input sample.pdf

# 指定输出文件
python -m src.cli extract --input 案件概要書.pdf --output result.json

# 指定只提取某些字段
python -m src.cli extract --input sample.pdf --fields project_name,skill_requirement,rate

# 强制使用 LLM 模式（跳过规则）
python -m src.cli extract --input sample.pdf --mode llm

# 强制使用规则模式（跳过 LLM）
python -m src.cli extract --input sample.pdf --mode rule
```

### 3.2 批量处理

```bash
# 处理文件夹内所有案件文件
python -m src.cli batch --input-dir ./inbox/ --output-dir ./outbox/

# 指定输出格式（json / csv / excel）
python -m src.cli batch --input-dir ./inbox/ --output-dir ./outbox/ --format excel

# 多线程处理
python -m src.cli batch --input-dir ./inbox/ --output-dir ./outbox/ --workers 8

# 仅处理未处理的文件（跳过已存在输出文件的）
python -m src.cli batch --input-dir ./inbox/ --output-dir ./outbox/ --skip-existing
```

### 3.3 查看结果

```bash
# 以可读格式查看提取结果
python -m src.cli extract --input sample.pdf --pretty

# 提取结果示例输出:
```
{
  "project_name": "某証券会社向け基幹システム開発",
  "skill_requirement": ["Java", "Spring Boot", "AWS"],
  "location": {
    "city": "東京都品川区",
    "station": "品川駅"
  },
  "rate": {
    "min": 70,
    "max": 80,
    "unit": "monthly"
  },
  "period": {
    "start_date": "2025-07-01",
    "end_date": "2026-03-31"
  },
  ...
}
```
```

---

## 4. Web API 使用

### 4.1 启动服务器

```bash
# 默认配置启动
python -m src.api.app

# 指定端口
python -m src.api.app --port 8080 --reload

# 或使用 uvicorn 直接启动
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.2 API 调用示例

#### 单文件提取

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@sample.pdf" \
  -F "mode=auto" \
  -F "fields=project_name,skill_requirement,rate" \
  | jq .
```

#### 批量提交

```bash
curl -X POST http://localhost:8000/batch \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf" \
  -F "callback_url=https://your-server.com/webhook" \
  | jq .
# 返回 job_id → 用 job_id 轮询进度
```

#### 查询批处理进度

```bash
curl http://localhost:8000/batch/{job_id}

# 响应:
# {
#   "job_id": "batch_20250628_001",
#   "status": "processing",
#   "progress": { "done": 5, "total": 20, "failed": 0 },
#   "results_url": "/batch/batch_20250628_001/results"
# }
```

#### 提交修正反馈

```bash
curl -X PUT http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_00123",
    "field": "skill_requirement",
    "extracted_value": ["Java", "AWS"],
    "corrected_value": ["Java", "Spring Boot", "AWS"],
    "correction_type": "missing_value"
  }'
```

### 4.3 交互式 API 文档

启动服务器后访问：

```
http://localhost:8000/docs   → Swagger UI
http://localhost:8000/redoc  → ReDoc
```

---

## 5. 规则管理

### 5.1 CLI 规则管理

```bash
# 列出所有规则
python -m src.cli rule list

# 列出特定字段的规则
python -m src.cli rule list --field skill_requirement

# 查看规则详情
python -m src.cli rule show --rule-id field_skill_001

# 启用/禁用规则
python -m src.cli rule toggle --rule-id field_skill_001 --enable
python -m src.cli rule toggle --rule-id field_skill_001 --disable

# 测试规则
python -m src.cli rule test --rule-id field_skill_001 --input sample.txt

# 手动触发规则学习
python -m src.cli rule learn --field skill_requirement --format-type template_a
```

### 5.2 规则统计

```bash
# 查看系统统计概要
python -m src.cli stats

# 输出示例:
# ┌────────────────────┬──────────┐
# │ Metric             │ Value    │
# ├────────────────────┼──────────┤
# │ Total rules        │ 156      │
# │ Active rules       │ 132      │
# │ Rule coverage      │ 78.5%    │
# │ Avg confidence     │ 0.91     │
# │ LLM call rate      │ 21.5%    │
# │ Processed docs     │ 1,203    │
# └────────────────────┴──────────┘
```

---

## 6. 人工修正工作流

### 6.1 何时需要人工修正

- 提取结果置信度低于 0.7
- 规则引擎无法匹配 → 以 LLM 模式提取后自动标记
- 字段间存在冲突（例：rate.max < rate.min）
- 系统无法识别文档格式

### 6.2 修正流程

```
1. 系统标记低置信度结果
       │
       ▼
2. 修正者が結果を確認
   ┌─────────────────────────────────────┐
   │ 案件名: 某証券会社向け基幹システム     │
   │ スキル: [Java, Spring, AWS]         │
   │ 単価: 70-80万円                      │
   │                                      │
   │ [✓] 正确  [✗] 修正  [ ] スキル追加   │
   └─────────────────────────────────────┘
       │
       ▼
3. 修正送信 → システムにフィードバック
       │
       ▼
4. ルール学習エンジンが修正を分析
   → パターン発見 → ルール生成 or ルール更新
```

### 6.3 CLI 修正操作

```bash
# 列出待修正条目
python -m src.cli feedback list --status pending

# 提交修正
python -m src.cli feedback submit \
  --document-id doc_00123 \
  --field skill_requirement \
  --corrected "Java,Spring Boot,AWS,PostgreSQL"

# 确认正确（无需修正）
python -m src.cli feedback confirm --document-id doc_00123
```

---

## 7. 最佳实践

### 7.1 文档准备

| 文档类型 | 最佳实践 |
|---|---|
| PDF | 文字版 PDF（非扫描件）效果最佳。扫描件需 OCR 且准确率取决于画质 |
| 图片 | 解像度 300dpi 以上推奨。文字がはっきり読めること |
| Word/Excel | テーブル構造が保持されていれば高精度で抽出可能 |
| HTML 邮件 | HTML ソースから直接抽出可。装飾タグは自動除去 |

### 7.2 精度提升技巧

1. **统一文件名格式**: `YYYY-MM-DD_案件名_会社名.pdf`
2. **避免密码保护文件**: 系统不支持加密文档
3. **合并相关文档**: 同一案件有多个附件时，合并后提取效果更好
4. **修正结果要积极反馈**: 修正データが多ければ多いほど、ルールが賢くなる

### 7.3 性能考虑

- 单文档提取通常 < 10 秒（LLM 模式）
- 规则模式提取 < 1 秒
- 大量批处理建议使用异步模式 + 多 workers
- 高峰期考虑 LLM API の rate limit

---

## 8. トラブルシューティング

### 8.1 よくある問題

| 問題 | 原因 | 解決策 |
|---|---|---|
| "Unsupported format" | 未対応のファイル形式 | 対応形式に変換するか、新形式として登録 |
| LLM 出力が JSON として無効 | API 応答が不完全 | 再試行、または model を変更 |
| スキルが正しく分割されない | 区切り文字が特殊 | ルールの postProcess.split を調整 |
| 日付が正しく抽出されない | 和暦/西暦混在 | ルールを修正してパターンを追加 |
| 抽出結果が空になる | ルール未作成 or テンプレート未登録 | 初回は自動的に LLM モードで抽出 |

### 8.2 ログの確認

```bash
# リアルタイムログ
tail -f data/extractor.log

# エラーのみ表示
tail -f data/extractor.log | grep ERROR

# 特定ドキュメントのログ
grep "doc_00123" data/extractor.log
```

---

## 9. 附录: ファイル形式対応状況

| 形式 | 対応 | 備考 |
|---|---|---|
| PDF (テキスト) | ✓ | PyMuPDF で抽出 |
| PDF (スキャン) | ✓ | OCR 必要（処理時間増加） |
| Word (.docx) | ✓ | — |
| Word (.doc) | △ | 古い形式、変換推奨 |
| Excel (.xlsx) | ✓ | — |
| HTML | ✓ | — |
| メール (.eml) | ✓ | — |
| メール (.msg) | △ | Outlook形式、変換推奨 |
| 画像 (.png/.jpg) | ✓ | OCR 依存、画質注意 |
| プレーンテキスト | ✓ | — |

---

## 10. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2025-06-28 | 初版 |
