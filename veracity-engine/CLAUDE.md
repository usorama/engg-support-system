# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Veracity Engine (Ground-Truth Context System / GTCS) is a deterministic GraphRAG platform that indexes codebases into a Neo4j knowledge graph for auditable, evidence-based retrieval. It provides AI agents with architectural context validated for "veracity" (staleness, orphans, contradictions) before delivery.

**Status**: Alpha (~15% production-ready)

## Common Commands

### Python Core (Graph Operations)
```bash
# Build/refresh knowledge graph for a project
python3 core/build_graph.py --project-name NAME --root-dir PATH

# Query the knowledge graph
python3 core/ask_codebase.py --project-name NAME "your question"

# Generate codebase map
python3 core/generate_codebase_map.py
```

### UI (React/Vite Dashboard)
```bash
cd ui
npm install          # Install dependencies
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Production build
npm run lint         # ESLint check
```

### Infrastructure (Docker)
```bash
# Start Neo4j + NeoDash + UI stack
cd infra && docker compose up -d

# Neo4j browser: http://localhost:7474
# NeoDash: http://localhost:5005
# Veracity UI: http://localhost:5173
```

### Testing
```bash
pytest               # Run Python tests from repo root
```

### Project Installation (in target codebase)
```bash
./scripts/install.sh  # Installs GTCS, boots Neo4j, creates venv, indexes project
```

## Architecture

### Data Flow
```
Source Code → build_graph.py → AST Parser → Neo4j
                                    ↓
                            Ollama Embeddings (nomic-embed-text)
                                    ↓
                            Neo4j Vector Index

Query → ask_codebase.py → Hybrid Search (Vector + Full-Text) → LLM Synthesis → Output
```

### Directory Structure
- `core/` - Python engines: `build_graph.py` (indexing), `ask_codebase.py` (querying)
- `ui/` - React + Vite + Tailwind dashboard with Neo4j driver and force-graph visualization
- `infra/` - Docker Compose stack (Neo4j 5.15.0, NeoDash, UI)
- `templates/` - Agent configuration templates (e.g., `context-kg.mdc` for Cursor)
- `scripts/` - `install.sh` (project bootstrapping), `setup_service.sh`
- `docs/` - Architecture, PRD, UI spec, story plans

### Graph Data Model
- **Node Types**: File, Class, Function, Document, Capability, Feature, Component
- **Relationships**: DEFINES, CALLS, DEPENDS_ON, HAS_ASSET
- **Multitenancy**: Via `project` label on nodes

### Veracity System
The `GroundTruthContextSystem` class in `ask_codebase.py` validates:
- **STALE_DOC**: Documents >90 days old
- **ORPHANED_NODE**: Nodes with <2 connections
- **Contradictions**: (Placeholder for LLM-based diffing)

## Development Workflow

Follow **TDD workflow** in `docs/plans/IMPLEMENTATION_WORKFLOW.md`:
1. **Specification** - Write Given-When-Then specs
2. **Test Development** - Write failing tests first
3. **Research** - Evidence-based gap analysis
4. **Implement** - Make tests pass
5. **Verify** - All tests + DoD satisfied

Story tracking: `docs/plans/MASTER_TASKS.md`

## Configuration

### Environment Variables
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EMBED_MODEL=nomic-embed-text  # Ollama embedding model
```

### Prerequisites
- **Docker**: For Neo4j/NeoDash infrastructure
- **Ollama**: Local LLM + embeddings (`ollama pull llama3.2`, `ollama pull nomic-embed-text`)
- **Python 3.x**: With `neo4j>=5.15.0`, `ollama>=0.1.0`, `pytest`
- **Node.js**: For UI development

## Current Limitations (Known Gaps)
- Only indexes `.py` and `.md` files (not all file types)
- Python AST parsing only (non-Python files excluded)
- Unpinned embedding models (non-deterministic)
- No deterministic chunking strategy
- LLM synthesis in default query output
- Hardcoded credentials in docker-compose
- No observability (logs, metrics, health checks)

## GTCS Protocol for AI Agents

Before answering architectural questions, run:
```bash
python3 ./core/ask_codebase.py --project-name PROJECT "Identify relationships related to: [focus]"
```

- Trust `code_truth` findings over assumptions
- If `STALE_DOC` flagged, verify before trusting
- Queries are logged in `.graph_rag/audit/`
