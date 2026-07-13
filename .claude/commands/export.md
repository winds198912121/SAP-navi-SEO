# Export — 抽出結果のエクスポート

## Excel 出力

最新の抽出結果 JSON を Excel (41 列) に変換:

```bash
source .venv/bin/activate
python3 src/export_excel.py
```

出力: `data/output/jp_recruit_cases_{timestamp}.xlsx`

## JSON 出力確認

```bash
ls -lt data/output/extraction_result_*.json | head -3
```

## CLI エクスポート

```bash
# 単一ファイル抽出 + JSON出力
python -m src.cli extract --input sample.txt --output data/output/result.json --pretty

# バッチ処理
python -m src.cli batch --input-dir data/ --output-dir data/output/ --format json

# CSV出力 (バッチ時)
python -m src.cli batch --input-dir data/ --output-dir data/output/ --format csv

# Excel出力 (バッチ時)
python -m src.cli batch --input-dir data/ --output-dir data/output/ --format excel
```

## エクスポート列 (41 列)

案件全文を含む全フィールドがエクスポート対象。
