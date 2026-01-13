/**
 * SynthesisAgent - Intelligent Answer Synthesis
 *
 * Bridges the gap between raw Qdrant/Neo4j results and intelligent answers.
 * Supports multiple LLM providers:
 * - Ollama (local)
 * - Anthropic-compatible APIs (zAI, OpenRouter, etc.)
 *
 * @module SynthesisAgent
 */

import type {
  SemanticResult,
  SemanticMatch,
  StructuralResult,
  StructuralRelationship,
  CombinedInsights,
} from "../types/agent-contracts.js";

// ============================================================================
// Types
// ============================================================================

/**
 * Citation extracted from synthesis
 */
export interface SynthesisCitation {
  /** Source file path */
  source: string;
  /** Line start (if available) */
  lineStart?: number;
  /** Line end (if available) */
  lineEnd?: number;
  /** Relevance score (0-1) */
  relevance: number;
  /** Source type */
  type: "code" | "doc" | "graph";
}

/**
 * Synthesized answer
 */
export interface SynthesizedAnswer {
  /** The synthesized answer text */
  text: string;
  /** Confidence score (0-1) */
  confidence: number;
  /** Evidence citations */
  citations: SynthesisCitation[];
}

/**
 * Complete synthesis result
 */
export interface SynthesisResult {
  /** Synthesized answer */
  answer: SynthesizedAnswer;
  /** Combined insights (populates CombinedInsights interface) */
  insights: CombinedInsights;
}

/**
 * Synthesis options
 */
export interface SynthesisOptions {
  /** Temperature for LLM (default: 0.3 for determinism) */
  temperature?: number;
  /** Maximum tokens to generate */
  maxTokens?: number;
  /** Seed for reproducibility */
  seed?: number;
}

/**
 * LLM Provider type
 * - ollama: Local Ollama instance
 * - anthropic: Anthropic-compatible API (Claude, etc.)
 * - openai: OpenAI-compatible API (zAI, OpenRouter, etc.)
 */
export type LLMProvider = "ollama" | "anthropic" | "openai";

/**
 * SynthesisAgent configuration
 */
export interface SynthesisAgentConfig {
  /** LLM provider type (default: ollama) */
  provider?: LLMProvider;
  /** API base URL (Ollama URL, Anthropic URL, or OpenAI-compatible URL) */
  baseUrl: string;
  /** Model name (default: llama3.2 for Ollama, glm-4.7 for Anthropic/OpenAI) */
  model?: string;
  /** API key (required for Anthropic and OpenAI providers) */
  apiKey?: string;
  /** Request timeout in ms (default: 30000) */
  timeout?: number;
}

/**
 * Legacy config for backwards compatibility
 * @deprecated Use SynthesisAgentConfig instead
 */
export interface LegacySynthesisAgentConfig {
  ollamaUrl: string;
  model?: string;
  timeout?: number;
}

// ============================================================================
// SynthesisAgent Class
// ============================================================================

/**
 * SynthesisAgent - Synthesizes intelligent answers from raw search results
 */
export class SynthesisAgent {
  private readonly provider: LLMProvider;
  private readonly baseUrl: string;
  private readonly model: string;
  private readonly apiKey?: string;
  private readonly timeout: number;

  constructor(config: SynthesisAgentConfig | LegacySynthesisAgentConfig) {
    // Handle legacy config format
    if ("ollamaUrl" in config) {
      this.provider = "ollama";
      this.baseUrl = config.ollamaUrl.replace(/\/$/, "");
      this.model = config.model ?? "llama3.2";
      this.timeout = config.timeout ?? 30000;
      // apiKey not set for legacy Ollama config
    } else {
      this.provider = config.provider ?? "ollama";
      this.baseUrl = config.baseUrl.replace(/\/$/, "");
      // Set default model based on provider
      if (config.model) {
        this.model = config.model;
      } else if (this.provider === "anthropic" || this.provider === "openai") {
        this.model = "glm-4.7";
      } else {
        this.model = "llama3.2";
      }
      this.timeout = config.timeout ?? 30000;
      // Only set apiKey if defined
      if (config.apiKey !== undefined) {
        this.apiKey = config.apiKey;
      }
    }
  }

