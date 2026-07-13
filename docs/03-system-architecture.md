# 03 — 系统架构设计 (System Architecture Design)

> **文档版本**: v1.0
> **更新日期**: 2025-06-28
> **状态**: 已批准

## 1. 系统概述

JP Recruit Extractor 是一个面向日本 IT 招聘案件文档的智能数据提取系统。系统采用 **分层架构** 和 **管线模式**，支持从多种文档格式中提取结构化数据，并通过 AI 辅助 + 规则引擎逐步减少对 LLM 的依赖。

### 1.1 设计原则

| 原则 | 说明 |
|---|---|
| **渐进式自动化** | 先 LLM 保底再逐步规则化 |
| **容错设计** | 任何环节失败不中断全流程，降级策略明确 |
| **可观测性** | 每个环节输出指标，规则质量可量化 |
| **扩展性** | 新格式 + 新字段可插拔，无需修改核心代码 |
| **日语优先** | 所有文本处理环节以日语为前提优化 |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API 层 (FastAPI)                           │
│  POST /extract  │  POST /batch  │  GET /rules  │  PUT /feedback    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                       管线调度器 (Pipeline Orchestrator)              │
│  步骤编排  │  异常处理  │  重试逻辑  │  结果聚合                      │
└──┬──────────────────────────────────────────────────────────────────┘
   │
   ├── 1. ┌───────────────────────────────────────────────────────┐
   │      │  预处理层 (Preprocessing Layer)                        │
   │      │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
   │      │  │ PDF      │ │ Word     │ │ Excel    │ │ HTML    │ │
   │      │  │ Processor│ │ Processor│ │ Processor│ │ Parser  │ │
   │      │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
   │      │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
   │      │  │ Email    │ │ Image    │ │ Text Normalizer      │ │
   │      │  │ Parser   │ │ OCR      │ │ (全半角/機種依存/..) │ │
   │      │  └──────────┘ └──────────┘ └──────────────────────┘ │
   │      └───────────────────────────────────────────────────────┘
   │                    │
   ├── 2. ┌───────────────────────────────────────────────────────┐
   │      │  格式识别 & 路由 (Format Recognizer & Router)          │
   │      │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
   │      │  │ 模板匹配器    │ │ 字段规则查询  │ │ 置信度评估器  │ │
   │      │  └──────────────┘ └──────────────┘ └──────────────┘ │
   │      └───────────────────────────────────────────────────────┘
   │                    │
   ├── 3. ┌───────────────────────────────────────────────────────┐
   │      │  提取执行层 (Extraction Layer)                         │
   │      │  ┌──────────────────┐    ┌────────────────────────┐  │
   │      │  │ 规则引擎         │    │ LLM 引擎               │  │
   │      │  │ - 字段级匹配     │    │ - Prompt Template      │  │
   │      │  │ - 多模式组合     │    │ - Few-shot 注入        │  │
   │      │  │ - 后处理标准化   │    │ - JSON Schema 约束     │  │
   │      │  └──────────────────┘    └────────────────────────┘  │
   │      │         │                         │                  │
   │      │         └──────────┬──────────────┘                  │
   │      │                    ▼                                 │
   │      │            ┌──────────────────┐                      │
   │      │            │ 结果融合器       │                      │
   │      │            │ (Result Merger)  │                      │
   │      │            └──────────────────┘                      │
   │      └───────────────────────────────────────────────────────┘
   │                    │
   ├── 4. ┌───────────────────────────────────────────────────────┐
   │      │  后处理验证层 (Post-processing Layer)                  │
   │      │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
   │      │  │ 字段校验器    │ │ 值标准化器    │ │ 冲突检测器    │ │
   │      │  └──────────────┘ └──────────────┘ └──────────────┘ │
   │      └───────────────────────────────────────────────────────┘
   │                    │
   └── 5. ┌───────────────────────────────────────────────────────┐
          │  输出 & 反馈 (Output & Feedback)                      │
          │  结构化 JSON │ 提取日志  │ 低置信度フラグ             │
          └───────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详细设计

