# STORY-011: Taxonomy Expansion (APIs, Contracts, Methods, Services)

## Outcome
KG taxonomy covers required concepts beyond Class/Function: API endpoints, service boundaries, contracts/schemas, and methods, with evidence-backed extraction rules.

## Scope
- Extend node and relationship types to cover APIs, contracts, services, and methods.
- Define deterministic extraction rules per file type.

## Non-Goals
- Heuristic inference without evidence in code or config.
- Runtime tracing.

## Inputs / References
- `core/build_graph.py`
- `docs/ARCHITECTURE.md`

## Definition of Ready (DoR)
- Evidence of where APIs/contracts are defined in this repo (file paths and formats).
- Agreed mapping of taxonomy terms to concrete evidence sources.
- Evidence-only policy confirmed for taxonomy extraction.

## Steps (Checklist)
- [x] Inventory current taxonomy in graph builder and docs (evidence-based list).
- [x] Identify API definitions and contract sources in this repo (e.g., OpenAPI, protobuf, route files).
- [x] Define extraction rules per source type with deterministic parsing.
- [x] Implement new node types and relationships (e.g., Service -> API, API -> Contract, File -> API).
- [x] Update graph schema constraints/indexes as needed.
- [x] Add audit logging for taxonomy extraction.

## Definition of Done (DoD)
- API and contract nodes are created with stable IDs.
- Relationships link services/files to APIs and contracts with evidence paths.
- Re-run produces identical taxonomy for unchanged inputs.
- No taxonomy nodes are created from inference without evidence.

## Tests
- Unit: extraction for API/contract sources.
- Integration: graph build yields expected node counts for fixture inputs.
- Regression: snapshot of taxonomy nodes/edges.

## Risks
- Multiple API formats in the repo.

## Mitigations
- Start with evidence-present formats; expand as additional evidence appears.

## Upstream Dependencies
- STORY-003 (file ingestion).

## Downstream Impacts
- Query and UI must support new node types.

## Change Management
- Rollout: add new node labels without removing existing ones.
- Rollback: disable new extractors via config flag.

## Research Summary
- Evidence: `core/build_graph.py` creates nodes for Capability, Feature, Component, File, Class, Function, and Document only.
- Evidence: No extraction exists for API endpoints or contract schemas in `core/build_graph.py`.

## Decisions
- Taxonomy mapping for APIs/contracts/services in this repo.
- Naming conventions and UID format for new node types.

## Proposed Defaults (Initial Taxonomy Scope)
- In-scope formats: OpenAPI (`openapi.yaml`, `swagger.yaml`) and protobuf (`.proto`).
- API node UID: `api::<path>::<operationId or method+path>`.
- Contract node UID: `contract::<path>::<schema name>`.

## Blocked / Needs Clarification
- Where APIs/contracts are defined (OpenAPI/proto/route files) (needs codebase scan).
- Best-practice extraction rules for each format (needs web research).
- Confirm which API/contract formats are in-scope for the first pass.


## Evidence Ledger
- `core/build_graph.py` creates `Capability`, `Feature`, `Component`, `File`, `Class`, `Function`, `Document` nodes only.
- No API/contract extraction exists in current code (`core/build_graph.py`).

## Inputs (Exact)
- Files: `core/build_graph.py`.
- Commands: `python3 core/build_graph.py --project-name <name> --root-dir <path>`.
- Config/Env: none.

## Outputs (Exact)
- Files changed/created: `core/build_graph.py` (taxonomy extraction).
- Expected KG nodes/edges: new labels for API/Contract/Service/Method.
- Artifacts: updated indexes if added.

## Command Matrix
- Unit Tests: none present in repo.
- Integration Tests: build_graph on repo with API/contract sources.
- Regression Tests: compare taxonomy counts.

## Verification Artifacts
- Evidence files/logs: Neo4j nodes for new labels.
- Snapshot hashes: taxonomy node counts by label.
- Node/edge counts: `MATCH (n:API) RETURN count(n)` etc.
- Evidence references: core/build_graph.py

## Rollback Procedure
- Revert files: `core/build_graph.py`.
- Disable flags/config: revert taxonomy extraction options.
- Validation after rollback: no new label nodes.

## Change Impact Matrix
- Upstream components: file ingestion and parsing.
- Downstream components: query results and UI categorization.
- External dependencies: parsers for API/contract formats.

## Security & Privacy Constraints
- Secrets handling: avoid indexing secrets in contract files.
- Data retention/logging: audit output remains local.
- Access controls: Neo4j credentials via env vars.

## Data Migration Notes
- Schema/index changes: new labels may require indexes.
- Backfill requirements: re-run build to populate new nodes.
- Migration verification: compare label counts.
