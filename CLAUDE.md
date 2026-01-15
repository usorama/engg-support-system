# CLAUDE.md - Engineering Support System

> **Unified Intelligence System**: Knowledge-Base (Qdrant) + Veracity-Engine (Neo4j) for Complete Codebase Understanding

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Working Preferences (Memory)

**CRITICAL: Always follow these rules when working with this codebase**

1. **File Organization**: User prefers proper organization of files. Documents should be placed in appropriate directories (e.g., plans go in `docs/plans/`).

2. **Edit vs. Create**: When user requests changes to existing documentation:
   - **ALWAYS edit the existing file** - never create a new file
   - Use the Edit tool to modify the existing document in place
   - Only create new files when explicitly requested or for genuinely new content

3. **Documentation Structure**:
   - `docs/plans/` - All planning documents
   - `docs/` - General documentation
   - Root `CLAUDE.md` - System overview and context

---

## Vision, Objectives, Outcomes

### Vision
To create a **deterministic, evidence-based engineering intelligence system** that provides AI agents with complete codebase understanding through hybrid vector + graph search, ground-truth validation, and unified infrastructure.

### Objectives
1. **Integrate Qdrant + Neo4j** for hybrid search capabilities (vector similarity + graph relationships)
2. **Share Ollama models** between both systems efficiently (nomic-embed-text, llama3.2, mistral, codeqwen)
3. **Unify MCP APIs** into a single gateway for AI agents
4. **Create shared infrastructure** with Docker Compose for unified deployment
5. **Implement codebase ingestion** for full triangulated truth (multi-language support)
6. **Maintain determinism** throughout all operations (no hallucinations, evidence-based)

### Outcomes
- Single entry point for AI agents to query codebase intelligence
- Redundant storage (vector + graph) for reliability and cross-validation
- Shared model resources for cost efficiency
- Modular architecture allowing independent enhancement of each component
- Production-ready deployment on VPS with health checks and monitoring

---

## System Architecture

### Component Overview

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
        │ MCP Server    │  │ MCP Server     │  │ ├─ nomic-embed│
        │ Ingestion     │  │ Watcher Daemon │  │ ├─ llama3.2   │
        │ FallbackMgr   │  │ Veracity Check │  │ ├─ mistral    │
        └───────────────┘  └───────────────┘  │ └─ codeqwen   │
                                     │          └───────────────┘
                                     └──────────────┬────────────┘
                                                    │
                           ┌────────────────────────┼────────────────────────┐
                           ▼                        ▼                        ▼
                ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
                │  Qdrant (6333)   │    │  Neo4j (7474/    │    │  Shared          │
                │  Vector DB       │    │   7687)          │    │  Infrastructure  │
                ├──────────────────┤    ├──────────────────┤    ├──────────────────┤
                │ 768-dim vectors  │    │ Graph Nodes/Edges│    │ Docker Compose   │
                │ Cosine distance  │    │ Vector index     │    │ Health checks    │
                │ UUID v4 IDs      │    │ Project labels   │    │ Monitoring       │
                └──────────────────┘    └──────────────────┘    └──────────────────┘
