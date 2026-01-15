/**
 * FallbackEmbeddingProvider - Multi-Provider Embeddings with Automatic Fallback
 *
 * Wraps multiple embedding providers and automatically falls back through
 * the chain when a provider fails. This ensures high availability of
 * embedding generation for vector search.
 *
 * @module FallbackEmbeddingProvider
 */

import type { EmbeddingProviderConfig } from "../config/providers.js";

// ============================================================================
// Types
// ============================================================================

/**
 * Embedding result with provider info
 */
export interface EmbeddingResult {
  /** The embedding vector */
  embedding: number[];
  /** Provider that generated the embedding */
  providerId: string;
  /** Provider display name */
  providerName: string;
  /** Number of providers tried before success */
  attemptCount: number;
  /** Whether fallback was used */
  usedFallback: boolean;
}

/**
 * Provider health status
 */
export interface EmbeddingProviderHealth {
  id: string;
  name: string;
  available: boolean;
  lastChecked: Date;
  lastError?: string;
  consecutiveFailures: number;
}

// ============================================================================
// FallbackEmbeddingProvider Class
// ============================================================================

/**
 * Multi-provider embedding generator with automatic fallback
 */
export class FallbackEmbeddingProvider {
  private readonly providers: EmbeddingProviderConfig[];
  private readonly healthStatus: Map<string, EmbeddingProviderHealth> = new Map();
  private readonly maxConsecutiveFailures = 3;
  private readonly healthCheckIntervalMs = 60000;

  constructor(providerConfigs: EmbeddingProviderConfig[]) {
    if (providerConfigs.length === 0) {
      throw new Error("At least one embedding provider must be configured");
    }

    this.providers = providerConfigs;

    // Initialize health status
    for (const config of this.providers) {
      this.healthStatus.set(config.id, {
        id: config.id,
        name: config.name,
        available: true,
        lastChecked: new Date(0),
        consecutiveFailures: 0,
      });
    }

    console.log(
      `[FallbackEmbeddingProvider] Initialized with ${this.providers.length} providers: ` +
        this.providers.map((p) => p.name).join(" → ")
    );
  }

