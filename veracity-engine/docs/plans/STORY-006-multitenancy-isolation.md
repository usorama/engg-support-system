# STORY-009: Multitenancy Isolation (Schema + Query Guards)

## Outcome
Projects are strictly isolated at the schema and query layers with deterministic guards to prevent cross-tenant data leakage.

## Scope
- Add schema constraints and indexes for `project`.
- Enforce project scoping in all Cypher queries.
- Add validation checks for cross-project edges.

## Non-Goals
- Admin UI for tenant management.
- Multi-DB deployment changes.

## Inputs / References
- `core/build_graph.py`
- `core/ask_codebase.py`
- `docs/ARCHITECTURE.md`

## Definition of Ready (DoR)
- Confirm tenant identifier format and immutability rules.
- Evidence-only policy confirmed for tenant discovery and reporting.

## Steps (Checklist)
- [x] Define a project identity contract (format, allowed chars).
- [x] Add schema constraints and indexes for `project`.
- [x] Enforce project scope in build and query Cypher.
- [x] Add integrity check for cross-project relationships.
- [x] Log and fail on violations with evidence.

## Definition of Done (DoD)
- All nodes and relationships are tagged with project id.
- Queries cannot return data outside the requested project.
- Cross-project edges are prevented or flagged deterministically.
- Tenant reports include evidence for any violations.

## Tests
- Unit: query guards for project scoping.
- Integration: attempt cross-project query returns empty or error.
- Regression: tenant isolation checks on fixture data.

## Risks
- Legacy data without project labels.

## Mitigations
- Provide a backfill or guard-only mode for transition.

## Upstream Dependencies
- STORY-001 (configurable project discovery).

## Downstream Impacts
- UI project selector and query filtering.

## Change Management
- Rollout: guard-only warnings for one release.

## Research Summary
- Evidence: project scoping exists but lacks explicit constraints and guard validation.

## Decisions
- Enforce error vs warning on cross-tenant edges.

## Proposed Defaults (Tenant Isolation)
- Project id format: lowercase slug `[a-z0-9._-]+`, max length 64.
- Enforcement: error on cross-tenant edge creation or query leakage.
- Constraints: composite uniqueness on `(project, uid)` plus index on `project`.

## Blocked / Needs Clarification
- Define tenant identifier format and immutability rules.
- Decide enforcement posture (warn vs error) for cross-tenant edges.
