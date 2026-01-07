# Conversational Agent Implementation Plan

> **Status**: Detailed Planning | **Date**: 2026-01-07 | **Version**: 1.0
> **Related Research**: [multi-agent-conversation-patterns-2026.md](./multi-agent-conversation-patterns-2026.md)

---

## Executive Summary

This document provides a detailed implementation plan for adding **optional conversational mode** to the EnggContextAgent. Conversations allow the agent to clarify ambiguous queries, gather missing context, and refine results through back-and-forth dialogue.

**Key Principle**: One-shot mode is DEFAULT; conversational mode is OPTIONAL enhancement.

---

## Integration with Main Plan

### Placement in Implementation Phases

```
Main Plan Phase              | Conversational Agent | Dependencies
-----------------------------|----------------------|-------------
Phase 0a: Unified Gateway  | [N/A - One-shot only]  | Infrastructure
                             |                      |
Phase 0b: Conversational Mode | BASIC IMPLEMENTATION   | Phase 0a complete
                             | - Query classification |
                             | - Clarification logic  |
                             | - 2-round max          |
                             |                      |
Phase 1: Infrastructure     | ENHANCEMENT            | Redis for state
                             | - Redis state storage  |
                             | - 3-round max          |
                             | - Better caching       |
                             |                      |
Phase 2-3: Features         | INTEGRATION            | Use for:
                             |                      | - Ingestion refinement
                             |                      | - Veracity checks
                             |                      |
Phase 4+: Optimization     | ADVANCED FEATURES      | - Learning from patterns
                             | - Auto-refinement       |
                             | - Predictive questions
```

**Critical Path**: Phase 0a (one-shot) must be COMPLETE before Phase 0b (conversational)

---

## Implementation Phases

### Phase 0b: Basic Conversational Mode (Week 0b)

**Duration**: 2-3 days (after Phase 0a complete)

**Goal**: Add basic clarification capability to Gateway

**Scope**:
- Query ambiguity detection
- Clarification question generation
- 2-round conversation limit
- In-memory state storage

**Deliverables**:

1. **Query Classifier Enhancement**
   ```typescript
   // File: gateway/src/agents/QueryClassifier.ts

   interface QueryClassification {
     intent: QueryIntent;
     clarity: "clear" | "ambiguous" | "requires_context";
     confidence: number;  // 0-1
     suggestedMode: "one-shot" | "conversational";
     ambiguityReasons?: string[];
   }

   export function classifyQuery(query: string): QueryClassification {
     // Detect ambiguity indicators
     const indicators = {
       pronouns: ["it", "they", "that", "this thing"],
       vague: ["something", "anything", "stuff", "whatever"],
       broad: ["all", "everything", "the whole", "each"],
       context_dependent: ["the", "a", "an"]  // Without nouns
     };

     // Count ambiguous patterns
     const ambiguousCount = countAmbiguousPatterns(query, indicators);

     // Classify
     if (ambiguousCount === 0) {
       return {
         intent: detectIntent(query),
         clarity: "clear",
         confidence: 0.9,
         suggestedMode: "one-shot"
       };
     } else if (ambiguousCount <= 2) {
       return {
         intent: detectIntent(query),
         clarity: "ambiguous",
         confidence: 0.6,
         suggestedMode: "conversational",
         ambiguityReasons: [`Found ${ambiguousCount} ambiguous indicators`]
       };
     } else {
       return {
         intent: "unknown",
         clarity: "requires_context",
         confidence: 0.3,
         suggestedMode: "conversational",
         ambiguityReasons: ["High ambiguity detected"]
       };
     }
   }
   ```

