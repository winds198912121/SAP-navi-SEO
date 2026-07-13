# Learn Rules — ルール学習 / ルール管理

## ルールライブラリ編集

ルールは `data/rules/field_rules.json` に JSON 形式で保存。

### ルール追加例

```json
{
  "rules": {
    "period": [
      {
        "id": "period_013",
        "pattern": "（新パターン）",
        "priority": 85,
        "field": "period"
      }
    ]
  }
}
```

### ルール命名規約

- `{field}_{3桁連番}`: `period_001`, `skill_must_001`
- 日本語レベル: `jp_{3桁}`
- 英語レベル: `eng_{3桁}`
- Excel row_text 専用: `{field}_rowtext_{連番}`

### ルールを追加したら

```bash
# 再実行して結果確認
python3 src/run_pipeline.py

# 品質確認
/evaluate
```

## CLI からのルール管理

```bash
# ルール一覧
python -m src.cli rule list

# 特定フィールドのルール
python -m src.cli rule list --field period

# ルールテスト
python -m src.cli rule test period_001 sample.txt

# ルール精度評価
python -m src.cli rule evaluate period_001 data/test/dataset.jsonl
```

## ルール学習 (Phase 2 feature)

LLM 結果から自動ルール生成 (現在開発中):

```bash
python -m src.cli rule learn --field skill_requirement
```

## 回帰テスト

```bash
python -m src.cli rule regression data/test/
```
