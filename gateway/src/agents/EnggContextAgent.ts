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
  QueryRequestWithMode,
  GatewayResponse,
  ConversationResponse,
  ConversationRequest,
  SynthesizedAnswer,
} from "../types/agent-contracts.js";
import { QdrantGatewayClient, type QdrantClientConfig } from "../utils/qdrant-client.js";
import { Neo4jGatewayClient } from "../utils/neo4j-client.js";
import { classifyQuery, type QueryClassification } from "./QueryClassifier.js";
import { generateClarifications } from "./ClarificationGenerator.js";
import { conversationManager } from "./ConversationManager.js";
import { SynthesisAgent } from "./SynthesisAgent.js";

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
    /** Model for synthesis (default: llama3.2) */
    synthesisModel?: string;
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
  private synthesisAgent?: SynthesisAgent;

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

      // Initialize SynthesisAgent for intelligent answer generation
      this.synthesisAgent = new SynthesisAgent({
        ollamaUrl: config.ollama.url,
        model: config.ollama.synthesisModel ?? "llama3.2",
      });
    }
  }

  /**
   * Process a query request - ALWAYS queries both databases
   * Returns GatewayResponse (QueryResponse | ConversationResponse)
   */
  async query(request: QueryRequestWithMode): Promise<GatewayResponse> {
    const startTime = Date.now();

    // Classify query to detect ambiguity and determine mode
    const classification = classifyQuery(request.query);

    // Check if conversational mode is requested or auto-detected
    const shouldUseConversationalMode =
      request.mode === "conversational" ||
      (request.mode === undefined &&
        classification.suggestedMode === "conversational");

    // Branch to conversational mode if needed
    if (shouldUseConversationalMode) {
      return this.queryWithConversation(request, classification);
    }

    // One-shot mode: proceed with normal query flow
    const queryType = classification.intent;

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

    // Build base response (raw results)
    const baseResponse = this.buildResponse({
      request,
      queryType,
      status,
      qdrantResult,
      neo4jResult,
      qdrantAvailable,
      neo4jAvailable,
      totalLatency,
    });

    // If raw mode requested or no synthesis agent, return raw results
    if (request.synthesisMode === "raw" || !this.synthesisAgent) {
      return baseResponse;
    }

    // Synthesize intelligent answer
    try {
      const synthesisResult = await this.synthesisAgent.synthesize(
        request.query,
        baseResponse.results.semantic,
        baseResponse.results.structural,
      );

      // Return enriched response with answer and insights
      return {
        ...baseResponse,
        answer: synthesisResult.answer,
        results: {
          ...baseResponse.results,
          insights: synthesisResult.insights,
        },
      } as QueryResponse;
    } catch (synthesisError) {
      // If synthesis fails, return raw results with warning
      const warnings = [
        ...(("warnings" in baseResponse ? baseResponse.warnings : []) as string[]),
        `⚠️ Synthesis unavailable: ${synthesisError instanceof Error ? synthesisError.message : "Unknown error"}`,
      ];

      return {
        ...baseResponse,
        warnings,
      } as QueryResponse;
    }
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

  /**
   * Handle conversational mode query
   * Returns clarification questions or executes query after context collection
   */
  private async queryWithConversation(
    request: QueryRequestWithMode,
    classification: QueryClassification,
  ): Promise<ConversationResponse> {
    // Start or continue conversation
    const conversationState =
      await conversationManager.startConversation(request.query);

    // Generate clarification questions
    const clarificationQuestions = generateClarifications(
      request.query,
      classification,
    );

    // Build conversation response
    return {
      type: "conversation",
      conversationId: conversationState.conversationId,
      round: conversationState.round,
      maxRounds: conversationState.maxRounds,
      phase: conversationState.phase,
      clarifications: {
        questions: clarificationQuestions,
        message:
          classification.clarity === "requires_context"
            ? "I need more information to help you effectively."
            : "I'd like to clarify a few things to give you better results.",
      },
      meta: {
        originalQuery: request.query,
        detectedIntent: classification.intent,
        confidence: classification.confidence,
        collectedContext: conversationState.collectedContext,
      },
    };
  }

  /**
   * Continue conversation with user's answers
   * Returns QueryResponse with results or another ConversationResponse
   */
  async continueConversation(
    request: ConversationRequest,
  ): Promise<GatewayResponse> {
    // Get conversation state
    const conversationState =
      await conversationManager.getConversation(request.conversationId);

    if (conversationState === undefined) {
      // Invalid conversation ID - return error response
      return {
        requestId: request.requestId,
        status: "unavailable",
        timestamp: new Date().toISOString(),
        queryType: "unknown",
        results: {
          semantic: { summary: "Invalid conversation ID", matches: [] },
          structural: { summary: "Invalid conversation ID", relationships: [] },
        },
        warnings: ["Invalid conversation ID provided"],
        fallbackMessage: "Please start a new conversation",
        meta: {
          qdrantQueried: false,
          neo4jQueried: false,
          qdrantLatency: 0,
          neo4jLatency: 0,
          totalLatency: 0,
          cacheHit: false,
        },
      };
    }

    // Collect context from answers
    for (const [key, value] of Object.entries(request.answers)) {
      await conversationManager.addContext(
        request.conversationId,
        key,
        value,
      );
    }

    // Check if max rounds reached
    if (conversationState.round >= conversationState.maxRounds) {
      // End conversation and execute query
      await conversationManager.endConversation(request.conversationId);
      return this.executeQueryWithCollectedContext(
        request,
        conversationState,
      );
    }

    // Advance to next round
    const updatedState = await conversationManager.advanceRound(
      request.conversationId,
    );

    if (updatedState === undefined) {
      // Conversation not found - return error
      return {
        requestId: request.requestId,
        status: "unavailable",
        timestamp: new Date().toISOString(),
        queryType: "unknown",
        results: {
          semantic: { summary: "Conversation not found", matches: [] },
          structural: { summary: "Conversation not found", relationships: [] },
        },
        warnings: ["Conversation not found"],
        fallbackMessage: "Please start a new conversation",
        meta: {
          qdrantQueried: false,
          neo4jQueried: false,
          qdrantLatency: 0,
          neo4jLatency: 0,
          totalLatency: 0,
          cacheHit: false,
        },
      };
    }

    if (updatedState.phase === "completed") {
      // Max rounds reached, execute query
      return this.executeQueryWithCollectedContext(
        request,
        conversationState,
      );
    }

    // Still need more context - generate follow-up questions
    const classification = classifyQuery(
      conversationState.originalQuery,
    );
    const clarificationQuestions = generateClarifications(
      conversationState.originalQuery,
      classification,
    );

    return {
      type: "conversation",
      conversationId: updatedState.conversationId,
      round: updatedState.round,
      maxRounds: updatedState.maxRounds,
      phase: updatedState.phase,
      clarifications: {
        questions: clarificationQuestions,
        message: "Thank you. I have a few more questions to understand your needs.",
      },
      meta: {
        originalQuery: updatedState.originalQuery,
        detectedIntent: classification.intent,
        confidence: classification.confidence,
        collectedContext: updatedState.collectedContext,
      },
    };
  }

  /**
   * Execute query with collected context from conversation
   */
  private async executeQueryWithCollectedContext(
    request: ConversationRequest,
    conversationState: { originalQuery: string; collectedContext: Record<string, unknown> },
  ): Promise<QueryResponse> {
    // Build enriched query with collected context
    const enrichedQuery = this.buildEnrichedQuery(
      conversationState.originalQuery,
      conversationState.collectedContext,
    );

    // Execute query with enriched context
    return this.query({
      query: enrichedQuery,
      requestId: request.requestId,
      timestamp: request.timestamp,
      context: Object.values(conversationState.collectedContext).map(String),
    }) as Promise<QueryResponse>;
  }

  /**
   * Build enriched query with collected context
   */
  private buildEnrichedQuery(
    originalQuery: string,
    collectedContext: Record<string, unknown>,
  ): string {
    const contextParts: string[] = [originalQuery];

    // Add collected context to query
    if (collectedContext.aspect !== undefined) {
      contextParts.push(`Focus: ${collectedContext.aspect}`);
    }
    if (collectedContext.scope !== undefined) {
      contextParts.push(`Scope: ${collectedContext.scope}`);
    }
    if (collectedContext.context !== undefined) {
      contextParts.push(`Goal: ${collectedContext.context}`);
    }

    return contextParts.join(". ");
  }
}
