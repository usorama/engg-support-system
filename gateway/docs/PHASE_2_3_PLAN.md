# Phase 2-3 Integration Plan

> **Status**: Detailed Planning | **Date**: 2026-01-08 | **Dependencies**: Phase 1 Complete
> **Related**: [Phase 1 Verification](PHASE_1_VERIFICATION.md) | [Implementation Plan](../plans/CONVERSATIONAL_AGENT_IMPLEMENTATION.md)

---

## Executive Summary

Phase 2-3 focuses on **integrating the conversational agent** with existing system features (ingestion, veracity checks, code search) to provide intelligent clarification and refinement capabilities.

**Goal**: Enable conversational mode to enhance specific system workflows

**Duration**: 1-2 weeks

**Dependencies**:
- ✅ Phase 1 (Redis persistence) - Complete
- ✅ EnggContextAgent - Complete
- ✅ QueryClassifier & ClarificationGenerator - Complete
- ✅ ConversationManager - Complete

---

## Integration Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EnggContextAgent (Gateway)                      │
├─────────────────────────────────────────────────────────────────────┤
│  query()                                                             │
│  ├─ classifyQuery() → intent, clarity                               │
│  ├─ if conversational:                                              │
│  │   ├─ startConversation()                                        │
│  │   └─ generateClarifications()                                   │
│  └─ generateOneShotResponse()                                      │
└────────────┬────────────────────────────────────────────────────────┘
             │
    ┌────────┼────────┬───────────────┬────────────────┐
    │        │        │               │                │
    ▼        ▼        ▼               ▼                ▼
┌────────┐ ┌─────┐ ┌──────┐  ┌─────────────┐  ┌─────────────┐
│Qdrant  │ │Neo4j│ │Ollama│  │Ingestion    │  │Veracity     │
│KB      │ │KG   │ │LLM   │  │Integration  │  │Integration  │
└────────┘ └─────┘ └──────┘  └─────────────┘  └─────────────┘
```

### Integration Points

| System | Integration Type | Conversation Use Case |
|--------|------------------|----------------------|
| **Ingestion** (build_graph.py) | Wrapper + CLI | Clarify project setup parameters |
| **Veracity** (ask_codebase.py) | Wrapper + CLI | Scope veracity checks by focus area |
| **Code Search** (hybrid search) | Direct integration | Iterative search refinement |

---

## Phase 2: Ingestion Integration

### Goal

Enable conversational project setup when ingesting new codebases.

### Current State

```bash
# Current ingestion requires all parameters upfront
python3 core/build_graph.py \
  --project-name myproject \
  --root-dir /path/to/code \
  --include-dirs src,lib \
  --exclude-dirs tests,docs \
  --file-types py,md \
  --force
```

**Problem**: Users must know all options beforehand. No guidance on optimal choices.

### Proposed Solution

**Conversation-Enhanced Ingestion**:

```bash
# Start conversational ingestion
python3 core/build_graph.py \
  --project-name myproject \
  --root-dir /path/to/code \
  --conversational

# Agent asks clarifying questions:
# 1. "Which directories should I include?"
# 2. "Should I include test files?"
# 3. "What file types should I prioritize?"
# 4. "Should I force rebuild or use cache?"
```

### Implementation Tasks

#### Task 2.1: Create ConversationalBuildGraph Wrapper

**File**: `gateway/src/agents/ConversationalIngestion.ts`

```typescript
export class ConversationalIngestion {
  private agent: EnggContextAgent;
  private manager: ConversationManager;

  async startIngestion(
    projectName: string,
    rootDir: string,
    mode: "one-shot" | "conversational" = "auto"
  ): Promise<IngestionResponse> {
    // Start conversation
    const state = await this.manager.startConversation(
      `Ingest codebase at ${rootDir}`
    );

    // Generate clarifications for ingestion
    const clarifications = [
      {
        key: "includeDirs",
        question: "Which directories should I include?",
        options: this.detectDirectories(rootDir),
        multiple: true
      },
      {
        key: "includeTests",
        question: "Should I include test files?",
        options: ["yes", "no"],
        multiple: false
      },
      {
        key: "fileTypes",
        question: "What file types should I prioritize?",
        options: this.detectFileTypes(rootDir),
        multiple: true
      }
    ];

    return {
      type: "conversation",
      conversationId: state.conversationId,
      round: state.round,
      clarifications: { questions: clarifications }
    };
  }

