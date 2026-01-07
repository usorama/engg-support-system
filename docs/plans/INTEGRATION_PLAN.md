# Engineering Support System - Integration Plan
## Knowledge-Base + Veracity-Engine Unified Architecture

> **Status**: Planning Phase | **Date**: 2026-01-07 (Revised: Post-review) | **Version**: 1.5 (Multi-agent conversation support + conversational agent implementation)

---

## Executive Summary

This document outlines the comprehensive integration of two powerful systems:

1. **knowledge-base**: Qdrant-based vector storage with Ollama SLMs for semantic search and document retrieval
2. **veracity-engine**: Neo4j-based code graph with deterministic validation and architectural context

**Goal**: Create a unified Engineering Support System that leverages both vector similarity search (Qdrant) and graph relationships (Neo4j) with shared resources (Ollama models) for complete codebase intelligence.

---

## Vision, Objectives, Outcomes

### Vision
To create a **deterministic, evidence-based engineering intelligence system** that provides AI agents with:
- **Complete codebase understanding** through hybrid vector + graph search
- **Ground-truth validation** via veracity checking (staleness, orphans, contradictions)
- **Unified infrastructure** with shared models and resources
- **Multi-tenant capabilities** for supporting multiple projects simultaneously

### Objectives
1. **Integrate Qdrant + Neo4j** for hybrid search capabilities
2. **Share Ollama models** between both systems efficiently
3. **Unify MCP APIs** into a single gateway for AI agents
4. **Create shared infrastructure** with Docker Compose
5. **Implement codebase ingestion** for full triangulated truth
6. **Maintain determinism** throughout all operations

### Outcomes
- Single entry point for AI agents to query codebase intelligence
- **Complementary hybrid storage** (Qdrant vector similarity + Neo4j graph relationships) for triangulated truth: semantic search ("what is similar?") + structural traversal ("what is connected?")
- Shared model resources with **request queuing** (Redis + BullMQ/Celery) for optimal performance, resource utilization, and LLM throughput management
- Modular architecture allowing independent enhancement of each component
- Production-ready deployment on VPS with health checks and monitoring

---

## Current State Analysis

### knowledge-base (Qdrant System)

**Strengths**:
- Production-ready Qdrant vector database (768-dim embeddings)
- FallbackManager for multi-provider orchestration (Ollama VPS → Local → OpenAI)
- MCP server for agent integration
- VPS deployment with Docker Compose
- TypeScript implementation with strict typing

**Limitations**:
- Relationships in payload metadata (Qdrant is vector DB, not graph DB - this is correct architecture)
- Relationship extraction not implemented
- Caching layer incomplete
- Limited to semantic search (no structural context)

### veracity-engine (Neo4j System)

**Strengths**:
- True graph relationships (DEFINES, CALLS, DEPENDS_ON, etc.)
- Veracity validation (STALE_DOCS, ORPHANED_NODES, contradictions)
- Python AST parsing for code structure
- MCP server for Claude Code integration
- File watcher daemon for real-time updates
- NeoDash visualization UI

**Limitations**: (Parser limitations, not Neo4j - solution: add multi-language AST parsers)
- Only indexes .py and .md files
- Python AST parsing only (no TypeScript, Go, etc.)
- No vector similarity search initially
- Alpha status (~15% production-ready)
- Hardcoded credentials in docker-compose

---

## Architecture Rationale - Critical Design Decisions

This section addresses key architectural questions and explains the rationale behind keeping both Qdrant and Neo4j as complementary systems.

### Q1: Why Both Qdrant AND Neo4j? (Complementary, Not Redundant)

**Your Observation**: You correctly identified that "redundant" was wrong terminology. These systems are **complementary**, not redundant.

**Technical Analysis**:

| Capability | Qdrant (Vector DB) | Neo4j (Graph DB) | Verdict |
|------------|-------------------|------------------|---------|
| **Primary Purpose** | Semantic similarity search | Graph relationship traversal |
| **Index Type** | HNSW (Hierarchical Navigable Small World) | Native graph with optional vector index |
| **Query Type** | "What is semantically similar?" | "What is structurally connected?" |
| **Performance (ANN)** | ~10K-100K queries/sec (optimized) | ~1K-5K queries/sec (not primary use case) |
| **Relationship Queries** | Payload metadata filtering | Native Cypher graph traversal |
| **Best For** | Finding similar documents, chunks, embeddings | Finding dependencies, calls, inheritance |
| **Storage Model** | Vector + payload | Property graph (nodes + edges) |

**Why Both Are Needed**:

1. **Qdrant excels at semantic search**:
   - Purpose-built for Approximate Nearest Neighbor (ANN) search
   - HNSW index is 10-100x faster than Neo4j's vector index
   - Optimized for 768-dim embeddings with cosine similarity
   - Use case: "Find all functions similar to `authenticateUser()`"

2. **Neo4j excels at structural relationships**:
   - Native graph database with Cypher query language
   - Efficient traversal of complex relationship patterns
   - Path finding algorithms (shortest path, all paths, etc.)
   - Use case: "Find all functions that CALL `authenticateUser()`"

3. **Together = Triangulated Truth**:
   - Semantic: "This code is about authentication" (Qdrant)
   - Structural: "This code is called by login handlers" (Neo4j)
   - Combined: "This authentication code is semantically relevant AND structurally connected to the login flow"

**Architectural Decision**: **KEEP BOTH** - they serve different primary purposes and together enable capabilities neither could provide alone.

---

### Q2: Do We Need a Queuing System?

**Your Observation**: Yes, we need queuing from both system resource and LLM performance perspectives.

**Technical Analysis**:

**System Resource Constraints**:
- Ollama models have concurrent request limits (typically 2-4 parallel requests per model)
- Docker containers have CPU/memory limits
- Multiple AI agents querying simultaneously = contention
- No built-in request coordination between knowledge-base and veracity-engine

**LLM Performance Constraints**:
- Models have token throughput limits (tokens/second)
- Batch processing is more efficient than individual requests
- Rate limiting prevents OOM (Out of Memory) errors
- Some operations (embeddings) can be batched for efficiency

**Queue Types Required**:

1. **Request Queue** (agent queries):
   - Fair scheduling between multiple agents
   - Priority queues for different query types
   - Backpressure handling when system overloaded

2. **Model Inference Queue** (Ollama requests):
   - Serialize requests to each model
   - Batch embedding requests when possible
   - Prevent model overload

3. **Result Processing Queue** (post-processing):
   - Async result processing (ranking, veracity checks)
   - Decouple query from response processing

**Recommended Solution**:

| Component | Technology | Purpose |
|-----------|------------|---------|
| Queue Backend | Redis | Fast, in-memory, pub/sub |
| TypeScript Queue | BullMQ | For knowledge-base/gateway |
| Python Queue | Celery or RQ | For veracity-engine |
| Priority Queues | Multiple queues | High/medium/low priority |

**Architectural Decision**: **YES - Add queuing system** to Phase 1 infrastructure.

---

### Q3: Should We Use Neo4j and Get Rid of Qdrant?

**Your Observation**: Given Qdrant's "relationships in payload" limitation, should we use only Neo4j?

**Technical Analysis**:

**Qdrant's "Relationships in Payload"**:
- This is NOT a bug or limitation
- Qdrant is a **vector database**, not a graph database
- Payload is for metadata, not graph traversal
- This is correct architecture for a vector DB

**Neo4j's Vector Index**:
- Neo4j 5.x added vector similarity search
- BUT: It's not as optimized as Qdrant
- Neo4j's vector index is ~10-50x slower for pure ANN search
- Neo4j's primary purpose is graph relationships, not vector similarity

**Performance Comparison** (industry benchmarks):

| Operation | Qdrant | Neo4j Vector Index |
|-----------|--------|-------------------|
| 100K-vector ANN search | ~10ms | ~100ms+ |
| 1M-vector ANN search | ~50ms | ~500ms+ |
| Graph traversal (3 hops) | N/A | ~10ms |
| Relationship query | Not supported | ~5ms |

**Cost Considerations**:
- Neo4j is more resource-intensive (Java JVM)
- Neo4j requires more memory for graph operations
- Qdrant is lightweight (Rust) for pure vector operations

**Architectural Decision**: **KEEP BOTH** - use each for their strength:
- Qdrant: Vector similarity search engine (semantic)
- Neo4j: Graph relationship engine (structural)

---

### Q4: Can Neo4j with TypeScript Support Remove Limitations?

**Your Observation**: Can we remove the limitations by adding TypeScript support?

**Root Cause Analysis**:

The limitations listed are NOT in Neo4j - they are in the **PARSER**:

| Limitation | Root Cause | Solution |
|------------|------------|----------|
| Only indexes .py and .md | Python `ast` module only | Add multi-language parsers |
| Python AST parsing only | Parser implementation, not DB | Use universal parser |
| No TypeScript, Go, Rust | Parser limitation | Add language-specific parsers |
| No vector similarity | Graph DB focus | Use Qdrant for vectors |