2. **Clarification Question Generator**
   ```typescript
   // File: gateway/src/agents/ClarificationGenerator.ts

   interface ClarificationQuestion {
     id: string;
     question: string;
     options: string[];
     multipleChoice: boolean;
     required: boolean;
   }

   export function generateClarifications(
     query: string,
     classification: QueryClassification
   ): ClarificationQuestion[] {

     const questions: ClarificationQuestion[] = [];

     // Based on ambiguity patterns
     if (classification.clarity === "ambiguous") {

       // Question 1: Aspect clarification
       if (query.toLowerCase().includes("auth")) {
         questions.push({
           id: "aspect",
           question: "What aspect of authentication are you asking about?",
           options: [
             "How it works (explanation)",
             "Code implementation",
             "Configuration",
             "Recent changes",
             "Troubleshooting"
           ],
           multipleChoice: false,
           required: true
         });
       }

       // Question 2: Scope clarification
       questions.push({
         id: "scope",
         question: "Which scope should I focus on?",
         options: [
           "Entire system",
           "Specific component(s)",
           "Specific file(s)",
           "Recent changes only"
         ],
         multipleChoice: false,
         required: classification.clarity === "requires_context"
       });

       // Question 3: Context clarification
       questions.push({
         id: "context",
         question: "What is your goal with this information?",
         options: [
           "Understanding/learning",
           "Implementation",
           "Debugging",
           "Documentation",
           "Refactoring"
         ],
         multipleChoice: true,
         required: false
       });
     }

     return questions;
   }
   ```

3. **Conversation State Manager** (In-Memory)
   ```typescript
   // File: gateway/src/agents/ConversationManager.ts

   interface ConversationState {
     conversationId: string;
     originalQuery: string;
     round: number;
     maxRounds: number;
     phase: "analyzing" | "clarifying" | "executing" | "completed";
     collectedContext: Record<string, any>;
     history: ConversationMessage[];
     startTime: number;
   }

   interface ConversationMessage {
     round: number;
     type: "query" | "clarification" | "answer" | "response";
     content: any;
     timestamp: number;
   }

   class ConversationManager {
     private activeConversations = new Map<string, ConversationState>();

     startConversation(query: string): ConversationState {
       const conversationId = generateUUID();
       const state: ConversationState = {
         conversationId,
         originalQuery: query,
         round: 1,
         maxRounds: 2,  // Phase 0b: 2 rounds max
         phase: "analyzing",
         collectedContext: {},
         history: [],
         startTime: Date.now()
       };

       this.activeConversations.set(conversationId, state);
       return state;
     }

     advanceRound(conversationId: string): ConversationState | null {
       const state = this.activeConversations.get(conversationId);
       if (!state) return null;

       if (state.round >= state.maxRounds) {
         // Force completion
         state.phase = "completed";
         return state;
       }

       state.round++;
       return state;
     }

     addContext(conversationId: string, key: string, value: any): void {
       const state = this.activeConversations.get(conversationId);
       if (state) {
         state.collectedContext[key] = value;
       }
     }

     endConversation(conversationId: string): ConversationState | null {
       const state = this.activeConversations.get(conversationId);
       if (state) {
         state.phase = "completed";
         this.activeConversations.delete(conversationId);
         return state;
       }
       return null;
     }

     getConversation(conversationId: string): ConversationState | undefined {
       return this.activeConversations.get(conversationId);
     }
   }

   export const conversationManager = new ConversationManager();
   ```