  async continueIngestion(
    conversationId: string,
    answers: Record<string, unknown>
  ): Promise<IngestionResult> {
    // Collect answers and build command
    const state = await this.manager.getConversation(conversationId);
    const cmd = this.buildIngestCommand(state, answers);

    // Execute ingestion
    const result = await this.executeIngestion(cmd);

    // End conversation
    await this.manager.endConversation(conversationId);

    return result;
  }

  private detectDirectories(rootDir: string): string[] {
    // Scan directory and return detected subdirectories
    // Exclude common exclusions: node_modules, .git, etc.
  }

  private detectFileTypes(rootDir: string): string[] {
    // Scan directory and return detected file types
    // Prioritize code files: py, ts, js, go, rs, etc.
  }

  private buildIngestCommand(
    state: ConversationState,
    answers: Record<string, unknown>
  ): string {
    // Build build_graph.py command with collected answers
    const args = [
      "--project-name", state.collectedContext.projectName,
      "--root-dir", state.collectedContext.rootDir
    ];

    if (answers.includeDirs) {
      args.push("--include-dirs", answers.includeDirs.join(","));
    }

    // ... other arguments

    return `python3 core/build_graph.py ${args.join(" ")}`;
  }

  private async executeIngestion(cmd: string): Promise<IngestionResult> {
    // Execute command and return result
  }
}
```

#### Task 2.2: Create Ingestion Tests

**File**: `gateway/src/test/e2e/ingestion-conversation.e2e.test.ts`

```typescript
describe("Conversational Ingestion", () => {
  it("should start ingestion conversation", async () => {
    const ingestion = new ConversationalIngestion();
    const response = await ingestion.startIngestion(
      "test-project",
      "/tmp/test-code",
      "conversational"
    );

    expect(response.type).toBe("conversation");
    expect(response.clarifications.questions).toHaveLength(3);
    expect(response.clarifications.questions[0].key).toBe("includeDirs");
  });

  it("should detect directories from codebase", async () => {
    const ingestion = new ConversationalIngestion();
    const dirs = await ingestion.detectDirectories("/tmp/test-code");

    expect(dirs).toContain("src");
    expect(dirs).toContain("lib");
    expect(dirs).not.toContain("node_modules");
  });

  it("should complete ingestion with collected answers", async () => {
    const ingestion = new ConversationalIngestion();
    const start = await ingestion.startIngestion("test", "/tmp/code", "conversational");

    const result = await ingestion.continueIngestion(
      start.conversationId,
      {
        includeDirs: ["src", "lib"],
        includeTests: "no",
        fileTypes: ["py", "ts"]
      }
    );

    expect(result.status).toBe("success");
    expect(result.nodesIndexed).toBeGreaterThan(0);
  });
});
```

#### Task 2.3: Create CLI Interface

**File**: `gateway/src/cli/ingest.ts`

```typescript
#!/usr/bin/env node
import { ConversationalIngestion } from "../agents/ConversationalIngestion.js";

async function main() {
  const args = process.argv.slice(2);
  const projectName = args[0];
  const rootDir = args[1];
  const mode = args[2] || "auto";

  const ingestion = new ConversationalIngestion();

  if (mode === "conversational" || mode === "auto") {
    const response = await ingestion.startIngestion(projectName, rootDir);

    if (response.type === "conversation") {
      console.log("Ingestion Setup");
      console.log("=".repeat(50));
      console.log(`Conversation ID: ${response.conversationId}\n`);

      response.clarifications.questions.forEach((q, i) => {
        console.log(`${i + 1}. ${q.question}`);
        if (q.options) {
          q.options.forEach((opt) => console.log(`   - ${opt}`));
        }
        console.log();
      });

      console.log("To continue, provide answers via CLI or API");
    }
  } else {
    // One-shot mode with defaults
    const result = await ingestion.continueIngestion(null, {
      projectName,
      rootDir,
      includeDirs: ["src"],
      includeTests: false,
      fileTypes: ["py", "ts", "js"]
    });

    console.log(`Ingestion complete: ${result.nodesIndexed} nodes indexed`);
  }
}

