# Veracity Engine Glossary

This document defines key terms and concepts used throughout the Veracity Engine project. These definitions serve as testable acceptance criteria for story implementations.

---

## Evidence-Only Mode

### Definition

**Evidence-Only Mode** is the default operating mode for the Veracity Engine query pipeline where responses contain ONLY information that exists in the Neo4j knowledge graph, without any LLM synthesis, interpretation, summarization, or inference.

### Core Principle

> "If it is not in the graph, it is not in the response."

Evidence-only mode enforces that every claim, entity, or relationship in a query response can be traced directly to a specific node or edge in the knowledge graph with an explicit citation.

### Testable Criteria

All of the following criteria MUST be met for a response to be considered "evidence-only":

#### TC-EO-001: No LLM Synthesis API Calls
- [ ] No calls to `ollama.chat()` or equivalent LLM completion APIs during query execution
- [ ] The `technical_brief` field is NOT present in the response packet
- [ ] Lines 237-296 in `core/ask_codebase.py` (LLM synthesis block) are skipped when evidence-only mode is enabled

#### TC-EO-002: Graph-Derived Content Only
- [ ] All `code_truth[]` entries reference existing Neo4j nodes with valid `id` (uid)
- [ ] All `doc_claims[]` entries reference existing Neo4j Document nodes
- [ ] All `graph_relationships[]` entries map to actual Neo4j relationships
- [ ] No fields contain generated/inferred text not present in node properties

#### TC-EO-003: Explicit Source Citations
- [ ] Every entry in `code_truth[]` includes: `path` (file path), `id` (node uid), `type` (node labels)
- [ ] Every entry in `doc_claims[]` includes: `path`, `id`, `last_modified`
- [ ] Line numbers are included when available: `start_line`, `end_line`
- [ ] Citations are verifiable by querying Neo4j directly with the provided `id`

#### TC-EO-004: Deterministic Confidence Scoring
- [ ] `context_veracity.confidence_score` is computed from graph metrics only (staleness, connectivity)
- [ ] Confidence adjustments use fixed values: -15 for STALE_DOC, -5 for ORPHANED_NODE
- [ ] No LLM-based judgment or sentiment analysis in scoring

#### TC-EO-005: Deterministic Ordering
- [ ] Results are sorted by: `score DESC`, then `path ASC`, then `id ASC`
- [ ] Identical inputs produce identical output ordering
- [ ] Ordering algorithm is documented and reproducible

#### TC-EO-006: Structured JSON Output
- [ ] Response conforms to the Evidence Packet schema (see STORY-011)
- [ ] No freeform prose fields (e.g., `summary`, `brief`, `explanation`)
- [ ] Schema version is included in `meta.schema_version`

#### TC-EO-007: Insufficient Evidence Handling
- [ ] When no graph matches are found, response includes `"status": "insufficient_evidence"`
- [ ] Empty results return an explicit status, not null or empty array without explanation
- [ ] Suggested actions (e.g., "Run build_graph.py") are pre-defined, not LLM-generated

### Implementation Requirements

#### Feature Flag
```bash
# CLI flag (default: true for evidence-only)
python3 core/ask_codebase.py --project-name NAME "query" --evidence-only
python3 core/ask_codebase.py --project-name NAME "query" --allow-synthesis  # Opt-in synthesis

# Environment variable
EVIDENCE_ONLY=true  # Default
EVIDENCE_ONLY=false # Enable synthesis
```

#### Code Changes Required (core/ask_codebase.py)
When `--evidence-only` is enabled (default):
1. Skip lines 237-296 (LLM synthesis block)
2. Remove `technical_brief` from packet before logging
3. Add `"mode": "evidence-only"` to `meta` block
4. Return packet directly after `VeracityLogger.log_packet()`

#### Response Packet Structure (Evidence-Only)
```json
{
  "meta": {
    "schema_version": "1.0",
    "query_id": "uuid",
    "timestamp": "ISO8601",
    "project": "string",
    "question": "string",
    "mode": "evidence-only"
  },
  "context_veracity": {
    "confidence_score": 85.0,
    "is_stale": false,
    "faults": []
  },
  "code_truth": [
    {
      "id": "node-uid",
      "name": "entity-name",
      "type": ["Class", "Code"],
      "path": "/path/to/file.py",
      "start_line": 10,
      "end_line": 50,
      "docstring": "extracted docstring",
      "neighbors": ["related-node-1", "related-node-2"]
    }
  ],
  "doc_claims": [
    {
      "id": "doc-node-uid",
      "name": "document-name",
      "type": ["Document"],
      "path": "/path/to/doc.md",
      "last_modified": 1704067200,
      "doc_type": "markdown"
    }
  ],
  "graph_relationships": [
    {"from": "entity-name", "to": "related-entity", "type": "CALLS"}
  ],
  "suggested_actions": [],
  "status": "success"
}
```

