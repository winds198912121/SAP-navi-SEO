# LLM Extract — LLM 抽出パイプライン実行

DeepSeek API を使用して案件データを抽出する。

## 実行

```bash
source .venv/bin/activate
python3 src/run_llm_pipeline.py
```

## 前提条件

- `.env` に `DEEPSEEK_API_KEY` が必要
- または環境変数 `EXTRACTOR_DEEPSEEK_API_KEY`
- LLM 実行のため API コストが発生

## 出力

- `data/output/llm_extraction_result_{timestamp}.json`

## ルール結果とマージ

LLM 結果とルール結果をマージ:

```bash
python3 src/merge_results.py
```

## 確認事项

- DeepSeek API キーが正しいこと
- `data/cache/` にキャッシュが作成される
- Phase 1 用途: ルール未整備の新フォーマット用 LLM 抽出
- Phase 2 以降: ルール学習の教師データ生成用
