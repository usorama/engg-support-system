# Knowledge Graph System for Rad Engineer v2

> Production-ready Knowledge Graph system with VPS deployment, Ollama SLMs, and MCP server integration.

## Overview

This system provides:

- **VPS-Deployed**: Complete KB system + MCP server on Hostinger VPS
- **Local Ollama SLMs**: Embeddings + evidence-based summarization (NOT OpenAI)
- **Knowledge Graph**: Rich relationships (dependencies, hierarchies, temporal) in Qdrant
- **MCP Server API**: REST/WebSocket for agents to query KB
- **Claude SDK Integration**: Local agents query VPS KB deterministically

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HOSTINGER VPS (Cloud)                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Docker Compose Stack                     │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│  │  │   Qdrant     │  │  KB API      │  │   Ollama     │      │ │
│  │  │  (Vector +   │  │  (MCP +      │  │  (SLMs for   │      │ │
│  │  │   Graph)     │  │   REST)      │  │  embed/sum)  │      │ │
│  │  │  Port: 6333  │  │  Port: 3000  │  │  Port: 11434 │      │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS / SSH
                              │ MCP Protocol
                              │
┌─────────────────────────────┴─────────────────────────────────────┐
│                    LOCAL MACHINE (rad-engineer)                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                     Claude Code + Agents                     │ │
│  │                                                              │ │
│  │  Queries VPS KB via MCP Client                                │ │
│  │  ├→ SSH tunnel for long-running tasks                        │ │
│  │  ├→ Direct API for quick queries                             │ │
│  │  └→ Local Ollama fallback (when VPS down)                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. VPS Setup (Phase 0 - MUST BE FIRST)

```bash
# SSH into Hostinger VPS
ssh root@your-vps-ip

# Clone repository
git clone https://github.com/your-repo/rad-engineer-v2.git
cd rad-engineer-v2/knowledge-base/vps

# Run setup script
chmod +x setup.sh
sudo ./setup.sh

# Configure environment
cp ../.env.example ../.env
nano ../.env  # Add your API keys

# Deploy
chmod +x deploy.sh
./deploy.sh
```

### 2. Local Development

```bash
# Install dependencies
cd knowledge-base
npm install

# Build TypeScript
npm run build

# Run MCP server locally
npm run start:mcp

# Or run webhook server
npm run start:webhook
```

### 3. Ingest Claude Code Documentation

```bash
# Incremental update (only processes changed docs)
npm run ingest:docs

# Force re-ingestion of all docs
npm run ingest:docs:force

# Dry run (preview what would change)
npm run ingest:docs:dry

# Verbose mode (detailed logging)
npm run ingest:docs:verbose
```

**Features**:
- Dynamic content fetching from code.claude.com
- Incremental updates (only processes changed docs using SHA-256 hashing)
- State tracking for resume capability
- 48 documentation pages across 10 categories
- Error handling and retry logic

**Registry**: `scripts/claude-docs-registry.json` - Add/remove docs here
**State**: `scripts/ingestion-state.json` - Tracks processed docs and changes

## Configuration

### Environment Variables

```bash
# KB API Configuration
KB_API_KEY=your-secure-api-key-here

# GitHub Webhook Configuration
GITHUB_WEBHOOK_SECRET=whsec_your-webhook-secret-here

# VPS Configuration
VPS_HOST=your-vps-domain.com
QDRANT_URL=http://localhost:6333
OLLAMA_URL=http://localhost:11434

# OpenAI Fallback (emergency only)
OPENAI_API_KEY=sk-your-openai-key-here
```

### Knowledge Graph Schema

See `config/relationships.schema.yaml` for all relationship types:

- Document: `REFERENCES`, `RELATED_TO`, `EXTENDS`, `SUPERSEDES`
- Code: `DEPENDS_ON`, `IMPLEMENTS`, `EXTENDS_CLASS`, `CALLS`
- Temporal: `PRECEDES`, `FOLLOWS`
- Concept: `CONCEPT_RELATES`, `CONCEPT_SIMILAR`

## API Endpoints

### MCP Server (Port 3000)

```
POST /mcp/query      - Query knowledge graph
POST /mcp/ingest     - Ingest documents
GET  /mcp/stats      - Get statistics
GET  /health         - Health check
```

### Query Example

```bash
curl -X POST http://localhost:3000/mcp/query \
  -H "Authorization: Bearer $KB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to use tool use in Claude SDK?",
    "collection": "claude-sdk-docs",
    "topK": 5
  }'
```

## Development

### Project Structure

```
knowledge-base/
├── src/
│   ├── core/              # Core KB orchestrators
│   ├── ingestion/         # Content ingestion pipeline
│   ├── retrieval/         # Query and retrieval
│   ├── cache/             # Hybrid caching layer
│   ├── mcp/               # MCP Server
│   ├── agents/            # Agent integration
│   └── utils/             # Utilities
├── vps/                   # VPS deployment files
├── config/                # Configuration files
├── scripts/               # Setup and deployment scripts
└── test/                  # Tests
```

### Testing

```bash
# Run all tests
npm test

# Unit tests only
npm run test:unit

# Integration tests
npm run test:integration

# Chaos tests
npm run test:chaos
```

### Build

```bash
# Type check
npm run typecheck

# Build
npm run build

# Lint
npm run lint
```

## Knowledge Graph Features

### Hybrid Storage

- **Qdrant (VPS)**: Primary storage with full knowledge graph
- **LanceDB (Local)**: Hot cache for frequently accessed documents
- **Temperature-based**: Auto-promotion/demotion based on access patterns

### Evidence-Based Summarization

- Uses Ollama SLMs (llama3.2, mistral-nemo)
- Mandatory citations from retrieved chunks
- Deterministic results (low temperature)

### 3-Tier Fallback

1. Local LanceDB cache (<10ms)
2. Cloud Qdrant (~100-500ms)
3. Web search (agent-based, ~24h cache)

## Cost

- **Hostinger VPS**: ~$5-10/month
- **Qdrant**: Self-hosted (free)
- **Ollama SLMs**: Self-hosted (free)
- **OpenAI**: Emergency fallback only (minimal usage)

**Total**: $5-10/month

## License

MIT
