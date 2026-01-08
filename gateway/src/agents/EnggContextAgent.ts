/**
 * EnggContextAgent - Internal Query Agent
 *
 * Deterministic agent that queries BOTH Qdrant and Neo4j
 * and returns structured results following the agent contracts.
 *
 * CRITICAL: This agent ALWAYS queries both databases, no exceptions.
 * Partial answers return with warnings, complete answers return success.
 */

import type {
  QueryRequest,
  QueryResponse,
  QueryIntent,
  QueryStatus,
  SemanticResult,
  StructuralResult,
} from "../types/agent-contracts.js";
import { QdrantGatewayClient, type QdrantClientConfig } from "../utils/qdrant-client.js";
import { Neo4jGatewayClient } from "../utils/neo4j-client.js";

export interface EnggContextAgentConfig {
  qdrant: {
    url: string;
    apiKey?: string;
    collection: string;
  };
  neo4j: {
    uri: string;
    user: string;
    password: string;
  };
  ollama?: {
    url: string;
    embedModel: string;
  };
}

/**
 * Engineering Context Agent
 * Deterministic query agent that ALWAYS queries both Qdrant and Neo4j
 */
export class EnggContextAgent {
  private qdrantClient: QdrantGatewayClient;
  private neo4jClient: Neo4jGatewayClient;
  private ollamaUrl?: string;
  private ollamaModel?: string;

  constructor(config: EnggContextAgentConfig) {
    const qdrantConfig: QdrantClientConfig = {
      url: config.qdrant.url,
      collection: config.qdrant.collection,
    };

    if (config.qdrant.apiKey !== undefined) {
      qdrantConfig.apiKey = config.qdrant.apiKey;
    }

    this.qdrantClient = new QdrantGatewayClient(qdrantConfig);

    this.neo4jClient = new Neo4jGatewayClient({
      uri: config.neo4j.uri,
      user: config.neo4j.user,
      password: config.neo4j.password,
    });

    if (config.ollama !== undefined) {
      this.ollamaUrl = config.ollama.url;
      this.ollamaModel = config.ollama.embedModel;
    }
  }

  /**
   * Process a query request - ALWAYS queries both databases
   */
  async query(request: QueryRequest): Promise<QueryResponse> {
    const startTime = Date.now();

    // Classify query intent
    const queryType = this.classifyQuery(request.query);

    // Generate embedding for query (if Ollama available)
    const queryVector = this.ollamaUrl
      ? await this.generateEmbedding(request.query)
      : null;

    // Query both databases in parallel
    const [qdrantAvailable, neo4jAvailable] = await Promise.all([
      this.qdrantClient.isAvailable(),
      this.neo4jClient.isAvailable(),
    ]);

    // Handle different availability scenarios
    if (!qdrantAvailable && !neo4jAvailable) {
      return this.createUnavailableResponse(request, Date.now() - startTime);
    }

    // Query available databases
    const results = await Promise.allSettled([
      qdrantAvailable && queryVector
        ? this.qdrantClient.semanticSearch(request.query, queryVector)
        : Promise.reject(new Error("Qdrant unavailable")),
      neo4jAvailable
        ? this.neo4jClient.structuralSearch(
            request.query,
            request.project === undefined
              ? { limit: 10 }
              : { limit: 10, project: request.project },
          )
        : Promise.reject(new Error("Neo4j unavailable")),
    ]);

    const totalLatency = Date.now() - startTime;

    // Extract results
    const qdrantResult =
      results[0].status === "fulfilled" ? results[0].value : null;
    const neo4jResult =
      results[1].status === "fulfilled" ? results[1].value : null;

    // Determine response status
    const status = this.determineStatus(
      qdrantAvailable,
      neo4jAvailable,
      qdrantResult,
      neo4jResult,
    );

    // Build response
    return this.buildResponse({
      request,
      queryType,
      status,
      qdrantResult,
      neo4jResult,
      qdrantAvailable,
      neo4jAvailable,
      totalLatency,
    });
  }

  /**
   * Classify query intent deterministically
   */
  private classifyQuery(query: string): QueryIntent {
    const lowerQuery = query.toLowerCase();

    // CODE intent indicators
    if (
      /\b(show me|code|implement|function|class|source)\b/.test(lowerQuery)
    ) {
      return "code";
    }

    // EXPLANATION intent indicators
    if (
      /\b(explain|how does|why|what is|describe|overview|documentation)\b/.test(
        lowerQuery,
      )
    ) {
      return "explanation";
    }

    // LOCATION intent indicators
    if (/\b(where|find|locate|which file)\b/.test(lowerQuery)) {
      return "location";
    }

    // RELATIONSHIP intent indicators
    if (/\b(depends on|calls|imports|used by|connected)\b/.test(lowerQuery)) {
      return "relationship";
    }

    // Default to both for ambiguous queries
    return "both";
  }