4. **Enhanced Query Response**
   ```typescript
   // File: gateway/src/agents/EnggContextAgent.ts (Enhanced)

   export class EnggContextAgent {

     async query(request: QueryRequest): Promise<QueryResponse | ConversationResponse> {

       // 1. Classify query
       const classification = classifyQuery(request.query);

       // 2. Decide mode (respect user preference)
       const mode = request.mode || classification.suggestedMode;

       // 3. Route based on mode
       if (mode === "conversational" && classification.clarity !== "clear") {

         // Start conversation
         const conversation = conversationManager.startConversation(request.query);

         // Generate clarifications
         const clarifications = generateClarifications(request.query, classification);

         // Return clarification response
         return {
           type: "conversation",
           conversationId: conversation.conversationId,
           round: 1,
           maxRounds: conversation.maxRounds,
           phase: "clarifying",
           clarifications: {
             questions: clarifications,
             message: "I need clarification to provide the best results"
           },
           meta: {
             originalQuery: request.query,
             detectedIntent: classification.intent,
             confidence: classification.confidence
           }
         };

       } else {

         // One-shot mode (existing logic)
         return await this.generateOneShotResponse(request, classification);
       }
     }

     async continueConversation(request: ConversationRequest): Promise<QueryResponse | ConversationResponse> {

       // Get conversation state
       const state = conversationManager.getConversation(request.conversationId);
       if (!state) {
         throw new Error("Conversation not found");
       }

       // Collect answers
       for (const [key, value] of Object.entries(request.answers)) {
         conversationManager.addContext(request.conversationId, key, value);
       }

       // Check if ready to generate response
       if (this.isContextSufficient(state)) {

         // Generate final response
         const enhancedQuery = this.enhanceQuery(state.originalQuery, state.collectedContext);
         const response = await this.generateOneShotResponse(
           { ...request, query: enhancedQuery },
           { intent: "inferred" }
         );

         // End conversation
         conversationManager.endConversation(request.conversationId);

         // Add conversation metadata
         (response as any).meta.conversationRounds = state.round;
         (response as any).meta.collectedContext = state.collectedContext;

         return response;

       } else {

         // Need more clarification
         const newClarifications = this.generateFollowUpClarifications(state);

         conversationManager.advanceRound(request.conversationId);

         return {
           type: "conversation",
           conversationId: request.conversationId,
           round: state.round,
           maxRounds: state.maxRounds,
           phase: "clarifying",
           clarifications: {
             questions: newClarifications,
             message: "I need a bit more information"
           },
           meta: {
             originalQuery: state.originalQuery,
             collectedContext: state.collectedContext
           }
         };
       }
     }

     private isContextSufficient(state: ConversationState): boolean {
       // Check if we have enough context to generate good response
       if (state.round >= state.maxRounds) return true;  // Force completion
       if (Object.keys(state.collectedContext).length >= 2) return true;  // Has 2+ pieces of context
       return false;
     }

     private enhanceQuery(originalQuery: string, context: Record<string, any>): string {
       // Enhance query with collected context
       let enhanced = originalQuery;

       if (context.aspect) {
         enhanced += ` (${context.aspect})`;
       }

       if (context.scope) {
         enhanced += ` focusing on ${context.scope}`;
       }

       if (context.goal) {
         enhanced += ` for ${context.goal}`;
       }

       return enhanced;
     }

     private generateFollowUpClarifications(state: ConversationState): ClarificationQuestion[] {
       // Generate targeted follow-up questions based on what we know
       const questions: ClarificationQuestion[] = [];

       if (!state.collectedContext.scope) {
         questions.push({
           id: "scope",
           question: "Which specific files or components should I focus on?",
           options: [],
           multipleChoice: false,
           required: true
         });
       }

       return questions;
     }

     private async generateOneShotResponse(
       request: QueryRequest,
       classification: QueryClassification
     ): Promise<QueryResponse> {
       // Existing one-shot logic
       // (This is the existing implementation from Phase 0a)
     }
   }
   ```

**Testing**:
```typescript
// Test: Clear query uses one-shot
const response1 = await agent.query({
   query: "Show me the AuthService class",
   requestId: "test-001"
});
assert(response1.type !== "conversation");

// Test: Ambiguous query starts conversation
const response2 = await agent.query({
   query: "What about the auth thing?",
   requestId: "test-002"
});
assert(response2.type === "conversation");
assert(response2.clarifications.questions.length > 0);

// Test: Conversation flow
const conversationId = response2.conversationId;
const response3 = await agent.continueConversation({
   conversationId,
   answers: {
     aspect: "How it works",
     scope: "All components"
   }
});
assert(response3.status === "success");
```

**Success Criteria**:
- [ ] Clear queries bypass conversation
- [ ] Ambiguous queries trigger clarification
- [ ] Max 2 rounds enforced
- [ ] Conversation state tracked
- [ ] Final response incorporates collected context

---

### Phase 1 Enhancement: Redis State Storage (Week 1)

