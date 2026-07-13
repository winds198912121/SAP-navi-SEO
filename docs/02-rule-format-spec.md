# 02 — 规则格式规范 (Rule Format Specification)

> **文档版本**: v1.0  
> **更新日期**: 2025-06-28  
> **状态**: 已批准

## 1. 概述

本文档定义了日本招聘案件提取系统的规则格式。规则是系统从"LLM 依赖"过渡到"纯规则驱动"的核心资产。每条规则定义了如何从特定格式的文档中提取特定字段的值。

规则分 4 个层级：

```
Level 1 — 通用规则 (Global): 跨格式、跨字段的通用转换规则
Level 2 — 格式规则 (Format):  针对特定文档模板/格式的结构规则
Level 3 — 字段规则 (Field):   针对特定字段的匹配模式集合
Level 4 — 字典规则 (Dict):    同义词映射、标准化规则
```

---

## 2. 规则结构定义

### 2.1 顶层格式（JSON）

每条规则是一个 JSON 对象，存放于规则库中：

```json
{
  "ruleId": "field_skill_001",
  "version": 2,
  "field": "skill_requirement",
  "formatType": ["template_a", "free_form"],
  "priority": 90,
  "enabled": true,
  "tags": ["production", "auto_generated"],
  "description": "キーワード「スキル」に続く内容を抽出",

  "patterns": [
    {
      "type": "regex",
      "value": "(?:スキル|必要スキル|求めるスキル|必須スキル)[：:]([^\\n]+(?:\\n(?!\\n|【|■|●|・|募集|案件|単価|期間|場所|備考)[^\\n]*)*)",
      "flags": ["MULTILINE"],
      "confidence": 0.92
    }
  ],

  "postProcess": {
    "split": ["、", "・", "/", "\\s+"],
    "trim": true,
    "filterEmpty": true,
    "deduplicate": true,
    "mapToCanonical": true
  },

  "validation": {
    "required": true,
    "minLength": 1,
    "minItems": 1,
    "mustContainPattern": "(?:Java|Python|JavaScript|AWS|Azure|SQL|...)"
  },

  "metadata": {
    "createdBy": "learner_v2",
    "createdAt": "2025-06-01T10:30:00Z",
    "updatedAt": "2025-06-15T14:22:00Z",
    "hitCount": 45,
    "accuracy": 0.97,
    "sourceTemplate": null,
    "sampleCount": 23
  }
}
```

### 2.2 字段说明

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `ruleId` | string | ✓ | 全局唯一规则 ID。格式: `{field}_{type}_{NNN}` |
| `version` | integer | | 规则版本号，递增 |
| `field` | string | ✓ | 此规则关联的目标字段名 |
| `formatType` | string[] | ✓ | 适用的格式类型列表。`["*"]` 表示通用 |
| `priority` | integer | | 优先级 0-100，越高越优先 |
| `enabled` | boolean | | 是否启用 |
| `tags` | string[] | | 标签，用于分类和搜索 |
| `description` | string | | 规则说明 |
| `patterns` | Pattern[] | ✓ | 匹配模式数组（详见下文） |
| `postProcess` | object | | 后处理规则 |
| `validation` | object | | 验证规则 |
| `metadata` | object | | 元数据 |

---

## 3. 模式类型 (Pattern Types)

### 3.1 `regex` — 正则表达式模式

最常用的模式类型，通过正则表达式从文本中提取字段值。

```json
{
  "type": "regex",
  "value": "(?:案件名|件名)[：:]([^\\n]+)",
  "flags": ["MULTILINE", "DOTALL"],
  "confidence": 0.90,
  "weight": 1.0
}
```

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `value` | string | ✓ | 正则表达式。捕获组 `()` 提取目标值。 |
| `flags` | string[] | | 正则标志: `MULTILINE`, `DOTALL`, `IGNORECASE`, `UNICODE` |
| `confidence` | number | | 此模式的置信度 (0.0-1.0) |
| `weight` | number | | 此模式在组合中的权重 |