  /**
   * Synthesize an intelligent answer from Qdrant + Neo4j results
   *
   * @param query - Original user query
   * @param semanticResult - Results from Qdrant vector search
   * @param structuralResult - Results from Neo4j graph search
   * @param options - Synthesis options
   * @returns Synthesis result with answer and insights
   */
  async synthesize(
    query: string,
    semanticResult: SemanticResult,
    structuralResult: StructuralResult,
    options?: SynthesisOptions
  ): Promise<SynthesisResult> {
    // Build context from both sources
    const context = this.buildContext(semanticResult, structuralResult);

    // Generate answer using Ollama
    const answerText = await this.generateAnswer(query, context, options);

    // Extract citations from the generated answer
    const citations = this.extractCitations(
      answerText,
      semanticResult,
      structuralResult
    );

    // Calculate confidence score
    const confidence = this.calculateConfidence(
      semanticResult,
      structuralResult,
      citations
    );

    // Build insights for CombinedInsights interface
    const insights = this.buildInsights(
      answerText,
      semanticResult,
      structuralResult
    );

    return {
      answer: {
        text: answerText,
        confidence,
        citations,
      },
      insights,
    };
  }

  /**
   * Check if the LLM provider is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      if (this.provider === "openai") {
        // For OpenAI-compatible APIs (zAI, etc.), check if we have an API key
        if (!this.apiKey) {
          return false;
        }
        // Simple health check - try a minimal request
        const response = await fetch(`${this.baseUrl}/chat/completions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${this.apiKey}`,
          },
          body: JSON.stringify({
            model: this.model,
            max_tokens: 1,
            messages: [{ role: "user", content: "test" }],
          }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        // 200 or 400 (invalid request) both indicate service is available
        return response.ok || response.status === 400;
      } else if (this.provider === "anthropic") {
        // For Anthropic-compatible APIs, check if we have an API key
        if (!this.apiKey) {
          return false;
        }
        // Simple health check - try a minimal request
        const response = await fetch(`${this.baseUrl}/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-api-key": this.apiKey,
            "anthropic-version": "2023-06-01",
          },
          body: JSON.stringify({
            model: this.model,
            max_tokens: 1,
            messages: [{ role: "user", content: "test" }],
          }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        // 200 or 400 (invalid request) both indicate service is available
        return response.ok || response.status === 400;
      } else {
        // Ollama health check
        const response = await fetch(`${this.baseUrl}/api/tags`, {
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          return false;
        }

        const data = (await response.json()) as { models?: Array<{ name: string }> };
        const models = data.models ?? [];

        // Check if our model is available
        return models.some(
          (m) => m.name === this.model || m.name.startsWith(`${this.model}:`)
        );
      }
    } catch {
      return false;
    }
  }

  // ==========================================================================
  // Private Methods
  // ==========================================================================

  /**
   * Build context string from both result sources
   */
  private buildContext(
    semanticResult: SemanticResult,
    structuralResult: StructuralResult
  ): string {
    const parts: string[] = [];

    // Add semantic matches (vector search results)
    if (semanticResult.matches.length > 0) {
      parts.push("## Vector Search Results (Semantic Matches)\n");
      for (const match of semanticResult.matches.slice(0, 5)) {
        const location = match.lineStart
          ? `${match.source}:${match.lineStart}-${match.lineEnd}`
          : match.source;
        parts.push(`### [Source: ${location}]`);
        parts.push(`Relevance: ${(match.score * 100).toFixed(1)}%`);
        parts.push(`Type: ${match.type}`);
        if (match.language) {
          parts.push(`\`\`\`${match.language}\n${match.content}\n\`\`\``);
        } else {
          parts.push(match.content);
        }
        parts.push("");
      }
    }

    // Add structural relationships (graph search results)
    if (structuralResult.relationships.length > 0) {
      parts.push("\n## Code Graph Results (Structural Relationships)\n");
      for (const rel of structuralResult.relationships.slice(0, 5)) {
        parts.push(`### [Graph: ${rel.source} → ${rel.target}]`);
        parts.push(`Relationship: ${rel.type}`);
        parts.push(`Path: ${rel.path.join(" → ")}`);
        if (rel.explanation) {
          parts.push(`Explanation: ${rel.explanation}`);
        }
        parts.push("");
      }
    }

    return parts.join("\n");
  }