  /**
   * Generate embedding with automatic fallback
   */
  async generateEmbedding(text: string): Promise<EmbeddingResult> {
    let attemptCount = 0;
    const failedProviders: string[] = [];

    for (const config of this.providers) {
      attemptCount++;

      // Check circuit breaker
      const health = this.healthStatus.get(config.id);
      if (health && health.consecutiveFailures >= this.maxConsecutiveFailures) {
        const timeSinceLastCheck = Date.now() - health.lastChecked.getTime();
        if (timeSinceLastCheck < this.healthCheckIntervalMs) {
          console.log(
            `[FallbackEmbeddingProvider] Skipping ${config.name} (circuit breaker open)`
          );
          failedProviders.push(config.name);
          continue;
        }
      }

      try {
        console.log(`[FallbackEmbeddingProvider] Trying ${config.name}...`);
        const embedding = await this.callProvider(config, text);

        // Validate dimensions
        if (embedding.length !== config.dimensions) {
          console.warn(
            `[FallbackEmbeddingProvider] ${config.name} returned ${embedding.length}d embedding, expected ${config.dimensions}d`
          );
          // Try to truncate/pad if needed
          if (embedding.length > config.dimensions) {
            embedding.length = config.dimensions;
          }
        }

        // Success
        this.updateHealthStatus(config.id, true);
        console.log(`[FallbackEmbeddingProvider] Success with ${config.name}`);

        return {
          embedding,
          providerId: config.id,
          providerName: config.name,
          attemptCount,
          usedFallback: attemptCount > 1,
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error(`[FallbackEmbeddingProvider] ${config.name} failed: ${errorMessage}`);
        this.updateHealthStatus(config.id, false, errorMessage);
        failedProviders.push(config.name);
      }
    }

    throw new Error(
      `All embedding providers failed. Tried: ${failedProviders.join(", ")}`
    );
  }

  /**
   * Call specific provider API
   */
  private async callProvider(
    config: EmbeddingProviderConfig,
    text: string
  ): Promise<number[]> {
    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      config.timeout ?? 30000
    );

    try {
      if (config.type === "ollama") {
        return await this.callOllama(config, text, controller.signal);
      } else if (config.type === "openai") {
        return await this.callOpenAI(config, text, controller.signal);
      } else if (config.type === "openrouter") {
        return await this.callOpenRouter(config, text, controller.signal);
      } else {
        throw new Error(`Unsupported provider type: ${config.type}`);
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Call Ollama embedding API
   */
  private async callOllama(
    config: EmbeddingProviderConfig,
    text: string,
    signal: AbortSignal
  ): Promise<number[]> {
    const response = await fetch(`${config.baseUrl}/api/embeddings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: config.model,
        prompt: text,
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.status}`);
    }

    const data = (await response.json()) as { embedding?: number[] };
    if (!data.embedding) {
      throw new Error("Invalid Ollama response: missing embedding");
    }

    return data.embedding;
  }

  /**
   * Call OpenAI embedding API
   */
  private async callOpenAI(
    config: EmbeddingProviderConfig,
    text: string,
    signal: AbortSignal
  ): Promise<number[]> {
    if (!config.apiKey) {
      throw new Error("OpenAI API key required");
    }

    const response = await fetch(`${config.baseUrl}/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        model: config.model,
        input: text,
        dimensions: config.dimensions,
      }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI API error: ${response.status} - ${errorText}`);
    }

    const data = (await response.json()) as {
      data?: Array<{ embedding?: number[] }>;
    };

    const embedding = data.data?.[0]?.embedding;
    if (!embedding) {
      throw new Error("Invalid OpenAI response: missing embedding");
    }

    return embedding;
  }

  /**
   * Call OpenRouter embedding API
   * Uses OpenAI-compatible endpoint
   */
  private async callOpenRouter(
    config: EmbeddingProviderConfig,
    text: string,
    signal: AbortSignal
  ): Promise<number[]> {
    if (!config.apiKey) {
      throw new Error("OpenRouter API key required");
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.apiKey}`,
    };

    // Add OpenRouter-specific headers
    if (config.extraHeaders) {
      Object.assign(headers, config.extraHeaders);
    }

    const response = await fetch(`${config.baseUrl}/embeddings`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: config.model,
        input: text,
        dimensions: config.dimensions,
      }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenRouter API error: ${response.status} - ${errorText}`);
    }

    const data = (await response.json()) as {
      data?: Array<{ embedding?: number[] }>;
    };

    const embedding = data.data?.[0]?.embedding;
    if (!embedding) {
      throw new Error("Invalid OpenRouter response: missing embedding");
    }

    return embedding;
  }

  /**
   * Check if primary provider is available
   */
  async isPrimaryAvailable(): Promise<boolean> {
    const primary = this.providers[0];
    if (!primary) return false;

    try {
      if (primary.type === "ollama") {
        const response = await fetch(`${primary.baseUrl}/api/tags`, {
          signal: AbortSignal.timeout(5000),
        });
        return response.ok;
      }
      // For API providers, assume available if configured
      return Boolean(primary.apiKey);
    } catch {
      return false;
    }
  }

  /**
   * Get health status of all providers
   */
  getHealthStatus(): EmbeddingProviderHealth[] {
    return Array.from(this.healthStatus.values());
  }

  /**
   * Update health status
   */
  private updateHealthStatus(
    providerId: string,
    success: boolean,
    error?: string
  ): void {
    const status = this.healthStatus.get(providerId);
    if (!status) return;

    if (success) {
      status.available = true;
      status.consecutiveFailures = 0;
      delete status.lastError;
    } else {
      status.consecutiveFailures++;
      if (error) {
        status.lastError = error;
      }
      if (status.consecutiveFailures >= this.maxConsecutiveFailures) {
        status.available = false;
      }
    }
    status.lastChecked = new Date();

    this.healthStatus.set(providerId, status);
  }

  /**
   * Get list of configured providers
   */
  getProviders(): Array<{ id: string; name: string; model: string; dimensions: number }> {
    return this.providers.map((p) => ({
      id: p.id,
      name: p.name,
      model: p.model,
      dimensions: p.dimensions,
    }));
  }
}

/**
 * Create FallbackEmbeddingProvider from configs
 */
export function createFallbackEmbeddingProvider(
  configs: EmbeddingProviderConfig[]
): FallbackEmbeddingProvider {
  return new FallbackEmbeddingProvider(configs);
}
