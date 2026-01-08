/**
 * Qdrant Client Utility
 * Handles semantic search queries to Qdrant vector database
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import type { SemanticResult, SemanticMatch } from "../types/agent-contracts.js";

export interface QdrantClientConfig {
  url: string;
  apiKey?: string;
  collection: string;
  timeout?: number;
}

/**
 * Qdrant client for semantic search
 */
export class QdrantGatewayClient {
  private client: QdrantClient;
  private collection: string;
  private timeout: number;

  constructor(config: QdrantClientConfig) {
    const clientConfig: {
      url: string;
      apiKey?: string;
      timeout: number;
    } = {
      url: config.url,
      timeout: config.timeout || 30000,
    };

    if (config.apiKey !== undefined) {
      clientConfig.apiKey = config.apiKey;
    }

    this.client = new QdrantClient(clientConfig);
    this.collection = config.collection;
    this.timeout = config.timeout || 30000;
  }

  /**
   * Check if Qdrant is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      await this.client.getCollections();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Perform semantic search
   */
  async semanticSearch(
    query: string,
    queryVector: number[],
    options: {
      limit?: number;
      minScore?: number;
      filters?: Record<string, unknown>;
    } = {},
  ): Promise<{ results: SemanticResult; latency: number }> {
    const startTime = Date.now();

    try {
      const searchParams: {
        vector: number[];
        limit: number;
        score_threshold?: number;
      } = {
        vector: queryVector,
        limit: options.limit || 10,
      };

      if (options.minScore !== undefined) {
        searchParams.score_threshold = options.minScore;
      }

      const searchResults = await this.client.search(this.collection, searchParams);

      const latency = Date.now() - startTime;

      const matches: SemanticMatch[] = searchResults.map((result) => {
        const payload = result.payload as {
          content: string;
          source: string;
          type: "code" | "doc" | "comment";
          lineStart?: number;
          lineEnd?: number;
          language?: string;
        };

        const match: SemanticMatch = {
          content: payload.content,
          score: result.score,
          source: payload.source,
          type: payload.type,
        };

        if (payload.lineStart !== undefined) {
          match.lineStart = payload.lineStart;
        }

        if (payload.lineEnd !== undefined) {
          match.lineEnd = payload.lineEnd;
        }

        if (payload.language !== undefined) {
          match.language = payload.language;
        }

        return match;
      });

      const summary = this.generateSummary(matches);

      return {
        results: {
          summary,
          matches,
        },
        latency,
      };
    } catch (error) {
      throw new Error(
        `Qdrant search failed: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  /**
   * Generate summary from matches
   */
  private generateSummary(matches: SemanticMatch[]): string {
    if (matches.length === 0) {
      return "No matches found.";
    }

    const codeCount = matches.filter((m) => m.type === "code").length;
    const docCount = matches.filter((m) => m.type === "doc").length;

    return `Found ${matches.length} semantic match${matches.length > 1 ? "es" : ""} (${codeCount} code, ${docCount} documentation)`;
  }

  /**
   * Get collection info
   */
  async getCollectionInfo(): Promise<{ pointsCount: number } | null> {
    try {
      const collection = await this.client.getCollection(this.collection);
      const pointsCount = collection.points_count ?? 0;
      return { pointsCount };
    } catch {
      return null;
    }
  }
}