### Verification Commands

```bash
# Test TC-EO-001: Verify no LLM calls in evidence-only mode
grep -n "ollama.chat" core/ask_codebase.py  # Should be gated by flag

# Test TC-EO-002: Query should return only graph nodes
python3 core/ask_codebase.py --project-name test "query" --evidence-only | jq '.code_truth[].id'

# Test TC-EO-003: All entries should have path and id
python3 core/ask_codebase.py --project-name test "query" --evidence-only | jq '.code_truth[] | select(.path == null or .id == null)'
# Expected: empty output

# Test TC-EO-005: Deterministic ordering
HASH1=$(python3 core/ask_codebase.py --project-name test "query" --evidence-only | sha256sum)
HASH2=$(python3 core/ask_codebase.py --project-name test "query" --evidence-only | sha256sum)
[ "$HASH1" == "$HASH2" ] && echo "PASS: Deterministic" || echo "FAIL: Non-deterministic"

# Test TC-EO-006: Schema validation
python3 core/ask_codebase.py --project-name test "query" --evidence-only | python3 -c "import sys,json; json.load(sys.stdin)"
```

### Related Stories

| Story | Relationship |
|-------|--------------|
| STORY-010 | Defines evidence-only query output (this is the primary implementation story) |
| STORY-011 | Evidence Packet Contract schema that evidence-only responses must conform to |
| STORY-009 | Provenance model that provides citation metadata for evidence entries |
| STORY-012 | Veracity logic that produces graph-derived confidence scores |
| STORY-015 | UI rendering of evidence-only packets |
| STORY-016 | Testing framework for evidence-only reproducibility |
| STORY-017 | KG self-indexing that ensures graph coverage for evidence |

### Anti-Patterns (What Evidence-Only Mode is NOT)

1. **NOT "reduced synthesis"** - It is zero synthesis, not less synthesis
2. **NOT "best effort citations"** - Every claim MUST have a citation or it is excluded
3. **NOT "optional validation"** - Schema validation failures are hard errors
4. **NOT "LLM-assisted formatting"** - Even formatting is deterministic, not LLM-generated
5. **NOT "confidence from LLM"** - Confidence is graph metrics only

---

## Evidence Packet

### Definition

An **Evidence Packet** is the structured JSON output of an evidence-only query, conforming to a versioned schema with strict validation. See STORY-011 for full schema specification.

### Key Properties
- Versioned schema (`meta.schema_version`)
- Deterministic ordering
- Content hash for audit verification
- Zero synthesis fields

---

## Veracity

### Definition

**Veracity** is a measure of the trustworthiness of graph-derived context, computed from:
1. **Staleness**: Age of Document nodes (>90 days = STALE_DOC)
2. **Connectivity**: Orphaned nodes (<2 neighbors = ORPHANED_NODE)
3. **Contradictions**: Conflicting claims between code and docs (future)

### Scoring Formula
```
confidence_score = 100.0
for each STALE_DOC: confidence_score -= 15
for each ORPHANED_NODE: confidence_score -= 5
confidence_score = max(0.0, min(100.0, confidence_score))
```

---

## Provenance

### Definition

**Provenance** metadata tracks the origin and extraction method for each graph node:
- `source_path`: Original file path
- `content_hash`: SHA-256 of source content
- `extraction_method`: Parser used (e.g., "ast.parse", "markdown")
- `indexed_at`: Timestamp of ingestion

See STORY-009 for implementation details.

---

## Knowledge Graph (KG)

### Definition

The **Knowledge Graph** is a Neo4j graph database storing code entities and their relationships:
- **Nodes**: File, Class, Function, Document, Capability, Feature, Component
- **Relationships**: DEFINES, CALLS, DEPENDS_ON, HAS_ASSET
- **Multitenancy**: Scoped by `project` property on nodes

---

## Synthesis Mode (Opt-In)

### Definition

**Synthesis Mode** is the opt-in alternative to evidence-only mode where LLM-generated content is allowed:
- Enabled via `--allow-synthesis` flag or `EVIDENCE_ONLY=false`
- Adds `technical_brief` field to packet
- Each synthesized claim MUST cite evidence sources
- Clearly marked as `"mode": "synthesis"` in meta

### When to Use
- Human-readable summaries for end users
- Agent handoff requiring narrative context
- Debugging/exploration workflows

### When NOT to Use
- Audit trails requiring deterministic output
- Automated pipelines expecting stable hashes
- Compliance scenarios requiring traceable claims

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-01 | GTCS Team | Initial glossary with Evidence-Only Mode definition |
