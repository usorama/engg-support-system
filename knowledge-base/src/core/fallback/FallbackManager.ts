/**
 * Fallback Manager
 * Orchestrates fallback chain: Ollama VPS → Ollama local → OpenAI
 *
 * VPS Endpoint: http://72.60.204.156:11434
 * Fallback triggers: timeout, container_down, retry_exceeded, model_not_found
 */

import type {
  EmbeddingRequest,
  EmbeddingResponse,
  SummarizationRequest,
  SummarizationResponse,
  FallbackTrigger,
  FallbackAttempt,
} from "../types.js";
import { FallbackProvider } from "../types.js";
import { OllamaEmbeddingProvider } from "../providers/OllamaEmbeddingProvider.js";
import { OllamaSummarizer } from "../../search/summarizer/OllamaSummarizer.js";

/**
 * Fallback manager configuration
 */
export interface FallbackManagerConfig {
  ollamaVPS: {
    enabled: boolean;
    url: string;
    timeout: number;
    maxRetries: number;
  };
  ollamaLocal: {
    enabled: boolean;
    url: string;
    timeout: number;
  };
  openai: {
    enabled: boolean;
    apiKey?: string;
    timeout: number;
    maxRetriesBeforeFallback: number;
  };
}

/**
 * Provider interface for embeddings
 */
interface EmbeddingProvider {
  embed(text: string): Promise<number[]>;
  embedBatch(texts: string[]): Promise<number[][]>;
  isAvailable(): Promise<boolean>;
  getProvider(): FallbackProvider;
}

/**
 * Provider interface for summarization
 */
interface SummarizationProvider {
  summarizeWithCitations(
    query: string,
    nodes: any[],
    scores: number[]
  ): Promise<any>;
  isAvailable(): Promise<boolean>;
  getProvider(): FallbackProvider;
}

/**
 * FallbackManager - Multi-provider orchestration with fallback
 */
export class FallbackManager {
  private config: FallbackManagerConfig;
  private embeddingProviders: EmbeddingProvider[] = [];
  private summarizationProviders: SummarizationProvider[] = [];
  private attemptHistory: FallbackAttempt[] = [];

  constructor(config: FallbackManagerConfig) {
    this.config = config;

    // Initialize embedding providers in priority order
    if (this.config.ollamaVPS.enabled) {
      this.embeddingProviders.push(
        new OllamaEmbeddingProvider({
          url: this.config.ollamaVPS.url,
          timeout: this.config.ollamaVPS.timeout,
          maxRetries: this.config.ollamaVPS.maxRetries,
        })
      );
    }

    if (this.config.ollamaLocal.enabled) {
      this.embeddingProviders.push(
        new OllamaEmbeddingProvider({
          url: this.config.ollamaLocal.url,
          timeout: this.config.ollamaLocal.timeout,
          maxRetries: 1, // Don't retry on local fallback
        })
      );
    }

    // Initialize summarization providers in priority order
    if (this.config.ollamaVPS.enabled) {
      this.summarizationProviders.push(
        new OllamaSummarizer({
          url: this.config.ollamaVPS.url,
          timeout: this.config.ollamaVPS.timeout,
        })
      );
    }

    if (this.config.ollamaLocal.enabled) {
      this.summarizationProviders.push(
        new OllamaSummarizer({
          url: this.config.ollamaLocal.url,
          timeout: this.config.ollamaLocal.timeout,
        })
      );
    }
  }

  /**
   * Embed texts with fallback chain
   * @param request - Embedding request
   * @returns Embedding response with provider info
   */
  async embed(request: EmbeddingRequest): Promise<EmbeddingResponse> {
    const startTime = Date.now();

    for (const provider of this.embeddingProviders) {
      const providerType = provider.getProvider();
      const attempt: FallbackAttempt = {
        provider: providerType,
        success: false,
        duration: 0,
      };

      try {
        // Check if provider is available
        const available = await provider.isAvailable();
        if (!available) {
          attempt.error = "Provider not available";
          attempt.trigger = "container_down" as FallbackTrigger;
          this.recordAttempt(attempt);
          continue; // Try next provider
        }

        // Try to embed
        const embeddings =
          request.texts.length === 1
            ? [await provider.embed(request.texts[0])]
            : await provider.embedBatch(request.texts);

        // Success!
        attempt.success = true;
        attempt.duration = Date.now() - startTime;
        this.recordAttempt(attempt);

        return {
          embeddings,
          model: request.model || "nomic-embed-text",
          provider: providerType,
          duration: attempt.duration,
        };
      } catch (error) {
        const triggerType = this.detectTriggerType(error);
        attempt.error = error instanceof Error ? error.message : String(error);
        attempt.trigger = triggerType;
        attempt.duration = Date.now() - startTime;
        this.recordAttempt(attempt);

        // If no more providers, throw
        if (provider === this.embeddingProviders[this.embeddingProviders.length - 1]) {
          throw new Error(
            `All embedding providers failed. Last error: ${attempt.error}`
          );
        }

        // Otherwise, continue to next provider
        console.warn(
          `Embedding provider ${providerType} failed: ${attempt.error}. Trying next provider...`
        );
      }
    }

    throw new Error("No embedding providers available");
  }