  /**
   * Generate embedding via Ollama
   */
  private async generateEmbedding(
    text: string,
  ): Promise<number[] | null> {
    if (this.ollamaUrl === undefined || this.ollamaModel === undefined) {
      return null;
    }

    try {
      const response = await fetch(`${this.ollamaUrl}/api/embeddings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: this.ollamaModel,
          prompt: text,
        }),
      });

      if (!response.ok) {
        return null;
      }

      const data = (await response.json()) as { embedding?: number[] };
      return data.embedding ?? null;
    } catch {
      return null;
    }
  }

  /**
   * Determine response status based on availability and results
   */
  private determineStatus(
    qdrantAvailable: boolean,
    neo4jAvailable: boolean,
    _qdrantResult: { results: unknown; latency: number } | null,
    _neo4jResult: { results: unknown; latency: number } | null,
  ): QueryStatus {
    if (qdrantAvailable && neo4jAvailable) {
      return "success";
    }

    if (!qdrantAvailable && !neo4jAvailable) {
      return "unavailable";
    }

    // One database unavailable
    return "partial";
  }

  /**
   * Create unavailable response
   */
  private createUnavailableResponse(
    request: QueryRequest,
    latency: number,
  ): QueryResponse {
    const emptySemantic: SemanticResult = {
      summary: "No results available",
      matches: [],
    };

    const emptyStructural: StructuralResult = {
      summary: "No structural data available",
      relationships: [],
    };

    return {
      requestId: request.requestId,
      status: "unavailable",
      timestamp: new Date().toISOString(),
      queryType: "unknown",
      results: {
        semantic: emptySemantic,
        structural: emptyStructural,
      },
      warnings: [
        "❌ Engineering context system temporarily unavailable",
        "❌ Both Qdrant and Neo4j databases are unreachable",
      ],
      fallbackMessage: "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH",
      meta: {
        qdrantQueried: false,
        neo4jQueried: false,
        qdrantLatency: 0,
        neo4jLatency: 0,
        totalLatency: latency,
        cacheHit: false,
      },
    };
  }

  /**
   * Build query response
   */
  private buildResponse(options: {
    request: QueryRequest;
    queryType: QueryIntent;
    status: QueryStatus;
    qdrantResult: { results: SemanticResult; latency: number } | null;
    neo4jResult: { results: StructuralResult; latency: number } | null;
    qdrantAvailable: boolean;
    neo4jAvailable: boolean;
    totalLatency: number;
  }): QueryResponse {
    const {
      request,
      queryType,
      status,
      qdrantResult,
      neo4jResult,
      qdrantAvailable,
      neo4jAvailable,
      totalLatency,
    } = options;

    // Base response
    const baseResponse = {
      requestId: request.requestId,
      status,
      timestamp: new Date().toISOString(),
      queryType,
      results: {
        semantic: qdrantResult?.results ?? {
          summary: "No semantic results available",
          matches: [],
        },
        structural: neo4jResult?.results ?? {
          summary: "No structural data available",
          relationships: [],
        },
      },
      meta: {
        qdrantQueried: qdrantAvailable,
        neo4jQueried: neo4jAvailable,
        qdrantLatency: qdrantResult?.latency ?? 0,
        neo4jLatency: neo4jResult?.latency ?? 0,
        totalLatency,
        cacheHit: false,
      },
    };

    // Add warnings for partial results
    if (!qdrantAvailable || !neo4jAvailable) {
      const warnings: string[] = [];
      if (!qdrantAvailable) {
        warnings.push(
          "⚠️ Qdrant semantic search unavailable - returning structural results only",
        );
      }
      if (!neo4jAvailable) {
        warnings.push(
          "⚠️ Neo4j structural search unavailable - returning semantic results only",
        );
      }

      return {
        ...baseResponse,
        warnings,
      } as QueryResponse;
    }

    return baseResponse as QueryResponse;
  }

  /**
   * Close connections
   */
  async close(): Promise<void> {
    await this.neo4jClient.close();
  }
}