**常见日语模式示例**:

```
# 案件名
(?:案件名|件名|タイトル|案件タイトル)[：:]([^\n]+)

# 単価 — 幅あり
単価[：:]\s*(?:月額|日額)?\s*(\d+[万]?)\s*[〜~\-]\s*(\d+[万]?)\s*(?:円|万円)?(?:\/(?:月|日|時))?

# 単価 — 固定
単価[：:]\s*(?:月額|日額)?\s*(\d+[万]?)\s*(?:円|万円)?(?:\/(?:月|日|時))?

# 期間
(?:期間|契約期間|作業期間)[：:]\s*(\d{4})[年\/\-](\d{1,2})[月\/\-](\d{1,2})?\s*[〜~\-]\s*(\d{4})[年\/\-](\d{1,2})[月\/\-](\d{1,2})?

# スキル（複数行対応）
(?:スキル|必要スキル|求めるスキル|必須スキル)[：:]([\s\S]+?)(?=\n(?:【|■|●|・|備考|案件|単価|期間|場所))
```

### 3.2 `position` — 位置模式

基于文档结构位置来定位字段值。

```json
{
  "type": "position",
  "section": "募集要件",
  "lineOffset": 2,
  "direction": "below",
  "confidence": 0.85,
  "stopPattern": "^【|^■|^●|^$"
}
```

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `key` | string | | 作为锚点的关键词 |
| `section` | string | | 所在段落/章节标题 |
| `lineOffset` | integer | | 从锚点偏移的行数 |
| `direction` | string | | 方向: `below`, `above`, `same_line` |
| `relativeTo` | string | | 相对位置基准: `key` 或 `section_start` |
| `stopPattern` | string | | 停止匹配的模式 |
| `spanLines` | integer | | 向下取多少行内容 |
| `tableAnchor` | object | | 表格内的位置锚点 |

**表格位置示例**:

```json
{
  "type": "position",
  "tableAnchor": {
    "rowKeyword": "単価",
    "colKeyword": "金額",
    "offset": [0, 1]
  },
  "confidence": 0.90
}
```

### 3.3 `xpath` / `css` — HTML/XML 路径模式

针对 HTML 格式的邮件和网页。

```json
{
  "type": "xpath",
  "value": "/html/body/table[2]/tr[3]/td[2]",
  "namespace": null,
  "confidence": 0.95
}
```

```json
{
  "type": "css",
  "value": "table.recruit-info tr:nth-child(3) td.value",
  "confidence": 0.90
}
```

### 3.4 `keyword` — 关键词字典模式

基于关键词字典的模糊匹配。

```json
{
  "type": "keyword",
  "dictionary": "skill_dict",
  "scope": "section",
  "sectionKeyword": ["スキル", "要件", "求める人材"],
  "matchStrategy": "overlap",
  "minScore": 0.6,
  "confidence": 0.80
}
```

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `dictionary` | string | ✓ | 使用的字典名称 |
| `scope` | string | | 搜索范围: `full_text`, `section`, `paragraph` |
| `sectionKeyword` | string[] | | 限定从包含这些关键词的段落搜索 |
| `matchStrategy` | string | | `exact`(完全匹配), `overlap`(部分匹配), `fuzzy`(模糊) |
| `minScore` | number | | 最低匹配分数 |

### 3.5 `layout` — 布局/排版模式

基于文本排版特征（字体大小、粗体、颜色、对齐方式）的提取。适用于 PDF/Word 等保留排版信息的格式。

```json
{
  "type": "layout",
  "features": {
    "fontSize": { "min": 12, "max": 18 },
    "bold": true,
    "color": null
  },
  "relation": "follows_keyword",
  "keyword": "案件概要",
  "confidence": 0.85
}
```

### 3.6 `ml` — 轻量模型模式

当规则复杂度超出正则/位置表达能力时，使用轻量 ML 模型。通常在 Phase 2 后期引入。

