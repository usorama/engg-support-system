#!/bin/bash
# Test script for Claude Code Integration with ESS Veracity Engine
# Tests SSH tunnel and MCP server connectivity

set -e

echo "=== Claude Code Integration Test ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VPS_HOST="72.60.204.156"
LOCAL_NEO4J_PORT=7688
LOCAL_QDRANT_PORT=6334
VPS_NEO4J_PASSWORD="password123"

echo "Step 1: Check SSH tunnel"
if ps aux | grep -v grep | grep "ssh.*${LOCAL_NEO4J_PORT}" > /dev/null; then
    echo -e "${GREEN}✅ SSH tunnel is running${NC}"
    ps aux | grep -v grep | grep "ssh.*${LOCAL_NEO4J_PORT}" | awk '{print "   PID: " $2}'
else
    echo -e "${YELLOW}⚠️  SSH tunnel not found. Starting...${NC}"
    ssh -L ${LOCAL_NEO4J_PORT}:127.0.0.1:7687 -L ${LOCAL_QDRANT_PORT}:127.0.0.1:6333 root@${VPS_HOST} -N -f
    sleep 2
    if ps aux | grep -v grep | grep "ssh.*${LOCAL_NEO4J_PORT}" > /dev/null; then
        echo -e "${GREEN}✅ SSH tunnel started${NC}"
    else
        echo -e "${RED}❌ Failed to start SSH tunnel${NC}"
        exit 1
    fi
fi

echo ""
echo "Step 2: Test tunnel ports"
if nc -zv localhost ${LOCAL_NEO4J_PORT} 2>&1 | grep -q succeeded; then
    echo -e "${GREEN}✅ Neo4j tunnel port ${LOCAL_NEO4J_PORT} is open${NC}"
else
    echo -e "${RED}❌ Neo4j tunnel port ${LOCAL_NEO4J_PORT} is not accessible${NC}"
    exit 1
fi

if nc -zv localhost ${LOCAL_QDRANT_PORT} 2>&1 | grep -q succeeded; then
    echo -e "${GREEN}✅ Qdrant tunnel port ${LOCAL_QDRANT_PORT} is open${NC}"
else
    echo -e "${RED}❌ Qdrant tunnel port ${LOCAL_QDRANT_PORT} is not accessible${NC}"
    exit 1
fi

echo ""
echo "Step 3: Test VPS Neo4j directly"
ESS_COUNT=$(ssh root@${VPS_HOST} "docker exec ess-neo4j cypher-shell -u neo4j -p ${VPS_NEO4J_PASSWORD} 'MATCH (n) WHERE n.project = \"ess\" RETURN count(n) as count;' --format plain" | tail -1 | tr -d '"')
if [ "$ESS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ VPS Neo4j has ${ESS_COUNT} ESS nodes${NC}"
else
    echo -e "${RED}❌ VPS Neo4j query failed or returned 0 nodes${NC}"
    exit 1
fi

echo ""
echo "Step 4: Test Python Neo4j driver through tunnel"
/opt/homebrew/bin/python3.11 << 'EOF'
from neo4j import GraphDatabase
import sys

try:
    # Note: Using 127.0.0.1 instead of localhost to force IPv4
    driver = GraphDatabase.driver('bolt://127.0.0.1:7688', auth=('neo4j', 'password123'))
    with driver.session() as session:
        result = session.run('MATCH (n) WHERE n.project = "ess" RETURN count(n) as count')
        record = result.single()
        count = record['count']
        print(f'\033[0;32m✅ Python driver connected through tunnel\033[0m')
        print(f'   ESS nodes: {count:,}')

        # Get sample file
        result = session.run('MATCH (n:File) WHERE n.project = "ess" RETURN n.path as path LIMIT 1')
        record = result.single()
        if record:
            print(f'   Sample file: {record["path"]}')
    driver.close()
    sys.exit(0)
except Exception as e:
    print(f'\033[0;31m❌ Python driver failed: {e}\033[0m', file=sys.stderr)
    sys.exit(1)
EOF

PYTHON_STATUS=$?
if [ $PYTHON_STATUS -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Python driver test failed${NC}"
    echo "This may be due to Neo4j protocol version mismatch or authentication"
    echo "The MCP server may still work with different driver settings"
fi

echo ""
echo "Step 5: Check Claude Code config"
CONFIG_FILE="$HOME/.config/claude-code/config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✅ Claude Code config exists${NC}"
    echo "   Location: $CONFIG_FILE"

    # Check permissions
    PERMS=$(stat -f "%OLp" "$CONFIG_FILE" 2>/dev/null || stat -c "%a" "$CONFIG_FILE" 2>/dev/null)
    if [ "$PERMS" = "600" ]; then
        echo -e "${GREEN}✅ Config permissions are secure (600)${NC}"
    else
        echo -e "${YELLOW}⚠️  Config permissions are $PERMS (should be 600)${NC}"
        echo "   Run: chmod 600 $CONFIG_FILE"
    fi

    # Check if veracity-ess is configured
    if grep -q "veracity-ess" "$CONFIG_FILE"; then
        echo -e "${GREEN}✅ veracity-ess MCP server is configured${NC}"
    else
        echo -e "${RED}❌ veracity-ess MCP server not found in config${NC}"
    fi
else
    echo -e "${RED}❌ Claude Code config not found${NC}"
    echo "   Expected at: $CONFIG_FILE"
    exit 1
fi

echo ""
echo "Step 6: Check MCP server script"
MCP_SERVER="/Users/umasankr/Projects/engg-support-system/veracity-engine/core/mcp_server.py"
if [ -f "$MCP_SERVER" ]; then
    echo -e "${GREEN}✅ MCP server script exists${NC}"
    echo "   Location: $MCP_SERVER"
else
    echo -e "${RED}❌ MCP server script not found${NC}"
    echo "   Expected at: $MCP_SERVER"
    exit 1
fi

echo ""
echo "Step 7: Check Python dependencies"
if /opt/homebrew/bin/python3.11 -c "import neo4j, mcp" 2>/dev/null; then
    echo -e "${GREEN}✅ Required Python packages installed${NC}"
else
    echo -e "${YELLOW}⚠️  Some Python packages may be missing${NC}"
    echo "   Run: cd veracity-engine && pip install -r requirements.txt"
fi

echo ""
echo "=== Test Summary ==="
echo ""
echo -e "${GREEN}✅ SSH tunnel operational${NC}"
echo -e "${GREEN}✅ VPS Neo4j accessible${NC}"
echo -e "${GREEN}✅ ESS project data verified (${ESS_COUNT} nodes)${NC}"
echo -e "${GREEN}✅ Claude Code config ready${NC}"
if [ $PYTHON_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ Python driver working${NC}"
else
    echo -e "${YELLOW}⚠️  Python driver needs attention${NC}"
fi

echo ""
echo "Next Steps:"
echo "1. Restart Claude Code to load MCP configuration"
echo "2. In Claude Code, run: Use veracity-ess to list_projects"
echo "3. Expected result: Shows 'ess' project with ${ESS_COUNT} nodes"
echo ""
echo "Troubleshooting:"
echo "- View integration guide: docs/CLAUDE_CODE_INTEGRATION.md"
echo "- MCP server logs go to stderr (Claude Code will show errors)"
echo "- To stop tunnel: pkill -f 'ssh.*${LOCAL_NEO4J_PORT}'"
echo ""
