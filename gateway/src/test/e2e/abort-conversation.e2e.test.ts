/**
 * E2E Tests: Abort Conversation Functionality
 *
 * Tests for conversation abort/cancel functionality:
 * 1. User can explicitly abort conversation
 * 2. Aborted conversations are cleaned up properly
 * 3. Aborted conversations don't execute queries
 * 4. Multiple abort scenarios
 */

import { describe, it, expect } from "vitest";
import { conversationManager } from "../../agents/ConversationManager.js";

describe("Abort Conversation (E2E)", () => {
  describe("Explicit abort via endConversation", () => {
    it("should abort conversation in first round", async () => {
      const state = await conversationManager.startConversation("Abort me");

      // Abort immediately
      const result = await conversationManager.endConversation(state.conversationId);

      expect(result).toBeDefined();
      expect(result?.phase).toBe("completed");
      expect(result?.conversationId).toBe(state.conversationId);

      // Verify conversation is gone
      const retrieved = await conversationManager.getConversation(
        state.conversationId,
      );
      expect(retrieved).toBeUndefined();
    });

    it("should abort conversation in middle of flow", async () => {
      const state = await conversationManager.startConversation("中途停止");

      // Add some context
      await conversationManager.addContext(state.conversationId, "key", "value");

      // Advance to round 2
      await conversationManager.advanceRound(state.conversationId);

      // Abort in middle
      const result = await conversationManager.endConversation(state.conversationId);

      expect(result?.phase).toBe("completed");
      expect(result?.round).toBe(2); // Should preserve final round number
      expect(result?.collectedContext.key).toBe("value"); // Should preserve context

      // Verify cleaned up
      const retrieved = await conversationManager.getConversation(
        state.conversationId,
      );
      expect(retrieved).toBeUndefined();
    });

    it("should abort conversation at max rounds", async () => {
      const state = await conversationManager.startConversation("Complete me");

      // Go through all rounds
      await conversationManager.advanceRound(state.conversationId); // Round 2
      await conversationManager.advanceRound(state.conversationId); // Round 3
      const completed = await conversationManager.advanceRound(
        state.conversationId,
      ); // Complete

      expect(completed?.phase).toBe("completed");

      // Abort (should be idempotent at this point)
      const result = await conversationManager.endConversation(
        state.conversationId,
      );

      expect(result).toBeDefined();
      expect(result?.phase).toBe("completed");
    });
  });

  describe("Abort behavior with context", () => {
    it("should preserve context when aborting", async () => {
      const state = await conversationManager.startConversation(
        "Preserve context",
      );

      // Add multiple context items
      await conversationManager.addContext(state.conversationId, "item1", "value1");
      await conversationManager.addContext(state.conversationId, "item2", "value2");
      await conversationManager.addContext(state.conversationId, "item3", "value3");

      // Abort
      const result = await conversationManager.endConversation(
        state.conversationId,
      );

      // Should return final state with all context
      expect(result?.collectedContext.item1).toBe("value1");
      expect(result?.collectedContext.item2).toBe("value2");
      expect(result?.collectedContext.item3).toBe("value3");
    });

    it("should handle abort with no context", async () => {
      const state = await conversationManager.startConversation("No context");

      // Abort without adding any context
      const result = await conversationManager.endConversation(
        state.conversationId,
      );

      expect(result?.collectedContext).toEqual({});
    });
  });

  describe("Multiple abort scenarios", () => {
    it("should handle multiple abort attempts gracefully", async () => {
      const state = await conversationManager.startConversation("Multi abort");

      // First abort
      const result1 = await conversationManager.endConversation(
        state.conversationId,
      );
      expect(result1).toBeDefined();

      // Second abort (should return undefined since already deleted)
      const result2 = await conversationManager.endConversation(
        state.conversationId,
      );
      expect(result2).toBeUndefined();
    });

    it("should handle abort after operations", async () => {
      const state = await conversationManager.startConversation("Complex flow");

      // Perform various operations
      await conversationManager.addContext(state.conversationId, "key", "value");
      await conversationManager.advanceRound(state.conversationId);
      await conversationManager.addContext(state.conversationId, "key2", "value2");

      // Abort after all operations
      const result = await conversationManager.endConversation(
        state.conversationId,
      );

      expect(result?.collectedContext.key).toBe("value");
      expect(result?.collectedContext.key2).toBe("value2");
      expect(result?.round).toBe(2);
    });
  });

  describe("Abort vs complete", () => {
    it("should distinguish between user abort and natural completion", async () => {
      // Natural completion
      const state1 = await conversationManager.startConversation(
        "Natural complete",
      );
      await conversationManager.advanceRound(state1.conversationId); // Round 2
      await conversationManager.advanceRound(state1.conversationId); // Round 3
      const completed = await conversationManager.advanceRound(
        state1.conversationId,
      ); // Complete

      expect(completed?.phase).toBe("completed");
      expect(completed?.round).toBe(3);

      // User abort (same end state)
      const state2 = await conversationManager.startConversation("User abort");
      await conversationManager.advanceRound(state2.conversationId); // Round 2
      const aborted = await conversationManager.endConversation(
        state2.conversationId,
      );

      expect(aborted?.phase).toBe("completed");
      expect(aborted?.round).toBe(2); // Stopped at round 2

      // Cleanup
      await conversationManager.endConversation(state1.conversationId);
    });
  });

  describe("Error scenarios", () => {
    it("should handle abort of non-existent conversation", async () => {
      const result = await conversationManager.endConversation(
        "non-existent-id",
      );

      expect(result).toBeUndefined();
    });

    it("should handle abort with invalid conversation ID", async () => {
      const result = await conversationManager.endConversation("");

      expect(result).toBeUndefined();
    });

    it("should handle rapid abort and recreate", async () => {
      // Create and immediately abort
      const state1 = await conversationManager.startConversation("Rapid 1");
      await conversationManager.endConversation(state1.conversationId);

      // Create new conversation with same query
      const state2 = await conversationManager.startConversation("Rapid 1");

      // Should have different IDs
      expect(state2.conversationId).not.toBe(state1.conversationId);

      // Cleanup
      await conversationManager.endConversation(state2.conversationId);
    });
  });

  describe("Cleanup verification", () => {
    it("should fully clean up aborted conversation", async () => {
      const state = await conversationManager.startConversation("Cleanup test");

      // Add context and advance
      await conversationManager.addContext(state.conversationId, "test", "value");
      await conversationManager.advanceRound(state.conversationId);

      // Abort
      await conversationManager.endConversation(state.conversationId);

      // Verify not retrievable
      const retrieved = await conversationManager.getConversation(
        state.conversationId,
      );
      expect(retrieved).toBeUndefined();

      // Verify operations don't recreate it
      await conversationManager.addContext(
        state.conversationId,
        "new",
        "value",
      );

      const stillRetrieved = await conversationManager.getConversation(
        state.conversationId,
      );
      expect(stillRetrieved).toBeUndefined();
    });
  });
});
