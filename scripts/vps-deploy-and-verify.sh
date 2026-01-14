#!/bin/bash
#
# VPS Deployment and Verification Script
# Run this ON THE VPS as: bash scripts/vps-deploy-and-verify.sh
#
# This script:
# 1. Pulls latest code from git
# 2. Rebuilds and redeploys gateway
# 3. Ingests ESS codebase into Qdrant
# 4. Verifies all systems are operational
#

set -euo pipefail

PROJECT_ROOT="/home/devuser/Projects/engg-support-system"
LOG_FILE="$PROJECT_ROOT/logs/deployment-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $*" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $*" | tee -a "$LOG_FILE"
}

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

log "========================================="
log "ESS VPS Deployment and Verification"
log "========================================="

# Step 1: Pull latest code
log "Step 1: Pulling latest code from git..."
cd "$PROJECT_ROOT"
git fetch origin
CURRENT_COMMIT=$(git rev-parse HEAD)
LATEST_COMMIT=$(git rev-parse origin/main)

if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    warning "Already at latest commit: $CURRENT_COMMIT"
else
    log "Updating from $CURRENT_COMMIT to $LATEST_COMMIT"
    git pull origin main
    success "Code updated to $(git rev-parse --short HEAD)"
fi

# Step 2: Rebuild gateway
log "Step 2: Building gateway..."
cd "$PROJECT_ROOT/gateway"

log "Installing dependencies..."
npm install --production

log "Compiling TypeScript..."
npm run build

success "Gateway built successfully"

# Step 3: Redeploy containers
log "Step 3: Redeploying gateway container..."
cd "$PROJECT_ROOT"

log "Stopping existing gateway container..."
docker stop ess-gateway || true

log "Starting gateway with new code..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d ess-gateway

log "Waiting for gateway to be healthy..."
for i in {1..30}; do
    if docker ps | grep ess-gateway | grep -q "healthy"; then
        success "Gateway is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        error "Gateway failed to become healthy after 30 seconds"
        docker logs ess-gateway --tail 50
        exit 1
    fi
    sleep 1
done

# Step 4: Verify Neo4j connection and data
log "Step 4: Verifying Neo4j data..."
NEO4J_NODES=$(docker exec ess-neo4j cypher-shell -u neo4j -p password123 \
    "MATCH (n) WHERE n.project = 'ess' RETURN count(n) as total" --format plain | tail -1)

if [ "$NEO4J_NODES" -gt 0 ]; then
    success "Neo4j contains $NEO4J_NODES nodes for ESS project"
else
    error "Neo4j has no ESS data! Re-indexing required"
fi

# Sample file check
SAMPLE_FILE=$(docker exec ess-neo4j cypher-shell -u neo4j -p password123 \
    "MATCH (f:File) WHERE f.project = 'ess' RETURN f.path LIMIT 1" --format plain | tail -1 || echo "")

if [[ "$SAMPLE_FILE" == *"gateway"* ]] || [[ "$SAMPLE_FILE" == *"veracity-engine"* ]]; then
    success "Neo4j contains correct ESS files: $SAMPLE_FILE"
else
    warning "Neo4j may contain wrong data. Sample: $SAMPLE_FILE"
fi

# Step 5: Ingest ESS into Qdrant
log "Step 5: Ingesting ESS codebase into Qdrant..."
cd "$PROJECT_ROOT/knowledge-base"