  /**
   * Generate answer using the configured LLM provider
   */
  private async generateAnswer(
    query: string,
    context: string,
    options?: SynthesisOptions
  ): Promise<string> {
    const systemPrompt = `You are a technical knowledge assistant analyzing a codebase.

INSTRUCTIONS:
1. Answer the question using ONLY the provided context
2. Include mandatory citations in format [Source: file-path:line] or [Graph: source → target]
3. If the context doesn't contain the answer, say "I don't have enough information from the indexed codebase"
4. Be concise but comprehensive
5. Prioritize code evidence over general explanations
6. For code questions, include relevant code snippets with file references

CITATION FORMAT:
- For semantic matches: [Source: path/to/file.ts:lineStart-lineEnd]
- For graph relationships: [Graph: SourceNode → TargetNode]

Do NOT make up information. Only use what's in the context.`;

    const userPrompt = `CONTEXT FROM CODEBASE SEARCH:

${context}

QUESTION: ${query}

Provide your answer with citations:`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      if (this.provider === "openai") {
        return await this.generateAnswerOpenAI(
          systemPrompt,
          userPrompt,
          options,
          controller.signal
        );
      } else if (this.provider === "anthropic") {
        return await this.generateAnswerAnthropic(
          systemPrompt,
          userPrompt,
          options,
          controller.signal
        );
      } else {
        return await this.generateAnswerOllama(
          systemPrompt,
          userPrompt,
          options,
          controller.signal
        );
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Synthesis timed out after ${this.timeout}ms`);
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Generate answer using Ollama API
   */
  private async generateAnswerOllama(
    systemPrompt: string,
    userPrompt: string,
    options: SynthesisOptions | undefined,
    signal: AbortSignal
  ): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        stream: false,
        options: {
          temperature: options?.temperature ?? 0.3,
          num_predict: options?.maxTokens ?? 2048,
          seed: options?.seed ?? 42,
        },
      }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Ollama request failed: ${response.status} ${errorText}`);
    }

    const data = (await response.json()) as {
      message?: { content?: string };
    };

    if (!data.message?.content) {
      throw new Error("Invalid response from Ollama: missing message content");
    }