**Available AST Parsers**:

| Language | Parser | Maturity |
|----------|--------|----------|
| TypeScript/JavaScript | `@typescript-eslint/typescript-estree` | Production |
| TypeScript/JavaScript | `@babel/parser` | Production |
| Go | `go/parser` (standard library) | Production |
| Rust | `syn` crate | Production |
| **Universal** | **`tree-sitter`** | **Production** |

**Recommended Solution: tree-sitter**

`tree-sitter` is a universal parser generator that supports 20+ languages:
- TypeScript, JavaScript, Python, Go, Rust, C, C++, Java, etc.
- Incremental parsing (fast)
- Error-tolerant (handles incomplete code)
- Language-agnostic API

**Architectural Decision**: **No DB change needed** - add `tree-sitter` multi-language parsing to Phase 4.

---

## Summary of Architecture Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Qdrant vs Neo4j? | **Both** (complementary) | Semantic + structural = triangulated truth |
| Queuing system? | **Yes** (Redis + BullMQ/Celery) | Resource + LLM performance management |
| Replace Qdrant with Neo4j? | **No** | 10-100x performance difference for ANN search |
| TypeScript support? | **Yes** (via tree-sitter) | Parser limitation, not DB limitation |

---
---

## Critical Risk Assessment - "Both Together for All Purposes"

**CRITICAL PRINCIPLE**: Both Qdrant AND Neo4j must be used together for EVERY query, ALWAYS. No exceptions.

### 🚨 CRITICAL GAPS IDENTIFIED

#### Gap #1: TWO Separate MCP Servers (HIGH RISK)
**Problem**: 
- Current plan shows knowledge-base MCP server (port 3000) 
- Current plan shows veracity-engine MCP server (separate)
- Agents could connect to EITHER system and get INCOMPLETE answers

**Impact**: 🚨 **SYSTEM BREAKING** - Defeats entire purpose of unified system

**Solution**: 
- **Phase 0** (NEW): Create Unified MCP Gateway FIRST
- Deprecate individual MCP servers
- ALL agents go through ONE gateway that ALWAYS queries both DBs

---

#### Gap #2: Separate Ingestion Pipelines (MEDIUM RISK)
**Problem**:
- knowledge-base has its own ingestion
- veracity-engine has watcher daemon ingestion
- Same file could be ingested twice with different results
- No coordination between pipelines

**Impact**: Data inconsistency, duplicate data, stale data

**Solution**:
- **Single unified ingestion pipeline** for both systems
- One file watcher triggers BOTH Qdrant and Neo4j updates atomically
- Cross-system transaction log

---

#### Gap #3: No "Both Together" Query Logic (CRITICAL)
**Problem**:
- Plan shows 4 separate endpoints: query_knowledge_base, query_code_graph, hybrid_search, validate_veracity
- Agents might call only ONE endpoint and get incomplete answers
- No enforcement of "both together" principle

**Impact**: 🚨 **SYSTEM BREAKING** - Agents get partial answers

**Solution**:
- **ONE endpoint only**: `/query` - ALWAYS queries both DBs
- Remove individual database endpoints
- Gateway internally decides how to combine results
- Agents have NO choice but to get complete answers

---

#### Gap #4: Phase Order Creates Fragmentation (HIGH RISK)
**Problem**:
- Phase 1: Setup both DBs (systems still separate)
- Phase 2: Build unified gateway
- During Phase 1, anyone testing gets SEPARATE systems

**Impact**: Transitional period creates bad patterns, testing is incomplete

**Solution**:
- **Reorder phases**: Gateway FIRST (Phase 0)
- Phase 1: Infrastructure WITH gateway from day one
- No "transitional" period where systems are separate

---

#### Gap #5: No Cross-System References (MEDIUM RISK)
**Problem**:
- Qdrant stores: "this document is about authentication"
- Neo4j stores: "AuthService calls Database"
- No way to link: "this Qdrant document REFERENCES this Neo4j code node"

**Impact**: Can't connect docs to code, incomplete answers

**Solution**:
- Unified node ID system across both systems
- Cross-reference fields in both DBs
- Link document chunks to code nodes bidirectionally

---

#### Gap #6: No Single Source of Truth Strategy (MEDIUM RISK)
**Problem**:
- Who "owns" the code structure data?
- If Neo4j and Qdrant disagree, which is correct?
- No clear authority for different data types

**Impact**: Contradictory answers, confusion

**Solution**:
- **Clear ownership**:
  - Code structure (classes, functions, calls) = Neo4j owns
  - Semantic meaning (embeddings, chunks) = Qdrant owns
  - Cross-references = Both store, Neo4j is authority
- Neo4j node IDs stored in Qdrant payloads
- Qdrant vector IDs stored in Neo4j node properties

---

#### Gap #7: Query Performance Degradation (LOW RISK)
**Problem**:
- Querying BOTH DBs for every request doubles latency
- No caching for cross-system results
- Under load, response times could be unacceptable

**Impact**: Slow responses, user frustration

**Solution**:
- Redis caching for combined results
- Parallel async queries to both DBs
- Timeout handling if one DB is slow
- Cached "popular query" results

---

## Revised Architecture: "Both Together" Enforcement

### Single Unified Endpoint

**BEFORE** (WRONG - allows partial answers):
```
/query/vector    # Only Qdrant - INCOMPLETE
/query/graph     # Only Neo4j - INCOMPLETE  
/query/hybrid    # Both - but agent might choose wrong one
```

**AFTER** (CORRECT - always complete):
```
/query            # ALWAYS queries BOTH DBs
```

### Query Logic (Internal to Gateway - Agents Have No Choice)

```
Agent Request → /query
                  ↓
            ┌─────────────────────┐
            │  Unified Gateway    │
            └─────────────────────┘
                  ↓
        ┌─────────┴─────────┐
        ▼                   ▼
    [Qdrant]            [Neo4j]
    (semantic)          (structural)
        │                   │
        └─────────┬─────────┘
                  ↓
            [Merge & Rank]
            (Both together)
                  ↓
              [Response]
           (Complete answer)
```

### Ingestion Logic (Single Pipeline)

```
File Changed
      ↓
[Unified Ingestion Engine]
      ↓
┌─────────────┴─────────────┐
▼                           ▼
[Qdrant Update]        [Neo4j Update]
(embeddings)          (relationships)
      │                      │
      └──────────┬───────────┘
                 ↓
          [Atomic Commit]
      (Both or neither)
```

---

## Revised Implementation Order

### Phase 0: Unified Gateway (WEEK 0 - CRITICAL PATH)

**MUST BE FIRST** - Before any other work:

1. **Create Unified MCP Gateway**
   - Single `/query` endpoint
   - ALWAYS queries both DBs
   - No option to query just one
   - Returns merged results

2. **Deprecate Individual MCP Servers**
   - knowledge-base MCP server: DEPRECATED
   - veracity-engine MCP server: DEPRECATED
   - All agents MUST use unified gateway

3. **Test "Both Together" Enforcement**
   - Verify every query hits both DBs
   - Verify no partial answers possible
   - Verify failure handling (if one DB down)

### Phase 1: Infrastructure (Revised)

Setup with gateway already in place:
- Docker Compose with all services
- Gateway connects to both DBs
- End-to-end testing: Agent → Gateway → Both DBs → Response

### Phase 2-7: Remaining Work
(Continue with original plan, but gateway already enforces "both together")

---

## "Both Together" Contract

**This is a non-negotiable system contract:**

1. **EVERY query MUST use BOTH databases**
2. **NO exceptions** - not even for "simple" questions
3. **Agent cannot opt out** - gateway enforces automatically
4. **Partial answers = system failure** - not acceptable

**If a query returns results from only one DB, return `status: "partial"` with warnings - not acceptable but handled gracefully.**

---


---

## Integration Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Agent / Claude Code                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Unified MCP Gateway                                                         │
│  ├─ query_knowledge_base()   # Semantic search via Qdrant                  │
│  ├─ query_code_graph()       # Graph traversal via Neo4j                   │
│  ├─ hybrid_search()          # Combined vector + graph                     │
│  └─ validate_veracity()      # Ground-truth checking                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
        │ knowledge-base│  │veracity-engine│  │ Shared        │
        │   (Qdrant)    │  │   (Neo4j)     │  │ Resources     │
        ├───────────────┤  ├───────────────┤  ├───────────────┤
        │ Vector Search │  │ Graph Traversal│  │ Ollama SLMs   │
        │ MCP Server    │  │ MCP Server     │  │ ├─ nomic-embed│
        │ Ingestion     │  │ Watcher Daemon │  │ ├─ llama3.2   │
        │ FallbackMgr   │  │ Veracity Check │  │ ├─ mistral    │
        └───────────────┘  └───────────────┘  │ └─ codeqwen   │
                                     │          └───────────────┘
                                     └──────────────┬────────────┘
                                                    │
                           ┌────────────────────────┼────────────────────────┐
                           ▼                        ▼                        ▼
                ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
                │  Qdrant (6333)   │    │  Neo4j (7474/    │    │  Shared          │
                │  Vector DB       │    │   7687)          │    │  Infrastructure  │
                ├──────────────────┤    ├──────────────────┤    ├──────────────────┤
                │ 768-dim vectors  │    │ Graph Nodes/Edges│    │ Docker Compose   │
                │ Cosine distance  │    │ Vector index     │    │ Health checks    │
                │ UUID v4 IDs      │    │ Project labels   │    │ Monitoring       │
                └──────────────────┘    └──────────────────┘    └──────────────────┘
