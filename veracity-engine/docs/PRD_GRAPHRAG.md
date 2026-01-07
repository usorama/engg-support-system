# Product Requirements Document (PRD): Veracity Engine - Deterministic GraphRAG Service

## 1. Executive Summary

**Current State (Alpha)**: The Veracity Engine is a deterministic, evidence-based context engineering platform that indexes codebases into a knowledge graph for auditable retrieval. The system currently indexes Python and Markdown files, uses AST parsing for code analysis, and provides a React-based visualization UI with Neo4j backend.

**Target State (Production)**: Production-grade GraphRAG service that indexes ALL file types, provides evidence-only query outputs with full veracity checks, supports multi-tenant deployments, and is deployable via Docker Compose on VPS infrastructure with full observability and security hardening.

## 2. Problem Statement

### Primary Problem
Highly complex codebases are difficult for both humans and AI agents to navigate using text search alone. Current systems lack:
- **Determinism**: Same inputs produce different outputs due to unpinned models/dependencies
- **Evidence-Only**: LLM synthesis generates hallucinations rather than citing sources
- **Coverage**: Only subset of files (Python/Markdown) are indexed
- **Observability**: No health checks, logging, or metrics for operations
- **Security**: Hardcoded credentials and secrets in source code

### Target Users
1. **AI Agents** (Cursor, Claude): Need deterministic, evidence-based context
2. **Developers**: Need to visualize code relationships and dependencies
3. **Operations Teams**: Need observability and production deployment capability

## 3. Goals & Objectives

### Production Goals
- **Determinism**: Same inputs → identical outputs (reproducible KG builds and queries)
- **Evidence-Only**: All outputs cite exact sources (file paths, line numbers, node IDs)
- **Full Coverage**: Index every file type (code, config, docs, infrastructure)
- **Production Ready**: Health checks, structured logging, metrics configuration
- **Security**: Secrets management, no hardcoded credentials
- **Scalability**: Deployable on VPS, supports 10+ projects (expandable)

### Non-Goals
- Kubernetes deployment (Docker Compose sufficient for VPS)
- Advanced authentication (UID/Pwd acceptable; full AuthZ deferred)
- Real-time auto-scaling (manual scaling acceptable)

## 4. Deployment Architecture

### VPS Deployment (Primary Target)
- **Platform**: VPS hosting (Hostinger or similar)
- **Infrastructure**: Docker Compose
- **Scale**: Starts at 10 projects, expandable architecture
- **LLM Strategy**: Self-hosted Ollama with OpenAI API edge cases/escalations
- **Security**: UID/Pwd authentication; Auth spec in backlog (design required, implementation deferred)

### Resource Requirements (Minimum)
- CPU: 2 cores
- RAM: 4GB (2GB minimum, 4GB recommended)
- Disk: 20GB (5GB minimum, 20GB recommended)
- OS: Ubuntu 22.04 or similar

## 5. Key Features

### 5.1. Core Engine (Current State)

**Implemented:**
- ✅ Python AST parsing (extracts Classes, Functions, Imports)
- ✅ Incremental sync using SHA1 hashing
- ✅ Vector indexing for Class/Function nodes only
- ✅ Markdown document indexing
- ✅ React + Vite UI with graph visualization
- ✅ Multitenancy via project labels on nodes

**Missing (Target State):**
- ❌ Multi-language parsing (currently Python-only)
- ❌ All file type indexing (currently .py and .md only)
- ❌ Configuration files indexed (YAML, JSON, etc.)
- ❌ Infrastructure files indexed (Dockerfile, docker-compose.yml)
- ❌ Binary file metadata (hash, size)
- ❌ Deterministic chunking (currently no chunking)
- ❌ Model version pinning (non-deterministic embeddings)

### 5.2. Multitenancy (Current State)
- ✅ Project isolation via labels
- ⚠️ Hash cache stored in engine directory (should be in target project)
- ❌ Query guards for cross-tenant leakage (planned: STORY-006)

### 5.3. Interface (Current State)

**Implemented:**
- ✅ CLI query engine (`ask_codebase.py`)
- ✅ React visualization UI (`ui/src/App.jsx`)
- ✅ NeoDash integration
- ✅ Git hooks in installer

**Missing (Target State):**
- ❌ Evidence-only query output (currently uses LLM synthesis by default)
- ❌ Evidence packet format with schema validation
- ❌ Provenance fields in UI (hash, extractor, timestamps)

### 5.4. Infrastructure (Current State)

**Implemented:**
- ✅ Docker Compose stack (Neo4j, NeoDash, UI)
- ✅ Installer script (`scripts/install.sh`)

**Missing (Target State):**
- ❌ Health check endpoints
- ❌ Structured JSON logging
- ❌ Metrics collection
- ❌ Secrets management (.env support)
- ❌ VPS deployment validation

## 6. Technical Stack

### Current Stack
```
- Database: Neo4j 5.15.0 (not pinned to digest)
- Embeddings: Ollama nomic-embed-text (not version-pinned)
- LLM: Ollama llama3.2 (not version-pinned)
- Parsing: Python ast module (Python-only)
- Infrastructure: Docker & Docker Compose
- UI: React + Vite + Cytoscape.js
```

### Target Stack (After Foundation Stories)
```
- Database: Neo4j 5.15.0 (pinned to digest SHA256)
- Embeddings: Ollama nomic-embed-text v1.5.0 (pinned to SHA256 with seed)
- LLM: Ollama llama3.2 3.2.3 (pinned to SHA256 with seed)
- Fallback: OpenAI API (for edge cases/escalations)
- Parsing: Python ast (expandable to tree-sitter)
- Infrastructure: Docker Compose with health checks
- Configuration: YAML + env vars + CLI hierarchy
- Observability: structlog + health endpoints + metrics
- Secrets: .env files with validation
- Security: Basic UID/Pwd (AuthZ spec deferred)
```

