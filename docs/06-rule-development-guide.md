# 06 — 规则开发 & 维护指南

> **文档版本**: v1.0
> **更新日期**: 2025-06-28

## 1. 概述

本指南面向**规则开发者**——即需要编写、测试和维护提取规则的人员。规则是系统的核心资产，高质量的规则意味着高精度提取和低 LLM 成本。

### 1.1 规则开发流程

```
需求分析 → 样本收集 → 模式设计 → 规则编写 → 测试验证 → 部署上线 → 监控维护
```

### 1.2 所需技能

- 正则表达式（Python 风格，含 `regex` 模块扩展）
- 日语阅读能力（N2 以上推奨）
- 基本的 JSON / Markdown 读写
- 了解日本 IT 招聘案件的结构和常用术语

---

## 2. 规则开发环境

### 2.1 本地测试工具

```bash
# 测试单条规则
python -m src.cli rule test \
  --rule-id my_new_rule \
  --input sample.txt

# 可视化规则匹配
python -m src.cli rule debug \
  --rule-id field_skill_001 \
  --input 案件概要書.pdf \
  --show-context

# 批量测试规则（用标注数据集）
python -m src.cli rule evaluate \
  --rule-id field_skill_001 \
  --test-set data/test/skill_requirement_test.jsonl
```

### 2.2 规则沙箱模式

新规则在沙箱模式下不会影响生产流程：

```bash
# 沙箱模式运行
python -m src.cli extract --input sample.pdf --sandbox

# 沙箱模式下：
# - 使用生产规则 + 新规则同时执行
# - 新规则结果单独记录，不参与最终输出
# - 输出对比报告
```

---

## 3. 规则开发详细指南

### 3.1 理解字段特征

开发规则前，先分析目标字段在文档中的表现特征：

| 特征 | 应选择的模式类型 |
|---|---|
| 固定的关键词前缀（如「案件名：xxx」） | `regex` |
| 固定位置（某格式的第 N 行） | `position` |
| HTML 表格中的固定单元格 | `xpath` / `css` |
| 通过词汇列表匹配（如スキル名） | `keyword` |
| 基于排版特征（粗体、大字号标题） | `layout` |

### 3.2 正则表达式最佳实践

#### 3.2.1 一般原则

```python
# ✅ 好的做法：捕获组精确、结束条件明确
r"(?:案件名|件名|タイトル)[：:]\s*([^\n]+)"

# ❌ 不好的做法：过度贪婪、缺少边界
r"案件名[：:](.+)"   # .+ 会跨行匹配到不需要的内容

# ✅ 好的做法：表記揺れを考慮
r"(?:スキル|必須スキル|求めるスキル|必要スキル)[：:]([^\n]+)"

# ❌ 不好的做法：表記揺れ未考慮
r"スキル[：:]([^\n]+)"  # ドキュメントが「必須スキル」の場合にマッチしない
```

#### 3.2.2 日语特定模式

```python
# 日期: 多种日语格式
# 令和N年 → 2019+N 年
r"(?:令和|平成|昭和)(\d+)年(\d{1,2})月(\d{1,2})日"

# 単価: 範囲あり / 固定 / 月額/日額/時給
r"単価[：:]\s*(?:月額|日額)?\s*(\d+(?:\.\d+)?)[万]?\s*[〜~\-]\s*(\d+(?:\.\d+)?)[万]?\s*(?:円|万円)?(?:\s*/\s*(?:月|日|時))?"

# スキル: 複数行対応（区切り文字まで取る）
r"(?:スキル|求めるスキル|必須スキル)[：:]\s*([\s\S]+?)(?=\n(?:【|■|●|・|募集要項|案件概要|備考|単価|期間|場所))"

# 数量: "万円" → 数值
r"(\d+(?:\.\d+)?)(?:万|千)"
```

#### 3.2.3 性能与安全

```python
# ⚠️ 危险：可能导致 Catastrophic Backtracking
r"(.*,)+skill"    # 嵌套量词

# ✅ 安全：使用原子组或明确范围
r"(?>[^,]+)(?:,skill)"
# 或：明确指定匹配范围
r"^.{0,100}skill"

# ⚠️ 危险：大文本上的 .* 过多
r"案件概要(.*)備考(.*)単価"  # 在大文本上极慢

# ✅ 安全：限定范围
r"案件概要(.{0,200})備考(.{0,200})単価"

# 避免在长文本上使用过多回溯的正则
# 使用 re 模块的 timeout 保护（Python regex 库支持）
import regex
result = regex.search(pattern, text, timeout=0.1)  # 100ms 超时
```

### 3.3 位置规则最佳实践

位置规则基于文档的结构位置，适用于格式固定的模板文档。

```json
{
  "type": "position",
  "section": "案件概要",      // 先定位到章节
  "lineOffset": 2,           // 章节标题下第 2 行
  "direction": "below",
  "spanLines": 3,            // 取 3 行内容
  "stopPattern": "^$|^【|^■",  // 碰到空行或标记停止
  "confidence": 0.85
}
```

**开发步骤**:

1. 找到锚点（关键词或章节标题）
2. 确认字段值相对锚点的位置（行偏移、同列等）
3. 设置合理的 spanLines（取值可能跨越多行）
4. 设置 stopPattern（防止越界匹配）
5. 添加 fallback（锚点不存在时备用策略）

### 3.4 关键词字典最佳实践

关键词字典是实现高精度スキル抽出的关键。

#### 3.4.1 字典结构

```json
{
  "dict_name": "skill_dict",
  "version": 3,
  "entries": [
    {
      "canonical": "Java",
      "variants": ["JAVA", "java", "Java11", "Java17", "Java8", "j2se"],
      "category": "programming_language",
      "weight": 1.0
    },
    {
      "canonical": "Spring Boot",
      "variants": ["spring boot", "SpringBoot", "spring-boot", "Spring Boot2"],
      "category": "framework",
      "weight": 1.0
    }
  ]
}
```