```

### Data Flow

**Ingestion Flow**:
```
Codebase → AST Parser → Structure Extract →
├─→ Neo4j (relationships, dependencies)
└─→ Qdrant (embeddings, chunks)
```

**Query Flow**:
```
Agent Query → Unified Gateway →
├─→ Qdrant (semantic similarity)
├─→ Neo4j (graph traversal)
└─→ Merge & Rank → Veracity Check → Response
```

---


---

## Comprehensive Failure Scenario Analysis

### Data Migration Strategy

**Current State**:
- Qdrant: Has Claude Code documentation (knowledge-base already ingested)
- Neo4j: May have test data from veracity-engine development

**Migration Plan**:

1. **Qdrant Data Preservation**:
   - Claude Code docs in Qdrant = VALUABLE, keep it
   - This data represents semantic knowledge about Claude Code
   - Will be integrated with Neo4j code structure when ingested

2. **Neo4j Data Cleanup**:
   - Clear existing test data
   - Fresh ingestion of current codebase
   - Use current project as test case

3. **Unified Ingestion** (Current Codebase as Test):
   ```
   Current Project: /home/devuser/Projects/engg-support-system/
   ├── knowledge-base/
   ├── veracity-engine/
   ├── docs/
   └── CLAUDE.md
   
   Ingest → BOTH Qdrant (embeddings) + Neo4j (structure)
   ```

---

### Central Abstraction Layer for LLMs

**Problem**: LLMs need a simple way to query both DBs without understanding complexity

**Solution**: **Query Orchestrator** (Middle Layer Between LLM and DBs)

```
┌─────────────┐                    ┌──────────────┐
│   LLM Agent │ ── Simple Query ──▶│ Query        │
│             │                    │ Orchestrator │
└─────────────┘                    └──────────────┘
                                           │
                    ┌────────────────────────┴────────────────────────┐
                    ▼                        ▼                        ▼
            ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
            │   Qdrant     │        │    Neo4j     │        │    Cache     │
            │  (Semantic)  │        │  (Structural)│        │   (Redis)    │
            └──────────────┘        └──────────────┘        └──────────────┘
```

**Query Orchestrator Responsibilities**:
1. **Simple API for LLMs**:
   ```
   query("How does authentication work?")
   → Returns: Complete answer from both DBs
   
   LLM doesn't need to know:
   - Which DB to query
   - How to merge results
   - How to handle failures
   ```

2. **Automatic "Both Together"**:
   - LLM asks ONE question
   - Orchestrator queries BOTH DBs
   - Merges results automatically
   - Returns complete answer

3. **Failure Handling** (LLM-agnostic):
   - If Qdrant down: Return Neo4j results with warning

---

## Internal Query Agent - Deterministic Contract

**CRITICAL**: We need a formal internal agent that handles the deterministic "both together" process and returns results in a **specific, reproducible structure**.

### Architecture: External Agent → Internal Query Agent → Both DBs

```
┌─────────────────────┐                    ┌──────────────────────┐
│  External Agent     │ ── Standard Query ─▶│ Internal Query Agent │
│  (Claude, GPT, etc) │                    │ (Deterministic)      │
└─────────────────────┘                    └──────────────────────┘
                                                   │
                     ┌──────────────────────────────┴──────────────────────────────┐
                     ▼                                                              ▼
             ┌──────────────────┐                                        ┌──────────────────┐
             │ Qdrant (768-dim) │                                        │   Neo4j (Graph)  │
             │ Semantic Search  │                                        │ Structure Traversal│
             └──────────────────┘                                        └──────────────────┘
                     │                                                              │
                     └──────────────────────────────┬──────────────────────────────┘
                                                    ▼
                                         ┌──────────────────────┐
                                         │  Result Merger       │
                                         │  (Deterministic)     │
                                         └──────────────────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────┐
                                         │  Structured Output   │
                                         │  (Reproducible)      │
                                         └──────────────────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────┐
                                         │ External Agent       │
                                         │ (Standard Response)  │
                                         └──────────────────────┘
```

### Internal Query Agent - Specification

**Name**: `EnggContextAgent` (Engineering Context Agent)

**Purpose**: Deterministic agent that queries both Qdrant + Neo4j and returns structured results.

**Input Contract** (From External Agent):
```typescript
interface QueryRequest {
  query: string;                    // Natural language query
  project?: string;                 // Optional: specific project
  context?: string[];               // Optional: additional context
  requestId: string;                // Unique request ID
  timestamp: string;                // ISO timestamp
}
```

**Output Contract** (To External Agent):
```typescript
interface QueryResponse {
  requestId: string;                // Echo request ID
  status: "success" | "partial" | "unavailable";
  timestamp: string;                // Response timestamp
  
  // ALWAYS included (if available)
  results: {
    semantic: {                     // From Qdrant
      matches: Array<{
        content: string;
        score: number;              // 0-1 confidence
        source: string;             // File path
        type: "code" | "doc" | "comment";
      }>;
    };
    structural: {                   // From Neo4j
      relationships: Array<{
        source: string;             // File/node name
        target: string;             // Related file/node
        type: string;              // Relationship type
        path: string[];            // Full path
      }>;
    };
  };
  
  // Warnings (if partial/unavailable)
  warnings?: string[];
  
  // Fallback message (if unavailable)
  fallbackMessage?: "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH";
  
  // Metadata
  meta: {
    qdrantQueried: boolean;
    neo4jQueried: boolean;
    qdrantLatency: number;         // ms
    neo4jLatency: number;          // ms
    totalLatency: number;          // ms
    cacheHit: boolean;
  };
}
```

---

### Deterministic Behavior Rules

**The Internal Query Agent MUST**:

1. **Always Query Both**:
   ```
   IF qdrant_available AND neo4j_available:
       query both
   ELSE IF qdrant_only:
       query qdrant + add warning
   ELSE IF neo4j_only:
       query neo4j + add warning
   ELSE:
       RETURN "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH"
   ```

2. **Always Return Structure**:
   - Even if empty, return the same structure
   - External agents can ALWAYS parse the response
   - No "surprise" fields or missing fields

3. **Always Include Metadata**:
   - Which DBs were queried
   - Latency for each
   - Cache status
   - Enables debugging and monitoring

4. **Always Explain Partial Results**:
   - If one DB down: explain in `warnings`
   - If data missing: explain what's missing
   - Never return silent failures

5. **Always Provide Fallback**:
   - If system unavailable: return specific message
   - External agent knows to use web/codebase research
   - No ambiguity about what to do next

---

### Example: Normal Response

**Request**:
```json
{
  "query": "How does authentication work?",
  "requestId": "req-123",
  "timestamp": "2026-01-07T10:30:00Z"
}
```

**Response**:
```json
{
  "requestId": "req-123",
  "status": "success",
  "timestamp": "2026-01-07T10:30:00.250Z",
  "results": {
    "semantic": {
      "matches": [
        {
          "content": "AuthService handles user authentication...",
          "score": 0.92,
          "source": "src/auth/AuthService.ts",
          "type": "code"
        },
        {
          "content": "Authentication uses JWT tokens...",
          "score": 0.88,
          "source": "docs/auth-guide.md",
          "type": "doc"
        }
      ]
    },
    "structural": {
      "relationships": [
        {
          "source": "LoginPage.tsx",
          "target": "AuthService",
          "type": "CALLS",
          "path": ["LoginPage.tsx", "AuthService.authenticate", "Database.verifyUser"]
        },
        {
          "source": "AuthService",
          "target": "JWTUtils",
          "type": "DEPENDS_ON",
          "path": ["AuthService", "JWTUtils.signToken"]
        }
      ]
    }
  },
  "meta": {
    "qdrantQueried": true,
    "neo4jQueried": true,
    "qdrantLatency": 45,
    "neo4jLatency": 32,
    "totalLatency": 120,
    "cacheHit": false
  }
}
```

---

### Example: Partial Response (One DB Down)

**Response**:
```json
{
  "requestId": "req-124",
  "status": "partial",
  "timestamp": "2026-01-07T10:31:00.100Z",
  "results": {
    "semantic": {
      "matches": [/* ... Qdrant results ... */]
    },
    "structural": {
      "relationships": []  // Empty - Neo4j unavailable
    }
  },
  "warnings": [
    "⚠️ Neo4j structural search unavailable - returning semantic results only",
    "⚠️ Code relationships and dependencies not included in this response"
  ],
  "meta": {
    "qdrantQueried": true,
    "neo4jQueried": false,
    "qdrantLatency": 50,
    "neo4jLatency": 0,
    "totalLatency": 60,
    "cacheHit": false
  }
}
```

---

### Example: Unavailable Response (Both DBs Down)

**Response**:
```json
{
  "requestId": "req-125",
  "status": "unavailable",
  "timestamp": "2026-01-07T10:32:00.050Z",
  "results": {
    "semantic": {
      "matches": []
    },
    "structural": {
      "relationships": []
    }
  },
  "warnings": [
    "❌ Engineering context system temporarily unavailable",
    "❌ Both Qdrant and Neo4j databases are unreachable"
  ],
  "fallbackMessage": "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH",
  "meta": {
    "qdrantQueried": false,
    "neo4jQueried": false,
    "qdrantLatency": 0,
    "neo4jLatency": 0,
    "totalLatency": 50,
    "cacheHit": false
  }
}
```

**External Agent Behavior**:
Upon receiving `status: "unavailable"`, the external agent (Claude, GPT, etc.) should:
1. Acknowledge the system is unavailable
2. Fall back to web search for external documentation
3. Fall back to codebase search (grep, file reading) for code
4. Inform user about fallback behavior

---

### Internal Agent Implementation

**Files**:
```
engg-support-system/gateway/
├── src/
│   ├── agents/
│   │   ├── EnggContextAgent.ts      # Main agent implementation
│   │   ├── QueryOrchestrator.ts      # Internal query logic
│   │   └── ResultMerger.ts           # Deterministic merge logic
│   ├── types/
│   │   └── agent-contracts.ts        # TypeScript interfaces
│   └── utils/
│       ├── qdrant-client.ts
│       └── neo4j-client.ts
```

**Technology Stack**:
- **TypeScript** (type safety, reproducible structures)
- **Zod** (runtime schema validation)
- **Pino** (structured logging)

---

### Why This Matters

**Without Internal Agent** (Current Plan Gap):
```
External Agent → Gateway → ???
- Unclear what gateway returns
- Unclear how to parse response
- Unclear what to do on failure
```

**With Internal Agent** (Fixed):
```
External Agent → EnggContextAgent → Predictable Structure
- Always returns same structure
- Always parseable
- Always knows what to do on failure
```

---

### Contract Testing

**Critical**: Test the contract with multiple external agents

```typescript
// Test with simulated external agents
const testAgents = [
  "claude-code",
  "claude-api",
  "gpt-4",
  "custom-agent"
];

