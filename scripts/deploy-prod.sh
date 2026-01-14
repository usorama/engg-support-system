#!/bin/bash
#
# ESS Production Deployment Script
# Deploys Gateway + Chat UI to VPS with nginx SSL termination
#
# Usage: ./deploy-prod.sh [--build-only] [--skip-build]
#
# Prerequisites:
#   - SSH access to VPS (devuser@72.60.204.156)
#   - Docker installed on VPS
#   - nginx with certbot configured
#   - Existing infrastructure containers running (neo4j, qdrant, redis, ollama)

set -euo pipefail

# Configuration
VPS_HOST="72.60.204.156"
VPS_USER="devuser"
PROJECT_DIR="/home/devuser/Projects/engg-support-system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Parse arguments
BUILD_ONLY=false
SKIP_BUILD=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only) BUILD_ONLY=true; shift ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "              ESS Production Deployment"
echo "              Domain: https://ess.ping-gadgets.com"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# =============================================================================
# Step 1: Validate environment
# =============================================================================
log_step "1/7: Validating environment..."

if [[ ! -f "${ROOT_DIR}/.env.prod" ]]; then
    log_error ".env.prod not found. Copy .env.example to .env.prod and configure."
    exit 1
fi

# Check required variables
source "${ROOT_DIR}/.env.prod" 2>/dev/null || true
if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
    log_error "NEO4J_PASSWORD not set in .env.prod"
    exit 1
fi

log_info "Environment validated"

# =============================================================================
# Step 2: Sync code to VPS
# =============================================================================
log_step "2/7: Syncing code to VPS..."

# Ensure latest code is on VPS
ssh "${VPS_USER}@${VPS_HOST}" "cd ${PROJECT_DIR} && git fetch origin && git checkout -f main && git pull origin main" || {
    log_warn "Git sync failed, using rsync fallback..."
    rsync -avz --delete \
        --exclude='node_modules' \
        --exclude='dist' \
        --exclude='.env.local' \
        --exclude='*.log' \
        "${ROOT_DIR}/" "${VPS_USER}@${VPS_HOST}:${PROJECT_DIR}/"
}

# Copy production env file
log_info "Copying .env.prod to VPS..."
scp "${ROOT_DIR}/.env.prod" "${VPS_USER}@${VPS_HOST}:${PROJECT_DIR}/.env.prod"

log_info "Code synced to VPS"

# =============================================================================
# Step 3: Build containers on VPS
# =============================================================================
if [[ "$SKIP_BUILD" != "true" ]]; then
    log_step "3/7: Building containers on VPS..."

    ssh "${VPS_USER}@${VPS_HOST}" << 'BUILD_EOF'
set -e
cd /home/devuser/Projects/engg-support-system

# Build Gateway
echo "[BUILD] Building Gateway..."
docker build -t ess-gateway:latest -f gateway/Dockerfile gateway/

# Build Chat UI
echo "[BUILD] Building Chat UI..."
docker build -t ess-chat-ui:latest -f gateway/ui/Dockerfile gateway/ui/

echo "[BUILD] Build complete!"
docker images | grep ess-
BUILD_EOF

    log_info "Containers built"
else
    log_info "Skipping build (--skip-build)"
fi

if [[ "$BUILD_ONLY" == "true" ]]; then
    log_info "Build-only mode, stopping here"
    exit 0
fi

# =============================================================================
# Step 4: Stop existing containers
# =============================================================================
log_step "4/7: Stopping existing containers..."

ssh "${VPS_USER}@${VPS_HOST}" << 'STOP_EOF'
# Stop existing ESS containers if running
docker stop ess-gateway 2>/dev/null || true
docker rm ess-gateway 2>/dev/null || true
docker stop ess-chat-ui 2>/dev/null || true
docker rm ess-chat-ui 2>/dev/null || true

# Also stop any legacy processes
pkill -f "node dist/server.js" 2>/dev/null || true

echo "Existing containers stopped"
STOP_EOF

log_info "Containers stopped"

# =============================================================================
# Step 5: Start containers
# =============================================================================
log_step "5/7: Starting containers..."

ssh "${VPS_USER}@${VPS_HOST}" << 'START_EOF'
set -e
cd /home/devuser/Projects/engg-support-system

# Load environment
set -a
source .env.prod
set +a

# Create Docker network if not exists
docker network create ess-network 2>/dev/null || true

