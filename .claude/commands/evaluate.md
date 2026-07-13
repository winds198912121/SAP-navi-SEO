# Evaluate — 抽出品質評価 / 確認

## 直近の抽出結果を確認

```bash
source .venv/bin/activate
python3 src/export_excel.py
ls -lt data/output/extraction_result_*.json | head -3
python3 -c "
import json, sys
from pathlib import Path
files = sorted(Path('data/output/').glob('extraction_result_*.json'))
if files:
    with open(files[-1]) as f:
        data = json.load(f)
    print(f'抽出日時: {data[\"extraction_date\"]}')
    print(f'ルール数: {data[\"rule_library\"][\"total_rules\"]}')
    print(f'処理ファイル: {data[\"stats\"][\"files_processed\"]}')
    print(f'全案件数: {data[\"stats\"][\"total_cases\"]}')
    print(f'モード: {data[\"stats\"][\"extraction_mode\"]}')
    for fname, result in data['results'].items():
        print(f'  📄 {fname}: {result.get(\"case_count\",\"?\")} 件')
"
```

## 品質指標の確認

各案件の抽出狀態を確認:

```bash
python3 -c "
import json
from pathlib import Path
files = sorted(Path('data/output/').glob('extraction_result_*.json'))
if not files: exit()
with open(files[-1]) as f:
    data = json.load(f)
total = 0
with_skills = 0
with_period = 0
with_jp = 0
with_rate = 0
with_location = 0
with_original = 0
for fname, result in data['results'].items():
    for case in result.get('cases', []):
        total += 1
        if case.get('skill_requirement'): with_skills += 1
        if case.get('period'): with_period += 1
        if case.get('japanese_level') and case['japanese_level'].get('level')!='not_specified': with_jp += 1
        if case.get('rate') and case['rate'].get('min'): with_rate += 1
        if case.get('location') and case['location'].get('city'): with_location += 1
        if case.get('original_text'): with_original += 1
print(f'總案件数: {total}')
if total:
    print(f'  スキル抽出率: {with_skills}/{total} ({100*with_skills//total}%)')
    print(f'  期間抽出率: {with_period}/{total} ({100*with_period//total}%)')
    print(f'  日本語レベル抽出率: {with_jp}/{total} ({100*with_jp//total}%)')
    print(f'  単価抽出率: {with_rate}/{total} ({100*with_rate//total}%)')
    print(f'  勤務地抽出率: {with_location}/{total} ({100*with_location//total}%)')
    print(f'  案件全文保持率: {with_original}/{total} ({100*with_original//total}%)')
"
```

## フィールド別ルールカバレッジ

```bash
python3 -c "
import json
from pathlib import Path
with open('data/rules/field_rules.json') as f:
    rules = json.load(f)
for field, rule_list in rules.get('rules', {}).items():
    print(f'  {field}: {len(rule_list)} ルール')
"
```
