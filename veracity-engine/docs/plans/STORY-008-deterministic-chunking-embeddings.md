# STORY-004: Deterministic Chunking + Embedding Controls

## Outcome
Chunks and embeddings are generated with deterministic boundaries, stable IDs, and pinned model versions; reruns produce identical vectors and graph structures when inputs are unchanged.

## Scope
- Chunking strategy for text content.
- Embedding generation controls and caching.
- Deterministic ordering and stable ID generation.

## Non-Goals
- Introducing new LLM-based summarization.
- Changing query UI.

## Inputs / References
- `core/build_graph.py`
- `docs/prompts/graphrag-overhaul-continuation.md`

## Definition of Ready (DoR)
- Chunking strategy agreed (fixed size, delimiter-based, or hybrid).
- Embedding model selection and pinning approved.
- Cache key strategy defined.
- Neo4j vector index dimensions validated against current schema (evidence from `core/build_graph.py`).
- Evidence-only policy confirmed; embeddings derived only from source content.

## Steps (Checklist)
- [x] Define chunking rules (size, overlap, separators) per file type.
- [x] Implement stable chunk ID generation (hash of file path + chunk index + content hash).
- [x] Add deterministic ordering for chunk creation and storage.
- [x] Pin embedding model version and configuration.
- [x] Implement embedding cache with strong keys and TTL policy.
- [x] Store embedding metadata (model name, version, parameters, timestamp).
- [x] Add fallback behavior for empty or oversized chunks.

## Definition of Done (DoD)
- Chunking produces identical outputs on rerun with unchanged inputs.
- Embeddings are identical across reruns with unchanged inputs and pinned model.
- Embedding metadata is persisted for provenance.
- No embedding inputs include synthesized or inferred content.

## Tests
- Unit: chunking boundaries, ID stability, cache key stability.
- Integration: build_graph ingestion produces deterministic chunk/embedding counts.
- Regression: snapshot embedding vectors or hashes for stable inputs.

## Risks
- Embedding model drift or remote service changes.
- Large file chunking performance issues.

## Mitigations
- Pin exact model versions and local inference where possible.
- Limit chunk size and stream processing.

## Upstream Dependencies
- STORY-003 (file ingestion).

## Downstream Impacts
- Query relevance and evidence retrieval quality.

## Change Management
- Rollout: allow dual run (old vs new chunking) and compare outputs.
- Rollback: revert to prior embedding behavior.

## Research Summary
- Evidence: `core/build_graph.py` generates embeddings only for `Class` and `Function` nodes, not file or document nodes.
- Evidence: Vector index is configured for 768 dimensions in `core/build_graph.py`.
- Evidence: Embedding model is set to `nomic-embed-text` in `core/build_graph.py`.
- Web research: Neo4j vector index docs specify vector dimensions and require comparisons to use the same dimensions. (Source: `docs/research/web/plan-research-notes.md`)
- Web research: Ollama API provides `/api/embed` and `/api/embeddings` endpoints with model and dimensions parameters. (Source: `docs/research/web/plan-research-notes.md`)

## Decisions
- Chunking strategy per file type (size/overlap rules).
- Embedding model pinning strategy and cache key schema.
- Whether to embed docs and file nodes in addition to chunks.

## Proposed Defaults (Deterministic Chunking)
- Chunk size: 1200 characters, overlap 200 characters.
- Split order: prefer `\n\n`, then `\n`, then sentence boundary; fall back to hard split.
- Chunk ID: SHA256 of `path + ":" + chunk_index + ":" + chunk_content_hash`.
- Embeddings: `nomic-embed-text`, dimensions 768 (matches current vector index).
- Embed all Chunk nodes and Document nodes; do not embed File nodes.
- Cache key: SHA256 of `model + params + chunk_content_hash`; TTL none (cache forever).

## Blocked / Needs Clarification
- Neo4j vector index constraints and limits for this dataset (needs Neo4j docs research).
- Ollama embedding determinism guarantees for the pinned model (needs web research).
- Define chunking strategy (size, overlap, separators) per file type.
- Pin embedding model version/tag and any parameters that affect determinism.
- Define embedding cache key and TTL policy.


## Evidence Ledger

### Session Fixes (2025-12-30)
1. **Embedding prefix consistency**: Unified embedding prefixes in `core/embeddings.py`
2. **core/embeddings.py**: Created shared module with consistent prefix handling for all embedding operations
3. **Prefix format**: Uses "passage: " and "query: " prefixes consistently across indexing and retrieval

### Files Created
- `core/embeddings.py` - Shared embedding module with:
  - `get_embedding(text, prefix="passage")` function
  - Consistent prefix handling ("passage: " for indexing, "query: " for retrieval)
  - Uses os.getenv() for EMBED_MODEL configuration

### Previous Evidence
- `core/build_graph.py` embeds only Class/Function nodes.
- `core/build_graph.py` configures vector index with 768 dimensions.
- Web: Neo4j vector docs require same dimensions; Ollama embed API supports `dimensions`.

## Inputs (Exact)
- Files: `core/build_graph.py`.
- Commands: `python3 core/build_graph.py --project-name <name> --root-dir <path>`.
- Config/Env: `EMBED_MODEL` (defaults to `nomic-embed-text`).

## Outputs (Exact)
- Files changed/created: `core/build_graph.py` (chunking + embedding).
- Expected KG nodes/edges: `Chunk` nodes with `embedding` property.
- Artifacts: updated vector index and embeddings.

## Command Matrix
- Unit Tests: none present in repo.
- Integration Tests: build_graph run with fixed inputs.
- Regression Tests: compare embedding hash or vector lengths.

## Verification Artifacts
- Evidence files/logs: Neo4j vector index configuration.
- Snapshot hashes: deterministic chunk IDs and embedding hashes.
- Node/edge counts: count `Chunk` nodes.
- Evidence references: core/build_graph.py, docs/research/web/plan-research-notes.md

## Rollback Procedure
- Revert files: `core/build_graph.py`.
- Disable flags/config: revert chunking/embedding flags.
- Validation after rollback: embeddings limited to Class/Function nodes.

## Change Impact Matrix
- Upstream components: file ingestion (Story-001).
- Downstream components: query relevance and vector search.
- External dependencies: Ollama embedding API.

## Security & Privacy Constraints
- Secrets handling: avoid embedding secrets or env files.
- Data retention/logging: embeddings stored in Neo4j.
- Access controls: Neo4j credentials via env vars.

## Data Migration Notes
- Schema/index changes: vector index updates.
- Backfill requirements: re-embed existing nodes.
- Migration verification: index rebuild success logs.
