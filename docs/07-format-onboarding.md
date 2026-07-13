# 07 — 新格式适配流程 (New Format Onboarding)

> **文档版本**: v1.0
> **更新日期**: 2025-06-28

## 1. 概述

当遇到系统尚未支持的文档格式时，按照本文档的流程进行适配。新格式适配的目标是：**初始通过 LLM 提取 → 快速生成规则 → 后续无需 LLM 秒级处理**。

### 1.1 什么是"新格式"

| 判定条件 | 说明 |
|---|---|
| 格式识别模块返回 `free_form` 或 `unknown` | 未注册的模板 |
| 规则覆盖率 < 30%（大部分字段走 LLM） | 格式已知但规则不足 |
| 相同来源/样式文档 ≥ 3 份 | 值得注册为新格式 |

---

## 2. 适配流程概览

```
Step 1: 样本收集 ──────── 收集 3-5 份同格式文档
    │
Step 2: 格式特征提取 ──── 分析文档结构和排版特征
    │
Step 3: 模板注册 ──────── 注册新的 format type
    │
Step 4: LLM 提取验证 ──── 用 LLM 提取这些文档，人工修正
    │
Step 5: 规则自动生成 ──── 运行规则学习引擎
    │
Step 6: 规则验证 ──────── 回测验证，精确率达标后入库
    │
Step 7: 监控 ──────────── 上线后持续监控质量
```

---

## 3. Step 1: 样本收集

### 3.1 收集要求

| 项目 | 要求 |
|---|---|
| 最小样本数 | ≥ 3 份同格式文档 |
| 推荐样本数 | 5-10 份（规则质量更稳定） |
| 样本多样性 | 尽可能覆盖不同案件类型（金融、公共、SIer等） |
| 标注 | 人工提取所有字段的标准答案 |

### 3.2 标注格式

```json
{
  "document_id": "fmt_X_sample_001",
  "filename": "案件概要書_20250601_A社.pdf",
  "format_type": ">> ここに新しいフォーマット名 <<",
  "ground_truth": {
    "project_name": "某証券会社向け基幹システム開発",
    "skill_requirement": ["Java", "Spring Boot", "AWS"],
    "location": {"city": "東京都品川区", "station": "品川駅"},
    "rate": {"min": 70, "max": 80, "unit": "monthly"},
    "period": {"start_date": "2025-07-01", "end_date": "2026-03-31"},
    "headcount": 2,
    "industry": "金融",
    "trade_flow": {"contract_type": "jun_inin", "layers": 2},
    "japanese_level": {"level": "business"}
  }
}
```

### 3.3 存储位置

```
data/samples/{format_name}/
├── raw/              # 原始文档
│   ├── sample_001.pdf
│   ├── sample_002.pdf
│   └── sample_003.pdf
├── annotations/       # 标注（JSONL）
│   └── annotations.jsonl
└── README.md          # 格式说明
```

---

## 4. Step 2: 格式特征提取

分析新格式文档的结构特征，用于后续自动识别。

### 4.1 特征检查清单

```
□ 文档类型:            PDF / Word / Excel / HTML / 邮件 / 其他
□ 页面布局:            单栏 / 双栏 / 表格为主 / 自由排版
□ 识别标记:
   - 标题头:           例「【案件概要書】」「★案件情報★」
   - 公司标志:         有无 / 位置
   - 页眉/页脚:        内容
□ 章节结构:
   - 章节标题格式:     【】/ ■ / ● / 数字付き
   - 固定章节:         案件概要 / 募集要項 / 応募資格 / 単価条件
□ 表格结构:
   - 行数:             固定 or 可変
   - 列数:             key:value / 多列
   - ヘッダー有無:     あり / なし
□ 字段布局:
   - 齊一的前缀:       案件名：、スキル：、場所：
   - 固定位置:         第 N 行第 M 列
   - 混合排版:         自由文の中に埋め込み
```

### 4.2 特征记录

