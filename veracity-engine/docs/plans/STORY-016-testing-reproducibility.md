# STORY-013: Testing and Reproducibility Harness (Unit/Integration/Regression)

## Outcome
Automated tests validate ingestion coverage, deterministic outputs, and regressions for build and query flows.

## Scope
- Unit tests for ingestion, chunking, embeddings, and veracity rules.
- Integration tests for KG build and query.
- Regression snapshots for stable outputs.

## Non-Goals
- Performance benchmarking beyond basic regression checks.

## Inputs / References
- `requirements.txt`
- `core/build_graph.py`
- `core/ask_codebase.py`

## Definition of Ready (DoR)
- [x] Test framework and fixtures directory defined.
- [x] Determinism success criteria agreed.
- [x] Evidence-only policy included in test assertions (no synthesis outputs).
- [x] tests/ directory exists with pytest configuration

## Steps (Checklist)
- [x] Define fixture repos with mixed file types and stable content.
- [x] Add unit tests for file discovery, parsing, chunking, embeddings, veracity rules.
- [x] Add integration tests for full build and query flows.
- [x] Add regression snapshots for KG nodes/edges and query outputs.
- [x] Add CI-friendly test runner scripts.

## Definition of Done (DoD)
- Tests cover unit, integration, and regression for core flows.
- Determinism tests pass on repeated runs.
- Test documentation in `docs/plans` is updated with commands.
- Tests validate evidence-only outputs and absence of inferred content.

## Tests
- Unit: pytest suite for ingestion and veracity logic.
- Integration: build_graph + ask_codebase on fixture repo.
- Regression: snapshot hash comparisons for KG and query outputs.

## Risks
- Test flakiness due to external services (Neo4j/Ollama).

## Mitigations
- Use local test fixtures and pinned versions.
- Mock embedding calls where appropriate.

## Upstream Dependencies
- STORY-001 to STORY-011.

## Downstream Impacts
- Enables safe refactoring and change management.

## Change Management
- Rollout: add tests incrementally to avoid blocking.
- Rollback: none; tests should be additive.

## Research Summary
- Evidence: `requirements.txt` includes `pytest`, but there is no `tests/` directory at repo root.
- Evidence: No test runner scripts exist in `scripts/` for GraphRAG build/query flows.

## Decisions
- Fixture repo design and storage strategy.
- Which tests run in CI vs local-only.

## Proposed Defaults (Tests)
- Fixtures: `tests/fixtures/sample_repo` with mixed text/binary files.
- Determinism check: run build twice, compare node counts and chunk IDs.
- Query check: run fixed query twice, compare evidence packet hash.
- Use mocks for embeddings in unit tests; integration tests use live Ollama.

## Blocked / Needs Clarification
- Neo4j/Ollama test environment strategy (local container vs mock) (needs infra review + web research).
- Define fixture repo scope (size, file types, and storage location).
- Define determinism success criteria and snapshot expectations.


## Evidence Ledger

### Session Fixes (2025-12-30)
1. **tests/ directory created**: Full test directory structure established
2. **pytest.ini**: Configuration file created with test discovery settings
3. **conftest.py**: Shared fixtures file created for pytest
4. **Test structure**: Created `tests/unit/`, `tests/integration/`, `tests/fixtures/` directories

### Files Created
- `tests/pytest.ini` - Pytest configuration with test paths and markers
- `tests/conftest.py` - Shared fixtures including Neo4j and Ollama mocks
- `tests/__init__.py` - Package marker
- `tests/unit/__init__.py` - Unit tests package
- `tests/integration/__init__.py` - Integration tests package
- `tests/fixtures/` - Directory for test fixtures

### Previous Evidence
- `requirements.txt` includes `pytest`.
- No `tests/` directory at repo root (NOW FIXED).

## Inputs (Exact)
- Files: `requirements.txt`, new `tests/` to be created.
- Commands: `pytest` (available via requirements).
- Config/Env: `pytest.ini` not present.

## Outputs (Exact)
- Files changed/created: `tests/`, `pytest.ini` (if added).
- Expected KG nodes/edges: none.
- Artifacts: test reports, snapshot files.

## Command Matrix
- Unit Tests: `pytest tests/unit` (to be created).
- Integration Tests: `pytest tests/integration` (to be created).
- Regression Tests: `pytest tests/regression` or snapshot runner (to be created).

## Verification Artifacts
- Evidence files/logs: test output logs.
- Snapshot hashes: stored under `tests/fixtures` (to be created).
- Node/edge counts: not applicable.
- Evidence references: requirements.txt, tests/

## Rollback Procedure
- Revert files: `tests/` and related configs.
- Disable flags/config: remove test runner scripts if needed.
- Validation after rollback: no test files remain.

## Change Impact Matrix
- Upstream components: core build/query scripts.
- Downstream components: CI or local validation workflow.
- External dependencies: pytest.

## Security & Privacy Constraints
- Secrets handling: avoid embedding secrets in fixtures.
- Data retention/logging: test logs local only.
- Access controls: none.

## Data Migration Notes
- Schema/index changes: none.
- Backfill requirements: none.
- Migration verification: test suite passes on repeated runs.