**Duration**: 1-2 days

**Goal**: Move conversation state from in-memory to Redis for persistence and distributed support

**Scope**:
- Redis integration for state storage
- Conversation TTL configuration
- State recovery after restart

**Deliverables**:

1. **Redis State Storage**
   ```typescript
   // File: gateway/src/storage/RedisConversationStore.ts

   import { Redis } from 'ioredis';

   class RedisConversationStore {
     private redis: Redis;
     private keyPrefix = "conversation:";

     constructor() {
       this.redis = new Redis({
         host: process.env.REDIS_HOST || "localhost",
         port: parseInt(process.env.REDIS_PORT || "6379")
       });
     }

     async save(state: ConversationState): Promise<void> {
       const key = this.keyPrefix + state.conversationId;
       await this.redis.setex(key, 3600, JSON.stringify(state));  // 1 hour TTL
     }

     async load(conversationId: string): Promise<ConversationState | null> {
       const key = this.keyPrefix + conversationId;
       const data = await this.redis.get(key);
       if (!data) return null;
       return JSON.parse(data);
     }

     async delete(conversationId: string): Promise<void> {
       const key = this.keyPrefix + conversationId;
       await this.redis.del(key);
     }

     async getAllActive(): Promise<ConversationState[]> {
       const keys = await this.redis.keys(this.keyPrefix + "*");
       const states = await this.redis.mget(keys);
       return states.filter(Boolean).map(s => JSON.parse(s));
     }
   }
   ```

2. **Conversation Manager Enhancement**
   ```typescript
   // Enhanced ConversationManager with Redis backing

   class ConversationManager {
     private store: RedisConversationStore;
     private localCache = new Map<string, ConversationState>();  // Fast access

     constructor() {
       this.store = new RedisConversationStore();
     }

     async startConversation(query: string): Promise<ConversationState> {
       const state: ConversationState = {
         conversationId: generateUUID(),
         originalQuery: query,
         round: 1,
         maxRounds: 3,  // Phase 1: Increase to 3 rounds
         phase: "analyzing",
         collectedContext: {},
         history: [],
         startTime: Date.now()
       };

       // Save to Redis
       await this.store.save(state);

       // Cache locally
       this.localCache.set(state.conversationId, state);

       return state;
     }

     async getConversation(conversationId: string): Promise<ConversationState | null> {
       // Check local cache first
       if (this.localCache.has(conversationId)) {
         return this.localCache.get(conversationId)!;
       }

       // Load from Redis
       const state = await this.store.load(conversationId);
       if (state) {
         this.localCache.set(conversationId, state);
       }

       return state;
     }

     async advanceRound(conversationId: string): Promise<ConversationState | null> {
       const state = await this.getConversation(conversationId);
       if (!state) return null;

       if (state.round >= state.maxRounds) {
         state.phase = "completed";
         await this.store.save(state);
         return state;
       }

       state.round++;
       await this.store.save(state);
       this.localCache.set(conversationId, state);

       return state;
     }

     // ... other methods
   }
   ```

**Testing**:
```typescript
// Test: Persistence across restarts
const conversationId = "test-persistence";

// Start conversation
await agent.query({
   query: "What about auth?",
  requestId: "test-001"
});

// Simulate restart (clear local cache)
conversationManager.clearLocalCache();

// Should still be able to continue
const state = await conversationManager.getConversation(conversationId);
assert(state !== null);
```

**Success Criteria**:
- [ ] State persisted to Redis
- [ ] State recoverable after restart
- [ ] Local cache for fast access
- [ ] TTL cleanup (1 hour)

---

### Phase 2-3 Integration: Feature Enhancement (Weeks 2-3)

**Goal**: Use conversational mode for specific features

**Use Cases**:

1. **Ingestion Refinement**
   ```typescript
   // When ingesting new codebase, ask for clarification

   agent.query({
     query: "Ingest this codebase",
     mode: "conversational"
   });

   // Response:
   {
     clarifications: {
       questions: [
         "Which directories should I include?",
         "Should I include test files?",
         "What file types should I prioritize?"
       ]
     }
   }
   ```

