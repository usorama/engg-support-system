# STORY-010: Repository Map + Structural Ranking (Graph-Based Context)

## Outcome
A deterministic repository map is generated from AST and dependency edges, ranked via graph algorithms (e.g., PageRank), stored as KG artifacts, and used to provide compact, evidence-based context for queries.

## Scope
- Build AST symbol extraction for supported languages.
- Construct dependency graph at file and symbol levels.
- Implement ranking with deterministic inputs and ordering.
- Store repo map in KG as a first-class node with provenance.
- Optional export to markdown as a derived artifact (not source of truth).

## Non-Goals
- LLM-generated summaries in the repo map.
- Runtime code execution or dynamic analysis.

## Inputs / References
- `docs/research/Context Engineering for Large Codebases.md`
- `core/build_graph.py`

## Definition of Ready (DoR)
- Supported languages list agreed based on evidence (repo file inventory).
- AST parser selection (tree-sitter or native parsers) confirmed.
- Token budget and output format defined.
- Evidence-only policy confirmed for repo map outputs (no summaries).

## Steps (Checklist)
- [x] Define repo map output schema (file, symbol, signature, path, provenance).
- [x] Map file inventory to supported language parsers (evidence-based).
- [x] Implement AST extraction per language with deterministic ordering.
- [x] Build dependency graph edges (imports, references, includes).
- [x] Implement graph ranking with PageRank (or equivalent) using fixed parameters.
- [x] Add personalization inputs (mentioned files, active files) with explicit weights.
- [x] Add token-budgeted packing with deterministic cutoff.
- [x] Store repo map artifact in KG as a separate node with provenance.
- [x] If required, export `docs/CODEBASE_MAP.md` as a derived view (optional).

## Definition of Done (DoD)
- Repo map is reproducible with identical input state.
- Ranking outputs are deterministic for the same inputs.
- Repo map entries link to evidence (file paths, symbol signatures).
- Repo map contains no inferred descriptions or synthesized text.

## Tests
- Unit: AST extraction, graph construction, ranking stability.
- Integration: repo map generation on a fixture repo.
- Regression: snapshot of repo map output for stable inputs.

## Risks
- Parser inconsistencies across languages.
- Ranking drift due to nondeterministic ordering.

## Mitigations
- Pin parser versions and enforce stable sorting.
- Use deterministic seed/parameters for ranking.

## Upstream Dependencies
- STORY-003 (file ingestion) for complete file coverage.

## Downstream Impacts
- Query pipeline can use repo map for context compaction.

## Change Management
- Rollout: store repo map without changing query logic until validated.
- Rollback: disable repo map usage if ranking quality regresses.

## Research Summary
- Evidence: No repository map or graph ranking logic exists in `core/build_graph.py` or `core/ask_codebase.py`.
- Evidence: `core/generate_codebase_map.py` only outputs a shallow directory listing, not AST symbols or dependency edges.
- Web research: Aider documents a “repository map” used to provide code context to LLMs. (Source: `docs/research/web/plan-research-notes.md`)

## Decisions
- Parser stack: tree-sitter vs language-specific parsers (evidence + web research).
- Ranking algorithm parameters and token budget definition.
- Repo map storage format and location.
- Tree-sitter is an incremental parsing library, which supports parser selection across languages. (Source: `docs/research/web/plan-research-notes.md`)

## Proposed Defaults (Deterministic Repo Map)
- Supported languages: Python only for v1 (matches current AST support).
- Parser: Python `ast` for v1; tree-sitter later.
- Token budget: 1024 tokens for repo map output (from `docs/research/Context Engineering for Large Codebases.md`).
- Ranking: PageRank damping 0.85, max 100 iterations, deterministic tie-break by path.
- Output format: JSON array of entries `{path, symbol, kind, signature, rank, provenance}` stored in KG.

## Blocked / Needs Clarification
- Supported language list based on repo inventory (needs codebase scan).
- Best-practice repo map compaction strategy (needs web research).
- Confirm parser choice: tree-sitter vs per-language native parsers.
- Define token budget and output format for the repo map.


## Evidence Ledger
- `core/generate_codebase_map.py` only lists directories; no AST or dependencies.
- `core/build_graph.py` lacks repo map generation or ranking.
- Web: Aider repo map concept for context compaction (see `docs/research/web/plan-research-notes.md`).

## Inputs (Exact)
- Files: `core/generate_codebase_map.py`, `core/build_graph.py`.
- Commands: `python3 core/generate_codebase_map.py` (current).
- Config/Env: none currently; to be added.

## Outputs (Exact)
- Files changed/created: `core/generate_codebase_map.py`, optional `docs/CODEBASE_MAP.md`.
- Expected KG nodes/edges: `RepoMap` node with `DERIVED_FROM` edges.
- Artifacts: optional markdown export for human browsing.

## Command Matrix
- Unit Tests: none present in repo.
- Integration Tests: `python3 core/generate_codebase_map.py`.
- Regression Tests: snapshot `docs/CODEBASE_MAP.md` content hash.

## Verification Artifacts
- Evidence files/logs: KG `RepoMap` node and edges; optional `docs/CODEBASE_MAP.md`.
- Snapshot hashes: checksum of repo map output.
- Node/edge counts: if stored in KG, count `RepoMap` nodes.
- Evidence references: core/generate_codebase_map.py, docs/research/web/plan-research-notes.md

## Rollback Procedure
- Revert files: `core/generate_codebase_map.py`, `docs/CODEBASE_MAP.md`.
- Disable flags/config: revert any repo map generation flags.
- Validation after rollback: repo map no longer referenced by queries.

## Change Impact Matrix
- Upstream components: file ingestion (Story-001).
- Downstream components: query compaction and UI context display.
- External dependencies: optional tree-sitter parsers.

## Security & Privacy Constraints
- Secrets handling: do not include secrets in repo map output.
- Data retention/logging: store only structural signatures.
- Access controls: repo map visible in docs and/or KG.

## Data Migration Notes
- Schema/index changes: new node type if stored in KG.
- Backfill requirements: generate map per project.
- Migration verification: compare map output for stable inputs.
