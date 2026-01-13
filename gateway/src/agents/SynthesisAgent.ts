/**
 * SynthesisAgent - Intelligent Answer Synthesis
 *
 * Bridges the gap between raw Qdrant/Neo4j results and intelligent answers.
 * Uses Ollama llama3.2 to synthesize context-aware responses with citations.
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
 * SynthesisAgent configuration
 */
export interface SynthesisAgentConfig {
  /** Ollama URL */
  ollamaUrl: string;
  /** Model name (default: llama3.2) */
  model?: string;
  /** Request timeout in ms (default: 30000) */
  timeout?: number;
}

// ============================================================================
// SynthesisAgent Class
// ============================================================================

/**
 * SynthesisAgent - Synthesizes intelligent answers from raw search results
 */
export class SynthesisAgent {
  private readonly ollamaUrl: string;
  private readonly model: string;
  private readonly timeout: number;

  constructor(config: SynthesisAgentConfig) {
    this.ollamaUrl = config.ollamaUrl.replace(/\/$/, "");
    this.model = config.model ?? "llama3.2";
    this.timeout = config.timeout ?? 30000;
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
   * Check if Ollama is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${this.ollamaUrl}/api/tags`, {
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
   * Generate answer using Ollama chat API
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
      const response = await fetch(`${this.ollamaUrl}/api/chat`, {
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
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

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
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Synthesis timed out after ${this.timeout}ms`);
      }

      throw error;
    }
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
 * Create a SynthesisAgent for local development
 */
export function createLocalSynthesisAgent(
  ollamaPort = 11434
): SynthesisAgent {
  return new SynthesisAgent({
    ollamaUrl: `http://localhost:${ollamaPort}`,
  });
}

/**
 * Create a SynthesisAgent for VPS deployment
 */
export function createVPSSynthesisAgent(): SynthesisAgent {
  return new SynthesisAgent({
    ollamaUrl: process.env.OLLAMA_URL ?? "http://localhost:11434",
    timeout: 60000, // Longer timeout for VPS
  });
}

/**
 * Create a SynthesisAgent from environment
 */
export function createSynthesisAgentFromEnv(): SynthesisAgent {
  const ollamaUrl = process.env.OLLAMA_URL;

  if (!ollamaUrl) {
    throw new Error("OLLAMA_URL environment variable is required");
  }

  const config: SynthesisAgentConfig = {
    ollamaUrl,
    model: process.env.OLLAMA_MODEL ?? "llama3.2",
  };

  // Only add timeout if explicitly set in environment
  if (process.env.OLLAMA_TIMEOUT) {
    config.timeout = parseInt(process.env.OLLAMA_TIMEOUT, 10);
  }

  return new SynthesisAgent(config);
}