2. **Veracity Check Enhancement**
   ```typescript
   // When checking veracity, ask for focus area

   agent.query({
     query: "Check veracity of authentication system",
     mode: "conversational"
   });

   // Response:
   {
     clarifications: {
       questions: [
         "What should I focus on?",
         "options": ["Stale documents", "Orphaned nodes", "Contradictions", "All"]
       ]
     }
   }
   ```

3. **Code Search Refinement**
   ```typescript
   // Refine search based on user feedback

   agent.continueConversation({
     conversationId: "conv-123",
     answers: {
       refinement: "Narrow down to JWT validation only"
     }
   });
   ```

**Success Criteria**:
- [ ] Ingestion uses conversation for project setup
- [ ] Veracity checks use conversation for scope
- [ ] Code search supports refinement

---

### Phase 4+: Advanced Features (Week 4+)

**Goal**: Add learning and optimization

**Features**:

1. **Conversation Pattern Learning**
   ```typescript
   // Learn from past conversations which clarifications are most useful

   interface ConversationAnalytics {
     totalConversations: number;
     averageRounds: number;
     mostEffectiveQuestions: string[];
     abandonedConversations: number;
     userSatisfaction: number;
   }

   async analyzeConversations(): Promise<ConversationAnalytics> {
     // Analyze Redis conversation history
     // Identify patterns
     // Suggest improvements
   }
   ```

2. **Predictive Question Generation**
   ```typescript
   // Predict what clarification questions will be needed
   // Based on query patterns

   function predictClarifications(query: string): ClarificationQuestion[] {
     // Use ML or pattern matching to predict
     // Pre-generate questions before user responds
   }
   ```

3. **Auto-Refinement**
   ```typescript
   // Agent proactively refines without asking

   async queryWithAutoRefinement(request: QueryRequest): Promise<QueryResponse> {

     // Initial results
     let results = await this.query(request);

     // If results are too broad, auto-refine
     if (results.meta.resultSize.semanticMatches > 50) {

       // Auto-narrow based on scores
       const topResults = results.results.semantic.matches.slice(0, 20);

       // Return with note
       results.warnings = [
         "Results narrowed to top 20 by relevance",
         "Use conversational mode for specific refinement"
       ];

       results.results.semantic.matches = topResults;
     }

     return results;
   }
   ```

**Success Criteria**:
- [ ] Analytics collected
- [ ] Patterns identified
- [ ] Auto-refinement working
- [ ] Satisfaction improved

---

## API Specification

### Endpoints

#### 1. Query (with mode selection)

```typescript
POST /query
Content-Type: application/json

{
  "query": string,
  "mode?: "one-shot" | "conversational" | "auto",
  "requestId": string,
  "maxRounds?: number,  // Max conversation rounds
  "timeout?: number     // Max duration (ms)
}

Response: QueryResponse | ConversationResponse
```

#### 2. Continue Conversation

```typescript
POST /query/continue
Content-Type: application/json

{
  "conversationId": string,
  "answers": Record<string, any>
}

Response: QueryResponse | ConversationResponse
```

#### 3. Abort Conversation

```typescript
DELETE /query/conversation/{conversationId}

Response: {
  "success": true,
  "abortedAt": number
}
```

#### 4. Get Conversation State

```typescript
GET /query/conversation/{conversationId}

Response: ConversationState
```

---

## Response Formats

### Conversation Initiation Response

```typescript
interface ConversationResponse {
  type: "conversation";
  conversationId: string;
  round: number;
  maxRounds: number;
  phase: "clarifying" | "executing" | "completed";

  // Clarification questions
  clarifications: {
    questions: Array<{
      id: string;
      question: string;
      options?: string[];
      multipleChoice: boolean;
      required: boolean;
    }>;
    message: string;
  };

  // Metadata
  meta: {
    originalQuery: string;
    detectedIntent: QueryIntent;
    confidence: number;
    estimatedRoundsRemaining: number;
  };
}
```