# Check if already ingested
CURRENT_POINTS=$(curl -s http://localhost:6333/collections/ess_knowledge_base | jq -r '.result.points_count')

if [ "$CURRENT_POINTS" -gt 0 ]; then
    warning "Qdrant already has $CURRENT_POINTS points. Skipping ingestion."
    log "To force re-ingestion, manually delete and recreate the collection."
else
    log "Starting Qdrant ingestion (this may take 10-15 minutes)..."
    npm run ingest -- --project ess --root-dir "$PROJECT_ROOT" 2>&1 | tee -a "$LOG_FILE"

    FINAL_POINTS=$(curl -s http://localhost:6333/collections/ess_knowledge_base | jq -r '.result.points_count')
    success "Qdrant ingestion complete: $FINAL_POINTS points"
fi

# Step 6: Run end-to-end verification
log "Step 6: Running end-to-end verification tests..."

# Test 1: Health check
log "Test 1: Gateway health check..."
HEALTH_RESPONSE=$(curl -s http://localhost:3001/health)
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status')

if [ "$HEALTH_STATUS" = "healthy" ] || [ "$HEALTH_STATUS" = "degraded" ]; then
    success "Gateway health: $HEALTH_STATUS"
else
    error "Gateway unhealthy: $HEALTH_RESPONSE"
fi

# Test 2: Qdrant connectivity
log "Test 2: Qdrant connectivity..."
QDRANT_HEALTH=$(echo "$HEALTH_RESPONSE" | jq -r '.services.qdrant')
if [ "$QDRANT_HEALTH" = "healthy" ]; then
    success "Qdrant: $QDRANT_HEALTH"
else
    error "Qdrant: $QDRANT_HEALTH"
fi

# Test 3: Neo4j connectivity
log "Test 3: Neo4j connectivity..."
NEO4J_HEALTH=$(echo "$HEALTH_RESPONSE" | jq -r '.services.neo4j')
if [ "$NEO4J_HEALTH" = "healthy" ]; then
    success "Neo4j: $NEO4J_HEALTH"
else
    error "Neo4j: $NEO4J_HEALTH"
fi

# Test 4: End-to-end query test
log "Test 4: End-to-end query test..."
QUERY_RESPONSE=$(curl -s -X POST http://localhost:3001/api/query \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer 72774e042f90c353b9a6433f70c65b63c5efc7861046428a016e4d91e7b98a6a" \
    -d '{"query":"What is ESS?"}')

QUERY_STATUS=$(echo "$QUERY_RESPONSE" | jq -r '.status')
SEMANTIC_COUNT=$(echo "$QUERY_RESPONSE" | jq -r '.results.semantic.results | length // 0')
STRUCTURAL_COUNT=$(echo "$QUERY_RESPONSE" | jq -r '.results.structural.nodes | length // 0')

if [ "$QUERY_STATUS" = "success" ] && [ "$SEMANTIC_COUNT" -gt 0 ] && [ "$STRUCTURAL_COUNT" -gt 0 ]; then
    success "Query test PASSED"
    success "  Status: $QUERY_STATUS"
    success "  Semantic results: $SEMANTIC_COUNT"
    success "  Structural results: $STRUCTURAL_COUNT"
else
    error "Query test FAILED"
    error "  Status: $QUERY_STATUS"
    error "  Semantic results: $SEMANTIC_COUNT"
    error "  Structural results: $STRUCTURAL_COUNT"
    log "Full response: $QUERY_RESPONSE"
fi

# Step 7: Final summary
log "========================================="
log "Deployment and Verification Complete"
log "========================================="

echo ""
echo -e "${GREEN}Deployment Summary:${NC}"
echo "  Commit: $(git rev-parse --short HEAD)"
echo "  Neo4j nodes: $NEO4J_NODES"
echo "  Qdrant points: $(curl -s http://localhost:6333/collections/ess_knowledge_base | jq -r '.result.points_count')"
echo "  Gateway status: $(docker ps --filter name=ess-gateway --format '{{.Status}}')"
echo "  Health check: $HEALTH_STATUS"
echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo "  Chat UI: https://ess.ping-gadgets.com/"
echo "  API: https://ess.ping-gadgets.com/api/"
echo "  Health: https://ess.ping-gadgets.com/health"
echo ""
echo -e "${GREEN}Logs:${NC}"
echo "  Deployment log: $LOG_FILE"
echo "  Gateway logs: docker logs ess-gateway"
echo ""

success "Deployment complete! ESS Chat UI should now be fully operational."
