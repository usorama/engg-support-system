/**
 * E2E Tests: Redis Persistence Across Restarts
 *
 * Tests that conversation state persists correctly across:
 * 1. Service restarts (simulated by creating new manager instances)
 * 2. Cache invalidation (local cache cleared, Redis still has data)
 * 3. TTL expiration
 *
 * Run with: docker-compose up -d redis
 */

import { describe, it, expect, beforeAll } from "vitest";
import { ConversationManager } from "../../agents/ConversationManager.js";

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

describe("Redis Persistence (E2E)", () => {
  let redisAvailable: boolean;

  beforeAll(async () => {
    redisAvailable = await isRedisAvailable();
    if (!redisAvailable) {
      console.warn("⚠️  Redis not available - persistence tests will be skipped");
      console.warn("   Start Redis with: docker-compose up -d redis");
    }
  });

  describe("Persistence across manager instances", () => {
    it("should persist conversation when creating new manager instance", async () => {
      if (!redisAvailable) {
        return;
      }

      // Create conversation with first manager instance
      const manager1 = new ConversationManager();
      const state1 = await manager1.startConversation("Persistence test");

      // Add context
      await manager1.addContext(state1.conversationId, "key1", "value1");
      await manager1.addContext(state1.conversationId, "key2", "value2");

      // Close first manager
      await manager1.close();

      // Create new manager instance (simulates restart)
      const manager2 = new ConversationManager();

      // Wait a bit for Redis connection to establish
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Retrieve conversation with new manager
      const state2 = await manager2.getConversation(state1.conversationId);

      expect(state2).toBeDefined();
      expect(state2?.conversationId).toBe(state1.conversationId);
      expect(state2?.originalQuery).toBe("Persistence test");
      expect(state2?.collectedContext.key1).toBe("value1");
      expect(state2?.collectedContext.key2).toBe("value2");

      // Cleanup
      await manager2.endConversation(state1.conversationId);
      await manager2.close();
    });

    it("should maintain conversation state across multiple manager lifecycles", async () => {
      if (!redisAvailable) {
        return;
      }

      // First lifecycle
      const manager1 = new ConversationManager();
      const state1 = await manager1.startConversation("Lifecycle test");
      await manager1.addContext(state1.conversationId, "round", "1");
      await manager1.advanceRound(state1.conversationId);
      await manager1.close();

      // Second lifecycle
      const manager2 = new ConversationManager();
      await new Promise((resolve) => setTimeout(resolve, 100));

      const state2 = await manager2.getConversation(state1.conversationId);
      expect(state2?.round).toBe(2);
      if (state2) {
        await manager2.addContext(state2.conversationId, "round", "2");
        await manager2.advanceRound(state2.conversationId);
      }
      await manager2.close();

      // Third lifecycle
      const manager3 = new ConversationManager();
      await new Promise((resolve) => setTimeout(resolve, 100));

      const state3 = await manager3.getConversation(state1.conversationId);
      expect(state3?.round).toBe(3);
      expect(state3?.collectedContext.round).toBe("2");

      // Cleanup
      await manager3.endConversation(state1.conversationId);
      await manager3.close();
    });
  });

  describe("Cache invalidation", () => {
    it("should fall back to Redis when local cache is empty", async () => {
      if (!redisAvailable) {
        return;
      }

      const manager = new ConversationManager();
      const state = await manager.startConversation("Cache test");

      // Add context and verify in cache
      await manager.addContext(state.conversationId, "test", "value");
      let retrieved = await manager.getConversation(state.conversationId);
      expect(retrieved?.collectedContext.test).toBe("value");

      // Simulate cache invalidation by creating new manager
      await manager.close();
      const manager2 = new ConversationManager();
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Should still retrieve from Redis
      retrieved = await manager2.getConversation(state.conversationId);
      expect(retrieved?.collectedContext.test).toBe("value");

      // Cleanup
      await manager2.endConversation(state.conversationId);
      await manager2.close();
    });

    it("should update both cache and Redis on modifications", async () => {
      if (!redisAvailable) {
        return;
      }

      const manager = new ConversationManager();

      // Create conversation
      const state = await manager.startConversation("Sync test");
      await manager.addContext(state.conversationId, "initial", "value");

      // Verify in cache
      let retrieved = await manager.getConversation(state.conversationId);
      expect(retrieved?.collectedContext.initial).toBe("value");

      // Update context
      await manager.addContext(state.conversationId, "updated", "value2");

      // Verify update in cache
      retrieved = await manager.getConversation(state.conversationId);
      expect(retrieved?.collectedContext.updated).toBe("value2");

      // Verify update persisted to Redis by clearing cache
      await manager.close();
      const manager2 = new ConversationManager();
      await new Promise((resolve) => setTimeout(resolve, 100));

      retrieved = await manager2.getConversation(state.conversationId);
      expect(retrieved?.collectedContext.initial).toBe("value");
      expect(retrieved?.collectedContext.updated).toBe("value2");

      // Cleanup
      await manager2.endConversation(state.conversationId);
      await manager2.close();
    });
  });

  describe("TTL behavior", () => {
    it("should respect conversation TTL in Redis", async () => {
      if (!redisAvailable) {
        return;
      }

      const manager = new ConversationManager();
      const state = await manager.startConversation("TTL test");

      // Conversation should be immediately retrievable
      const retrieved = await manager.getConversation(state.conversationId);
      expect(retrieved).toBeDefined();

      // Check TTL is set
      const store = manager as unknown as { redisStore: { getTTL: (id: string) => Promise<number> } };
      const ttl = await store.redisStore.getTTL(state.conversationId);
      expect(ttl).toBeGreaterThan(0);

      // Cleanup
      await manager.endConversation(state.conversationId);
      await manager.close();
    });

    it("should handle conversation deletion", async () => {
      if (!redisAvailable) {
        return;
      }

      const manager = new ConversationManager();
      const state = await manager.startConversation("Delete test");

      // Verify conversation exists
      const store = manager as unknown as { redisStore: { exists: (id: string) => Promise<boolean> } };
      let exists = await store.redisStore.exists(state.conversationId);
      expect(exists).toBe(true);

      // End conversation (deletes from Redis)
      await manager.endConversation(state.conversationId);

      // Verify conversation deleted from Redis
      exists = await store.redisStore.exists(state.conversationId);
      expect(exists).toBe(false);

      // Verify not retrievable
      const retrieved = await manager.getConversation(state.conversationId);
      expect(retrieved).toBeUndefined();

      await manager.close();
    });
  });

  describe("Concurrent access", () => {
    it("should handle concurrent access to same conversation", async () => {
      if (!redisAvailable) {
        return;
      }

      const manager1 = new ConversationManager();
      const manager2 = new ConversationManager();

      const state = await manager1.startConversation("Concurrent test");

      // Both managers should be able to read the conversation
      const retrieved1 = await manager1.getConversation(state.conversationId);
      const retrieved2 = await manager2.getConversation(state.conversationId);

      expect(retrieved1).toBeDefined();
      expect(retrieved2).toBeDefined();
      expect(retrieved1?.conversationId).toBe(retrieved2?.conversationId);

      // Both should be able to add context
      await Promise.all([
        manager1.addContext(state.conversationId, "manager", "1"),
        manager2.addContext(state.conversationId, "manager", "2"),
      ]);

      // Last write should win
      const final = await manager1.getConversation(state.conversationId);
      expect(final?.collectedContext.manager).toBe("2");

      // Cleanup
      await manager1.endConversation(state.conversationId);
      await manager1.close();
      await manager2.close();
    });
  });
});
