#!/bin/bash
# VPS Deployment Script
# Run this after setup.sh to deploy the KB stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Rad Engineer Knowledge Base Deployment ==="

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file with required variables:"
    echo "  KB_API_KEY=your-api-key-here"
    echo "  GITHUB_WEBHOOK_SECRET=your-webhook-secret"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$KB_API_KEY" ]; then
    echo -e "${RED}Error: KB_API_KEY not set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}Environment variables loaded${NC}"

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down

# Build images
echo "Building Docker images..."
docker-compose build

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."
check_health() {
    local service=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $service is healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ $service is not healthy${NC}"
        return 1
    fi
}

# Health checks
check_health "Qdrant" "http://localhost:6333/health"
check_health "Ollama" "http://localhost:11434/api/tags"
check_health "KB API" "http://localhost:3000/health"

# Pull Ollama models
echo ""
echo "Pulling Ollama models..."
docker exec kb-ollama ollama pull nomic-embed-text || echo -e "${YELLOW}Warning: Failed to pull nomic-embed-text${NC}"
docker exec kb-ollama ollama pull llama3.2 || echo -e "${YELLOW}Warning: Failed to pull llama3.2${NC}"
docker exec kb-ollama ollama pull mistral-nemo || echo -e "${YELLOW}Warning: Failed to pull mistral-nemo${NC}"

# Verify models
echo ""
echo "Verifying Ollama models..."
docker exec kb-ollama ollama list

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Services running:"
docker-compose ps
echo ""
echo "Service URLs:"
echo "  Qdrant:    http://localhost:6333"
echo "  Ollama:    http://localhost:11434"
echo "  KB API:    http://localhost:3000"
echo "  Webhook:   http://localhost:8080"
echo ""
echo "For external access, configure SSL certificates in nginx"