### 3.1 预处理层 (Preprocessing Layer)

#### 3.1.1 模块职责

- 接收原始文件，识别文件类型
- 提取文本并转化为统一格式（Markdown 结构化文本）
- 处理日语特有的文本规范化

#### 3.1.2 接口定义

```python
class DocumentPreprocessor(ABC):
    """文档预处理器基类"""

    SUPPORTED_FORMATS: ClassVar[set[str]] = set()

    @abstractmethod
    def process(self, file_path: str) -> PreprocessingResult:
        """
        处理文档并返回结构化文本。

        Args:
            file_path: 文件路径

        Returns:
            PreprocessingResult 包含:
            - raw_text: 提取的原始文本
            - structured_text: 保留排版结构的 Markdown 文本
            - metadata: 文档元数据（页数、表格位置、字体信息等）
            - pages: 按页分隔的文本列表（PDF等分页文档）
            - tables: 表格结构列表
        """
        ...

    def detect_encoding(self, file_path: str) -> str:
        """検出文字コード (Shift-JIS, EUC-JP, UTF-8 等)"""
        ...

class PreprocessingResult(BaseModel):
    raw_text: str
    structured_text: str
    metadata: dict[str, Any]
    pages: list[str] = []
    tables: list[TableStructure] = []
    error: str | None = None
```

#### 3.1.3 日语文本标准化

```python
class JapaneseTextNormalizer:
    """日语文本标准化处理流水线"""

    def normalize(self, text: str) -> str:
        """完整的标准化流程"""
        text = self._unify_encoding(text)       # EUC-JP/SJIS → UTF-8
        text = self._unify_width(text)          # 全角英数→半角、半角カナ→全角
        text = self._remove_ruby(text)          # ルビ除去
        text = self._normalize_kigou(text)      # 機種依存文字正規化
        text = self._normalize_punctuation(text) # 句読点統一
        text = self._optimize_line_breaks(text) # 日本語改行最適化
        text = self._normalize_whitespace(text) # 空白正規化
        return text.strip()
```

### 3.2 格式识别 & 路由 (Format Recognizer & Router)

#### 3.2.1 模块职责

- 识别文档所属的格式模板类型
- 逐字段检查规则库中是否有可用规则
- 决定每个字段使用规则模式 / LLM模式 / 混合模式

#### 3.2.2 流程

```
                     ┌──────────────┐
                     │ 格式化文本输入 │
                     └──────┬───────┘
                            ▼
              ┌─────────────────────────┐
              │ 提取文档结构特征          │
              │ - 头部标记               │
              │ - 表格结构               │
              │ - 行数 / 段落数          │
              │ - 关键词集合             │
              │ - 排版特征（PDF/Word）   │
              └──────────┬──────────────┘
                         ▼
              ┌─────────────────────────┐
              │ 格式模板匹配             │
              │ 对每个已知模板计算相似度   │
              └──────────┬──────────────┘
                         ▼
              ┌─────────────────────────┐
              │ 取最高分模板             │
              │ score > 0.8 → 确定格式   │
              │ score 0.5~0.8 → 模糊匹配 │
              │ score < 0.5 → free_form  │
              └──────────┬──────────────┘
                         ▼
              ┌─────────────────────────┐
              │ 逐字段路由决策           │
              │                         │
              │ for each field:         │
              │   查询 rule_repo        │
              │   if 规则置信度 > 0.9:   │
              │     → rule_only         │
              │   elif > 0.7:           │
              │     → hybrid            │
              │   else:                 │
              │     → llm_only          │
              └─────────────────────────┘
```

#### 3.2.3 模板匹配算法

