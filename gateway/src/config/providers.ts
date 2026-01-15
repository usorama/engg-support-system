/**
 * Centralized Provider Configuration
 *
 * Defines synthesis (LLM) and embedding providers with fallback chains.
 * All provider configurations are centralized here for easy management.
 *
 * @module providers
 */

// ============================================================================
// Types
// ============================================================================

/**
 * Synthesis provider configuration
 */
export interface SynthesisProviderConfig {
  /** Provider identifier */
  id: string;
  /** Human-readable name */
  name: string;
  /** Provider type: openai (OpenRouter, zAI OpenAI endpoint), anthropic (Claude, zAI Anthropic endpoint), or ollama */
  type: "openai" | "anthropic" | "ollama";
  /** API base URL */
  baseUrl: string;
  /** Model identifier */
  model: string;
  /** API key (required for openai/anthropic) */
  apiKey?: string;
  /** Request timeout in ms */
  timeout?: number;
  /** Cost per million input tokens (for monitoring) */
  costPerMInput?: number;
  /** Cost per million output tokens (for monitoring) */
  costPerMOutput?: number;
  /** Whether this provider is free */
  isFree?: boolean;
  /** Context window size */
  contextWindow?: number;
  /** Optional HTTP headers (e.g., for OpenRouter site info) */
  extraHeaders?: Record<string, string>;
}

/**
 * Embedding provider configuration
 */
export interface EmbeddingProviderConfig {
  /** Provider identifier */
  id: string;
  /** Human-readable name */
  name: string;
  /** Provider type */
  type: "ollama" | "openai" | "openrouter";
  /** API base URL */
  baseUrl: string;
  /** Model identifier */
  model: string;
  /** API key (required for openai/openrouter) */
  apiKey?: string;
  /** Expected embedding dimensions (must match Qdrant collection) */
  dimensions: number;
  /** Request timeout in ms */
  timeout?: number;
  /** Cost per million input tokens */
  costPerMInput?: number;
  /** Whether this provider is free */
  isFree?: boolean;
  /** Optional HTTP headers */
  extraHeaders?: Record<string, string>;
}

/**
 * Complete provider chain configuration
 */
export interface ProviderChainConfig {
  /** Synthesis providers in fallback order */
  synthesis: SynthesisProviderConfig[];
  /** Embedding providers in fallback order */
  embedding: EmbeddingProviderConfig[];
}

// ============================================================================
// Default Provider Configurations
// ============================================================================

/**
 * OpenRouter base URL for all OpenRouter models
 */
export const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";

/**
 * OpenRouter HTTP headers (recommended by OpenRouter for analytics)
 */
export function getOpenRouterHeaders(appName = "ESS-Gateway"): Record<string, string> {
  return {
    "HTTP-Referer": "https://ess.ping-gadgets.com",
    "X-Title": appName,
  };
}

/**
 * Create synthesis provider configuration from environment
 * Returns an array of providers in fallback order
 */
export function createSynthesisProviderChain(): SynthesisProviderConfig[] {
  const providers: SynthesisProviderConfig[] = [];
  const openRouterKey = process.env.OPENROUTER_API_KEY;
  const zaiKey = process.env.SYNTHESIS_API_KEY;
  const ollamaUrl = process.env.OLLAMA_URL;

  // 1. Primary: OpenRouter MiMo-V2-Flash (FREE)
  if (openRouterKey) {
    providers.push({
      id: "openrouter-mimo",
      name: "OpenRouter MiMo-V2-Flash",
      type: "openai",
      baseUrl: OPENROUTER_BASE_URL,
      model: "xiaomi/mimo-v2-flash:free",
      apiKey: openRouterKey,
      timeout: 60000,
      costPerMInput: 0,
      costPerMOutput: 0,
      isFree: true,
      contextWindow: 262144,
      extraHeaders: getOpenRouterHeaders(),
    });
  }

  // 2. Fallback 1: OpenRouter Gemini 3 Flash Preview
  if (openRouterKey) {
    providers.push({
      id: "openrouter-gemini3",
      name: "OpenRouter Gemini 3 Flash Preview",
      type: "openai",
      baseUrl: OPENROUTER_BASE_URL,
      model: "google/gemini-3-flash-preview",
      apiKey: openRouterKey,
      timeout: 60000,
      costPerMInput: 0.50,
      costPerMOutput: 3.00,
      isFree: false,
      contextWindow: 1048576,
      extraHeaders: getOpenRouterHeaders(),
    });
  }

  // 3. Fallback 2: OpenRouter DeepSeek R1 (FREE)
  if (openRouterKey) {
    providers.push({
      id: "openrouter-deepseek",
      name: "OpenRouter DeepSeek R1",
      type: "openai",
      baseUrl: OPENROUTER_BASE_URL,
      model: "deepseek/deepseek-r1-0528:free",
      apiKey: openRouterKey,
      timeout: 90000, // Longer timeout for reasoning model
      costPerMInput: 0,
      costPerMOutput: 0,
      isFree: true,
      contextWindow: 163840,
      extraHeaders: getOpenRouterHeaders(),
    });
  }

  // 4. Fallback 3: zAI via Anthropic-compatible API
  if (zaiKey) {
    const zaiUrl = process.env.SYNTHESIS_API_URL ?? "https://api.z.ai/api/anthropic/v1";
    const zaiModel = process.env.SYNTHESIS_MODEL ?? "claude-sonnet-4.5";
    providers.push({
      id: "zai",
      name: "zAI",
      type: "anthropic",
      baseUrl: zaiUrl,
      model: zaiModel,
      apiKey: zaiKey,
      timeout: 60000,
      costPerMInput: 0.40,
      costPerMOutput: 1.50,
      isFree: false,
      contextWindow: 200000,
    });
  }

  // 5. Final Fallback: Local Ollama
  if (ollamaUrl) {
    const ollamaModel = process.env.SYNTHESIS_OLLAMA_MODEL ?? "llama3.2";
    providers.push({
      id: "ollama",
      name: "Local Ollama",
      type: "ollama",
      baseUrl: ollamaUrl,
      model: ollamaModel,
      timeout: 120000,
      costPerMInput: 0,
      costPerMOutput: 0,
      isFree: true,
      contextWindow: 128000,
    });
  }

  return providers;
}