for (const agent of testAgents) {
  const response = await enggContextAgent.query({
    query: "How does authentication work?",
    requestId: `test-${agent}`,
    timestamp: new Date().toISOString()
  });
  
  // Verify contract
  assert(response.status !== undefined);
  assert(response.results !== undefined);
  assert(response.meta !== undefined);
  assert(typeof response.meta.totalLatency === "number");
}
```

---

## Results Format & Output Strategy - Deterministic Design

**CRITICAL**: How results are returned to AI agents affects usability, performance, and determinism.

### Key Questions to Answer

1. **What format?** (JSON, Markdown, YAML, mixed?)
2. **Streaming or one-shot?** (Chunked vs complete response)
3. **Size limits?** (Min/max bytes based on query type)
4. **Intent inference?** (What if requirements aren't explicit?)
5. **Compression?** (For large result sets)

---

## Format Decision: Structured JSON + Markdown Content

**Chosen Format**: JSON wrapper with Markdown content fields

**Rationale**:
| Format | Pros | Cons | Verdict |
|--------|------|-------|---------|
| Pure JSON | Easy to parse, type-safe | Hard to read, verbose | ❌ |
| Pure Markdown | Human-readable | Hard to parse, unstructured | ❌ |
| Pure YAML | Middle ground | Not standard for APIs | ❌ |
| **JSON + Markdown** | **Structured + readable** | **Slightly more complex** | ✅ **YES** |

---

### Output Structure Specification

```typescript
interface QueryResponse {
  // === Metadata (Always included) ===
  requestId: string;
  status: "success" | "partial" | "unavailable";
  timestamp: string;
  queryType: "code" | "explanation" | "both" | "unknown";
  
  // === Results (Structured) ===
  results: {
    // Semantic matches (Qdrant)
    semantic: {
      summary: string;              // Markdown summary
      matches: Array<{
        content: string;           // Markdown (code block, text, etc.)
        score: number;             // 0-1 confidence
        source: string;            // File path
        lineStart?: number;        // Line numbers for code
        lineEnd?: number;
        type: "code" | "doc" | "comment";
        language?: string;         // For code blocks: "typescript", "python", etc.
      }>;
    };
    
    // Structural relationships (Neo4j)
    structural: {
      summary: string;              // Markdown summary
      relationships: Array<{
        source: string;
        target: string;
        type: string;
        path: string[];
        explanation?: string;      // Markdown explanation
      }>;
    };
    
    // Combined insights (Both together)
    insights?: {
      summary: string;              // Executive summary (Markdown)
      keyFindings: string[];        // Bullet points (Markdown)
      recommendations?: string[];   // Optional (Markdown)
    };
  };
  
  // === Warnings & Fallback ===
  warnings?: string[];
  fallbackMessage?: string;
  
  // === Metadata for Debugging ===
  meta: {
    qdrantQueried: boolean;
    neo4jQueried: boolean;
    qdrantLatency: number;
    neo4jLatency: number;
    totalLatency: number;
    cacheHit: boolean;
    resultSize: {
      totalBytes: number;
      semanticMatches: number;
      structuralRelationships: number;
      compressed: boolean;
    };
  };
}
```

---

## Streaming vs One-Shot Decision

### Decision: **One-Shot by Default, Streaming Available**

**Rationale**:

| Factor | One-Shot | Streaming |
|--------|----------|-----------|
| Simplicity | ✅ Simple | ❌ Complex (chunk handling, errors) |
| Determinism | ✅ Predictable | ⚠️ Depends on chunk order |
| Reliability | ✅ All or nothing | ⚠️ Partial failures possible |
| Performance | ❌ Wait for all | ✅ First results fast |
| Memory | ❌ Holds all in memory | ✅ Streams through |

**Strategy**:
```typescript
// Default: One-shot (deterministic, simple)
const response = await agent.query({ query: "..." });

// Optional: Streaming (for large result sets)
const stream = await agent.queryStream({ query: "..." });
for await (const chunk of stream) {
  // Handle chunks as they arrive
}
```

**When to Stream**:
- Result size > 100KB (configurable)
- Explicitly requested: `stream: true`
- Query type: "explanation" (long-form content)

**When to Use One-Shot**:
- Result size < 100KB
- Query type: "code" (just need the code)
- Default behavior

---

## Data Size Limits (Deterministic Bounds)

### Size Strategy: Configurable per Query Type

```typescript
interface SizeLimits {
  // Absolute limits (prevent abuse)
  maxResponseSize: number;        // Default: 10MB
  maxMatches: number;              // Default: 100 results
  
  // Per-query-type limits
  code: {
    minMatches: 1;                // At least 1 result
    maxMatches: 20;               // Code: fewer, higher quality
    maxBytesPerMatch: 50_000;     // 50KB per code block
  };
  
  explanation: {
    minMatches: 3;                // More context for explanations
    maxMatches: 50;               // Explanations: more results ok
    maxBytesPerMatch: 10_000;     // 10KB per explanation
  };
  
  both: {
    minMatches: 5;                // Need both code + explanation
    maxMatches: 30;               // Balanced
    maxBytesPerMatch: 25_000;     // Medium size
  };
}
```

### Size Enforcement Logic

```typescript
function enforceSizeLimits(
  results: QueryResponse,
  queryType: string,
  limits: SizeLimits
): QueryResponse {
  
  // 1. Check absolute limits
  if (results.meta.resultSize.totalBytes > limits.maxResponseSize) {
    // Truncate results, add warning
    results.warnings = [
      `Response truncated to ${limits.maxResponseSize} bytes`,
      "Use more specific query or request streaming for full results"
    ];
    // Truncate to max limit
    results = truncateToSize(results, limits.maxResponseSize);
  }
  
  // 2. Check per-query-type limits
  const typeLimits = limits[queryType] || limits.both;
  
  if (results.results.semantic.matches.length > typeLimits.maxMatches) {
    // Keep top-k by score
    results.results.semantic.matches = results.results.semantic.matches
      .slice(0, typeLimits.maxMatches);
    results.warnings = [
      `Results limited to top ${typeLimits.maxMatches} matches by relevance`
    ];
  }
  
  // 3. Ensure minimum
  if (results.results.semantic.matches.length < typeLimits.minMatches) {
    // This is a "no results" case
    results.status = "partial";
    results.warnings = [
      "Limited results found",
      "Try rephrasing query or use broader terms"
    ];
  }
  
  return results;
}
```

---

## Intent Inference Strategy

### Problem: Queries Don't Always Specify Requirements

**Examples**:
- "Show me authentication code" → Wants CODE
- "Explain how auth works" → Wants EXPLANATION
- "What is the auth system?" → AMBIGUOUS - might want both

**Solution**: Query Classification + Result Composition

### Query Classification (Deterministic)

```typescript
type QueryIntent = 
  | "code"              // Just show me the code
  | "explanation"       // Explain how it works
  | "both"              // Code + explanation
  | "location"          // Where is this thing?
  | "relationship"      // What connects to this?
  | "unknown";          // Ambiguous, return both

