#!/bin/bash
# Deploy ESS Gateway to VPS with SSL
set -e

VPS_HOST="72.60.204.156"
VPS_USER="devuser"
PROJECT_DIR="/home/devuser/Projects/engg-support-system"

echo "=== ESS VPS Deployment ==="
echo ""

# 1. Sync latest code
echo "[1/6] Syncing code to VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${PROJECT_DIR} && git checkout -f"

# 2. Copy nginx config
echo "[2/6] Installing nginx config..."
scp infra/nginx-ess.ping-gadgets.com.conf ${VPS_USER}@${VPS_HOST}:/tmp/
ssh ${VPS_USER}@${VPS_HOST} "sudo cp /tmp/nginx-ess.ping-gadgets.com.conf /etc/nginx/sites-available/ess.ping-gadgets.com"
ssh ${VPS_USER}@${VPS_HOST} "sudo ln -sf /etc/nginx/sites-available/ess.ping-gadgets.com /etc/nginx/sites-enabled/"

# 3. Get SSL cert (if not exists)
echo "[3/6] Checking SSL certificate..."
ssh ${VPS_USER}@${VPS_HOST} << 'CERT_EOF'
if [ ! -d "/etc/letsencrypt/live/ess.ping-gadgets.com" ]; then
    echo "Getting SSL certificate..."
    sudo certbot certonly --nginx -d ess.ping-gadgets.com --non-interactive --agree-tos -m admin@ping-gadgets.com || {
        echo "Certbot failed, trying standalone..."
        sudo systemctl stop nginx
        sudo certbot certonly --standalone -d ess.ping-gadgets.com --non-interactive --agree-tos -m admin@ping-gadgets.com
        sudo systemctl start nginx
    }
else
    echo "SSL certificate already exists"
fi
CERT_EOF

# 4. Test nginx config and reload
echo "[4/6] Reloading nginx..."
ssh ${VPS_USER}@${VPS_HOST} "sudo nginx -t && sudo systemctl reload nginx"

# 5. Install gateway dependencies and build
echo "[5/6] Building gateway..."
ssh ${VPS_USER}@${VPS_HOST} << 'BUILD_EOF'
cd /home/devuser/Projects/engg-support-system/gateway
export PATH="$HOME/.bun/bin:$PATH"
bun install
bun run build
BUILD_EOF

# 6. Start gateway with PM2 or systemd
echo "[6/6] Starting gateway service..."
ssh ${VPS_USER}@${VPS_HOST} << 'START_EOF'
cd /home/devuser/Projects/engg-support-system/gateway
export PATH="$HOME/.bun/bin:$PATH"

# Load production env
set -a
source ../.env.prod
set +a

# Kill existing if running
pkill -f "node dist/server.js" 2>/dev/null || true

# Start with nohup (or use PM2 if available)
nohup node dist/server.js > /tmp/ess-gateway.log 2>&1 &
echo "Gateway started with PID $!"

sleep 3
curl -sf http://localhost:3001/health && echo "Gateway health OK" || echo "Gateway health FAILED"
START_EOF

echo ""
echo "=== Deployment Complete ==="
echo "Test: https://ess.ping-gadgets.com/health"