```

### Data Flow

**Ingestion Flow**:
```
Codebase → AST Parser → Structure Extract →
├─→ Neo4j (relationships, dependencies, graph structure)
└─→ Qdrant (embeddings, chunks, semantic vectors)
```

**Query Flow**:
```
Agent Query → Unified Gateway →
├─→ Qdrant (semantic similarity search)
├─→ Neo4j (graph traversal, relationships)
└─→ Merge & Rank → Veracity Check → Evidence-Based Response
```

---

## Component Details

### 1. knowledge-base (Qdrant Vector System)

**Location**: `knowledge-base/`

**Purpose**: Semantic search and document retrieval using vector embeddings

**Key Features**:
- Vector storage with 768-dim embeddings (nomic-embed-text)
- Multi-provider fallback (Ollama VPS → Local → OpenAI)
- MCP server for agent integration
- TypeScript implementation with strict typing
- VPS deployment ready

**Core Files**:
- `src/core/KnowledgeBase.ts` - Main orchestrator
- `src/core/QdrantProvider.ts` - Vector + graph storage client
- `src/core/FallbackManager.ts` - Multi-provider orchestration
- `src/core/OllamaEmbeddingProvider.ts` - Embeddings via Ollama
- `src/core/OllamaSummarizer.ts` - Evidence-based summarization

**Relationship Schema** (config/relationships.schema.yaml):
- Document: REFERENCES, RELATED_TO, EXTENDS, SUPERSEDES
- Code: DEPENDS_ON, IMPLEMENTS, EXTENDS_CLASS, CALLS
- Temporal: PRECEDES, FOLLOWS
- Concept: CONCEPT_RELATES, CONCEPT_SIMILAR
- Part-whole: PART_OF, HAS_PART
- Documentation: DESCRIBES, IS_DESCRIBED_BY
- Test: TESTS, IS_TESTED_BY

**Commands**:
```bash
cd knowledge-base
npm run build           # Compile TypeScript
npm run typecheck       # Type check
npm run dev            # Watch mode
npm run start:mcp      # Start MCP server (port 3000)
npm test               # Run tests
npm run lint           # ESLint check
```

**Current Limitations**:
- Relationships stored in payload (not true graph)
- Relationship extraction not implemented
- Caching layer incomplete
- Limited to semantic search (no structural context)

---

### 2. veracity-engine (Neo4j Graph System)

**Location**: `veracity-engine/`

**Purpose**: Code graph with deterministic validation and architectural context

**Key Features**:
- True graph relationships (DEFINES, CALLS, DEPENDS_ON, HAS_COMPONENT)
- Veracity validation (STALE_DOCS, ORPHANED_NODES, contradictions)
- Python AST parsing for code structure
- MCP server for Claude Code integration
- File watcher daemon for real-time updates
- NeoDash visualization UI

**Core Files**:
- `core/build_graph.py` - Indexing engine
- `core/ask_codebase.py` - Query engine with veracity
- `core/mcp_server.py` - MCP server for agents
- `core/watcher_daemon.py` - File system watcher
- `core/project_registry.py` - Project configuration

**Graph Data Model**:
- **Node Types**: File, Class, Function, Document, Capability, Feature, Component
- **Relationships**: DEFINES, CALLS, DEPENDS_ON, HAS_ASSET
- **Multitenancy**: Via `project` label on nodes

**Veracity System**:
- **STALE_DOC**: Documents >90 days old
- **ORPHANED_NODE**: Nodes with <2 connections
- **Contradictions**: (Placeholder for LLM-based diffing)

**Commands**:
```bash
cd veracity-engine

# Python Core
python3 core/build_graph.py --project-name NAME --root-dir PATH
python3 core/ask_codebase.py --project-name NAME "your question"

# Infrastructure
cd infra && docker compose up -d  # Neo4j + NeoDash

# UI
cd ui && npm install && npm run dev

# Daemon
./scripts/install-daemon.sh
veracityd register myproject /path/to/project
veracityd start
```

**Current Limitations**:
- Only indexes .py and .md files (no TypeScript, Go, Rust yet)
- Python AST parsing only
- No vector similarity search (relies on Neo4j's vector index)
- Alpha status (~15% production-ready)
- Hardcoded credentials in docker-compose

---

### 3. Shared Resources

**Ollama Models** (Shared between both systems):

| Model | Purpose | Dimensions | Use Case |
|-------|---------|------------|----------|
| nomic-embed-text | Embeddings | 768 | Vector generation |
| llama3.2:3b | Fast reasoning | - | Low-latency queries |
| llama3.2 | General purpose | - | Default synthesis |
| mistral-nemo | Code understanding | - | Code analysis |
| codeqwen | Code-specific | - | Advanced code |
| deepseek-coder | Code analysis | - | Veracity checking |

**Infrastructure Services**:
- **Qdrant**: Vector database (port 6333/6334)
- **Neo4j**: Graph database (port 7474/7687)
- **NeoDash**: Graph visualization (port 5005)
- **Ollama**: Shared SLM service (port 11434)
- **Redis**: Shared caching layer (port 6379)

---

## Development Workflow

### Prerequisites

- **Docker**: For all infrastructure services
- **Ollama**: For local embeddings and LLM
- **Node.js 18+**: For knowledge-base TypeScript
- **Python 3.10+**: For veracity-engine Python
- **Bun**: For knowledge-base testing

### Quick Start

```bash
# 1. Start infrastructure
cd infra && docker compose up -d

# 2. Start knowledge-base MCP server
cd knowledge-base
npm install && npm run build && npm run start:mcp

# 3. Start veracity-engine MCP server (in separate terminal)
cd veracity-engine
pip install -r requirements.txt
python3 core/mcp_server.py

# 4. Ingest a codebase
cd veracity-engine
python3 core/build_graph.py --project-name myproject --root-dir /path/to/code