main();
```

### Success Criteria

- [ ] ConversationalIngestion class created
- [ ] Directory detection working
- [ ] File type detection working
- [ ] CLI interface functional
- [ ] E2E tests passing
- [ ] Integration with build_graph.py working

---

## Phase 3: Veracity Integration

### Goal

Enable conversational scoping of veracity checks.

### Current State

```bash
# Current veracity check requires focus area upfront
python3 core/ask_codebase.py \
  --project-name myproject \
  "Check veracity of authentication system"
```

**Problem**: Queries can be ambiguous. Which aspects of authentication? What type of veracity checks?

### Proposed Solution

**Conversation-Enhanced Veracity**:

```bash
# Start conversational veracity check
python3 core/ask_codebase.py \
  --project-name myproject \
  --conversational \
  "Check veracity of authentication system"

# Agent asks clarifying questions:
# 1. "What should I focus on?"
#    Options: [Stale documents, Orphaned nodes, Contradictions, All]
# 2. "Which components should I check?"
#    Options: [AuthService, UserController, LoginFlow, All]
# 3. "How far back should I check for staleness?"
#    Options: [30 days, 90 days, 180 days, All time]
```

### Implementation Tasks

#### Task 3.1: Create ConversationalVeracity Wrapper

**File**: `gateway/src/agents/ConversationalVeracity.ts`

```typescript
export class ConversationalVeracity {
  private agent: EnggContextAgent;
  private manager: ConversationManager;

  async startVeracityCheck(
    projectName: string,
    query: string,
    mode: "one-shot" | "conversational" = "auto"
  ): Promise<VeracityResponse> {
    // Classify query
    const classification = classifyQuery(query);

    // If clear, run one-shot
    if (classification.clarity === "clear") {
      return await this.runOneShotVeracity(projectName, query);
    }

    // Start conversation for ambiguous queries
    const state = await this.manager.startConversation(query);

    // Generate veracity-specific clarifications
    const clarifications = [
      {
        key: "focusArea",
        question: "What should I focus on?",
        options: ["Stale documents", "Orphaned nodes", "Contradictions", "All"],
        multiple: true
      },
      {
        key: "components",
        question: "Which components should I check?",
        options: await this.detectComponents(projectName),
        multiple: true
      },
      {
        key: "stalenessThreshold",
        question: "How far back should I check for staleness?",
        options: ["30 days", "90 days", "180 days", "All time"],
        multiple: false
      }
    ];

    return {
      type: "conversation",
      conversationId: state.conversationId,
      round: state.round,
      clarifications: { questions: clarifications }
    };
  }

  async continueVeracityCheck(
    conversationId: string,
    answers: Record<string, unknown>
  ): Promise<VeracityResult> {
    // Collect answers and build query
    const state = await this.manager.getConversation(conversationId);
    const enhancedQuery = this.buildVeracityQuery(state, answers);

    // Execute veracity check
    const result = await this.executeVeracityCheck(state, enhancedQuery, answers);

    // End conversation
    await this.manager.endConversation(conversationId);

    return result;
  }

  private async detectComponents(projectName: string): Promise<string[]> {
    // Query Neo4j for available components in project
    // Return list of Class, Function, Component nodes
  }

  private buildVeracityQuery(
    state: ConversationState,
    answers: Record<string, unknown>
  ): string {
    // Build enhanced query with collected context
    let query = state.originalQuery;

    if (answers.focusArea) {
      query += ` focusing on ${answers.focusArea}`;
    }

    if (answers.components) {
      query += ` in ${Array(answers.components).join(", ")}`;
    }

    return query;
  }

