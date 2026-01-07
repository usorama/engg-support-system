# STORY-003: Index Every File Type (Evidence-First Ingestion)

## Outcome
Every file in the project root becomes a KG node with deterministic metadata. Text-like files are ingested into chunk nodes; binary files are represented by metadata-only nodes with stable hashing and size/type attributes.

## Scope
- File discovery for all files under the target root (respecting ignore rules and explicit inventory).
- Deterministic file classification and metadata capture.
- Text extraction for supported formats.
- Node/edge creation for File -> Chunk -> Project/Hierarchy.

## Non-Goals
- LLM summarization of file contents.
- Semantic inference beyond evidence.
- UI changes.

## Inputs / References
- `core/build_graph.py`
- `docs/research/Context Engineering for Large Codebases.md`
- `docs/prompts/graphrag-overhaul-continuation.md`

## Definition of Ready (DoR)
- File discovery rules and ignore patterns agreed.
- File type handling policy approved (text vs binary).
- Deterministic hashing approach selected.
- Evidence-based inventory of file extensions in this repo (and representative target repos).
- Evidence-only policy confirmed for ingestion outputs (no inferred metadata).

## Steps (Checklist)
- [x] Inventory file extensions and sizes under the repo root (evidence list to drive parser support).
- [x] Define file discovery rules and ignore list (include repo config, exclude temp/build artifacts).
- [x] Create deterministic file classification table (extension + magic bytes fallback).
- [x] Implement text extraction adapters for: md, txt, json, yaml, toml, ini, xml, js/ts, py, sh, go, java, rs, html, css.
- [x] Implement binary handling: metadata-only nodes with size, hash, mime, last_modified.
- [x] Create chunking interface for text extraction output.
- [x] Update graph builder to scan full root (not just `DEFAULT_TARGET_DIRS`) while honoring ignore rules.
- [x] Update graph builder to create File nodes for every discovered file.
- [x] Add edges: Project/Hierarchy -> File, File -> Chunk.
- [x] Add deterministic ordering for ingestion and chunk creation.
- [x] Add failure logging with file path and reason; do not skip silently.

## Definition of Done (DoD)
- All files under target root are represented as File nodes.
- Text files produce chunk nodes with stable chunk IDs.
- Binary files produce metadata-only nodes with stable IDs.
- Re-running ingestion produces identical node counts and IDs for unchanged files.
- Ingestion metadata is evidence-derived only; no inferred summaries or labels.

## Tests
- Unit: file classification, hashing, extraction per format.
- Integration: build_graph on a fixture repo with mixed file types.
- Regression: snapshot of node counts + IDs for stable inputs.

## Risks
- Inconsistent parsing across formats.
- Binary detection false positives.
- Large files causing memory spikes.

## Mitigations
- Size-based cutoffs and streaming extraction.
- Use deterministic libraries and pinned versions.
- Log skipped/partial extraction with reason codes.

## Upstream Dependencies
- None.

## Downstream Impacts
- Query pipeline must handle Chunk nodes and binary metadata.
- UI and reporting may need updates to display new node types.

## Change Management
- Rollout: behind a feature flag or config gate.
- Rollback: revert to Python-only ingestion path.

## Research Summary
- Evidence: `core/build_graph.py` scans only `DEFAULT_TARGET_DIRS` and collects only `*.py` files into `current_files`, so non-Python files are excluded from file nodes.
- Evidence: `core/build_graph.py:index_documents()` only indexes `*.md` files, so other docs/configs are ignored.
- Evidence: `core/build_graph.py:parse_file()` uses `ast.parse(content)`, so non-Python files fail parsing and are skipped.
- Evidence: `core/build_graph.py:classify_asset()` categorizes files but does not ingest non-Python content.

## Decisions
- Discovery scope: full repo root vs curated target dirs (evidence-based).
- Ignore source of truth: .gitignore vs explicit allow/deny list.
- Binary handling policy: metadata-only vs limited extraction per type.

## Proposed Defaults (Evidence-First)
- Discovery scope: full repo root (not `DEFAULT_TARGET_DIRS`), deterministic path sort.
- Ignore rules: honor `.gitignore` as primary source. Always exclude `.git` plus generated artifacts (`.graph_hashes_*.json`), even if not in `.gitignore`.
- Secrets exclusion: `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.keystore`, `id_rsa`, `id_ed25519` (always excluded).
- File hash: SHA1 of raw bytes (matches current code) for change detection; stable across reruns.
- Binary handling: metadata-only nodes (size, hash, mime) with no text extraction.

## Blocked / Needs Clarification
- Which file types are mandatory for first-pass ingestion (needs repo inventory + web research on reliable parsers).
- Preferred ignore semantics for this repo (needs codebase inspection).
- Is `.gitignore` the authoritative ignore source, or do we maintain an explicit allow/deny list?
- What is the minimum required extension inventory to proceed (repo-only vs representative external repos)?


## Evidence Ledger
- `core/build_graph.py`: `DEFAULT_TARGET_DIRS` limits scan scope.
- `core/build_graph.py`: `current_files` only collects `*.py`.
- `core/build_graph.py`: `index_documents()` only indexes `*.md`.
- `core/build_graph.py`: `ast.parse` used in `parse_file()`.

## Inputs (Exact)
- Files: `core/build_graph.py`, `requirements.txt`.
- Commands: `python3 core/build_graph.py --project-name <name> --root-dir <path>`.
- Config/Env: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `EMBED_MODEL`.

## Outputs (Exact)
- Files changed/created: `core/build_graph.py` (ingestion logic).
- Expected KG nodes/edges: `File` nodes for all files, `HAS_ASSET` edges to hierarchy, `Chunk` nodes (new).
- Artifacts: `.graph_hashes_<project>.json` for change detection.

## Command Matrix
- Unit Tests: none present in repo (see `docs/plans/STORY-013-testing-reproducibility.md`).
- Integration Tests: run `python3 core/build_graph.py --project-name <name> --root-dir <path>`.
- Regression Tests: none present in repo (to be added in STORY-013).

## Verification Artifacts
- Evidence files/logs: `.graph_hashes_<project>.json`, Neo4j node counts via Cypher.
- Snapshot hashes: file hash cache entries in `.graph_hashes_<project>.json`.
- Node/edge counts: `MATCH (n {project: $project}) RETURN count(n)` (manual check).
- Evidence references: core/build_graph.py

## Rollback Procedure
- Revert files: `core/build_graph.py`.
- Disable flags/config: revert any new ingestion flags or env vars.
- Validation after rollback: re-run `python3 core/build_graph.py --project-name <name>` and compare counts.

## Change Impact Matrix
- Upstream components: none.
- Downstream components: `core/ask_codebase.py` query output coverage, UI graph display.
- External dependencies: Neo4j, Ollama embedding endpoint.

## Security & Privacy Constraints
- Secrets handling: do not ingest `.env` or secret files; confirm ignore rules.
- Data retention/logging: audit logs written to `.graph_rag/audit` by `core/ask_codebase.py`.
- Access controls: Neo4j creds via env vars.

## Data Migration Notes
- Schema/index changes: new node labels for chunks may require indexes.
- Backfill requirements: re-run build to ingest all files.
- Migration verification: compare node counts before/after.
