/**
 * Unit Tests: OllamaSummarizer
 */

import { describe, it, expect, beforeEach } from "bun:test";
import { OllamaSummarizer } from "../../../dist/search/summarizer/OllamaSummarizer.js";
import type { KGNode } from "../../../dist/core/types.js";

describe("OllamaSummarizer", () => {
  let summarizer: OllamaSummarizer;
  let mockNodes: KGNode[];

  beforeEach(() => {
    summarizer = new OllamaSummarizer({
      url: "http://72.60.204.156:11434",
      timeout: 30000,
      temperature: 0.3,
      maxTokens: 4096,
    });

    // Create mock nodes
    mockNodes = [
      {
        id: "node1",
        type: "CODE" as any,
        content: "The Tool interface allows function calling in Claude SDK.",
        source: {
          repo: "anthropics/anthropic-sdk-typescript",
          path: "docs/tools.md",
          language: "typescript",
        },
        vector: [],
        relationships: [],
        metadata: {
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      {
        id: "node2",
        type: "MARKDOWN" as any,
        content: "Tool use is built on top of the function calling mechanism.",
        source: {
          repo: "anthropics/anthropic-sdk-typescript",
          path: "docs/examples.md",
          language: "typescript",
        },
        vector: [],
        relationships: [],
        metadata: {
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    ];
  });

  describe("constructor", () => {
    it("should initialize with default config", () => {
      const defaultSummarizer = new OllamaSummarizer();
      expect(defaultSummarizer).toBeDefined();
    });

    it("should initialize with custom config", () => {
      const customSummarizer = new OllamaSummarizer({
        url: "http://localhost:11434",
        timeout: 10000,
        temperature: 0.5,
        maxTokens: 2048,
      });
      expect(customSummarizer).toBeDefined();
    });

    it("should return correct provider type", () => {
      expect(summarizer.getProvider()).toBe("ollama_vps");
    });
  });

  describe("isAvailable", () => {
    it("should check if Ollama service is available", async () => {
      const available = await summarizer.isAvailable();
      expect(typeof available).toBe("boolean");
    }, 30000);
  });

  describe("summarizeWithCitations", () => {
    it("should generate summary with citations", async () => {
      const query = "What is tool use in Claude SDK?";
      const scores = [0.9, 0.8];

      const summary = await summarizer.summarizeWithCitations(
        query,
        mockNodes,
        scores
      );

      expect(summary).toBeDefined();
      expect(summary.text).toBeString();
      expect(summary.text.length).toBeGreaterThan(0);
      expect(summary.citations).toBeInstanceOf(Array);
      expect(summary.confidence).toBeGreaterThanOrEqual(0);
      expect(summary.confidence).toBeLessThanOrEqual(1);
    }, 60000);

    it("should throw on empty nodes array", async () => {
      let errorThrown = false;
      try {
        await summarizer.summarizeWithCitations("test", [], []);
      } catch (error) {
        errorThrown = true;
      }
      expect(errorThrown).toBe(true);
    });

    it("should throw on mismatched nodes and scores", async () => {
      let errorThrown = false;
      try {
        await summarizer.summarizeWithCitations("test", mockNodes, [0.5]);
      } catch (error) {
        errorThrown = true;
      }
      expect(errorThrown).toBe(true);
    });

    it("should include metadata in summary", async () => {
      const query = "What is tool use?";
      const scores = [0.9, 0.8];

      const summary = await summarizer.summarizeWithCitations(
        query,
        mockNodes,
        scores
      );

      expect(summary.metadata).toBeDefined();
      expect(summary.metadata.query).toBe(query);
      expect(summary.metadata.nodeCount).toBe(2);
      expect(summary.metadata.model).toBe("llama3.2");
      expect(summary.metadata.generatedAt).toBeString();
    }, 60000);
  });

  describe("citation extraction", () => {
    it("should extract citations from summary text", () => {
      // This is tested implicitly through summarizeWithCitations
      // The regex pattern should match [Source: file-path] format
      const textWithCitation = "According to [Source: docs/tools.md], tool use is important.";
      const citationRegex = /\[Source:\s*([^\]]+)\]/g;
      const matches = textWithCitation.match(citationRegex);
      expect(matches).toHaveLength(1);
    });
  });

  describe("confidence calculation", () => {
    it("should calculate confidence from scores and citations", async () => {
      const query = "What is tool use?";
      const scores = [0.9, 0.8];

      const summary = await summarizer.summarizeWithCitations(
        query,
        mockNodes,
        scores
      );

      // Confidence should be reasonable (between 0 and 1)
      expect(summary.confidence).toBeGreaterThan(0);
      expect(summary.confidence).toBeLessThanOrEqual(1);

      // With good scores and citations, confidence should be higher than 0.5
      expect(summary.confidence).toBeGreaterThan(0.5);
    }, 60000);
  });
});
