# Master Tasks and Progress

## Overview
This is the unified progress tracker for all stories, ordered by production-ready implementation sequence.
Follow the workflow in `docs/plans/IMPLEMENTATION_WORKFLOW.md` (Updated for TDD) for execution.

## Revised Architecture (2025-12-30 Pivot)

### Production-Ready Sequence Overview

**PHASE 1: Configuration & Secrets Foundation**
- Configuration management with hierarchical layers (CLI → Env → Config → Defaults)
- Dependency pinning for reproducibility
- Secrets management for security

**PHASE 2: Core Infrastructure**
- Observability (structured logging, metrics, health checks)
- Runtime dependencies validation
- Multitenancy Isolation Design

**PHASE 3: Core Data Model**
- Index Every File Type (evidence-first ingestion)
- Deterministic Chunking + Embeddings
- Provenance Model (source tracking)

**PHASE 4: Query Layer Refactor**
- Evidence-Only Query Output (remove LLM synthesis default)
- Evidence Packet Contract (schema validation)
- Veracity Logic Expansion

**PHASE 5: Advanced Features**
- Repository Map + Structural Ranking
- Taxonomy Expansion (APIs, contracts)
- UI Evidence & Provenance Surface

**PHASE 6: Quality & Automation**
- Testing and Reproducibility Harness
- KG Self-Indexing + Automation

## Story Index & Progress

| ID | Title | Phase | Status | Last Update | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STORY-001** | Configuration Management | Foundation | COMPLETE | 2025-12-30 | ConfigLoader with Pydantic validation; hierarchical resolution; 21 tests passing |
| **STORY-002** | Dependency Pinning & Model Version Control | Foundation | COMPLETE | 2025-12-30 | Pinned all deps; core/models.py; 38 tests passing; verify_models.py script |
| **STORY-003** | Secrets Management & Security Hardening | Foundation | COMPLETE | 2025-12-30 | Secret validation; redaction; deploy script; 56 tests pass |
| **STORY-004** | Observability Infrastructure Setup | Infrastructure | COMPLETE | 2025-12-30 | structlog, health checks, metrics, correlation IDs; 88 tests pass |
| **STORY-005** | Runtime Dependencies + Infra Validation | Infrastructure | COMPLETE | 2025-12-30 | health-check.sh; validate-deps.py; VPS docs; 107 tests pass |
| **STORY-006** | Multitenancy Isolation | Core Data | COMPLETE | 2025-12-30 | core/multitenancy.py; query guards; validation; 146 tests pass |
| **STORY-007** | Index Every File Type | Core Data | COMPLETE | 2025-12-30 | core/file_ingestion.py; file discovery, classification, extraction; 187 tests pass |
| **STORY-008** | Deterministic Chunking + Embedding Controls | Core Data | COMPLETE | 2025-12-30 | core/chunking.py; deterministic IDs, split strategies; 224 tests pass |
| **STORY-009** | Provenance Model | Core Data | COMPLETE | 2025-12-30 | core/provenance.py; cross-platform hashing; build_graph.py integration; 253 tests pass |
| **STORY-010** | Evidence-Only Query Output | Query Layer | COMPLETE | 2025-12-30 | core/evidence_query.py; --evidence-only default; 279 tests pass |
| **STORY-011** | Evidence Packet Contract | Query Layer | COMPLETE | 2025-12-30 | core/packet_contract.py; schema v1.0; validation; hashing; 301 tests pass |
| **STORY-012** | Veracity Logic Expansion | Query Layer | COMPLETE | 2025-12-30 | core/veracity.py; staleness, orphans, contradictions, coverage; 331 tests pass |
| **STORY-013** | Repository Map + Structural Ranking | Advanced | COMPLETE | 2025-12-30 | core/repo_map.py; AST extraction, PageRank, token budget; 363 tests pass |
| **STORY-014** | Taxonomy Expansion | Advanced | COMPLETE | 2025-12-30 | core/taxonomy.py; APIs, contracts, services; 395 tests pass |
| **STORY-015** | UI Evidence & Provenance Surface | Advanced | COMPLETE | 2025-12-30 | EvidencePanel, ProvenanceDisplay components; 416 tests pass |
| **STORY-016** | Testing and Reproducibility Harness | Quality | COMPLETE | 2025-12-30 | Reproducibility tests; fixture repo; test runner script; 436 tests pass |
| **STORY-017** | KG Self-Indexing + Automation | Automation | COMPLETE | 2025-12-30 | self_index.py; git hooks; CI workflow; 471 tests pass |
| **STORY-018** | MCP Server for Agent Integration | Integration | COMPLETE | 2025-12-31 | mcp_server.py; 4 tools; deterministic evidence output |
| **STORY-019** | Autonomous Project Watcher | Automation | COMPLETE | 2025-12-31 | watcher_daemon.py; veracityd; launchd integration |
| **STORY-020** | Multi-Language AST Parsing | Quality | PLANNED | 2025-12-31 | tree-sitter integration; call graph; import mapping |

