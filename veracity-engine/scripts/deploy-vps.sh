#!/bin/bash
# Veracity Engine VPS Deployment Script (STORY-003)
#
# This script performs security checks and deploys Veracity Engine to a VPS.
#
# Usage:
#   ./scripts/deploy-vps.sh [--check-only] [--fix-permissions]
#
# Options:
#   --check-only       Only run security checks, don't deploy
#   --fix-permissions  Automatically fix file permissions
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file exists in infra/ directory
#   - Proper file permissions (600 for .env)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_ROOT/infra"
ENV_FILE="$INFRA_DIR/.env"

# Parse arguments
CHECK_ONLY=false
FIX_PERMISSIONS=false

for arg in "$@"; do
    case $arg in
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --fix-permissions)
            FIX_PERMISSIONS=true
            shift
            ;;
    esac
done

echo "========================================"
echo "Veracity Engine VPS Deployment"
echo "========================================"
echo ""

# Track if any checks fail
CHECKS_PASSED=true

# -----------------------------------------------------------------------------
# Security Checks
# -----------------------------------------------------------------------------

echo "Running security checks..."
echo ""

# Check 1: .env file exists
echo -n "Checking .env file exists... "
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  ERROR: $ENV_FILE does not exist"
    echo "  Run: cp $INFRA_DIR/.env.example $ENV_FILE"
    CHECKS_PASSED=false
fi

# Check 2: .env file permissions
echo -n "Checking .env file permissions... "
if [ -f "$ENV_FILE" ]; then
    PERMS=$(stat -f "%Lp" "$ENV_FILE" 2>/dev/null || stat -c "%a" "$ENV_FILE" 2>/dev/null)
    if [ "$PERMS" = "600" ]; then
        echo -e "${GREEN}PASS${NC} (mode 600)"
    else
        echo -e "${YELLOW}WARN${NC} (mode $PERMS)"
        echo "  WARNING: .env file should have permissions 600"
        if [ "$FIX_PERMISSIONS" = true ]; then
            echo "  Fixing permissions..."
            chmod 600 "$ENV_FILE"
            echo -e "  ${GREEN}Fixed!${NC}"
        else
            echo "  Run: chmod 600 $ENV_FILE"
            echo "  Or use: ./scripts/deploy-vps.sh --fix-permissions"
        fi
    fi
fi

# Check 3: No default password in .env
echo -n "Checking for default passwords... "
if [ -f "$ENV_FILE" ]; then
    if grep -qE "^NEO4J_PASSWORD=password$" "$ENV_FILE" || \
       grep -qE "^NEO4J_AUTH=neo4j/password$" "$ENV_FILE"; then
        echo -e "${RED}FAIL${NC}"
        echo "  ERROR: Default password detected in .env file"
        echo "  Please set a secure password:"
        echo "    NEO4J_PASSWORD=\$(openssl rand -base64 32)"
        CHECKS_PASSED=false
    else
        echo -e "${GREEN}PASS${NC}"
    fi
else
    echo -e "${YELLOW}SKIP${NC} (no .env file)"
fi

# Check 4: Required environment variables
echo -n "Checking required environment variables... "
if [ -f "$ENV_FILE" ]; then
    MISSING_VARS=""

    # Source the .env file
    set -a
    source "$ENV_FILE"
    set +a

    [ -z "${NEO4J_PASSWORD:-}" ] && MISSING_VARS="$MISSING_VARS NEO4J_PASSWORD"
    [ -z "${NEO4J_URI:-}" ] && MISSING_VARS="$MISSING_VARS NEO4J_URI"

    if [ -z "$MISSING_VARS" ]; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${YELLOW}WARN${NC}"
        echo "  Missing variables:$MISSING_VARS"
        echo "  Check $INFRA_DIR/.env.example for required variables"
    fi
else
    echo -e "${YELLOW}SKIP${NC} (no .env file)"
fi

# Check 5: Docker installed
echo -n "Checking Docker installation... "
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d ' ' -f 3 | tr -d ',')
    echo -e "${GREEN}PASS${NC} (v$DOCKER_VERSION)"
else
    echo -e "${RED}FAIL${NC}"
    echo "  ERROR: Docker is not installed"
    CHECKS_PASSED=false
fi

# Check 6: Docker Compose installed
echo -n "Checking Docker Compose... "
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  ERROR: Docker Compose is not installed"
    CHECKS_PASSED=false
fi

# Check 7: No secrets in git history (quick check)
echo -n "Checking git history for secrets... "
cd "$PROJECT_ROOT"
if git log -p --all -S 'password' --oneline 2>/dev/null | grep -v '.env.example' | grep -v 'STORY-' | grep -v 'test' | head -1 | grep -q .; then
    echo -e "${YELLOW}WARN${NC}"
    echo "  WARNING: Potential secrets found in git history"
    echo "  Review with: git log -p --all -S 'password'"
else
    echo -e "${GREEN}PASS${NC}"
fi

echo ""
echo "========================================"
echo "Security Check Summary"
echo "========================================"

if [ "$CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}All critical checks passed!${NC}"
else
    echo -e "${RED}Some checks failed. Please fix before deploying.${NC}"
    exit 1
fi

# Exit if check-only mode
if [ "$CHECK_ONLY" = true ]; then
    echo ""
    echo "Check-only mode. Exiting."
    exit 0
fi

echo ""

# -----------------------------------------------------------------------------
# Deployment
# -----------------------------------------------------------------------------

echo "========================================"
echo "Starting Deployment"
echo "========================================"
echo ""

cd "$INFRA_DIR"

# Pull latest images
echo "Pulling Docker images..."
docker compose pull

# Start services
echo "Starting services..."
docker compose up -d

# Wait for Neo4j to be healthy
echo "Waiting for Neo4j to be ready..."
MAX_WAIT=60
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if docker compose exec -T neo4j wget -q --spider http://localhost:7474 2>/dev/null; then
        echo -e "${GREEN}Neo4j is ready!${NC}"
        break
    fi
    COUNTER=$((COUNTER + 5))
    echo "  Waiting... ($COUNTER/$MAX_WAIT seconds)"
    sleep 5
done

if [ $COUNTER -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}WARNING: Neo4j health check timed out${NC}"
    echo "  Check logs: docker compose logs neo4j"
fi

# Show status
echo ""
echo "========================================"
echo "Deployment Complete"
echo "========================================"
echo ""
docker compose ps

echo ""
echo "Services:"
echo "  Neo4j Browser: http://localhost:7474"
echo "  Neo4j Bolt:    bolt://localhost:7687"
echo "  Veracity UI:   http://localhost:5173"
echo "  NeoDash:       http://localhost:5005"
echo ""
echo "View logs: cd infra && docker compose logs -f"