```python
@dataclass
class FormatTemplate:
    template_id: str
    description: str
    patterns: list[IdentificationPattern]
    sample_count: int
    accuracy: float

class FormatRecognizer:
    def __init__(self, templates: list[FormatTemplate]):
        self.templates = templates

    def identify(self, text: str, metadata: dict) -> FormatMatch:
        """
        识别文档格式类型。

        使用 weighed scoring:
        - header_marker 匹配: +0.4
        - table_structure 匹配: +0.3
        - keyword_present 匹配: +0.2
        - line_count 在范围内: +0.1
        """
        scores = []
        for template in self.templates:
            score = 0.0
            for pattern in template.patterns:
                score += self._match_pattern(pattern, text, metadata)
            scores.append((template.template_id, score))

        best = max(scores, key=lambda x: x[1])

        return FormatMatch(
            format_type=best[0] if best[1] > 0.5 else "free_form",
            confidence=best[1],
            all_scores=dict(scores)
        )
```

### 3.3 规则引擎 (Rule Engine)

#### 3.3.1 模块职责

- 加载匹配的规则集
- 对每个字段执行规则匹配（尝试多种模式）
- 返回提取结果 + 置信度

#### 3.3.2 核心执行逻辑

```python
class RuleEngine:
    def __init__(self, repository: RuleRepository):
        self.repository = repository
        self.matchers: dict[str, PatternMatcher] = {
            "regex": RegexMatcher(),
            "position": PositionMatcher(),
            "xpath": XPathMatcher(),
            "keyword": KeywordMatcher(),
            "layout": LayoutMatcher(),
            "ml": MLMatcher(),
        }

    def extract_field(
        self,
        field: str,
        text: str,
        format_type: str,
        context: ExtractionContext
    ) -> FieldResult:
        """对单个字段进行规则提取"""

        # 1. 查询规则
        rules = self.repository.get_rules(field, format_type)

        if not rules:
            return FieldResult(field=field, value=None, confidence=0.0, source="no_rule")

        # 2. 按优先级排序
        rules.sort(key=lambda r: r.priority, reverse=True)

        candidates = []
        for rule in rules:
            if not rule.enabled:
                continue

            for pattern in rule.patterns:
                # 3. 获取对应匹配器
                matcher = self.matchers.get(pattern.type)
                if not matcher:
                    continue

                # 4. 执行匹配
                result = matcher.match(pattern, text, context)

                if result.matched:
                    # 5. 后处理
                    value = self._apply_post_process(result.value, rule.post_process)

                    # 6. 验证
                    if self._validate(value, rule.validation):
                        effective_confidence = result.confidence * rule.priority / 100
                        candidates.append(ExtractionCandidate(
                            value=value,
                            confidence=effective_confidence,
                            rule_id=rule.ruleId
                        ))

        # 7. 选择最佳结果
        if not candidates:
            return FieldResult(field=field, value=None, confidence=0.0, source="rule_no_match")

        best = max(candidates, key=lambda c: c.confidence)
        return FieldResult(
            field=field,
            value=best.value,
            confidence=best.confidence,
            source="rule",
            rule_id=best.rule_id
        )
```

### 3.4 LLM 引擎 (LLM Engine)

#### 3.4.1 模块职责

- 构建 Prompt（含系统指令 + 文档内容 + 输出格式约束）
- 调用 LLM API
- 解析返回结果，提取结构化 JSON
- 处理异常（API 错误、格式错误、内容截断等）

#### 3.4.2 接口定义