## Critical Path (Must Complete Before Features)

**Immediate Blockers (cannot continue without these):**
1. ~~STORY-001: Complete configuration hierarchy expansion~~ COMPLETE (2025-12-30)
2. ~~STORY-002: Dependency pinning (models + deps)~~ COMPLETE (2025-12-30)
3. ~~STORY-003: Secrets management (no hardcoded passwords)~~ COMPLETE (2025-12-30)
4. ~~STORY-004: Observability (logs, health checks, metrics)~~ COMPLETE (2025-12-30)
5. ~~STORY-005: Runtime Dependencies + Infra Validation~~ COMPLETE (2025-12-30)
6. ~~STORY-006: Multitenancy Isolation~~ COMPLETE (2025-12-30)
7. ~~STORY-007: Index Every File Type~~ COMPLETE (2025-12-30)
8. ~~STORY-008: Deterministic Chunking + Embedding Controls~~ COMPLETE (2025-12-30)
9. ~~STORY-009: Provenance Model~~ COMPLETE (2025-12-30)
10. ~~STORY-010: Evidence-Only Query Output~~ COMPLETE (2025-12-30)
11. ~~STORY-011: Evidence Packet Contract~~ COMPLETE (2025-12-30)
12. ~~STORY-012: Veracity Logic Expansion~~ COMPLETE (2025-12-30)
13. ~~STORY-013: Repository Map + Structural Ranking~~ COMPLETE (2025-12-30)
14. ~~STORY-014: Taxonomy Expansion~~ COMPLETE (2025-12-30)
15. ~~STORY-015: UI Evidence & Provenance Surface~~ COMPLETE (2025-12-30)
16. ~~STORY-016: Testing and Reproducibility Harness~~ COMPLETE (2025-12-30)
17. ~~STORY-017: KG Self-Indexing + Automation~~ COMPLETE (2025-12-30)

**ALL FOUNDATION STORIES COMPLETE** - System is production-ready for feature development!

**Query Layer Prerequisites (STORY-010, 011, 012 require):**
- STORY-007: Complete file indexing (evidence coverage)
- STORY-008: Deterministic embeddings (reproducibility)

## Plan Gap Review (Current Evidence-Based Gaps)

### Critical Issues Identified
- `core/build_graph.py` only indexes `*.py` and `*.md`; others ignored
- Parsing restricted to Python AST; non-Python files fail
- ~~No embedding model version pinning (non-deterministic)~~ **FIXED: core/models.py + config fields (STORY-002)**
- No deterministic chunking strategy
- `ask_codebase.py` uses LLM synthesis (risks hallucinations)
- ~~No observability (no structured logging, no metrics, no health checks)~~ **FIXED: core/logging.py, core/metrics.py, core/health.py (STORY-004)**
- ~~No secrets management (hardcoded passwords)~~ **FIXED: validate_secrets(), redact_config(), deploy-vps.sh (STORY-003)**
- ~~No testing harness (pytest in requirements but no tests)~~ **PARTIAL: tests/ framework created (88 tests)**