function classifyQuery(query: string): QueryIntent {
  const lowerQuery = query.toLowerCase();
  
  // CODE intent indicators
  if (lowerQuery.match(/show me|code|implement|function|class|source/)) {
    return "code";
  }
  
  // EXPLANATION intent indicators
  if (lowerQuery.match(/explain|how does|why|what is|describe|overview/)) {
    return "explanation";
  }
  
  // LOCATION intent indicators
  if (lowerQuery.match(/where|find|locate|which file/)) {
    return "location";
  }
  
  // RELATIONSHIP intent indicators
  if (lowerQuery.match(/depends on|calls|imports|used by|connected/)) {
    return "relationship";
  }
  
  // AMBIGUOUS - default to both
  return "both";
}
```

### Result Composition Based on Intent

```typescript
function composeResults(
  intent: QueryIntent,
  qdrantResults: SemanticResults,
  neo4jResults: StructuralResults
): QueryResponse {
  
  switch (intent) {
    case "code":
      return {
        queryType: "code",
        results: {
          semantic: {
            summary: "Code matches for your query:",
            matches: qdrantResults.matches.filter(m => m.type === "code"),
            // NO verbose explanations, just code
          },
          structural: {
            summary: "Related code structure:",
            relationships: neo4jResults.relationships,
          },
          // NO insights field for code-only queries
        }
      };
    
    case "explanation":
      return {
        queryType: "explanation",
        results: {
          semantic: {
            summary: "Here's how it works:",
            matches: qdrantResults.matches, // Include docs and comments
            // Include explanations
          },
          structural: {
            summary: "Code relationships:",
            relationships: neo4jResults.relationships,
            explanation: "These components work together as follows...",
          },
          insights: {
            summary: "Executive summary:",
            keyFindings: [
              "• The system uses JWT for authentication",
              "• Code is organized into 3 main modules",
              // ... more insights
            ]
          }
        }
      };
    
    case "both":
    case "unknown":
      return {
        queryType: "both",
        results: {
          // Include everything
          semantic: { /* ... */ },
          structural: { /* ... */ },
          insights: { /* ... */ }
        }
      };
  }
}
```

---

## Response Format Examples by Intent

### Example 1: Code Intent ("Show me authentication code")

**Request**:
```json
{
  "query": "Show me the authentication code",
  "requestId": "req-001"
}
```

**Response** (Compact, code-focused):
```json
{
  "requestId": "req-001",
  "status": "success",
  "queryType": "code",
  "results": {
    "semantic": {
      "summary": "Found authentication code in 3 files",
      "matches": [
        {
          "content": "```typescript\nexport class AuthService {\n  authenticate(username, password) {\n    // JWT auth logic\n  }\n}\n```",
          "score": 0.95,
          "source": "src/auth/AuthService.ts",
          "lineStart": 10,
          "lineEnd": 45,
          "type": "code",
          "language": "typescript"
        }
        // ... more code matches
      ]
    },
    "structural": {
      "summary": "Code structure",
      "relationships": [
        {
          "source": "AuthService.ts",
          "target": "JWTUtils.ts",
          "type": "CALLS",
          "path": ["AuthService.ts:15", "JWTUtils.ts:signToken"]
        }
      ]
    }
    // NO insights field - code queries don't need verbose explanations
  },
  "meta": {
    "resultSize": {
      "totalBytes": 8500,
      "semanticMatches": 3,
      "structuralRelationships": 5
    }
  }
}
```

---

### Example 2: Explanation Intent ("Explain how authentication works")

**Request**:
```json
{
  "query": "Explain how the authentication system works",
  "requestId": "req-002"
}
```

**Response** (Verbose, explanation-focused):
```json
{
  "requestId": "req-002",
  "status": "success",
  "queryType": "explanation",
  "results": {
    "semantic": {
      "summary": "## Authentication System Overview\n\nThe authentication system uses JWT (JSON Web Tokens) for stateless authentication...",
      "matches": [
        {
          "content": "## How JWT Authentication Works\n\n1. User submits credentials\n2. Server validates against database\n3. Server generates JWT token\n4. Client stores token\n5. Client includes token in subsequent requests\n6. Server validates token on each request",
          "score": 0.92,
          "source": "docs/auth-guide.md",
          "type": "doc"
        },
        {
          "content": "```typescript\n// Token validation middleware\nexport function validateToken(req, res, next) {\n  const token = req.headers.authorization?.split(' ')[1];\n  if (!token) return res.status(401).send('Unauthorized');\n  // ... validation logic\n}\n```",
          "score": 0.88,
          "source": "src/middleware/auth.ts",
          "type": "code",
          "language": "typescript"
        }
      ]
    },
    "structural": {
      "summary": "## Code Relationships\n\nThe authentication flow involves these components:",
      "relationships": [
        {
          "source": "LoginPage.tsx",
          "target": "AuthService",
          "type": "CALLS",
          "explanation": "Login page calls authentication service to validate credentials"
        }
      ]
    },
    "insights": {
      "summary": "## Executive Summary\n\nThe authentication system is a JWT-based, stateless authentication mechanism with the following characteristics:",
      "keyFindings": [
        "• **Stateless**: Uses JWT tokens, no server-side session storage",
        "• **Secure**: Passwords hashed with bcrypt (10 rounds)",
        "• **Scalable**: No session synchronization needed across servers",
        "• **Token Expiration**: Access tokens expire after 15 minutes"
      ],
      "recommendations": [
        "• Consider implementing refresh tokens for better UX",
        "• Add rate limiting to prevent brute force attacks"
      ]
    }
  },
  "meta": {
    "resultSize": {
      "totalBytes": 45000,
      "semanticMatches": 8,
      "structuralRelationships": 12
    }
  }
}
```

---

### Example 3: Ambiguous Intent ("What is the authentication system?")

**Request**:
```json
{
  "query": "What is the authentication system?",
  "requestId": "req-003"
}
```

**Response** (Balanced - includes both code and explanation):
```json
{
  "requestId": "req-003",
  "status": "success",
  "queryType": "both",
  "results": {
    "semantic": {
      "summary": "## Authentication System\n\nThe authentication system provides user authentication using JWT tokens...",
      "matches": [
        {
          "content": "```typescript\nexport class AuthService { ... }\n```",
          "score": 0.94,
          "source": "src/auth/AuthService.ts",
          "type": "code"
        },
        {
          "content": "The authentication system supports:\n- Email/password login\n- JWT token generation\n- Token validation\n...",
          "score": 0.89,
          "source": "README.md",
          "type": "doc"
        }
      ]
    },
    "structural": { /* ... */ },
    "insights": {
      "summary": "The authentication system is a JWT-based authentication service...",
      "keyFindings": [
        "• Located in `src/auth/` directory",
        "• Uses bcrypt for password hashing",
        "• Implements JWT token generation and validation"
      ]
    }
  }
}
```

---

## Streaming Format (For Large Results)

### When to Stream

```typescript
// Automatic streaming for large results
if (estimatedResponseSize > 100_000) {  // 100KB
  return streamResponse(query);
}

// Explicit request
if (request.stream === true) {
  return streamResponse(query);
}
```

### Streaming Chunk Format

```typescript
interface StreamChunk {
  chunkId: number;
  totalChunks: number;
  requestId: string;
  type: "metadata" | "results" | "insights" | "completion";
  data: any;
  isFinal: boolean;
}

// Example chunks
{
  "chunkId": 1,
  "totalChunks": 5,
  "requestId": "req-004",
  "type": "metadata",
  "data": { status: "success", queryType: "explanation" },
  "isFinal": false
}

{
  "chunkId": 2,
  "totalChunks": 5,
  "requestId": "req-004",
  "type": "results",
  "data": { semantic: { /* partial results */ } },
  "isFinal": false
}

// ... more chunks ...

