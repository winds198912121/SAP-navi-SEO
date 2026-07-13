# 01 — 字段定义规范 (Field Definition Specification)

> **文档版本**: v1.0  
> **更新日期**: 2025-06-28  
> **状态**: 已批准

## 1. 概述

本文档定义了日本 IT 招聘案件中需要从原始文档提取的全部字段。所有字段均以 JSON Schema 形式定义，作为 LLM 结构化输出和规则引擎的统一数据契约。

### 1.1 字段分类

```
核心字段 (Core)      — 必须提取，每个案件必备
    案件名、スキル要件、勤務地、単価
    ─────────────────────────────────
重要字段 (Important) — 业务关键字段，尽量提取
    期間、募集人数、業種、商流、日本語レベル
    ─────────────────────────────────
辅助字段 (Auxiliary) — 补充信息，有则提取
    英語レベル、勤務時間、備考、面接回数、即日可否
    ─────────────────────────────────
来源字段 (Source)    — 元数据，系统自动填充
    ファイル形式、ファイル名、受信日、原文パス
```

### 1.2 字段命名规则

- 使用英文 snake_case
- 字段名自描述
- 枚举值统一使用小写 snake_case

---

## 2. JSON Schema 完整定义

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "JapaneseRecruitmentCase",
  "description": "日本IT招聘案件结构化数据",
  "type": "object",
  "required": [
    "project_name",
    "skill_requirement",
    "location",
    "rate"
  ],
  "properties": {

    "project_name": {
      "type": "string",
      "description": "案件名 / プロジェクト名。案件を識別する固有の名称。",
      "minLength": 1,
      "maxLength": 200,
      "examples": [
        "某証券会社向け基幹システム開発",
        "ECサイトリニューアルプロジェクト",
        "大手損保 次期顧客管理システム構築"
      ]
    },

    "project_description": {
      "type": "string",
      "description": "案件概要 / プロジェクト概要。案件の背景や目的、実施内容の簡単な説明。",
      "maxLength": 2000,
      "examples": [
        "既存のメインフレームシステムをJavaベースのWebシステムにリプレースするプロジェクト"
      ]
    },

    "skill_requirement": {
      "type": "array",
      "description": "必須スキル / 求めるスキル。応募者が必ず持っているべき技術スキル。",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "uniqueItems": true,
      "examples": [
        ["Java", "Spring Boot", "AWS", "MySQL"],
        ["Python", "Django", "PostgreSQL", "Docker"],
        ["React", "TypeScript", "Node.js"]
      ]
    },

    "preferred_skills": {
      "type": "array",
      "description": "尚可スキル / 歓迎スキル。あると望ましいが必須ではないスキル。",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true,
      "examples": [
        ["Kubernetes", "Terraform"],
        ["AWS認定資格", "日本語N1"]
      ]
    },

    "experience_years": {
      "type": "object",
      "description": "必要経験年数。業界経験 or 特定スキルの実務経験年数。",
      "properties": {
        "min": {
          "type": "integer",
          "description": "最低経験年数",
          "minimum": 0,
          "examples": [3]
        },
        "max": {
          "type": "integer",
          "description": "最高経験年数（あれば）",
          "minimum": 0,
          "examples": [10]
        },
        "description": {
          "type": "string",
          "description": "経験年数の説明文（自由形式）",
          "examples": ["Java 実務経験5年以上"]
        }
      }
    },

    "location": {
      "type": "object",
      "description": "勤務地。案件の作業場所に関する情報。",
      "required": ["city"],
      "properties": {
        "city": {
          "type": "string",
          "description": "都市名（東京都、大阪市など）",
          "examples": ["東京都港区", "大阪市北区", "名古屋市中区"]
        },
        "station": {
          "type": "string",
          "description": "最寄駅",
          "examples": ["品川駅", "大手町駅", "梅田駅"]
        },
        "remote_policy": {
          "type": "string",
          "description": "リモート可否の方針",
          "enum": ["full_remote", "hybrid", "office_only", "not_specified"],
          "enumDescriptions": [
            "フルリモート可",
            "ハイブリッド（週N日出社）",
            "オンサイトのみ",
            "未記載"
          ]
        },
        "remote_detail": {
          "type": "string",
          "description": "リモートに関する補足",
          "examples": ["週2日出社、3日リモート", "初期のみ出社必要"]
        },
        "relocation_required": {
          "type": "boolean",
          "description": "転居を伴う異動の要不要"
        }
      }
    },

    "rate": {
      "type": "object",
      "description": "単価 / 給与。案件の報酬に関する情報。",
      "required": ["unit"],
      "properties": {
        "min": {
          "type": "number",
          "description": "最低単価。単位は unit フィールドを参照。",
          "minimum": 0,
          "examples": [50, 600000]
        },
        "max": {
          "type": "number",
          "description": "最高単価。単位は unit フィールドを参照。",
          "minimum": 0,
          "examples": [70, 800000]
        },
        "unit": {
          "type": "string",
          "description": "単価の単位",
          "enum": ["monthly", "daily", "hourly", "yearly"]
        },
        "unit_jp": {
          "type": "string",
          "description": "単位の日本語表記（原文ママ）",
          "examples": ["万円", "千円", "円", "月額", "日額", "時給"]
        },
        "currency": {
          "type": "string",
          "description": "通貨",
          "default": "JPY",
          "examples": ["JPY", "USD"]
        },
        "note": {
          "type": "string",
          "description": "単価に関する補足",
          "examples": ["交通費別", "残業代別途", "月額単価制"]
        }
      }
    },

    "period": {
      "type": "object",
      "description": "契約期間 / 作業期間。",
      "properties": {
        "start_date": {
          "type": "string",
          "format": "date",
          "description": "開始日。形式: YYYY-MM-DD",
          "examples": ["2025-07-01"]
        },
        "end_date": {
          "type": "string",
          "format": "date",
          "description": "終了日（あれば）。形式: YYYY-MM-DD",
          "examples": ["2026-03-31"]
        },
        "duration_months": {
          "type": "integer",
          "description": "予定月数",
          "minimum": 1,
          "examples": [6, 12]
        },
        "long_term": {
          "type": "boolean",
          "description": "長期案件かどうかのフラグ。長期/中期/短期といった記載がある場合。"
        },
        "note": {
          "type": "string",
          "description": "期間に関する補足",
          "examples": ["以降、案件状況により更新あり"]
        }
      }
    },

    "headcount": {
      "type": "integer",
      "description": "募集人数",
      "minimum": 1,
      "maximum": 999,
      "examples": [1, 2, 5, 10]
    },

    "industry": {
      "type": "string",
      "description": "業種 / 案件区分。エンドユーザーの業種。",
      "examples": ["金融", "保険", "流通", "通信", "公共", "製造", "SIer"]
    },

    "trade_flow": {
      "type": "object",
      "description": "商流 / 契約形態。契約の種類と商流階層。",
      "properties": {
        "contract_type": {
          "type": "string",
          "description": "契約形態",
          "enum": ["jun_inin", "ukeoi", "haken", "ses", "other"],
          "enumDescriptions": [
            "準委任",
            "請負",
            "派遣",
            "SES（客先常駐型）",
            "その他"
          ]
        },
        "contract_type_jp": {
          "type": "string",
          "description": "契約形態の日本語原文",
          "examples": ["準委任", "請負", "派遣", "SES"]
        },
        "layers": {
          "type": "integer",
          "description": "商流階層数。自社からエンド客户までの間に何社入るか。",
          "minimum": 1,
          "maximum": 10,
          "examples": [1, 2, 3]
        },
        "end_client": {
          "type": "string",
          "description": "最終顧客先 / エンドユーザー",
          "examples": ["〇〇銀行", "△△生命保険"]
        },
        "intermediaries": {
          "type": "array",
          "description": "中間に存在する会社",
          "items": { "type": "string" },
          "examples": [["株式会社A", "株式会社B"]]
        }
      }
    },

    "japanese_level": {
      "type": "object",
      "description": "日本語レベル。募集条件としての日本語能力要件。",
      "properties": {
        "level": {
          "type": "string",
          "enum": ["native", "business", "n2", "n3", "n4", "not_specified"],
          "description": "日本語レベル"
        },
        "level_jp": {
          "type": "string",
          "description": "日本語表記（原文ママ）",
          "examples": ["母国語", "ビジネスレベル", "N2以上", "日常会話レベル"]
        },
        "detail": {
          "type": "string",
          "description": "日本語要件の詳細",
          "examples": ["日本語でのドキュメント作成・メールコミュニケーションができること"]
        }
      }
    },

    "english_level": {
      "type": "object",
      "description": "英語レベル。募集条件としての英語能力要件。",
      "properties": {
        "level": {
          "type": "string",
          "enum": ["business", "daily", "none", "native", "not_specified"],
          "description": "英語レベル"
        },
        "detail": {
          "type": "string",
          "description": "英語要件の詳細",
          "examples": ["英語での読み書きができること", "TOEIC 800点以上"]
        }
      }
    },

    "working_hours": {
      "type": "object",
      "description": "勤務時間。",
      "properties": {
        "start": {
          "type": "string",
          "description": "開始時間",
          "examples": ["09:00", "10:00", "09:30"]
        },
        "end": {
          "type": "string",
          "description": "終了時間",
          "examples": ["17:00", "18:00", "18:30"]
        },
        "flex_time": {
          "type": "boolean",
          "description": "フレックスタイム制の有無"
        },
        "overtime": {
          "type": "string",
          "description": "残業の有無と目安",
          "examples": ["月20時間以内", "なし", "場合によりあり"]
        }
      }
    },

    "interviews": {
      "type": "integer",
      "description": "面接回数",
      "minimum": 0,
      "maximum": 10,
      "examples": [1, 2, 3]
    },

    "immediate_start": {
      "type": "boolean",
      "description": "即日／即参画可能かどうか"
    },

    "screening_flow": {
      "type": "string",
      "description": "選考フロー。面談から参画までの流れ。",
      "examples": ["書類選考 → 面談1回 → 採用", "面談1回のみ"]
    },

    "remarks": {
      "type": "string",
      "description": "備考。上記のどの項目にも属さない特記事項。",
      "maxLength": 2000,
      "examples": [
        "2025年7月参画予定、服装自由、資格取得支援制度あり"
      ]
    },

    "source": {
      "type": "object",
      "description": "案件来源信息。システム自動記録。",
      "properties": {
        "original_format": {
          "type": "string",
          "enum": ["pdf", "word", "excel", "html", "email", "image", "text", "unknown"]
        },
        "filename": {
          "type": "string",
          "description": "元ファイル名"
        },
        "source_url": {
          "type": "string",
          "format": "uri",
          "description": "案件URL（取得元がWebの場合）"
        },
        "received_date": {
          "type": "string",
          "format": "date",
          "description": "受信日／取得日。YYYY-MM-DD"
        },
        "sender": {
          "type": "string",
          "description": "送信元（メールの場合）"
        },
        "extraction_date": {
          "type": "string",
          "format": "date-time",
          "description": "抽出実行日時"
        },
        "extraction_mode": {
          "type": "string",
          "enum": ["rule_only", "llm_only", "hybrid"],
          "description": "抽出に使用したモード"
        }
      }
    }
  }
}
```

---

## 3. 字段提取优先级策略

### 3.1 多源性处理

同一个字段可能在文档中多处出现，处理策略：

| 场景 | 策略 |
|---|---|
| 规则提取 vs LLM 提取 结果一致 | 直接采用 |
| 规则提取 vs LLM 提取 冲突 | 取置信度高者；若都低则标记需人工确认 |
| 同模式多个匹配（如2个スキル段落） | 合并去重后取并集 |
| 字段缺失 | 标记 null，不在 required 范围的就不报错 |

### 3.2 值标准化规则

| 字段 | 标准化规则 |
|---|---|
| `rate.unit` | 万円/月 → `monthly`、日額 → `daily`、時給 → `hourly`、年収 → `yearly` |
| `rate.min/max` | 単位を統一して数値化（例: 70万円/月 → 70; 80万/月 → 80） |
| `period.start_date` | 令和N年M月D日 → YYYY-MM-DD; 2025年7月→2025-07-01; 即日→today |
| `japanese_level` | "N2以上" → n2; "ビジネスレベル" → business; "ネイティブ" → native |
| `skill_requirement` | 全角英数字→半角; 技術名の揺れ統一（例: JQuery→jQuery） |
| `location.city` | "東京"→"東京都"; "大阪"→"大阪府"（必要に応じて正式名称に補完） |

---

## 4. 扩展机制

### 4.1 添加新字段

1. 在 `schema.py` 的 JSON Schema 中添加字段定义
2. 指定 required / optional
3. 更新 LLM 的 Prompt Template（在 JSON output 示例中体现）
4. 规则引擎无需额外改动——新字段自动进入提取管线

### 4.2 字典映射

スキル名、地域名等に同義語／表記揺れがある場合、辞書ファイルで管理：

```json
{
  "skill_synonyms": [
    {"canonical": "Java", "variants": ["JAVA", "java", "Java11", "Java17", "J2SE"]},
    {"canonical": "JavaScript", "variants": ["javascript", "Javascript", "JS", "ECMAScript"]},
    {"canonical": "TypeScript", "variants": ["typescript", "Type Script", "TS"]}
  ],
  "location_synonyms": [
    {"canonical": "東京都", "variants": ["東京", "Tokyo", "tokyo", "東京都内"]},
    {"canonical": "大阪市", "variants": ["大阪", "Osaka", "osaka", "大阪市内"]}
  ]
}
```

---

## 5. 验证规则

各字段的校验规则（在 `validator.py` 中实现）：

| 字段 | 校验规则 |
|---|---|
| `project_name` | 非空、长度 ≥ 2 |
| `skill_requirement` | 至少 1 个 skill、每个 skill 长度 ≥ 1 |
| `location.city` | 非空 |
| `rate.min` | ≤ rate.max（当两者皆存在时） |
| `rate.max` | ≥ rate.min |
| `period.start_date` | ≤ period.end_date（当两者皆存在时） |
| `period.duration_months` | ≤ 120（10年） |
| `headcount` | 1 ≤ headcount ≤ 999 |
| `interviews` | 0 ≤ interviews ≤ 10 |
| `trade_flow.layers` | 1 ≤ layers ≤ 10 |

---

## 6. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|---|---|---|---|
| v1.0 | 2025-06-28 | 初版制定 | — |