## 7. Implementation Roadmap

### Phase 1: Foundation (Stories 001-005)
**Target: 30% Production Ready**

- STORY-001: Configuration Management (hierarchical: CLI → Env → Config → Defaults)
- STORY-002: Dependency Pinning & Model Version Control (determinism)
- STORY-003: Secrets Management & Security Hardening (.env support)
- STORY-004: Observability Infrastructure Setup (logging, health checks, metrics)
- STORY-005: Runtime Dependencies + Infra Validation (VPS deployment)

### Phase 2: Core Data Model (Stories 006-009)
**Target: 50% Production Ready**

- STORY-006: Multitenancy Isolation (schema + query guards)
- STORY-007: Index Every File Type (all file types, evidence-first)
- STORY-008: Deterministic Chunking + Embeddings (pinned models, seed)
- STORY-009: Provenance Model (source tracking, hashes, timestamps)

### Phase 3: Query Layer Refactor (Stories 010-012)
**Target: 70% Production Ready**

- STORY-010: Evidence-Only Query Output (remove LLM synthesis default)
- STORY-011: Evidence Packet Contract (schema validation, versioned)
- STORY-012: Veracity Logic Expansion (contradictions, staleness, orphans)

### Phase 4: Advanced Features (Stories 013-015)
**Target: 85% Production Ready**

- STORY-013: Repository Map + Structural Ranking (PageRank, AST)
- STORY-014: Taxonomy Expansion (APIs, contracts, services)
- STORY-015: UI Evidence & Provenance Surface (render packets)

### Phase 5: Quality & Automation (Stories 016-017)
**Target: 90%+ Production Ready**

- STORY-016: Testing and Reproducibility Harness (TDD)
- STORY-017: KG Self-Indexing + Automation (index this repo)

## 8. Production-Ready Criteria

### 16-Layer Production Architecture Compliance

**Layers 1-4: Foundation (BLOCKER)**
1. ✅ Configuration Management (STORY-001 - in progress)
2. ❌ Ingestion Pipeline (partial - needs STORY-007)
3. ⚠️ Change Detection (implemented - hashes work)
4. ❌ File Parsing (Python only - needs multi-language)

**Layers 5-8: Data Processing (BLOCKER)**
5. ❌ Entity Extraction (Python AST only)
6. ❌ Chunking Strategy (not implemented)
7. ⚠️ Knowledge Graph (basic multitenant)
8. ❌ Vector Search (no model pinning)

**Layers 9-12: Query & Caching (CRITICAL)**
9. ❌ Query Engine (LLM synthesis default - violates evidence-only)
10. ❌ Routing (no query routing)
11. ❌ Caching (no caching layer)
12. ❌ Security (no AuthZ, hardcoded passwords)

**Layers 13-16: Operations (CRITICAL)**
13. ❌ Deployment (no VPS validation)
14. ❌ Observability (no logs/metrics/health checks)
15. ❌ Alerting (no alerting)
16. ❌ Analytics (no usage tracking)

### Current Production Readiness Score: **15%**
### Target Before Feature Development: **90%+**

## 9. Constraints & Assumptions

### Constraints
1. **TDD Requirement**: All features must have TDD specifications before implementation
2. **Evidence-Only**: No LLM synthesis in default query output
3. **Determinism**: Pinned model versions, seeded generation
4. **VPS Deployment**: Docker Compose, not Kubernetes
5. **Security**: UID/Pwd only; full AuthZ deferred

### Assumptions
1. Ollama runs as local binary (not containerized)
2. OpenAI API available for edge cases (paid service)
3. VPS has SSH access and Docker installed
4. Initial deployment target: 10 projects (expandable)

## 10. Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Unpinned model versions cause non-determinism | High | High | STORY-002 pins all models |
| LLM synthesis produces hallucinations | High | High | STORY-010 removes synthesis default |
| Hardcoded credentials in code | High | Medium | STORY-003 adds .env support |
| No observability causes operational blind spots | Medium | High | STORY-004 adds logs/metrics/health checks |
| Incomplete file indexing reduces evidence coverage | High | High | STORY-007 indexes all file types |
| Cross-tenant data leakage | Medium | Medium | STORY-006 adds query guards |

## 11. Success Metrics

### Before Foundation Stories (Current)
- File coverage: ~20% (.py + .md only)
- Determinism: Low (unpinned models)
- Security: Critical (hardcoded passwords)
- Observability: None (no logs/metrics)
- Production Readiness: 15%

### After Foundation Stories (Target)
- Configuration: Hierarchical layers operational
- Determinism: High (pinned models, seeded generation)
- Security: Acceptable (.env support, validation)
- Observability: Functional (JSON logs, health checks, metrics)
- Production Readiness: 50%

### After All Stories (Target)
- File coverage: 100% (all file types)
- Determinism: High (fully reproducible)
- Security: High (managed secrets, basic Auth)
- Observability: High (16-layer coverage)
- Production Readiness: 90%+

## 12. Appendix

### References
- Architecture Review: `docs/research/ARCHITECTURE_REVIEW_DEEP_DIVE.md`
- Pivot Summary: `docs/research/ARCHITECTURE_PIVOT_SUMMARY.md`
- Master Tasks: `docs/plans/MASTER_TASKS.md`
- Implementation Workflow: `docs/plans/IMPLEMENTATION_WORKFLOW.md` (TDD)

### Version History
- **2025-12-01**: Initial PRD (pre-pivot)
- **2025-12-30**: Major revision - Production-ready architecture pivot, TDD workflow, 16-layer architecture reference
