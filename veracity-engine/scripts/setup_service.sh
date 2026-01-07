#!/bin/bash

# Knowledge Graph Service Setup Script
# This script initializes the Neo4j infrastructure for the GraphRAG service.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_DIR="$SCRIPT_DIR/../infra"

echo "🚀 Initializing GraphRAG Infrastructure..."

# 1. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker and try again."
    exit 1
fi

# 2. Start Infrastructure
echo "📦 Starting Neo4j and NeoDash containers..."
cd "$INFRA_DIR"
docker compose up -d

echo "✅ Infrastructure is running!"
echo "   - Neo4j Browser: http://localhost:7474 (neo4j/password)"
echo "   - NeoDash UI: http://localhost:5005"

# 3. Instructions
echo ""
echo "📝 To index a project, run:"
echo "python3 core/build_graph.py --project-name <name> --root-dir <path>"
echo ""
echo "🔍 To query a project, run:"
echo "python3 core/ask_codebase.py --project-name <name> \"Your question\""
