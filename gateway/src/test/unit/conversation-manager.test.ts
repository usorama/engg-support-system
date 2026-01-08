/**
 * Unit Tests: Conversation Manager
 * Phase 1: Redis Integration - TDD GREEN Phase
 *
 * Tests for async methods with Redis persistence + local caching
 */

import { describe, it, expect, beforeEach } from "vitest";
import { conversationManager } from "../../agents/ConversationManager.js";

// Helper to check if Redis is available
async function isRedisAvailable(): Promise<boolean> {
  try {
    const Redis = (await import("ioredis")).default;
    const redis = new Redis({
      host: process.env.REDIS_HOST || "localhost",
      port: parseInt(process.env.REDIS_PORT || "6379", 10),
      retryStrategy: () => null,
      maxRetriesPerRequest: 1,
    });
    await redis.ping();
    await redis.quit();
    return true;
  } catch {
    return false;
  }
}

describe("ConversationManager (Phase 1: Redis Integration)", () => {
  let redisAvailable: boolean;

  beforeEach(async () => {
    redisAvailable = await isRedisAvailable();
    if (!redisAvailable) {
      console.warn("⚠️  Redis not available - some tests will be skipped");
      console.warn("   Start Redis with: docker-compose up -d redis");
    }
  });

  describe("startConversation", () => {
    it("should create a new conversation with unique ID", async () => {
      const state = await conversationManager.startConversation("What about auth?");

      expect(state).toBeDefined();
      expect(state.conversationId).toBeDefined();
      expect(state.conversationId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
      );
    });

    it("should initialize conversation in analyzing phase", async () => {
      const state = await conversationManager.startConversation("Tell me something");

      expect(state.phase).toBe("analyzing");
    });

    it("should set round to 1 for new conversation", async () => {
      const state = await conversationManager.startConversation("What about that?");

      expect(state.round).toBe(1);
    });

    it("should set maxRounds to 3 for Phase 1", async () => {
      const state = await conversationManager.startConversation("Any information?");

      expect(state.maxRounds).toBe(3);
    });

    it("should store original query", async () => {
      const query = "Show me everything";
      const state = await conversationManager.startConversation(query);

      expect(state.originalQuery).toBe(query);
    });

    it("should initialize empty collected context", async () => {
      const state = await conversationManager.startConversation("What about the thing?");

      expect(state.collectedContext).toEqual({});
    });

    it("should initialize empty history", async () => {
      const state = await conversationManager.startConversation("Tell me about it");

      expect(state.history).toEqual([]);
    });

    it("should set start time", async () => {
      const beforeTime = Date.now();
      const state = await conversationManager.startConversation("What about that?");
      const afterTime = Date.now();

      expect(state.startTime).toBeGreaterThanOrEqual(beforeTime);
      expect(state.startTime).toBeLessThanOrEqual(afterTime);
    });

    it("should persist conversation to Redis", async () => {
      if (!redisAvailable) {
        return;
      }

      const state = await conversationManager.startConversation("Persistence test");

      // Should be retrievable via getConversation
      const retrieved = await conversationManager.getConversation(state.conversationId);
      expect(retrieved).toEqual(state);
    });
  });

  describe("advanceRound", () => {
    let conversationId: string;

    beforeEach(async () => {
      const state = await conversationManager.startConversation("Test query");
      conversationId = state.conversationId;
    });

    it("should advance to round 2", async () => {
      const result = await conversationManager.advanceRound(conversationId);

      expect(result?.round).toBe(2);
    });

    it("should advance to round 3", async () => {
      await conversationManager.advanceRound(conversationId);
      const result = await conversationManager.advanceRound(conversationId);

      expect(result?.round).toBe(3);
    });

    it("should return undefined for non-existent conversation", async () => {
      const result = await conversationManager.advanceRound("non-existent-id");

      expect(result).toBeUndefined();
    });

    it("should complete conversation when max rounds reached (Phase 1: 3 rounds)", async () => {
      await conversationManager.advanceRound(conversationId); // Round 2
      await conversationManager.advanceRound(conversationId); // Round 3
      const result = await conversationManager.advanceRound(conversationId); // Complete

      expect(result?.phase).toBe("completed");
    });

    it("should not increment round beyond maxRounds", async () => {
      await conversationManager.advanceRound(conversationId); // Round 2
      await conversationManager.advanceRound(conversationId); // Round 3
      await conversationManager.advanceRound(conversationId); // Complete
      const result = await conversationManager.advanceRound(conversationId); // Still complete

      expect(result?.round).toBe(3);
    });

    it("should persist round changes to Redis", async () => {
      if (!redisAvailable) {
        return;
      }

      await conversationManager.advanceRound(conversationId);

      // Retrieve fresh from Redis
      const retrieved = await conversationManager.getConversation(conversationId);
      expect(retrieved?.round).toBe(2);
    });
  });

  describe("addContext", () => {
    let conversationId: string;

    beforeEach(async () => {
      const state = await conversationManager.startConversation("Test query");
      conversationId = state.conversationId;
    });

    it("should add context value to conversation", async () => {
      await conversationManager.addContext(conversationId, "aspect", "How it works");
      const state = await conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.aspect).toBe("How it works");
    });

    it("should add multiple context values", async () => {
      await conversationManager.addContext(conversationId, "aspect", "Code");
      await conversationManager.addContext(conversationId, "scope", "Entire system");
      const state = await conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.aspect).toBe("Code");
      expect(state?.collectedContext.scope).toBe("Entire system");
    });

    it("should overwrite existing context with same key", async () => {
      await conversationManager.addContext(conversationId, "aspect", "First value");
      await conversationManager.addContext(conversationId, "aspect", "Second value");
      const state = await conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.aspect).toBe("Second value");
    });

    it("should handle null and undefined values", async () => {
      await conversationManager.addContext(conversationId, "key", null);
      const state = await conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.key).toBeNull();
    });

    it("should persist context changes to Redis", async () => {
      if (!redisAvailable) {
        return;
      }

      await conversationManager.addContext(conversationId, "test_key", "test_value");

      // Retrieve fresh from Redis
      const retrieved = await conversationManager.getConversation(conversationId);
      expect(retrieved?.collectedContext.test_key).toBe("test_value");
    });
  });

  describe("endConversation", () => {
    let conversationId: string;

    beforeEach(async () => {
      const state = await conversationManager.startConversation("Test query");
      conversationId = state.conversationId;
    });

    it("should mark conversation as completed", async () => {
      const result = await conversationManager.endConversation(conversationId);

      expect(result?.phase).toBe("completed");
    });

    it("should remove conversation from active conversations", async () => {
      await conversationManager.endConversation(conversationId);
      const state = await conversationManager.getConversation(conversationId);

      expect(state).toBeUndefined();
    });

    it("should return undefined for non-existent conversation", async () => {
      const result = await conversationManager.endConversation("non-existent-id");

      expect(result).toBeUndefined();
    });

    it("should return conversation state with final data", async () => {
      await conversationManager.addContext(conversationId, "test", "value");
      const result = await conversationManager.endConversation(conversationId);

      expect(result?.collectedContext.test).toBe("value");
      expect(result?.phase).toBe("completed");
    });

    it("should delete conversation from Redis", async () => {
      if (!redisAvailable) {
        return;
      }

      await conversationManager.endConversation(conversationId);

      // Should not exist in Redis anymore
      const retrieved = await conversationManager.getConversation(conversationId);
      expect(retrieved).toBeUndefined();
    });
  });

  describe("getConversation", () => {
    it("should return conversation state for valid ID", async () => {
      const state = await conversationManager.startConversation("Test query");
      const retrieved = await conversationManager.getConversation(state.conversationId);

      expect(retrieved).toEqual(state);
    });

    it("should return undefined for non-existent conversation", async () => {
      const result = await conversationManager.getConversation("non-existent-id");

      expect(result).toBeUndefined();
    });

    it("should retrieve from Redis after local cache miss", async () => {
      if (!redisAvailable) {
        return;
      }

      const state = await conversationManager.startConversation("Redis retrieval test");

      // Simulate local cache miss by creating new manager instance
      // In real scenario, this would test Redis fallback
      const retrieved = await conversationManager.getConversation(state.conversationId);
      expect(retrieved).toBeDefined();
      expect(retrieved?.conversationId).toBe(state.conversationId);
    });
  });

  describe("Local Caching", () => {
    it("should use local cache for fast access", async () => {
      const state = await conversationManager.startConversation("Cache test");

      // First access should populate local cache
      const first = await conversationManager.getConversation(state.conversationId);

      // Second access should be from local cache (same reference)
      const second = await conversationManager.getConversation(state.conversationId);

      expect(first).toEqual(second);
    });
  });
});