#### 3.4.2 开发指南

1. **从高频技能开始**: 收集 100 份案件的技能数据，统计高频技能
2. **覆盖表記揺れ**: java, JAVA, Java17, Java8, J2SE → Java
3. **分層管理**:
   - プログラミング言語: Java, Python, C#, TypeScript...
   - フレームワーク: Spring Boot, Django, React...
   - インフラ: AWS, Azure, Docker, Kubernetes...
   - データベース: Oracle, PostgreSQL, MySQL...
   - ツール: Git, Jenkins, Jira...
4. **定期更新**: 每月从新的标注数据中提取未收录的技能名
5. **冲突处理**: 短名（JS, TS, AI）需要上下文消歧

---

## 4. 测试与验证

### 4.1 测试数据集

每条规则应在测试数据集上验证。测试数据集结构：

```jsonl
# data/test/skill_requirement_test.jsonl
{"document": "【必須スキル】Java, Spring, PostgreSQL", "expected": ["Java", "Spring", "PostgreSQL"]}
{"document": "【求めるスキル】\n・Python開発経験\n・AWSでの設計経験", "expected": ["Python", "AWS"]}
{"document": "【スキル】C# / ASP.NET / SQL Server", "expected": ["C#", "ASP.NET", "SQL Server"]}
```

### 4.2 评估指标

```bash
# 运行规则评估
python -m src.cli rule evaluate \
  --rule-id field_skill_003 \
  --test-set data/test/skill_requirement_test.jsonl

# 输出:
# Precision: 0.97
# Recall: 0.94
# F1 Score: 0.95
# Accuracy: 0.96
```

| 指标 | 计算 | 目标值 |
|---|---|---|
| Precision | TP / (TP + FP) | ≥ 0.95 |
| Recall | TP / (TP + FN) | ≥ 0.90 |
| F1 | 2 × P × R / (P + R) | ≥ 0.93 |

### 4.3 回归测试

每次规则变更后，运行完整回归测试：

```bash
python -m src.cli rule regression --test-dir data/test/
```

自动检测：
- 新规则引入的精度下降
- 旧规则被意外影响
- 覆盖率变化

---

## 5. 规则维护

### 5.1 日常维护任务

| 頻度 | タスク | 说明 |
|---|---|---|
| 每天 | 检查低置信度结果 | 查看置信度 < 0.7 的提取 |
| 每周 | 分析新标注数据 | 从人工修正中发现新模式 |
| 每月 | 字典更新 | 添加新技能、公司名等 |
| 每季 | 规则健康度检查 | 清理低使用率/低精度规则 |
| 每半年 | 全量回归测试 | 确保规则库整体质量 |

### 5.2 规则优先级管理

```
高优先级 (90-100):  精确匹配特定格式的核心字段规则
中优先级 (50-89):   通用正则规则，置信度好
低优先级 (10-49):   覆盖边缘情况的规则，置信度较低
后备规则 (1-9):     精度不高但聊胜于无
```

### 5.3 规则退役条件

- 准确率持续低于 80%的超 30 次命中
- 被更高置信度的规则完全替代
- 90 天以上未命中
- 对应的格式类型已不再使用

---

## 6. 进阶主题

### 6.1 复合规则

对于复杂字段，组合多种模式类型：

```json
{
  "ruleId": "field_skill_complex_001",
  "field": "skill_requirement",
  "patterns": [
    {
      "type": "regex",
      "value": "(?:スキル|必須スキル)[：:]([^\\n]+)",
      "confidence": 0.85
    },
    {
      "type": "keyword",
      "dictionary": "skill_dict",
      "scope": "section",
      "sectionKeyword": ["要件", "求める人材", "応募資格"],
      "confidence": 0.75
    }
  ],
  "combineStrategy": "union",     // union: 合并去重; intersect: 交集; weighted: 加权
  "postProcess": {
    "deduplicate": true,
    "mapToCanonical": true
  }
}
```

### 6.2 条件规则

当特定条件满足时才执行的规则：

```json
{
  "ruleId": "field_rate_conditional_001",
  "field": "rate",
  "conditions": [
    {
      "field": "trade_flow.contract_type",
      "operator": "equals",
      "value": "jun_inin"
    }
  ],
  "patterns": [...]
}
```

### 6.3 规则链

一条规则的输出作为另一条规则的输入：

```json
{
  "ruleId": "chain_rate_unit_001",
  "field": "rate.unit",
  "chainsFrom": "field_rate_raw_001",
  "patterns": [
    {
      "type": "keyword",
      "dictionary": "rate_unit_dict",
      "scope": "matched_text",
      "confidence": 0.95
    }
  ]
}
```

---

## 7. 协作规范

### 7.1 命名规范

```
规则 ID: {field}_{type}_{NNN}
  field: 字段名 | type: 模式类型 | NNN: 3位数字序号

示例:
  field_skill_regex_001
  field_rate_position_002
  field_location_keyword_001
  format_template_a_001
```

### 7.2 代码审查清单

规则提交前检查：

- [ ] 正则表达式有明确的边界条件
- [ ] 处理了全角/半角表記揺れ
- [ ] 不会导致 Catastrophic Backtracking
- [ ] 有对应的测试数据
- [ ] 精确率和召回率达标
- [ ] 优先级设置合理
- [ ] 后处理步骤正确
- [ ] 不与其他活跃规则冲突

### 7.3 文档要求

每条规则应包含：
- 清晰的 description（说明做什么、适用场景）
- 至少一个匹配示例
- 已知的限制或不适用范围

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2025-06-28 | 初版 |