### Production Readiness Score
**Current**: 100% foundation complete (was 95%)
**Target**: 90%+ before feature development ✅ ACHIEVED

All 17 foundation stories complete. System ready for production deployment and feature development.

## Recent Session Updates

### 2025-12-31: STORY-020 Multi-Language AST Parsing Planned
**Story Created**: `docs/plans/STORY-020-multi-language-ast-parsing.md`

**Problem Identified (from pinglearn query testing):**
- Current multi-language support uses regex-based extraction
- Complex patterns missed (arrow functions, HOCs, dynamic exports)
- No call graph for non-Python languages
- Import/dependency tracking incomplete for JS/TS
- Cross-language relationships not captured

**Lessons Learned:**
1. Hardcoded Python assumption in `build_graph.py:670` - fixed with CODE_EXTENSIONS
2. Config file patterns weren't being consumed - now used
3. AST parsing is language-specific - Python `ast.parse()` only works for Python

**Recommended Solution:**
- Integrate tree-sitter for proper AST parsing (100+ languages)
- Create unified AST model (language-agnostic)
- Extract CALLS and IMPORTS relationships for all languages
- Detect cross-language API boundaries

**Status:** PLANNED - ready for implementation when prioritized.

### 2025-12-31: STORY-019 Autonomous Project Watcher Complete
**Commit**: `5a4189d` - `feat(STORY-019): autonomous project watcher daemon`

**New Infrastructure Created:**
- `core/watcher_daemon.py` - Background daemon using watchdog:
  - Real-time file system monitoring (FSEvents/inotify)
  - Debounced change aggregation (prevents rapid re-indexing)
  - Git-only mode (only re-index on commits)
  - Polling mode for network drives
- `core/project_registry.py` - Project configuration management:
  - YAML-based project registry (~/.veracity/projects.yaml)
  - CLI for project registration/unregistration
  - Per-project watch mode configuration
- `scripts/veracityd` - Daemon control script:
  - start/stop/restart/status commands
  - register/unregister projects
  - index all projects on demand
- `scripts/install-daemon.sh` - launchd installation script
- `infra/com.veracity.daemon.plist` - macOS launchd configuration

**Key Features:**
- Zero configuration in target projects
- Auto-start on macOS login via launchd
- Multiple watch modes: realtime, polling, git-only
- Project registry at ~/.veracity/projects.yaml

**Business Impact:** Projects now stay in sync autonomously without requiring git hooks or manual intervention.

### 2025-12-31: STORY-018 MCP Server for Agent Integration Complete
**Commit**: `6c194fb` - `feat(STORY-018): MCP server for agent integration`

**New Infrastructure Created:**
- `core/mcp_server.py` - Complete MCP server implementation:
  - 4 tools: query_codebase, get_component_map, list_projects, get_file_relationships
  - stdio transport for Claude Code integration
  - SecretStr handling for Neo4j authentication
  - Deterministic, evidence-based responses (no LLM synthesis)
- `scripts/install-mcp.sh` - Installation script for Claude Code:
  - Python 3.11 detection
  - Dependency verification
  - MCP config generation

**Files Modified:**
- `requirements.txt` - Added `mcp>=1.2.0`
- `~/Library/Application Support/Claude/claude_desktop_config.json` - Added veracity server

**Key Features:**
- Native agent integration via MCP protocol
- 4 tools for knowledge graph access:
  - `query_codebase`: Query graph for code evidence with file paths and line numbers
  - `get_component_map`: Generate architecture maps with relationships
  - `list_projects`: List indexed projects with node counts
  - `get_file_relationships`: Get file dependencies (imports, defines)
- Evidence-based responses with veracity scores
- No LLM hallucination - only graph-derived facts

**Business Impact:** AI agents in indexed codebases can now access deterministic context without shell commands or assumptions.

### 2025-12-30: STORY-017 KG Self-Indexing + Automation Complete
**Commit**: (pending) - `feat(STORY-017): KG self-indexing and automation`

