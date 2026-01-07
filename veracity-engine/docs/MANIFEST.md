# Veracity Engine System Manifest - Deterministic GraphRAG Service

This document provides a single-point reference for the Veracity Engine, a deterministic, evidence-based context engineering platform.

## Current State (Alpha - Production Readiness: 15%)

### 📂 Core Capability Directory: repo root (`core/`, `infra/`, `docs/`, `ui/`, `scripts/`)

### 🛠️ Core Scripts (`core/`)
| File | Purpose | Status | Key Feature |
| :--- | :--- | :--- | :--- |
| [build_graph.py](../core/build_graph.py) | Incremental KG Builder | ✅ Functional | SHA1 Hashing, Python AST |
| [ask_codebase.py](../core/ask_codebase.py) | Semantic Query Interface | ✅ Functional | Hybrid Search, **LLM Synthesis** |
| [generate_codebase_map.py](../core/generate_codebase_map.py) | Structural Documentation | ✅ CLI Args | Optional markdown export |

### 🏗️ Infrastructure (`infra`)
| File | Component | Status | Role |
| :--- | :--- | :--- | :--- |
| [docker-compose.yml](../infra/docker-compose.yml) | Docker Stack | ✅ Functional | Neo4j, NeoDash, UI |
| Health Checks | Service Monitoring | ❌ Missing | Not implemented |

### 📜 Documentation (`docs`)
| File | Purpose | Status |
| :--- | :--- | :--- |
| [PRD_GRAPHRAG.md](PRD_GRAPHRAG.md) | Vision & Requirements | ✅ **Updated 2025-12-30** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System & Data Flow | ⚠️ Needs update |
| [UI_SPEC_KG.md](UI_SPEC_KG.md) | UI Specifications | ℹ️ Reference |

### 📋 Research & Planning (`docs/research`, `docs/plans`)
| Location | Content | Status |
| :--- | :--- | :--- |
| [ARCHITECTURE_REVIEW_DEEP_DIVE.md](ARCHITECTURE_REVIEW_DEEP_DIVE.md) | Architecture Analysis | ✅ **New 2025-12-30** |
| [ARCHITECTURE_PIVOT_SUMMARY.md](ARCHITECTURE_PIVOT_SUMMARY.md) | Pivot Documentation | ✅ **New 2025-12-30** |
| [MASTER_TASKS.md](../plans/MASTER_TASKS.md) | Story Tracker | ✅ **Updated 2025-12-30** |
| [IMPLEMENTATION_WORKFLOW.md](../plans/IMPLEMENTATION_WORKFLOW.md) | TDD Workflow | ✅ **Updated 2025-12-30** |
| Stories 001-017 | Implementation Plans | ✅ Reorganized |

## System Components (Current vs Target)

### Implemented Components ✅
- **KG Builder**: Python AST parsing, incremental sync, basic multitenancy
- **Query Engine**: Hybrid vector+semantic search, LLM synthesis
- **Visualization**: React graph UI with project selector
- **Installer**: Bootstrap script for target projects

### Missing Critical Components ❌
- **Configuration Management**: Partial (CLI only, hierarchical pending) - STORY-001
- **Dependency Pinning**: Models and deps unpinned - STORY-002
- **Secrets Management**: Hardcoded passwords in code - STORY-003
- **Observability**: No logs/health checks/metrics - STORY-004
- **Health Checks**: No service validation - STORY-005
- **Evidence-Only Queries**: LLM synthesis by default - STORY-010
- **Full File Indexing**: Only .py/.md files - STORY-007
- **Deterministic Chunking**: Not implemented - STORY-008

## Production Readiness (16-Layer Architecture)