{
  "chunkId": 5,
  "totalChunks": 5,
  "requestId": "req-004",
  "type": "completion",
  "data": { meta: { /* final metadata */ } },
  "isFinal": true  // Signal end of stream
}
```

---

## Compression Strategy (For Large Responses)

### When to Compress

```typescript
if (responseSize > 1_000_000) {  // 1MB
  response.compression = "gzip";
  response.compressedSize = compressedSize;
}
```

### Compression Header

```typescript
interface CompressedResponse {
  compressed: true;
  compressionType: "gzip" | "brotli";
  originalSize: number;
  compressedSize: number;
  encoding: "base64";
  data: string;  // Compressed, base64-encoded JSON
}
```

---

## Determinism Guarantees

**For Same Query, Always Get**:
1. ✅ Same structure (field names, nesting)
2. ✅ Same format (JSON + Markdown content)
3. ✅ Same size limits (enforced deterministically)
4. ✅ Same intent classification (deterministic rules)
5. ✅ Same ordering (results sorted by score, then source)

**What CAN Vary** (Non-deterministic):
- ⚠️ Exact match scores (embedding model variations)
- ⚠️ Result order for ties (same score = undefined order)
- ⚠️ Response timing (latency varies)

---

## Summary: Results Format Strategy

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Format** | JSON + Markdown content | Structured + readable |
| **Delivery** | One-shot default, streaming optional | Simplicity + flexibility |
| **Size limits** | Per-query-type, configurable | Prevent abuse, ensure usefulness |
| **Intent inference** | Deterministic classification + composition | Handle ambiguous queries gracefully |
| **Compression** | Auto-compress > 1MB | Handle large result sets |
| **Determinism** | Structure, format, limits guaranteed | Predictable for agents |

---

---

## Multi-Agent Conversation Support

**Related Documents**:
- **Research**: [docs/research/multi-agent-conversation-patterns-2026.md](../research/multi-agent-conversation-patterns-2026.md)
- **Implementation**: [docs/plans/CONVERSATIONAL_AGENT_IMPLEMENTATION.md](./CONVERSATIONAL_AGENT_IMPLEMENTATION.md)

### Overview

The EnggContextAgent supports **optional conversational mode** for handling ambiguous queries through back-and-forth dialogue with the requesting agent.

**Key Principle**: One-shot mode is DEFAULT; conversational mode is OPTIONAL enhancement.

### When Conversational Mode Activates

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Auto-detect** | Query has >2 ambiguous indicators | Suggest conversational mode |
| **Explicit request** | `mode: "conversational"` in request | Start conversation |
| **Low confidence** | Intent classification confidence < 0.5 | Ask clarifications |
| **User override** | `mode: "one-shot"` always | Force one-shot response |

### Conversation Flow

```
Round 1: Agent Query
  ↓
Query Analysis (Ambiguity Detection)
  ↓
[If Ambiguous]
  ↓
Round 1 Response: Clarification Questions
  ↓
Round 2: Agent Answers
  ↓
Query Enhancement (incorporate context)
  ↓
Round 2 Response: Final Results
```

**Max Rounds**: 2 (Phase 0b), 3 (Phase 1+)
**Max Duration**: 30 seconds
**Fallback**: One-shot with best-guess if limits exceeded

### Implementation Phases

| Phase | Focus | Location |
|-------|-------|----------|
| **Phase 0b** | Basic conversational mode | See [CONVERSATIONAL_AGENT_IMPLEMENTATION.md](./CONVERSATIONAL_AGENT_IMPLEMENTATION.md#phase-0b-basic-conversational-mode-week-0b) |
| **Phase 1** | Redis state storage | See [CONVERSATIONAL_AGENT_IMPLEMENTATION.md](./CONVERSATIONAL_AGENT_IMPLEMENTATION.md#phase-1-enhancement-redis-state-storage-week-1) |
| **Phase 2-3** | Feature integration | See [CONVERSATIONAL_AGENT_IMPLEMENTATION.md](./CONVERSATIONAL_AGENT_IMPLEMENTATION.md#phase-2-3-integration-feature-enhancement-weeks-2-3) |
| **Phase 4+** | Advanced features | See [CONVERSATIONAL_AGENT_IMPLEMENTATION.md](./CONVERSATIONAL_AGENT_IMPLEMENTATION.md#phase-4-advanced-features-week-4) |

### API Examples

**One-Shot Request** (Default):
```json
{
  "query": "Show me the AuthService class",
  "requestId": "req-001"
}
```

**Conversational Request**:
```json
{
  "query": "What about the auth system?",
  "mode": "conversational",
  "requestId": "req-002"
}
```

**Response** (Round 1 - Clarification):
```json
{
  "type": "conversation",
  "conversationId": "conv-123",
  "round": 1,
  "maxRounds": 3,
  "clarifications": {
    "questions": [
      {
        "id": "aspect",
        "question": "What aspect of authentication?",
        "options": ["How it works", "Code", "Config", "Changes"],
        "required": true
      }
    ]
  }
}
```

**Continue Conversation** (Round 2):
```json
{
  "conversationId": "conv-123",
  "answers": {
    "aspect": "How it works"
  }
}
```

### Impact on Determinism

| Factor | One-Shot | Conversational |
|--------|----------|---------------|
| **Predictability** | HIGH (same query = same response) | MEDIUM (conversation path matters) |
| **Latency** | LOW (~100-500ms) | MEDIUM (~500ms-5s) |
| **Cacheability** | HIGH (response cacheable) | LOW (conversation state) |
| **Use When** | **Default (80%+ of queries)** | Ambiguous queries only |

### Success Metrics

- **Target**: 80%+ of queries use one-shot mode
- **Ambiguous detection**: 90%+ accuracy
- **Conversation completion**: >95%
- **Average rounds**: 2 (not 3)
- **Satisfaction**: >90%

---



---

   - If Neo4j down: Return Qdrant results with warning
   - If both down: Return cached results or error
   - LLM doesn't need to handle these cases

---

### ALL Failure Scenarios (Ultra-Thinking)

#### Scenario 1: One Database Down
**Qdrant Down, Neo4j Up**:
```
Query → Orchestrator
       → Qdrant: ❌ Connection refused
       → Neo4j: ✅ Returns structure
       → Result: Structural data + "⚠️ Semantic search unavailable"
       → LLM gets partial answer with warning
```

**Neo4j Down, Qdrant Up**:
```
Query → Orchestrator
       → Qdrant: ✅ Returns semantic results
       → Neo4j: ❌ Connection refused
       → Result: Semantic data + "⚠️ Structural search unavailable"
       → LLM gets partial answer with warning
```

**Mitigation**:
- Graceful degradation
- Clear warnings to LLM
- Cache recent results for fallback

---

#### Scenario 2: Both Databases Down
```
Query → Orchestrator
       → Qdrant: ❌ Down
       → Neo4j: ❌ Down
       → Fallback 1: Redis cache
       → Fallback 2: "System temporarily unavailable, retry in 30s"
```

**Mitigation**:
- Redis cache of recent queries
- Health check endpoints
- Auto-retry with exponential backoff

---

#### Scenario 3: Slow Response (One DB Lagging)
```
Query → Orchestrator
       → Qdrant: 100ms (normal)
       → Neo4j: 5000ms (slow!)
       → Decision: Wait for Neo4j or return partial?
       
Strategy:
- If timeout < 3s: Wait for both
- If timeout > 3s: Return Qdrant + "⚠️ Structural data delayed"
- Background: Continue fetching Neo4j, update cache
```

**Mitigation**:
- Configurable timeouts
- Parallel async queries
- Partial result delivery with "still fetching" status

---

#### Scenario 4: Contradictory Data
```
Qdrant says: "AuthService handles login"
Neo4j says: "LoginHandler handles login, AuthService is deprecated"

Both can't be true. Which is correct?

Resolution Strategy:
1. Check timestamps (Neo4j newer = more likely correct)
2. Check veracity flags (STALE_DOC warnings)
3. Return BOTH with confidence scores:
   {
     "AuthService": {"source": "qdrant", "confidence": 0.6, "warning": "may be stale"},
     "LoginHandler": {"source": "neo4j", "confidence": 0.95, "verified": true}
   }
4. LLM decides based on confidence
```

**Mitigation**:
- Timestamp-based conflict resolution
- Veracity checking flags stale data
- Confidence scoring
- Return contradictory data with warnings

---

#### Scenario 5: Ingestion Failure (Partial Update)
```
File changed: src/auth.ts

Ingestion starts:
├─ Qdrant update: ✅ Success
└─ Neo4j update: ❌ Failure (out of memory)

PROBLEM: Qdrant says "auth.ts has new content" but Neo4j shows old structure
RESULT: Contradictory data, LLM gets confused

Solution: ATOMIC TRANSACTIONS
├─ Qdrant update: STAGED
├─ Neo4j update: STAGED
├─ Both ready? → COMMIT BOTH
└─ One failed? → ROLLBACK BOTH
```

**Mitigation**:
- Atomic cross-system transactions
- Transaction log for recovery
- Rollback on partial failure
- Retry logic with backoff

---

#### Scenario 6: Queue Overflow
```
High load: 1000 queries/second
Queue capacity: 100 queries
Result: Queue overflow, queries dropped

Mitigation:
- Priority queues (urgent queries first)
- Backpressure (reject new requests with "429 Too Many Requests")
- Auto-scale Ollama containers
- Load shedding (drop low-priority queries)
```

---

#### Scenario 7: Ollama Model Crash
```
Query needs embedding
Ollama container: CRASHED