```python
class LLMExtractor:
    def __init__(self, client: LLMClient, prompt_builder: PromptBuilder):
        self.client = client
        self.prompt_builder = prompt_builder

    async def extract(
        self,
        text: str,
        schema: dict,
        fields: list[str] | None = None
    ) -> ExtractionResult:
        """
        使用 LLM 从文本中提取结构化数据。

        Args:
            text: 预处理后的文档文本
            schema: 输出 JSON Schema
            fields: 指定只提取哪些字段（None=全部）

        Returns:
            ExtractionResult: 提取结果 + 元数据
        """
        # 1. 构建 prompt
        prompt = self.prompt_builder.build(
            system_template="extraction_system",
            user_template="extraction_user",
            context={
                "text": self._truncate_if_needed(text),
                "schema": json.dumps(schema, ensure_ascii=False, indent=2),
                "fields": fields,
                "examples": self._get_few_shot_examples(fields),
            }
        )

        # 2. 调用 API
        response = await self.client.chat_completion(
            system=prompt.system,
            messages=[{"role": "user", "content": prompt.user}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4000,
        )

        # 3. 解析响应
        return self._parse_response(response, fields)

    def _truncate_if_needed(self, text: str, max_chars: int = 80000) -> str:
        """LLM context window 不足时截断文本"""
        ...

    def _get_few_shot_examples(self, fields: list[str] | None) -> list[dict]:
        """从样本库中获取 few-shot 示例"""
        ...
```

### 3.5 结果融合器 (Result Merger)

#### 3.5.1 融合策略

```python
class ResultMerger:
    """规则引擎结果 + LLM 结果的融合器"""

    def merge(
        self,
        rule_results: dict[str, FieldResult],
        llm_results: dict[str, FieldResult]
    ) -> dict[str, FinalField]:
        """融合两种结果，生成最终输出"""

        all_fields = set(rule_results.keys()) | set(llm_results.keys())
        final = {}

        for field in all_fields:
            rule = rule_results.get(field)
            llm = llm_results.get(field)

            if rule and rule.confidence > 0.9:
                # 规则高置信度，直接采用
                final[field] = FinalField(
                    value=rule.value,
                    confidence=rule.confidence,
                    source="rule"
                )
            elif rule and llm:
                if self._values_agree(rule.value, llm.value):
                    # 一致且置信度叠加
                    final[field] = FinalField(
                        value=rule.value,
                        confidence=max(rule.confidence, llm.confidence),
                        source="both_agree"
                    )
                else:
                    # 冲突，取置信度高者
                    if rule.confidence >= llm.confidence:
                        final[field] = FinalField(
                            value=rule.value,
                            confidence=rule.confidence,
                            source="rule",
                            conflict_note=f"LLM disagree: {llm.value}"
                        )
                    else:
                        final[field] = FinalField(
                            value=llm.value,
                            confidence=llm.confidence,
                            source="llm",
                            conflict_note=f"Rule disagree: {rule.value}"
                        )
            elif llm:
                final[field] = FinalField(
                    value=llm.value,
                    confidence=llm.confidence,
                    source="llm"
                )
            else:
                final[field] = FinalField(
                    value=rule.value if rule else None,
                    confidence=rule.confidence if rule else 0,
                    source="rule" if rule else "none"
                )

        return final
```

### 3.6 规则学习引擎 (Rule Learner)

#### 3.6.1 学习流程

