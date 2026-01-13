#!/bin/bash
set -e

echo "=== ESS Local Environment Verification ==="
echo ""

# Check Neo4j
echo -n "Checking Neo4j... "
if curl -s -f http://localhost:7474 > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED (port 7474)"
fi

# Check Qdrant (root returns version info)
echo -n "Checking Qdrant... "
if curl -s http://localhost:6333/ 2>/dev/null | grep -q "qdrant"; then
    echo "✓ OK"
else
    echo "✗ FAILED (port 6333)"
fi

# Check Redis via Docker
echo -n "Checking Redis... "
if docker exec ess-redis-local redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✓ OK"
else
    echo "✗ FAILED (port 6380)"
fi

# Check Ollama
echo -n "Checking Ollama... "
if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED (port 11434)"
fi

# Check Ollama model
echo -n "Checking nomic-embed-text model... "
if docker exec ess-ollama-local ollama list 2>/dev/null | grep -q nomic-embed-text; then
    echo "✓ OK"
else
    echo "✗ NOT FOUND (run: docker exec ess-ollama-local ollama pull nomic-embed-text)"
fi

echo ""
echo "=== Verification Complete ==="