  /**
   * Summarize with fallback chain
   * @param request - Summarization request
   * @returns Summarization response with provider info
   */
  async summarize(request: SummarizationRequest): Promise<SummarizationResponse> {
    const startTime = Date.now();

    for (const provider of this.summarizationProviders) {
      const providerType = provider.getProvider();
      const attempt: FallbackAttempt = {
        provider: providerType,
        success: false,
        duration: 0,
      };

      try {
        // Check if provider is available
        const available = await provider.isAvailable();
        if (!available) {
          attempt.error = "Provider not available";
          attempt.trigger = "container_down" as FallbackTrigger;
          this.recordAttempt(attempt);
          continue; // Try next provider
        }

        // Try to summarize
        const summary = await provider.summarizeWithCitations(
          request.query,
          request.nodes,
          request.scores
        );

        // Success!
        attempt.success = true;
        attempt.duration = Date.now() - startTime;
        this.recordAttempt(attempt);

        return {
          summary,
          model: request.model || "llama3.2",
          provider: providerType,
          duration: attempt.duration,
        };
      } catch (error) {
        const triggerType = this.detectTriggerType(error);
        attempt.error = error instanceof Error ? error.message : String(error);
        attempt.trigger = triggerType;
        attempt.duration = Date.now() - startTime;
        this.recordAttempt(attempt);

        // If no more providers, throw
        if (
          provider ===
          this.summarizationProviders[this.summarizationProviders.length - 1]
        ) {
          throw new Error(
            `All summarization providers failed. Last error: ${attempt.error}`
          );
        }

        // Otherwise, continue to next provider
        console.warn(
          `Summarization provider ${providerType} failed: ${attempt.error}. Trying next provider...`
        );
      }
    }

    throw new Error("No summarization providers available");
  }

  /**
   * Detect trigger type from error
   * @param error - Error object
   * @returns Fallback trigger type
   */
  private detectTriggerType(error: unknown): FallbackTrigger {
    const errorMessage = error instanceof Error ? error.message : String(error);

    // Timeout detection
    if (
      errorMessage.includes("timeout") ||
      errorMessage.includes("ETIMEDOUT") ||
      errorMessage.includes("ESOCKETTIMEDOUT")
    ) {
      return "timeout" as FallbackTrigger;
    }

    // Container down / connection refused
    if (
      errorMessage.includes("ECONNREFUSED") ||
      errorMessage.includes("ENOTFOUND") ||
      errorMessage.includes("connect") ||
      errorMessage.includes("Network error")
    ) {
      return "container_down" as FallbackTrigger;
    }

    // Model not found
    if (
      errorMessage.includes("model") &&
      (errorMessage.includes("not found") ||
        errorMessage.includes("does not exist") ||
        errorMessage.includes("unknown"))
    ) {
      return "model_not_found" as FallbackTrigger;
    }

    // Default: retry exceeded
    return "retry_exceeded" as FallbackTrigger;
  }

  /**
   * Record fallback attempt for metrics
   * @param attempt - Attempt details
   */
  private recordAttempt(attempt: FallbackAttempt): void {
    this.attemptHistory.push({
      ...attempt,
      timestamp: new Date(),
    } as any);

    // Keep only last 100 attempts
    if (this.attemptHistory.length > 100) {
      this.attemptHistory.shift();
    }
  }

  /**
   * Get attempt history
   * @param provider - Optional provider filter
   * @returns Recent attempts
   */
  getAttemptHistory(provider?: FallbackProvider): FallbackAttempt[] {
    if (!provider) {
      return [...this.attemptHistory];
    }

    return this.attemptHistory.filter((attempt) => attempt.provider === provider);
  }

  /**
   * Get provider health status
   * @returns Health status for all providers
   */
  async getHealthStatus(): Promise<
    Record<FallbackProvider | string, { available: boolean; latency?: number }>
  > {
    const status: Record<string, { available: boolean; latency?: number }> = {};

    for (const provider of this.embeddingProviders) {
      const providerType = provider.getProvider();
      const start = Date.now();
      const available = await provider.isAvailable();
      status[providerType] = {
        available,
        latency: available ? Date.now() - start : undefined,
      };
    }

    return status;
  }

  /**
   * Get fallback statistics
   * @returns Fallback metrics
   */
  getStats(): {
    totalAttempts: number;
    successRate: number;
    fallbackRate: number;
    byProvider: Record<FallbackProvider | string, { attempts: number; successes: number }>;
  } {
    const totalAttempts = this.attemptHistory.length;
    const successes = this.attemptHistory.filter((a) => a.success).length;
    const successRate = totalAttempts > 0 ? successes / totalAttempts : 0;

    // Calculate fallback rate (attempts that weren't the first provider)
    const fallbacks = this.attemptHistory.filter(
      (_, i) => i > 0 && this.attemptHistory[i - 1].success === false
    ).length;
    const fallbackRate = totalAttempts > 0 ? fallbacks / totalAttempts : 0;

    // Group by provider
    const byProvider: Record<string, { attempts: number; successes: number }> = {};
    for (const attempt of this.attemptHistory) {
      if (!byProvider[attempt.provider]) {
        byProvider[attempt.provider] = { attempts: 0, successes: 0 };
      }
      byProvider[attempt.provider].attempts++;
      if (attempt.success) {
        byProvider[attempt.provider].successes++;
      }
    }

    return {
      totalAttempts,
      successRate,
      fallbackRate,
      byProvider,
    };
  }

  /**
   * Clear attempt history
   */
  clearHistory(): void {
    this.attemptHistory = [];
  }
}