```json
{
  "format_name": "abc_corporation_template_v1",
  "source": "ABC株式会社 案件案内メール",
  "detection_patterns": [
    {"type": "header_marker", "value": "【ABC社 案件案内】", "weight": 0.4},
    {"type": "keyword_present", "value": "ABC株式会社", "weight": 0.2},
    {"type": "table_structure", "rows": 10, "cols": 2, "weight": 0.3},
    {"type": "line_count", "min": 25, "max": 60, "weight": 0.1}
  ],
  "field_positions": {
    "project_name": {"section": "案件概要", "lineOffset": 0, "direction": "below"},
    "skill_requirement": {"section": "応募資格", "lineOffset": 1, "spanLines": 3},
    "rate": {"tableAnchor": {"rowKeyword": "単価", "colKeyword": "詳細"}},
    "location": {"keyword": "勤務地", "direction": "same_line", "delimiter": "："}
  },
  "notes": "メール本文形式。各案件が区切り線で区切られている。"
}
```

---

## 5. Step 3: 模板注册

### 5.1 CLI 注册

```bash
# 注册新格式（交互式）
python -m src.cli format register

# 注册新格式（直接指定）
python -m src.cli format register \
  --name abc_corporation_template_v1 \
  --description "ABC株式会社 案件案内メール" \
  --patterns-json '[
    {"type": "header_marker", "value": "【ABC社 案件案内】", "weight": 0.4},
    {"type": "keyword_present", "value": "ABC株式会社", "weight": 0.2}
  ]'
```

### 5.2 API 注册

```bash
curl -X POST http://localhost:8000/formats \
  -H "Content-Type: application/json" \
  -d '{
    "name": "abc_corporation_template_v1",
    "description": "ABC株式会社 案件案内メール",
    "patterns": [
      {"type": "header_marker", "value": "【ABC社 案件案内】", "weight": 0.4},
      {"type": "keyword_present", "value": "ABC株式会社", "weight": 0.2}
    ],
    "samples": ["sample_001.eml", "sample_002.eml"]
  }'
```

### 5.3 注册后的自动处理

注册完成后，系统自动执行：

1. ✅ 格式类型加入识别引擎（后续文档可自动分类）
2. ✅ 已有样本文档使用 LLM 模式提取
3. ✅ 提取结果供规则学习引擎使用
4. 🔄 3-5 份样本满足后自动触发规则学习

---

## 6. Step 4: LLM 提取验证

系统自动使用标准 LLM 提取管线处理已注册格式的样本文档。

### 6.1 提取后处理

```bash
# 查看该格式的 LLM 提取结果
python -m src.cli format status --name abc_corporation_template_v1

# 输出:
# Format: abc_corporation_template_v1
# Status: ONBOARDING
# Samples: 3 / 5  (min 3 required)
# LLM extraction: 3/3 completed
# Manual review: 0/3 completed ← 需要人工確認
# Rules generated: 0
```

### 6.2 人工审查

```bash
# 交互式审查该格式的提取结果
python -m src.cli format review --name abc_corporation_template_v1

# 逐个字段确认:
# Document 1/3: sample_001.eml
# ┌──────────────────────────────────────┐
# │ project_name:                        │
# │   Extracted: 某証券会社向け基幹システム  │
# │   [✓] Correct  [ ] Edit: __________ │
# ├──────────────────────────────────────┤
# │ skill_requirement:                   │
# │   Extracted: Java, Spring, AWS       │
# │   [✓] Correct  [ ] Edit: __________ │
# └──────────────────────────────────────┘
```

---

## 7. Step 5: 规则自动生成

### 7.1 触发规则学习

```bash
# 手动触发
python -m src.cli rule learn \
  --format-type abc_corporation_template_v1 \
  --all-fields

# 或按字段触发
python -m src.cli rule learn \
  --format-type abc_corporation_template_v1 \
  --fields project_name,skill_requirement,rate
```

### 7.2 学习过程输出

```
学習開始: abc_corporation_template_v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

フィールド: project_name
  パターン発見: 3 件の候補から 1 件のルールを生成
  ルール: regex「(?:案件名|件名)[：:]([^\n]+)」
  精度: 1.0 (3/3)
  ステータス: active

フィールド: skill_requirement
  パターン発見: 5 件の候補から 2 件のルールを生成
  ルール1: regex「(?:スキル|必須スキル)[：:]([^\n]+)」
  精度: 1.0 (3/3)
  ルール2: position (section: 募集要件, lineOffset: 2)
  精度: 0.67 (2/3)
  ステータス: active / testing

フィールド: rate
  パターン発見: 2 件の候補から 1 件のルールを生成
  ルール: position (tableAnchor: {row: 単価, col: 詳細})
  精度: 1.0 (3/3)
  ステータス: active

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
学習完了: 4 件のルールを生成、3 件を active、1 件を testing
```

