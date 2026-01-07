# STORY-006: Evidence-Only Query Output (No Freeform Hallucination)

## Outcome
Query responses are strictly evidence-based, structured, and cite exact file paths and node IDs; optional synthesis is gated and traceable.

## Scope
- Query response schema design.
- Remove or gate LLM synthesis in `core/ask_codebase.py`.
- Add evidence citations and provenance for every claim.

## Non-Goals
- UI redesign.
- Changing embedding models.

## Inputs / References
- `core/ask_codebase.py`
- `docs/prompts/graphrag-overhaul-continuation.md`

## Definition of Ready (DoR)
- Output schema approved (JSON with citations).
- Default mode is evidence-only; synthesis is disabled unless explicitly enabled.
- Evidence-only policy acknowledged for all query outputs.

## Steps (Checklist)
- [x] Define evidence-only output schema with required fields (path, node id, excerpt, relationship).
- [x] Refactor query pipeline to populate evidence fields from KG results.
- [x] Add deterministic ordering for result sets.
- [x] Remove synthesis from the default output path; keep optional synthesis behind an explicit flag.
- [x] If synthesis is enabled, enforce schema validation and include evidence references per sentence.
- [x] Add audit logging for output packets with evidence hashes.

## Definition of Done (DoD)

> **Reference**: See `docs/GLOSSARY.md#evidence-only-mode` for formal definition and all testable criteria.

### Testable Acceptance Criteria (All MUST pass)

#### DoD-1: No LLM Synthesis in Default Mode (TC-EO-001)
- [x] `--evidence-only` flag exists and is the DEFAULT behavior
- [x] When `--evidence-only` is active, `ollama.chat()` is NOT called (lines 237-296 skipped)
- [x] Response packet does NOT contain `technical_brief` field
- [x] Verification: `python3 core/ask_codebase.py --project-name test "query" | jq '.technical_brief'` returns `null`

#### DoD-2: All Content is Graph-Derived (TC-EO-002)
- [x] Every entry in `code_truth[]` has a valid Neo4j node `id` that can be queried directly
- [x] Every entry in `doc_claims[]` has a valid Neo4j node `id`
- [x] No fields contain LLM-generated text
- [x] Verification: Query Neo4j with each returned `id` to confirm existence

#### DoD-3: Explicit Source Citations (TC-EO-003)
- [x] All `code_truth[]` entries include: `id`, `path`, `type`, `name`
- [x] All `doc_claims[]` entries include: `id`, `path`, `last_modified`
- [x] Line numbers (`start_line`, `end_line`) are included when available
- [x] Verification: `jq '.code_truth[] | select(.path == null or .id == null)' output.json` returns empty

#### DoD-4: Deterministic Confidence Scoring (TC-EO-004)
- [x] `confidence_score` computed from graph metrics only (staleness -15, orphan -5)
- [x] No LLM judgment in scoring
- [x] Verification: Score is reproducible for identical graph state

#### DoD-5: Deterministic Ordering (TC-EO-005)
- [x] Results sorted by: `score DESC`, `path ASC`, `id ASC`
- [x] Identical inputs produce identical ordering
- [x] Verification: Run query twice, compare SHA-256 hashes of output
  ```bash
  HASH1=$(python3 core/ask_codebase.py --project-name test "query" --evidence-only | sha256sum)
  HASH2=$(python3 core/ask_codebase.py --project-name test "query" --evidence-only | sha256sum)
  [ "$HASH1" == "$HASH2" ]  # MUST pass
  ```

#### DoD-6: Opt-In Synthesis Mode (TC-EO-001 inverse)
- [x] `--allow-synthesis` flag enables LLM synthesis (opt-in only)
- [x] When synthesis enabled, `technical_brief` is present
- [x] Response includes `"mode": "synthesis"` in meta block
- [x] Each synthesized claim cites evidence sources

#### DoD-7: Insufficient Evidence Handling (TC-EO-007)
- [x] When no graph matches found, response includes `"status": "insufficient_evidence"`
- [x] `suggested_actions` contains pre-defined messages (not LLM-generated)
- [x] Verification: Query with nonsense string, check response status