  private async executeVeracityCheck(
    state: ConversationState,
    query: string,
    options: Record<string, unknown>
  ): Promise<VeracityResult> {
    // Call ask_codebase.py with enhanced query and options
    // Parse and return results
  }
}
```

#### Task 3.2: Create Veracity Tests

**File**: `gateway/src/test/e2e/veracity-conversation.e2e.test.ts`

```typescript
describe("Conversational Veracity", () => {
  it("should start veracity conversation for ambiguous query", async () => {
    const veracity = new ConversationalVeracity();
    const response = await veracity.startVeracityCheck(
      "myproject",
      "Check veracity of auth",
      "conversational"
    );

    expect(response.type).toBe("conversation");
    expect(response.clarifications.questions).toHaveLength(3);
  });

  it("should detect components from project", async () => {
    const veracity = new ConversationalVeracity();
    const components = await veracity.detectComponents("myproject");

    expect(components).toContain("AuthService");
    expect(components).toContain("UserController");
  });

  it("should complete veracity check with collected answers", async () => {
    const veracity = new ConversationalVeracity();
    const start = await veracity.startVeracityCheck("myproject", "Check auth", "conversational");

    const result = await veracity.continueVeracityCheck(
      start.conversationId,
      {
        focusArea: ["Stale documents", "Contradictions"],
        components: ["AuthService"],
        stalenessThreshold: "90 days"
      }
    );

    expect(result.confidenceScore).toBeDefined();
    expect(result.faults).toBeInstanceOf(Array);
  });
});
```

#### Task 3.3: Enhance ask_codebase.py for Conversation Options

**File**: `veracity-engine/core/ask_codebase.py`

```python
# Add support for veracity options from conversation
def query_graph_with_options(question, project_name, veracity_options=None, config=None):
    """
    Query the knowledge graph with veracity options.

    Args:
        question: The query string
        project_name: Project name for multitenancy
        veracity_options: Dict with focus_area, components, staleness_threshold
        config: Optional VeracityConfig instance
    """
    if veracity_options:
        # Apply veracity options
        focus_area = veracity_options.get('focus_area', [])

        # Adjust staleness threshold
        if 'staleness_threshold' in veracity_options:
            threshold_str = veracity_options['staleness_threshold']
            # Parse "90 days" -> 90 days in seconds
            # Update GroundTruthContextSystem

        # Filter components
        if 'components' in veracity_options:
            components = veracity_options['components']
            # Add component filter to Cypher query

    # Run query with options applied
    return query_graph(question, project_name, config)
```

### Success Criteria

- [ ] ConversationalVeracity class created
- [ ] Component detection working
- [ ] Veracity options parsing working
- [ ] Integration with ask_codebase.py working
- [ ] E2E tests passing

---

## Phase 3: Code Search Refinement

### Goal

Enable iterative search refinement through conversation.

### Current State

```bash
# Single search query, results returned
curl -X POST http://localhost:3000/api/query \
  -d '{"query": "authentication flow"}'
```

**Problem**: If results are too broad or not specific enough, user must refine query manually.

### Proposed Solution

**Conversation-Enhanced Search**:

```bash
# Initial search
curl -X POST http://localhost:3000/api/query \
  -d '{"query": "authentication", "mode": "conversational"}'

# Response: Too many results (50+ matches)
{
  "type": "conversation",
  "clarifications": {
    "questions": [
      "Results are broad. Narrow down to:",
      "options": ["JWT validation", "Login flow", "Session management", "Password reset"]
    ]
  }
}

# User provides refinement
curl -X POST http://localhost:3000/api/query/continue \
  -d '{"conversationId": "conv-123", "refinement": "JWT validation"}'

