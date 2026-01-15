#!/usr/bin/env npx tsx
/**
 * Provider Test Script
 *
 * Tests each synthesis and embedding provider independently to verify
 * they are working correctly.
 *
 * Usage:
 *   source ../.env.local && npx tsx src/scripts/test-providers.ts
 *   # or
 *   set -a; source ../.env.local; set +a; npx tsx src/scripts/test-providers.ts
 *
 * Environment: Uses environment variables from shell
 */

import {
  createSynthesisProviderChain,
  createEmbeddingProviderChain,
  type SynthesisProviderConfig,
  type EmbeddingProviderConfig,
} from "../config/providers.js";

// ============================================================================
// Test Functions
// ============================================================================

/**
 * Test a synthesis provider
 */
async function testSynthesisProvider(config: SynthesisProviderConfig): Promise<{
  success: boolean;
  latency: number;
  error?: string;
  response?: string;
}> {
  const startTime = Date.now();

  try {
    let url: string;
    let headers: Record<string, string>;
    let body: string;

    if (config.type === "ollama") {
      url = `${config.baseUrl}/api/chat`;
      headers = { "Content-Type": "application/json" };
      body = JSON.stringify({
        model: config.model,
        messages: [{ role: "user", content: "Say 'Hello from ESS test'" }],
        stream: false,
        options: { num_predict: 20 },
      });
    } else if (config.type === "openai") {
      url = `${config.baseUrl}/chat/completions`;
      headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.apiKey}`,
        ...(config.extraHeaders ?? {}),
      };
      body = JSON.stringify({
        model: config.model,
        messages: [{ role: "user", content: "Say 'Hello from ESS test'" }],
        max_tokens: 20,
      });
    } else if (config.type === "anthropic") {
      url = `${config.baseUrl}/messages`;
      headers = {
        "Content-Type": "application/json",
        "x-api-key": config.apiKey!,
        "anthropic-version": "2023-06-01",
      };
      body = JSON.stringify({
        model: config.model,
        messages: [{ role: "user", content: "Say 'Hello from ESS test'" }],
        max_tokens: 20,
      });
    } else {
      throw new Error(`Unknown provider type: ${config.type}`);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout ?? 30000);

    const response = await fetch(url, {
      method: "POST",
      headers,
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const latency = Date.now() - startTime;

    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        latency,
        error: `HTTP ${response.status}: ${errorText.slice(0, 200)}`,
      };
    }

    const data = await response.json() as {
      message?: { content?: string };
      choices?: Array<{ message?: { content?: string } }>;
      content?: Array<{ text?: string }>;
    };

    // Extract response text based on provider type
    let responseText: string | undefined;
    if (config.type === "ollama") {
      responseText = data.message?.content;
    } else if (config.type === "openai") {
      responseText = data.choices?.[0]?.message?.content;
    } else if (config.type === "anthropic") {
      responseText = data.content?.[0]?.text;
    }

    return {
      success: true,
      latency,
      response: responseText?.slice(0, 100),
    };
  } catch (error) {
    return {
      success: false,
      latency: Date.now() - startTime,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * Test an embedding provider
 */
async function testEmbeddingProvider(config: EmbeddingProviderConfig): Promise<{
  success: boolean;
  latency: number;
  dimensions?: number;
  error?: string;
}> {
  const startTime = Date.now();
  const testText = "This is a test embedding for ESS provider verification";

  try {
    let url: string;
    let headers: Record<string, string>;
    let body: string;

    if (config.type === "ollama") {
      url = `${config.baseUrl}/api/embeddings`;
      headers = { "Content-Type": "application/json" };
      body = JSON.stringify({
        model: config.model,
        prompt: testText,
      });
    } else {
      // OpenAI and OpenRouter use the same format
      url = `${config.baseUrl}/embeddings`;
      headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.apiKey}`,
        ...(config.extraHeaders ?? {}),
      };
      body = JSON.stringify({
        model: config.model,
        input: testText,
        dimensions: config.dimensions,
      });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout ?? 30000);

    const response = await fetch(url, {
      method: "POST",
      headers,
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const latency = Date.now() - startTime;

    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        latency,
        error: `HTTP ${response.status}: ${errorText.slice(0, 200)}`,
      };
    }

    const data = await response.json() as {
      embedding?: number[];
      data?: Array<{ embedding?: number[] }>;
    };

    // Extract embedding based on provider type
    const embedding = config.type === "ollama" ? data.embedding : data.data?.[0]?.embedding;

    if (!embedding || embedding.length === 0) {
      return {
        success: false,
        latency,
        error: "Empty embedding returned",
      };
    }

    return {
      success: true,
      latency,
      dimensions: embedding.length,
    };
  } catch (error) {
    return {
      success: false,
      latency: Date.now() - startTime,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

// ============================================================================
// Main Test Runner
// ============================================================================

async function main(): Promise<void> {
  console.log("\n╔═══════════════════════════════════════════════════════════════╗");
  console.log("║              ESS Provider Chain Test Suite                    ║");
  console.log("╚═══════════════════════════════════════════════════════════════╝\n");

  const synthesisProviders = createSynthesisProviderChain();
  const embeddingProviders = createEmbeddingProviderChain();

  console.log(`Found ${synthesisProviders.length} synthesis providers`);
  console.log(`Found ${embeddingProviders.length} embedding providers\n`);

  // Test Synthesis Providers
  console.log("═══════════════════════════════════════════════════════════════");
  console.log("Testing SYNTHESIS Providers");
  console.log("═══════════════════════════════════════════════════════════════\n");

  let synthesisResults: Array<{
    name: string;
    model: string;
    success: boolean;
    latency: number;
    error?: string;
  }> = [];

  for (const provider of synthesisProviders) {
    process.stdout.write(`  [${provider.name}] Testing ${provider.model}... `);
    const result = await testSynthesisProvider(provider);

    if (result.success) {
      console.log(`✅ OK (${result.latency}ms)`);
      if (result.response) {
        console.log(`     Response: "${result.response}..."`);
      }
    } else {
      console.log(`❌ FAILED`);
      console.log(`     Error: ${result.error}`);
    }

    synthesisResults.push({
      name: provider.name,
      model: provider.model,
      success: result.success,
      latency: result.latency,
      error: result.error,
    });

    console.log("");
  }

  // Test Embedding Providers
  console.log("═══════════════════════════════════════════════════════════════");
  console.log("Testing EMBEDDING Providers");
  console.log("═══════════════════════════════════════════════════════════════\n");

  let embeddingResults: Array<{
    name: string;
    model: string;
    success: boolean;
    latency: number;
    dimensions?: number;
    error?: string;
  }> = [];

  for (const provider of embeddingProviders) {
    process.stdout.write(`  [${provider.name}] Testing ${provider.model}... `);
    const result = await testEmbeddingProvider(provider);

    if (result.success) {
      console.log(`✅ OK (${result.latency}ms, ${result.dimensions}d)`);
    } else {
      console.log(`❌ FAILED`);
      console.log(`     Error: ${result.error}`);
    }

    embeddingResults.push({
      name: provider.name,
      model: provider.model,
      success: result.success,
      latency: result.latency,
      dimensions: result.dimensions,
      error: result.error,
    });

    console.log("");
  }

  // Summary
  console.log("═══════════════════════════════════════════════════════════════");
  console.log("SUMMARY");
  console.log("═══════════════════════════════════════════════════════════════\n");

  const synthesisOk = synthesisResults.filter((r) => r.success).length;
  const embeddingOk = embeddingResults.filter((r) => r.success).length;

  console.log(`Synthesis: ${synthesisOk}/${synthesisResults.length} providers working`);
  console.log(`Embedding: ${embeddingOk}/${embeddingResults.length} providers working`);

  if (synthesisOk === 0) {
    console.log("\n⚠️  WARNING: No synthesis providers available!");
  }
  if (embeddingOk === 0) {
    console.log("\n⚠️  WARNING: No embedding providers available!");
  }

  // Fallback chain visualization
  console.log("\n📋 Fallback Chain Order:\n");

  console.log("  Synthesis:");
  for (let i = 0; i < synthesisResults.length; i++) {
    const r = synthesisResults[i];
    if (r) {
      const status = r.success ? "✅" : "❌";
      const priority = i === 0 ? "PRIMARY" : `FALLBACK ${i}`;
      console.log(`    ${status} [${priority}] ${r.name}`);
    }
  }

  console.log("\n  Embedding:");
  for (let i = 0; i < embeddingResults.length; i++) {
    const r = embeddingResults[i];
    if (r) {
      const status = r.success ? "✅" : "❌";
      const priority = i === 0 ? "PRIMARY" : `FALLBACK ${i}`;
      console.log(`    ${status} [${priority}] ${r.name} (${r.dimensions ?? "?"}d)`);
    }
  }

  console.log("\n═══════════════════════════════════════════════════════════════\n");

  // Exit with error if no providers work
  if (synthesisOk === 0 || embeddingOk === 0) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
