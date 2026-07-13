# JP Recruit Extractor — 日本招聘案件データ抽出システム

## 项目简介

日本 IT 招聘市场案件資料（PDF/Word/Excel/HTML/邮件/图片）的智能数据提取系统。

**核心理念**: AI 引导 → 规则固化 → 逐步脱离 LLM

### 四阶段路线

| 阶段 | 说明 |
|------|------|
| Phase 0 | 字段定义、样本收集、PoC |
| Phase 1 | 纯 LLM 模式，快速上线 ≥ 90% |
| Phase 2 | 规则学习引擎自动归纳提取规则 |
| Phase 3 | 80%+ 案件无需 LLM，秒级规则提取 ≥ 95% |
| Phase 4 | 规则库持续进化，维护成本趋近于零 |

### 当前状态 (2026-07-05 实測)

- ルール抽出パイプライン稼働中 (LLM 不使用、約 0.3 秒で 28 件処理)
- ルールライブラリ: **107** ルール / 11 フィールド
- 品質メトリクス: 案件名 100%, スキル 96%, 期間 96%, 日本語レベル 28%, 全文保持 100%

---

## 项目目录结构

```
jp-recruit-extractor/
├── .claude/                      # Claude Code 设定
│   ├── CLAUDE.md                 # 本文件
│   └── commands/                 # 自定义命令
│       ├── extract.md            # /extract - 运行规则提取
│       ├── llm-extract.md        # /llm-extract - 运行 LLM 提取
│       ├── evaluate.md           # /evaluate - 评估提取品质
│       ├── add-data.md           # /add-data - 添加新数据
│       ├── learn-rules.md        # /learn-rules - 学习规则
│       └── export.md             # /export - 导出结果
├── src/
│   ├── cli.py                    # CLI 入口 (typer)
│   ├── config.py                 # 全局設定
│   ├── preprocessor/             # 格式归一化 / 文本提取 / 日语标准化
│   ├── llm_engine/               # LLM 提取引擎 (Claude/OpenAI/DeepSeek)
│   ├── rule_engine/              # 规则引擎 (core, matcher, validator)
│   ├── rule_learner/             # 规则学习引擎 (模式发现、规则生成)
│   ├── rule_repository/          # 规则存储 (SQLite)
│   ├── api/                      # FastAPI 服务
│   └── common/                   # 数据模型 (models.py, schema.py, utils.py)
├── data/
│   ├── rules/
│   │   └── field_rules.json      # ルールライブラリ (107 ルール)
│   ├── output/                   # 抽出结果 JSON / Excel
│   └── cache/                    # 缓存
├── docs/                         # 文档
├── tests/                        # pytest 测试
├── requirements.txt
├── setup.py
└── README.md
```

---

## 数据模型 (RecruitmentCase)

核心模型在 `src/common/models.py`，案件字段:

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | str | 案件名 |
| `project_description` | str | 案件概要 |
| `skill_requirement` | list[str] | 必須スキル |
| `preferred_skills` | list[str] | 歓迎スキル |
| `experience_years` | ExperienceYears | 経験年数 (min, max) |
| `location` | Location | 勤務地 (city, station, remote_policy) |
| `rate` | Rate | 単価 (min, max, unit, currency) |
| `period` | Period | 期間 (start_date, end_date, long_term) |
| `headcount` | int | 募集人数 |
| `industry` | str | 業種 |
| `trade_flow` | TradeFlow | 商流 (contract_type, layers) |
| `japanese_level` | JapaneseLevelInfo | 日本語レベル (native/business/n2/n3/n4) |
| `english_level` | EnglishLevelInfo | 英語レベル |
| `working_hours` | WorkingHours | 勤務時間 |
| `interviews` | int | 面接回数 |
| `immediate_start` | bool | 即日参画可否 |
| `screening_flow` | str | 選考フロー |
| `remarks` | str | 備考 |
| `original_text` | str | 案件全文（抽出元の生テキスト） |

---

## 実行方法

### 前置准备

```bash
source .venv/bin/activate
```

### ルール抽出 (LLM 不使用, 0.3 秒)

```bash
python3 src/run_pipeline.py
```

### LLM 抽出 (DeepSeek API 必要)

```bash
python3 src/run_llm_pipeline.py
```

### LLM + ルール結果マージ

```bash
python3 src/merge_results.py
```

### Excel 出力

```bash
python3 src/export_excel.py
```

### CLI 工具

```bash
python -m src.cli extract --input sample.pdf --output result.json
python -m src.cli batch --input-dir ./inbox/ --output-dir ./outbox/
python -m src.cli rule list
python -m src.cli init
python -m src.cli stats
```

### API 服务

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

---

## ルールシステム

ルール定义在 `data/rules/field_rules.json`，按 field 分组:

```json
{
  "rules": {
    "period": [
      {"id": "period_001", "pattern": "...", "priority": 90, "field": "period"},
      ...
    ],
    "skill_must": [...],
    "skill_preferred": [...],
    "location": [...],
    "rate": [...],
    ...
  },
  "post_process": { ... }
}
```

### ルール命名规范

- `{field}_{3桁連番}`: 例 `period_001`, `skill_must_001`
- Excel 专用: `{field}_rowtext_{連番}`
- 日本語レベル: `jp_{3桁}`, 英語レベル: `eng_{3桁}`

### ルール追加流程

1. 編集 `data/rules/field_rules.json`
2. 実行 `python3 src/run_pipeline.py`
3. 確認出力 JSON / Excel

---

## 确立的规则 (memory 记录)

- **月のみ→現在年デフォルトルール**: 月のみの記載は現在年をデフォルト、過ぎた月は翌年
- **日本語レベル**: ルールID→レベルマッピング方式 (jp_007/jp_008/jp_009 対応)
- **案件全文保持**: 各案件に `original_text` で抽出元テキストを保持
- **スキル抽出**: `skill_must` / `skill_preferred` セクションを個別抽出

---

## 核心约定

### 语言

- 代码注释用日语（案件データ用語に合わせる）
- CLI 输出用日语
- 技术文档用中文
- ルールパターンは JSON で管理

### 编码

- Python 3.11+, Pydantic v2
- ルールエンジンは純 Python、LLM 依存なし
- 日付処理: 月のみ→年推論ルール strict 準拠
- テスト: pytest

### ファイル処理

- TXT: 単一案件
- Markdown: `案件名/■` マーカーで分割、複数案件対応
- Excel: 1行=1案件、列マッピング固定
- PDF/Word/HTML/画像/メール: `preprocessor/` で処理、LLM 抽出対応

### 出力形式

- JSON: `data/output/extraction_result_{timestamp}.json`
- Excel: `data/output/jp_recruit_cases_{timestamp}.xlsx` (41 列)