**New Infrastructure Created:**
- `core/self_index.py` - Self-indexing configuration and utilities:
  - SELF_PROJECT_NAME constant ("veracity-engine")
  - SelfIndexConfig dataclass with deterministic settings
  - IndexingResult dataclass for tracking results
  - compute_repo_hash() for change detection
  - should_reindex() to check if re-indexing needed
  - save_index_result() for hash file persistence
  - verify_indexing() to validate KG node counts
  - install_git_hook() / uninstall_git_hook() utilities
- `scripts/self-index.sh` - Self-indexing shell script:
  - --dry-run mode for prerequisite checking
  - --verify mode for node count validation
  - Verbose output with colored logging
  - Neo4j connectivity verification
- `scripts/hooks/post-commit` - Git hook for auto-indexing
- `.github/workflows/ci.yml` - CI pipeline:
  - Test job with Neo4j service container
  - Lint job with flake8/black checks
  - Optional index job triggered by workflow_dispatch
- `tests/test_self_index.py` - 35 unit tests for self-indexing

**Key Features:**
- Canonical project name: "veracity-engine"
- Content hash-based change detection (skip unchanged)
- Git hook for automatic re-indexing after commits
- CI integration for automated testing and indexing
- Verification queries to validate node/edge counts

**Test Results:** 471 tests passing (436 previous + 35 self_index)

### 2025-12-30: STORY-016 Testing and Reproducibility Harness Complete
**Commit**: (pending) - `feat(STORY-016): testing and reproducibility harness`

**New Infrastructure Created:**
- `tests/test_reproducibility.py` - 20 reproducibility tests:
  - File ingestion determinism (discovery, classification, metadata)
  - Chunking determinism (IDs, text chunking, file chunking)
  - Provenance determinism (normalization, hashing, records)
  - Packet determinism (hash stability)
  - Veracity determinism (scoring, validation)
  - Repo map determinism (PageRank, symbol extraction)
  - Fixture integrity tests
- `tests/fixtures/sample_repo/` - Sample repository for integration tests:
  - src/main.py, src/utils.py, src/config.py - Python modules
  - docs/API.md - API documentation
  - README.md - Project overview
- `scripts/run_tests.sh` - Test runner script:
  - Supports modes: all, unit, integration, reproducibility
  - CI mode with coverage reporting
  - JSON output for CI/CD integration
  - Verbose mode option

**Key Features:**
- Determinism validation for all core modules
- Cross-platform text normalization verification (CRLF→LF)
- Stable chunk ID verification
- PageRank reproducibility tests
- Symbol extraction determinism tests
- Fixture-based integration testing

**Test Results:** 436 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 22 packet_contract + 30 veracity + 32 repo_map + 32 taxonomy + 21 ui_evidence + 20 reproducibility + 1 placeholder)

### 2025-12-30: STORY-015 UI Evidence & Provenance Surface Complete
**Commit**: (pending) - `feat(STORY-015): UI evidence panel and provenance components`

**New Infrastructure Created:**
- `ui/src/components/EvidencePanel.jsx` - React component for evidence display:
  - EvidenceItem for individual evidence entries
  - ProvenanceDisplay for provenance metadata
  - VeracitySummary for confidence score display
  - Tab-based navigation (Code Evidence, Documents)
  - Copy-to-clipboard functionality
- `ui/src/components/evidenceUtils.js` - Utility functions:
  - formatTimestamp(), truncateText(), truncateHash()
  - getConfidenceColor(), getDocumentFreshness()
  - validateEvidencePacket(), sortEvidence()
  - hasProvenance(), extractProvenance()
- `tests/test_ui_evidence.py` - 21 Python tests for UI data contracts

**Key Features:**
- Evidence packet rendering with citations and paths
- Provenance fields display (hashes, timestamps, extractor)
- Veracity summary with confidence score and faults
- Evidence-only mode support (no synthesis display)
- UI data contract validation tests

**Test Results:** 416 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 22 packet_contract + 30 veracity + 32 repo_map + 32 taxonomy + 21 ui_evidence + 1 placeholder)

### 2025-12-30: STORY-014 Taxonomy Expansion Complete
**Commit**: (pending) - `feat(STORY-014): taxonomy expansion for APIs and contracts`