### 7.3 学习结果的规则示例

```json
{
  "ruleId": "field_skill_fmt_abc_001",
  "field": "skill_requirement",
  "formatType": ["abc_corporation_template_v1"],
  "priority": 85,
  "patterns": [
    {
      "type": "regex",
      "value": "(?:スキル|必須スキル|求めるスキル)[：:]([^\\n]+)",
      "confidence": 0.95
    }
  ],
  "postProcess": {
    "split": ["、", "・", "/"],
    "trim": true,
    "filterEmpty": true,
    "deduplicate": true
  },
  "metadata": {
    "createdBy": "learner_auto",
    "sampleCount": 3,
    "accuracy": 1.0
  }
}
```

---

## 8. Step 6: 规则验证

### 8.1 验证流程

```
1. 准备验证集: 该格式的标注数据（预留 20% 作为验证集）
2. 规则回测: 在验证集上运行规则
3. 计算指标:
   - 精确率 = 正确提取数 / 总提取数
   - 召回率 = 正确提取数 / 总应提取数
   - 覆盖率 = 有规则覆盖的字段数 / 总字段数
4. 判定:
   - 全部字段精确率 ≥ 0.95 → 自动入库（active）
   - 主要字段精确率 ≥ 0.90 → 入库（testing 状态）
   - 主要字段精确率 < 0.90 → 需要优化后重新学习
```

### 8.2 手动优化

如果自动生成的规则质量不达标，可以手动优化：

```bash
# 查看规则建议
python -m src.cli rule suggest --field skill_requirement --format-type abc_corporation_template_v1

# 手动创建规则
python -m src.cli rule create \
  --field skill_requirement \
  --format-type abc_corporation_template_v1 \
  --pattern-type regex \
  --pattern-value "(?:必須スキル|求めるスキル)[：:]([^\\n]+)" \
  --split "、" \
  --priority 90
```

---

## 9. Step 7: 监控

### 9.1 上线后监控

```bash
# 查看格式运行统计
python -m src.cli format stats --name abc_corporation_template_v1

# 输出:
# Format: abc_corporation_template_v1
# ┌─────────────────────┬────────┐
# │ Documents processed │ 47     │
# │ Rule coverage       │ 87.5%  │
# │ Average confidence  │ 0.93   │
# │ LLM fallback rate   │ 12.5%  │
# │ Rule accuracy       │ 0.96   │
# └─────────────────────┴────────┘
```

### 9.2 持续改进

```
規則の精度が低下した場合:
  原因分析:
    - フォーマット変更? → 新フォーマットとして再登録
    - プロンプト不足?   → LLM抽出結果を確認
    - 辞書不足?         → スキル辞書等を更新

改善:
    - 追加サンプルで再学習
    - 手動でルール修正
    - 新パターン追加
```

### 9.3 格式退役

格式文档不再使用时：

```bash
python -m src.cli format archive --name abc_corporation_template_v1
# 存档后：规则保留但不活跃，格式不参与识别匹配
```

---

## 10. 检查清单：新格式适配

```markdown
## 新格式适配检查清单

### 初期
- [ ] 收集 ≥ 3 份样本文档
- [ ] 完成所有字段的人工标注
- [ ] 分析文档结构特征

### 注册
- [ ] 注册新格式类型
- [ ] 验证格式识别能正确匹配样本

### 提取
- [ ] LLM 提取所有样本
- [ ] 人工确认提取结果
- [ ] 修正任何错误

### 规则
- [ ] 自动生成规则
- [ ] 验证规则精确率 ≥ 0.95
- [ ] 低精度规则人工优化
- [ ] 规则入库（active / testing）

### 验证
- [ ] 用预留验证集回测
- [ ] 整体精确率 ≥ 0.90
- [ ] 运行回归测试，不影响其他格式

### 生产
- [ ] 新规则在生产环境运行
- [ ] Shadow Mode 监控 7 天
- [ ] 指标正常后完全切换
```

---

## 11. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2025-06-28 | 初版 |
