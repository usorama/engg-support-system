/**
 * Integration Tests: Knowledge Base End-to-End
 * Tests the complete KB flow: ingest → query → summarize
 */

import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { KnowledgeBase } from "../../dist/core/KnowledgeBase.js";
import type { KBConfig, IngestDocument } from "../../dist/core/types.js";

describe("Knowledge Base E2E Integration", () => {
  let kb: KnowledgeBase;
  let config: KBConfig;

  beforeEach(async () => {
    // Configure KB to use VPS services (localhost for VPS testing, external IP for local testing)
    const isVPS = process.env.VPS === "true";

    config = {
      qdrant: {
        url: isVPS ? "http://127.0.0.1:6333" : (process.env.QDRANT_URL || "http://72.60.204.156:6333"),
        collection: "test_kb_e2e",
        timeout: 90000,  // 90s for VPS
        vectorSize: 768,
      },
      ollama: {
        vps: {
          url: isVPS ? "http://127.0.0.1:11434" : (process.env.OLLAMA_URL || "http://72.60.204.156:11434"),
          embedModel: "nomic-embed-text",
          summarizeModel: "llama3.2",
          timeout: 90000,  // 90s for VPS
          maxRetries: 3,
        },
        local: {
          enabled: false,
          url: "http://localhost:11434",
          embedModel: "nomic-embed-text",
          summarizeModel: "llama3.2",
          timeout: 10000,
        },
      },
      openai: {
        enabled: false,
        apiKey: undefined,
        embedModel: "text-embedding-3-small",
        summarizeModel: "gpt-4o-mini",
        timeout: 30000,
        fallbackTriggers: [],
        maxRetriesBeforeFallback: 3,
      },
      localCache: {
        enabled: false,
        path: "/tmp/kb_cache",
        maxSize: 500,
        maxDocuments: 10000,
        promotionThreshold: 0.6,
        demotionThreshold: 0.3,
      },
      knowledgeGraph: {
        enabled: true,
        relationshipSchema: "config/relationships.schema.yaml",
        maxTraversalDepth: 2,
        minRelationshipStrength: 0.5,
      },
      search: {
        semantic: {
          enabled: true,
          weight: 1.0,
          topK: 5,
          minScore: 0.7,
        },
        graph: {
          enabled: true,
          weight: 0.0,
          maxDepth: 2,
          followRelationships: [],
        },
      },
      summarization: {
        enabled: true,
        provider: "ollama",
        model: "llama3.2",
        citationRequired: true,
      },
      mcp: {
        enabled: false,
        port: 3000,
        auth: {
          enabled: false,
          apiKey: undefined,
        },
      },
      logging: {
        level: "error",
        format: "json",
      },
    };

    kb = new KnowledgeBase(config);
    await kb.initialize();
  }, 60000);

  afterEach(async () => {
    // Cleanup
    await kb.shutdown();
  });

  describe("initialization", () => {
    it("should initialize KB successfully", async () => {
      expect(kb).toBeDefined();
      // Should not throw
      await kb.initialize();
    }, 60000);

    it("should handle double initialization", async () => {
      await kb.initialize();
      // Should not throw
      await kb.initialize();
    }, 60000);
  });

  describe("ingest → query flow", () => {
    it("should ingest documents and query them back", async () => {
      // Ingest test documents
      const documents: IngestDocument[] = [
        {
          source: {
            repo: "test/repo",
            path: "src/Tool.ts",
            language: "typescript",
          },
          content:
            "The Tool interface defines function calling in Claude SDK. " +
            "It includes parameters, name, and description fields.",
        },
        {
          source: {
            repo: "test/repo",
            path: "docs/guide.md",
            language: "markdown",
          },
          content:
            "Tool use is the primary way to extend Claude's capabilities. " +
            "You can define custom tools for specific tasks.",
        },
      ];

      const ingestResult = await kb.ingest(documents);

      expect(ingestResult.status).toBe("completed");
      expect(ingestResult.documentsProcessed).toBe(2);
      expect(ingestResult.nodesCreated).toBe(2);

      // Wait for indexing
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Query for the ingested content
      const queryResult = await kb.query({
        query: "What is the Tool interface?",
        topK: 2,
      });

      expect(queryResult.results).toBeInstanceOf(Array);
      expect(queryResult.results.length).toBeGreaterThan(0);
      expect(queryResult.metadata.provider).toBeDefined();
      expect(queryResult.metadata.duration).toBeNumber();

      // Check that we got relevant results
      const topResult = queryResult.results[0];
      expect(topResult.score).toBeGreaterThan(0);
      expect(topResult.node.content).toContain("Tool");
    }, 120000);

    it("should return empty results for non-existent content", async () => {
      const queryResult = await kb.query({
        query: "xyz123nonexistentcontent456",
        topK: 5,
      });

      expect(queryResult.results).toBeInstanceOf(Array);
      // May be empty or have very low scores
      queryResult.results.forEach((result) => {
        expect(result.score).toBeLessThan(0.5); // Low relevance
      });
    }, 60000);
  });

  describe("summarization", () => {
    it("should generate summary with citations", async () => {
      // Ingest test documents
      const documents: IngestDocument[] = [
        {
          source: {
            repo: "test/repo",
            path: "docs/summarization.md",
          },
          content:
            "Claude SDK provides two main features: tool use and streaming. " +
            "Tool use allows function calling. Streaming enables real-time responses.",
        },
      ];

      await kb.ingest(documents);

      // Wait for indexing
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Query with summarization enabled
      const queryResult = await kb.query({
        query: "What are the main features of Claude SDK?",
        topK: 3,
      });

      expect(queryResult.summary).toBeDefined();
      expect(queryResult.summary?.text).toBeString();
      expect(queryResult.summary?.text.length).toBeGreaterThan(0);
      expect(queryResult.summary?.citations).toBeInstanceOf(Array);
      expect(queryResult.summary?.confidence).toBeGreaterThan(0);
    }, 120000);
  });

  describe("statistics", () => {
    it("should return KB statistics", async () => {
      const stats = await kb.getStats();

      expect(stats).toBeDefined();
      expect(stats.nodes).toBeGreaterThanOrEqual(0);
      expect(stats.collections).toContain("test_kb_e2e");
      expect(stats.cache).toBeDefined();
      expect(stats.ingestion).toBeDefined();
    }, 30000);
  });

  describe("health check", () => {
    it("should return healthy status when services are up", async () => {
      const health = await kb.healthCheck();

      expect(health).toBeDefined();
      expect(["healthy", "degraded", "unhealthy"]).toContain(health.status);
      expect(health.services.qdrant).toBeBoolean();
      expect(health.services.ollama).toBeBoolean();
    }, 30000);
  });

  describe("error handling", () => {
    it("should throw error when querying before initialization", async () => {
      const uninitializedKb = new KnowledgeBase(config);

      let errorThrown = false;
      try {
        await uninitializedKb.query({ query: "test", topK: 5 });
      } catch (error) {
        errorThrown = true;
        expect((error as Error).message).toContain("not initialized");
      }
      expect(errorThrown).toBe(true);
    });

    it("should throw error when ingesting before initialization", async () => {
      const uninitializedKb = new KnowledgeBase(config);

      let errorThrown = false;
      try {
        await uninitializedKb.ingest([]);
      } catch (error) {
        errorThrown = true;
        expect((error as Error).message).toContain("not initialized");
      }
      expect(errorThrown).toBe(true);
    });
  });

  describe("concurrent operations", () => {
    it("should handle multiple concurrent queries", async () => {
      // Ingest some content first
      const documents: IngestDocument[] = [
        {
          source: { repo: "test", path: "test1.md" },
          content: "Test content 1",
        },
        {
          source: { repo: "test", path: "test2.md" },
          content: "Test content 2",
        },
        {
          source: { repo: "test", path: "test3.md" },
          content: "Test content 3",
        },
      ];
      await kb.ingest(documents);

      // Wait for indexing
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Run concurrent queries
      const queries = [
        kb.query({ query: "test 1", topK: 2 }),
        kb.query({ query: "test 2", topK: 2 }),
        kb.query({ query: "test 3", topK: 2 }),
      ];

      const results = await Promise.all(queries);

      results.forEach((result) => {
        expect(result.results).toBeInstanceOf(Array);
        expect(result.metadata.duration).toBeNumber();
      });
    }, 120000);
  });
});