**New Infrastructure Created:**
- `core/taxonomy.py` - Extended taxonomy extraction module:
  - NodeType enum (API, CONTRACT, SERVICE, METHOD, etc.)
  - RelationType enum (DEFINES_API, IMPLEMENTS_CONTRACT, etc.)
  - APIEndpoint dataclass with deterministic UID
  - Contract dataclass for schemas/protobufs
  - extract_openapi_endpoints() - OpenAPI/Swagger parsing
  - extract_protobuf_definitions() - Protocol Buffers parsing
  - extract_fastapi_routes() - FastAPI route detection
  - extract_flask_routes() - Flask route detection
  - extract_taxonomy() - Complete extraction pipeline
- `tests/test_taxonomy.py` - 32 unit tests for taxonomy

**Key Features:**
- OpenAPI 3.0 and Swagger 2.0 endpoint extraction
- Protocol Buffers message and service extraction
- FastAPI decorator-based route detection
- Flask @app.route decorator detection
- Deterministic UID generation for all entity types
- Configurable extraction via TaxonomyConfig

**Test Results:** 395 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 22 packet_contract + 30 veracity + 32 repo_map + 32 taxonomy + 1 placeholder)

### 2025-12-30: STORY-013 Repository Map + Structural Ranking Complete
**Commit**: (pending) - `feat(STORY-013): repository map with PageRank ranking`

**New Infrastructure Created:**
- `core/repo_map.py` - Complete repository map module:
  - SymbolKind enum (FUNCTION, CLASS, METHOD, VARIABLE, IMPORT, MODULE)
  - SymbolEntry dataclass with signature and ranking
  - DependencyEdge for import relationships
  - RepoMapConfig with PageRank parameters
  - extract_symbols_from_file() - Python AST extraction
  - extract_imports() - Import statement parsing
  - build_dependency_graph() - File-level dependency graph
  - compute_pagerank() - Deterministic PageRank implementation
  - generate_repo_map() - Complete pipeline with token budgeting
- `tests/test_repo_map.py` - 32 unit tests for repository map

**Key Features:**
- Python AST symbol extraction (functions, classes, methods, variables)
- Import-based dependency graph construction
- PageRank with configurable damping (default: 0.85)
- Deterministic output ordering (rank DESC, path ASC, symbol ASC)
- Token budget packing for context compaction (default: 1024 tokens)
- Provenance via file path tracking

**Test Results:** 363 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 22 packet_contract + 30 veracity + 32 repo_map + 1 placeholder)

### 2025-12-30: STORY-012 Veracity Logic Expansion Complete
**Commit**: (pending) - `feat(STORY-012): veracity logic module with deterministic scoring`

**New Infrastructure Created:**
- `core/veracity.py` - Complete veracity checking module:
  - FaultType enum (STALE_DOC, ORPHANED_NODE, CONTRADICTION, LOW_COVERAGE)
  - VeracityConfig dataclass with configurable thresholds
  - VeracityFault with evidence citation
  - VeracityResult with confidence score and staleness flag
  - check_staleness() - Document age detection (default: 90 days)
  - check_orphans() - Node connectivity check (default: 2 neighbors)
  - check_contradictions() - Doc/code timestamp divergence (default: 30 days)
  - check_coverage() - Result count validation (default: 5 results)
  - compute_confidence_score() - Formula-based scoring
  - validate_veracity() - Complete validation pipeline
- `tests/test_veracity.py` - 30 unit tests for veracity logic

**Key Features:**
- Configurable thresholds (staleness_days, orphan_threshold, contradiction_days)
- Deterministic scoring formula:
  - STALE_DOC: -15 points
  - ORPHANED_NODE: -5 points
  - CONTRADICTION: -20 points
  - LOW_COVERAGE: -10 points
- Evidence citations in all faults (node_id, timestamps, counts)
- Score floored at 0, capped at 100
- Only Document nodes checked for staleness (Code excluded)

**Test Results:** 331 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 22 packet_contract + 30 veracity + 1 placeholder)

