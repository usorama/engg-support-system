# STORY-018: MCP Server for Agent Integration

**Priority**: P0 - BLOCKER
**Status**: COMPLETE
**Created**: 2025-12-31
**Completed**: 2025-12-31
**Dependencies**: STORY-010 (Evidence-Only Query), STORY-011 (Packet Contract)

---

## Problem Statement

The Veracity Engine can index codebases and answer queries, but **AI agents cannot access this knowledge natively**. Agents working inside indexed projects (like pinglearn) must shell out to CLI commands, which:

1. Breaks the agent workflow (context switching)
2. Requires PYTHONPATH configuration
3. Returns unstructured text instead of typed data
4. Cannot be discovered as available tools

**Business Impact**: Agents hallucinate or make assumptions instead of consulting the ground-truth knowledge graph.

---

## Success Criteria

1. Claude Code can discover `veracity:query_codebase` as an MCP tool
2. Queries return deterministic, evidence-based responses
3. Response includes exact file paths, line numbers, and relationships
4. No LLM synthesis in default mode - pure graph evidence
5. Agent can get architectural maps like `UNIFIED-TEACHING-BOARD-MAP.md` quality

---

## Technical Design

### MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code / AI Agent                       │
├─────────────────────────────────────────────────────────────────┤
│  Tool: veracity:query_codebase                                   │
│  Input: {project_name, question, query_type}                     │
│  Output: EvidencePacket (deterministic, no hallucination)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ stdio (JSON-RPC)
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Server (Python)                         │
│  mcp_server.py                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Tools:                                                          │
│  ├── query_codebase(project, question) → EvidencePacket          │
│  ├── get_component_map(project, component) → ArchitectureMap     │
│  ├── get_data_flow(project, source, target) → DataFlowDiagram    │
│  └── list_projects() → ProjectList                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Core Query Engine                            │
│  core/ask_codebase.py → query_graph()                            │
│  core/evidence_query.py → EvidencePacket                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Neo4j Knowledge Graph                        │
│  Nodes: File, Class, Function, Component, Feature                │
│  Relationships: DEFINES, CALLS, IMPORTS, DEPENDS_ON              │
└─────────────────────────────────────────────────────────────────┘
```

### Tool Definitions

#### 1. `query_codebase` (Primary Tool)
```python
@mcp.tool()
def query_codebase(
    project_name: str,
    question: str,
    max_results: int = 20
) -> EvidencePacket:
    """
    Query the knowledge graph for code evidence.

    Returns deterministic, evidence-based results with:
    - Exact file paths and line numbers
    - Code relationships (calls, imports, defines)
    - Veracity score (confidence, staleness, orphans)

    NO LLM synthesis - only graph-derived facts.
    """
```

#### 2. `get_component_map` (Architecture Analysis)
```python
@mcp.tool()
def get_component_map(
    project_name: str,
    component_path: str
) -> ComponentMap:
    """
    Generate comprehensive component analysis like UNIFIED-TEACHING-BOARD-MAP.md.

    Returns:
    - Direct imports (what the component imports)
    - Reverse dependencies (what imports this component)
    - Event bus connections (emitters/consumers)
    - Type definitions used
    - Technical debt flags
    """
```

#### 3. `get_data_flow` (Pipeline Tracing)
```python
@mcp.tool()
def get_data_flow(
    project_name: str,
    source: str,
    target: str
) -> DataFlowDiagram:
    """
    Trace data flow between two points in the codebase.

    Returns:
    - Complete path from source to target
    - Intermediate transformations
    - Event bus hops
    - Type transformations at each step
    """
```

#### 4. `list_projects` (Discovery)
```python
@mcp.tool()
def list_projects() -> list[ProjectInfo]:
    """
    List all indexed projects in the knowledge graph.

    Returns:
    - Project name
    - Last indexed timestamp
    - Node count
    - File count
    """
```

### Output Schema (EvidencePacket)

```python
class EvidencePacket(BaseModel):
    meta: PacketMeta
    status: Literal["success", "insufficient_evidence", "project_not_found"]

    # Deterministic evidence
    code_truth: list[CodeEvidence]      # Functions, classes, imports
    doc_claims: list[DocEvidence]       # Documentation fragments
    graph_relationships: list[Relationship]  # CALLS, IMPORTS, DEFINES

    # Veracity validation
    context_veracity: VeracityReport

    # Actionable guidance
    suggested_actions: list[str]

class CodeEvidence(BaseModel):
    node_type: Literal["File", "Class", "Function", "Import"]
    name: str
    file_path: str
    line_number: int | None
    docstring: str | None
    relationships: list[str]  # What it calls/imports

class VeracityReport(BaseModel):
    confidence_score: float  # 0-100
    is_stale: bool
    faults: list[str]  # STALE_DOC, ORPHANED_NODE, etc.
```

---

## Implementation Plan

### Phase 1: Core MCP Server (4 hours)

1. Create `core/mcp_server.py`
2. Implement `query_codebase` tool wrapping `query_graph()`
3. Add stdio transport
4. Test with `mcp dev`

### Phase 2: Enhanced Tools (4 hours)

1. Implement `get_component_map`
2. Implement `get_data_flow`
3. Implement `list_projects`

### Phase 3: Claude Code Integration (2 hours)

1. Create installation script for MCP config
2. Update `scripts/install.sh` to register MCP server
3. Document agent usage

### Phase 4: Verification (2 hours)

1. Test with pinglearn project
2. Verify deterministic responses
3. Compare output quality to UNIFIED-TEACHING-BOARD-MAP.md

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `core/mcp_server.py` | CREATE | Main MCP server implementation |
| `core/component_map.py` | CREATE | Architecture analysis tool |
| `core/data_flow.py` | CREATE | Data flow tracing tool |
| `scripts/install-mcp.sh` | CREATE | MCP server registration |
| `requirements.txt` | MODIFY | Add `mcp>=1.2.0` |
| `docs/AGENT_INTEGRATION.md` | CREATE | Usage documentation |

---

## Testing Checklist

- [x] `mcp dev core/mcp_server.py` starts without errors
- [x] `list_projects` returns pinglearn (1,664 nodes)
- [x] `query_codebase("pinglearn", "What is the agent?")` returns evidence
- [x] Response includes file paths with line numbers
- [x] Veracity score is calculated correctly (100% confidence)
- [x] Claude Code discovers the tool via MCP config
- [x] No LLM hallucination in responses (deterministic graph data only)

---

## Definition of Done

1. MCP server runs and exposes 4 tools
2. Claude Code can query indexed projects natively
3. Responses match evidence quality of UNIFIED-TEACHING-BOARD-MAP.md
4. Zero LLM synthesis in default mode
5. Documentation complete
6. All tests pass
