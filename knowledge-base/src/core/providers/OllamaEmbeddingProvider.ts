/**
 * Ollama Embedding Provider
 * Generates embeddings using Ollama nomic-embed-text model (768 dimensions)
 *
 * VPS Endpoint: http://72.60.204.156:11434
 * Model: nomic-embed-text
 * Dimensions: 768
 */

import axios, { type AxiosInstance } from "axios";
import type {} from "../types.js";
import { FallbackProvider } from "../types.js";

/**
 * Ollama embedding configuration
 */
export interface OllamaEmbeddingConfig {
  /** Ollama API URL (default: VPS) */
  url: string;
  /** Model name (default: nomic-embed-text) */
  model: string;
  /** Request timeout in milliseconds */
  timeout: number;
  /** Maximum retry attempts */
  maxRetries: number;
  /** Batch size for embeddings */
  batchSize: number;
}

/**
 * Ollama API response for embeddings
 */
interface OllamaEmbedResponse {
  embeddings: number[][];
  model: string;
}

/**
 * OllamaEmbeddingProvider - Generate embeddings using Ollama
 */
export class OllamaEmbeddingProvider {
  private client: AxiosInstance;
  private config: OllamaEmbeddingConfig;

  constructor(config: Partial<OllamaEmbeddingConfig> = {}) {
    this.config = {
      url: config.url || (process.env.OLLAMA_URL || "http://localhost:11434"),
      model: config.model || "nomic-embed-text",
      timeout: config.timeout || 90000,  // 90s for slower VPS performance
      maxRetries: config.maxRetries || 3,
      batchSize: config.batchSize || 32,
    };

    this.client = axios.create({
      baseURL: this.config.url,
      timeout: this.config.timeout,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  /**
   * Generate embedding for a single text
   * @param text - Input text
   * @returns Embedding vector (768 dimensions)
   */
  async embed(text: string): Promise<number[]> {
    const results = await this.embedBatch([text]);
    return results[0];
  }

  /**
   * Generate embeddings for a batch of texts
   * @param texts - Input texts
   * @returns Array of embedding vectors (each 768 dimensions)
   */
  async embedBatch(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) {
      return [];
    }

    // Process in batches if needed
    if (texts.length > this.config.batchSize) {
      const results: number[][] = [];
      for (let i = 0; i < texts.length; i += this.config.batchSize) {
        const batch = texts.slice(i, i + this.config.batchSize);
        const batchResults = await this.embedBatchWithRetry(batch);
        results.push(...batchResults);
      }
      return results;
    }

    return this.embedBatchWithRetry(texts);
  }

  /**
   * Generate embeddings with retry logic
   * @param texts - Input texts
   * @param attempt - Current attempt number
   * @returns Array of embedding vectors
   */
  private async embedBatchWithRetry(
    texts: string[],
    attempt: number = 1
  ): Promise<number[][]> {
    try {
      const response = await this.client.post<OllamaEmbedResponse>(
        "/api/embed",
        {
          model: this.config.model,
          input: texts,
        }
      );

      if (!response.data?.embeddings) {
        throw new Error("Invalid response from Ollama: missing embeddings");
      }

      const embeddings = response.data.embeddings;

      // Validate embedding dimensions
      for (const embedding of embeddings) {
        if (embedding.length !== 768) {
          throw new Error(
            `Invalid embedding dimension: expected 768, got ${embedding.length}`
          );
        }
      }

      return embeddings;
    } catch (error) {
      if (attempt < this.config.maxRetries) {
        // Exponential backoff: 1s, 2s, 4s
        const delay = Math.pow(2, attempt - 1) * 1000;
        console.warn(
          `Embedding attempt ${attempt} failed, retrying in ${delay}ms:`,
          error instanceof Error ? error.message : String(error)
        );
        await this.sleep(delay);
        return this.embedBatchWithRetry(texts, attempt + 1);
      }

      throw new Error(
        `Embedding generation failed after ${this.config.maxRetries} attempts: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    }
  }

  /**
   * Check if Ollama service is available
   * @returns true if Ollama is responding
   */
  async isAvailable(): Promise<boolean> {
    try {
      const response = await this.client.get("/api/tags", {
        timeout: 5000, // Short timeout for health check
      });

      // Check if our model is available
      const models = response.data?.models || [];
      // Use startsWith to match model with or without tag (e.g., "nomic-embed-text" matches "nomic-embed-text:latest")
      const modelAvailable = models.some(
        (m: { name: string }) => m.name === this.config.model || m.name.startsWith(this.config.model + ":")
      );

      return modelAvailable;
    } catch {
      return false;
    }
  }

  /**
   * Get embedding dimension
   * @returns Dimension of embeddings (768 for nomic-embed-text)
   */
  getDimension(): number {
    return 768;
  }

  /**
   * Get provider type
   * @returns Provider identifier
   */
  getProvider(): FallbackProvider {
    return FallbackProvider.OLLAMA_VPS;
  }

  /**
   * Sleep utility for retry delays
   * @param ms - Milliseconds to sleep
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