### 2025-12-30: STORY-011 Evidence Packet Contract Complete
**Commit**: (pending) - `feat(STORY-011): evidence packet contract with schema v1.0`

**New Infrastructure Created:**
- `core/packet_contract.py` - Versioned packet schema and validation:
  - SCHEMA_VERSION = "1.0" with semver format
  - PacketMeta, CodeResult, DocResult, VeracityReport dataclasses
  - EvidencePacketV1 complete packet structure
  - validate_packet() with required field checks
  - compute_packet_hash() for stable SHA256 hashing
  - create_audit_entry() for audit logging with hash
- `tests/test_packet_contract.py` - 22 unit tests for packet contract

**Key Features:**
- Versioned schema (v1.0) for forward compatibility
- Required field validation for meta, code_truth, doc_claims
- Deterministic packet hashing (sorted JSON serialization)
- Audit entry creation with hash and timestamp
- Schema version mismatch detection

**Test Results:** 301 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 22 packet_contract + 1 placeholder)

### 2025-12-30: STORY-010 Evidence-Only Query Output Complete
**Commit**: (pending) - `feat(STORY-010): evidence-only query output with deterministic ordering`

**New Infrastructure Created:**
- `core/evidence_query.py` - Evidence-based query output module:
  - EvidenceOutputMode enum (EVIDENCE_ONLY, SYNTHESIS)
  - CodeEvidence, DocEvidence dataclasses with provenance fields
  - EvidencePacket for structured output
  - Deterministic sorting (score DESC, path ASC, id ASC)
  - Insufficient evidence handling with predefined actions
  - Packet validation functions
- `tests/test_evidence_query.py` - 26 unit tests for evidence query

**Files Modified:**
- `core/ask_codebase.py` - Integrated evidence-only mode:
  - Added `--evidence-only` flag (default: True)
  - Added `--allow-synthesis` flag (opt-in synthesis mode)
  - Added `--json` flag for raw JSON output
  - Conditional LLM synthesis based on mode

**Key Features:**
- Evidence-only mode is the DEFAULT (no LLM synthesis)
- LLM synthesis requires explicit `--allow-synthesis` flag
- Deterministic result ordering for reproducible outputs
- Structured JSON output with `--json` flag
- Predefined suggested actions (not LLM-generated)
- Mode indicator in output meta block

**Test Results:** 279 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 26 evidence_query + 1 placeholder)

### 2025-12-30: STORY-009 Provenance Model Complete
**Commit**: (pending) - `feat(STORY-009): provenance module with cross-platform hashing`

**New Infrastructure Created:**
- `core/provenance.py` - Complete provenance tracking module:
  - ProvenanceRecord and ProvenanceConfig dataclasses
  - Content normalization for cross-platform hashing (CRLF→LF)
  - File hash (SHA1 of raw bytes for speed/git compatibility)
  - Text hash (SHA256 of normalized content for integrity)
  - Extractor version tracking via VERACITY_VERSION env var
  - Provenance validation and serialization utilities
  - Change detection helper functions
- `tests/test_provenance.py` - 29 unit tests for provenance

**Files Modified:**
- `core/build_graph.py` - Integrated provenance into File and Document nodes:
  - Added provenance fields to File node creation
  - Added provenance fields to Document node creation
  - Updated Neo4j commit logic to persist provenance fields

**Key Features:**
- Cross-platform determinism: CRLF, CR, LF all hash identically
- Dual hashing: SHA1 for file bytes, SHA256 for normalized text
- Extractor versioning via VERACITY_VERSION env var (default: 0.1.0-dev)
- Provenance fields: prov_path, prov_file_hash, prov_text_hash, prov_last_modified, prov_extractor, prov_extractor_version
- Integrated into File and Document nodes in Neo4j

**Test Results:** 253 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 29 provenance + 1 placeholder)

### 2025-12-30: STORY-008 Deterministic Chunking + Embedding Controls Complete
**Commit**: (pending) - `feat(STORY-008): deterministic chunking module with stable IDs`

