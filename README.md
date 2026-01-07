# Engineering Support System

> **Unified Intelligence System**: Knowledge-Base (Qdrant) + Veracity-Engine (Neo4j) for Complete Codebase Understanding

A deterministic, evidence-based engineering intelligence system that provides AI agents with complete codebase understanding through hybrid vector + graph search, ground-truth validation, and unified infrastructure.

## Overview

The Engineering Support System combines two powerful technologies:

- **knowledge-base**: Qdrant-based vector search with semantic similarity
- **veracity-engine**: Neo4j-based code graph with deterministic validation

Together, they provide **triangulated truth** - cross-validated architectural context through multiple data sources.

## Key Features

- **Hybrid Search**: Vector similarity (Qdrant) + graph relationships (Neo4j)
- **Deterministic**: Evidence-based responses with veracity validation
- **Multi-Language**: Support for TypeScript, Python, Go, Rust, and more
- **MCP Integration**: Model Context Protocol for AI agent communication
- **Shared Infrastructure**: Unified Docker Compose deployment
- **Real-time Updates**: File watcher daemon for live codebase indexing

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+
- Python 3.10+
- Ollama (for local embeddings)

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/engg-support-system.git
cd engg-support-system

# Install knowledge-base
cd knowledge-base
npm install
npm run build

# Install veracity-engine
cd ../veracity-engine
pip install -r requirements.txt
```

### 2. Start Infrastructure

```bash
cd infra
docker compose up -d
```

This starts:
- Qdrant (vector database) on port 6333
- Neo4j (graph database) on ports 7474/7687
- Ollama (SLM service) on port 11434
- Redis (caching) on port 6379

### 3. Pull Ollama Models

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
ollama pull mistral-nemo
ollama pull codeqwen
```

### 4. Index Your Codebase

```bash
cd veracity-engine
python3 core/build_graph.py --project-name myproject --root-dir /path/to/code
```

### 5. Start MCP Servers

```bash
# Terminal 1: knowledge-base MCP server
cd knowledge-base
npm run start:mcp

# Terminal 2: veracity-engine MCP server
cd veracity-engine
python3 core/mcp_server.py
```

### 6. Query the System

```bash
# Semantic search (Qdrant)
cd knowledge-base
npm run query -- "authentication flow"

# Graph traversal (Neo4j)
cd veracity-engine
python3 core/ask_codebase.py --project-name myproject "What components depend on AuthService?"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Agent / Claude Code                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Unified MCP Gateway                                                         │
│  ├─ query_knowledge_base()   # Semantic search via Qdrant                  │
│  ├─ query_code_graph()       # Graph traversal via Neo4j                   │
│  ├─ hybrid_search()          # Combined vector + graph                     │
│  └─ validate_veracity()      # Ground-truth checking                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
        │ knowledge-base│  │veracity-engine│  │ Shared        │
        │   (Qdrant)    │  │   (Neo4j)     │  │ Resources     │
        ├───────────────┤  ├───────────────┤  ├───────────────┤
        │ Vector Search │  │ Graph Traversal│  │ Ollama SLMs   │
        │ MCP Server    │  │ MCP Server     │  │ Redis Cache   │
        └───────────────┘  └───────────────┘  └───────────────┘
```

## Project Structure

```
engg-support-system/
├── knowledge-base/           # Qdrant vector search system
│   ├── src/                 # TypeScript source
│   ├── config/              # Relationship schemas
│   └── package.json
├── veracity-engine/         # Neo4j graph system
│   ├── core/               # Python source
│   ├── infra/              # Docker compose for Neo4j
│   └── requirements.txt
├── infra/                   # Shared infrastructure
│   └── docker-compose.yml   # All services
├── docs/                    # Documentation
│   ├── plans/              # Integration roadmap
│   └── research/           # Research papers
├── CLAUDE.md               # System overview
└── README.md               # This file
```

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Complete system overview and development guide
- **[Integration Plan](./docs/plans/INTEGRATION_PLAN.md)** - Comprehensive integration roadmap
- **[Conversational Agent](./docs/plans/CONVERSATIONAL_AGENT_IMPLEMENTATION.md)** - Multi-agent conversation patterns
- **[Research Papers](./docs/research/)** - Industry research and analysis

## Core Principles

### "Both Together" Rule

**Every query must use BOTH databases** - no exceptions:

- Qdrant answers "what is similar?" (semantic search)
- Neo4j answers "what is connected?" (structural traversal)
- Together they provide complete, cross-validated context

### Determinism Over Flexibility

- Same query → same structure, format, limits
- Evidence-based responses with citations
- No hallucinations - if unknown, say so

### Graceful Degradation

- If Qdrant fails → use Neo4j only with warning
- If Neo4j fails → use Qdrant only with warning
- If both fail → "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH"

## Development

### Type Check

```bash
cd knowledge-base && npm run typecheck  # TypeScript
cd veracity-engine && pytest            # Python tests
```

### Build

```bash
cd knowledge-base && npm run build
```

### Lint

```bash
cd knowledge-base && npm run lint
cd veracity-engine && flake8 core/
```

## Current Status

**Version**: 0.1.0-alpha

**Completed**:
- ✅ knowledge-base: Vector search with Ollama embeddings
- ✅ veracity-engine: Graph database with Python AST parsing
- ✅ MCP servers for both systems
- ✅ Shared infrastructure (Docker Compose)
- ✅ Multi-agent conversation research

**In Progress**:
- 🚧 Unified MCP Gateway (Phase 0a)
- 🚧 Multi-language support (tree-sitter)
- 🚧 Enhanced relationship extraction
- 🚧 Redis caching layer

**See [Integration Plan](./docs/plans/INTEGRATION_PLAN.md)** for complete roadmap.

## Contributing

This project is in active development. See the [Integration Plan](./docs/plans/INTEGRATION_PLAN.md) for how to contribute.

## License

MIT License - See LICENSE file for details

## Contact

For questions or issues, please open a GitHub issue.

---

**Last Updated**: 2026-01-07
**Status**: Planning Complete, Implementation In Progress
