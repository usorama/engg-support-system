#!/bin/bash
# Veracity Engine Health Check Script (STORY-005)
#
# Checks health of all runtime dependencies:
# - Neo4j database
# - Ollama LLM service
# - System resources (disk, memory)
#
# Usage:
#   ./scripts/health-check.sh [--json] [--quiet]
#
# Exit codes:
#   0 - All healthy
#   1 - Warning (some degraded)
#   2 - Error (critical failure)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Exit codes
EXIT_OK=0
EXIT_WARNING=1
EXIT_ERROR=2

# Parse arguments
JSON_OUTPUT=false
QUIET=false
for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --quiet) QUIET=true ;;
    esac
done

# Accumulate status
OVERALL_STATUS=0

# Individual check results (bash 3.x compatible - no associative arrays)
NEO4J_STATUS="unknown"
NEO4J_LATENCY=""
OLLAMA_STATUS="unknown"
OLLAMA_NOMIC="unknown"
OLLAMA_LLAMA32="unknown"
DISK_STATUS="unknown"
DISK_FREE_GB="0"
MEMORY_STATUS="unknown"
MEMORY_FREE_GB="0"
DOCKER_NEO4J="unknown"
DOCKER_UI="unknown"

log() {
    if [ "$QUIET" = false ] && [ "$JSON_OUTPUT" = false ]; then
        echo -e "$@"
    fi
}

# Check Neo4j
check_neo4j() {
    log -n "Checking Neo4j... "

    NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
    NEO4J_USER="${NEO4J_USER:-neo4j}"
    NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"

    # Check if Neo4j is reachable
    START_TIME=$(python3 -c "import time; print(int(time.time() * 1000))" 2>/dev/null || echo "0")

    if python3 -c "
from neo4j import GraphDatabase
import sys
try:
    driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD'))
    driver.verify_connectivity()
    driver.close()
    sys.exit(0)
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
        END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))" 2>/dev/null || echo "0")
        NEO4J_LATENCY=$(( END_TIME - START_TIME ))
        NEO4J_STATUS="healthy"
        log "${GREEN}OK${NC} (${NEO4J_LATENCY}ms)"
    else
        NEO4J_STATUS="unhealthy"
        log "${RED}FAILED${NC}"
        OVERALL_STATUS=$EXIT_ERROR
    fi
}

# Check Ollama
check_ollama() {
    log -n "Checking Ollama... "

    OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

    # Check if Ollama API is reachable
    if curl -s --max-time 5 "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
        OLLAMA_STATUS="healthy"
        log "${GREEN}OK${NC}"

        # Check required models
        log "  Checking models..."

        # Check nomic-embed-text
        if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
            OLLAMA_NOMIC="available"
            log "  - nomic-embed-text: ${GREEN}OK${NC}"
        else
            OLLAMA_NOMIC="missing"
            log "  - nomic-embed-text: ${YELLOW}MISSING${NC}"
            if [ $OVERALL_STATUS -lt $EXIT_WARNING ]; then
                OVERALL_STATUS=$EXIT_WARNING
            fi
        fi

        # Check llama3.2
        if ollama list 2>/dev/null | grep -q "llama3.2"; then
            OLLAMA_LLAMA32="available"
            log "  - llama3.2: ${GREEN}OK${NC}"
        else
            OLLAMA_LLAMA32="missing"
            log "  - llama3.2: ${YELLOW}MISSING${NC}"
            if [ $OVERALL_STATUS -lt $EXIT_WARNING ]; then
                OVERALL_STATUS=$EXIT_WARNING
            fi
        fi
    else
        OLLAMA_STATUS="unhealthy"
        log "${RED}FAILED${NC}"
        OVERALL_STATUS=$EXIT_ERROR
    fi
}