**New Infrastructure Created:**
- `core/chunking.py` - Comprehensive deterministic chunking module:
  - SplitStrategy enum (PARAGRAPH, LINE, SENTENCE, FIXED)
  - ChunkMetadata and Chunk dataclasses for typed outputs
  - ChunkingConfig with validation and per-file-type defaults
  - ChunkingResult for operation tracking with error handling
  - Deterministic chunk ID generation using SHA256
  - Content hashing for change detection (rechunk_if_changed)
  - Natural split point detection with fallback tolerance
- `tests/test_chunking.py` - 37 unit tests for chunking

**Key Features:**
- Deterministic IDs: SHA256(source_path + ":" + chunk_index + ":" + content_hash)[:16]
- Split strategies respect natural boundaries (paragraphs, lines, sentences)
- Per-extension defaults (code=1000 chars, docs=1500 chars, config=800 chars)
- Overlap support for context continuity between chunks
- Change detection skips unchanged content (hash comparison)
- Reproducible outputs: same inputs always produce same chunks

**Test Results:** 224 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 37 chunking + 1 placeholder)

### 2025-12-30: STORY-007 Index Every File Type Complete
**Commit**: (pending) - `feat(STORY-007): file ingestion module for evidence-first indexing`

**New Infrastructure Created:**
- `core/file_ingestion.py` - Comprehensive file ingestion module:
  - FileCategory enum (Code, Documentation, Config, Data, Infrastructure, Binary)
  - FileMetadata dataclass for deterministic metadata
  - File discovery with .gitignore and security patterns
  - Binary detection (null byte check + UTF-8 decode)
  - Text/binary classification for 100+ extensions
  - Content extraction with truncation support
  - Deterministic UID generation
- `tests/test_file_ingestion.py` - 41 unit tests

**Key Features:**
- Discovers all files respecting .gitignore + security exclusions
- Classifies files by extension and content analysis
- Extracts metadata: hash, MIME type, line count, encoding
- Security patterns exclude .env, .pem, .key, node_modules, etc.
- Deterministic ordering for reproducible ingestion

**Test Results:** 187 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 41 file_ingestion + 1 placeholder)

### 2025-12-30: STORY-006 Multitenancy Isolation Complete
**Commit**: (pending) - `feat(STORY-006): multitenancy isolation with schema and query guards`

**New Infrastructure Created:**
- `core/multitenancy.py` - Tenant isolation module with:
  - TenantViolation/TenantValidationResult dataclasses
  - Schema constraints for composite uniqueness (project, uid)
  - Query guard functions (build_project_scoped_query)
  - Node/relationship validation functions
  - Cross-project edge detection utilities
- `tests/test_multitenancy.py` - 39 unit tests for tenant isolation

**Files Modified:**
- `core/validation.py` - Updated project name format to lowercase slug [a-z0-9._-]+
- `core/build_graph.py` - Integrated multitenancy schema constraints

**Key Features:**
- Project names normalized to lowercase slugs (max 64 chars)
- Composite uniqueness constraint on (project, uid)
- Query guards reject unscoped queries
- Cross-project edge validation with violations reporting
- Integrity check utilities for tenant data

**Test Results:** 146 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infra + 39 multitenancy + 1 placeholder)

### 2025-12-30: STORY-005 Runtime Dependencies + Infra Validation Complete
**Commit**: (pending) - `feat(STORY-005): runtime dependencies and infrastructure validation`

**New Infrastructure Created:**
- `scripts/health-check.sh` - Cross-platform bash health check script
- `scripts/validate-deps.py` - Python dependency validation with JSON output
- `docs/OPERATIONS/VPS_DEPLOYMENT.md` - Complete VPS deployment guide
- `tests/test_infrastructure.py` - 19 unit tests for infrastructure validation

**Key Features:**
- Health check script checks Neo4j, Ollama, disk, memory, Docker
- Validate deps checks Python version, packages, Docker, ports, Ollama models
- Both scripts support --json flag for CI/CD integration
- Cross-platform (Linux and macOS) support

**Test Results:** 107 tests passing (21 config + 16 models + 18 secrets + 32 observability + 19 infrastructure + 1 placeholder)

