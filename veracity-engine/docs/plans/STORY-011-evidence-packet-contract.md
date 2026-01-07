# STORY-007: Evidence Packet Contract (Schema + Validation)

## Outcome
Query outputs are emitted as a strictly validated evidence packet with versioned schema, stable ordering, and zero synthesis. Packets are suitable for agent-to-agent handoff and UI rendering.

## Scope
- Define the evidence packet schema (fields, required/optional).
- Enforce schema validation at query time.
- Add versioning and deterministic ordering rules.
- Define audit log format and validation rules.

## Non-Goals
- Changing KG ingestion logic.
- UI redesign beyond consuming the packet.

## Inputs / References
- `core/ask_codebase.py`
- `docs/ARCHITECTURE.md`
- `docs/PRD_GRAPHRAG.md`

## Definition of Ready (DoR)
- Agreement on packet format (JSON required; XML optional).
- Decision to disable synthesis entirely by default.
- Evidence-only policy confirmed for packet contents.

## Steps (Checklist)
- [x] Define evidence packet schema and version (fields: query, project, results[], citations[], provenance, veracity).
- [x] Specify deterministic ordering rules for results and citations.
- [x] Implement schema validation (pydantic or jsonschema) with hard failure on invalid output.
- [x] Ensure packet contains only evidence-derived fields (no synthesis or inference).
- [x] Store packet in audit logs with a content hash.
- [x] Add docs describing the packet format and guarantees.

## Definition of Done (DoD)
- All query outputs conform to the schema and validate on every run.
- No freeform synthesis is emitted in the default output path.
- Packet hashes are stable for identical inputs.
- Packets contain only evidence-derived fields and citations.

## Tests
- Unit: schema validation for minimum/edge cases.
- Integration: query produces a valid packet with deterministic ordering.
- Regression: snapshot packet hashes for fixed queries.

## Risks
- Schema churn causing downstream breakage.

## Mitigations
- Version the schema and keep backward compatibility.

## Upstream Dependencies
- STORY-006 (evidence-only query output).

## Downstream Impacts
- UI should render from packet instead of raw KG results.

## Change Management
- Rollout: dual-output mode (legacy + packet) for one release.
- Rollback: retain legacy output path behind a flag.

## Research Summary
- Evidence: `core/ask_codebase.py` emits a synthesized "TECHNICAL BRIEF" today.
- Evidence: Audit logs already exist in `.graph_rag/audit/` and can host the packet.

## Decisions
- JSON as the canonical packet format (XML optional).
- Validation library choice.

## Proposed Defaults (Packet Schema v1)
- Format: JSON only, schema version `1.0`.
- Required fields: `meta{schema_version, query_id, timestamp, project, question}`, `results[]`, `citations[]`, `veracity{confidence_score,is_stale,faults}`.
- Result entry: `{id, type, path, start_line, end_line, excerpt, evidence_hash, score, sources[]}`.
- Deterministic ordering: sort by `score desc`, then `path asc`, then `id asc`.

## Blocked / Needs Clarification
- Whether XML is required for agent handoff.
- Define the JSON schema fields and required/optional sections.
- Decide on schema versioning and compatibility policy.