---

## Data Model

### Conversation State Schema

```typescript
interface ConversationState {
  // Identification
  conversationId: string;
  requestId: string;

  // Query information
  originalQuery: string;
  enhancedQuery?: string;

  // Conversation progress
  round: number;
  maxRounds: number;
  phase: ConversationPhase;

  // Collected context
  collectedContext: {
    [key: string]: any;
  };

  // Classification
  classification: QueryClassification;

  // History
  history: ConversationMessage[];

  // Timing
  startTime: number;
  endTime?: number;
  lastActivity: number;

  // Status
  status: "active" | "completed" | "aborted" | "timeout";
}

type ConversationPhase =
  | "analyzing"      // Initial query analysis
  | "clarifying"    // Asking questions
  | "executing"      // Generating response
  | "completed";     // Done
```

---

## Monitoring and Observability

### Metrics to Track

```typescript
interface ConversationMetrics {
  // Volume metrics
  totalQueries: number;
  conversationalQueries: number;
  oneShotQueries: number;
  conversationRate: number;  // % that need conversation

  // Performance metrics
  averageRoundsPerConversation: number;
  averageLatency: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;

  // Quality metrics
  abandonedConversations: number;
  completionRate: number;
  averageConfidence: number;

  // Cache metrics
  cacheHitRate: number;
  redisConnectionErrors: number;
}
```

### Logging Strategy

```typescript
// Structured logging for conversations

logger.info({
  event: "conversation_started",
  conversationId,
  query,
  classification,
  timestamp: Date.now()
});

logger.info({
  event: "clarification_generated",
  conversationId,
  round,
  questions: clarifications.length,
  timestamp: Date.now()
});

logger.info({
  event: "context_collected",
  conversationId,
  round,
  contextKeys: Object.keys(answers),
  timestamp: Date.now()
});

logger.info({
  event: "conversation_completed",
  conversationId,
  rounds: state.round,
  duration: Date.now() - state.startTime,
  finalResponseGenerated: true,
  timestamp: Date.now()
});
```

---

## Testing Strategy

### Unit Tests

```typescript
describe("QueryClassifier", () => {

  it("classifies clear queries correctly", () => {
    const result = classifyQuery("Show me the AuthService class");
    expect(result.clarity).toBe("clear");
    expect(result.suggestedMode).toBe("one-shot");
  });

  it("detects ambiguous queries", () => {
    const result = classifyQuery("What about the auth thing?");
    expect(result.clarity).toBe("ambiguous");
    expect(result.suggestedMode).toBe("conversational");
  });

  it("detects context-dependent queries", () => {
    const result = classifyQuery("How does it work?");
    expect(result.clarity).toBe("requires_context");
  });
});

describe("ConversationManager", () => {

  it("manages conversation state", async () => {
    const state = await manager.startConversation("test query");
    expect(state.round).toBe(1);
    expect(state.phase).toBe("analyzing");
  });

  it("enforces round limits", async () => {
    const state = await manager.startConversation("test");
    state.maxRounds = 2;

    await manager.advanceRound(state.conversationId);  // Round 2
    const updated = await manager.advanceRound(state.conversationId);  // Round 3

    expect(updated.phase).toBe("completed");
  });

  it("persists state to Redis", async () => {
    const state = await manager.startConversation("test");

    const loaded = await manager.getConversation(state.conversationId);
    expect(loaded).toEqual(state);
  });
});

describe("EnggContextAgent", () => {

  it("returns one-shot for clear queries", async () => {
    const response = await agent.query({
      query: "Show me AuthService code",
      requestId: "test-001"
    });

    expect(response.type).not.toBe("conversation");
  });

  it("starts conversation for ambiguous queries", async () => {
    const response = await agent.query({
      query: "What about auth?",
      requestId: "test-002"
    });

    expect(response.type).toBe("conversation");
    expect(response.clarifications.questions.length).toBeGreaterThan(0);
  });

  it("continues conversation with answers", async () => {
    const conv1 = await agent.query({ query: "Tell me about it", requestId: "test" });

    const conv2 = await agent.continueConversation({
      conversationId: conv1.conversationId,
      answers: { aspect: "How it works" }
    });

    expect(conv2.status).toBe("success");
  });
});
```

