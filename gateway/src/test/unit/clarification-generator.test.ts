/**
 * Unit Tests: Clarification Generator
 * TDD RED Phase - These tests MUST fail initially
 */

import { describe, it, expect } from "vitest";
import { generateClarifications } from "../../agents/ClarificationGenerator.js";
import type { QueryClassification } from "../../agents/QueryClassifier.js";

describe("ClarificationGenerator", () => {
  describe("generateClarifications", () => {
    const ambiguousClassification: QueryClassification = {
      intent: "unknown",
      clarity: "ambiguous",
      confidence: 0.6,
      suggestedMode: "conversational",
      ambiguityReasons: ["Found 2 ambiguous indicators"],
    };

    it("should generate clarification questions for ambiguous query", () => {
      const result = generateClarifications("What about auth?", ambiguousClassification);

      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
    });

    it("should generate aspect question for auth-related queries", () => {
      const result = generateClarifications("Tell me about auth", ambiguousClassification);

      const aspectQuestion = result.find((q) => q.id === "aspect");
      expect(aspectQuestion).toBeDefined();
      expect(aspectQuestion?.question).toContain("authentication");
    });

    it("should generate scope question for ambiguous queries", () => {
      const result = generateClarifications("Show me something", ambiguousClassification);

      const scopeQuestion = result.find((q) => q.id === "scope");
      expect(scopeQuestion).toBeDefined();
      expect(scopeQuestion?.options).toBeDefined();
      expect(scopeQuestion?.options.length).toBeGreaterThan(0);
    });

    it("should generate context question with multiple choice", () => {
      const result = generateClarifications("What about the code?", ambiguousClassification);

      const contextQuestion = result.find((q) => q.id === "context");
      expect(contextQuestion).toBeDefined();
      expect(contextQuestion?.multipleChoice).toBe(true);
    });

    it("should mark required questions correctly", () => {
      const result = generateClarifications("What about that thing?", {
        ...ambiguousClassification,
        clarity: "requires_context",
      });

      const requiredQuestions = result.filter((q) => q.required);
      expect(requiredQuestions.length).toBeGreaterThan(0);
    });

    it("should return empty array for clear queries", () => {
      const clearClassification: QueryClassification = {
        intent: "code",
        clarity: "clear",
        confidence: 0.9,
        suggestedMode: "one-shot",
      };

      const result = generateClarifications("Show me AuthService", clearClassification);

      expect(result).toEqual([]);
    });

    it("should include specific aspect options for auth queries", () => {
      const result = generateClarifications("Tell me about auth", ambiguousClassification);

      const aspectQuestion = result.find((q) => q.id === "aspect");
      expect(aspectQuestion?.options).toContain("How it works (explanation)");
      expect(aspectQuestion?.options).toContain("Code implementation");
    });

    it("should include scope options for system focus", () => {
      const result = generateClarifications("What about the system?", ambiguousClassification);

      const scopeQuestion = result.find((q) => q.id === "scope");
      expect(scopeQuestion?.options).toContain("Entire system");
      expect(scopeQuestion?.options).toContain("Specific component(s)");
    });

    it("should include goal options for context", () => {
      const result = generateClarifications("What about the code?", ambiguousClassification);

      const contextQuestion = result.find((q) => q.id === "context");
      expect(contextQuestion?.options).toContain("Understanding/learning");
      expect(contextQuestion?.options).toContain("Implementation");
      expect(contextQuestion?.options).toContain("Debugging");
    });

    it("should not mark context question as required", () => {
      const result = generateClarifications("What about the code?", ambiguousClassification);

      const contextQuestion = result.find((q) => q.id === "context");
      expect(contextQuestion?.required).toBe(false);
    });

    it("should mark scope question as required for requires_context", () => {
      const result = generateClarifications("What about that thing?", {
        ...ambiguousClassification,
        clarity: "requires_context",
      });

      const scopeQuestion = result.find((q) => q.id === "scope");
      expect(scopeQuestion?.required).toBe(true);
    });
  });
});