```
   ┌────────────┐   ┌──────────────┐   ┌────────────┐
   │ 标注数据    │   │ 预处理文本    │   │ 现有的规则  │
   └──────┬─────┘   └──────┬───────┘   └─────┬──────┘
          │                │                  │
          ▼                ▼                  ▼
   ┌──────────────────────────────────────────────┐
   │  1. 文本特征提取                              │
   │     - 对每个标注字段，提取其周围的文本特征       │
   │     - 位置特征：绝对位置、相对位置、段落位置     │
   │     - 上下文特征：前后N字符、所在段落关键词      │
   │     - 排版特征：字体大小、粗体、颜色            │
   │     - 结构特征：是否在表头、单元格位置           │
   └──────────────────┬───────────────────────────┘
                      ▼
   ┌──────────────────────────────────────────────┐
   │  2. 模式发现                                  │
   │                                              │
   │  方法 A: 基于序列的模式发现                    │
   │    - 对同字段的多个标注样本                    │
   │    - 提取字段值前后的 N-gram 序列              │
   │    - 取高频共现的序列作为候选关键词模式          │
   │                                              │
   │  方法 B: 基于位置的模式发现                    │
   │    - 对同模板的多个文档                        │
   │    - 统计字段值出现的相对位置分布               │
   │    - 位置偏差小于阈值 → 生成位置规则            │
   │                                              │
   │  方法 C: LLM 辅助模式发现                      │
   │    - 将标注样本提交给 LLM                      │
   │    - 要求 LLM 抽象出提取规则（正则或关键词）     │
   │    - LLM 返回候选正则 → 自动验证后入库          │
   └──────────────────┬───────────────────────────┘
                      ▼
   ┌──────────────────────────────────────────────┐
   │  3. 规则生成                                  │
   │     - 候选模式 → 形式化为 Rule 对象            │
   │     - 设置优先级、置信度（基于样本统计）         │
   │     - 生成后处理规则（split, trim, map 等）     │
   │     - 生成验证规则（根据字段定义自动生成）       │
   └──────────────────┬───────────────────────────┘
                      ▼
   ┌──────────────────────────────────────────────┐
   │  4. 规则验证                                  │
   │     - 用留出测试集回测                         │
   │     - 计算 precision / recall / F1            │
   │     - 与现有规则对比，检查是否需要替代          │
   │     - 高于阈值 → active / testing 状态入库      │
   │     - 低于阈值 → 标记 suggestion 待人工审核    │
   └──────────────────┬───────────────────────────┘
                      ▼
   ┌──────────────────────────────────────────────┐
   │  5. 规则入库 & 通知                           │
   │     - 写入 rule_repository                   │
   │     - 记录学习日志                            │
   │     - 新规则生效后发送通知                     │
   └─────────────────────────────────────────────┘
```

#### 3.6.2 模式发现示例

```python
class PatternDiscovery:
    """从标注数据中发现提取模式"""

    def discover_patterns(
        self,
        annotations: list[Annotation],  # 同字段的标注数据
        texts: list[str],               # 对应的原始文本
        field: str,
        method: str = "auto"
    ) -> list[CandidatePattern]:

        patterns = []

        if method in ("auto", "keyword"):
            # 方法 A: 关键词序列发现
            kw_patterns = self._discover_keyword_patterns(annotations, texts)
            patterns.extend(kw_patterns)

        if method in ("auto", "position"):
            # 方法 B: 位置模式发现（需要同模板文档才能有效）
            pos_patterns = self._discover_position_patterns(annotations, texts)
            patterns.extend(pos_patterns)

        if method in ("auto", "llm"):
            # 方法 C: LLM 辅助
            llm_patterns = self._discover_with_llm(annotations, texts, field)
            patterns.extend(llm_patterns)

        return patterns

    def _discover_keyword_patterns(
        self, annotations: list[Annotation], texts: list[str]
    ) -> list[CandidatePattern]:
        """
        关键词序列发现算法:

        1. 对每个标注样本，提取字段值前 L 个字符（L=30/50/100）
        2. 在所有样本中计算各个 N-gram 的出现频率
        3. 筛选高频出现的序列作为关键词模式
        4. 生成带捕获组的正则表达式
        """
        from collections import Counter

        prefixes = []
        for ann, text in zip(annotations, texts):
            pos = text.find(ann.value)
            if pos > 0:
                prefix = text[max(0, pos-30):pos]
                prefixes.append(prefix)

        # N-gram 频率统计
        ngram_counts = Counter()
        for prefix in prefixes:
            for n in range(1, 6):
                for i in range(len(prefix) - n + 1):
                    ngram_counts[prefix[i:i+n]] += 1

        # 筛选有区分度的 N-gram
        significant = [
            (ngram, count)
            for ngram, count in ngram_counts.most_common(20)
            if len(ngram) >= 2 and count >= len(annotations) * 0.6
        ]

        # 生成候选正则
        return [self._to_regex_pattern(ngram, field) for ngram, _ in significant]
```

### 3.7 规则库存储 (Rule Repository)

#### 3.7.1 接口抽象

