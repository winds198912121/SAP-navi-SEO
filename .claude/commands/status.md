# Status — プロジェクト状態確認

## システム概要

```bash
python -m src.cli stats
```

## 抽出結果サマリー

```bash
python3 -c "
import json
from pathlib import Path
files = sorted(Path('data/output/').glob('extraction_result_*.json'))
if not files:
    print('まだ抽出結果がありません。`/extract` を実行してください。')
    exit()
latest = files[-1]
with open(latest) as f:
    data = json.load(f)
print(f'📋 直近の抽出 ({data[\"extraction_date\"][:19]})')
print(f'   処理ファイル: {data[\"stats\"][\"files_processed\"]}')
print(f'   全案件数: {data[\"stats\"][\"total_cases\"]}')
print(f'   使用ルール数: {data[\"rule_library\"][\"total_rules\"]}')
print(f'   モード: {data[\"stats\"][\"extraction_mode\"]}')
for fname, result in data['results'].items():
    print(f'   📄 {fname}: {result.get(\"case_count\",\"error\")} 件')
"
```

## ルール統計

```bash
python3 -c "
import json
from pathlib import Path
with open('data/rules/field_rules.json') as f:
    data = json.load(f)
rules = data['rules']
total = sum(len(v) for v in rules.values())
print(f'📚 ルールライブラリ: {total} ルール / {len(rules)} フィールド')
for field, rlist in sorted(rules.items()):
    print(f'   {field}: {len(rlist)} ルール')
"
```

## データファイル一覧

```bash
echo "📁 data/ 内の案件ファイル:"
find data/ -type f \( -name "*.txt" -o -name "*.md" -o -name "*.xlsx" -o -name "*.pdf" -o -name "*.docx" \) ! -path "*/output/*" ! -path "*/cache/*" ! -path "*/samples/*" 2>/dev/null | sort
echo ""
echo "📁 data/output/ の結果ファイル:"
ls -lh data/output/ 2>/dev/null | awk 'NR>1 {print "   " $9 " (" $5 ")"}'
```
