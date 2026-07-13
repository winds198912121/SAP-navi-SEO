---
name: run-jp-recruit-extractor
description: Run, test, and verify the jp-recruit-extractor Japanese recruitment data extraction pipeline (rule-based, no LLM by default)
---

# run-jp-recruit-extractor

日本招聘案件データ抽出パイプライン — ルールベース抽出 → ユーザー確認 →
LLM修正 → ルール書き込み のインタラクティブフィードバックループ。

**基本:** LLM 不要、0円、約0.3秒で28案件をルール抽出。
**拡張:** 結果に問題があれば LLM（DeepSeek）で分析・修正し、新しいルールを自動生成。

**Driver:** `.claude/skills/run-jp-recruit-extractor/driver.sh`
**(以下では全てのパスはプロジェクトルートからの相対パス)**

## Prerequisites

```bash
python3 --version  # 3.11+
pip3 install -q -r requirements.txt
```

## Virtual Environment

```bash
source .venv/bin/activate
```

なければ自動で作られる:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -q -r requirements.txt
```

---

## 🚀 推奨ワークフロー: インタラクティブフィードバックループ

**1コマンドで全自動: 抽出 → 確認 → 修正 → ルール書き込み**

```bash
source .venv/bin/activate
python3 src/interactive_feedback.py
```

### このコマンドでできること:

1. **ルール抽出** — LLM不使用、約0.3秒で全28案件抽出 → JSON + Excel 出力
2. **結果確認** — 案件一覧から選んで詳細表示（案件名・スキル・単価・期間・日本語レベルなど）
3. **ユーザー判定** — 抽出結果は正しい？ (y/n)
4. **✅ 正しい場合** → 次の案件へ
5. **❌ 間違っている場合:**
   - 何が問題か記述（例: "スキルにPythonが足りない"）
   - LLM（DeepSeek）が原文を分析し修正案を提示
   - ユーザー確認 (y/n)
   - 修正が正しい場合 → **新しいルールを自動生成してルールライブラリに書き込み**
   - 再実行して確認
6. **全案件確認完了 → 終了**

### フィードバック例:

```
問題の説明: スキルに Python, Django が漏れている
→ LLMが原文を分析し修正案を表示
→ ユーザー確認
→ 新しい正規表現ルールを自動生成して field_rules.json に追加
```

---

## ルール抽出のみ（LLM不要）

```bash
source .venv/bin/activate
python3 src/run_pipeline.py && python3 src/export_excel.py
```

出力:
- JSON: `data/output/extraction_result_{timestamp}.json`
- Excel: `data/output/jp_recruit_cases_{timestamp}.xlsx`（41列）

---

## 最新品質メトリクス (2026-07-05 実測)

| 指標 | 値 |
|------|-----|
| ルール数 | **107** ルール / 11フィールド |
| 処理ファイル数 | 3（txt ×1, md ×1, xlsx ×1） |
| 全案件数 | **28 件** |
| 案件名抽出率 | **100%** (28/28) |
| スキル抽出率 | **96%** (27/28) |
| 期間抽出率 | **96%** (27/28) |
| 勤務地抽出率 | **50%** (14/28) |
| 日本語レベル抽出率 | **28%** (8/28) |
| 案件全文保持率 | **100%** (28/28) |
| 処理時間 | **約0.3秒**（LLM不使用、0円） |

---

## LLM分析・修正（フィードバックループ、上級者向け）

`.env` に DeepSeek API Key 設定済み:

```
EXTRACTOR_DEEPSEEK_API_KEY=sk-aa39ee...
```

個別モジュールの実行:

```bash
# LLM分析（特定案件の抽出結果を修正）
python3 -c "
from src.llm_fix import analyze_and_fix
result = analyze_and_fix(
    original_text='...',
    rule_result={'skill_requirement': ['Java']},
    user_feedback='スキルにPythonが足りない'
)
print(result['analysis'])
print(result['corrections'])
"

# ルール書き込み
python3 -c "
from src.rule_writer import write_rules_from_feedback
write_rules_from_feedback(
    original_text='...',
    user_feedback='...',
    llm_analysis='...',
    corrections={'skill_requirement': ['Java', 'Python']}
)
"
```

---

## 品質評価

```bash
source .venv/bin/activate
python3 -c "
import json
from pathlib import Path
files = sorted(Path('data/output/').glob('extraction_result_*.json'))
if not files:
    print('まだ抽出結果がありません。先に python3 src/run_pipeline.py を実行してください。')
    exit()
with open(files[-1]) as f:
    data = json.load(f)
total = data['stats']['total_cases']
fields_count = {
    'スキル抽出': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('skill_requirement')),
    '期間抽出': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('period') and c['period'].get('start_date')),
    '日本語レベル': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('japanese_level') and c['japanese_level'].get('level')!='not_specified'),
    '単価抽出': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('rate') and c['rate'].get('min')),
    '勤務地抽出': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('location') and c['location'].get('city')),
    '全文保持': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('original_text')),
}
print(f'全案件数: {total}')
for k, v in fields_count.items():
    pct = 100 * v // total
    print(f'  {k}: {v}/{total} ({pct}%)')
"
```

## ルール統計

```bash
source .venv/bin/activate
python3 -c "
import json
with open('data/rules/field_rules.json') as f:
    data = json.load(f)