| Layer | Component | Current | Target Story |
| :--- | :--- | :--- | :--- |
| 1 | Config Management | ⚠️ Partial | STORY-001 |
| 2 | Ingestion Pipeline | ⚠️ Partial | STORY-007 |
| 3 | Change Detection | ✅ SHA1 implemented | - |
| 4 | File Parsing | ⚠️ Python-only | STORY-007 |
| 5 | Entity Extraction | ❌ AST only | STORY-007 |
| 6 | Chunking Strategy | ❌ None | STORY-008 |
| 7 | Knowledge Graph | ⚠️ Basic multi-tenant | STORY-006 |
| 8 | Vector Search | ❌ Unpinned | STORY-008 |
| 9 | Query Engine | ⚠️ LLM synthesis | STORY-010 |
| 10 | Query Routing | ❌ None | - |
| 11 | Caching | ❌ None | - |
| 12 | Security | ❌ Hardcoded | STORY-003 |
| 13 | Deployment | ❌ No VPS validation | STORY-005 |
| 14 | Observability | ❌ None | STORY-004 |
| 15 | Alerting | ❌ None | - |
| 16 | Analytics | ❌ None | - |

**Overall Production Readiness: 15%**

## Deployment

### Current Deployment
- **Platform**: Development only
- **Infrastructure**: Docker Compose locally
- **LLM**: Ollama local binary
- **Database**: Neo4j 5.15.0 (not pinned to digest)

### Target Deployment
- **Platform**: VPS (Hostinger or similar)
- **Infrastructure**: Docker Compose with health checks
- **LLM**: Ollama + OpenAI API edge cases
- **Database**: Neo4j 5.15.0 (pinned to digest)
- **Scale**: 10 projects (expandable)

## Getting Started (Current)

```bash
# Install in target project
bash scripts/install.sh

# Build knowledge graph
python3 core/build_graph.py --project-name MY_PROJECT --root-dir .

# Query the graph
python3 core/ask_codebase.py --project-name MY_PROJECT "your question"

# Start UI
cd ui && npm install && npm run dev
```

## References

### Primary Documentation
- [PRD_GRAPHRAG.md](PRD_GRAPHRAG.md) - Product Requirements (Updated 2025-12-30)
- [ARCHITECTURE.md](ARCHITECTURE.md) - System Architecture
- [AGENTS.md](../AGENTS.md) - Coding Guidelines

### Research & Planning
- [Architecture Review](ARCHITECTURE_REVIEW_DEEP_DIVE.md) - Deep dive analysis
- [Pivot Summary](ARCHITECTURE_PIVOT_SUMMARY.md) - Reorganization summary
- [Master Tasks](../plans/MASTER_TASKS.md) - Story tracker
- [Implementation Workflow](../plans/IMPLEMENTATION_WORKFLOW.md) - TDD process

### Story Files (`docs/plans/`)
- Foundation: 001-005 (Configuration, Deps, Secrets, Observability, Infra)
- Core Data: 006-009 (Multitenancy, Files, Chunking, Provenance)
- Query Layer: 010-012 (Evidence-Only, Packet Contract, Veracity)
- Advanced: 013-015 (Repo Map, Taxonomy, UI)
- Quality: 016-017 (Tests, Automation)

## Version History
- **2025-12-01**: Initial manifest (pre-pivot)
- **2025-12-30**: Production-ready restructure, 16-layer reference, TDD workflow

> [!NOTE]
> **Host Environment**: Neo4j runs on OrbStack. Data and logs are persisted to `$HOME/.gemini/neo4j` to ensure the Knowledge Graph survives container restarts.

### 🤖 Automation
- **Git Hook**: optional post-commit hook installed by `scripts/install.sh` in the target project.
  - Updates the Knowledge Graph and Codebase Map on every commit.
  - Index state is stored in `core/.graph_hashes_<project>.json` (generated at runtime).

---

## 🔗 How it Works
1. **Extraction**: `build_graph.py` uses Python's `ast` module to extract classes, functions, and imports.
2. **Indexing**: It calculates SHA1 hashes of every file. If a file hasn't changed, it's skipped.
3. **Neo4j Commit**: Nodes are created with unique `uid` identifiers (e.g., `services/auth::oauth_callback`).
4. **Relationship Mapping**: Uses the `uid` for ultra-fast, index-backed `MERGE` operations.
5. **Discovery**: `ask_codebase.py` performs hybrid search querying Neo4j for both semantic (embedding) and structural (AST) matches.

## 🛠️ Dependencies
- **Neo4j**: Graph Database
- **Ollama**: Embedding generation (`nomic-embed-text`)
- **Python**: `neo4j`, `hashlib`, `ast`, `pydantic`