# Response: Refined results
{
  "type": "response",
  "results": {
    "matches": [
      {"file": "src/auth/JWTValidator.ts", "score": 0.95},
      {"file": "src/auth/token.ts", "score": 0.89}
    ]
  }
}
```

### Implementation Tasks

#### Task 3.4: Enhance EnggContextAgent for Search Refinement

**File**: `gateway/src/agents/EnggContextAgent.ts`

```typescript
async query(request: QueryRequest): Promise<QueryResponse | ConversationResponse> {
  const classification = classifyQuery(request.query);

  // Check if conversational mode requested
  if (request.mode === "conversational" || (request.mode === "auto" && classification.clarity !== "clear")) {
    const state = await this.conversationManager.startConversation(request.query);

    // Run initial search
    const initialResults = await this.hybridSearch(request.query, classification);

    // Check if results need refinement
    if (initialResults.meta.resultSize.semanticMatches > 20) {
      // Generate refinement clarifications
      const clarifications = this.generateRefinementClarifications(initialResults);

      return {
        type: "conversation",
        conversationId: state.conversationId,
        round: state.round,
        clarifications: {
          questions: clarifications,
          message: "Results are broad. Would you like to narrow down?"
        },
        meta: {
          originalQuery: request.query,
          resultCount: initialResults.meta.resultSize.semanticMatches,
          topResults: initialResults.results.semantic.matches.slice(0, 5).map((m) => ({
            file: m.payload.file_path,
            score: m.score
          }))
        }
      };
    }
  }

  // One-shot mode
  return await this.generateOneShotResponse(request, classification);
}

private generateRefinementClarifications(results: SearchResults): ClarificationQuestion[] {
  // Analyze results to generate refinement options
  const topFiles = results.results.semantic.matches.slice(0, 20);

  // Extract common patterns
  const directories = new Set<string>();
  const components = new Set<string>();

  topFiles.forEach((match) => {
    const path = match.payload.file_path;
    const parts = path.split("/");
    if (parts.length > 1) {
      directories.add(parts[parts.length - 2]);
    }
  });

  // Generate questions
  return [
    {
      id: "directory",
      question: "Narrow down to specific directory?",
      options: Array.from(directories).slice(0, 5),
      multipleChoice: false,
      required: false
    },
    {
      id: "component",
      question: "Focus on specific component?",
      options: Array.from(components),
      multipleChoice: false,
      required: false
    },
    {
      id: "keyword",
      question: "Add specific keyword?",
      options: [],
      multipleChoice: false,
      required: false
    }
  ];
}
```

### Success Criteria

- [ ] Refinement clarification generation working
- [ ] Result narrowing logic working
- [ ] Continue query supports refinement
- [ ] E2E tests passing

---

## Implementation Order

### Week 1: Core Integration

| Day | Tasks |
|-----|-------|
| 1 | Task 2.1: Create ConversationalIngestion class |
| 2 | Task 2.2: Create ingestion tests |
| 3 | Task 2.3: Create CLI interface |
| 4 | Task 3.1: Create ConversationalVeracity class |
| 5 | Task 3.2: Create veracity tests |

### Week 2: Enhancement & Testing

| Day | Tasks |
|-----|-------|
| 1 | Task 3.3: Enhance ask_codebase.py for options |
| 2 | Task 3.4: Enhance EnggContextAgent for search refinement |
| 3 | Integration testing (E2E) |
| 4 | Documentation updates |
| 5 | Quality gates, commit, push |

---

## Testing Strategy

### Unit Tests

- `ConversationalIngestion.test.ts` - Test directory/file detection, command building
- `ConversationalVeracity.test.ts` - Test component detection, query building
- `SearchRefinement.test.ts` - Test clarification generation

### Integration Tests

- `ingestion-conversation.e2e.test.ts` - Full ingestion flow
- `veracity-conversation.e2e.test.ts` - Full veracity check flow
- `search-refinement.e2e.test.ts` - Full search refinement flow

### Test Scenarios

1. **Ingestion**:
   - Start conversation → Detect dirs → Collect answers → Execute ingestion
   - One-shot mode with defaults
   - Invalid directory handling
   - Partial answers handling

2. **Veracity**:
   - Start conversation → Detect components → Collect answers → Execute check
   - One-shot mode for clear queries
   - Focus area filtering
   - Component-specific checks

3. **Search Refinement**:
   - Broad query → Refinement options → Narrowed results
   - Multiple refinement rounds
   - Keyword addition
   - Directory filtering

---

## API Changes

### New Endpoints

```typescript
// Ingestion endpoints
POST /api/ingest/start
POST /api/ingest/continue