```python
class RuleRepository(ABC):
    """规则库存储抽象层"""

    @abstractmethod
    def get_rules(self, field: str, format_type: str) -> list[Rule]:
        """获取特定字段+格式类型的规则"""
        ...

    @abstractmethod
    def save_rule(self, rule: Rule) -> str:
        """保存新规则"""
        ...

    @abstractmethod
    def update_rule(self, rule_id: str, updates: dict) -> bool:
        """更新规则"""
        ...

    @abstractmethod
    def get_format_templates(self) -> list[FormatTemplate]:
        """获取所有格式模板"""
        ...

    @abstractmethod
    def save_format_template(self, template: FormatTemplate) -> str:
        """保存格式模板"""
        ...

    @abstractmethod
    def get_dictionary(self, name: str) -> list[dict]:
        """获取字典"""
        ...

    @abstractmethod
    def log_hit(self, rule_id: str, document_id: str, matched: bool,
                 confidence: float, value: str | None) -> None:
        """记录规则命中"""
        ...

    @abstractmethod
    def get_rule_stats(self, rule_id: str) -> RuleStats:
        """获取规则统计信息"""
        ...
```

---

## 4. 部署架构

### 4.1 单机部署（开发/小规模）

```
┌─────────────────────────────────────┐
│           単一サーバー               │
│                                     │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ FastAPI  │  │  Worker (Celery) │ │
│  │ (API)    │  │  (非同期処理)     │ │
│  └─────┬────┘  └────────┬─────────┘ │
│        │                │           │
│        ▼                ▼           │
│  ┌──────────────────────────────┐   │
│  │         SQLite DB            │   │
│  │  (rules + logs + templates)  │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ locales/ (LLM API 依頼先)    │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

### 4.2 生产部署（团队/企业）

```
                         ┌──────────────────┐
                         │   Load Balancer   │
                         └────────┬─────────┘
                                  │
         ┌────────────────────────┼────────────────────┐
         │                        │                    │
  ┌──────▼──────┐         ┌──────▼──────┐     ┌──────┴──────┐
  │  API Server  │         │  API Server  │     │  API Server  │
  │  (FastAPI)   │  ...    │  (FastAPI)   │     │  (FastAPI)   │
  └──────┬───────┘         └──────┬───────┘     └──────┬───────┘
         │                        │                    │
         └────────────────────────┼────────────────────┘
                                  │
                         ┌────────▼────────┐
                         │    PostgreSQL    │
                         │  (rules + data)  │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │     Redis        │
                         │  (cache + queue) │
                         └─────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
   ┌──────▼──────┐       ┌───────▼───────┐       ┌───────▼───────┐
   │  Worker     │       │  Worker       │       │  Worker       │
   │  (CPU: 4)   │  ...  │  (CPU: 4)     │       │  (CPU: 4)     │
   │  - PDF処理  │       │  - 規則実行   │       │  - LLM呼出    │
   │  - OCR      │       │  - 後処理     │       │  - 規則学習   │
   └─────────────┘       └───────────────┘       └───────────────┘
```

---

## 5. 数据流设计

### 5.1 同步提取流

```
Client → POST /extract (file)
  → 文件保存到临时目录
  → 预处理 (同步)
  → 格式识别 (同步)
  → 规则提取 (同步，快速)
  → LLM 提取 (同步，等待)
  → 结果融合 (同步)
  → 后处理验证 (同步)
  → 返回 JSON
```

### 5.2 异步批处理流

```
Client → POST /batch (files)
  → 创建任务 Job ID → 返回 202 Accepted
  → Worker 从队列取任务:
    循环每个文件:
      → 预处理
      → 格式识别
      → 规则提取
      → LLM 提取(需要时)
      → 结果融合
      → 保存结果
  → Client GET /batch/{job_id} → 进度 & 结果
```

### 5.3 规则学习流

```
定時トリガー / 手動トリガー
  → 获取新标注数据（人工修正済みのLLM抽出結果）
  → 分组：(field, format_type) 为单位
  → 每组执行 Pattern Discovery
  → 生成候选规则
  → 回测验证
  → 达标 → 入库 → 记录日志
  → 不达标 → 保存候选 → 等待人工审核
