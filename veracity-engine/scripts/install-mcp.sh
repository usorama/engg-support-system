#!/bin/bash
#
# Install Veracity Engine MCP Server for Claude Code
#
# This script registers the Veracity Engine MCP server with Claude Code,
# enabling agents to query the knowledge graph natively.
#
# Usage:
#   ./scripts/install-mcp.sh
#
# After installation, Claude Code can use:
#   - query_codebase: Query knowledge graph for code evidence
#   - get_component_map: Generate architecture maps
#   - list_projects: List indexed projects
#   - get_file_relationships: Get file dependencies
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERACITY_ROOT="$(dirname "$SCRIPT_DIR")"
MCP_SERVER="$VERACITY_ROOT/core/mcp_server.py"

# Detect Python 3.11 path
PYTHON_PATH=""
if command -v /opt/homebrew/bin/python3.11 &> /dev/null; then
    PYTHON_PATH="/opt/homebrew/bin/python3.11"
elif command -v python3.11 &> /dev/null; then
    PYTHON_PATH="$(which python3.11)"
elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "$PY_VERSION" > "3.9" ]]; then
        PYTHON_PATH="$(which python3)"
    fi
fi

if [ -z "$PYTHON_PATH" ]; then
    echo "ERROR: Python 3.10+ required for MCP server"
    echo "Install with: brew install python@3.11"
    exit 1
fi

echo "=== Veracity Engine MCP Server Installation ==="
echo "Python: $PYTHON_PATH"
echo "MCP Server: $MCP_SERVER"
echo ""

# Check if MCP server exists
if [ ! -f "$MCP_SERVER" ]; then
    echo "ERROR: MCP server not found at $MCP_SERVER"
    exit 1
fi

# Verify MCP package is installed
if ! $PYTHON_PATH -c "import mcp" 2>/dev/null; then
    echo "Installing MCP package..."
    $PYTHON_PATH -m pip install "mcp[cli]"
fi

# Verify other dependencies
echo "Checking dependencies..."
$PYTHON_PATH -c "import neo4j, ollama, structlog, pydantic" || {
    echo "Installing dependencies..."
    $PYTHON_PATH -m pip install neo4j ollama structlog pydantic pydantic-settings pyyaml
}

# Determine Claude Code config location
CLAUDE_CONFIG_DIR="$HOME/.config/claude-code"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/config.json"

# Alternative locations
if [ -d "$HOME/Library/Application Support/Claude" ]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
fi

# Create config directory if needed
mkdir -p "$CLAUDE_CONFIG_DIR"

# Generate MCP server configuration
MCP_CONFIG=$(cat <<EOF
{
    "veracity": {
        "command": "$PYTHON_PATH",
        "args": ["$MCP_SERVER"],
        "env": {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "PYTHONPATH": "$VERACITY_ROOT"
        }
    }
}
EOF
)

# Check if config file exists
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "Existing Claude config found at: $CLAUDE_CONFIG_FILE"
    echo ""
    echo "Add the following to mcpServers in your config:"
    echo ""
    echo "$MCP_CONFIG"
    echo ""
    echo "Or run this script with --force to overwrite"
else
    # Create new config
    cat > "$CLAUDE_CONFIG_FILE" <<EOF
{
    "mcpServers": $MCP_CONFIG
}
EOF
    echo "Created Claude config at: $CLAUDE_CONFIG_FILE"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "To verify, restart Claude Code and look for these tools:"
echo "  - veracity:query_codebase"
echo "  - veracity:get_component_map"
echo "  - veracity:list_projects"
echo "  - veracity:get_file_relationships"
echo ""
echo "Test with: Ask Claude Code to 'list indexed projects using veracity'"
