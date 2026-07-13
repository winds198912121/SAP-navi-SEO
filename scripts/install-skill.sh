#!/usr/bin/env bash
# ──────────────────────────────────────────
# JP Recruit Extractor — Skill 全局安裝脚本
# ──────────────────────────────────────────
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/raysource/jp-recruit-extractor/main/scripts/install-skill.sh | bash
# 或:
#   bash scripts/install-skill.sh
#
# 效果:
#   1. clone (或更新) 仓库到 ~/jp-recruit-extractor
#   2. 建立 ~/.claude/skills/run-jp-recruit-extractor symlink
#   3. 安装 Python 依赖
#   4. 验证安装成功
# ──────────────────────────────────────────

set -euo pipefail

REPO_URL="https://github.com/raysource/jp-recruit-extractor.git"
TARGET_DIR="${HOME}/jp-recruit-extractor"
SKILL_NAME="run-jp-recruit-extractor"
CLAUDE_SKILLS_DIR="${HOME}/.claude/skills"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  JP Recruit Extractor — Skill インストール${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Clone / pull repository
if [ -d "$TARGET_DIR" ]; then
    echo -e "${GREEN}✓${NC} リポジトリが既に存在: $TARGET_DIR"
    echo "  更新中..."
    cd "$TARGET_DIR" && git pull --ff-only
else
    echo "リポジトリをクローン中..."
    git clone "$REPO_URL" "$TARGET_DIR"
fi

# 2. Create global skills symlink
mkdir -p "$CLAUDE_SKILLS_DIR"
if [ -L "${CLAUDE_SKILLS_DIR}/${SKILL_NAME}" ]; then
    rm "${CLAUDE_SKILLS_DIR}/${SKILL_NAME}"
fi
ln -sf "${TARGET_DIR}/.claude/skills/${SKILL_NAME}" "${CLAUDE_SKILLS_DIR}/${SKILL_NAME}"
echo -e "${GREEN}✓${NC} Skill symlink: ${CLAUDE_SKILLS_DIR}/${SKILL_NAME} → ${TARGET_DIR}/.claude/skills/${SKILL_NAME}"

# 3. Install Python dependencies
cd "$TARGET_DIR"
echo "Python 仮想環境と依存関係をインストール中..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip3 install --quiet -r requirements.txt
echo -e "${GREEN}✓${NC} Python 依存関係インストール完了"

# 4. Run smoke test
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "スモークテストを実行中..."
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
bash "${TARGET_DIR}/.claude/skills/${SKILL_NAME}/driver.sh"

# 5. Instructions
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ インストール完了！${NC}"
echo ""
echo "使用法:"
echo ""
echo "  【A】Claude Code 内で Skill を呼び出す:"
echo "      Claude に「run-jp-recruit-extractor を実行して」と依頼"
echo ""
echo "  【B】プロジェクトディレクトリで直接実行:"
echo "      cd ${TARGET_DIR}"
echo "      source .venv/bin/activate"
echo "      python3 src/run_pipeline.py              # ルール抽出 (0.3秒)"
echo "      python3 src/export_excel.py               # Excel出力"
echo "      python3 src/interactive_feedback.py       # フィードバックループ"
echo ""
echo "  【C】カスタムコマンド (プロジェクト内):"
echo "      /extract    → ルール抽出"
echo "      /evaluate   → 品質評価"
echo "      /export     → Excel出力"
echo "      /status     → 状態確認"
echo ""
echo "📂 データディレクトリ: ${TARGET_DIR}/data/"
echo "📚 ルールライブラリ: ${TARGET_DIR}/data/rules/field_rules.json"
echo "📄 ドキュメント: ${TARGET_DIR}/docs/"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
