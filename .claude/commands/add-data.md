# Add Data — 新規データ追加と抽出

新しい案件ファイルを追加して抽出パイプラインで処理する。

## 手順

### 1. ファイルを配置

対応している形式:

| 拡張子 | 説明 |
|--------|------|
| `.txt` | テキスト (単一案件) |
| `.md` | マークダウン (複数案件、案件名マーカーで分割) |
| `.xlsx` | Excel (1行=1案件) |
| `.pdf` | PDF (LLM 抽出用) |
| `.docx` | Word (LLM 抽出用) |
| `.html` | HTML (LLM 抽出用) |
| `.eml` | メール (LLM 抽出用) |
| `.png/.jpg/.jpeg` | 画像 (LLM 抽出用、OCR 要) |

```bash
cp /path/to/your/file.docx data/
```

### 2. ルール抽出パイプラインを更新

新規ファイルがルール抽出対象の場合:

- 编辑 `src/run_pipeline.py` 的 `files_to_process` 列表
- 追加格式:
```python
("your_new_file.xlsx", "excel", processor.process_excel),
("your_new_file.md", "text", processor.process_markdown),
("your_new_file.txt", "text", processor.process_txt),
```

### 3. 抽出実行

```bash
source .venv/bin/activate
python3 src/run_pipeline.py
```

### 4. Excel 出力

```bash
python3 src/export_excel.py
```

## 確認

- `/evaluate` で品質指標を確認
- 結果は `data/output/` に保存
