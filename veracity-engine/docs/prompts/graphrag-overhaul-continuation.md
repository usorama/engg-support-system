<!-- CONTINUATION PROMPT START -->
# 🔄 Continue Previous Session (GraphRAG / Veracity Engine Overhaul)

**Read this entire continuation package before doing any work.**

---

## CONTEXT (Background & Current State)

**Session Information:**
- **Session ID**: `9d34e598`
- **Generated**: 2025-12-29 18:30:53 IST
- **Package File**: `docs/continuation-packages/continuation_20251229_183052.md`
- **Repo**: Git repository root
- **Branch**: `main`
- **Last Commit**: `ab6f28a [INTGAPS-29DEC]: Fix missing os import in LLM modules`
- **Uncommitted Changes**: `3` (see below)

**Uncommitted / Untracked (git status --porcelain):**
```text
 M .graph_rag/audit/audit_202512.jsonl
?? .ai/monitoring-reports/cycle-20251229-181518.md
?? INTEGRATION-GAPS-FIX-SUMMARY.md
```

**Recent activity (last ~8h, sampled):**
```text
./INTEGRATION-GAPS-FIX-SUMMARY.md
./.cursor/debug.log
./.cursor/rules/context-kg.mdc
./.graph_rag/audit/audit_202512.jsonl
./docs/archive/completion-reports/INTEGRATION-GAPS-FIX-SUMMARY.md
./docs/archive/completion-reports/SELF-HEALING-FIX-SUMMARY.md
./docs/archive/completion-reports/README.md
./docs/archive/completion-reports/INTEGRATION-GAPS-ANALYSIS.md
./docs/DOCUMENTATION-AUDIT-2025-12-29.md
./docs/continuation-packages/continuation_20251229_175000.md
./docs/tech-debt/ORPHANED_TABLES.md
./docs/architecture/SYSTEM-ARCHITECTURE.md
./docs/agents.md
./docs/CODEBASE_MAP.md
./.cursorrules
./README.md
./.ai/monitoring-reports/cycle-20251229-140000.md
./.ai/monitoring-reports/cycle-20251229-120000.md
./.ai/monitoring-reports/cron.log
./.ai/monitoring-reports/cycle-20251229-181518.md
./.ai/monitoring-reports/cycle-20251229-103901.md
./.ai/monitoring-reports/cycle-20251229-130000.md
./.ai/monitoring-reports/cycle-20251229-110000.md
./CLAUDE.md
./services/monitoring-daemon/llm/escalation_policy.py
```

**Active TODOs/FIXMEs/WIP (sample):**
- `services/ui/pages/chat.py:306` → `TODO-008: Replace with actual database query for conversation history (see TECH-DEBT-BACKLOG.md)`
- `services/ui/pages/chat.py:675` → `# TODO-015: Parse actual message components to extract text (see TECH-DEBT-BACKLOG.md)`
- `services/observability/analysis/architecture_advisor.py:470` → `contract_coverage=0.0,  # TODO: Calculate from contract registry`
- `core/build_graph.py:344` → `doc_type = ... if "TODO" in f ...`

**Note on tooling:**
- `rg` (ripgrep) is **not installed** in this shell (`command not found: rg`). Use Cursor tool `functions.grep` or install `ripgrep` later if needed.

---

## TASK (Primary Objective)

**Primary Objective (User Requirement):**
- Make the GraphRAG / Knowledge Graph system **index + create embeddings + create links for everything inside every single file inside a project folder**, **regardless of file type**.
- Perform a **comprehensive review** of the system: architecture, dependencies, integrations, and LLM controls so outputs are **100% repeatable / reproducible / deterministic**, with **no hallucinations or assumptions**, **only evidence**.
- **Research first** (code + web), then produce a **thorough, gap-free plan**, **stop and wait for user review/approval**, then implement.

**Task Category:** Architecture / Research / Determinism & Reliability

**Relevant Systems / Code (confirmed in this session):**
- External “Veracity Engine” scripts used by Cursor rules:
  - `./core/build_graph.py`
  - `./core/ask_codebase.py`
- In-repo GraphRAG service also exists (needs review next session):
  - repo root (`core/`, `docs/`, `infra/`, `ui/`)

---

## KEY FINDINGS (Evidence from this session; DO NOT assume beyond this)

### 1) Current indexing is **not** “all files” (only Python + Markdown)

**Evidence: `veracity-engine/core/build_graph.py` only collects `*.py` into `current_files`:**
```python
# ./core/build_graph.py
for f in filenames:
    if f.endswith(".py"):
        current_files.append(os.path.join(root, f))
```

