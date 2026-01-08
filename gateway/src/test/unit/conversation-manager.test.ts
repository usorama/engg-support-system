/**
 * Unit Tests: Conversation Manager
 * TDD RED Phase - These tests MUST fail initially
 */

import { describe, it, expect, beforeEach } from "vitest";
import { conversationManager } from "../../agents/ConversationManager.js";

describe("ConversationManager", () => {
  describe("startConversation", () => {
    it("should create a new conversation with unique ID", () => {
      const state = conversationManager.startConversation("What about auth?");

      expect(state).toBeDefined();
      expect(state.conversationId).toBeDefined();
      expect(state.conversationId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
      );
    });

    it("should initialize conversation in analyzing phase", () => {
      const state = conversationManager.startConversation("Tell me something");

      expect(state.phase).toBe("analyzing");
    });

    it("should set round to 1 for new conversation", () => {
      const state = conversationManager.startConversation("What about that?");

      expect(state.round).toBe(1);
    });

    it("should set maxRounds to 2 for Phase 0b", () => {
      const state = conversationManager.startConversation("Any information?");

      expect(state.maxRounds).toBe(2);
    });

    it("should store original query", () => {
      const query = "Show me everything";
      const state = conversationManager.startConversation(query);

      expect(state.originalQuery).toBe(query);
    });

    it("should initialize empty collected context", () => {
      const state = conversationManager.startConversation("What about the thing?");

      expect(state.collectedContext).toEqual({});
    });

    it("should initialize empty history", () => {
      const state = conversationManager.startConversation("Tell me about it");

      expect(state.history).toEqual([]);
    });

    it("should set start time", () => {
      const beforeTime = Date.now();
      const state = conversationManager.startConversation("What about that?");
      const afterTime = Date.now();

      expect(state.startTime).toBeGreaterThanOrEqual(beforeTime);
      expect(state.startTime).toBeLessThanOrEqual(afterTime);
    });
  });

  describe("advanceRound", () => {
    let conversationId: string;

    beforeEach(() => {
      const state = conversationManager.startConversation("Test query");
      conversationId = state.conversationId;
    });

    it("should advance to round 2", () => {
      const result = conversationManager.advanceRound(conversationId);

      expect(result?.round).toBe(2);
    });

    it("should return null for non-existent conversation", () => {
      const result = conversationManager.advanceRound("non-existent-id");

      expect(result).toBeNull();
    });

    it("should complete conversation when max rounds reached", () => {
      conversationManager.advanceRound(conversationId);
      const result = conversationManager.advanceRound(conversationId);

      expect(result?.phase).toBe("completed");
    });

    it("should not increment round beyond maxRounds", () => {
      conversationManager.advanceRound(conversationId);
      conversationManager.advanceRound(conversationId);
      const result = conversationManager.advanceRound(conversationId);

      expect(result?.round).toBe(2);
    });
  });

  describe("addContext", () => {
    let conversationId: string;

    beforeEach(() => {
      const state = conversationManager.startConversation("Test query");
      conversationId = state.conversationId;
    });

    it("should add context value to conversation", () => {
      conversationManager.addContext(conversationId, "aspect", "How it works");
      const state = conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.aspect).toBe("How it works");
    });

    it("should add multiple context values", () => {
      conversationManager.addContext(conversationId, "aspect", "Code");
      conversationManager.addContext(conversationId, "scope", "Entire system");
      const state = conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.aspect).toBe("Code");
      expect(state?.collectedContext.scope).toBe("Entire system");
    });

    it("should overwrite existing context with same key", () => {
      conversationManager.addContext(conversationId, "aspect", "First value");
      conversationManager.addContext(conversationId, "aspect", "Second value");
      const state = conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.aspect).toBe("Second value");
    });

    it("should handle null and undefined values", () => {
      conversationManager.addContext(conversationId, "key", null);
      const state = conversationManager.getConversation(conversationId);

      expect(state?.collectedContext.key).toBeNull();
    });
  });

  describe("endConversation", () => {
    let conversationId: string;

    beforeEach(() => {
      const state = conversationManager.startConversation("Test query");
      conversationId = state.conversationId;
    });

    it("should mark conversation as completed", () => {
      const result = conversationManager.endConversation(conversationId);

      expect(result?.phase).toBe("completed");
    });

    it("should remove conversation from active conversations", () => {
      conversationManager.endConversation(conversationId);
      const state = conversationManager.getConversation(conversationId);

      expect(state).toBeUndefined();
    });

    it("should return null for non-existent conversation", () => {
      const result = conversationManager.endConversation("non-existent-id");

      expect(result).toBeNull();
    });

    it("should return conversation state with final data", () => {
      conversationManager.addContext(conversationId, "test", "value");
      const result = conversationManager.endConversation(conversationId);

      expect(result?.collectedContext.test).toBe("value");
      expect(result?.phase).toBe("completed");
    });
  });

  describe("getConversation", () => {
    it("should return conversation state for valid ID", () => {
      const state = conversationManager.startConversation("Test query");
      const retrieved = conversationManager.getConversation(state.conversationId);

      expect(retrieved).toEqual(state);
    });

    it("should return undefined for non-existent conversation", () => {
      const result = conversationManager.getConversation("non-existent-id");

      expect(result).toBeUndefined();
    });
  });
});
