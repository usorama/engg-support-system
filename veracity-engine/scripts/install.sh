#!/bin/bash

# Ground-Truth Context System (GTCS) - Universal Installer
# Purpose: Bootstrap the full context engineering system in any target project.

set -e

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
TARGET_PROJECT_DIR=$(pwd)
PROJECT_NAME=$(basename "$TARGET_PROJECT_DIR")

echo "🚀 Bootstrapping Ground-Truth Context System for project: $PROJECT_NAME"

# 1. Environment Check
echo "🔍 Checking dependencies..."
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker not found. Please install Docker."
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo "❌ Error: Ollama not found. Please install Ollama (https://ollama.ai)."
    exit 1
fi

# 2. Infra Setup (Neo4j)
echo "📦 Ensuring Neo4j is running..."
(cd "$REPO_DIR/infra" && docker compose up -d)

# 3. Python Environment
echo "🐍 Setting up Python environment..."
if [ ! -d "$TARGET_PROJECT_DIR/.veracity_venv" ]; then
    python3 -m venv "$TARGET_PROJECT_DIR/.veracity_venv"
fi
source "$TARGET_PROJECT_DIR/.veracity_venv/bin/activate"
pip install -r "$REPO_DIR/requirements.txt"

# 4. Project Initialization
echo "🏗️ Initializing Knowledge Graph..."
python3 "$REPO_DIR/core/build_graph.py" --project-name "$PROJECT_NAME" --root-dir "$TARGET_PROJECT_DIR"

# 5. Git Hook Installation
echo "🪝 Installing Git Commit Hook..."
if git rev-parse --is-inside-work-tree &>/dev/null; then
    mkdir -p ".git/hooks"
    HOOK_FILE=".git/hooks/post-commit"
    cat <<EOF > "$HOOK_FILE"
#!/bin/bash
# Ground-Truth Context System - Post-Commit Indexing
echo "📊 Updating Knowledge Graph for $PROJECT_NAME..."
source "$TARGET_PROJECT_DIR/.veracity_venv/bin/activate"
python3 "$REPO_DIR/core/build_graph.py" --project-name "$PROJECT_NAME" --root-dir "$TARGET_PROJECT_DIR"
EOF
    chmod +x "$HOOK_FILE"
else
    echo "⚠️ Not a git repository, skipping hook installation."
fi

# 6. Templates & Rules
echo "📜 Injecting AI Agent Rules..."
mkdir -p "$TARGET_PROJECT_DIR/.cursor/rules"
if [ -f "$REPO_DIR/templates/context-kg.mdc" ]; then
    sed "s/{{project_name}}/$PROJECT_NAME/g" "$REPO_DIR/templates/context-kg.mdc" > "$TARGET_PROJECT_DIR/.cursor/rules/context-kg.mdc"
else
    echo "⚠️ Template context-kg.mdc missing in repo."
fi

# Append to CLAUDE.md if it exists
if [ -f "$TARGET_PROJECT_DIR/CLAUDE.md" ]; then
    if ! grep -q "veracity-engine" "$TARGET_PROJECT_DIR/CLAUDE.md"; then
        echo -e "\n## Ground-Truth Context System\nBefore complex tasks, run: \`python3 $REPO_DIR/core/ask_codebase.py --project-name $PROJECT_NAME \"your question\"\`" >> "$TARGET_PROJECT_DIR/CLAUDE.md"
    fi
fi

echo "✅ Ground-Truth Context System installed successfully!"
echo "   - View Graph: http://localhost:5173"
echo "   - Query Context: python3 $REPO_DIR/core/ask_codebase.py --project-name $PROJECT_NAME \"What is...\""
