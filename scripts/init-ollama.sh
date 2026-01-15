#!/bin/bash
# init-ollama.sh - Initialize Ollama with required models
# Run this script after Ollama container starts to pull required models

set -e

OLLAMA_HOST="${OLLAMA_HOST:-localhost:11434}"

echo "=== ESS Ollama Model Initialization ==="
echo "Ollama host: $OLLAMA_HOST"
echo ""

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
max_retries=30
retry_count=0
while ! curl -sf "http://${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "ERROR: Ollama did not become ready after ${max_retries} retries"
        exit 1
    fi
    echo "  Waiting... (attempt $retry_count/$max_retries)"
    sleep 2
done
echo "Ollama is ready!"
echo ""

# Required models for ESS
MODELS=(
    "nomic-embed-text"   # Required: Embedding generation (768 dimensions)
    "llama3.2"           # Required: Default synthesis model
)

# Optional models (pull if resources allow)
OPTIONAL_MODELS=(
    "mistral-nemo"       # Optional: Code understanding
    "codeqwen"           # Optional: Advanced code analysis
)

echo "=== Pulling Required Models ==="
for model in "${MODELS[@]}"; do
    echo "Checking model: $model"
    if curl -sf "http://${OLLAMA_HOST}/api/show" -d "{\"name\":\"$model\"}" > /dev/null 2>&1; then
        echo "  Model $model already exists"
    else
        echo "  Pulling $model..."
        if ollama pull "$model"; then
            echo "  Successfully pulled $model"
        else
            echo "ERROR: Failed to pull required model: $model"
            exit 1
        fi
    fi
done
echo ""

echo "=== Pulling Optional Models (best effort) ==="
for model in "${OPTIONAL_MODELS[@]}"; do
    echo "Checking model: $model"
    if curl -sf "http://${OLLAMA_HOST}/api/show" -d "{\"name\":\"$model\"}" > /dev/null 2>&1; then
        echo "  Model $model already exists"
    else
        echo "  Pulling $model (optional)..."
        if ollama pull "$model"; then
            echo "  Successfully pulled $model"
        else
            echo "  WARNING: Failed to pull optional model: $model (continuing)"
        fi
    fi
done
echo ""

echo "=== Model Status ==="
ollama list

echo ""
echo "=== Ollama Initialization Complete ==="
echo "ESS is ready to use embeddings and synthesis!"