Mitigation:
1. Fallback to secondary Ollama (if available)
2. Use cached embeddings for similar queries
3. Return error with "try again in 30s"
4. Auto-restart Ollama container
```

---

#### Scenario 8: Data Corruption
```
Neo4j returns: corrupted relationship data
Qdrant returns: malformed payload

Detection:
1. Schema validation on all responses
2. Checksum verification
3. "Sanity check" queries (expected results)

Recovery:
1. Restore from backup
2. Re-ingest from source
3. Mark corrupted data with warning
```

---

#### Scenario 9: Network Partition
```
Gateway can reach Qdrant but NOT Neo4j
Network partition between services

Mitigation:
1. Local Redis cache for recent queries
2. Circuit breaker (stop trying after 3 failures)
3. Graceful degradation
4. Background retry with exponential backoff
```

---

#### Scenario 10: LLM Gets Stuck in Loop
```
LLM keeps asking same question
Query queue fills up
System becomes unresponsive

Mitigation:
1. Query deduplication (same query = cached result)
2. Rate limiting per agent
3. Query timeout (max 30s per query)
4. Circuit breaker (stop serving misbehaving agents)
```

---

## Testing Strategy (Using Current Codebase)

### Phase 0: Unified Gateway Testing

**Test Case 1: Current Project Ingestion**
```
Target: /home/devuser/Projects/engg-support-system/

1. Clear Neo4j test data
2. Run unified ingestion:
   - knowledge-base/ → Qdrant (embeddings)
   - veracity-engine/ → Neo4j (structure)
   - docs/ → Both (docs + structure)
   
3. Verify:
   - Qdrant has embeddings for all files
   - Neo4j has code structure for all files
   - Cross-references exist (Qdrant payload has neo4j_id)
```

**Test Case 2: Query Both DBs**
```
Query: "How does the MCP gateway work?"

Expected Results:
├─ Qdrant: Semantic matches (docs, comments mentioning "MCP gateway")
├─ Neo4j: Structural matches (files that define/use MCP gateway)
└─ Combined: Complete answer with citations

Verification:
- Both DBs queried
- Results merged
- Citations from both sources
- No partial answers
```

**Test Case 3: Failure Simulation**
```
1. Stop Qdrant container
2. Run query
3. Verify: Graceful degradation + warning

4. Stop Neo4j container
5. Run query
6. Verify: Graceful degradation + warning

7. Stop both containers
8. Run query
9. Verify: Error message OR cached result
```

**Test Case 4: Contradictory Data**
```
1. Manually create conflict:
   - Qdrant: "AuthService handles login"
   - Neo4j: "LoginHandler handles login"

2. Query: "What handles login?"

3. Verify response:
   - Both answers returned
   - Confidence scores included
   - Warnings about conflict
   - LLM can decide
```

---

## Summary: "Both Together" Failure Handling

| Failure Type | Impact | Mitigation | LLM Experience |
|--------------|--------|------------|----------------|
| One DB down | Partial answers | Graceful degradation + warning | Gets available data + ⚠️ |
| Both DBs down | No answers | Cache + auto-retry | Cached data OR error |
| Slow DB | Delayed responses | Timeout + partial delivery | Fast partial + "fetching rest..." |
| Contradictory data | Confusion | Confidence scores + timestamps | Both results + LLM decides |
| Partial ingestion | Inconsistent state | Atomic transactions | Query blocked until consistent |
| Queue overflow | Dropped queries | Priority queues + backpressure | "429 Too Many" |
| Model crash | No embeddings | Fallback + restart | Error OR cache |
| Data corruption | Wrong answers | Validation + re-ingest | Warning + fallback |
| Network partition | Partial connectivity | Circuit breaker + retry | Partial + warning |
| LLM loop | System overload | Deduplication + rate limit | Cached results |

---

## Critical Success Criteria

**For this system to work, EVERY query must:**

1. ✅ Query BOTH databases (no exceptions)
2. ✅ Merge results from both sources
3. ✅ Handle failures gracefully
4. ✅ Return complete OR explain what's missing
5. ✅ Provide citations for all claims
6. ✅ Work without LLM understanding the architecture

**If ANY of these fail, return `status: "unavailable"` with fallback message: "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH"**

---

## Detailed Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)

#### 1.1 Shared Docker Compose Stack
**File**: `engg-support-system/infra/docker-compose.yml`

**Components**:
- **qdrant**: Vector database (port 6333/6334)
- **neo4j**: Graph database (port 7474/7687)
- **neodash**: Graph visualization (port 5005)
- **ollama**: Shared SLM service (port 11434)
  - Pre-loaded models: nomic-embed-text, llama3.2, mistral-nemo, codeqwen
- **redis**: Shared caching layer (port 6379)
- **prometheus**: Metrics collection (port 9090)
- **grafana**: Monitoring dashboard (port 3000)

**Todo**:
- [ ] Create unified docker-compose.yml
- [ ] Add environment variable template (.env.example)
- [ ] Configure health checks for all services
- [ ] Set up volume persistence for data
- [ ] Create startup order dependencies

#### 1.2 Ollama Model Management
**File**: `engg-support-system/infra/ollama_models.txt`

**Pre-loaded Models**:
```
nomic-embed-text:latest   # Embeddings (768-dim)
llama3.2:3b               # Fast reasoning
llama3.2:latest           # General purpose
mistral-nemo:latest       # Code understanding
codeqwen:latest           # Code-specific
deepseek-coder:latest     # Advanced code analysis
```

**Todo**:
- [ ] Create model pull script
- [ ] Add model health check endpoint
- [ ] Document model capabilities per use case
- [ ] Set up model fallback chain

#### 1.3 Request Queuing System
**Files**: `engg-support-system/infra/queues/`

**Purpose**: Manage concurrent requests, optimize resource utilization, and prevent model overload.

**Components**:
- **Redis**: Queue backend (port 6379, shared with caching)
- **BullMQ**: TypeScript queue for knowledge-base/gateway
- **Celery or RQ**: Python queue for veracity-engine
- **Priority Queues**: High/Medium/Low priority lanes

**Queue Architecture**:
```
Agent Request → Gateway → [Priority Queue] →
├─→ [Request Queue] → Qdrant Search
├─→ [Request Queue] → Neo4j Traversal  
├─→ [Model Queue] → Ollama Embeddings (batched)
└─→ [Processing Queue] → Veracity Check (async)
```

**Todo**:
- [ ] Create Redis queue configuration
- [ ] Implement BullMQ queues for TypeScript
- [ ] Implement Celery/RQ queues for Python
- [ ] Add priority queue logic (high/medium/low)
- [ ] Implement batch processing for embeddings
- [ ] Add queue monitoring and metrics
- [ ] Document queue configuration

---

### Phase 2: Unified MCP Gateway (Week 2)

#### 2.1 Gateway Service
**File**: `engg-support-system/gateway/src/server.ts`

**Features**:
- Route requests to appropriate backend (Qdrant vs Neo4j)
- Implement hybrid search (merge + rank)
- Unified authentication
- Rate limiting per project
- Request/response logging

**API Endpoints**:
```
POST /query/vector         # Qdrant semantic search
POST /query/graph          # Neo4j graph traversal
POST /query/hybrid         # Combined search
POST /query/veracity       # Ground-truth validation
POST /ingest/codebase      # Full codebase ingestion
GET  /health               # System health check
GET  /stats                # Usage statistics
```

**Todo**:
- [ ] Design unified MCP protocol
- [ ] Implement request router
- [ ] Add hybrid search algorithm
- [ ] Create unified authentication
- [ ] Add request/response logging
- [ ] Implement rate limiting
- [ ] Add circuit breakers for backends

#### 2.2 Client SDK
**File**: `engg-support-system/gateway/sdk/client.ts`

**Features**:
- Type-safe client for TypeScript/Python
- Auto-retry with exponential backoff
- Streaming response support
- Connection pooling

**Todo**:
- [ ] Create TypeScript SDK
- [ ] Create Python SDK
- [ ] Add streaming support
- [ ] Document usage examples
- [ ] Add integration tests

---

### Phase 3: Enhanced knowledge-base (Week 3)

#### 3.1 Relationship Extraction
**File**: `engg-support-system/knowledge-base/src/core/RelationshipExtractor.ts`

**Features**:
- Extract code relationships (imports, calls, inherits)
- Link documentation to code
- Cross-reference commits and issues

**Todo**:
- [ ] Implement AST-based relationship extraction
- [ ] Add support for TypeScript, Python, Go, Rust
- [ ] Create relationship confidence scoring
- [ ] Add relationship validation
- [ ] Document relationship types

#### 3.2 Complete Caching Layer
**File**: `engg-support-system/knowledge-base/src/core/CacheManager.ts`

**Features**:
- Redis-backed distributed cache
- Temperature-based cache promotion
- TTL management
- Cache invalidation on updates

**Todo**:
- [ ] Implement Redis cache client
- [ ] Add cache warming strategies
- [ ] Implement cache invalidation
- [ ] Add cache metrics
- [ ] Document cache policies

---

### Phase 4: Enhanced veracity-engine (Week 4)

#### 4.1 Multi-Language Support via tree-sitter
**File**: `engg-support-system/veracity-engine/core/parsers/tree_sitter_parser.py`

**Architecture**: Use `tree-sitter` universal parser instead of language-specific parsers.

**Why tree-sitter?**:
- Single parser for 20+ languages (TypeScript, Go, Rust, Python, C, C++, Java, etc.)
- Incremental parsing (fast for large files)
- Error-tolerant (handles incomplete code)
- Language-agnostic API
- Production-ready and battle-tested

**Supported Languages** (out of the box):
| Language | tree-sitter Grammar | Status |
|----------|---------------------|--------|
| TypeScript/JavaScript | `tree-sitter-typescript` | ✅ Ready |
| Python | `tree-sitter-python` | ✅ Ready |
| Go | `tree-sitter-go` | ✅ Ready |
| Rust | `tree-sitter-rust` | ✅ Ready |
| C/C++ | `tree-sitter-c` | ✅ Ready |
| Java | `tree-sitter-java` | ✅ Ready |
| +15 more languages | Various | ✅ Ready |

**Parser Interface**:
```python
class TreeSitterParser:
    """Universal AST parser using tree-sitter"""
    
    def parse_file(self, file_path: str, language: str) -> ASTNode:
        """Parse any supported language file"""
        
    def extract_functions(self, ast: ASTNode) -> List[Function]:
        """Extract function definitions"""
        
    def extract_classes(self, ast: ASTNode) -> List[Class]:
        """Extract class definitions"""
        
    def extract_imports(self, ast: ASTNode) -> List[Import]:
        """Extract import/require statements"""
        
    def extract_relationships(self, ast: ASTNode) -> List[Relationship]:
        """Extract CALLS, DEFINES, DEPENDS_ON relationships"""