```json
{
  "type": "ml",
  "modelName": "skill_ner_v1",
  "modelPath": "models/skill_ner_v1.onnx",
  "inputFeatures": ["char_ngram", "pos_tags", "section_context"],
  "minConfidence": 0.75,
  "confidence": 0.88
}
```

---

## 4. 格式类型定义 (Format Types)

格式类型（`formatType`）用于将文档模板与适用的规则关联：

```json
{
  "formatTypes": {
    "template_a": {
      "description": "株式会社A 標準案件概要書フォーマット",
      "patterns": [
        {"type": "header_marker", "value": "【案件概要書】"},
        {"type": "table_structure", "rows": 12, "cols": 2},
        {"type": "keyword_present", "value": "株式会社A"}
      ],
      "sampleCount": 45,
      "accuracy": 0.98
    },
    "template_b": {
      "description": "B社 メール配信フォーマット",
      "patterns": [
        {"type": "header_marker", "value": "★案件情報★"},
        {"type": "line_count", "min": 30, "max": 80}
      ],
      "sampleCount": 32,
      "accuracy": 0.95
    },
    "free_form": {
      "description": "自由形式（特定テンプレートに属さない文書）",
      "patterns": [],
      "sampleCount": 120,
      "accuracy": 0.82
    }
  }
}
```

### 格式识别流程

```
1. 提取文档的结构特征（头部标记、表格结构、行数、关键词集合）
2. 与 formatTypes 中的特征做匹配
3. 取匹配度最高的格式类型
4. 若匹配度低于阈值 (0.6)，归类为 "free_form"
5. 加载对应格式类型 + 字段的规则集
```

---

## 5. 后处理规则 (PostProcess)

### 5.1 支持的后处理操作

| 操作 | 参数 | 说明 |
|---|---|---|
| `split` | string[] | 按分隔符分割字符串为数组 |
| `trim` | boolean | 去除前后空白 |
| `filterEmpty` | boolean | 过滤空字符串 |
| `deduplicate` | boolean | 去重 |
| `mapToCanonical` | boolean | 使用字典映射为标准名 |
| `normalizeDate` | string | 日期归一化格式 |
| `extractNumbers` | boolean | 从字符串中提取数字 |
| `replace` | [from, to][] | 字符串替换 |
| `template` | string | 模板渲染（用提取值填充模板） |

### 5.2 示例

```json
{
  "postProcess": {
    "steps": [
      {"operation": "trim"},
      {"operation": "split", "delimiters": ["、", "・", "/"]},
      {"operation": "filterEmpty"},
      {"operation": "mapToCanonical", "dictionary": "skill_dict"},
      {"operation": "deduplicate"}
    ]
  }
}
```

---

## 6. 规则验证 (Validation)

每条规则可附带验证规则，用于校验提取结果的合理性：

```json
{
  "validation": {
    "rules": [
      {"type": "notEmpty"},
      {"type": "minLength", "value": 2},
      {"type": "pattern", "value": "^[\\u4e00-\\u9fff\\w\\s]+$"},
      {"type": "reference", "field": "rate.max", "comparison": "gte"}
    ],
    "onFailure": "discard",
    "fallbackToNextPattern": true
  }
}
```

**验证类型**:

| 类型 | 参数 | 说明 |
|---|---|---|
| `notEmpty` | — | 值不能为空 |
| `minLength` | value | 最小长度 |
| `maxLength` | value | 最大长度 |
| `pattern` | value | 必须匹配的正则 |
| `notPattern` | value | 不得匹配的正则 |
| `type` | typeName | 值类型检查 |
| `range` | min, max | 数值范围 |
| `enum` | values | 枚举值 |
| `reference` | field, comparison | 与其他字段交叉验证 |
| `dateRange` | min, max | 日期范围 |

---

## 7. 规则生命周期

```
起草 (Draft) ──→ 测试 (Testing) ──→ 已启用 (Active) ──→ 已废弃 (Deprecated) ──→ 已删除 (Deleted)
                      │                    │                        │
                      ↓                    ↓                        ↓
                  测试失败              准确率下降                到期清理
                   → 返写 Draft          → 降级 Testing            → 归档
```