```

---

## 6. 错误处理策略

```python
class ErrorHandlingStrategy:
    """系统级错误处理策略"""

    STRATEGIES = {
        "preprocessing": {
            "pdf_corrupt": "skip_file",
            "ocr_low_confidence": "partial_result_with_warning",
            "unsupported_format": "return_error",
        },
        "llm": {
            "api_timeout": "retry(3, backoff=2)",
            "rate_limit": "retry_with_backoff(exponential)",
            "invalid_json": "retry_with_strict_schema(2)",
            "context_overflow": "truncate_and_retry",
        },
        "rule_engine": {
            "no_matching_rule": "fallback_to_llm",
            "low_confidence": "flag_for_review",
            "validation_failed": "discard_result",
        },
        "merge": {
            "field_conflict": "take_higher_confidence",
            "all_null": "mark_low_quality",
        }
    }
```

---

## 7. 可观测性

### 7.1 Metrics

```python
# Prometheus metrics
EXTRACTION_REQUESTS = Counter("extraction_requests_total", "Total extraction requests")
EXTRACTION_LATENCY = Histogram("extraction_duration_seconds", "Extraction duration by mode",
                                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
                                labelnames=["mode"])
FIELD_CONFIDENCE = Gauge("field_confidence", "Confidence per field", labelnames=["field"])
RULE_ACCURACY = Gauge("rule_accuracy", "Accuracy per rule", labelnames=["rule_id"])
LLM_CALLS = Counter("llm_calls_total", "LLM API calls", labelnames=["provider", "model"])
RULE_COVERAGE = Gauge("rule_coverage_ratio", "Ratio of fields covered by rules")
```

### 7.2 日志

```json
{
  "timestamp": "2025-06-28T10:30:00Z",
  "level": "INFO",
  "event": "extraction_completed",
  "document_id": "doc_00123",
  "format_type": "template_a",
  "extraction_mode": "hybrid",
  "fields_total": 8,
  "fields_rule": 6,
  "fields_llm": 2,
  "duration_ms": 1520,
  "confidence_avg": 0.93,
  "llm_cost_usd": 0.015
}
```

---

## 8. 模块间依赖关系

```
cli.py / api/app.py
    │
    ├──▶ preprocessor/
    │      ├── pdf_processor.py     → PyMuPDF
    │      ├── word_processor.py    → python-docx
    │      ├── excel_processor.py   → openpyxl
    │      ├── html_processor.py    → BeautifulSoup
    │      ├── email_processor.py   → built-in email
    │      └── image_processor.py   → pytesseract
    │
    ├──▶ llm_engine/
    │      ├── prompt_builder.py    → templates/
    │      ├── claude_client.py     → anthropic
    │      └── openai_client.py     → openai
    │
    ├──▶ rule_engine/
    │      ├── core.py
    │      ├── matcher.py           → regex, jsonpath-ng
    │      └── merger.py
    │
    ├──▶ rule_learner/
    │      ├── pattern_discovery.py → collections, ngram
    │      ├── rule_generator.py
    │      └── rule_validator.py
    │
    ├──▶ rule_repository/
    │      └── sqlite_repo.py       → sqlite3
    │
    └──▶ common/
           ├── models.py            → pydantic
           └── schema.py
```

---

## 9. 性能指标目标

| 指标 | 目标值 | 备注 |
|---|---|---|
| 单文档预处理耗时 | < 3s | PDF 100 页以内 |
| 规则引擎单字段提取 | < 50ms | 纯内存计算 |
| LLM 提取耗时 | 3-15s | 取决于文档大小和模型 |
| 批处理吞吐量 | > 100 文档/分钟 | 规则模式 |
| 系统可用性 | 99.5% | 核心 API |
| 规则命中率 | > 80% | Phase 3 目标 |

---

## 10. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|---|---|---|---|
| v1.0 | 2025-06-28 | 初版制定 | — |
