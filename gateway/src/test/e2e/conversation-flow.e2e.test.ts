/**
 * E2E Tests: Conversation Flow
 *
 * End-to-end integration tests for the full conversation lifecycle:
 * 1. Start conversation with query
 * 2. Receive clarification questions
 * 3. Provide answers
 * 4. Continue through rounds
 * 5. Execute query with collected context
 *
 * Run with: docker-compose up -d redis
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { conversationManager } from "../../agents/ConversationManager.js";
import { classifyQuery } from "../../agents/QueryClassifier.js";
import { generateClarifications } from "../../agents/ClarificationGenerator.js";

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

describe("Conversation Flow (E2E)", () => {
  let redisAvailable: boolean;

  beforeAll(async () => {
    redisAvailable = await isRedisAvailable();
    if (!redisAvailable) {
      console.warn("⚠️  Redis not available - E2E tests will use in-memory fallback");
      console.warn("   Start Redis with: docker-compose up -d redis");
    }
  });

  afterAll(async () => {
    await conversationManager.close();
  });

  describe("Full conversation lifecycle", () => {
    it("should complete full 3-round conversation flow", async () => {
      // Round 1: Start conversation
      const initialState = await conversationManager.startConversation(
        "How do I implement authentication?",
      );

      expect(initialState.conversationId).toBeDefined();
      expect(initialState.round).toBe(1);
      expect(initialState.maxRounds).toBe(3);
      expect(initialState.phase).toBe("analyzing");
      expect(initialState.collectedContext).toEqual({});

      // Round 1: Add context
      await conversationManager.addContext(
        initialState.conversationId,
        "framework",
        "Express.js",
      );
      await conversationManager.addContext(
        initialState.conversationId,
        "authType",
        "JWT",
      );

      // Round 1 → Round 2: Advance
      const round2State = await conversationManager.advanceRound(
        initialState.conversationId,
      );

      expect(round2State).toBeDefined();
      expect(round2State?.round).toBe(2);
      expect(round2State?.phase).toBe("analyzing");

      // Verify context persisted
      expect(round2State?.collectedContext.framework).toBe("Express.js");
      expect(round2State?.collectedContext.authType).toBe("JWT");

      // Round 2: Add more context
      await conversationManager.addContext(
        initialState.conversationId,
        "database",
        "PostgreSQL",
      );

      // Round 2 → Round 3: Advance
      const round3State = await conversationManager.advanceRound(
        initialState.conversationId,
      );

      expect(round3State).toBeDefined();
      expect(round3State?.round).toBe(3);
      expect(round3State?.phase).toBe("analyzing");

      // Round 3: Add final context
      await conversationManager.addContext(
        initialState.conversationId,
        "experience",
        "intermediate",
      );

      // Round 3 → Complete: Advance (reaches maxRounds)
      const finalState = await conversationManager.advanceRound(
        initialState.conversationId,
      );

      expect(finalState?.phase).toBe("completed");
      expect(finalState?.round).toBe(3); // Should not increment beyond maxRounds

      // Verify all context collected
      expect(finalState?.collectedContext.framework).toBe("Express.js");
      expect(finalState?.collectedContext.authType).toBe("JWT");
      expect(finalState?.collectedContext.database).toBe("PostgreSQL");
      expect(finalState?.collectedContext.experience).toBe("intermediate");

      // Cleanup
      await conversationManager.endConversation(initialState.conversationId);
    });

    it("should handle conversation with no context gracefully", async () => {
      // Start conversation
      const state = await conversationManager.startConversation(
        "Quick question about caching",
      );

      // Immediately complete (no context collection needed)
      await conversationManager.advanceRound(state.conversationId); // Round 2
      await conversationManager.advanceRound(state.conversationId); // Round 3
      const completed = await conversationManager.advanceRound(
        state.conversationId,
      ); // Complete

      expect(completed?.phase).toBe("completed");
      expect(completed?.collectedContext).toEqual({});

      // Cleanup
      await conversationManager.endConversation(state.conversationId);
    });

    it("should persist conversation across retrieval cycles", async () => {
      // Create and populate conversation
      const state1 = await conversationManager.startConversation(
        "Persistence test query",
      );
      const actualId = state1.conversationId;

      await conversationManager.addContext(actualId, "key1", "value1");
      await conversationManager.addContext(actualId, "key2", "value2");

      // Retrieve conversation
      const state2 = await conversationManager.getConversation(actualId);

      expect(state2).toBeDefined();
      expect(state2?.conversationId).toBe(actualId);
      expect(state2?.collectedContext.key1).toBe("value1");
      expect(state2?.collectedContext.key2).toBe("value2");

      // Add more context
      await conversationManager.addContext(actualId, "key3", "value3");

      // Retrieve again to verify persistence
      const state3 = await conversationManager.getConversation(actualId);

      expect(state3?.collectedContext.key3).toBe("value3");

      // Cleanup
      await conversationManager.endConversation(actualId);
    });
  });

  describe("Integration with QueryClassifier and ClarificationGenerator", () => {
    it("should integrate classification with conversation flow", async () => {
      const query = "How do I add user authentication to my API?";

      // Classify the query
      const classification = classifyQuery(query);

      expect(classification.intent).toBeDefined();
      expect(classification.clarity).toBeDefined();

      // Start conversation based on classification
      const conversationState =
        await conversationManager.startConversation(query);

      expect(conversationState.phase).toBe("analyzing");

      // Generate clarifications based on classification
      const clarifications = generateClarifications(query, classification);

      expect(Array.isArray(clarifications)).toBe(true);

      // If clarifications are generated (query is ambiguous), test that flow
      if (clarifications.length > 0) {
        // Simulate user answering clarifications
        const answers: Record<string, unknown> = {
          framework: "Express.js",
          authMethod: "JWT tokens",
        };

        for (const [key, value] of Object.entries(answers)) {
          await conversationManager.addContext(
            conversationState.conversationId,
            key,
            value,
          );
        }

        // Verify context collected
        const retrieved = await conversationManager.getConversation(
          conversationState.conversationId,
        );

        expect(retrieved?.collectedContext.framework).toBe("Express.js");
        expect(retrieved?.collectedContext.authMethod).toBe("JWT tokens");
      } else {
        // Query is clear - verify no clarifications needed
        expect(classification.clarity).toBe("clear");
      }

      // Cleanup
      await conversationManager.endConversation(conversationState.conversationId);
    });

    it("should handle different query intents in conversations", async () => {
      const queries = [
        "How do I optimize database queries?",
        "What's the best way to handle errors?",
        "How can I improve API performance?",
      ];

      for (const query of queries) {
        const classification = classifyQuery(query);
        const state = await conversationManager.startConversation(query);

        expect(state.conversationId).toBeDefined();
        expect(classification.intent).toBeDefined();

        // Add context based on intent
        await conversationManager.addContext(
          state.conversationId,
          "intent",
          classification.intent,
        );

        // Verify context
        const retrieved = await conversationManager.getConversation(
          state.conversationId,
        );

        expect(retrieved?.collectedContext.intent).toBe(classification.intent);

        // Cleanup
        await conversationManager.endConversation(state.conversationId);
      }
    });
  });

  describe("Error handling and edge cases", () => {
    it("should handle non-existent conversation gracefully", async () => {
      const result = await conversationManager.getConversation(
        "non-existent-id",
      );

      expect(result).toBeUndefined();
    });

    it("should handle advancing non-existent conversation", async () => {
      const result = await conversationManager.advanceRound(
        "non-existent-id",
      );

      expect(result).toBeUndefined();
    });

    it("should handle ending non-existent conversation", async () => {
      const result = await conversationManager.endConversation(
        "non-existent-id",
      );

      expect(result).toBeUndefined();
    });

    it("should handle context operations on non-existent conversation", async () => {
      // Should not throw, just silently fail
      await expect(
        conversationManager.addContext("non-existent-id", "key", "value"),
      ).resolves.not.toThrow();
    });

    it("should handle rapid context additions", async () => {
      const state = await conversationManager.startConversation("Rapid test");

      // Add multiple context values rapidly
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(
          conversationManager.addContext(
            state.conversationId,
            `key${i}`,
            `value${i}`,
          ),
        );
      }

      await Promise.all(promises);

      // Verify all context persisted
      const retrieved = await conversationManager.getConversation(
        state.conversationId,
      );

      expect(retrieved?.collectedContext.key0).toBe("value0");
      expect(retrieved?.collectedContext.key9).toBe("value9");

      // Cleanup
      await conversationManager.endConversation(state.conversationId);
    });
  });

  describe("Conversation state management", () => {
    it("should track conversation lifecycle correctly", async () => {
      const state = await conversationManager.startConversation(
        "Lifecycle test",
      );

      // Initial state
      expect(state.phase).toBe("analyzing");
      expect(state.round).toBe(1);

      // Round 2
      await conversationManager.advanceRound(state.conversationId);
      let retrieved = await conversationManager.getConversation(
        state.conversationId,
      );
      expect(retrieved?.round).toBe(2);

      // Round 3
      await conversationManager.advanceRound(state.conversationId);
      retrieved = await conversationManager.getConversation(state.conversationId);
      expect(retrieved?.round).toBe(3);

      // Complete
      const completed = await conversationManager.advanceRound(
        state.conversationId,
      );
      expect(completed?.phase).toBe("completed");

      // Cleanup
      await conversationManager.endConversation(state.conversationId);

      // Should not exist after cleanup
      const final = await conversationManager.getConversation(
        state.conversationId,
      );
      expect(final).toBeUndefined();
    });

    it("should maintain conversation isolation", async () => {
      // Create multiple conversations
      const conv1 = await conversationManager.startConversation("Query 1");
      const conv2 = await conversationManager.startConversation("Query 2");
      const conv3 = await conversationManager.startConversation("Query 3");

      // Add different context to each
      await conversationManager.addContext(conv1.conversationId, "id", "1");
      await conversationManager.addContext(conv2.conversationId, "id", "2");
      await conversationManager.addContext(conv3.conversationId, "id", "3");

      // Verify isolation
      const retrieved1 = await conversationManager.getConversation(
        conv1.conversationId,
      );
      const retrieved2 = await conversationManager.getConversation(
        conv2.conversationId,
      );
      const retrieved3 = await conversationManager.getConversation(
        conv3.conversationId,
      );

      expect(retrieved1?.collectedContext.id).toBe("1");
      expect(retrieved2?.collectedContext.id).toBe("2");
      expect(retrieved3?.collectedContext.id).toBe("3");

      // Cleanup
      await conversationManager.endConversation(conv1.conversationId);
      await conversationManager.endConversation(conv2.conversationId);
      await conversationManager.endConversation(conv3.conversationId);
    });
  });
});