# Check system resources
check_resources() {
    log "Checking system resources..."

    # Check disk space (need at least 5GB free)
    # Cross-platform: Linux uses -BG, macOS uses different format
    if df -BG / >/dev/null 2>&1; then
        # Linux with GNU coreutils
        DISK_FREE_GB=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
    else
        # macOS - df -g shows GB
        DISK_FREE_GB=$(df -g / | awk 'NR==2 {print $4}')
    fi

    if [ -n "$DISK_FREE_GB" ] && [ "$DISK_FREE_GB" -ge 5 ] 2>/dev/null; then
        DISK_STATUS="healthy"
        log "  - Disk space: ${GREEN}OK${NC} (${DISK_FREE_GB}GB free)"
    elif [ -n "$DISK_FREE_GB" ] && [ "$DISK_FREE_GB" -gt 0 ] 2>/dev/null; then
        DISK_STATUS="warning"
        log "  - Disk space: ${YELLOW}LOW${NC} (${DISK_FREE_GB}GB free, need 5GB+)"
        if [ $OVERALL_STATUS -lt $EXIT_WARNING ]; then
            OVERALL_STATUS=$EXIT_WARNING
        fi
    else
        DISK_STATUS="unknown"
        DISK_FREE_GB="0"
        log "  - Disk space: ${YELLOW}UNKNOWN${NC}"
    fi

    # Check memory (need at least 2GB free)
    if command -v free &> /dev/null; then
        # Linux
        MEMORY_FREE_GB=$(free -g | awk '/^Mem:/ {print $7}')
    else
        # macOS - calculate from vm_stat (pages free * page size)
        PAGE_FREE=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub(/\./,"",$3); print $3}')
        if [ -n "$PAGE_FREE" ]; then
            MEMORY_FREE_GB=$(( PAGE_FREE * 4096 / 1024 / 1024 / 1024 ))
        else
            MEMORY_FREE_GB="0"
        fi
    fi

    if [ -n "$MEMORY_FREE_GB" ] && [ "$MEMORY_FREE_GB" -ge 2 ] 2>/dev/null; then
        MEMORY_STATUS="healthy"
        log "  - Memory: ${GREEN}OK${NC} (${MEMORY_FREE_GB}GB free)"
    elif [ -n "$MEMORY_FREE_GB" ]; then
        MEMORY_STATUS="warning"
        log "  - Memory: ${YELLOW}LOW${NC} (${MEMORY_FREE_GB}GB free, need 2GB+)"
        if [ $OVERALL_STATUS -lt $EXIT_WARNING ]; then
            OVERALL_STATUS=$EXIT_WARNING
        fi
    else
        MEMORY_STATUS="unknown"
        MEMORY_FREE_GB="0"
        log "  - Memory: ${YELLOW}UNKNOWN${NC}"
    fi
}

# Check Docker services
check_docker() {
    log "Checking Docker services..."

    if ! command -v docker &> /dev/null; then
        DOCKER_NEO4J="not_installed"
        DOCKER_UI="not_installed"
        log "  - Docker: ${YELLOW}NOT INSTALLED${NC}"
        return
    fi

    # Check if Neo4j container is running
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "graphrag_neo4j"; then
        DOCKER_NEO4J="running"
        log "  - Neo4j container: ${GREEN}RUNNING${NC}"
    else
        DOCKER_NEO4J="stopped"
        log "  - Neo4j container: ${YELLOW}STOPPED${NC}"
    fi

    # Check if UI container is running
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "graphrag_ui"; then
        DOCKER_UI="running"
        log "  - UI container: ${GREEN}RUNNING${NC}"
    else
        DOCKER_UI="stopped"
        log "  - UI container: ${YELLOW}STOPPED${NC}"
    fi
}

# Output JSON
output_json() {
    # Determine overall status string
    if [ $OVERALL_STATUS -eq 0 ]; then
        STATUS_STR="healthy"
    elif [ $OVERALL_STATUS -eq 1 ]; then
        STATUS_STR="degraded"
    else
        STATUS_STR="unhealthy"
    fi

    # Format latency (null if empty)
    if [ -n "$NEO4J_LATENCY" ]; then
        LATENCY_JSON="$NEO4J_LATENCY"
    else
        LATENCY_JSON="null"
    fi

    cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "overall_status": "$STATUS_STR",
  "neo4j": {
    "status": "$NEO4J_STATUS",
    "latency_ms": $LATENCY_JSON
  },
  "ollama": {
    "status": "$OLLAMA_STATUS",
    "nomic-embed-text": "$OLLAMA_NOMIC",
    "llama3.2": "$OLLAMA_LLAMA32"
  },
  "resources": {
    "disk": {
      "status": "$DISK_STATUS",
      "free_gb": $DISK_FREE_GB
    },
    "memory": {
      "status": "$MEMORY_STATUS",
      "free_gb": $MEMORY_FREE_GB
    }
  },
  "docker": {
    "neo4j": "$DOCKER_NEO4J",
    "ui": "$DOCKER_UI"
  }
}
EOF
}

# Main
main() {
    if [ "$JSON_OUTPUT" = false ] && [ "$QUIET" = false ]; then
        echo "========================================"
        echo "Veracity Engine Health Check"
        echo "========================================"
        echo ""
    fi

    check_neo4j
    check_ollama
    check_resources
    check_docker

    if [ "$JSON_OUTPUT" = true ]; then
        output_json
    else
        echo ""
        echo "========================================"
        echo "Summary"
        echo "========================================"

        if [ $OVERALL_STATUS -eq 0 ]; then
            echo -e "Overall: ${GREEN}HEALTHY${NC}"
        elif [ $OVERALL_STATUS -eq 1 ]; then
            echo -e "Overall: ${YELLOW}DEGRADED${NC}"
        else
            echo -e "Overall: ${RED}UNHEALTHY${NC}"
        fi
    fi

    exit $OVERALL_STATUS
}

main
