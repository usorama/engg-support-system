# Configuration Guide

This document describes how to configure Veracity Engine for different deployment scenarios.

## Configuration Hierarchy

Veracity Engine uses a hierarchical configuration system with the following precedence (highest to lowest):

1. **CLI Arguments** - Command-line arguments passed to scripts
2. **Environment Variables** - `VERACITY_*` prefixed variables (new format)
3. **Legacy Environment Variables** - `NEO4J_*`, `EMBED_MODEL`, `LLM_MODEL` (backward compatible)
4. **Configuration File** - YAML file specified via `--config` flag
5. **Default Values** - Built into the application

Higher priority sources override lower priority ones.

## Quick Start

### Option 1: Environment Variables (Recommended for Production)

```bash
# Copy the example environment file
cp infra/.env.example infra/.env

# Edit with your credentials
vim infra/.env

# Run with Docker Compose
cd infra && docker compose up -d
```

### Option 2: Configuration File (Recommended for Development)

```bash
# Copy the example config
cp config/veracity.example.yaml config/veracity.yaml

# Edit with your settings
vim config/veracity.yaml

# Run with config file
python3 core/build_graph.py --config config/veracity.yaml --project-name myproject --root-dir .
```

### Option 3: CLI Arguments Only

```bash
# All defaults are used, Neo4j must be accessible at bolt://localhost:7687
python3 core/build_graph.py --project-name myproject --root-dir .
```

## Configuration Options

### Neo4j Database

| Option | Environment Variable | Config Key | Default |
|--------|---------------------|------------|---------|
| URI | `NEO4J_URI` or `VERACITY_NEO4J__URI` | `neo4j.uri` | `bolt://localhost:7687` |
| User | `NEO4J_USER` or `VERACITY_NEO4J__USER` | `neo4j.user` | `neo4j` |
| Password | `NEO4J_PASSWORD` or `VERACITY_NEO4J__PASSWORD` | `neo4j.password` | `password` |
| Pool Size | `VERACITY_NEO4J__POOL_SIZE` | `neo4j.pool_size` | `50` |

### Embedding Model

| Option | Environment Variable | Config Key | Default |
|--------|---------------------|------------|---------|
| Model | `EMBED_MODEL` or `VERACITY_EMBEDDING__MODEL` | `embedding.model` | `nomic-embed-text` |
| Version | `VERACITY_EMBEDDING__VERSION` | `embedding.version` | `null` |
| Batch Size | `VERACITY_EMBEDDING__BATCH_SIZE` | `embedding.batch_size` | `32` |
| Document Prefix | `VERACITY_EMBEDDING__DOCUMENT_PREFIX` | `embedding.document_prefix` | `search_document:` |
| Query Prefix | `VERACITY_EMBEDDING__QUERY_PREFIX` | `embedding.query_prefix` | `search_query:` |

### LLM (Large Language Model)

| Option | Environment Variable | Config Key | Default |
|--------|---------------------|------------|---------|
| Model | `LLM_MODEL` or `VERACITY_LLM__MODEL` | `llm.model` | `llama3.2` |
| Version | `VERACITY_LLM__VERSION` | `llm.version` | `null` |
| Seed | `LLM_SEED` or `VERACITY_LLM__SEED` | `llm.seed` | `42` |
| Temperature | `VERACITY_LLM__TEMPERATURE` | `llm.temperature` | `0.0` |
| Repeat Penalty | `VERACITY_LLM__REPEAT_PENALTY` | `llm.repeat_penalty` | `1.1` |

### Logging

| Option | Environment Variable | Config Key | Default |
|--------|---------------------|------------|---------|
| Level | `VERACITY_LOGGING__LEVEL` | `logging.level` | `INFO` |
| Format | `VERACITY_LOGGING__FORMAT` | `logging.format` | `%(asctime)s - %(levelname)s - %(message)s` |

Valid log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Project

| Option | Environment Variable | Config Key | Default |
|--------|---------------------|------------|---------|
| Name | `VERACITY_PROJECT__NAME` | `project.name` | `null` |
| Root Dir | `VERACITY_PROJECT__ROOT_DIR` | `project.root_dir` | `null` |
| Target Dirs | `VERACITY_PROJECT__TARGET_DIRS` | `project.target_dirs` | See below |

Default target directories:
```yaml
target_dirs:
  - services
  - models
  - scripts
  - docs
  - core
  - api
  - lib
  - src
```

## Configuration File Format

Configuration files use YAML format. See `config/veracity.example.yaml` for a complete example.

```yaml
# config/veracity.yaml
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "your_password"

embedding:
  model: "nomic-embed-text"
  batch_size: 32

llm:
  model: "llama3.2"
  seed: 42
  temperature: 0.0

logging:
  level: "INFO"
```

## Environment Variable Naming

The new `VERACITY_*` prefix format uses double underscores (`__`) as nested delimiters:

```bash
# Format: VERACITY_{SECTION}__{KEY}
VERACITY_NEO4J__URI=bolt://localhost:7687
VERACITY_NEO4J__USER=neo4j
VERACITY_EMBEDDING__MODEL=nomic-embed-text
VERACITY_LOGGING__LEVEL=DEBUG
```

## Security Best Practices

1. **Never commit credentials** - Use `.env` files (gitignored) or environment variables
2. **Secrets are masked** - Passwords are stored as `SecretStr` and masked in logs
3. **Use environment variables in production** - Don't store credentials in config files
4. **Rotate credentials regularly** - Especially for production Neo4j instances

## Docker Compose Configuration

The `infra/docker-compose.yml` reads from `infra/.env`:

```bash
cd infra
cp .env.example .env
# Edit .env with your credentials
docker compose up -d
```

## Programmatic Access

```python
from core.config import ConfigLoader, get_config

# Load with defaults
config = ConfigLoader.load()

# Load with config file
config = ConfigLoader.load(config_file="config/veracity.yaml")

# Load with CLI overrides
config = ConfigLoader.load(neo4j_uri="bolt://custom:7687")

# Get singleton instance
config = get_config()

# Access configuration values
print(config.neo4j.uri)
print(config.embedding.model)
print(config.neo4j.password.get_secret_value())  # Access secret
```

## Troubleshooting

### Configuration Not Loading

1. Check file path is correct: `--config path/to/config.yaml`
2. Verify YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"`
3. Check environment variable names use `__` delimiter

### Environment Variables Not Working

1. Verify prefix: `VERACITY_` (new format) or legacy names
2. Check case sensitivity (environment variables are case-insensitive in config)
3. Export variables: `export VERACITY_NEO4J__URI=bolt://host:7687`

### Validation Errors

Configuration is validated on load. Common errors:

- Invalid log level: Must be `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`
- Invalid URL format: Neo4j URI must be valid URL format
- Type mismatches: Numbers must be valid integers/floats

## Migration Guide

### From Hardcoded Values

If you previously modified source files directly:

1. Create `config/veracity.yaml` with your settings
2. Remove any hardcoded changes from source files
3. Run with `--config config/veracity.yaml`

### From Legacy Environment Variables

Legacy variables (`NEO4J_*`, `EMBED_MODEL`, `LLM_MODEL`) still work:

```bash
# These continue to work
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
export EMBED_MODEL=nomic-embed-text
export LLM_MODEL=llama3.2
```

New `VERACITY_*` format takes precedence if both are set.
