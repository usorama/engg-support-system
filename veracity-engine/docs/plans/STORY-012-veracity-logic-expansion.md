# STORY-008: Veracity Logic Expansion (Staleness, Orphans, Contradictions)

## Outcome
Veracity checks cover staleness, orphaned nodes, contradictions, and coverage gaps with deterministic scoring and evidence trails.

## Scope
- Expand `GroundTruthContextSystem` checks.
- Define contradiction heuristics and evidence requirements.
- Add coverage metrics per query result set.

## Non-Goals
- ML-based contradiction detection.

## Inputs / References
- `core/ask_codebase.py`
- `docs/prompts/graphrag-overhaul-continuation.md`

## Definition of Ready (DoR)
- Contradiction heuristics agreed and documented.
- Confidence scoring model defined.
- Evidence-only policy confirmed; veracity rules must cite sources.

## Steps (Checklist)
- [x] Define contradiction checks (doc vs code timestamp, doc claims vs missing code nodes).
- [x] Implement explicit staleness thresholds per node type.
- [x] Add orphan detection based on connectivity and expected edges.
- [x] Add coverage score based on result count vs expected coverage rules.
- [x] Log veracity faults with evidence references.

## Definition of Done (DoD)
- Veracity output includes faults with evidence.
- Confidence scoring is deterministic and reproducible.
- No silent failures or empty fault lists without justification.
- All faults and scores are evidence-derived with explicit citations.

## Tests
- Unit: each veracity rule with fixtures.
- Integration: query returns veracity faults for known conditions.
- Regression: snapshot veracity outputs.

## Risks
- Overly strict rules causing false negatives.

## Mitigations
- Make thresholds configurable with defaults.
- Document rule rationale and evidence path.

## Upstream Dependencies
- STORY-006 (evidence-only output).

## Downstream Impacts
- Consumers must interpret veracity faults and confidence scores.

## Change Management
- Rollout: log-only mode before enforcing strict behavior.
- Rollback: disable specific checks via config flags.

## Research Summary
- Evidence: `core/ask_codebase.py` implements `_check_staleness()` for Document nodes only and `_check_orphans()` using low connectivity.
- Evidence: `_check_contradictions()` is a stub (`pass`) in `core/ask_codebase.py`.

## Decisions
- Contradiction rule set and thresholds.
- Confidence scoring weights per fault type.

## Proposed Defaults (Deterministic Veracity)
- Staleness: Document nodes > 90 days since `last_modified`.
- Orphans: nodes with fewer than 2 neighbors in result set.
- Contradictions: Document linked to Code node where code `last_modified` is > 30 days newer than doc.
- Scoring: STALE -15, ORPHAN -5, CONTRADICTION -20; floor at 0.

## Blocked / Needs Clarification
- Authoritative sources for “truth” in this repo (needs codebase + docs audit).
- Industry patterns for deterministic contradiction checks (needs web research).
- Define contradiction heuristics and thresholds (exact rules).
- Define confidence scoring weights per fault type.


## Evidence Ledger
- `core/ask_codebase.py` implements `_check_staleness()` for Document nodes only.
- `_check_contradictions()` is a stub (`pass`).

## Inputs (Exact)
- Files: `core/ask_codebase.py`.
- Commands: `python3 core/ask_codebase.py --project-name <name> "<question>"`.
- Config/Env: none specific.

## Outputs (Exact)
- Files changed/created: `core/ask_codebase.py` (veracity logic).
- Expected KG nodes/edges: `VeracityReport` with enriched faults.
- Artifacts: updated audit packet fault lists.

## Command Matrix
- Unit Tests: none present in repo.
- Integration Tests: run query and inspect `context_veracity` in output.
- Regression Tests: compare fault lists for fixed queries.

## Verification Artifacts
- Evidence files/logs: `.graph_rag/audit/*.jsonl` entries with faults.
- Snapshot hashes: serialized `context_veracity` blocks.
- Node/edge counts: `VeracityReport` count unchanged.
- Evidence references: core/ask_codebase.py

## Rollback Procedure
- Revert files: `core/ask_codebase.py`.
- Disable flags/config: revert any new checks via config.
- Validation after rollback: faults list reverts to previous behavior.

## Change Impact Matrix
- Upstream components: KG node metadata (timestamps, doc types).
- Downstream components: UI/reporting interpretations.
- External dependencies: none.

## Security & Privacy Constraints
- Secrets handling: avoid embedding sensitive content into fault messages.
- Data retention/logging: faults stored in audit logs.
- Access controls: none beyond Neo4j env.

## Data Migration Notes
- Schema/index changes: none.
- Backfill requirements: none; checks run at query time.
- Migration verification: compare fault outputs.