```

**Todo**:
- [ ] Install tree-sitter Python bindings
- [ ] Add required language grammars
- [ ] Implement TreeSitterParser class
- [ ] Add language detection (file extension → grammar)
- [ ] Implement AST node extraction functions
- [ ] Implement relationship extraction
- [ ] Add parser tests for each language
- [ ] Document supported languages and capabilities
- [ ] Benchmark vs. current Python ast parser


#### 4.2 Enhanced Veracity Checking
**File**: `engg-support-system/veracity-engine/core/veracity.py`

**Features**:
- Cross-reference Qdrant for staleness detection
- Detect orphaned nodes across both stores
- Find contradictions between vector and graph
- Add confidence scoring

**Todo**:
- [ ] Implement cross-store staleness check
- [ ] Add orphan detection across stores
- [ ] Create contradiction detection
- [ ] Add confidence scoring
- [ ] Document veracity rules

---

### Phase 5: Full Codebase Ingestion (Week 5)

#### 5.1 Universal Ingestion Pipeline
**File**: `engg-support-system/ingestion/src/ingester.ts`

**Features**:
- Detect all supported file types
- Route to appropriate parser
- Parallel ingestion
- Progress tracking
- Incremental updates

**Supported File Types**:
- Code: .ts, .tsx, .js, .jsx, .py, .go, .rs
- Docs: .md, .txt, .rst
- Config: .json, .yaml, .yml, .toml
- Tests: .test.ts, .spec.ts, _test.go

**Todo**:
- [ ] Create file type detector
- [ ] Implement parallel ingestion
- [ ] Add progress tracking
- [ ] Implement incremental updates
- [ ] Add ingestion tests
- [ ] Document ingestion process

#### 5.2 Ingestion CLI
**File**: `engg-support-system/ingestion/src/cli.ts`

**Commands**:
```bash
engg-ingest init <project> <path>      # Initialize project
engg-ingest scan                         # Scan for changes
engg-ingest full                          # Full ingestion
engg-ingest incremental                   # Incremental update
engg-ingest status                        # Show ingestion status
```

**Todo**:
- [ ] Create CLI interface
- [ ] Add project management
- [ ] Implement watch mode
- [ ] Add status reporting
- [ ] Document CLI usage

---

### Phase 6: Testing & Validation (Week 6)

#### 6.1 Integration Tests
**File**: `engg-support-system/tests/integration/`

**Test Scenarios**:
- Full ingestion cycle
- Hybrid query accuracy
- Veracity validation
- Fallback behavior
- Concurrent access

**Todo**:
- [ ] Create ingestion test suite
- [ ] Create query test suite
- [ ] Create veracity test suite
- [ ] Create performance tests
- [ ] Document test coverage

#### 6.2 Performance Benchmarking
**File**: `engg-support-system/tests/benchmarks/`

**Metrics**:
- Ingestion throughput (files/sec)
- Query latency (p50, p95, p99)
- Storage efficiency
- Memory usage
- Cache hit rates

**Todo**:
- [ ] Create ingestion benchmarks
- [ ] Create query benchmarks
- [ ] Create memory profiling
- [ ] Document performance targets
- [ ] Set up CI benchmarking

---

### Phase 7: Production Deployment (Week 7)

#### 7.1 VPS Deployment
**File**: `engg-support-system/deploy/`

**Components**:
- Deployment scripts
- Configuration management
- Health monitoring
- Backup procedures
- Disaster recovery

**Todo**:
- [ ] Create deployment scripts
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Document deployment process
- [ ] Create runbook for incidents

#### 7.2 Documentation
**File**: `engg-support-system/docs/`

**Documents**:
- Architecture overview
- API reference
- User guide
- Operator guide
- Troubleshooting

**Todo**:
- [ ] Write architecture docs
- [ ] Write API reference
- [ ] Write user guides
- [ ] Write operator guide
- [ ] Create troubleshooting guide

---

## Shared Resources Configuration

### Environment Variables
**File**: `engg-support-system/.env.example`

```bash
# Infrastructure
QDRANT_URL=http://localhost:6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
REDIS_URL=redis://localhost:6379
OLLAMA_URL=http://localhost:11434

# Gateway
GATEWAY_PORT=4000
GATEWAY_API_KEY=changeme
GATEWAY_LOG_LEVEL=info

# Knowledge Base
KB_EMBED_MODEL=nomic-embed-text
KB_SUMMARIZE_MODEL=llama3.2
KB_FALLBACK_ENABLED=true

# Veracity Engine
VE_EMBED_MODEL=nomic-embed-text
VE_VERACITY_THRESHOLD=0.7
VE_STALE_DAYS=90

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
METRICS_ENABLED=true
```

### Model Assignment Matrix

| Use Case | Primary Model | Fallback | Rationale |
|----------|--------------|----------|-----------|
| Embeddings | nomic-embed-text | - | 768-dim, fast |
| Summarization | llama3.2:3b | mistral-nemo | Low latency first |
| Code Analysis | codeqwen | deepseek-coder | Code-specialized |
| Reasoning | llama3.2 | mistral-nemo | General purpose |
| Veracity Check | mistral-nemo | llama3.2 | Higher accuracy |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Ollama model conflicts | High | Medium | Separate model containers |
| Neo4j memory limits | High | Low | Configure heap size |
| Qdrant downtime | High | Low | Health checks + alerts |
| Integration bugs | Medium | High | Comprehensive tests |
| Performance degradation | Medium | Medium | Benchmarking + tuning |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| VPS resource exhaustion | High | Medium | Resource limits + monitoring |
| Data loss | Critical | Low | Regular backups |
| Security breach | High | Low | API keys + rate limits |
| Dependency conflicts | Medium | Medium | Pin versions |

---

## Success Criteria

### Functional Requirements
- [ ] Hybrid search returns results from both Qdrant and Neo4j
- [ ] Veracity checking validates across both stores
- [ ] Codebase ingestion supports 5+ languages
- [ ] MCP gateway serves both systems unified
- [ ] All tests pass with 80%+ coverage

### Performance Requirements
- [ ] Query latency < 500ms (p95)
- [ ] Ingestion throughput > 100 files/sec
- [ ] Cache hit rate > 60%
- [ ] Uptime > 99.5%

### Operational Requirements
- [ ] Health checks for all services
- [ ] Automated backups
- [ ] Monitoring dashboards
- [ ] Runbook for incidents

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Infrastructure | Docker Compose, Ollama models |
| 2 | Gateway | Unified MCP server, SDK |
| 3 | knowledge-base | Relationship extraction, caching |
| 4 | veracity-engine | Multi-language, enhanced veracity |
| 5 | Ingestion | Universal pipeline, CLI |
| 6 | Testing | Integration tests, benchmarks |
| 7 | Deployment | VPS setup, documentation |

---

## Next Steps

1. **Review this plan** and approve architecture
2. **Set up infrastructure** (Phase 1)
3. **Create unified CLAUDE.md** with context from both systems
4. **Begin Phase 1 implementation**

---

**Document Status**: Draft | **Last Updated**: 2026-01-07
