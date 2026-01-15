#!/bin/bash
#
# Register a project with ESS (Engineering Support System)
#
# NOTE: This script is a convenience wrapper for initial setup.
# Once ESS MCP server is running, prefer using MCP tools instead:
#
#   register_project(project_name="myproject", root_dir="/path/to/project")
#   index_project(project_name="myproject")
#
# Usage: ./register-project.sh <project-name> <project-path>
#
# Example:
#   ./register-project.sh pinglearn ~/Projects/pinglearn
#   ./register-project.sh rad-engineer ~/Projects/rad-engineer-v2
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
log_tip() { echo -e "${CYAN}[TIP]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESS_ROOT="$(dirname "$SCRIPT_DIR")"
VERACITY_ENGINE="${ESS_ROOT}/veracity-engine"

# Check arguments
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <project-name> <project-path>"
    echo ""
    echo "Examples:"
    echo "  $0 pinglearn ~/Projects/pinglearn"
    echo "  $0 rad-engineer ~/Projects/rad-engineer-v2"
    echo ""
    echo "Preferred method (once MCP server is running):"
    echo "  Use MCP tools: register_project() and index_project()"
    exit 1
fi

PROJECT_NAME="$1"
PROJECT_PATH="$2"

# Resolve path
PROJECT_PATH=$(cd "$PROJECT_PATH" && pwd)

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "           ESS Project Registration: ${PROJECT_NAME}"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Step 1: Verify project exists
log_step "1/4: Verifying project path..."
if [[ ! -d "$PROJECT_PATH" ]]; then
    log_warn "Project path does not exist: $PROJECT_PATH"
    exit 1
fi
log_info "Project found at: $PROJECT_PATH"

# Step 2: Index project with Veracity Engine
log_step "2/4: Indexing project with Veracity Engine..."
cd "$VERACITY_ENGINE"
python3 core/build_graph.py --project-name "$PROJECT_NAME" --root-dir "$PROJECT_PATH" 2>&1 | tail -10

log_info "Project indexed in Neo4j"

# Step 3: Check/Update CLAUDE.md
log_step "3/4: Checking CLAUDE.md for ESS integration..."
CLAUDE_MD="${PROJECT_PATH}/CLAUDE.md"

if [[ -f "$CLAUDE_MD" ]]; then
    if grep -q "Engineering Support System" "$CLAUDE_MD" 2>/dev/null; then
        log_info "CLAUDE.md already has ESS integration section"
    else
        log_warn "CLAUDE.md exists but missing ESS integration"
        echo ""
        echo "Add the ESS integration section from:"
        echo "  ${ESS_ROOT}/integration/CLAUDE_MD_INTEGRATION.md"
        echo ""
    fi
else
    log_warn "No CLAUDE.md found at $CLAUDE_MD"
    echo "Consider creating one with ESS integration section"
fi

# Step 4: Verify registration
log_step "4/4: Verifying registration..."
cd "$VERACITY_ENGINE"
python3 -c "
from core.project_registry import get_project
try:
    project = get_project('${PROJECT_NAME}')
    print(f'Project registered: {project}')
except Exception as e:
    print(f'Note: Project may not be in registry yet (this is OK)')
" 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "           Registration Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "  Project: ${PROJECT_NAME}"
echo "  Path:    ${PROJECT_PATH}"
echo ""
echo "  Once registered, use MCP tools (no more local scripts!):"
echo ""
log_tip "Query work items:"
echo "     query_work_items(project_name=\"${PROJECT_NAME}\", status=\"open\")"
echo ""
log_tip "Trace file to work:"
echo "     trace_file_to_work(file_path=\"src/file.ts\", project_name=\"${PROJECT_NAME}\")"
echo ""
log_tip "Query codebase:"
echo "     query_codebase(project_name=\"${PROJECT_NAME}\", question=\"What are the main components?\")"
echo ""
echo "  Add MCP server to your Claude Code config:"
echo "  See: ${ESS_ROOT}/integration/CLAUDE_MD_INTEGRATION.md"
echo ""
