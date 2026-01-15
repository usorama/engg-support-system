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
 * Qdrant payload from veracity-engine indexing
 */
interface VeracityPayload {
  uid: string;
  name: string;
  qualified_name: string;
  docstring: string;
  path: string;
  labels: string[];
  project: string;
}

/**
 * Qdrant payload from ingest-project.ts script
 */
interface IngestPayload {
  content: string;
  filePath: string;
  project: string;
  nodeType: string;
  createdAt: string;
}

/**
 * Union type for all possible payloads
 */
type QdrantPayload = VeracityPayload | IngestPayload;

/**
 * Check if payload is from ingest-project.ts
 */
function isIngestPayload(payload: QdrantPayload): payload is IngestPayload {
  return "content" in payload && "filePath" in payload && "nodeType" in payload;
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
      checkCompatibility: boolean;
    } = {
      url: config.url,
      timeout: config.timeout || 30000,
      checkCompatibility: false, // Skip version check for older Qdrant servers
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
        with_payload: boolean;
      } = {
        vector: queryVector,
        limit: options.limit || 10,
        with_payload: true,
      };

      if (options.minScore  !==  undefined) {
        searchParams.score_threshold = options.minScore;
      }

      const searchResults = await this.client.search(this.collection, searchParams);

      const latency = Date.now() - startTime;

      const matches: SemanticMatch[] = searchResults.map((result) => {
        const payload = result.payload as unknown as QdrantPayload;

        // Handle both payload formats
        if (isIngestPayload(payload)) {
          // IngestPayload from ingest-project.ts
          const match: SemanticMatch = {
            content: payload.content,
            score: result.score,
            source: payload.filePath,
            type: this.determineContentTypeFromNodeType(payload.nodeType),
          };
          return match;
        } else {
          // VeracityPayload from veracity-engine
          const match: SemanticMatch = {
            content: payload.docstring || payload.name,
            score: result.score,
            source: payload.path,
            type: this.determineContentType(payload.labels || []),
            name: payload.name,
            path: payload.path,
            docstring: payload.docstring,
            qualified_name: payload.qualified_name,
          } as SemanticMatch & { name?: string; path?: string; docstring?: string; qualified_name?: string };
          return match;
        }
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
   * Determine content type from labels (VeracityPayload)
   */
  private determineContentType(labels: string[]): "code" | "doc" | "comment" {
    if (labels.includes("Document") || labels.includes("Doc")) {
      return "doc";
    }
    if (labels.includes("Code") || labels.includes("Function") || labels.includes("Class")) {
      return "code";
    }
    return "code";
  }

  /**
   * Determine content type from nodeType (IngestPayload)
   */
  private determineContentTypeFromNodeType(nodeType: string): "code" | "doc" | "comment" {
    if (nodeType === "MARKDOWN" || nodeType === "DOCUMENT") {
      return "doc";
    }
    if (nodeType === "CODE") {
      return "code";
    }
    return "code";
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