### Verification Script
```bash
#!/bin/bash
# STORY-010 DoD Verification Script

PROJECT="veracity-engine"
QUERY="test query"

# DoD-1: No technical_brief in evidence-only mode
BRIEF=$(python3 core/ask_codebase.py --project-name "$PROJECT" "$QUERY" --evidence-only 2>/dev/null | jq -r '.technical_brief // "null"')
[ "$BRIEF" == "null" ] && echo "DoD-1: PASS" || echo "DoD-1: FAIL - technical_brief present"

# DoD-5: Deterministic ordering
HASH1=$(python3 core/ask_codebase.py --project-name "$PROJECT" "$QUERY" --evidence-only 2>/dev/null | sha256sum | cut -d' ' -f1)
HASH2=$(python3 core/ask_codebase.py --project-name "$PROJECT" "$QUERY" --evidence-only 2>/dev/null | sha256sum | cut -d' ' -f1)
[ "$HASH1" == "$HASH2" ] && echo "DoD-5: PASS" || echo "DoD-5: FAIL - non-deterministic"

# DoD-7: Insufficient evidence handling
STATUS=$(python3 core/ask_codebase.py --project-name "$PROJECT" "xyzzy_nonexistent_12345" --evidence-only 2>/dev/null | jq -r '.status // .context_veracity.faults[0]')
[[ "$STATUS" == *"insufficient"* ]] || [[ "$STATUS" == *"No relevant"* ]] && echo "DoD-7: PASS" || echo "DoD-7: FAIL"
```

## Tests
- Unit: output schema validation, deterministic ordering.
- Integration: query on stable KG produces stable response.
- Regression: snapshot outputs for fixed queries.

## Risks
- Reduced readability without synthesis.
- Partial evidence leading to empty responses.

## Mitigations
- Provide structured evidence with optional formatting layer.
- Return explicit “insufficient evidence” status when needed.

## Upstream Dependencies
- STORY-003, STORY-004 for complete evidence coverage.

## Downstream Impacts
- UI and consumer tools must adapt to structured evidence outputs.

## Change Management
- Rollout: dual-mode output (legacy + evidence-only) for validation window.
- Rollback: revert to legacy if critical consumers break.

## Research Summary
- Evidence: `core/ask_codebase.py` calls `ollama.chat` with model `llama3.2` to generate a "TECHNICAL BRIEF", which is a synthesis step beyond evidence retrieval.
- Evidence: The synthesized brief is logged in the audit packet (`packet['technical_brief']`).

## Decisions
- Evidence-only output schema (JSON vs XML vs markdown-with-citations).
- Whether to allow synthesis behind a strict flag or remove entirely.

## Proposed Defaults (Evidence-Only Output)
- Output format: JSON only; no XML/markdown in the default path.
- Deterministic ordering: sort by `score desc`, then `path asc`, then `id asc`.
- Default synthesis flag: `--allow-synthesis=false` (off by default).
- Include `insufficient_evidence` status when no results found.

## Blocked / Needs Clarification
- Downstream consumer requirements for output format (needs stakeholder input).
- Evidence citation format best practices (needs web research).
- Confirm evidence packet field list and structure (JSON schema).
- Specify the synthesis flag name and default behavior (default off).


## Evidence Ledger
- `core/ask_codebase.py` uses `ollama.chat` to produce a technical brief.
- Audit packets include `technical_brief` in `.graph_rag/audit` logs.

## Inputs (Exact)
- Files: `core/ask_codebase.py`.
- Commands: `python3 core/ask_codebase.py --project-name <name> "<question>"`.
- Config/Env: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

## Outputs (Exact)
- Files changed/created: `core/ask_codebase.py`.
- Expected KG nodes/edges: `VeracityReport` nodes persisted in Neo4j.
- Artifacts: audit logs in `.graph_rag/audit/`.

## Command Matrix
- Unit Tests: none present in repo.
- Integration Tests: run `python3 core/ask_codebase.py --project-name <name> "<question>"`.
- Regression Tests: compare audit packet outputs for fixed queries.

## Verification Artifacts
- Evidence files/logs: `.graph_rag/audit/audit_YYYYMM.jsonl`.
- Snapshot hashes: audit packet JSON hashes.
- Node/edge counts: `VeracityReport` node count in Neo4j.
- Evidence references: core/ask_codebase.py, .graph_rag/audit

## Rollback Procedure
- Revert files: `core/ask_codebase.py`.
- Disable flags/config: restore previous synthesis behavior if gated.
- Validation after rollback: technical brief prints restored.

## Change Impact Matrix
- Upstream components: KG ingestion coverage.
- Downstream components: UI display of reports and audit logs.
- External dependencies: Ollama chat endpoint (if retained).

## Security & Privacy Constraints
- Secrets handling: avoid logging secrets into audit packets.
- Data retention/logging: audit logs stored locally in `.graph_rag/audit`.
- Access controls: Neo4j credentials via env vars.

## Data Migration Notes
- Schema/index changes: none required unless new report fields added.
- Backfill requirements: optional re-run of queries.
- Migration verification: audit log schema validation.
