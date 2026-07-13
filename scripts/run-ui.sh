#!/usr/bin/env bash
# JP Recruit Extractor — Web UI 起動スクリプト
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "📋 JP Recruit Extractor — Web UI"
echo "================================="
echo ""

# Activate venv
if [ ! -f .venv/bin/activate ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --quiet -r requirements.txt
else
    source .venv/bin/activate
fi

echo "🚀 Starting Streamlit UI..."
echo "   Open in browser: http://localhost:8501"
echo ""

streamlit run src/ui/app.py --server.port 8501
