# Conversation API Documentation

> **Version**: Phase 1 (Redis-backed persistence) | **Last Updated**: 2026-01-08

This document provides comprehensive examples and usage patterns for the conversation system in the Engineering Support Gateway.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [ConversationManager API](#conversationmanager-api)
5. [Integration with EnggContextAgent](#integration-with-enggcontextagent)
6. [Redis Persistence](#redis-persistence)
7. [Advanced Patterns](#advanced-patterns)
8. [Error Handling](#error-handling)
9. [Testing](#testing)

---

## Overview

The conversation system enables multi-round dialogue between users and the EnggContextAgent. It allows the agent to:

- **Clarify ambiguous queries** through back-and-forth dialogue
- **Gather missing context** incrementally
- **Refine results** through iterative feedback
- **Maintain state** across service restarts via Redis persistence

**Key Features**:
- **3-round limit** (Phase 1) for focused conversations
- **Dual-layer caching** (local Map + Redis) for performance
- **Graceful fallback** to in-memory storage when Redis unavailable
- **TTL-based expiration** (1 hour) for automatic cleanup

---

## Quick Start

### Basic Conversation Flow

```typescript
import { ConversationManager } from "@engg-support/gateway";

// Create manager instance
const manager = new ConversationManager();

// Start a conversation
const state = await manager.startConversation("How do I implement authentication?");
// Returns: { conversationId: "uuid", round: 1, maxRounds: 3, phase: "analyzing", ... }

// Add context from user's answer
await manager.addContext(state.conversationId, "framework", "Express.js");
await manager.addContext(state.conversationId, "authType", "JWT");

// Advance to next round
const round2 = await manager.advanceRound(state.conversationId);
// Returns: { conversationId: "uuid", round: 2, maxRounds: 3, phase: "analyzing", collectedContext: { framework: "Express.js", authType: "JWT" } }

// End conversation when done
const finalState = await manager.endConversation(state.conversationId);
// Returns: { conversationId: "uuid", round: 2, phase: "completed", ... }

// Cleanup
await manager.close();
```

---

## Core Concepts

### Conversation State

```typescript
interface ConversationState {
  /** Unique conversation ID (UUID v4) */
  conversationId: string;

  /** Original query that started conversation */
  originalQuery: string;

  /** Current round number (1-based) */
  round: number;

  /** Maximum rounds allowed (Phase 1: 3) */
  maxRounds: number;

  /** Current conversation phase */
  phase: "analyzing" | "clarifying" | "executing" | "completed";

  /** Collected context from user */
  collectedContext: Record<string, unknown>;

  /** Message history */
  history: ConversationMessage[];

  /** Start timestamp */
  startTime: number;
}
```

### Conversation Lifecycle

```
┌─────────────┐
│ Start Query │
└──────┬──────┘
       │
       ▼
┌─────────────┐     addContext()     ┌──────────────┐
│ Round 1     │ ──────────────────▶ │ Collect Info │
│ (analyzing) │                     │ (optional)   │
└──────┬──────┘                     └──────────────┘
       │
       ▼ advanceRound()
┌─────────────┐     addContext()     ┌──────────────┐
│ Round 2     │ ──────────────────▶ │ Collect Info │
│ (analyzing) │                     │ (optional)   │
└──────┬──────┘                     └──────────────┘
       │
       ▼ advanceRound()
┌─────────────┐     addContext()     ┌──────────────┐
│ Round 3     │ ──────────────────▶ │ Collect Info │
│ (analyzing) │                     │ (optional)   │
└──────┬──────┘                     └──────────────┘
       │
       ▼ advanceRound()
┌─────────────┐
│ Completed   │  (max rounds reached)
└─────────────┘
```

---

## ConversationManager API

### Constructor

```typescript
const manager = new ConversationManager();
```

Creates a new ConversationManager instance with:
- Redis backing (if available)
- Local cache for fast access
- In-memory fallback (if Redis unavailable)

### Methods

#### `startConversation(query: string): Promise<ConversationState>`

Starts a new conversation with the user's query.

**Parameters**:
- `query`: The user's initial query

**Returns**: The initial conversation state

**Example**:
```typescript
const state = await manager.startConversation("How do I optimize database queries?");
console.log(state.conversationId); // "550e8400-e29b-41d4-a716-446655440000"
console.log(state.round); // 1
console.log(state.maxRounds); // 3
console.log(state.phase); // "analyzing"
```

#### `getConversation(conversationId: string): Promise<ConversationState | undefined>`

Retrieves conversation state by ID.

**Parameters**:
- `conversationId`: The conversation UUID

**Returns**: The conversation state, or `undefined` if not found

**Search Order**:
1. Local cache (fastest)
2. Redis (persistent)
3. Returns `undefined` if not found

**Example**:
```typescript
const state = await manager.getConversation("550e8400-e29b-41d4-a716-446655440000");
if (state) {
  console.log(`Round ${state.round} of ${state.maxRounds}`);
  console.log("Collected context:", state.collectedContext);
}
```

#### `addContext(conversationId: string, key: string, value: unknown): Promise<void>`

Adds context information to the conversation.

**Parameters**:
- `conversationId`: The conversation UUID
- `key`: Context key (e.g., "framework", "database")
- `value`: Context value (any JSON-serializable type)

**Side Effects**:
- Updates `collectedContext` in state
- Persists to Redis
- Updates local cache

**Example**:
```typescript
await manager.addContext(convId, "framework", "Express.js");
await manager.addContext(convId, "database", "PostgreSQL");
await manager.addContext(convId, "orm", "Prisma");
await manager.addContext(convId, "complexity", "high");
```

#### `advanceRound(conversationId: string): Promise<ConversationState | undefined>`

Advances the conversation to the next round.

**Parameters**:
- `conversationId`: The conversation UUID

**Returns**: Updated conversation state, or `undefined` if conversation not found

**Behavior**:
- If `round >= maxRounds`: Sets phase to "completed"
- Otherwise: Increments round by 1

**Example**:
```typescript
const nextState = await manager.advanceRound(convId);
if (nextState?.phase === "completed") {
  console.log("Conversation completed!");
  console.log("Collected context:", nextState.collectedContext);
} else {
  console.log(`Now in round ${nextState?.round}`);
}
```

#### `endConversation(conversationId: string): Promise<ConversationState | undefined>`

Ends the conversation and cleans up resources.

**Parameters**:
- `conversationId`: The conversation UUID

**Returns**: Final conversation state, or `undefined` if not found

**Side Effects**:
- Sets phase to "completed"
- Deletes from Redis
- Removes from local cache

**Example**:
```typescript
const finalState = await manager.endConversation(convId);
console.log("Conversation ended with phase:", finalState?.phase);
console.log("Total rounds:", finalState?.round);
console.log("Collected context:", finalState?.collectedContext);

// Conversation is now deleted - subsequent getConversation returns undefined
const check = await manager.getConversation(convId);
console.log(check); // undefined
```

#### `close(): Promise<void>`

Closes the manager and releases resources.

**Example**:
```typescript
await manager.close();
```

---

## Integration with EnggContextAgent

### Using Conversation Mode in Queries

The EnggContextAgent supports both one-shot and conversational modes:

```typescript
import { EnggContextAgent } from "@engg-support/gateway";

const agent = new EnggContextAgent();

// One-shot query (default)
const response1 = await agent.query({
  query: "What is the architecture of the payment service?",
  requestId: "req-001"
});
// Direct response without conversation

// Conversational query
const response2 = await agent.query({
  query: "How do I add authentication?",
  requestId: "req-002",
  mode: "conversational"
});
// Returns clarifications if query is ambiguous
```

### Conversational Response Structure

```typescript
interface ConversationalResponse {
  type: "clarification" | "response";
  conversationId?: string;
  round?: number;
  clarifications?: Array<{
    key: string;
    question: string;
    options?: string[];
  }>;
  answer?: string;
  sources?: Citation[];
}
```

### Example: Full Conversational Flow

```typescript
const agent = new EnggContextAgent();

// Round 1: User asks ambiguous question
const response1 = await agent.query({
  query: "How do I implement caching?",
  requestId: "req-001",
  mode: "conversational"
});

if (response1.type === "clarification") {
  console.log("Conversation ID:", response1.conversationId);
  console.log("Clarifications needed:");

  response1.clarifications.forEach((q) => {
    console.log(`- ${q.question}`);
  });

  // Round 2: User provides answers
  const response2 = await agent.query({
    query: "I'm using Express.js with Redis",
    requestId: "req-002",
    conversationId: response1.conversationId
  });

  if (response2.type === "clarification") {
    // More clarifications needed
    const response3 = await agent.query({
      query: "Cache for API responses, 5 minute TTL",
      requestId: "req-003",
      conversationId: response2.conversationId
    });

    if (response3.type === "response") {
      // Final answer with all context incorporated
      console.log("Answer:", response3.answer);
      console.log("Sources:", response3.sources);
    }
  }
}
```

---

## Redis Persistence

### Redis vs In-Memory Mode

The ConversationManager automatically detects Redis availability:

```typescript
const manager = new ConversationManager();

// Redis available: Persists to Redis + local cache
// Redis unavailable: Falls back to in-memory Map only

// Check if Redis is being used (for debugging)
const store = (manager as any).redisStore;
console.log("Redis available:", store.redisAvailable);
```

### Configuration

Redis connection uses environment variables:

```bash
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=          # Optional
REDIS_DB=0              # Optional
```

### TTL Behavior

Conversations expire after **1 hour** of inactivity:

```typescript
const state = await manager.startConversation("Test");

// 1 hour later...
const check = await manager.getConversation(state.conversationId);
console.log(check); // undefined (expired and auto-deleted)
```

### Persistence Across Restarts

```typescript
// Manager 1: Create conversation
const manager1 = new ConversationManager();
const state1 = await manager1.startConversation("Persistence test");
await manager1.addContext(state1.conversationId, "key", "value");
await manager1.close();

// Simulate service restart...

// Manager 2: Retrieve conversation (new instance)
const manager2 = new ConversationManager();
const state2 = await manager2.getConversation(state1.conversationId);

console.log(state2?.collectedContext.key); // "value" (persisted via Redis)
```

### Manual TTL Management

```typescript
const store = (manager as any).redisStore;

// Check TTL for a conversation
const ttl = await store.getTTL(conversationId);
console.log(`Expires in ${ttl} seconds`);

// Extend TTL (update the conversation to refresh TTL)
await manager.addContext(conversationId, "_refresh", Date.now());
```

---

## Advanced Patterns

### Pattern 1: Context-Aware Query Routing

```typescript
async function handleQuery(query: string) {
  const manager = new ConversationManager();
  const agent = new EnggContextAgent();

  // Classify query
  const classification = classifyQuery(query);

  if (classification.clarity === "clear") {
    // One-shot mode for clear queries
    return await agent.query({ query, requestId: generateId() });
  }

  // Conversational mode for ambiguous queries
  const state = await manager.startConversation(query);
  const clarifications = generateClarifications(query, classification);

  return {
    type: "clarification",
    conversationId: state.conversationId,
    round: state.round,
    clarifications
  };
}
```

### Pattern 2: Batch Context Collection

```typescript
async function collectBatchContext(conversationId: string, context: Record<string, unknown>) {
  const manager = new ConversationManager();

  // Add all context items in parallel
  const promises = Object.entries(context).map(([key, value]) =>
    manager.addContext(conversationId, key, value)
  );

  await Promise.all(promises);

  // Retrieve updated state
  const state = await manager.getConversation(conversationId);
  return state;
}

// Usage
const state = await collectBatchContext(convId, {
  framework: "Express.js",
  database: "PostgreSQL",
  orm: "Prisma",
  auth: "JWT",
  caching: "Redis"
});
```

### Pattern 3: Conversation Timeout Handling

```typescript
async function safeConversationOperation(
  conversationId: string,
  operation: () => Promise<void>
) {
  const manager = new ConversationManager();

  // Check conversation exists
  const state = await manager.getConversation(conversationId);
  if (!state) {
    throw new Error("Conversation not found or expired");
  }

  // Perform operation
  try {
    await operation();
  } catch (error) {
    // If conversation lost during operation
    const check = await manager.getConversation(conversationId);
    if (!check) {
      throw new Error("Conversation expired during operation");
    }
    throw error;
  }
}

// Usage
await safeConversationOperation(convId, async () => {
  await manager.addContext(convId, "key", "value");
  await manager.advanceRound(convId);
});
```

### Pattern 4: Conversation Recovery

```typescript
async function continueConversation(conversationId: string) {
  const manager = new ConversationManager();

  const state = await manager.getConversation(conversationId);

  if (!state) {
    // Conversation expired or never existed
    return {
      error: "Conversation not found",
      suggestion: "Start a new conversation"
    };
  }

  if (state.phase === "completed") {
    // Conversation already completed
    return {
      message: "Conversation completed",
      rounds: state.round,
      context: state.collectedContext
    };
  }

  // Resume conversation
  const roundsRemaining = state.maxRounds - state.round;
  return {
    message: "Conversation active",
    currentRound: state.round,
    roundsRemaining,
    context: state.collectedContext
  };
}
```

### Pattern 5: Multi-Manager Concurrent Access

```typescript
// Multiple managers can access the same conversation via Redis
const manager1 = new ConversationManager();
const manager2 = new ConversationManager();

// Manager 1 creates conversation
const state1 = await manager1.startConversation("Concurrent test");

// Manager 2 can read and modify
await manager2.addContext(state1.conversationId, "test", "from-manager-2");

// Manager 1 sees changes from manager 2
const state1Updated = await manager1.getConversation(state1.conversationId);
console.log(state1Updated.collectedContext.test); // "from-manager-2"
```

---

## Error Handling

### Conversation Not Found

```typescript
const state = await manager.getConversation("non-existent-id");

if (!state) {
  console.log("Conversation not found");
  // Handle gracefully - maybe start new conversation
}
```

### Redis Connection Failure

```typescript
// System automatically falls back to in-memory
// No action needed - operations continue transparently

const manager = new ConversationManager();

// This works even if Redis is down
const state = await manager.startConversation("Test");
await manager.addContext(state.conversationId, "key", "value");

// Note: State is lost when manager closes (no Redis persistence)
```

### Invalid Context Operations

```typescript
// Adding context to non-existent conversation silently fails
await manager.addContext("invalid-id", "key", "value");
// No error thrown, but context not added

// Best practice: Verify conversation exists first
const state = await manager.getConversation(conversationId);
if (state) {
  await manager.addContext(conversationId, "key", "value");
}
```

### Max Rounds Exceeded

```typescript
const state = await manager.startConversation("Test");

// Advance to max rounds
await manager.advanceRound(state.conversationId); // Round 2
await manager.advanceRound(state.conversationId); // Round 3
const completed = await manager.advanceRound(state.conversationId);

console.log(completed.phase); // "completed"
console.log(completed.round); // 3 (does not increment beyond maxRounds)

// Further advances have no effect
const again = await manager.advanceRound(state.conversationId);
console.log(again.round); // Still 3
```

---

## Testing

### Unit Test Example

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { ConversationManager } from "../src/agents/ConversationManager";

describe("ConversationManager", () => {
  let manager: ConversationManager;

  beforeEach(() => {
    manager = new ConversationManager();
  });

  it("should start conversation with initial state", async () => {
    const state = await manager.startConversation("Test query");

    expect(state.conversationId).toBeDefined();
    expect(state.round).toBe(1);
    expect(state.maxRounds).toBe(3);
    expect(state.phase).toBe("analyzing");
    expect(state.collectedContext).toEqual({});
  });

  it("should add context to conversation", async () => {
    const state = await manager.startConversation("Test");
    await manager.addContext(state.conversationId, "key", "value");

    const retrieved = await manager.getConversation(state.conversationId);
    expect(retrieved?.collectedContext.key).toBe("value");
  });

  it("should advance rounds correctly", async () => {
    const state = await manager.startConversation("Test");

    const round2 = await manager.advanceRound(state.conversationId);
    expect(round2?.round).toBe(2);

    const round3 = await manager.advanceRound(state.conversationId);
    expect(round3?.round).toBe(3);

    const completed = await manager.advanceRound(state.conversationId);
    expect(completed?.phase).toBe("completed");
    expect(completed?.round).toBe(3);
  });
});
```

### Integration Test Example

```typescript
describe("Conversation Integration", () => {
  it("should maintain conversation across manager instances", async () => {
    const manager1 = new ConversationManager();
    const state1 = await manager1.startConversation("Persistence test");
    await manager1.addContext(state1.conversationId, "key", "value");
    await manager1.close();

    const manager2 = new ConversationManager();
    const state2 = await manager2.getConversation(state1.conversationId);

    expect(state2?.collectedContext.key).toBe("value");
  });
});
```

---

## Best Practices

1. **Always close managers** when done to release resources:
   ```typescript
   await manager.close();
   ```

2. **Check for undefined** when retrieving conversations:
   ```typescript
   const state = await manager.getConversation(id);
   if (!state) { /* handle missing conversation */ }
   ```

3. **Use descriptive context keys** for better clarity:
   ```typescript
   // Good
   await manager.addContext(id, "framework", "Express.js");

   // Avoid
   await manager.addContext(id, "k1", "v1");
   ```

4. **Handle Redis unavailability** gracefully:
   ```typescript
   // System falls back automatically, but warn if Redis is down
   const store = (manager as any).redisStore;
   if (!store.redisAvailable) {
     console.warn("Redis unavailable - using in-memory storage");
   }
   ```

5. **Respect round limits** and check completion status:
   ```typescript
   if (state.phase === "completed") {
     console.log("Conversation already completed");
     return;
   }
   ```

---

## Type Exports

All conversation types are exported from the main package:

```typescript
import {
  ConversationManager,
  ConversationState,
  ConversationMessage,
  RedisConversationStore
} from "@engg-support/gateway";
```

---

**Document Version**: 1.0.0 | **API Version**: Phase 1 (Redis-backed)
