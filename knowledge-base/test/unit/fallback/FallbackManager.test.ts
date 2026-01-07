/**
 * Unit Tests: FallbackManager
 */

import { describe, it, expect, beforeEach } from "bun:test";
import { FallbackManager } from "../../../dist/core/fallback/FallbackManager.js";
import type { FallbackManagerConfig } from "../../../dist/core/fallback/FallbackManager.js";

describe("FallbackManager", () => {
  let manager: FallbackManager;
  let config: FallbackManagerConfig;

  beforeEach(() => {
    config = {
      ollamaVPS: {
        enabled: true,
        url: process.env.OLLAMA_URL || "http://localhost:11434",  // Use localhost for VPS testing
        timeout: 90000,  // 90s for VPS
        maxRetries: 3,
      },
      ollamaLocal: {
        enabled: false, // Disabled for tests
        url: "http://localhost:11434",
        timeout: 10000,
      },
      openai: {
        enabled: false, // Disabled for tests
        apiKey: undefined,
        timeout: 30000,
        maxRetriesBeforeFallback: 3,
      },
    };
    manager = new FallbackManager(config);
  });

  describe("constructor", () => {
    it("should initialize with config", () => {
      expect(manager).toBeDefined();
    });

    it("should accept all providers enabled", () => {
      const allEnabledConfig: FallbackManagerConfig = {
        ollamaVPS: {
          enabled: true,
          url: process.env.OLLAMA_URL || "http://localhost:11434",
          timeout: 90000,
          maxRetries: 3,
        },
        ollamaLocal: {
          enabled: true,
          url: "http://localhost:11434",
          timeout: 10000,
        },
        openai: {
          enabled: true,
          apiKey: "test-key",
          timeout: 30000,
          maxRetriesBeforeFallback: 3,
        },
      };
      const allEnabledManager = new FallbackManager(allEnabledConfig);
      expect(allEnabledManager).toBeDefined();
    });
  });

  describe("embed", () => {
    it("should generate embeddings with fallback", async () => {
      const request = {
        texts: ["Hello, world!", "Test embedding"],
      };

      const response = await manager.embed(request);

      expect(response).toBeDefined();
      expect(response.embeddings).toBeInstanceOf(Array);
      expect(response.embeddings).toHaveLength(2);
      expect(response.embeddings[0]).toHaveLength(768);
      expect(response.provider).toBe("ollama_vps"); // Should use VPS first
      expect(response.duration).toBeNumber();
    }, 60000);

    it("should handle empty array", async () => {
      const response = await manager.embed({ texts: [] });

      expect(response.embeddings).toEqual([]);
    });

    it("should handle single text", async () => {
      const response = await manager.embed({
        texts: ["Single text"],
      });

      expect(response.embeddings).toHaveLength(1);
      expect(response.embeddings[0]).toHaveLength(768);
    }, 30000);
  });

  describe("summarize", () => {
    it("should generate summary with fallback", async () => {
      const mockNodes = [
        {
          id: "node1",
          type: "CODE" as any,
          content: "Tool use allows function calling",
          source: { repo: "test", path: "test.md" } as any,
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

      const request = {
        query: "What is tool use?",
        nodes: mockNodes,
        scores: [0.9],
      };

      const response = await manager.summarize(request);

      expect(response).toBeDefined();
      expect(response.summary).toBeDefined();
      expect(response.summary.text).toBeString();
      expect(response.provider).toBe("ollama_vps");
      expect(response.duration).toBeNumber();
    }, 60000);

    it("should throw on empty nodes array", async () => {
      let errorThrown = false;
      try {
        await manager.summarize({
          query: "test",
          nodes: [],
          scores: [],
        });
      } catch (error) {
        errorThrown = true;
      }
      expect(errorThrown).toBe(true);
    });
  });

  describe("health status", () => {
    it("should return health status for all providers", async () => {
      const status = await manager.getHealthStatus();

      expect(status).toBeDefined();
      expect(status["ollama_vps"]).toBeDefined();
      expect(typeof status["ollama_vps"].available).toBe("boolean");
      expect(typeof status["ollama_vps"].latency).toBe("number");
    }, 30000);
  });

  describe("attempt history", () => {
    it("should track attempts", async () => {
      // Make a request to generate history
      await manager.embed({ texts: ["test"] });

      const history = manager.getAttemptHistory();

      expect(history).toBeInstanceOf(Array);
      expect(history.length).toBeGreaterThan(0);
      expect(history[0]).toHaveProperty("provider");
      expect(history[0]).toHaveProperty("success");
      expect(history[0]).toHaveProperty("duration");
    }, 30000);

    it("should filter history by provider", async () => {
      await manager.embed({ texts: ["test"] });

      const vpsAttempts = manager.getAttemptHistory("ollama_vps" as any);

      expect(vpsAttempts).toBeInstanceOf(Array);
      vpsAttempts.forEach((attempt) => {
        expect(attempt.provider).toBe("ollama_vps");
      });
    }, 30000);

    it("should clear history", async () => {
      await manager.embed({ texts: ["test"] });
      expect(manager.getAttemptHistory().length).toBeGreaterThan(0);

      manager.clearHistory();
      expect(manager.getAttemptHistory().length).toBe(0);
    }, 30000);
  });

  describe("statistics", () => {
    it("should return fallback statistics", async () => {
      // Generate some attempts
      await manager.embed({ texts: ["test1"] });
      await manager.embed({ texts: ["test2"] });

      const stats = manager.getStats();

      expect(stats).toBeDefined();
      expect(stats.totalAttempts).toBeGreaterThan(0);
      expect(stats.successRate).toBeGreaterThanOrEqual(0);
      expect(stats.successRate).toBeLessThanOrEqual(1);
      expect(stats.fallbackRate).toBeGreaterThanOrEqual(0);
      expect(stats.fallbackRate).toBeLessThanOrEqual(1);
      expect(stats.byProvider).toBeDefined();
    }, 60000);
  });

  describe("error handling", () => {
    it("should handle invalid URL gracefully", async () => {
      const invalidConfig: FallbackManagerConfig = {
        ollamaVPS: {
          enabled: false,
          url: "http://invalid:9999",
          timeout: 1000,
          maxRetries: 1,
        },
        ollamaLocal: {
          enabled: false,
          url: "http://localhost:11434",
          timeout: 10000,
        },
        openai: {
          enabled: false,
          timeout: 30000,
          maxRetriesBeforeFallback: 3,
        },
      };

      const invalidManager = new FallbackManager(invalidConfig);

      let errorThrown = false;
      try {
        await invalidManager.embed({ texts: ["test"] });
      } catch (error) {
        errorThrown = true;
      }
      expect(errorThrown).toBe(true);
    }, 10000);
  });
});
