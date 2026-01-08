/**
 * Unit Tests: Query Classifier
 * TDD RED Phase - These tests MUST fail initially
 */

import { describe, it, expect } from "vitest";
import { classifyQuery } from "../../agents/QueryClassifier.js";

describe("QueryClassifier", () => {
  describe("classifyQuery", () => {
    it("should classify clear query as one-shot mode", () => {
      const result = classifyQuery("Show me the AuthService class");

      expect(result.clarity).toBe("clear");
      expect(result.suggestedMode).toBe("one-shot");
      expect(result.confidence).toBeGreaterThan(0.8);
      expect(result.intent).toBeDefined();
    });

    it("should classify query with pronouns as ambiguous", () => {
      const result = classifyQuery("How does it work?");

      expect(result.clarity).toBe("ambiguous");
      expect(result.suggestedMode).toBe("conversational");
      expect(result.ambiguityReasons).toBeDefined();
      expect(result.ambiguityReasons?.length).toBeGreaterThan(0);
    });

    it("should classify query with vague terms as ambiguous", () => {
      const result = classifyQuery("Tell me something about authentication");

      expect(result.clarity).toBe("ambiguous");
      expect(result.suggestedMode).toBe("conversational");
      expect(result.confidence).toBeLessThan(0.8);
    });

    it("should classify query with broad terms as ambiguous", () => {
      const result = classifyQuery("Show me everything");

      expect(result.clarity).toBe("ambiguous");
      expect(result.suggestedMode).toBe("conversational");
    });

    it("should classify highly ambiguous query as requires_context", () => {
      const result = classifyQuery("Tell me something about that thing");

      expect(result.clarity).toBe("requires_context");
      expect(result.suggestedMode).toBe("conversational");
      expect(result.confidence).toBeLessThan(0.5);
    });

    it("should detect intent for code queries", () => {
      const result = classifyQuery("Show me the authentication code");

      expect(result.intent).toBe("code");
    });

    it("should detect intent for explanation queries", () => {
      const result = classifyQuery("Explain how authentication works");

      expect(result.intent).toBe("explanation");
    });

    it("should detect intent for location queries", () => {
      const result = classifyQuery("Where is the AuthService located?");

      expect(result.intent).toBe("location");
    });

    it("should detect intent for relationship queries", () => {
      const result = classifyQuery("What does AuthService depend on?");

      expect(result.intent).toBe("relationship");
    });

    it("should classify compound clear query correctly", () => {
      const result = classifyQuery(
        "Show me the UserService class and its dependencies",
      );

      expect(result.clarity).toBe("clear");
      expect(result.suggestedMode).toBe("one-shot");
      expect(result.intent).toBeDefined();
    });

    it("should handle empty query gracefully", () => {
      const result = classifyQuery("");

      expect(result.clarity).toBe("requires_context");
      expect(result.suggestedMode).toBe("conversational");
      expect(result.confidence).toBeLessThan(0.5);
    });

    it("should count multiple ambiguity indicators correctly", () => {
      const result = classifyQuery("Tell me about that thing over there");

      expect(result.ambiguityReasons?.length).toBeGreaterThan(1);
      expect(result.clarity).toBe("ambiguous");
    });
  });
});
