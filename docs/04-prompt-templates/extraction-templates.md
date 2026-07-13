# 04 — Prompt 模板集 (Prompt Templates)

> **文档版本**: v1.0
> **更新日期**: 2025-06-28

## 目录

1. [案件データ抽出用 Prompt](#1-案件データ抽出用-prompt)
2. [ルール生成用 Prompt](#2-ルール生成用-prompt)
3. [検証用 Prompt](#3-検証用-prompt)
4. [Few-shot 例示テンプレート](#4-few-shot-例示テンプレート)

---

## 1. 案件データ抽出用 Prompt

### 1.1 System Prompt (extraction_system)

```markdown
You are a specialized data extraction assistant for Japanese IT recruitment documents.

## Your Task
Extract structured information from the provided Japanese recruitment case document.
The document may contain: project name, skills required, location, rate/salary, period,
headcount, industry, trade flow, language requirements, working hours, and other details.

## Output Format
You MUST respond with a valid JSON object matching the provided schema.
Do NOT include any text outside the JSON object.
If a field's value is not found in the document, use null for the entire field
(or omit optional fields entirely).

## Language Handling
- The input document is in Japanese
- Extract values as-is (keep Japanese text for names, location names, etc.)
- Standardize dates to YYYY-MM-DD format
- Standardize rate/salary to numeric values when possible
- Skills should be extracted as individual strings in an array

## Quality Guidelines
1. Be precise: extract EXACTLY what the document says, do not infer or add information
2. If a value appears ambiguous, extract it and note the ambiguity in a note field
3. For skill requirements: list each skill separately, split by 、・/
4. For location: prefer the most specific address/station mentioned
5. If the document has multiple sections, pay attention to section headers
6. Japanese level: map descriptions to standard levels (native/business/n2/n3/n4)
7. Contract type: map descriptions to (jun_inin/ukeoi/haken/ses/other)
8. Do NOT merge "preferred" (歓迎/尚可) skills into required skills
```

### 1.2 User Prompt (extraction_user)

```markdown
以下の日本IT招聘案件の文書から、指定されたJSONスキーマに従って構造化データを抽出してください。

## 文書内容
```
{text}
```

## 出力JSONスキーマ
```json
{schema}
```

## 抽出対象フィールド
{fields}

## 注意事項
- 該当する値が文書にない場合は null を設定してください
- 日付は YYYY-MM-DD 形式に統一してください
- 金額は数値のみを抽出し、単位は unit フィールドに指定してください
- スキルは個別の要素として配列で出力してください
- 「歓迎」「尚可」「あると望ましい」と記載されたスキルは preferred_skills に分けてください
- 各フィールドの値は必ず文書の内容に基づいてください。推測や補完はしないでください

## 出力
上記のJSONスキーマに従って、有効なJSONオブジェクトのみを出力してください。
```

### 1.3 Context-optimized Prompt (長文ドキュメント用)

```markdown
以下の日本IT招聘案件の文書から構造化データを抽出してください。
文書が長いため、以下のガイドラインに従ってください：

1. 文書全体から関連するセクションを特定してください
2. 以下のキーワードを含むセクションに注目してください：
   - 案件名 / プロジェクト名 / タイトル
   - スキル / 要件 / 求める人材 / 応募資格
   - 勤務地 / 場所 / 拠点
   - 単価 / 金額 / 報酬 / 給与 / 月額 / 日額
   - 期間 / 契約期間 / 作業期間
   - 募集人数 / 人数
   - 業種 / 案件区分
   - 商流 / 契約形態 / 準委任 / 請負 / 派遣 / SES
   - 日本語 / 英語 / 言語
   - 勤務時間 / 残業
   - 面接 / 選考
3. 各キーワードセクションから該当する値を抽出し、JSONにマッピングしてください

## 文書
```
{text}
```

## 出力スキーマ
```json
{schema}
```
```

---

## 2. ルール生成用 Prompt

### 2.1 パターン発見 (pattern_discovery)

```markdown
You are a pattern discovery assistant for extraction rules.
Given multiple examples of the SAME FIELD being extracted from Japanese recruitment documents,
identify common patterns that can be used to extract this field reliably via regex.

## Input
- Field name: {field_name}
- {N} annotated examples showing the field value and its surrounding context

## Your Task
For each pattern you identify, provide:
1. A regular expression pattern (Python `regex` module compatible) that captures the field value
2. The confidence level (0.0-1.0) for this pattern
3. A brief description of what the pattern matches

## Guidelines for writing patterns
- Use non-capturing groups (?:...) for grouping without extracting
- Use capturing groups (...) for the value you want to extract
- Handle Japanese full-width/half-width variations: Ａ->A, ：->:, （->(
- Account for common variations: スキル / 必須スキル / 求めるスキル
- Use \\n for newlines within patterns
- If the value is a list (skills), use split post-processing, not multiple captures
- Mark patterns that rely on document structure (position) as "type": "position"

## Output format (JSON array)
```json
[
  {
    "type": "regex",
    "value": "(?:案件名|件名)[：:]([^\\n]+)",
    "confidence": 0.92,
    "description": "..."
  }
]
```
```

### 2.2 ルール検証 (rule_validation)

```markdown
You are a rule validation assistant.
Evaluate whether the provided extraction rule is correct, robust, and safe to deploy.

## Rule to Validate
```json
{rule}
```

## Evaluation Criteria
1. **Correctness**: Does the pattern accurately capture the intended field?
2. **Precision**: How likely is this pattern to produce false positives?
3. **Robustness**: Does it handle variations in formatting, whitespace, etc.?
4. **Safety**: Could this pattern cause catastrophic backtracking (ReDoS)?
5. **Japanese handling**: Does it properly handle full-width/half-width, etc.?

## Output
```json
{
  "is_valid": true/false,
  "issues": [
    {
      "severity": "high|medium|low",
      "description": "...",
      "suggestion": "..."
    }
  ],
  "estimated_precision": 0.0-1.0,
  "estimated_recall": 0.0-1.0,
  "final_verdict": "accept|review|reject"
}
```
```

---

## 3. 検証用 Prompt

### 3.1 抽出結果検証 (extraction_validation)

```markdown
You are a quality assurance assistant for data extraction.
Compare the extracted JSON with the original document and identify any errors or omissions.

## Original Document
```
{text}
```

## Extracted JSON
```json
{extracted}
```

## Your Task
For each field in the extracted JSON:
1. Verify the value matches the document content
2. Check for missing fields that should be present
3. Flag any values that appear to be inferred rather than extracted
4. Suggest corrections for any errors found

## Output Format
```json
{
  "overall_quality": "high|medium|low",
  "correct_fields": [],
  "incorrect_fields": [
    {
      "field": "field_name",
      "extracted_value": "...",
      "expected_value": "...",
      "issue": "description of the error",
      "severity": "high|medium|low"
    }
  ],
  "missing_fields": [],
  "suggestions": []
}
```
```

### 3.2 フィールド精度測定 (field_accuracy)

```markdown
You are an evaluation assistant.
Compare the extracted value with the ground truth value and determine accuracy.

## Field: {field_name}
## Extracted: {extracted_value}
## Ground Truth: {ground_truth}

## Accuracy Criteria
- **Exact match**: Values are identical → score = 1.0
- **Semantic match**: Values differ in wording but mean the same → score = 0.8
- **Partial match**: Some information correct, some missing/extra → score = 0.5
- **Wrong**: Incorrect value → score = 0.0
- **Missing**: Extracted as null but should have value → score = 0.0

## Output
```json
{
  "score": 0.0-1.0,
  "match_type": "exact|semantic|partial|wrong|missing",
  "note": "explanation"
}
```
```

---

## 4. Few-shot 例示テンプレート

### 4.1 標準Few-shot例

```json
[
  {
    "document": "【案件名】某証券会社向け基幹システム開発\n【スキル】Java, Spring Boot, AWS\n【単価】月額70-80万円\n【場所】東京都品川区（品川駅徒歩5分）\n【期間】2025/7/1〜2026/3/31（延長可能性あり）\n【商流】準委任／2社上乗せ\n【日本語】ビジネスレベル",
    "extraction": {
      "project_name": "某証券会社向け基幹システム開発",
      "skill_requirement": ["Java", "Spring Boot", "AWS"],
      "location": {"city": "東京都品川区", "station": "品川駅"},
      "rate": {"min": 70, "max": 80, "unit": "monthly"},
      "period": {"start_date": "2025-07-01", "end_date": "2026-03-31", "note": "延長可能性あり"},
      "trade_flow": {"contract_type": "jun_inin", "layers": 2},
      "japanese_level": {"level": "business"}
    }
  },
  {
    "document": "■案件名：ECサイトリニューアル\n■必須スキル：Python, Django, PostgreSQL, Docker\n■歓迎スキル：Kubernetes, AWS\n■単価：月額65-80万円\n■勤務地：大阪市北区（梅田駅）リモート可（週2出社）\n■契約期間：2025/8/1〜長期\n■募集人数：2名\n■面接：1回",
    "extraction": {
      "project_name": "ECサイトリニューアル",
      "skill_requirement": ["Python", "Django", "PostgreSQL", "Docker"],
      "preferred_skills": ["Kubernetes", "AWS"],
      "location": {"city": "大阪市北区", "station": "梅田駅", "remote_policy": "hybrid", "remote_detail": "週2出社"},
      "rate": {"min": 65, "max": 80, "unit": "monthly"},
      "period": {"start_date": "2025-08-01", "long_term": true},
      "headcount": 2,
      "interviews": 1
    }
  }
]
```

### 4.2 エッジケースFew-shot例

```json
[
  {
    "document": "【案件名】大手損保 次期顧客管理システム\n【応募資格】Java実務経験5年以上、Spring Framework\n【単価】70万〜80万円（月額）※交通費別\n【勤務地】東京・お茶の水\n【期間】2025/7/1〜2026/3/31（以降更新の可能性あり）",
    "notes": ["経験年数が明示されている", "単価に注釈あり", "勤務地が駅名のみ"],
    "extraction": {
      "project_name": "大手損保 次期顧客管理システム",
      "skill_requirement": ["Java", "Spring Framework"],
      "experience_years": {"min": 5, "description": "Java実務経験5年以上"},
      "location": {"city": "東京都", "station": "お茶の水"},
      "rate": {"min": 70, "max": 80, "unit": "monthly", "note": "交通費別"},
      "period": {"start_date": "2025-07-01", "end_date": "2026-03-31", "note": "以降更新の可能性あり"}
    }
  },
  {
    "document": "【案件名】某通信会社 5G関連開発\n【求めるスキル】\n・Java or C++ での開発経験\n・Linux での開発経験\n・SQL を使ったデータ処理\n・日本語N2以上\n【単価】スキル見合い（60-90万円/月額）\n【勤務地】東京都内（リモート可：週1出社程度）\n【期間】2025/7月〜長期",
    "notes": ["スキルが箇条書き", "単価が範囲広い", "リモート比率あり"],
    "extraction": {
      "project_name": "某通信会社 5G関連開発",
      "skill_requirement": ["Java", "C++", "Linux", "SQL"],
      "location": {"city": "東京都", "remote_policy": "hybrid", "remote_detail": "週1出社程度"},
      "rate": {"min": 60, "max": 90, "unit": "monthly"},
      "period": {"start_date": "2025-07-01", "long_term": true},
      "japanese_level": {"level": "n2", "level_jp": "N2以上"}
    }
  }
]
```

---

## 5. Prompt 管理ガイドライン

### 5.1 バージョン管理

- 各 Prompt テンプレートは `/templates/` ディレクトリで管理
- ファイル名: `{用途}_{言語}_{vN}.md`
- メタデータをファイル先頭に YAML Front Matter で記述

```yaml
---
template_id: extraction_system_v3
purpose: system_prompt_for_extraction
model_compatibility: [claude-opus-4, claude-sonnet-4, gpt-4o]
created_at: 2025-06-20
updated_at: 2025-06-28
accuracy_on_test_set: 0.94
---
```

### 5.2 A/B テスト

- 新しい Prompt は Shadow Mode で既存と比較
- 100 サンプルの精度比較後、有意に良い場合に切替
- Prompt 変更履歴は Git 管理

### 5.3 注意事項

1. **出力フォーマットは厳格に**: JSON mode を利用、スキーマを明示
2. **日本語処理は明示的に指示**: 全角/半角、日付形式、単位換算
3. **文脈長制限**: 80K トークンを超える文書は分割処理を検討
4. **Few-shot は最新の成功例を使う**: 定期的に更新
5. **エラーハンドリング**: パース失敗時の再試行ロジックを組み込む
