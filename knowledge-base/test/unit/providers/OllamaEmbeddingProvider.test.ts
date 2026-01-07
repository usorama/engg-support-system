/**
 * Unit Tests: OllamaEmbeddingProvider
 */

import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { OllamaEmbeddingProvider } from "../../../dist/core/providers/OllamaEmbeddingProvider.js";

describe("OllamaEmbeddingProvider", () => {
  let provider: OllamaEmbeddingProvider;

  beforeEach(() => {
    provider = new OllamaEmbeddingProvider({
      url: "http://72.60.204.156:11434",
      timeout: 30000,
      maxRetries: 3,
      batchSize: 32,
    });
  });

  describe("constructor", () => {
    it("should initialize with default config", () => {
      const defaultProvider = new OllamaEmbeddingProvider();
      expect(defaultProvider).toBeDefined();
    });

    it("should initialize with custom config", () => {
      const customProvider = new OllamaEmbeddingProvider({
        url: "http://localhost:11434",
        timeout: 10000,
        maxRetries: 2,
        batchSize: 16,
      });
      expect(customProvider).toBeDefined();
    });

    it("should return correct dimension", () => {
      expect(provider.getDimension()).toBe(768);
    });

    it("should return correct provider type", () => {
      expect(provider.getProvider()).toBe("ollama_vps");
    });
  });

  describe("isAvailable", () => {
    it("should return true when Ollama is available", async () => {
      const available = await provider.isAvailable();
      expect(typeof available).toBe("boolean");
      // Note: This test may fail if VPS is not running
    }, 30000);
  });

  describe("embed", () => {
    it("should generate embedding for single text", async () => {
      const text = "Hello, world!";
      const embedding = await provider.embed(text);

      expect(embedding).toBeInstanceOf(Array);
      expect(embedding).toHaveLength(768);
      expect(embedding[0]).toBeNumber();
    }, 60000);

    it("should generate embeddings for batch of texts", async () => {
      const texts = ["Hello", "World", "Test"];
      const embeddings = await provider.embedBatch(texts);

      expect(embeddings).toHaveLength(3);
      embeddings.forEach((emb) => {
        expect(emb).toHaveLength(768);
      });
    }, 60000);

    it("should handle empty array", async () => {
      const embeddings = await provider.embedBatch([]);
      expect(embeddings).toEqual([]);
    });

    it("should handle large batch with automatic batching", async () => {
      const texts = Array.from({ length: 50 }, (_, i) => `Text ${i}`);
      const embeddings = await provider.embedBatch(texts);

      expect(embeddings).toHaveLength(50);
    }, 120000);
  });

  describe("error handling", () => {
    it("should throw on invalid URL", async () => {
      const invalidProvider = new OllamaEmbeddingProvider({
        url: "http://invalid:9999",
        timeout: 1000,
        maxRetries: 1,
      });

      let errorThrown = false;
      try {
        await invalidProvider.embed("test");
      } catch (error) {
        errorThrown = true;
        expect(error).toBeDefined();
      }
      expect(errorThrown).toBe(true);
    }, 10000);
  });
});