# Start Gateway container
# Connect to existing infrastructure on host network
echo "[START] Starting Gateway..."
docker run -d \
    --name ess-gateway \
    --restart unless-stopped \
    --network host \
    -e NODE_ENV=production \
    -e PORT=3001 \
    -e NEO4J_URI=bolt://localhost:7688 \
    -e NEO4J_USER="${NEO4J_USER:-neo4j}" \
    -e NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
    -e QDRANT_URL=http://localhost:6335 \
    -e REDIS_URL=redis://localhost:6379 \
    -e OLLAMA_URL=http://localhost:11434 \
    -e EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}" \
    -e ESS_API_KEY="${ESS_API_KEY:-}" \
    -e ADMIN_TOKEN="${ADMIN_TOKEN:-}" \
    ess-gateway:latest

# Wait for gateway to be healthy
echo "[START] Waiting for Gateway health..."
for i in {1..30}; do
    if curl -sf http://localhost:3001/health > /dev/null 2>&1; then
        echo "[START] Gateway is healthy!"
        break
    fi
    echo -n "."
    sleep 2
done

# Start Chat UI container
echo "[START] Starting Chat UI..."
docker run -d \
    --name ess-chat-ui \
    --restart unless-stopped \
    -p 3002:80 \
    ess-chat-ui:latest

# Wait for chat UI
echo "[START] Waiting for Chat UI health..."
for i in {1..15}; do
    if curl -sf http://localhost:3002/health > /dev/null 2>&1; then
        echo "[START] Chat UI is healthy!"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "Container status:"
docker ps --filter "name=ess-"
START_EOF

log_info "Containers started"

# =============================================================================
# Step 6: Update nginx configuration
# =============================================================================
log_step "6/7: Updating nginx configuration..."

scp "${ROOT_DIR}/infra/nginx-ess.ping-gadgets.com.conf" \
    "${VPS_USER}@${VPS_HOST}:/tmp/ess.ping-gadgets.com.conf"

ssh "${VPS_USER}@${VPS_HOST}" << 'NGINX_EOF'
set -e

# Backup existing config
sudo cp /etc/nginx/sites-available/ess.ping-gadgets.com \
    /etc/nginx/sites-available/ess.ping-gadgets.com.bak 2>/dev/null || true

# Install new config
sudo cp /tmp/ess.ping-gadgets.com.conf /etc/nginx/sites-available/ess.ping-gadgets.com
sudo ln -sf /etc/nginx/sites-available/ess.ping-gadgets.com /etc/nginx/sites-enabled/

# Test nginx config
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo "nginx reloaded successfully"
else
    echo "nginx config test failed, rolling back..."
    sudo cp /etc/nginx/sites-available/ess.ping-gadgets.com.bak \
        /etc/nginx/sites-available/ess.ping-gadgets.com 2>/dev/null || true
    sudo systemctl reload nginx
    exit 1
fi
NGINX_EOF

log_info "nginx updated"

# =============================================================================
# Step 7: Verify deployment
# =============================================================================
log_step "7/7: Verifying deployment..."

echo ""

# Check Gateway health
log_info "Checking Gateway health..."
if curl -sf "https://ess.ping-gadgets.com/health" | head -c 200; then
    echo ""
    log_info "Gateway health: OK"
else
    log_warn "Gateway health check failed via HTTPS, trying local..."
    ssh "${VPS_USER}@${VPS_HOST}" "curl -sf http://localhost:3001/health | head -c 200" || log_error "Gateway not responding"
fi

# Check Chat UI
log_info "Checking Chat UI..."
if curl -sf "https://ess.ping-gadgets.com/" -o /dev/null; then
    log_info "Chat UI: OK"
else
    log_warn "Chat UI check failed"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "              Deployment Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "  Chat UI:    https://ess.ping-gadgets.com/"
echo "  API:        https://ess.ping-gadgets.com/api/"
echo "  Health:     https://ess.ping-gadgets.com/health"
echo "  Metrics:    https://ess.ping-gadgets.com/metrics"
echo "  Monitoring: https://ess.ping-gadgets.com/monitoring/health"
echo ""
echo "  Container logs:"
echo "    ssh ${VPS_USER}@${VPS_HOST} docker logs -f ess-gateway"
echo "    ssh ${VPS_USER}@${VPS_HOST} docker logs -f ess-chat-ui"
echo ""
