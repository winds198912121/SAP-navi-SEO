# JP Recruit Extractor 使用手册 v1.0

日本招聘案件データ抽出システム — ルールベース／LLM ハイブリッド抽出ツール

---

## 目录

1. [系统概述](#1-系统概述)
2. [快速安装](#2-快速安装)
3. [运行模式详解](#3-运行模式详解)
4. [数据文件格式要求](#4-数据文件格式要求)
5. [提取字段一览](#5-提取字段一览)
6. [使用输出结果](#6-使用输出结果)
7. [规则系统](#7-规则系统)
8. [交互式反馈循环（核心功能）](#8-交互式反馈循环核心功能)
9. [作为 Claude Code Skill 使用](#9-作为-claude-code-skill-使用)
10. [自定义命令参考](#10-自定义命令参考)
11. [API 服务](#11-api-服务)
12. [常见问题](#12-常见问题)
13. [附录：术语表](#13-附录术语表)

---

## 1. 系统概述

### 1.1 解决什么问题

日本 IT 招聘市场每天流通大量案件资料（日语：**案件**，指 IT 项目/职位需求），格式繁杂——PDF、Word、Excel、HTML 邮件、图片扫描件、纯文本、Markdown 等混杂在一起。每个案件包含：项目名称、必需技能、工作地点、单价、期间、日语要求等关键字段。

**人工整理 100 个案件需要数小时，且容易遗漏。** 本系统可以在 0.3 秒内从 3 种格式中提取 28 个案件的结构化数据，零成本。

### 1.2 核心理念：三阶段进化

```
Phase 1: LLM 提取（快速覆盖，成本高） ──→  准确率 ≥ 90%
    │
    ▼
Phase 2: 规则学习（从 LLM 结果自动归纳模式） ──→ 覆盖增加
    │
    ▼
Phase 3: 规则引擎为主（80%+ 案件用规则，秒级，零成本） ──→ 准确率 ≥ 95%
    │
    ▼
Phase 4: 持续进化（用户反馈闭环 → 自动生成新规则）
```

**当前阶段：** Phase 1~2 过渡，107 条规则覆盖 11 个字段，28 件案件约 0.3 秒完成规则提取。

### 1.3 系统架构

```
输入文件 (TXT / MD / Excel / PDF / Word / HTML / 邮件 / 图片)
    │
    ▼
┌─ 预处理层 ─────────────────────────────┐
│  格式检测 → 文本提取 → 日语标准化       │
│  (PDF: PyMuPDF / 图片: OCR / Excel: 行读取)│
└────────────────────────────────────────┘
    │
    ▼
┌─ 路由调度 ─────────────────────────────┐
│  规则匹配检查 → 决策: 规则 | LLM | 混合  │
│  (当前: 硬编码规则模式)                  │
└────────────────────────────────────────┘
    │
    ▼
┌─ 提取执行层 ───────────────────────────┐
│  规则引擎 (107条正则)             0.3秒 │
│  LLM引擎 (DeepSeek API)         ~30秒   │
│  结果融合 (规则+LLM 合并)               │
└────────────────────────────────────────┘
    │
    ▼
┌─ 输出层 ───────────────────────────────┐
│  JSON (完整结构化数据)                  │
│  Excel (41列 × N行, 带格式/筛选)       │
│  (通过 API: REST JSON)                  │
└────────────────────────────────────────┘
    │
    ▼
┌─ 反馈循环 ─────────────────────────────┐
│  用户确认 → LLM修正 → 规则自动生成       │
│  → 规则库更新 → 重新提取 → 验证         │
└────────────────────────────────────────┘
```

---

## 2. 快速安装

### 2.1 系统要求

| 项目 | 要求 |
|------|------|
| Python | 3.11+ |
| 操作系统 | macOS / Linux / WSL |
| 磁盘 | ~200 MB（包含虚拟环境和依赖） |
| API Key（可选）| DeepSeek API（交互式反馈循环用）|

### 2.2 标准安装

```bash
# 1. 克隆仓库
git clone https://github.com/winds198912121/SAP-navi-SEO.git
cd jp-recruit-extractor

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证安装
bash .claude/skills/run-jp-recruit-extractor/driver.sh
```

### 2.3 配置 API Key（可选）

编辑 `.env` 文件：

```bash
# DeepSeek API（交互反馈循环需要）
EXTRACTOR_DEEPSEEK_API_KEY=sk-your-key-here

# 其他配置（可选修改）
EXTRACTOR_LOG_LEVEL=INFO
EXTRACTOR_MAX_WORKERS=4
```

> **注意：** 纯规则提取（`run_pipeline.py`）完全不需要 API Key，零成本运行。

### 2.4 一键安装为 Claude Code Skill

```bash
bash scripts/install-skill.sh
```

或者从 GitHub 远程安装（仓库公开后）：

```bash
curl -fsSL https://raw.githubusercontent.com/winds198912121/SAP-navi-SEO/main/scripts/install-skill.sh | bash
```

---

## 3. 运行模式详解

系统提供 **3 种运行模式**，适应不同场景。

### 3.1 模式 A：纯规则提取（推荐日常使用）

> **特点：** 最快（0.3 秒）、零成本、完全离线

```bash
source .venv/bin/activate
python3 src/run_pipeline.py
```

**内部流程：**
1. 读取 `data/rules/field_rules.json`（107 条规则）
2. 扫描 `data/` 目录下的 3 个源文件
3. 对每个案件应用正则表达式规则
4. 输出 JSON 到 `data/output/extraction_result_*.json`

**输出示例：**
```
📚 ルールライブラリ: field_rules.json
   全ルール数: 107

📄 処理中: 案件List.md
   ✓ 抽出完了: 10 件の案件
     [1] 小売業固定資産/リース管理導入PM支援
         場所:千葉県 | 単価:-万円/月 | 4スキル | 2026-07-01 JP:biz
     [2] 1名確定、残り枠1名!!
         場所:? | 単価:-万円/月 | 1スキル | 2027-06-01 JP:biz
     ...

✅ ルール抽出完了
   全案件数: 28
   使用ルール数: 107
   結果保存先: data/output/extraction_result_20260706_231513.json
```

### 3.2 模式 B：交互式反馈循环（推荐首次使用 / 规则优化）

> **特点：** 逐案件确认、可修正、自动学习规则

```bash
source .venv/bin/activate
python3 src/interactive_feedback.py
```

**工作流程：**

```
1. 选择操作
   [1] 运行规则提取
   [2] 查看现有结果
   [3] 退出

2. 选择要检查的案件 (1-28)

3. 判定结果
   用户: 这个案件的技能提取正确吗？ (y/n)

   ┌─ [YES] → 标记为 OK，进入下一案件
   │
   └─ [NO] → 进入 LLM 修正流程：
       a. 选择问题字段（如 skill_requirement）
       b. 描述问题（如 "Python 被漏掉了"）
       c. LLM 分析原文 → 显示修正提案
       d. 用户确认修正 (y/n)
       e. [YES] → 自动生成新正则规则 → 写入规则库
       f. 重新运行提取 → 继续验证

4. 全部确认完毕 → 退出
```

**适合场景：**
- 首次使用系统，想了解提取质量
- 发现提取不准确，想修正并永久改进规则
- 添加了新类型的数据文件，需要适配规则

### 3.3 模式 C：LLM 批量提取（探索新格式）

> **特点：** 适合规则未覆盖的新格式，但需要 API 费用

```bash
source .venv/bin/activate
python3 src/run_llm_pipeline.py
```

**适用场景：**
- 完全新的文件格式，尚无规则覆盖
- 作为规则学习的"老师数据"——先用 LLM 提取，Phase 2 从中学习规则
- 规则提取质量不满意时的补充手段

**费用估算：**

| 案件数 | DeepSeek API 费用（约） |
|--------|------------------------|
| 28 件 | ~¥30-60 日元（¥0.2-0.4） |
| 100 件 | ~¥100-200 日元 |

---

## 4. 数据文件格式要求

### 4.1 支持的格式

| 格式 | 支持模式 | 说明 |
|------|----------|------|
| **TXT (.txt)** | 规则 + LLM | 单个案件全文，或带标题的多个案件 |
| **Markdown (.md)** | 规则 + LLM | 多个案件用 `案件名：` / `■` / `🔥` 等标记分割 |
| **Excel (.xlsx)** | 规则 + LLM | 1 行 = 1 个案件，固定的 8 列结构 |
| PDF (.pdf) | LLM 专用 | 文字 PDF 用 PyMuPDF，扫描件需 OCR |
| Word (.docx) | LLM 专用 | — |
| HTML (.html) | LLM 专用 | — |
| 邮件 (.eml) | LLM 专用 | — |
| 图片 (.png/.jpg) | LLM 专用 | 需 Tesseract OCR |

### 4.2 Excel 格式要求（`7月SAP案件一覧_0610.xlsx` 格式）

| 列 | 字段 | 示例 |
|----|------|------|
| A | 番号 (No) | 1 |
| B | 時期 | 7月 |
| C | 人数 | 2名 |
| D | 案件名 | S/4 HANA パブクラ導入案件 |
| E | 役割 | PM |
| F | レベル | 上級 |
| G | 必須スキル | ABAP開発経験6年以上, CDS-View... |
| H | 場所 | 東京都品川区 |

> **注意：** 当前只处理前 8 列。单价等列在公式中（9 列以后），规则引擎暂不支持。

### 4.3 Markdown 案件分割规则

`run_pipeline.py` 使用以下标记识别案件边界：

```
案件名[：:]      → "案件名：xxx"
■ 案件名         → "■ 案件名"
🔥 或 ！！        → 特殊标记
①②③④⑤          → 数字圈标记
直接客户         → 直接客户
Need candidates → 英文 JD
----            → 分隔线
```

**示例案件 list：**

````markdown
案件名　：小売業固定資産/リース管理導入PM支援
案件概要：大手小売業における新システム導入プロジェクト
要求技術：【必須】・システム開発PM経験(3年以上)
　　　　　　　　　・固定資産/リース資産管理システムの導入
　　　　　【尚可】・不動産契約管理の知見
作業場所：千葉（在宅勤務割合：50%）
作業期間：2026/07/01～長期
募集人数：1名
外国籍　：可
面談回数：1回

-----

！！１名確定、残り枠１名！！
①　６月～長期、SE２名、【必須】Azure設計・構築経験３年以上...
②　6月～長期、PL+SE 2名、【必須】AWSまたGCP の運用経験...
````

### 4.4 新数据文件添加步骤

```bash
# 1. 复制文件到 data/
cp /path/to/your/new-cases.xlsx data/

# 2. 编辑 run_pipeline.py 中的 files_to_process 列表
#    追加一行:
#    ("new-cases.xlsx", "excel", processor.process_excel),

# 3. 运行提取
python3 src/run_pipeline.py
```

---

## 5. 提取字段一览

### 5.1 完整字段列表（19 个字段）

| 字段 | 类型 | 说明 | 规则覆盖率 |
|------|------|------|-----------|
| `project_name` | str | 案件名 / 项目名称 | **100%** |
| `project_description` | str | 案件概要 / 项目描述 | — |
| `skill_requirement` | list[str] | 必須スキル / 必需技能 | **96%** |
| `preferred_skills` | list[str] | 歓迎スキル / 加分技能 | ✓ |
| `experience_years` | obj | 経験年数 / 经验年限 | ✓ |
| `location.city` | str | 勤務地（都道府県/市区） | **50%** |
| `location.station` | str | 最寄駅 / 最近车站 | △ |
| `location.remote_policy` | enum | リモート方針 | ✓ |
| `rate.min` / `rate.max` | float | 単価（万円/月） | **7%** |
| `period.start_date` | date | 開始日（YYYY-MM-DD） | **96%** |
| `period.end_date` | date | 終了日 | ✓ |
| `headcount` | int | 募集人数 | ✓ |
| `industry` | str | 業種 / 行业 | ✓ |
| `trade_flow.contract_type` | enum | 契約形態（準委任/派遣/請負/SES） | ✓ |
| `japanese_level.level` | enum | 日本語レベル | **28%** |
| `english_level.level` | str | 英語レベル | ✓ |
| `interviews` | int | 面接回数 / 面试次数 | ✓ |
| `immediate_start` | bool | 即日参画可否 | ✓ |
| `remarks` | str | 備考 / 备注 | ✓ |
| `original_text` | str | **案件全文（保持率 100%）** | **100%** |

### 5.2 日付处理规则

参照 `date-rule-month-no-year` 记忆：

| 写法 | 解析结果 | 规则说明 |
|------|---------|---------|
| `2026/07/01` | `2026-07-01` | 标准格式直接使用 |
| `7月`（当前 7 月） | `2026-07-01` | 月のみ→当前年 |
| `6月`（已过月份） | `2027-06-01` | 已经过的月份→**次年**同月 |
| `即日` | `2026-07-06`（当天） | 即日→系统日期 |
| `Immediate` | `2026-07-06` | 同上 |
| `令和7年4月1日` | `2025-04-01` | 和暦→西暦自动转换 |

### 5.3 日语等级映射

| 规则 ID | 原文关键词 | 抽取等级 |
|---------|-----------|---------|
| `jp_001` | `日本語N1流暢` | business |
| `jp_002` | `日本語N1` / `N2以上` | n2 / n3 |
| `jp_003` | `日本語でのコミュニケーション必須` | business |
| `jp_004` | `日本語ネイティブ` / `日本語母国語` | native |
| `jp_005` | `日本語ビジネスレベル` | business |
| `jp_006` | `日本語流暢` | business |
| `jp_007` | `JAPANESE ONLY OK` | business |
| `jp_008` | `外国籍：可` | business |
| `jp_009` | `日语业务水平` | business |

### 5.4 契約形態映射

| 规则 ID | 原文关键词 | 抽取值 |
|---------|-----------|--------|
| `trade_001` | 準委任 | `jun_inin` |
| `trade_002` | 派遣または準委任 | `jun_inin` |
| `trade_003` | 派遣 | `haken` |
| `trade_004` | 請負 | `ukeoi` |
| `trade_005` | SES | `ses` |
| `trade_008` | 直接客户 | `other`（layers=1） |

### 5.5 リモート方針映射

| 规则 ID | 原文关键词 | 抽取值 |
|---------|-----------|--------|
| `remote_001` | フルリモート | `full_remote` |
| `remote_002` | 基本リモート | `full_remote` |
| `remote_003` | 在宅勤務割合：N% | `hybrid` |
| `remote_004` | 週N在宅 | `hybrid` |
| `remote_005` | 週N出社 | `hybrid` |
| `remote_006` | 在宅併用 | `hybrid` |
| `remote_007` | 基本フル出勤 | `office_only` |

---

## 6. 使用输出结果

### 6.1 JSON 输出

每个运行生成一个带时间戳的 JSON 文件：

```json
{
  "extraction_date": "2026-07-06T23:15:13.834229",
  "rule_library": {
    "path": "data/rules/field_rules.json",
    "total_rules": 107
  },
  "stats": {
    "total_cases": 28,
    "files_processed": 3,
    "extraction_mode": "rule_based"
  },
  "results": {
    "案件List.md": {
      "file": "案件List.md",
      "format": "text",
      "case_count": 10,
      "cases": [
        {
          "project_name": "小売業固定資産/リース管理導入PM支援",
          "skill_requirement": [
            "システム開発PM経験(3年以上)",
            "固定資産/リース資産管理システムの導入プロジェクト経験(2年以上)",
            "不動産契約管理の知見"
          ],
          "location": {
            "city": "千葉県",
            "remote_policy": "hybrid",
            "remote_detail": "在宅勤務割合：50%"
          },
          "period": {
            "start_date": "2026-07-01",
            "long_term": true
          },
          "original_text": "...（案件全文）..."
        }
      ]
    }
  }
}
```

### 6.2 Excel 输出

```bash
python3 src/export_excel.py
```

生成 `data/output/jp_recruit_cases_{timestamp}.xlsx`

**工作簿结构：**

| シート | 内容 | 行数 |
|--------|------|------|
| `全案件一覧` | 所有案件汇总（28行 × 41列） | 先头 |
| `サマリー` | 运行概要统计 | — |
| `案件1.txt` | 该文件案件 | 1 行 |
| `案件List.md` | 该文件案件 | 10 行 |
| `7月SAP案件一覧_0610.xlsx` | 该文件案件 | 17 行 |

**41 列明细：**

```
案件名 / 案件概要 / 必須スキル / 歓迎スキル /
経験年数(最小/最大/詳細) / 勤務地(都市) / 最寄駅 /
リモート方針 / リモート詳細 /
単価(下限/上限) / 単価単位 / 通貨 / 単価備考 /
開始日 / 終了日 / 予定月数 / 長期フラグ / 期間備考 /
募集人数 / 業種 /
契約形態 / 商流階層 / 最終顧客 /
日本語レベル / 日本語詳細 /
英語レベル / 英語詳細 /
勤務開始 / 勤務終了 / フレックス / 残業 /
面接回数 / 即日参画 / 選考フロー / 備考 /
ソース形式 / ファイル名 / 案件全文
```

**Excel 功能：**
- 表头冻结（Freeze Panes）
- 自动筛选（Auto Filter）
- 交替行背景色
- 列宽预设
- 多行技能自动调整行高

---

## 7. 规则系统

### 7.1 规则库位置

```
data/rules/field_rules.json
```

### 7.2 规则结构

```json
{
  "rule_library_version": "1.0",
  "created": "2026-06-28",
  "rules": {
    "period": [
      {
        "id": "period_001",
        "description": "YYYY/MM/DD 〜 YYYY/MM/DD",
        "pattern": "(\\d{4})[/\\-年](\\d{1,2})[/\\-月](\\d{1,2})?..."
      },
      ...
    ],
    "skill_must": [ ... ],
    "skill_preferred": [ ... ],
    "location": [ ... ],
    "japanese_level": [ ... ],
    ...
  },
  "post_process": {
    "skill_requirement": {
      "split_delimiters": ["、", "・", "/"],
      "filter_headers": ["【必須】", "【尚可】", "■ 必須", "※"],
      "min_length": 2,
      "deduplicate": true
    }
  }
}
```

### 7.3 规则命名规范

| 前缀 | 说明 | 示例 |
|------|------|------|
| `{field}_NNN` | 普通规则 | `period_001`, `skill_must_001` |
| `{field}_rowtext_NNN` | Excel row_text 专用 | `period_rowtext_001` |
| `jp_NNN` | 日本語レベル | `jp_001` ~ `jp_009` |
| `eng_NNN` | 英語レベル | `eng_001` ~ `eng_003` |
| `remote_NNN` | リモート方針 | `remote_001` ~ `remote_007` |
| `trade_NNN` | 商流 | `trade_001` ~ `trade_008` |
| `pname_NNN` | 案件名 | `pname_001` ~ `pname_004` |
| `loc_NNN` | 勤務地 | `loc_001` ~ `loc_007` |
| `head_NNN` | 募集人数 | `head_001` ~ `head_008` |
| `int_NNN` | 面接回数 | `int_001` ~ `int_004` |
| `rate_NNN` | 単価 | `rate_001` ~ `rate_007` |

### 7.4 规则管理方式

#### 方式 A：手动编辑

```bash
# 编辑规则文件
vim data/rules/field_rules.json

# 重新运行提取
python3 src/run_pipeline.py

# 查看效果
python3 src/export_excel.py
```

#### 方式 B：通过交互式反馈循环自动生成（推荐）

```
1. 运行 python3 src/interactive_feedback.py
2. 选择有问题的案件
3. 输入 "技能中的 Python 被漏了"
4. LLM 分析 → 生成修正案 → 用户确认
5. 新规则自动写入 field_rules.json
```

#### 方式 C：CLI 命令

```bash
# 查看规则列表
python -m src.cli rule list

# 查看特定字段规则
python -m src.cli rule list --field period

# 测试规则
python -m src.cli rule test period_001 sample.txt
```

### 7.5 当前规则统计

```
english_level:   3 rules
experience_years: 3 rules
headcount:       9 rules
immediate_start:  3 rules
industry:        9 rules
interviews:      4 rules
japanese_level:  9 rules
location:        7 rules
period:         14 rules
project_name:    4 rules
rate:            7 rules
remarks:         3 rules
remote_policy:   7 rules
skill_must:     13 rules
skill_preferred: 2 rules
station:         2 rules
trade_flow:      8 rules
───────────────────────────
总计:          107 rules / 17 字段群
```

---

## 8. 交互式反馈循环（核心功能）

这是本系统最强大的功能——**一个人机协作的规则进化闭环**。

### 8.1 启动

```bash
source .venv/bin/activate
python3 src/interactive_feedback.py
```

### 8.2 完整流程示例

```
===== JP Recruit Extractor - インタラクティブフィードバックループ =====
  ルール抽出 → 確認 → LLM修正 → ルール書き込み

  1. ルール抽出を実行 (LLM不使用)
  2. 既存の最新結果を確認
  3. 終了

選択 (1-3): 1

...（规则提取运行，0.3 秒）...

===== フィードバックラウンド 1 =====

📋 全 28 件の案件:
 #   案件名                                   ファイル                  スキル数
 ──── ──────────────────────────────────────── ──────────────────────── ────────
 1   小売業固定資産/リース管理導入PM支援         案件List.md              4
 2   1名確定、残り枠1名!!                       案件List.md              1
 ...

確認したい案件番号を入力 (1-28): 1

────────────────────────────────────────────────────────────
  案件名: 小売業固定資産/リース管理導入PM支援
  概要: 大手小売業における、固定資産/リース資産管理領域の新システム導入プロジェクト支援
────────────────────────────────────────────────────────────
  必須スキル: システム開発PM経験(3年以上), 固定資産/...
  歓迎スキル: 不動産契約管理の知見, 事業会社システム部門での経験
  勤務地: 千葉県 / ? / hybrid
  単価: ? ~ ? 万円/月
  期間: 2026-07-01 ~ ? (長期:True)
  日本語レベル: business (日本語ビジネスレベル)
  面接回数: 1
────────────────────────────────────────────────────────────

この案件「小売業固定資産/リース管理導入PM支援」の抽出結果は正しいですか？ (y/n): y
  ✅ OK、次の案件に進みます。

...（循环至全部确认 / 遇到需要修正的案件）...

この案件「Need candidates...」の抽出結果は正しいですか？ (y/n): n

🤖 LLM分析

問題があるフィールド名を入力してください:
  フィールド名一覧:
    skill_requirement      → skill_must (必須スキル)
    period                 → (期間)
    ...

  入力 (空Enter=全体分析): skill_requirement

何が問題ですか？
  例: 「スキルにPythonが抜けている」「期間が8月ではなく7月から」
  問題の説明: スキルに Infor LN, ERP が足りない

  🔍 LLMで分析中...（DeepSeek API呼び出し）

============================================================
  📋 LLM分析:
============================================================
  原文の"Experience related to ERP would be ideal"と
  "implement the Infor LN package"から、Infor LN と ERP
  に関する知識もスキルとして追加すべきです。

────────────────────────────────────────────────────────────
  🔧 修正提案:
    skill_requirement:
      - Someone with experience as a business consultant...
      - Able to communicate directly with user departments
      - Able to lead and facilitate sessions
      - Infor LN
      - ERP
  確信度: 92%

この修正で正しいですか？ (y/n): y
  ✅ 修正を確認しました。

  📝 新しいルール生成中...（DeepSeek API呼び出し）

📝 新しいルール候補 (skill_must):
  [1] skill_must_010: Infor LN/ERP スキル検出
      パターン: (Infor LN|ERP関連|パッケージ導入)

   💡 英語のJDでパッケージ製品名がスキルとして記載されているパターン

上記のルールをルールライブラリに追加しますか？ (y/n): y
   ✅ 1 件のルールを追加しました。

ルールを反映するため再実行しますか？ (y/n): y
...（重新运行提取，验证效果）...

続けて他の案件を確認しますか？ (y/n): n
```

### 8.3 三核心模块说明

| 模块 | 文件 | 功能 |
|------|------|------|
| **主循环** | `src/interactive_feedback.py` | 案件选择 → 用户判断 → LLM 修正 → 规则写入 |
| **LLM 分析** | `src/llm_fix.py` | 接收原文+规则结果+用户反馈 → 返回分析+修正 |
| **规则写入** | `src/rule_writer.py` | 分析 LLM 修正 → 生成正则规则 → 写入 JSON 文件 |

---

## 9. 作为 Claude Code Skill 使用

### 9.1 安装为全局 Skill

```bash
bash scripts/install-skill.sh
```

之后在任何项目的 Claude Code 中可调用：

```
/run-jp-recruit-extractor
```

### 9.2 在项目内使用

在项目根目录运行 Claude Code 时，自动识别：

- `.claude/skills/run-jp-recruit-extractor/` — Skill 定义
- `.claude/commands/` — 9 个自定义命令
- `.claude/CLAUDE.md` — 项目上下文文档

### 9.3 Skill driver 冒烟测试

```bash
bash .claude/skills/run-jp-recruit-extractor/driver.sh
```

自动执行：
1. ✓ 激活虚拟环境
2. ✓ 运行规则提取管线
3. ✓ 输出品质指标
4. ✓ 导出 Excel
5. ✓ 显示规则统计

---

## 10. 自定义命令参考

在项目目录中使用以下命令（需要 Claude Code 环境）：

### /extract — 规则提取

```bash
source .venv/bin/activate
python3 src/run_pipeline.py
```

### /llm-extract — LLM 提取

```bash
source .venv/bin/activate
python3 src/run_llm_pipeline.py
```

### /evaluate — 品质评估

```bash
source .venv/bin/activate
python3 -c "
import json
from pathlib import Path
files = sorted(Path('data/output/').glob('extraction_result_*.json'))
if not files:
    print('先に /extract を実行してください')
    exit()
with open(files[-1]) as f:
    data = json.load(f)
total = data['stats']['total_cases']
print(f'全{total}件:')
# ...统计显示...
"
```

### /export — Excel 输出

```bash
source .venv/bin/activate
python3 src/export_excel.py
```

### /status — 状态确认

```bash
source .venv/bin/activate
python -m src.cli stats
```

### /rule — 规则管理

```bash
python -m src.cli rule list --field period
```

### /learn-rules — 规则学习

```bash
python3 -c "
from src.rule_writer import get_existing_rules
rules = get_existing_rules()
for field, rlist in rules.items():
    print(f'{field}: {len(rlist)} rules')
"
```

### /add-data — 添加数据

```bash
# 1. 复制文件到 data/
cp new_file.xlsx data/
# 2. 编辑 run_pipeline.py 添加 files_to_process 条目
# 3. /extract
```

### /init — 项目初始化

```bash
python -m src.cli init
```

---

## 11. API 服务

### 11.1 启动 API 服务器

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

### 11.2 API 端点

| 方法 | 端點 | 说明 |
|------|------|------|
| POST | `/extract` | 单文件提取 |
| POST | `/batch` | 批量提交 |
| GET | `/batch/{job_id}` | 批处理进度 |
| PUT | `/feedback` | 提交修正反馈 |

### 11.3 调用示例

```bash
# 单文件提取
curl -X POST http://localhost:8000/extract -F "file=@sample.pdf"

# 交互式 API 文档
open http://localhost:8000/docs    # Swagger UI
open http://localhost:8000/redoc   # ReDoc
```

---

## 12. 常见问题

### 12.1 安装问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'openpyxl'` | 缺少依赖 | `pip install openpyxl` 或 `pip install -r requirements.txt` |
| `pydantic` 警告 `PydanticSerializationUnexpectedValue` | Pydantic v2 序列化枚举 | 外观警告，不影响结果正确 |
| `Python 3.12` 兼容性 | 已验证可运行 | 需 Python 3.11+ |

### 12.2 运行问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 提取结果为空 | 规则未覆盖新格式 | 运行 `/llm-extract` 先用 LLM 提取 |
| スキルが正しく抽出できない | 特殊区切字符 | 调整 `post_process.split_delimiters` |
| 日付が 1970-01-01 になる | 年未指定の誤変換 | 确认 `convert_jp_date()` 的"过月→次年"规则 |
| Excel の単価が空 | 单价在公式列的 9 列之后 | 当前规则取前 8 列，需添加 LLM 支持 |
| `typer` 相关错误 | CLI 使用的 typer 与某依赖冲突 | 直接执行 `src/` 下的 Python 脚本 |

### 12.3 LLM 相关问题

| 问题 | 原因 | 解决 |
|------|------|------|
| DeepSeek API 调用失败 | API Key 未设置 | 确认 `.env` 的 `EXTRACTOR_DEEPSEEK_API_KEY` |
| LLM 分析返回空 | API 超时或响应格式错误 | 重试，检查网络连接 |
| LLM 日付が古い | SYSTEM_PROMPT 中的日期硬编码 | 编辑 `run_llm_pipeline.py` 第 61-62 行的日期 |

### 12.4 规则相关问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 新規ルール追加後も結果が変わらない | 规则文件未重新加载 | 重新运行 `python3 src/run_pipeline.py` |
| ルールが重複した | 自动跳过重复 ID | 手动检查 `field_rules.json` |
| 正規表現が効かない | 特殊文字未转义 | 测试规则: `python -m src.cli rule test <id> sample.txt` |

---

## 13. 附录：术语表

| 日本語 | 中文 | 说明 |
|--------|------|------|
| 案件 | 项目/职位需求 | IT 工程师的招聘项目或岗位 |
| 案件名 | 项目名称 | — |
| 必須スキル | 必需技能 | 必备的技术栈要求 |
| 歓迎スキル / 尚可 | 加分技能 | 有則更好，非强制 |
| 単価 | 单价/薪资 | 通常以万円/月为单位 |
| 商流 | 合同链路 | 客户→一次请负→二次请负→...→工程师 |
| 準委任 | 准委任契约 | 常见的工程师合同类型 |
| SES | System Engineering Service | 一种工程师派遣形态 |
| 請負 | 外包/承包 | 按成果交付的合同形式 |
| 商流制限 | 合同层数限制 | 最多经过几层（贵社/自社） |
| 即日参画 | 立即到岗 | 面试合格后即可开始 |
| 募集人数 | 招聘数量 | — |
| 面談回数 | 面试轮数 | — |
| 勤務地 | 工作地点 | — |
| 在宅勤務 | 远程办公 | — |
| フルリモート | 完全远程 | — |
| 和暦 | 日本年号 | 令和/平成/昭和 |
| 外国籍：可 | 接受外籍 | 意指"不排斥外国人，但需日语能力" |
| 案件全文 | 原始文本 | 保留每条案件的完整原文 |

---

*文档版本: v1.0 | 最后更新: 2026-07-06*
*项目仓库: https://github.com/winds198912121/SAP-navi-SEO*