rules = data['rules']
total = sum(len(v) for v in rules.values())
print(f'📚 全 {total} ルール / {len(rules)} フィールド')
for field, rlist in sorted(rules.items()):
    print(f'  • {field}: {len(rlist)} ルール')
"
```

## クイックコマンド一覧

| Command | 用途 |
|---------|------|
| `/extract` | ルール抽出パイプライン実行 |
| `/llm-extract` | DeepSeek LLM 抽出パイプライン実行 |
| `/evaluate` | 抽出品質評価 |
| `/export` | Excel 出力 |
| `/status` | プロジェクト状態確認 |
| `/rule` | ルール統計・検索 |
| `/learn-rules` | ルール学習・管理 |
| `/add-data` | 新規データ追加手順 |
| `/init` | プロジェクト初期化 |
| **`bash scripts/run-ui.sh`** | **🌐 Web UI 起動** |

---

## 🌐 Web UI（Streamlit ダッシュボード）

ブラウザベースのビジュアルインターフェース。パイプライン実行、案件一覧、フィードバックループ、ルール管理を GUI で操作。

```bash
source .venv/bin/activate
bash scripts/run-ui.sh
# または直接:
streamlit run src/ui/app.py
```

### UI ページ構成

| ページ | 機能 |
|--------|------|
| **📊 ダッシュボード** | 品質メトリクス、カバレッジチャート、ルール分布 |
| **📋 案件一覧** | 全案件ブラウズ、検索、フィルター、詳細表示 |
| **🔄 フィードバック** | インタラクティブ確認・修正・ルール自動生成（Web版） |
| **📚 ルール管理** | ルール表示、検索、正規表現テスト |
| **▶️ 実行パネル** | ルール抽出 / LLM抽出 / Excel出力の実行 |

### UI ファイル構成

```
src/ui/
├── app.py                    # メインエントリ（サイドバーナビ）
├── components.py             # 共通UI部品（カード、バッジ、CSS）
├── utils.py                  # データ読み込み・パイプライン実行
└── pages/
    ├── 01_Dashboard.py       # 📊 ダッシュボード
    ├── 02_Cases.py           # 📋 案件一覧
    ├── 03_Feedback.py        # 🔄 フィードバックループ
    ├── 04_Rules.py           # 📚 ルール管理
    └── 05_Run.py             # ▶️ 実行パネル
```

## Data layout

```
data/
├── rules/field_rules.json       # ルールライブラリ (107ルール、自動追加対応)
├── output/                       # 抽出結果 JSON + Excel
├── cache/                        # （ルール抽出では未使用）
├── 案件1.txt                     # 単一案件テキスト (1件)
├── 案件List.md                    # 複数案件マークダウン (10件)
└── 7月SAP案件一覧_0610.xlsx       # Excel案件一覧 (17件)

src/
├── interactive_feedback.py       # ★ インタラクティブフィードバックループ
├── llm_fix.py                    # LLM分析モジュール (DeepSeek)
├── rule_writer.py                # ルール自動生成・書き込み
├── run_pipeline.py               # 純ルール抽出パイプライン
├── run_llm_pipeline.py           # LLM抽出パイプライン (DeepSeek)
├── merge_results.py              # LLM+ルール結果マージ
├── export_excel.py               # Excel出力 (41列)
|
├── common/models.py              # Pydantic データモデル (RecruitmentCase他)
├── common/utils.py               # 日付変換・ユーティリティ
├── common/schema.py              # JSON Schema定義
├── rule_engine/                  # ルールエンジン (matcher, validator, merger)
├── rule_learner/                 # ルール学習エンジン (pattern_discovery, rule_generator)
├── rule_repository/              # ルールストレージ (SQLite)
├── llm_engine/                   # LLMクライアント (DeepSeek)
├── preprocessor/                 # 前処理 (PDF, OCR, テキスト正規化)
├── config.py                     # 環境設定 (.env)
├── cli.py                        # CLIエントリ (typer)
└── api/                          # FastAPI REST API
```

## Gotchas

- **ルール抽出のみならLLM不要**、約0.3秒、0円
- **LLM修正は DeepSeek API** — `.env` にキー設定済み（`EXTRACTOR_DEEPSEEK_API_KEY`）
- ルール追加後は `python3 src/run_pipeline.py` で再実行
- CLI（`python -m src.cli`）は typer 互換性問題あり — `src/` のスクリプトを直接実行推奨
- 新規データ追加: ファイルを `data/` に配置 → `src/run_pipeline.py` の `files_to_process` 編集
- Excel の単価列は数式のためルール抽出対象外（LLM 抽出が必要）
- SYSTEM_PROMPT 内の日付（`run_llm_pipeline.py`）は手動更新が必要

## Troubleshooting

| 症状 | 対処 |
|------|------|
| LLM分析が FAIL | DeepSeek API Key の確認: `.env` の `EXTRACTOR_DEEPSEEK_API_KEY` |
| ルール書き込み後も結果変わらない | `python3 src/run_pipeline.py` を再実行 |
| 既存ルールと重複した | 自動スキップされる。手動で `data/rules/field_rules.json` を確認 |
| `pydantic` の警告 | 外観のみ。結果は正しい。 |
| `ModuleNotFoundError` | `source .venv/bin/activate` を忘れていないか確認 |
| LLM抽出の日付が古い | `run_llm_pipeline.py` の SYSTEM_PROMPT の日付を現在日付に更新 |
