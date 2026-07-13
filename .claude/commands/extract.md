# Extract — ルール抽出パイプライン実行

案件ファイルからルールベースでデータ抽出を実行する (LLM 不使用、約 0.3 秒)。

## 実行

```bash
source .venv/bin/activate
python3 src/run_pipeline.py
```

## 出力

- `data/output/extraction_result_{timestamp}.json` — JSON 結果
- 自動的にルールライブラリ `data/rules/field_rules.json` を使用

## 処理対象ファイル

`run_pipeline.py` の `files_to_process` で指定:

| ファイル | 形式 |
|----------|------|
| `data/案件1.txt` | 単一テキスト |
| `data/案件List.md` | マークダウン (複数案件) |
| `data/7月SAP案件一覧_0610.xlsx` | Excel |

## 追加ファイルの処理

新規ファイルを処理する場合:

1. 対象ファイルを `data/` に配置
2. `run_pipeline.py` の `files_to_process` にエントリ追加
3. コマンド再実行

## 確認事项

- `source .venv/bin/activate` が済んでいること
- `data/rules/field_rules.json` が存在すること
- ルール追加後は必ず本コマンドを実行して結果を確認