**Evidence: `index_documents()` only indexes `*.md` files:**
```python
# ./core/build_graph.py
for f in filenames:
    if not f.endswith(".md"):
        continue
```

**Impact observed:** Questions about `docker-compose.yml` (YAML) did not retrieve actual compose services because YAML is not indexed as a node/document in the KG query pipeline.

### 2) Current parsing is Python-AST-only

**Evidence: `parse_file()` uses `ast.parse(content)`**, which only works for Python.

### 3) Query CLI (`ask_codebase.py`) includes an LLM synthesis step that can hallucinate

**Evidence: `ask_codebase.py` uses Ollama chat with `model='llama3.2'` to “synthesize” a brief from a JSON context packet:**
```python
# ./core/ask_codebase.py
response = ollama.chat(
    model='llama3.2',
    messages=[{'role': 'user', 'content': prompt}],
    options={'temperature': 0, 'seed': 42, 'repeat_penalty': 1.1}
)
brief = response['message']['content']
print("TECHNICAL BRIEF:")
print(brief)
```

**Impact observed:** LLM-produced “technical brief” output was generic and not grounded in the actual graph context for some questions.

---

## CONSTRAINTS (Quality Gates & Rules)

### 🔴 Hard constraints from user
- **No hallucinations or assumptions. Evidence only.**
- **Research first, then plan. Stop and wait for user approval before implementing.**
- **Determinism & reproducibility are non-negotiable** (same input → same output).
- **Index “everything in every file”, no matter file type** (at minimum: represent each file as a node; for non-text/binary, define deterministic handling).

### 🔴 Project constraints (PingTrade global)
- **Strict typing / no `any`** (where applicable).
- **Evidence-based**: claims must have logs, test outputs, or file-cited proof.

---

## SMART ACTION PLAN (NEXT SESSION — STOP AFTER PLAN FOR USER REVIEW)

### Phase A — Research & system understanding (no code changes yet)
1. Read and map both implementations:
   - `./core/*`
   - `core/*`
2. Determine which one is the “source of truth” used by Cursor workflow (likely the external path; confirm).
3. Audit Neo4j schema, indexes (`code_embeddings`, `code_search`), and how nodes are labeled/stored.
4. Identify determinism risks:
   - Embedding model/version drift
   - Chunking strategy nondeterminism
   - LLM synthesis step nondeterminism / hallucinations
5. Web research (2025 best practices) on:
   - Deterministic embeddings and model pinning
   - Multi-format parsing strategies (YAML/JSON/MD/PDF/etc.)
   - GraphRAG “evidence-only” response patterns (no freeform summaries)

### Phase B — Produce a gap-free design plan (deliverable for user approval)
Plan must specify:
- “Index everything” definition (what for binaries?)
- File ingestion pipeline (text extraction + deterministic chunking)
- Parsers per file type (pluggable)
- Node & relationship model (File → Chunks → Entities → References)
- Embedding generation for:
  - File-level
  - Chunk-level
  - Entity-level (where applicable)
- Query strategy and output format:
  - Prefer raw structured outputs with citations
  - If any LLM remains: strict schema validation + cross-checking against retrieved evidence
- Repeatability controls:
  - Model pinning, hashing, cache keys, deterministic ordering
- Testing & verification:
  - Regression tests proving same query yields same output
  - Snapshot tests for KG build + query
- Migration / backward compatibility plan

### Phase C — WAIT FOR USER REVIEW
Stop here and request approval before implementing.

---

## SUCCESS CRITERIA (for the eventual implementation phase)

1. **Coverage**: Every file under the chosen project root becomes at least one KG node (even if binary → metadata node).
2. **Embeddings**: Deterministic embeddings generated for every eligible text chunk (and optionally file nodes).
3. **Linking**: Deterministic relationships between:
   - Directory hierarchy → files
   - Files → chunks
   - Chunks → extracted entities (where parsers exist)
   - Cross-file references (imports, includes, links, etc.)
4. **Deterministic query outputs**:
   - No freeform “best guess” responses
   - Outputs cite exact file paths + line ranges (or explicit node IDs + evidence excerpts)
5. **Reproducibility**: Re-running build/query yields identical results (validated by automated tests).

---

## ORIGINAL USER CONTEXT (verbatim)

I need graph rag system to index, create embeddings, and link every thing inside every single file inside a project folder, no matter what the file is. Else this system is useless. Need a comprehensive review of the system, architecture, dependencies, integrations, LLM controls such that there's 100% repeatability, reproducability, and responses are deterministic without hallucinations and assumptions, only basis pure evidence. Need proper research of graph rag system code and web before, proper and thorough gaps-free planning, await my review of the plan and then implementation.

<!-- CONTINUATION PROMPT END -->