/**
 * Create embedding provider configuration from environment
 * Returns an array of providers in fallback order
 */
export function createEmbeddingProviderChain(): EmbeddingProviderConfig[] {
  const providers: EmbeddingProviderConfig[] = [];
  const ollamaUrl = process.env.OLLAMA_URL;
  const openaiKey = process.env.EMBEDDING_FALLBACK_API_KEY ?? process.env.OPENAI_API_KEY;
  const openRouterKey = process.env.OPENROUTER_API_KEY;

  // Target dimensions should match Qdrant collection (768 for nomic-embed-text)
  const targetDimensions = parseInt(process.env.EMBEDDING_DIMENSIONS ?? "768", 10);

  // 1. Primary: Local Ollama
  if (ollamaUrl) {
    const embedModel = process.env.EMBEDDING_MODEL ?? "nomic-embed-text";
    providers.push({
      id: "ollama",
      name: "Local Ollama",
      type: "ollama",
      baseUrl: ollamaUrl,
      model: embedModel,
      dimensions: 768,
      timeout: 30000,
      costPerMInput: 0,
      isFree: true,
    });
  }

  // 2. Fallback 1: OpenAI
  if (openaiKey) {
    const openaiModel = process.env.EMBEDDING_FALLBACK_MODEL ?? "text-embedding-3-small";
    providers.push({
      id: "openai",
      name: "OpenAI Embeddings",
      type: "openai",
      baseUrl: "https://api.openai.com/v1",
      model: openaiModel,
      apiKey: openaiKey,
      dimensions: targetDimensions,
      timeout: 30000,
      costPerMInput: 0.02,
      isFree: false,
    });
  }

  // 3. Fallback 2: OpenRouter Qwen3 Embedding
  if (openRouterKey) {
    providers.push({
      id: "openrouter-qwen3",
      name: "OpenRouter Qwen3 Embedding",
      type: "openrouter",
      baseUrl: OPENROUTER_BASE_URL,
      model: "qwen/qwen3-embedding-8b",
      apiKey: openRouterKey,
      dimensions: 768, // Qwen3 supports configurable dimensions
      timeout: 30000,
      costPerMInput: 0.01,
      isFree: false,
      extraHeaders: getOpenRouterHeaders(),
    });
  }

  return providers;
}

/**
 * Get full provider chain configuration
 */
export function getProviderChainConfig(): ProviderChainConfig {
  return {
    synthesis: createSynthesisProviderChain(),
    embedding: createEmbeddingProviderChain(),
  };
}

/**
 * Log provider chain summary (for startup)
 */
export function logProviderChainSummary(config: ProviderChainConfig): void {
  console.log("\n=== Provider Chain Configuration ===\n");

  console.log("Synthesis Providers (in fallback order):");
  for (let i = 0; i < config.synthesis.length; i++) {
    const p = config.synthesis[i];
    if (p) {
      const costInfo = p.isFree ? "FREE" : `$${p.costPerMInput}/M in, $${p.costPerMOutput}/M out`;
      const priority = i === 0 ? "[PRIMARY]" : `[FALLBACK ${i}]`;
      console.log(`  ${priority} ${p.name} (${p.model}) - ${costInfo}`);
    }
  }

  console.log("\nEmbedding Providers (in fallback order):");
  for (let i = 0; i < config.embedding.length; i++) {
    const p = config.embedding[i];
    if (p) {
      const costInfo = p.isFree ? "FREE" : `$${p.costPerMInput}/M tokens`;
      const priority = i === 0 ? "[PRIMARY]" : `[FALLBACK ${i}]`;
      console.log(`  ${priority} ${p.name} (${p.model}) - ${costInfo} - ${p.dimensions}d`);
    }
  }

  console.log("\n====================================\n");
}