| 状态 | 说明 |
|---|---|
| `draft` | 新建或从 testing 退回，未上线 |
| `testing` | 在 shadow mode 运行，计算准确率 |
| `active` | 正式启用参与提取 |
| `deprecated` | 标记为废弃（准确率 < 阈值 或 被更优规则替代） |
| `deleted` | 物理删除前保留 90 天 |

### 自动降级条件

- 连续 30 次匹配中准确率 < 80% → 从 `active` 降级到 `testing`
- 连续 90 天未命中 → 从 `active` 降级到 `deprecated`
- `deprecated` 超过 180 天 → 自动删除

---

## 8. 规则库存储结构

### SQLite 表结构

```sql
CREATE TABLE rules (
    rule_id         TEXT PRIMARY KEY,
    version         INTEGER NOT NULL DEFAULT 1,
    field           TEXT NOT NULL,
    format_type     TEXT NOT NULL,       -- JSON array string
    priority        INTEGER DEFAULT 50,
    enabled         INTEGER DEFAULT 1,
    status          TEXT DEFAULT 'draft', -- draft|testing|active|deprecated
    tags            TEXT,                 -- JSON array string
    description     TEXT,
    patterns        TEXT NOT NULL,        -- JSON array
    post_process    TEXT,                 -- JSON object
    validation      TEXT,                 -- JSON object
    created_by      TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    hit_count       INTEGER DEFAULT 0,
    accuracy        REAL DEFAULT 0.0,
    sample_count    INTEGER DEFAULT 0,
    superseded_by   TEXT                  -- 被哪条规则替代
);

CREATE INDEX idx_rules_field ON rules(field);
CREATE INDEX idx_rules_format ON rules(format_type);
CREATE INDEX idx_rules_status ON rules(status);

CREATE TABLE format_templates (
    template_id     TEXT PRIMARY KEY,
    description     TEXT,
    patterns        TEXT NOT NULL,        -- JSON array of identification patterns
    sample_count    INTEGER DEFAULT 0,
    accuracy        REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL
);

CREATE TABLE dictionaries (
    dict_name       TEXT PRIMARY KEY,
    dict_type       TEXT NOT NULL,        -- synonym|canonical|category
    entries         TEXT NOT NULL,        -- JSON array
    version         INTEGER DEFAULT 1,
    updated_at      TEXT NOT NULL
);

CREATE TABLE rule_hit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id         TEXT NOT NULL,
    document_id     TEXT,
    matched         INTEGER DEFAULT 1,
    confidence      REAL,
    extracted_value TEXT,
    feedback        TEXT,                 -- correct|incorrect|partial
    created_at      TEXT DEFAULT (datetime('now'))
);
```

---

## 9. 规则编写最佳实践

### 9.1 正则编写原则

1. **捕获组精确**: 只对需要的值部分使用 `()`
2. **避免贪婪匹配**: 使用 `[^\\n]+` 而非 `.+` 防止跨行
3. **应对表記揺れ**: 用 `(?:)` 列出所有可能写法
4. **结束边界清晰**: 明确指定结束条件（换行、下一个标记、关键词等）
5. **日语注意点**:
   - 全角/半角 `：:` `．.` `（(`
   - 句読点での改行が多い
   - ルビ（振り仮名）が本文中に含まれる場合がある

### 9.2 位置规则原则

1. **相对位置优于绝对位置**: 格式变化时更鲁棒
2. **多锚点备用**: 主锚点缺失时使用备用锚点
3. **明确边界条件**: 指定 stopPattern 防止越界

### 9.3 规则组合原则

1. 同一字段的多条规则按优先级排序
2. 高置信度规则 > 低置信度规则
3. 特定格式规则 > 通用规则（即使通用规则优先级更高）
4. 规则之间可以互补（如正则提取＋字典验证）

---

## 10. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2025-06-28 | 初版制定 |