    return data.message.content.trim();
  }

  /**
   * Generate answer using OpenAI-compatible API (zAI, OpenRouter, etc.)
   */
  private async generateAnswerOpenAI(
    systemPrompt: string,
    userPrompt: string,
    options: SynthesisOptions | undefined,
    signal: AbortSignal
  ): Promise<string> {
    if (!this.apiKey) {
      throw new Error("API key required for OpenAI provider");
    }

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: options?.maxTokens ?? 2048,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        temperature: options?.temperature ?? 0.3,
      }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI API request failed: ${response.status} ${errorText}`);
    }

    const data = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };

    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error("Invalid response from OpenAI API: missing message content");
    }

    return content.trim();
  }

  /**
   * Generate answer using Anthropic-compatible API (Claude, etc.)
   */
  private async generateAnswerAnthropic(
    systemPrompt: string,
    userPrompt: string,
    options: SynthesisOptions | undefined,
    signal: AbortSignal
  ): Promise<string> {
    if (!this.apiKey) {
      throw new Error("API key required for Anthropic provider");
    }

    const response = await fetch(`${this.baseUrl}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": this.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: options?.maxTokens ?? 2048,
        system: systemPrompt,
        messages: [
          { role: "user", content: userPrompt },
        ],
        temperature: options?.temperature ?? 0.3,
      }),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Anthropic API request failed: ${response.status} ${errorText}`);
    }

    const data = (await response.json()) as {
      content?: Array<{ type: string; text?: string }>;
    };

    const textContent = data.content?.find((c) => c.type === "text");
    if (!textContent?.text) {
      throw new Error("Invalid response from Anthropic API: missing text content");
    }

    return textContent.text.trim();
  }

  /**
   * Extract citations from generated answer
   */
  private extractCitations(
    answer: string,
    semanticResult: SemanticResult,
    structuralResult: StructuralResult
  ): SynthesisCitation[] {
    const citations: SynthesisCitation[] = [];
    const seenSources = new Set<string>();

    // Extract [Source: file:line] citations
    const sourceRegex = /\[Source:\s*([^\]]+)\]/g;
    let match;
    while ((match = sourceRegex.exec(answer)) !== null) {
      const capturedGroup = match[1];
      if (!capturedGroup) continue;

      const sourceRef = capturedGroup.trim();

      // Parse file:lineStart-lineEnd format
      const lineMatch = sourceRef.match(/^(.+?):(\d+)(?:-(\d+))?$/);
      const filePath = lineMatch?.[1] ?? sourceRef;
      const lineStart = lineMatch?.[2] ? parseInt(lineMatch[2], 10) : undefined;
      const lineEnd = lineMatch?.[3] ? parseInt(lineMatch[3], 10) : lineStart;

      // Find matching semantic result
      const matchingResult = semanticResult.matches.find(
        (m) => m.source.includes(filePath) || filePath.includes(m.source)
      );

      if (matchingResult && !seenSources.has(filePath)) {
        // Map "comment" type to "doc" for SynthesisCitation compatibility
        const citationType: "code" | "doc" | "graph" =
          matchingResult.type === "comment" ? "doc" : matchingResult.type;

        const citation: SynthesisCitation = {
          source: matchingResult.source,
          relevance: matchingResult.score,
          type: citationType,
        };

        // Only add line numbers if available
        const effectiveLineStart = lineStart ?? matchingResult.lineStart;
        const effectiveLineEnd = lineEnd ?? matchingResult.lineEnd;
        if (effectiveLineStart !== undefined) {
          citation.lineStart = effectiveLineStart;
        }
        if (effectiveLineEnd !== undefined) {
          citation.lineEnd = effectiveLineEnd;
        }

        citations.push(citation);
        seenSources.add(filePath);
      }
    }

    // Extract [Graph: source → target] citations
    const graphRegex = /\[Graph:\s*([^\]]+)\]/g;
    while ((match = graphRegex.exec(answer)) !== null) {
      const graphGroup = match[1];
      if (!graphGroup) continue;

      const graphRef = graphGroup.trim();
      const arrowMatch = graphRef.match(/(.+?)\s*→\s*(.+)/);

      if (arrowMatch?.[1] && arrowMatch[2]) {
        const sourceNode = arrowMatch[1].trim();
        const targetNode = arrowMatch[2].trim();

        // Find matching structural relationship
        const matchingRel = structuralResult.relationships.find(
          (r) =>
            r.source.includes(sourceNode) && r.target.includes(targetNode)
        );

        if (matchingRel && !seenSources.has(graphRef)) {
          citations.push({
            source: `${matchingRel.source} → ${matchingRel.target}`,
            relevance: 0.8, // Graph relationships get default relevance
            type: "graph",
          });
          seenSources.add(graphRef);
        }
      }
    }

    // If no citations found, create from top results
    if (citations.length === 0) {
      // Add top 3 semantic matches
      for (const semanticMatch of semanticResult.matches.slice(0, 3)) {
        // Map "comment" type to "doc" for SynthesisCitation compatibility
        const citationType: "code" | "doc" | "graph" =
          semanticMatch.type === "comment" ? "doc" : semanticMatch.type;

        const citation: SynthesisCitation = {
          source: semanticMatch.source,
          relevance: semanticMatch.score,
          type: citationType,
        };

        // Only add line numbers if available
        if (semanticMatch.lineStart !== undefined) {
          citation.lineStart = semanticMatch.lineStart;
        }
        if (semanticMatch.lineEnd !== undefined) {
          citation.lineEnd = semanticMatch.lineEnd;
        }

        citations.push(citation);
      }
    }

    return citations;
  }

  /**
   * Calculate confidence score based on multiple factors
   */
  private calculateConfidence(
    semanticResult: SemanticResult,
    structuralResult: StructuralResult,
    citations: SynthesisCitation[]
  ): number {
    // Factor 1: Average semantic match score (70% weight)
    const semanticScores = semanticResult.matches.map((m) => m.score);
    const avgSemanticScore =
      semanticScores.length > 0
        ? semanticScores.reduce((a, b) => a + b, 0) / semanticScores.length
        : 0;

    // Factor 2: Structural coverage (10% weight)
    const hasStructural = structuralResult.relationships.length > 0 ? 1 : 0;

    // Factor 3: Citation coverage (20% weight)
    const citationCoverage = Math.min(citations.length / 3, 1);

    // Combined confidence
    return avgSemanticScore * 0.7 + hasStructural * 0.1 + citationCoverage * 0.2;
  }

  /**
   * Build CombinedInsights from synthesis results
   */
  private buildInsights(
    answerText: string,
    semanticResult: SemanticResult,
    structuralResult: StructuralResult
  ): CombinedInsights {
    // Extract summary (first paragraph or first 500 chars)
    const paragraphs = answerText.split(/\n\n+/);
    const firstParagraph = paragraphs[0] ?? answerText;
    const summary =
      firstParagraph.length > 500
        ? firstParagraph.substring(0, 500) + "..."
        : firstParagraph;

    // Extract key findings (bullet points or key statements)
    const keyFindings: string[] = [];

    // Add top semantic matches as findings
    for (const match of semanticResult.matches.slice(0, 3)) {
      const location = match.lineStart
        ? `${match.source}:${match.lineStart}`
        : match.source;
      keyFindings.push(
        `Found relevant ${match.type} in \`${location}\` (${(match.score * 100).toFixed(0)}% match)`
      );
    }

    // Add structural relationships as findings
    for (const rel of structuralResult.relationships.slice(0, 2)) {
      keyFindings.push(
        `${rel.source} ${rel.type.toLowerCase().replace(/_/g, " ")} ${rel.target}`
      );
    }

    // Build recommendations based on coverage
    const recommendations: string[] = [];
    if (semanticResult.matches.length === 0) {
      recommendations.push(
        "Consider reindexing the codebase for better semantic coverage"
      );
    }
    if (structuralResult.relationships.length === 0) {
      recommendations.push(
        "No code relationships found - ensure Neo4j graph is populated"
      );
    }
    const firstMatch = semanticResult.matches[0];
    if (
      semanticResult.matches.length > 0 &&
      firstMatch &&
      firstMatch.score < 0.5
    ) {
      recommendations.push(
        "Low confidence match - try rephrasing the question with more specific terms"
      );
    }

    const result: CombinedInsights = {
      summary,
      keyFindings,
    };

    // Only add recommendations if we have any
    if (recommendations.length > 0) {
      result.recommendations = recommendations;
    }

    return result;
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a SynthesisAgent for local development with Ollama
 */
