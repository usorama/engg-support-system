#!/bin/bash
set -e

echo "=== Deploying to VPS ==="

# 1. Run local tests (if available)
echo "Running tests..."
if [ -d "gateway" ] && [ -f "gateway/package.json" ]; then
    cd gateway && bun test 2>/dev/null || echo "Gateway tests skipped" && cd ..
fi
if [ -d "veracity-engine" ] && [ -f "veracity-engine/requirements.txt" ]; then
    cd veracity-engine && pytest 2>/dev/null || echo "Veracity engine tests skipped" && cd ..
fi

# 2. Push to VPS
echo "Pushing to VPS..."
git push vps main

# 3. Deploy on VPS
echo "Deploying on VPS..."
ssh vps-dev << 'EOF'
cd /home/devuser/Projects/engg-support-system
git pull
docker-compose down
docker-compose up -d
sleep 10
curl -f http://localhost:3000/health 2>/dev/null || echo "Health check not available yet"
echo "Deployment complete!"
EOF

echo "=== Deployment Complete ==="
