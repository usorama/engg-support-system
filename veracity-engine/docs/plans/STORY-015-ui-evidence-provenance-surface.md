# STORY-012: UI Evidence & Provenance Surface (Evidence-First UX)

## Outcome
The UI renders evidence packets and provenance fields so users can audit every claim with explicit citations and hashes.

## Scope
- Render evidence packets in the UI with citations.
- Display provenance fields on node detail panels.
- Provide filters for evidence-only results.

## Non-Goals
- Large UI redesign or new visualization framework.

## Inputs / References
- `ui/src/App.jsx`
- `docs/UI_SPEC_KG.md`
- `docs/plans/STORY-007-evidence-packet-contract.md`
- `docs/plans/STORY-005-provenance-model.md`

## Definition of Ready (DoR)
- Evidence packet schema defined and implemented.
- Provenance fields present in KG and packets.
- Evidence-only policy confirmed for UI rendering (no synthesized text).

## Steps (Checklist)
- [x] Add evidence packet fetch path in UI.
- [x] Render evidence list with citations and file paths.
- [x] Show provenance fields (hash, extractor, timestamp) in detail panels.
- [x] Add UI guardrails for evidence-only mode (no synthesis).
- [x] Document UI behavior for evidence review.

## Definition of Done (DoD)
- UI displays evidence packets and provenance for each result.
- Users can audit claims without leaving the UI.
- UI does not render synthesized summaries by default.

## Tests
- Unit: rendering of evidence packets with mocked data.
- Integration: UI displays evidence fields from live KG.

## Risks
- Packet shape changes breaking UI.

## Mitigations
- Versioned schema with compatibility checks in UI.

## Upstream Dependencies
- STORY-007 (evidence packet schema).
- STORY-005 (provenance model).

## Downstream Impacts
- Improves auditability and evidence trust.

## Change Management
- Rollout: feature flag to toggle evidence view.

## Research Summary
- Evidence: current UI shows nodes, faults, and docstrings, but not evidence packets or provenance.

## Decisions
- UI layout for evidence packet and provenance panels.

## Proposed Defaults (UI Evidence)
- Add an "Evidence" tab in the detail panel listing citations with paths and excerpts.
- Display provenance fields (hash, extractor, timestamp) in the detail panel.
- Feature flag: `VITE_EVIDENCE_UI=true` by default.

## Blocked / Needs Clarification
- Confirm UI layout for evidence packet and provenance panels.
- Define feature flag behavior for evidence-only mode in UI.
