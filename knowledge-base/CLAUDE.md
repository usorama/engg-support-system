# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Knowledge Graph system for rad-engineer-v2 with VPS deployment, Ollama SLMs, and MCP server integration. It provides a production-ready KB system with local SLMs (NOT OpenAI), vector + graph storage in Qdrant, and MCP server API for agents.

**Architecture**: VPS-deployed (Hostinger) with Qdrant + Ollama containers, accessible via MCP REST/WebSocket API. Local agents query VPS KB deterministically with Ollama fallback.

## Development Commands

### Build & Type Check
```bash
npm run build           # Compile TypeScript to dist/
npm run typecheck       # Type check without emitting files
npm run dev            # Watch mode for development
```

### Running the Server
```bash
npm run start:mcp      # Start MCP server (port 3000)
npm run start:webhook  # Start GitHub webhook server
npm start              # Start main entry point
```

### Testing
```bash
npm test               # Run all tests with Bun
npm run test:unit      # Unit tests only
npm run test:integration  # Integration tests
npm run test:chaos     # Chaos/resilience tests
```

### Code Quality
```bash
npm run lint           # ESLint check
npm run format         # Prettier format
```

### Data Operations
```bash
npm run ingest:docs           # Incremental ingestion (only changed docs)
npm run ingest:docs:force     # Force re-ingest all docs
npm run ingest:docs:dry       # Preview what would change
npm run ingest:docs:verbose   # Verbose logging
npm run migrate:learnings     # Migrate learning data
```

**Ingestion System Details**:
- Main script: `scripts/ingest-sdk-docs.js`
- Docs registry: `scripts/claude-docs-registry.json` (48 docs)
- State tracking: `scripts/ingestion-state.json` (SHA-256 hashes)
- Features: Dynamic fetching, incremental updates, error handling

### VPS Deployment
```bash
npm run setup:vps      # Run VPS setup script
npm run deploy:vps     # Deploy to VPS
```

## Architecture Overview

### Core Components (src/core/)

**KnowledgeBase.ts**: Main orchestrator that coordinates all KB operations:
- `initialize()`: Creates Qdrant collection if not exists
- `query(request)`: Semantic search with optional summarization
- `ingest(documents)`: Ingest documents with embeddings
- `getStats()`: Collection statistics
- `healthCheck()`: Service health status

**QdrantProvider**: Vector + graph storage client for Qdrant:
- Uses @qdrant/js-client-rest
- Vector size: 768 (nomic-embed-text)
- Distance: Cosine
- Stores relationships in payload (not as edges)
- Requires UUID v4 for point IDs (use `crypto.randomUUID()`)

**FallbackManager**: Multi-provider orchestration with fallback chain:
- Priority: Ollama VPS → Ollama local → OpenAI (emergency)
- Fallback triggers: timeout, container_down, retry_exceeded, model_not_found
- Tracks attempt history and metrics

**OllamaEmbeddingProvider**: Embeddings via Ollama API
- Default model: nomic-embed-text (768 dimensions)
- Health check: GET /api/tags

**OllamaSummarizer**: Evidence-based summarization with citations
- Default model: llama3.2 or mistral-nemo
- Low temperature (0.3) for deterministic results
- Mandatory citations from retrieved chunks

### Type System (src/core/types.ts, src/types.ts)

Key types:
- `KGNode`: Knowledge graph node with vector, relationships, metadata
- `SearchRequest`: Query with filters, topK, minScore
- `SearchResult`: Node + score
- `IngestDocument`: Source + content + metadata
- `RelationshipType`: Enum of all relationship types (see config/relationships.schema.yaml)
- `FallbackProvider`: ollama_vps | ollama_local | openai

Node types: CODE, MARKDOWN, DOCUMENT, ISSUE, COMMIT, CONCEPT

### Knowledge Graph Schema (config/relationships.schema.yaml)

Relationship categories:
- **Document**: REFERENCES, RELATED_TO, EXTENDS, SUPERSEDES
- **Code**: DEPENDS_ON, IMPLEMENTS, EXTENDS_CLASS, CALLS
- **Temporal**: PRECEDES, FOLLOWS
- **Concept**: CONCEPT_RELATES, CONCEPT_SIMILAR
- **Part-whole**: PART_OF, HAS_PART
- **Example**: EXAMPLE_OF, HAS_EXAMPLE
- **Documentation**: DESCRIBES, IS_DESCRIBED_BY
- **Test**: TESTS, IS_TESTED_BY
- **Config**: CONFIGURES, IS_CONFIGURED_BY

Each relationship has:
- strength_range (0-1)
- directional (boolean)
- inverse relationship
- metadata_fields

### Testing (test/)

Uses Bun Test framework. Test setup in test/setup.ts:
- Sets QDRANT_URL and OLLAMA_URL based on VPS environment
- VPS (production): uses localhost
- Remote: uses external IP (72.60.204.156)

Test structure:
- test/unit/: Unit tests for providers, fallback manager
- test/integration/: End-to-end KB tests
- test/chaos/: Resilience and failure scenario tests

### VPS Deployment (vps/)

Docker Compose stack (Phase 0):
- **qdrant**: Port 6333 (HTTP), 6334 (gRPC)
- **ollama**: Port 11434

Deployment:
1. SSH into VPS: `ssh root@your-vps-ip`
2. Clone repo to /root/rad-engineer-v2/knowledge-base
3. Run setup.sh: `sudo ./setup.sh`
4. Configure .env: `cp ../.env.example ../.env`
5. Deploy: `./deploy.sh`

## Important Implementation Details

### Node ID Generation
Qdrant requires UUID v4 for string point IDs. Use `crypto.randomUUID()` - never use custom string IDs.

### Date Serialization
Relationships contain Date objects that must be serialized to ISO strings when storing in Qdrant and deserialized when retrieving. See QdrantProvider.upsertNodes() and pointToNode().

### Error Handling in Fallback Chain
FallbackManager detects trigger types from error messages:
- timeout: "timeout", "ETIMEDOUT", "ESOCKETTIMEDOUT"
- container_down: "ECONNREFUSED", "ENOTFOUND", "connect", "Network error"
- model_not_found: "model" + ("not found" | "does not exist" | "unknown")
- default: retry_exceeded

### Configuration
Environment variables (set in .env):
- QDRANT_URL: Qdrant endpoint (default: http://localhost:6333)
- OLLAMA_URL: Ollama endpoint (default: http://localhost:11434)
- KB_API_KEY: API key for MCP server authentication
- GITHUB_WEBHOOK_SECRET: GitHub webhook secret
- OPENAI_API_KEY: Emergency fallback (minimal usage expected)

### Node Type Inference
KnowledgeBase.inferNodeType() determines node type from file extension:
- .md → MARKDOWN
- .ts, .js, .tsx, .jsx, .py, .go, .rs → CODE
- .txt, .json, .yaml, .yml → DOCUMENT
- default → DOCUMENT

### ES Modules & TypeScript
- Uses ESNext modules with .js extensions in imports
- TypeScript target: ES2022
- Module resolution: bundler (Node.js next)
- All imports must use .js extension (even for .ts files)

### Logging
Uses Pino logger. Configure via LOG_LEVEL environment variable (error, warn, info, debug).

## Current Limitations (TODOs)

As noted in the code:
- Caching layer not fully implemented (cacheHit always false)
- Relationship extraction not implemented (relationships array always empty)
- Graph traversal paths need relationship strength calculation
- Temperature-based cache promotion not implemented
- Local LanceDB cache not integrated