export function createLocalSynthesisAgent(
  ollamaPort = 11434
): SynthesisAgent {
  return new SynthesisAgent({
    provider: "ollama",
    baseUrl: `http://localhost:${ollamaPort}`,
  });
}

/**
 * Create a SynthesisAgent for VPS deployment
 * Priority: zAI (openai) > Anthropic > Ollama
 */
export function createVPSSynthesisAgent(): SynthesisAgent {
  const synthesisProvider = process.env.SYNTHESIS_PROVIDER as LLMProvider | undefined;
  const apiUrl = process.env.SYNTHESIS_API_URL || process.env.ANTHROPIC_BASE_URL;
  const apiKey = process.env.SYNTHESIS_API_KEY || process.env.ANTHROPIC_API_KEY;

  // If explicitly configured or we have zAI-style URL
  if (apiUrl && apiKey) {
    const provider = synthesisProvider ?? (apiUrl.includes("api.z.ai") ? "openai" : "anthropic");
    return new SynthesisAgent({
      provider,
      baseUrl: apiUrl,
      apiKey,
      model: process.env.SYNTHESIS_MODEL || process.env.ANTHROPIC_MODEL || "glm-4.7",
      timeout: 60000,
    });
  }

  // Fall back to Ollama
  return new SynthesisAgent({
    provider: "ollama",
    baseUrl: process.env.OLLAMA_URL ?? "http://localhost:11434",
    timeout: 60000,
  });
}

