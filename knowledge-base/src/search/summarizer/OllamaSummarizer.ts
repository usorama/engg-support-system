/**
 * Ollama Summarizer
 * Evidence-based summarization with mandatory citations using Ollama SLMs
 *
 * VPS Endpoint: http://72.60.204.156:11434
 * Model: llama3.2
 * Temperature: 0.3 (deterministic)
 */

import axios, { type AxiosInstance } from "axios";
import type {
  KGNode,
  EvidenceSummary,
  Citation,
} from "../../core/types.js";
import { FallbackProvider } from "../../core/types.js";

/**
 * Ollama summarizer configuration
 */
export interface OllamaSummarizerConfig {
  /** Ollama API URL */
  url: string;
  /** Model name (default: llama3.2) */
  model: string;
  /** Request timeout in milliseconds */
  timeout: number;
  /** Temperature for generation (0-1, lower = more deterministic) */
  temperature: number;
  /** Maximum tokens to generate */
  maxTokens: number;
}

/**
 * Ollama chat message
 */
interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

/**
 * Ollama chat API response
 */
interface ChatResponse {
  message: {
    role: string;
    content: string;
  };
  done: boolean;
  model: string;
}

/**
 * OllamaSummarizer - Evidence-based summarization with citations
 */
export class OllamaSummarizer {
  private client: AxiosInstance;
  private config: OllamaSummarizerConfig;

  constructor(config: Partial<OllamaSummarizerConfig> = {}) {
    this.config = {
      url: config.url || (process.env.OLLAMA_URL || "http://localhost:11434"),
      model: config.model || "llama3.2",
      timeout: config.timeout || 90000,  // 90s for slower VPS performance
      temperature: config.temperature || 0.3,
      maxTokens: config.maxTokens || 4096,
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
   * Summarize with mandatory citations from retrieved chunks
   * @param query - User's question
   * @param nodes - Retrieved knowledge graph nodes
   * @param scores - Relevance scores for each node
   * @returns Evidence summary with citations
   */
  async summarizeWithCitations(
    query: string,
    nodes: KGNode[],
    scores: number[]
  ): Promise<EvidenceSummary> {
    if (nodes.length === 0) {
      throw new Error("No nodes provided for summarization");
    }

    if (nodes.length !== scores.length) {
      throw new Error("Nodes and scores must have the same length");
    }

    try {
      // Prepare context from nodes
      const context = this.prepareContext(nodes, scores);

      // Generate summary using Ollama
      const summaryText = await this.generateSummary(query, context);

      // Extract citations from summary
      const citations = this.extractCitations(summaryText, nodes, scores);

      // Calculate confidence based on scores and citation count
      const confidence = this.calculateConfidence(scores, citations.length);

      return {
        text: summaryText,
        citations,
        confidence,
        metadata: {
          query,
          nodeCount: nodes.length,
          model: this.config.model,
          generatedAt: new Date().toISOString(),
        },
      };
    } catch (error) {
      throw new Error(
        `Summarization failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Prepare context from nodes
   * @param nodes - Knowledge graph nodes
   * @param scores - Relevance scores
   * @returns Formatted context string
   */
  private prepareContext(nodes: KGNode[], scores: number[]): string {
    return nodes
      .map(
        (node, index) => `
[Source ${index + 1}: ${node.source.path}]
Relevance: ${(scores[index] * 100).toFixed(1)}%
${node.content}
`
      )
      .join("\n---\n");
  }

  /**
   * Generate summary using Ollama chat API
   * @param query - User's question
   * @param context - Formatted context from nodes
   * @returns Generated summary text
   */
  private async generateSummary(query: string, context: string): Promise<string> {
    const systemPrompt = `You are a technical knowledge assistant. Your task is to:
1. Answer the user's question using ONLY the provided context
2. Include mandatory citations in format [Source: file-path]
3. Be concise but comprehensive
4. If context doesn't contain the answer, say so clearly`;

    const userPrompt = `Context:
${context}

Question: ${query}

Provide a comprehensive answer with citations.`;

    const response = await this.client.post<ChatResponse>("/api/chat", {
      model: this.config.model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ] as ChatMessage[],
      stream: false,
      options: {
        temperature: this.config.temperature,
        num_predict: this.config.maxTokens,
      },
    });

    if (!response.data?.message?.content) {
      throw new Error("Invalid response from Ollama: missing message content");
    }

    return response.data.message.content.trim();
  }

  /**
   * Extract citations from generated summary
   * @param summary - Generated summary text
   * @param nodes - Original nodes
   * @param scores - Relevance scores
   * @returns Array of citations
   */
  private extractCitations(
    summary: string,
    nodes: KGNode[],
    scores: number[]
  ): Citation[] {
    const citations: Citation[] = [];
    const citationRegex = /\[Source:\s*([^\]]+)\]/g;
    const seenSources = new Set<string>();

    let match;
    while ((match = citationRegex.exec(summary)) !== null) {
      const sourcePath = match[1];

      // Find matching node
      const nodeIndex = nodes.findIndex((n) => n.source.path.includes(sourcePath));

      if (nodeIndex !== -1 && !seenSources.has(sourcePath)) {
        const node = nodes[nodeIndex];
        citations.push({
          nodeId: node.id,
          source: node.source,
          excerpt: node.content.substring(0, 200) + "...",
          confidence: scores[nodeIndex],
        });
        seenSources.add(sourcePath);
      }
    }

    // If no citations found in text, create from nodes
    if (citations.length === 0) {
      for (let i = 0; i < Math.min(3, nodes.length); i++) {
        citations.push({
          nodeId: nodes[i].id,
          source: nodes[i].source,
          excerpt: nodes[i].content.substring(0, 200) + "...",
          confidence: scores[i],
        });
      }
    }

    return citations;
  }

  /**
   * Calculate confidence score
   * @param scores - Relevance scores
   * @param citationCount - Number of citations extracted
   * @returns Confidence score (0-1)
   */
  private calculateConfidence(scores: number[], citationCount: number): number {
    // Average score
    const avgScore =
      scores.reduce((sum, score) => sum + score, 0) / scores.length;

    // Citation coverage (ideally have citations for top nodes)
    const citationCoverage = Math.min(citationCount / 3, 1);

    // Combined confidence: 70% average score, 30% citation coverage
    return avgScore * 0.7 + citationCoverage * 0.3;
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
      // Use startsWith to match model with or without tag (e.g., "llama3.2" matches "llama3.2:latest")
      const modelAvailable = models.some(
        (m: { name: string }) => m.name === this.config.model || m.name.startsWith(this.config.model + ":")
      );

      return modelAvailable;
    } catch {
      return false;
    }
  }

  /**
   * Get provider type
   * @returns Provider identifier
   */
  getProvider(): FallbackProvider {
    return FallbackProvider.OLLAMA_VPS;
  }
}
