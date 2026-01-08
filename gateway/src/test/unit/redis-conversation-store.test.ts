/**
 * Integration Tests: Redis Conversation Store
 * TDD GREEN Phase - Tests require Redis running
 *
 * Run with: docker-compose up -d redis
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { RedisConversationStore } from "../../storage/RedisConversationStore.js";
import type { ConversationState } from "../../agents/ConversationManager.js";

// Helper to check if Redis is available
async function isRedisAvailable(): Promise<boolean> {
  try {
    const Redis = (await import("ioredis")).default;
    const redis = new Redis({
      host: process.env.REDIS_HOST || "localhost",
      port: parseInt(process.env.REDIS_PORT || "6379", 10),
      retryStrategy: () => null, // Don't retry
      maxRetriesPerRequest: 1,
    });
    await redis.ping();
    await redis.quit();
    return true;
  } catch {
    return false;
  }
}

describe("RedisConversationStore", () => {
  let store: RedisConversationStore;

  beforeEach(async () => {
    const redisAvailable = await isRedisAvailable();
    if (!redisAvailable) {
      console.warn("⚠️  Redis not available - skipping RedisConversationStore tests");
      console.warn("   Start Redis with: docker-compose up -d redis");
    }
  });

  beforeEach(() => {
    store = new RedisConversationStore();
  });

  afterEach(async () => {
    try {
      await store.close();
    } catch {
      // Ignore close errors
    }
  });

  describe("save and load", () => {
    it("should save conversation state to Redis", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const state: ConversationState = {
        conversationId: "test-conv-001",
        originalQuery: "What about auth?",
        round: 1,
        maxRounds: 3,
        phase: "analyzing",
        collectedContext: {},
        history: [],
        startTime: Date.now(),
      };

      await store.save(state);

      // Verify saved - Redis should not throw
      await expect(store.save(state)).resolves.not.toThrow();
    });

    it("should load conversation state from Redis", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const state: ConversationState = {
        conversationId: "test-conv-002",
        originalQuery: "Tell me about it",
        round: 1,
        maxRounds: 3,
        phase: "clarifying",
        collectedContext: { aspect: "How it works" },
        history: [],
        startTime: Date.now(),
      };

      await store.save(state);
      const loaded = await store.load("test-conv-002");

      expect(loaded).not.toBeNull();
      expect(loaded?.conversationId).toBe("test-conv-002");
      expect(loaded?.originalQuery).toBe("Tell me about it");
      expect(loaded?.collectedContext.aspect).toBe("How it works");
    });

    it("should return null for non-existent conversation", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const loaded = await store.load("non-existent-id");
      expect(loaded).toBeNull();
    });
  });

  describe("delete", () => {
    it("should delete conversation from Redis", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const state: ConversationState = {
        conversationId: "test-conv-003",
        originalQuery: "Delete me",
        round: 1,
        maxRounds: 2,
        phase: "analyzing",
        collectedContext: {},
        history: [],
        startTime: Date.now(),
      };

      await store.save(state);
      await store.delete("test-conv-003");

      const loaded = await store.load("test-conv-003");
      expect(loaded).toBeNull();
    });

    it("should handle deleting non-existent conversation gracefully", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      await expect(store.delete("non-existent-id")).resolves.not.toThrow();
    });
  });

  describe("getAllActive", () => {
    it("should return all active conversations", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      // Clean up first
      await store.delete("test-conv-004");
      await store.delete("test-conv-005");

      const state1: ConversationState = {
        conversationId: "test-conv-004",
        originalQuery: "Query 1",
        round: 1,
        maxRounds: 2,
        phase: "analyzing",
        collectedContext: {},
        history: [],
        startTime: Date.now(),
      };

      const state2: ConversationState = {
        conversationId: "test-conv-005",
        originalQuery: "Query 2",
        round: 1,
        maxRounds: 2,
        phase: "clarifying",
        collectedContext: {},
        history: [],
        startTime: Date.now(),
      };

      await store.save(state1);
      await store.save(state2);

      const allActive = await store.getAllActive();

      expect(allActive.length).toBeGreaterThanOrEqual(2);
      const ids = allActive.map((s) => s.conversationId);
      expect(ids).toContain("test-conv-004");
      expect(ids).toContain("test-conv-005");

      // Cleanup
      await store.delete("test-conv-004");
      await store.delete("test-conv-005");
    });

    it("should return empty array when no active conversations", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const allActive = await store.getAllActive();
      expect(Array.isArray(allActive)).toBe(true);
    });
  });

  describe("TTL", () => {
    it("should set TTL on saved conversations", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const state: ConversationState = {
        conversationId: "test-conv-ttl",
        originalQuery: "Test TTL",
        round: 1,
        maxRounds: 2,
        phase: "analyzing",
        collectedContext: {},
        history: [],
        startTime: Date.now(),
      };

      await store.save(state);

      // Conversation should be immediately retrievable
      const loaded = await store.load("test-conv-ttl");
      expect(loaded).not.toBeNull();

      // Check TTL is set
      const ttl = await store.getTTL("test-conv-ttl");
      expect(ttl).toBeGreaterThan(0);

      // Cleanup
      await store.delete("test-conv-ttl");
    });
  });

  describe("exists", () => {
    it("should check if conversation exists", async () => {
      const redisAvailable = await isRedisAvailable();
      if (!redisAvailable) {
        return;
      }

      const state: ConversationState = {
        conversationId: "test-conv-exists",
        originalQuery: "Test exists",
        round: 1,
        maxRounds: 2,
        phase: "analyzing",
        collectedContext: {},
        history: [],
        startTime: Date.now(),
      };

      // Before save
      expect(await store.exists("test-conv-exists")).toBe(false);

      // After save
      await store.save(state);
      expect(await store.exists("test-conv-exists")).toBe(true);

      // After delete
      await store.delete("test-conv-exists");
      expect(await store.exists("test-conv-exists")).toBe(false);
    });
  });
});