/**
 * Create a SynthesisAgent from environment variables
 *
 * Supports three configurations:
 * 1. OpenAI-compatible API (zAI, OpenRouter, etc.):
 *    - SYNTHESIS_PROVIDER=openai
 *    - SYNTHESIS_API_URL (e.g., https://api.z.ai/api/paas/v4)
 *    - SYNTHESIS_API_KEY
 *    - SYNTHESIS_MODEL (default: glm-4.7)
 *
 * 2. Anthropic-compatible API (Claude, etc.):
 *    - SYNTHESIS_PROVIDER=anthropic
 *    - SYNTHESIS_API_URL or ANTHROPIC_BASE_URL
 *    - SYNTHESIS_API_KEY or ANTHROPIC_API_KEY
 *    - SYNTHESIS_MODEL or ANTHROPIC_MODEL (default: glm-4.7)
 *
 * 3. Ollama:
 *    - SYNTHESIS_PROVIDER=ollama (or unset)
 *    - OLLAMA_URL (required)
 *    - OLLAMA_MODEL (default: llama3.2)
 */
export function createSynthesisAgentFromEnv(): SynthesisAgent {
  const provider = (process.env.SYNTHESIS_PROVIDER ?? "ollama") as LLMProvider;

  if (provider === "openai") {
    const baseUrl = process.env.SYNTHESIS_API_URL;
    const apiKey = process.env.SYNTHESIS_API_KEY;

    if (!baseUrl || !apiKey) {
      throw new Error(
        "SYNTHESIS_API_URL and SYNTHESIS_API_KEY are required for openai provider"
      );
    }

    return new SynthesisAgent({
      provider: "openai",
      baseUrl,
      apiKey,
      model: process.env.SYNTHESIS_MODEL || "glm-4.7",
      timeout: process.env.SYNTHESIS_TIMEOUT ? parseInt(process.env.SYNTHESIS_TIMEOUT, 10) : 60000,
    });
  }

  if (provider === "anthropic") {
    const baseUrl = process.env.SYNTHESIS_API_URL || process.env.ANTHROPIC_BASE_URL;
    const apiKey = process.env.SYNTHESIS_API_KEY || process.env.ANTHROPIC_API_KEY;

    if (!baseUrl || !apiKey) {
      throw new Error(
        "SYNTHESIS_API_URL/ANTHROPIC_BASE_URL and SYNTHESIS_API_KEY/ANTHROPIC_API_KEY are required for anthropic provider"
      );
    }

    return new SynthesisAgent({
      provider: "anthropic",
      baseUrl,
      apiKey,
      model: process.env.SYNTHESIS_MODEL || process.env.ANTHROPIC_MODEL || "glm-4.7",
      timeout: process.env.SYNTHESIS_TIMEOUT ? parseInt(process.env.SYNTHESIS_TIMEOUT, 10) : 60000,
    });
  }

  // Ollama provider
  const ollamaUrl = process.env.OLLAMA_URL;

  if (!ollamaUrl) {
    throw new Error("OLLAMA_URL environment variable is required for ollama provider");
  }

  return new SynthesisAgent({
    provider: "ollama",
    baseUrl: ollamaUrl,
    model: process.env.OLLAMA_MODEL ?? "llama3.2",
    timeout: process.env.OLLAMA_TIMEOUT ? parseInt(process.env.OLLAMA_TIMEOUT, 10) : 30000,
  });
}

/**
 * Create a SynthesisAgent with zAI API (GLM-4.7)
 * Uses Anthropic-compatible endpoint at https://api.z.ai/api/anthropic/v1
 */
export function createZAISynthesisAgent(
  apiKey: string,
  options?: { model?: string; timeout?: number }
): SynthesisAgent {
  return new SynthesisAgent({
    provider: "anthropic",
    baseUrl: "https://api.z.ai/api/anthropic/v1",
    apiKey,
    model: options?.model ?? "glm-4.7",
    timeout: options?.timeout ?? 60000,
  });
}