# 5. Query the system
python3 core/ask_codebase.py --project-name myproject "What are the main components?"
```

### Project-Specific Commands

**knowledge-base**:
```bash
cd knowledge-base
npm run build          # Compile
npm run typecheck      # Verify types
npm run dev           # Watch mode
npm run start:mcp     # MCP server
npm test              # Run tests
npm run lint          # ESLint
```

**veracity-engine**:
```bash
cd veracity-engine
pytest                # Run tests
flake8 core/ tests/   # Lint
cd ui && npm run dev  # UI dashboard
```

---

## Configuration

### Environment Variables

**knowledge-base** (.env):
```bash
QDRANT_URL=http://localhost:6333
OLLAMA_URL=http://localhost:11434
KB_API_KEY=your-api-key
GITHUB_WEBHOOK_SECRET=your-webhook-secret
OPENAI_API_KEY=emergency-fallback-only
LOG_LEVEL=info
```

**veracity-engine** (.env):
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EMBED_MODEL=nomic-embed-text
```

---

## Type System

### knowledge-base Types

**Core Types** (src/core/types.ts):
```typescript
interface KGNode {
  id: string;              // UUID v4 required
  vector: number[];        // 768-dim embedding
  content: string;         // Text content
  nodeType: NodeType;      // CODE | MARKDOWN | DOCUMENT | ISSUE | COMMIT | CONCEPT
  relationships: Relationship[];
  metadata: NodeMetadata;
}

interface SearchRequest {
  query: string;
  topK?: number;
  minScore?: number;
  filters?: SearchFilter;
}

interface SearchResult {
  node: KGNode;
  score: number;
}

type RelationshipType =
  | "REFERENCES" | "RELATED_TO" | "EXTENDS" | "SUPERSEDES"
  | "DEPENDS_ON" | "IMPLEMENTS" | "EXTENDS_CLASS" | "CALLS"
  | "PRECEDES" | "FOLLOWS"
  | "CONCEPT_RELATES" | "CONCEPT_SIMILAR"
  | "PART_OF" | "HAS_PART"
  | "DESCRIBES" | "IS_DESCRIBED_BY"
  | "TESTS" | "IS_TESTED_BY"
  | "CONFIGURES" | "IS_CONFIGURED_BY";
```

### veracity-engine Types

**Graph Model**:
- Nodes: File, Class, Function, Document, Component
- Relationships: DEFINES, CALLS, DEPENDS_ON, HAS_COMPONENT
- Veracity fields: confidence_score, is_stale, faults

---

## Important Implementation Details

### Node ID Generation
**Qdrant requires UUID v4** for string point IDs:
```typescript
// ✅ Correct
const id = crypto.randomUUID();

// ❌ Wrong - will fail
const id = `file:${filePath}`;
```

### Date Serialization
Relationships contain Date objects that must be serialized:
```typescript
// Store
payload.created_at = date.toISOString();

// Retrieve
const createdAt = new Date(payload.created_at);
```

### Error Handling in Fallback Chain
FallbackManager detects trigger types from error messages:
- **timeout**: "timeout", "ETIMEDOUT", "ESOCKETTIMEDOUT"
- **container_down**: "ECONNREFUSED", "ENOTFOUND", "Network error"
- **model_not_found**: "model" + ("not found" | "does not exist")
- **default**: retry_exceeded

### ES Modules & TypeScript
- Uses ESNext modules with .js extensions in imports
- TypeScript target: ES2022
- All imports must use .js extension (even for .ts files)

---

## Testing

### knowledge-base Tests
```bash
cd knowledge-base
bun test              # All tests
bun test unit/        # Unit tests only
bun test integration/ # Integration tests
bun test chaos/       # Resilience tests
```

### veracity-engine Tests
```bash
cd veracity-engine
pytest               # All tests
pytest tests/unit/   # Unit tests
pytest tests/integration/  # Integration tests
```

---

## GTCS Protocol for AI Agents

Before answering architectural questions, run:

```bash
# For semantic context
cd knowledge-base
npm run query -- "search term"

# For structural context
cd veracity-engine
python3 core/ask_codebase.py --project-name PROJECT "Identify relationships"

# For veracity validation
python3 core/ask_codebase.py --project-name PROJECT --validate "focus area"
```

**Rules**:
- Trust `code_truth` findings over assumptions
- If `STALE_DOC` flagged, verify before trusting
- Queries are logged in `.graph_rag/audit/`
- Always provide citations from source code

---

## Current Limitations & TODOs

### knowledge-base
- [ ] Caching layer not fully implemented
- [ ] Relationship extraction not implemented
- [ ] Graph traversal paths need relationship strength calculation
- [ ] Temperature-based cache promotion not implemented
- [ ] Local LanceDB cache not integrated

