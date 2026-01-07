#!/bin/bash
# VPS Initial Setup Script
# Run this on Hostinger VPS to prepare the environment

set -e

echo "=== Rad Engineer Knowledge Base VPS Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "Installing system dependencies..."
apt install -y \
    curl \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw

# Install Docker
echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    usermod -aG docker $USER
fi

# Install Docker Compose
echo "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Create data directories
echo "Creating data directories..."
mkdir -p /data/qdrant
mkdir -p /data/ollama
mkdir -p /data/kb

# Set permissions
chown -R 1001:1001 /data/qdrant
chown -R 1001:1001 /data/ollama
chown -R 1001:1001 /data/kb

# Configure firewall
echo "Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 6333/tcp  # Qdrant
ufw allow 11434/tcp # Ollama (optional, for local access)
ufw --force enable

# Setup SSL (placeholder - user needs to configure domain)
echo "=== SSL Certificate Setup ==="
echo "To setup SSL certificates, run:"
echo "  certbot certonly --standalone -d your-domain.com"
echo "Then copy certificates to vps/ssl/ directory"

# Create docker network
echo "Creating Docker network..."
docker network create kb-network 2>/dev/null || true

echo ""
echo "=== VPS Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Configure SSL certificates"
echo "2. Copy project files to VPS"
echo "3. Run deploy.sh to start services"
echo ""
echo "System information:"
docker --version
docker-compose --version
nginx -v
