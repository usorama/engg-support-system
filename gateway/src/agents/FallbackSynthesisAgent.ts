/**
 * FallbackSynthesisAgent - Multi-Provider Synthesis with Automatic Fallback
 *
 * Wraps multiple synthesis providers and automatically falls back through
 * the chain when a provider fails. This ensures high availability of
 * LLM synthesis capabilities.
 *
 * @module FallbackSynthesisAgent
 */

import {
  SynthesisAgent,
  type SynthesisAgentConfig,
  type SynthesisResult,
  type SynthesisOptions,
  type LLMProvider,
} from "./SynthesisAgent.js";
import type { SynthesisProviderConfig } from "../config/providers.js";
import type { SemanticResult, StructuralResult } from "../types/agent-contracts.js";
import { getSynthesisTimeout } from "../config/timeouts.js";

// ============================================================================
// Types
// ============================================================================

/**
 * Result from synthesis attempt including provider info
 */
export interface FallbackSynthesisResult extends SynthesisResult {
  /** Provider that successfully generated the result */
  providerId: string;
  /** Provider display name */
  providerName: string;
  /** Number of providers tried before success */
  attemptCount: number;
  /** Providers that failed (in order) */
  failedProviders: Array<{ id: string; name: string; error: string }>;
}

/**
 * Provider health status
 */
export interface ProviderHealthStatus {
  id: string;
  name: string;
  available: boolean;
  lastChecked: Date;
  lastError?: string;
  consecutiveFailures: number;
}

// ============================================================================
// FallbackSynthesisAgent Class
// ============================================================================

/**
 * Multi-provider synthesis agent with automatic fallback
 */
export class FallbackSynthesisAgent {
  private readonly providers: Array<{
    config: SynthesisProviderConfig;
    agent: SynthesisAgent;
  }>;
  private readonly healthStatus: Map<string, ProviderHealthStatus> = new Map();
  private readonly maxConsecutiveFailures = 3;
  private readonly healthCheckIntervalMs = 60000; // 1 minute

  constructor(providerConfigs: SynthesisProviderConfig[]) {
    if (providerConfigs.length === 0) {
      throw new Error("At least one synthesis provider must be configured");
    }

    this.providers = providerConfigs.map((config) => ({
      config,
      agent: this.createAgentFromConfig(config),
    }));

    // Initialize health status for all providers
    for (const { config } of this.providers) {
      this.healthStatus.set(config.id, {
        id: config.id,
        name: config.name,
        available: true, // Assume available until proven otherwise
        lastChecked: new Date(0), // Never checked
        consecutiveFailures: 0,
      });
    }

    console.log(
      `[FallbackSynthesisAgent] Initialized with ${this.providers.length} providers: ` +
        this.providers.map((p) => p.config.name).join(" → ")
    );
  }

  /**
   * Create a SynthesisAgent from provider config
   */
  private createAgentFromConfig(config: SynthesisProviderConfig): SynthesisAgent {
    // Map config type to LLMProvider
    const providerType: LLMProvider = config.type;

    const agentConfig: SynthesisAgentConfig = {
      provider: providerType,
      baseUrl: config.baseUrl,
      model: config.model,
      timeout: config.timeout ?? getSynthesisTimeout(),
    };
    // Only add apiKey if defined
    if (config.apiKey) {
      agentConfig.apiKey = config.apiKey;
    }
    return new SynthesisAgent(agentConfig);
  }

  /**
   * Synthesize with automatic fallback through provider chain
   */
  async synthesize(
    query: string,
    semanticResult: SemanticResult,
    structuralResult: StructuralResult,
    options?: SynthesisOptions
  ): Promise<FallbackSynthesisResult> {
    const failedProviders: Array<{ id: string; name: string; error: string }> = [];
    let attemptCount = 0;

    for (const { config, agent } of this.providers) {
      attemptCount++;

      // Skip providers that have failed too many times (circuit breaker)
      const health = this.healthStatus.get(config.id);
      if (health && health.consecutiveFailures >= this.maxConsecutiveFailures) {
        // Check if enough time has passed to retry
        const timeSinceLastCheck = Date.now() - health.lastChecked.getTime();
        if (timeSinceLastCheck < this.healthCheckIntervalMs) {
          console.log(
            `[FallbackSynthesisAgent] Skipping ${config.name} (circuit breaker open)`
          );
          failedProviders.push({
            id: config.id,
            name: config.name,
            error: "Circuit breaker open - too many consecutive failures",
          });
          continue;
        }
        // Reset for retry
        console.log(
          `[FallbackSynthesisAgent] Retrying ${config.name} (circuit breaker timeout expired)`
        );
      }

      try {
        console.log(`[FallbackSynthesisAgent] Trying ${config.name}...`);
        const result = await agent.synthesize(
          query,
          semanticResult,
          structuralResult,
          options
        );

        // Success - reset failure count
        this.updateHealthStatus(config.id, true);

        console.log(`[FallbackSynthesisAgent] Success with ${config.name}`);
        return {
          ...result,
          providerId: config.id,
          providerName: config.name,
          attemptCount,
          failedProviders,
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error(
          `[FallbackSynthesisAgent] ${config.name} failed: ${errorMessage}`
        );

        // Record failure
        this.updateHealthStatus(config.id, false, errorMessage);
        failedProviders.push({
          id: config.id,
          name: config.name,
          error: errorMessage,
        });

        // Continue to next provider
      }
    }

    // All providers failed
    throw new Error(
      `All synthesis providers failed. Tried: ${failedProviders.map((p) => p.name).join(", ")}. ` +
        `Last error: ${failedProviders[failedProviders.length - 1]?.error ?? "Unknown"}`
    );
  }

  /**
   * Check if at least one provider is available
   */
  async isAvailable(): Promise<boolean> {
    for (const { config, agent } of this.providers) {
      try {
        const available = await agent.isAvailable();
        if (available) {
          return true;
        }
      } catch {
        // Continue to next provider
      }
    }
    return false;
  }

  /**
   * Get health status of all providers
   */
  getHealthStatus(): ProviderHealthStatus[] {
    return Array.from(this.healthStatus.values());
  }

  /**
   * Update health status for a provider
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
   * Force health check on all providers
   */
  async refreshHealthStatus(): Promise<ProviderHealthStatus[]> {
    const results = await Promise.allSettled(
      this.providers.map(async ({ config, agent }) => {
        const available = await agent.isAvailable();
        this.updateHealthStatus(config.id, available);
        return { id: config.id, available };
      })
    );

    console.log(
      "[FallbackSynthesisAgent] Health check complete:",
      results.map((r) =>
        r.status === "fulfilled"
          ? `${r.value.id}: ${r.value.available ? "OK" : "DOWN"}`
          : "ERROR"
      ).join(", ")
    );

    return this.getHealthStatus();
  }

  /**
   * Get list of configured providers
   */
  getProviders(): Array<{ id: string; name: string; model: string; isFree?: boolean }> {
    return this.providers.map(({ config }) => {
      const provider: { id: string; name: string; model: string; isFree?: boolean } = {
        id: config.id,
        name: config.name,
        model: config.model,
      };
      if (config.isFree !== undefined) {
        provider.isFree = config.isFree;
      }
      return provider;
    });
  }
}

/**
 * Create a FallbackSynthesisAgent from provider configs
 */
export function createFallbackSynthesisAgent(
  configs: SynthesisProviderConfig[]
): FallbackSynthesisAgent {
  return new FallbackSynthesisAgent(configs);
}