// Veracity endpoints
POST /api/veracity/check
POST /api/veracity/continue

// Search refinement (uses existing /api/query/continue)
```

### Request/Response Types

```typescript
interface IngestStartRequest {
  projectName: string;
  rootDir: string;
  mode?: "one-shot" | "conversational" | "auto";
}

interface IngestStartResponse {
  type: "conversation";
  conversationId: string;
  round: number;
  clarifications: {
    questions: Array<{
      key: string;
      question: string;
      options?: string[];
      multiple: boolean;
    }>;
  };
}

interface IngestContinueRequest {
  conversationId: string;
  answers: Record<string, unknown>;
}

interface IngestContinueResponse {
  type: "response";
  status: "success" | "failed";
  nodesIndexed: number;
  relationshipsCreated: number;
  duration: number;
}

interface VeracityStartRequest {
  projectName: string;
  query: string;
  mode?: "one-shot" | "conversational" | "auto";
}

interface VeracityStartResponse {
  type: "conversation";
  conversationId: string;
  round: number;
  clarifications: {
    questions: Array<{
      key: string;
      question: string;
      options?: string[];
    }>;
  };
}

interface VeracityContinueRequest {
  conversationId: string;
  answers: Record<string, unknown>;
}

interface VeracityContinueResponse {
  type: "response";
  confidenceScore: number;
  faults: string[];
  isStale: boolean;
  evidence: EvidencePacket;
}
```

---

## Documentation Updates

### Files to Update

1. `docs/CONVERSATION_API.md` - Add Phase 2-3 integration examples
2. `CLAUDE.md` - Update with new integration capabilities
3. `README.md` - Add ingestion and veracity CLI usage
4. `docs/plans/CONVERSATIONAL_AGENT_IMPLEMENTATION.md` - Mark Phase 2-3 complete

---

## Success Criteria Summary

### Phase 2: Ingestion Integration

- [ ] ConversationalIngestion class created and tested
- [ ] Directory detection working for common codebases
- [ ] File type detection working
- [ ] CLI interface functional
- [ ] Integration with build_graph.py working end-to-end
- [ ] E2E tests passing (10+ tests)

### Phase 3: Veracity Integration

- [ ] ConversationalVeracity class created and tested
- [ ] Component detection working via Neo4j queries
- [ ] Veracity options parsing working
- [ ] ask_codebase.py enhanced for options
- [ ] Integration working end-to-end
- [ ] E2E tests passing (10+ tests)

### Phase 3: Search Refinement

- [ ] Refinement clarification generation working
- [ ] Result narrowing logic working
- [ ] Multiple refinement rounds supported
- [ ] E2E tests passing (5+ tests)

### Overall Quality

- [ ] All tests passing (100+ tests)
- [ ] TypeScript 0 errors
- [ ] ESLint 0 warnings
- [ ] Documentation complete
- [ ] Git commit and push

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Python integration complexity | Use subprocess with proper error handling |
| Neo4j query performance | Cache component detection results |
| CLI argument parsing | Use commander.js for robust parsing |
| State loss during ingestion | Persist intermediate state to Redis |

---

## Rollback Plan

If Phase 2-3 integration fails:

1. **Keep Phase 1 intact** - Redis persistence remains functional
2. **Feature flags** - Add environment variables to disable integration
3. **Graceful degradation** - Fall back to one-shot mode on errors
4. **Separate modules** - Integration code in separate files, easy to disable

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-08
**Next Review**: Start of Phase 2-3 implementation