### Integration Tests

```typescript
describe("Conversation Flow Integration", () => {

  it("handles full conversation flow", async () => {
    // Start
    const r1 = await agent.query({
      query: "What about the system?",
      mode: "conversational"
    });

    expect(r1.type).toBe("conversation");
    expect(r1.round).toBe(1);

    // Continue
    const r2 = await agent.continueConversation({
      conversationId: r1.conversationId,
      answers: {
        aspect: "How it works",
        scope: "All components"
      }
    });

    expect(r2.status).toBe("success");
    expect(r2.meta.conversationRounds).toBe(2);
  });

  it("aborts conversation on demand", async () => {
    const r1 = await agent.query({
      query: "Tell me about stuff",
      mode: "conversational"
    });

    // Abort
    await agent.abortConversation(r1.conversationId);

    // Verify
    const state = await agent.getConversationState(r1.conversationId);
    expect(state.status).toBe("aborted");
  });
});
```

---

## Deployment Checklist

### Configuration

```bash
# .env configuration
CONVERSATION_ENABLED=true
CONVERSATION_MAX_ROUNDS=3
CONVERSATION_TIMEOUT_MS=30000
REDIS_CONVERSATION_TTL=3600
CONVERSATION_ANALYTICS_ENABLED=true
```

### Dependencies

```json
{
  "dependencies": {
    "ioredis": "^5.0.0",
    "uuid": "^9.0.0"
  }
}
```

### Docker Compose Update

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

---

## Risk Mitigation

### Risk 1: Infinite Conversations

**Mitigation**:
- Hard limit on rounds (max 3)
- Time limit (max 30 seconds)
- Force completion after limits

### Risk 2: Poor User Experience

**Mitigation**:
- Make conversations optional
- Provide "skip" option
- Show progress indicators
- Estimate rounds remaining

### Risk 3: State Loss

**Mitigation**:
- Redis persistence
- Local cache fallback
- Periodic state snapshots
- Recovery procedures

### Risk 4: External Agent Incompatibility

**Mitigation**:
- Graceful fallback to one-shot
- Clear API documentation
- Example implementations
- Test with multiple agents

---

## Success Metrics

### Phase 0b Success Criteria

- [ ] 80%+ of clear queries use one-shot mode
- [ ] Ambiguous queries trigger conversation 90%+ of time
- [ ] Average conversation: 2 rounds
- [ ] <5% abandoned conversations
- [ ] <2 second latency per round

### Phase 1 Success Criteria

- [ ] State persistence 99.9% uptime
- [ ] <100ms state retrieval latency
- [ ] Zero state loss in testing
- [ ] Distributed conversation support

### Overall Success Criteria

- [ ] Conversational mode used <20% of queries
- [ ] User satisfaction >90%
- [ ] System determinism maintained (cached conversations)
- [ ] No performance degradation (>500ms latency)

---

## Timeline Summary

| Phase | Duration | Deliverables | Dependencies |
|-------|----------|-------------|--------------|
| **0b** | 2-3 days | Basic conversational mode | Phase 0a complete |
| **1** | 1-2 days | Redis state storage | Phase 0b complete |
| **2-3** | 2 weeks | Feature integration | Phase 1 complete |
| **4+** | Ongoing | Advanced features | Phase 2-3 complete |

---

## Next Steps

1. **Review and approve** this implementation plan
2. **Integrate** with main INTEGRATION_PLAN.md
3. **Begin Phase 0b** implementation after Phase 0a complete

---

**Document Status**: Detailed Planning | **Last Updated**: 2026-01-07
**Related**: [INTEGRATION_PLAN.md](../plans/INTEGRATION_PLAN.md) | [Research](../research/multi-agent-conversation-patterns-2026.md)