### 2025-12-30: STORY-004 Observability Infrastructure Complete
**Commit**: (pending) - `feat(STORY-004): observability infrastructure setup`

**New Infrastructure Created:**
- `core/logging.py` - Structured JSON logging with structlog
- `core/metrics.py` - Prometheus-compatible Counter, Gauge, Histogram
- `core/health.py` - Health check HTTP server (/health, /ready, /metrics)
- `tests/test_observability.py` - 32 unit tests

**Files Modified:**
- `requirements.txt` - Added structlog==25.2.0
- `docs/OPERATIONS/MONITORING.md` - Complete observability documentation

**Test Results:** 88 tests passing (21 config + 16 models + 18 secrets + 32 observability + 1 placeholder)

### 2025-12-30: STORY-003 Secrets Management Complete
**Commit**: (pending) - `feat(STORY-003): secrets management and security hardening`

**New Infrastructure Created:**
- `tests/test_secrets.py` - 18 unit tests for secrets management
- `scripts/deploy-vps.sh` - VPS deployment with security checks

**Files Modified:**
- `core/config.py` - Added validate_secrets(), check_env_file_permissions(), redact_config()
- `.gitignore` - Added security patterns (.env.*, *.key, *.pem, secrets/, credentials/)
- `docs/OPERATIONS/SECURITY.md` - Complete security documentation

**Test Results:** 56 tests passing (21 config + 16 models + 18 secrets + 1 placeholder)

### 2025-12-30: STORY-002 Dependency Pinning Complete
**Commit**: (pending) - `feat(STORY-002): dependency pinning and model version control`

**New Infrastructure Created:**
- `core/models.py` - Model version validation with Ollama API integration
- `tests/test_models.py` - 16 unit tests for model versioning
- `scripts/verify_models.py` - CLI verification script
- `requirements-dev.txt` - Development dependencies
- `docs/RUNTIME/MODELS.md` - Model version documentation
- `docs/DEVELOPMENT/DEPENDENCIES.md` - Dependency management guide

**Files Modified:**
- `requirements.txt` - Pinned all versions exactly (neo4j==5.28.2, ollama==0.6.1, etc.)
- `core/config.py` - Added digest, dimensions, top_k, verify_on_startup fields
- `infra/docker-compose.yml` - Neo4j pinned to SHA256 digest

**Test Results:** 38 tests passing (21 config + 16 models + 1 placeholder)

### 2025-12-30: Planning Gap Analysis Session
**Commit**: `2a222d7` - `feat: comprehensive planning gap analysis and architecture pivot`

**New Infrastructure Created:**
- `core/__init__.py` - Package initialization
- `core/embeddings.py` - Consolidated embedding function with determinism support
- `core/validation.py` - Input validation for security (path traversal, injection)
- `tests/` - Test framework (pytest.ini, conftest.py, test_placeholder.py)
- `infra/.env.example` - Environment variable template
- `docs/GLOSSARY.md` - Formal evidence-only definition with test criteria
- `docs/OPERATIONS/` - Deployment, monitoring, security, troubleshooting stubs

**Code Fixes Applied:**
- `core/build_graph.py`: is_async/start_line persistence, VeracityReport schema, error handling
- `core/ask_codebase.py`: os.getenv() credentials, logging, LLM_SEED env var
- `core/generate_codebase_map.py`: Proper logging configuration
- Removed 13 lines of APOC dead code

**Documentation Updated:**
- All 17 story files renumbered with Foundation phase (001-006)
- ARCHITECTURE.md, MANIFEST.md, PRD_GRAPHRAG.md aligned
- 86 gaps identified in comprehensive gap analysis report

## VPS Deployment Requirements (User-Affirmed)

- **Scale**: Expandable architecture; start with 10 projects
- **LLM Strategy**: Self-hosted Ollama; OpenAI API for edge cases/escalations
- **Deployment Target**: VPS (Hostinger or similar) - Docker Compose approach
- **Security**: UID/Pwd for now; Auth spec for backlog (design required, implementation deferred)
