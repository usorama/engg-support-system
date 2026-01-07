# STORY-005: Provenance Model (Source, Hash, Extraction)

## Outcome
Every KG node and evidence packet entry carries explicit provenance: source path, content hash, extraction method, and timestamp, enabling auditable retrieval and deterministic replay.

## Scope
- Define provenance fields and naming conventions.
- Add provenance to File/Chunk/Document/Class/Function nodes.
- Include provenance in evidence packets.

## Non-Goals
- New parsing logic beyond provenance annotations.
- UI changes beyond exposing provenance fields.

## Inputs / References
- `core/build_graph.py`
- `core/ask_codebase.py`
- `docs/ARCHITECTURE.md`

## Definition of Ready (DoR)
- Provenance field list approved.
- Hashing policy confirmed (content hash vs file hash).
- Evidence-only policy confirmed for provenance population.

## Steps (Checklist)
- [x] Define provenance schema (path, hash, last_modified, extractor, version).
- [x] Add provenance fields to node creation in `core/build_graph.py`.
- [x] Ensure deterministic provenance values for unchanged inputs.
- [x] Include provenance in evidence packet entries.
- [x] Document provenance semantics and guarantees.

## Definition of Done (DoD)
- Nodes and packets include provenance fields with stable values.
- Evidence entries can be traced to exact source files and hashes.
- Provenance values are evidence-derived and deterministic.

## Tests
- Unit: provenance field population and stability.
- Integration: build + query produce provenance in packets.
- Regression: snapshot provenance hashes for stable inputs.

## Risks
- Hash mismatch across platforms (line endings, encoding).

## Mitigations
- Normalize content before hashing and document rules.

## Upstream Dependencies
- STORY-003 (full file ingestion).
- STORY-007 (evidence packet schema).

## Downstream Impacts
- UI and API consumers can display provenance fields.

## Change Management
- Rollout: additive fields; no breaking schema changes.

## Research Summary
- Evidence: current nodes include basic metadata but no explicit provenance contract.

## Decisions
- Hash normalization rules (LF vs CRLF).
- Where to store extractor version identifiers.

## Proposed Defaults (Provenance)
- File hash: SHA1 of raw bytes (matches current change detection).
- Text hash: SHA256 of normalized text with `\n` line endings.
- Extractor version: `VERACITY_VERSION` env var, default `0.1.0-dev`.
- Provenance fields: `path`, `file_hash`, `text_hash`, `last_modified`, `extractor`, `extractor_version`.

## Blocked / Needs Clarification
- Define content normalization rules for hashing (LF vs CRLF, encoding).
- Decide where to store extractor version identifiers.
