# Rule — ルール管理と集計

## 全ルール統計

```bash
python3 -c "
import json
from pathlib import Path
with open('data/rules/field_rules.json') as f:
    data = json.load(f)
rules = data['rules']
total = sum(len(v) for v in rules.values())
print(f'📊 全ルール数: {total}')
print(f'   対象フィールド数: {len(rules)}')
print()
for field, rule_list in sorted(rules.items()):
    print(f'  {field}: {len(rule_list)} ルール')
    for r in rule_list:
        print(f'    [{r[\"id\"]}] priority={r.get(\"priority\",50)}')
"
```

## ルールファイルバックアップ

```bash
cp data/rules/field_rules.json "data/rules/field_rules_$(date +%Y%m%d).json"
```

## ルール検索

```bash
python3 -c "
import json
import sys
term = sys.argv[1].lower()
with open('data/rules/field_rules.json') as f:
    data = json.load(f)
for field, rule_list in data['rules'].items():
    for r in rule_list:
        if term in r.get('pattern','').lower() or term in r['id'].lower():
            print(f'  [{r[\"id\"]}] ({field}) {r.get(\"pattern\",\"\")[:80]}')
" "$1"
```
