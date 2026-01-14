#!/bin/bash
#
# Quick Fix Script - Run on VPS to fix critical issues
# Usage: ssh devuser@ess.ping-gadgets.com 'bash -s' < scripts/quick-fix.sh
#

set -euo pipefail

echo "========================================"
echo "ESS Quick Fix - Critical Issues"
echo "========================================"

cd /home/devuser/Projects/engg-support-system

# Fix 1: Update .env.prod with correct Neo4j password
echo "✓ Updating Neo4j password in .env.prod..."
sed -i 's/NEO4J_PASSWORD=testpassword/NEO4J_PASSWORD=password123/' .env.prod

# Fix 2: Update .env.prod with correct synthesis model
echo "✓ Updating synthesis model name..."
sed -i 's/SYNTHESIS_MODEL=glm-4.7/SYNTHESIS_MODEL=claude-sonnet-4.5/' .env.prod

# Fix 3: Pull latest code (has timeout fix + error logging)
echo "✓ Pulling latest code..."
git pull origin main

# Fix 4: Rebuild gateway
echo "✓ Rebuilding gateway..."
cd gateway
npm install --production
npm run build
cd ..

# Fix 5: Redeploy gateway container
echo "✓ Redeploying gateway..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build ess-gateway

# Wait for healthy
echo "⏳ Waiting for gateway to be healthy..."
for i in {1..30}; do
    if docker ps | grep ess-gateway | grep -q "healthy"; then
        echo "✓ Gateway is healthy"
        break
    fi
    sleep 1
done

# Verify fix
echo ""
echo "========================================"
echo "Verification"
echo "========================================"

# Check health
curl -s http://localhost:3001/health | jq -r '"Status: \(.status) | Neo4j: \(.services.neo4j) | Qdrant: \(.services.qdrant)"'

echo ""
echo "✓ Quick fixes applied!"
echo ""
echo "Next steps:"
echo "  1. Ingest Qdrant: cd knowledge-base && npm run ingest -- --project ess --root-dir /home/devuser/Projects/engg-support-system"
echo "  2. Test query: curl -X POST http://localhost:3001/api/query -H 'Content-Type: application/json' -H 'Authorization: Bearer 72774e042f90c353b9a6433f70c65b63c5efc7861046428a016e4d91e7b98a6a' -d '{\"query\":\"What is ESS?\"}' | jq"