### veracity-engine
- [ ] Only indexes .py and .md files
- [ ] Python AST parsing only (need TypeScript, Go, Rust)
- [ ] Unpinned embedding models (non-deterministic)
- [ ] No deterministic chunking strategy
- [ ] LLM synthesis in default query output
- [ ] Hardcoded credentials in docker-compose
- [ ] No observability (logs, metrics, health checks)

### Integration TODOs
See `docs/plans/INTEGRATION_PLAN.md` for comprehensive integration roadmap.

---

## Integration Roadmap

See `docs/plans/INTEGRATION_PLAN.md` for the complete integration plan including:

**Phase 1**: Infrastructure Setup (Shared Docker Compose)
**Phase 2**: Unified MCP Gateway
**Phase 3**: Enhanced knowledge-base (Relationship extraction, caching)
**Phase 4**: Enhanced veracity-engine (Multi-language, veracity checking)
**Phase 5**: Full Codebase Ingestion (Multi-language pipeline)
**Phase 6**: Testing & Validation
**Phase 7**: Production Deployment

---

## Troubleshooting

### Query returns 0% confidence (veracity-engine)
- Vector search limit too low for multi-tenant
- Increase `vector_search_limit` in ask_codebase.py

### Daemon not detecting changes (veracity-engine)
- Check project registered: `veracityd list`
- Verify target directories exist
- Check logs: `veracityd logs`

### Neo4j connection refused
- Ensure infrastructure running: `cd infra && docker compose up -d`

### Qdrant timeout errors
- Check Ollama container: `docker ps | grep ollama`
- Verify Ollama models pulled: `ollama list`

---

## Project Integration (How Other Projects Use ESS)

ESS provides MCP tools for AI agents in other projects to track dev context.

### For Claude Code Agents in Other Projects

1. **Add MCP Server** to project's `.mcp.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ess-veracity": {
      "command": "python3",
      "args": ["/path/to/engg-support-system/veracity-engine/core/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_PASSWORD": "your-password"
      }
    }
  }
}
```

2. **Register the project** (first time only):
```
register_project(project_name="myproject", root_dir="/path/to/project")
index_project(project_name="myproject")
```

3. **Use MCP tools** for work tracking:

| Tool | Purpose |
|------|---------|
| `query_codebase` | Query knowledge graph for code evidence |
| `create_work_item` | Create new work item (feature, bug, task) |
| `query_work_items` | List work items with filters |
| `trace_file_to_work` | Find work items related to a file |
| `update_work_item` | Update status, priority, assignees |
| `analyze_code_for_work` | Auto-detect TODOs/FIXMEs |

### Integration Documentation

See `integration/` directory for:
- `CLAUDE_MD_INTEGRATION.md` - Template for other project CLAUDE.md files
- `claude-code-plugin/.mcp.json` - Ready-to-use MCP configuration
- `register-project.sh` - Convenience script for initial setup

### Key MCP Tools (Full Reference)

```
┌────────────────────────────────────────────────────────────────┐
│                    ESS MCP TOOLS REFERENCE                      │
├────────────────────────────────────────────────────────────────┤
│  QUERY & UNDERSTAND                                             │
│  query_codebase         → Search code structure & relationships │
│  query_work_items       → List work items with filters          │
│  get_work_context       → Full context for a work item          │
│  trace_file_to_work     → What work items touched this file?    │
│                                                                 │
│  CREATE & UPDATE                                                │
│  create_work_item       → Create feature/bug/task               │
│  update_work_item       → Update status/priority/assignees      │
│  record_code_change     → Record git commit (usually auto)      │
│  link_code_to_work      → Link commit to work item              │
│                                                                 │
│  ANALYZE & SETUP                                                │
│  analyze_code_for_work  → Detect TODOs/FIXMEs → work items      │
│  register_project       → Register new project                  │
│  index_project          → Index/re-index codebase               │
│  list_projects          → List all indexed projects             │
└────────────────────────────────────────────────────────────────┘
```

---

## VPS Deployment

### knowledge-base
```bash
cd knowledge-base/vps
./setup.sh    # Run VPS setup
./deploy.sh   # Deploy to VPS
```

### veracity-engine
```bash
cd veracity-engine/infra
docker compose up -d
```

### Full Stack (with Dev Context Tracking)
```bash
# Deploy all services including veracity-engine + UI
./scripts/deploy-prod.sh
```

---

**Document Status**: Unified | **Last Updated**: 2026-01-15
**See Also**: `docs/plans/INTEGRATION_PLAN.md` (comprehensive integration roadmap)
