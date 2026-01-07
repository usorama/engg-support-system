# STORY-014: KG Self-Indexing + Automation (This Repo in Graph)

## Outcome
This repository is indexed in the KG with deterministic settings, and automation exists to re-index on change.

## Scope
- Define indexing configuration for veracity-engine repo.
- Ensure deterministic build_graph invocation.
- Add automation hooks (optional) for re-indexing.

## Non-Goals
- Remote hosting or deployment automation.

## Inputs / References
- `scripts/install.sh`
- `core/build_graph.py`

## Definition of Ready (DoR)
- Project name and root directory agreed.
- Neo4j/Ollama availability confirmed.
- Codebase map generation configured (see STORY-001).
- Evidence-only policy confirmed for indexed outputs.

## Steps (Checklist)
- [x] Define canonical project name for KG tenant.
- [x] Run build_graph with deterministic settings against repo root.
- [x] Validate nodes/edges count for this repo.
- [x] Add optional automation (git hook or CI job) to refresh KG.
- [x] Document the indexing command in `AGENTS.md` or `docs/plans`.

## Definition of Done (DoD)
- KG contains nodes for this repo with expected coverage.
- Indexing command is documented and reproducible.
- Indexing produces evidence-only nodes and metadata.

## Tests
- Integration: run build_graph and verify node count > 0.
- Regression: verify rerun produces identical node/edge counts.

## Risks
- External dependency availability (Neo4j/Ollama).

## Mitigations
- Provide dry-run checks and clear dependency validation steps.

## Upstream Dependencies
- STORY-003 for full file coverage.
- STORY-001 for configurable paths and project discovery.

## Downstream Impacts
- Enables evidence-based planning and queries for this repo.

## Change Management
- Rollout: manual indexing first, then optional automation.
- Rollback: remove automation and document manual run.

## Research Summary
- Evidence: `scripts/install.sh` runs `core/build_graph.py` and installs a post-commit hook in the target project.
- Evidence: This repo does not have a configured project name or scheduled indexing job yet.

## Decisions
- Canonical project name for this repo in KG.
- Automation trigger: git hook vs scheduled job.

## Proposed Defaults (Self-Indexing)
- Project name: `veracity-engine` (repo basename).
- Automation: post-commit git hook (existing installer behavior).
- Scope: full repo root excluding ignore/secret patterns from STORY-003.

## Blocked / Needs Clarification
- Whether to include `docs/repo-swarm` in indexing scope (needs policy decision).
- Preferred automation method in your environment (needs stakeholder input).
- Confirm canonical project name for this repo in KG.


## Evidence Ledger
- `scripts/install.sh` runs `core/build_graph.py` and installs a post-commit hook in target projects.
- `scripts/setup_service.sh` starts Neo4j/NeoDash via `infra/docker-compose.yml`.

## Inputs (Exact)
- Files: `scripts/install.sh`, `scripts/setup_service.sh`, `core/build_graph.py`.
- Commands: `bash scripts/install.sh` (target project), `python3 core/build_graph.py --project-name <name>`.
- Config/Env: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

## Outputs (Exact)
- Files changed/created: optional git hook in target project; `.graph_hashes_<project>.json`.
- Expected KG nodes/edges: nodes for this repo under chosen project id.
- Artifacts: audit logs if queries run.

## Command Matrix
- Unit Tests: none present in repo.
- Integration Tests: run build_graph for this repo.
- Regression Tests: compare node counts across runs.

## Verification Artifacts
- Evidence files/logs: `.graph_hashes_<project>.json`.
- Snapshot hashes: hash cache entries.
- Node/edge counts: Neo4j counts for project.
- Evidence references: scripts/install.sh, scripts/setup_service.sh

## Rollback Procedure
- Revert files: none in repo unless automation added.
- Disable flags/config: remove git hook in target project.
- Validation after rollback: hook removed, no auto-indexing.

## Change Impact Matrix
- Upstream components: none.
- Downstream components: UI project selector and queries.
- External dependencies: Neo4j, Ollama.

## Security & Privacy Constraints
- Secrets handling: ensure hooks don’t expose env vars.
- Data retention/logging: `.graph_rag/audit` logs per query.
- Access controls: local file system and Neo4j credentials.

## Data Migration Notes
- Schema/index changes: none.
- Backfill requirements: run full build once.
- Migration verification: node counts stable.
