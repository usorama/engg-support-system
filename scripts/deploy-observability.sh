#!/bin/bash
# Deploy ESS Observability Stack
# Usage: ./scripts/deploy-observability.sh [--prod]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
PRODUCTION=false
for arg in "$@"; do
    case $arg in
        --prod|--production)
            PRODUCTION=true
            shift
            ;;
    esac
done

cd "$PROJECT_DIR"

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose is not installed"
    exit 1
fi

# Verify configuration files exist
log_info "Verifying configuration files..."

REQUIRED_FILES=(
    "infra/prometheus/prometheus.yml"
    "infra/loki/loki-config.yml"
    "infra/promtail/promtail-config.yml"
    "infra/alertmanager/alertmanager.yml"
    "infra/grafana/provisioning/datasources/datasources.yml"
    "observability-manifest.yaml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        log_error "Missing required file: $file"
        exit 1
    fi
done

log_info "All configuration files present"

# Select compose files
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.observability.yml"

if [[ "$PRODUCTION" == true ]]; then
    log_info "Production mode: using docker-compose.prod.yml"
    COMPOSE_FILES="-f docker-compose.prod.yml -f docker-compose.observability.yml"
fi

# Pull latest images
log_info "Pulling latest images..."
docker compose $COMPOSE_FILES pull prometheus grafana loki promtail alertmanager

# Deploy observability stack
log_info "Deploying observability stack..."
docker compose $COMPOSE_FILES up -d prometheus grafana loki promtail alertmanager

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."

wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "$service is healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done

    log_error "$service failed to become healthy after $max_attempts attempts"
    return 1
}

echo -n "Waiting for Prometheus"
wait_for_service "Prometheus" "http://localhost:9090/-/healthy"

echo -n "Waiting for Loki"
wait_for_service "Loki" "http://localhost:3100/ready"

echo -n "Waiting for Grafana"
wait_for_service "Grafana" "http://localhost:3003/api/health"

echo -n "Waiting for Alertmanager"
wait_for_service "Alertmanager" "http://localhost:9093/-/healthy"

# Verify metrics are being scraped
log_info "Verifying Prometheus targets..."
sleep 5

TARGETS_UP=$(curl -sf "http://localhost:9090/api/v1/targets" | grep -c '"health":"up"' || echo "0")
log_info "Prometheus has $TARGETS_UP healthy targets"

# Summary
echo ""
log_info "========================================="
log_info "ESS Observability Stack Deployed"
log_info "========================================="
echo ""
log_info "Services:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana:    http://localhost:3003 (admin/admin)"
echo "  - Loki:       http://localhost:3100"
echo "  - Alertmanager: http://localhost:9093"
echo ""
log_info "Retention: 8 days for metrics and logs"
echo ""

if [[ "$PRODUCTION" == true ]]; then
    log_warn "Production mode - ensure .env.prod is properly configured"
fi

log_info "Deployment complete!"
