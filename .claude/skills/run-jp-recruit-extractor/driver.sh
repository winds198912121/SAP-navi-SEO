#!/usr/bin/env bash
# jp-recruit-extractor driver — smoke-test the full pipeline
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
PYTHON="python3"

cd "$ROOT"

step() { echo "==> $*"; }
ok()   { echo "    ✓ $*"; }

# Activate venv
step "Activating virtual environment..."
if [ ! -f .venv/bin/activate ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install --quiet -r requirements.txt
else
    source .venv/bin/activate
fi
ok "venv activated"

# Quick extraction (no LLM)
step "Running rule extraction pipeline (LLM not used)..."
python3 src/run_pipeline.py
ok "pipeline complete"

# Find latest JSON
LATEST_JSON=$(ls -t data/output/extraction_result_*.json 2>/dev/null | head -1)
if [ -z "$LATEST_JSON" ]; then
    echo "    ⚠ No extraction result found!"
    exit 1
fi

# Quality metrics
step "Quality metrics:"
python3 -c "
import json
with open('$LATEST_JSON') as f:
    data = json.load(f)
total = data['stats']['total_cases']
print(f'    Total cases: {total}')
fields = {
    'Skills': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('skill_requirement')),
    'Period': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('period') and c['period'].get('start_date')),
    'JP Level': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('japanese_level') and c['japanese_level'].get('level')!='not_specified'),
    'Rate': sum(1 for r in data['results'].values() for c in r.get('cases',[]) if c.get('rate') and c['rate'].get('min')),
}
for k, v in fields.items():
    print(f'    {k}: {v}/{total} ({100*v//total}%)')
for fname, result in data['results'].items():
    print(f'    \U0001f4c4 {fname}: {result.get(\"case_count\",0)} cases')
"

# Export to Excel
step "Exporting to Excel..."
python3 src/export_excel.py
LATEST_XLSX=$(ls -t data/output/jp_recruit_cases_*.xlsx 2>/dev/null | head -1)
[ -n "$LATEST_XLSX" ] && ok "Excel: $LATEST_XLSX"

# Rule library stats
step "Rule library..."
python3 -c "
import json
with open('data/rules/field_rules.json') as f:
    data = json.load(f)
rules = data['rules']
total = sum(len(v) for v in rules.values())
print(f'    \U0001f4da {total} rules over {len(rules)} fields:')
for field, rlist in sorted(rules.items()):
    print(f'      • {field}: {len(rlist)} rules')
"
ok "done"

echo ""
echo "  \U0001f4a1 Interactive feedback loop:"
echo "     source .venv/bin/activate"
echo "     python3 src/interactive_feedback.py"
