# Init — プロジェクト初期化

プロジェクトの初期設定と必要なディレクトリを作成する。

## 実行

```bash
source .venv/bin/activate
python -m src.cli init
```

## 作成されるディレクトリ

| ディレクトリ | 用途 |
|-------------|------|
| `data/output/` | 抽出結果出力先 |
| `data/cache/` | キャッシュ |
| `data/samples/` | サンプルファイル |
| `data/rules/` | ルールライブラリ |

## 環境設定

```bash
# .env ファイルの編集
cp .env.example .env
# 必要に応じて API キーを設定
#   EXTRACTOR_DEEPSEEK_API_KEY=sk-xxxx
#   EXTRACTOR_ANTHROPIC_API_KEY=sk-xxxx
```

## 確認

- Python 3.11+ 必要
- `python3 --version` で確認
- 依存パッケージ: `pip install -r requirements.txt`
