# Model Version Control

This document describes how Veracity Engine manages Ollama model versions for reproducibility.

## Current Model Versions

### Embedding Model

| Field | Value |
|-------|-------|
| Model | `nomic-embed-text` |
| Version | `latest` |
| Digest | `0a109f422b47` |
| Dimensions | 768 |
| Size | ~274 MB |

### LLM Model

| Field | Value |
|-------|-------|
| Model | `llama3.2` |
| Version | `latest` |
| Digest | `a80c4f17acd5` |
| Size | ~2 GB |

## Model Verification

### Check Model Versions

```bash
# List all Ollama models with digests
python3 scripts/verify_models.py --list

# Full verification against config
python3 scripts/verify_models.py

# With custom config file
python3 scripts/verify_models.py --config config/veracity.yaml
```

### Export Model Digests

```bash
# Export as JSON for CI/CD
python3 scripts/verify_models.py --export > model-digests.json
```

## Configuration

### Config File (config/veracity.yaml)

```yaml
embedding:
  model: "nomic-embed-text"
  version: "latest"
  digest: "0a109f422b47"  # First 12 chars or full digest
  dimensions: 768
  verify_on_startup: true

llm:
  model: "llama3.2"
  version: "latest"
  digest: "a80c4f17acd5"
  seed: 42
  temperature: 0.0
  top_k: 1
  verify_on_startup: true
```

### Environment Variables

```bash
# Embedding model
VERACITY_EMBEDDING__MODEL=nomic-embed-text
VERACITY_EMBEDDING__DIGEST=0a109f422b47
VERACITY_EMBEDDING__VERIFY_ON_STARTUP=true

# LLM model
VERACITY_LLM__MODEL=llama3.2
VERACITY_LLM__DIGEST=a80c4f17acd5
VERACITY_LLM__SEED=42
VERACITY_LLM__TEMPERATURE=0.0
```

## Determinism Guarantees

### Embedding Generation

Embeddings are deterministic by design:
- Same input text → Same embedding vector
- No randomness in forward pass
- Model version/digest ensures exact same weights

### LLM Response Generation

For deterministic LLM responses:
- `seed`: Fixed random seed (default: 42)
- `temperature`: 0.0 (greedy decoding)
- `top_k`: 1 (single token selection)

```python
# Deterministic LLM call
response = ollama.chat(
    model="llama3.2",
    messages=[{"role": "user", "content": prompt}],
    options={
        "seed": 42,
        "temperature": 0.0,
        "top_k": 1,
        "repeat_penalty": 1.1
    }
)
```

## Model Upgrade Process

### 1. Identify New Version

```bash
# Pull latest model
ollama pull nomic-embed-text

# Get new digest
ollama list
```

### 2. Update Configuration

```yaml
embedding:
  model: "nomic-embed-text"
  version: "v1.6.0"  # New version
  digest: "new_digest_here"
```

### 3. Re-index Knowledge Graph

```bash
# Force rebuild with new embeddings
python3 core/build_graph.py --project-name PROJECT --force
```

### 4. Run Verification

```bash
python3 scripts/verify_models.py
```

### 5. Test Determinism

```bash
pytest tests/test_models.py -v
```

## Model Migration Checklist

When upgrading models:

- [ ] Document old model version/digest
- [ ] Pull new model
- [ ] Record new digest
- [ ] Update configuration
- [ ] Re-run indexing with `--force`
- [ ] Run verification script
- [ ] Run determinism tests
- [ ] Update this documentation
- [ ] Commit changes with model migration note

## Troubleshooting

### Model Not Found

```
ModelNotFoundError: Model 'nomic-embed-text' not found in Ollama
```

Solution: Pull the model
```bash
ollama pull nomic-embed-text
```

### Digest Mismatch

```
[WARN] Model digest mismatch for 'nomic-embed-text'
```

This indicates the installed model differs from configuration.
Either:
1. Update config with new digest
2. Pull the specific model version

### Ollama Not Running

```
Failed to list Ollama models: Connection refused
```

Solution: Start Ollama
```bash
ollama serve
```
