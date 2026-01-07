#!/bin/bash
#
# Self-Indexing Script (STORY-017)
#
# Indexes the veracity-engine repository into the knowledge graph.
# Uses deterministic settings for reproducible results.
#
# Usage:
#   ./scripts/self-index.sh           # Index with defaults
#   ./scripts/self-index.sh --dry-run # Check prerequisites only
#   ./scripts/self-index.sh --verify  # Index and verify node counts
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Canonical project name for this repo
PROJECT_NAME="veracity-engine"

# Default settings
DRY_RUN=false
VERIFY=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verify)
            VERIFY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Self-index the veracity-engine repository into the knowledge graph."
            echo ""
            echo "Options:"
            echo "  --dry-run    Check prerequisites without indexing"
            echo "  --verify     Index and verify node counts"
            echo "  -v, --verbose  Verbose output"
            echo "  -h, --help     Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Log function
log() {
    if [ "$VERBOSE" = true ] || [ "$1" = "ERROR" ] || [ "$1" = "SUCCESS" ]; then
        local level=$1
        shift
        case $level in
            INFO) echo -e "${BLUE}[INFO]${NC} $*" ;;
            SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $*" ;;
            WARN) echo -e "${YELLOW}[WARN]${NC} $*" ;;
            ERROR) echo -e "${RED}[ERROR]${NC} $*" ;;
        esac
    fi
}

# Check prerequisites
check_prerequisites() {
    log INFO "Checking prerequisites..."

    local failures=0

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log ERROR "Python 3 not found"
        ((failures++))
    else
        log INFO "Python 3: $(python3 --version)"
    fi

    # Check Neo4j connection
    if [ -n "$NEO4J_URI" ]; then
        log INFO "NEO4J_URI: $NEO4J_URI"
    else
        log WARN "NEO4J_URI not set, using default (bolt://localhost:7687)"
    fi

    # Check Ollama
    if command -v ollama &> /dev/null; then
        if ollama list &> /dev/null; then
            log INFO "Ollama: running"
        else
            log WARN "Ollama: not running or not accessible"
        fi
    else
        log WARN "Ollama CLI not found"
    fi

    # Check build_graph.py exists
    if [ -f "$PROJECT_ROOT/core/build_graph.py" ]; then
        log INFO "build_graph.py: found"
    else
        log ERROR "build_graph.py not found at $PROJECT_ROOT/core/build_graph.py"
        ((failures++))
    fi

    # Check Python dependencies
    if python3 -c "import neo4j" 2>/dev/null; then
        log INFO "neo4j package: installed"
    else
        log ERROR "neo4j package not installed"
        ((failures++))
    fi

    return $failures
}

# Run indexing
run_indexing() {
    log INFO "Starting indexing of $PROJECT_NAME..."
    log INFO "Project root: $PROJECT_ROOT"

    cd "$PROJECT_ROOT"

    # Build the command
    local cmd="python3 core/build_graph.py --project-name $PROJECT_NAME --root-dir $PROJECT_ROOT"

    if [ "$VERBOSE" = true ]; then
        echo -e "${YELLOW}Command: $cmd${NC}"
    fi

    # Execute
    if $cmd; then
        log SUCCESS "Indexing completed successfully"
        return 0
    else
        log ERROR "Indexing failed"
        return 1
    fi
}

# Verify indexing results
verify_indexing() {
    log INFO "Verifying indexing results..."

    cd "$PROJECT_ROOT"

    # Create verification script
    python3 << 'PYEOF'
import os
import sys
from neo4j import GraphDatabase

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")
project = "veracity-engine"

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Count nodes
        result = session.run(
            "MATCH (n {project: $project}) RETURN count(n) as count",
            project=project
        )
        node_count = result.single()["count"]

        # Count relationships
        result = session.run(
            "MATCH (n {project: $project})-[r]-() RETURN count(r) as count",
            project=project
        )
        edge_count = result.single()["count"]

        # Count by type
        result = session.run("""
            MATCH (n {project: $project})
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
        """, project=project)
        type_counts = {row["type"]: row["count"] for row in result}

        print(f"\n=== Verification Results for '{project}' ===")
        print(f"Total nodes: {node_count}")
        print(f"Total edges: {edge_count}")
        print("\nNodes by type:")
        for node_type, count in type_counts.items():
            print(f"  {node_type}: {count}")

        if node_count > 0:
            print(f"\n[SUCCESS] Verification passed - {node_count} nodes indexed")
            sys.exit(0)
        else:
            print("\n[ERROR] No nodes found for project")
            sys.exit(1)
    driver.close()
except Exception as e:
    print(f"[ERROR] Verification failed: {e}")
    sys.exit(1)
PYEOF
}

# Main execution
main() {
    echo -e "${BLUE}=== Veracity Engine Self-Indexing ===${NC}"
    echo ""

    # Check prerequisites
    if ! check_prerequisites; then
        log ERROR "Prerequisites check failed"
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        log SUCCESS "Dry run complete - all prerequisites satisfied"
        exit 0
    fi

    # Run indexing
    if ! run_indexing; then
        exit 1
    fi

    # Verify if requested
    if [ "$VERIFY" = true ]; then
        if ! verify_indexing; then
            exit 1
        fi
    fi

    echo ""
    log SUCCESS "Self-indexing complete for project: $PROJECT_NAME"
}

main
