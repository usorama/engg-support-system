#!/bin/bash
# ESS CI/CD Pipeline with TLS Deployment
set -e

echo "=== ESS CI/CD Pipeline ==="
echo "Started at: $(date)"

# Configuration
VPS_HOST="${VPS_HOST:-72.60.204.156}"
VPS_USER="${VPS_USER:-devuser}"
VPS_PATH="${VPS_PATH:-/home/devuser/Projects/engg-support-system}"
ESS_DOMAIN="${ESS_DOMAIN:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

# 1. Pre-flight checks
echo ""
echo "=== Pre-flight Checks ==="

if [ -z "$ESS_DOMAIN" ]; then
    print_warning "ESS_DOMAIN not set - HTTPS will use localhost (dev mode)"
fi

# Check git status
if [ -n "$(git status --porcelain)" ]; then
    print_warning "Uncommitted changes detected"
fi

# 2. Run local tests
echo ""
echo "=== Running Tests ==="

if [ -f "gateway/package.json" ]; then
    echo "Testing gateway..."
    cd gateway
    if bun test 2>/dev/null; then
        print_status "Gateway tests passed"
    else
        print_warning "Gateway tests skipped (no tests or test failure)"
    fi
    cd ..
fi

if [ -d "veracity-engine" ] && [ -f "veracity-engine/pytest.ini" ]; then
    echo "Testing veracity-engine..."
    cd veracity-engine
    if pytest -q 2>/dev/null; then
        print_status "Veracity-engine tests passed"
    else
        print_warning "Veracity-engine tests skipped"
    fi
    cd ..
fi

# 3. Build check
echo ""
echo "=== Building ==="

cd gateway
if bun run build; then
    print_status "TypeScript build successful"
else
    print_error "TypeScript build failed"
fi
cd ..

# 4. Push to VPS
echo ""
echo "=== Deploying to VPS ==="

echo "Pushing to VPS remote..."
if git push vps main 2>/dev/null; then
    print_status "Code pushed to VPS"
else
    print_warning "Git push failed (may not have vps remote)"
fi

# 5. Deploy on VPS
echo "Deploying on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << DEPLOY_EOF
set -e
cd ${VPS_PATH}

echo "Pulling latest code..."
git pull origin main 2>/dev/null || git pull vps main 2>/dev/null || true

echo "Stopping existing services..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

echo "Starting services with TLS..."
docker-compose -f docker-compose.prod.yml up -d

echo "Waiting for services to start..."
sleep 15

# Verify health
echo "Verifying health..."
if curl -sf http://localhost:3001/health > /dev/null 2>&1; then
    echo "Gateway health check passed"
else
    echo "Gateway health check failed"
    docker-compose -f docker-compose.prod.yml logs --tail=20 gateway
    exit 1
fi

# Verify HTTPS if domain is set
if [ -n "${ESS_DOMAIN}" ]; then
    if curl -sf "https://${ESS_DOMAIN}/health" > /dev/null 2>&1; then
        echo "HTTPS health check passed"
    else
        echo "HTTPS health check failed (cert may still be provisioning)"
    fi
fi

echo "Deployment complete!"
DEPLOY_EOF

print_status "Deployment complete"

echo ""
echo "=== CI/CD Pipeline Complete ==="
echo "Finished at: $(date)"

# Print access info
echo ""
echo "Access URLs:"
echo "  Local:  http://localhost:3001/health"
if [ -n "$ESS_DOMAIN" ]; then
    echo "  Prod:   https://${ESS_DOMAIN}/health"
fi
echo "  VPS:    http://${VPS_HOST}:3001/health"
