/**
 * Knowledge Base - Main Orchestrator
 *
 * Coordinates all KB operations:
 * - Query routing (semantic + graph)
 * - Document ingestion
 * - Provider fallback management
 * - Metrics tracking
 *
 * VPS Endpoints:
 * - Qdrant: http://72.60.204.156:6333
 * - Ollama: http://72.60.204.156:11434
 */

import type {
  KBConfig,
  SearchRequest,
  SearchResult,
  IngestDocument,
  IngestionResult,
  StatsResponse,
  EvidenceSummary,
  KGNode,
} from "./types.js";
import { IngestionStatus } from "./types.js";
import { QdrantProvider } from "./providers/QdrantProvider.js";
import { FallbackManager } from "./fallback/FallbackManager.js";
import type { FallbackManagerConfig } from "./fallback/FallbackManager.js";

/**
 * Knowledge Base - Main orchestrator class
 */
export class KnowledgeBase {
  private config: KBConfig;
  private qdrantProvider: QdrantProvider;
  private fallbackManager: FallbackManager;
  private initialized: boolean = false;

  // Metrics tracking
  private queryCount: number = 0;
  private ingestCount: number = 0;
  private totalQueryTime: number = 0;
  private totalIngestTime: number = 0;
  private lastActivity: Date = new Date();

  constructor(config: KBConfig) {
    this.config = config;

    // Initialize Qdrant provider
    this.qdrantProvider = new QdrantProvider({
      url: this.config.qdrant.url,
      apiKey: this.config.qdrant.apiKey,
      collection: this.config.qdrant.collection,
      vectorSize: this.config.qdrant.vectorSize,
      distance: "Cosine", // Default to Cosine distance
      timeout: this.config.qdrant.timeout,
    });

    // Initialize fallback manager
    const fallbackConfig: FallbackManagerConfig = {
      ollamaVPS: {
        enabled: true,
        url: this.config.ollama.vps.url,
        timeout: this.config.ollama.vps.timeout,
        maxRetries: this.config.ollama.vps.maxRetries,
      },
      ollamaLocal: {
        enabled: this.config.ollama.local.enabled,
        url: this.config.ollama.local.url,
        timeout: this.config.ollama.local.timeout,
      },
      openai: {
        enabled: this.config.openai.enabled && !!this.config.openai.apiKey,
        apiKey: this.config.openai.apiKey,
        timeout: this.config.openai.timeout,
        maxRetriesBeforeFallback: this.config.openai.maxRetriesBeforeFallback,
      },
    };
    this.fallbackManager = new FallbackManager(fallbackConfig);
  }

  /**
   * Initialize Knowledge Base
   * Creates Qdrant collection if not exists
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      console.log("Knowledge Base already initialized");
      return;
    }

    try {
      console.log("Initializing Knowledge Base...");
      console.log(`- Qdrant URL: ${this.config.qdrant.url}`);
      console.log(`- Ollama URL: ${this.config.ollama.vps.url}`);
      console.log(`- Collection: ${this.config.qdrant.collection}`);

      // Initialize Qdrant collection
      await this.qdrantProvider.initializeCollection();

      this.initialized = true;
      console.log("Knowledge Base initialized successfully");
    } catch (error) {
      throw new Error(
        `Failed to initialize Knowledge Base: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Query knowledge graph (semantic + graph)
   * @param request - Search request
   * @returns Search results with optional summary
   */
  async query(request: SearchRequest): Promise<{
    results: SearchResult[];
    summary?: EvidenceSummary;
    metadata: {
      duration: number;
      provider: string;
      cacheHit: boolean;
    };
  }> {
    if (!this.initialized) {
      throw new Error("Knowledge Base not initialized. Call initialize() first.");
    }

    const startTime = Date.now();

    try {
      // Generate embedding for query using fallback manager
      const embedResponse = await this.fallbackManager.embed({
        texts: [request.query],
      });
      const queryVector = embedResponse.embeddings[0];

      // Perform semantic search
      const searchResults = await this.qdrantProvider.search(
        queryVector,
        request.topK || this.config.search.semantic.topK
      );

      // Filter by min score
      const minScore = request.minScore ?? this.config.search.semantic.minScore;
      const filteredResults = searchResults.filter(
        (r) => r.score >= minScore
      );

      let summary: EvidenceSummary | undefined;

      // Generate summary if enabled and we have results
      if (
        this.config.summarization.enabled &&
        filteredResults.length > 0
      ) {
        const summaryResponse = await this.fallbackManager.summarize({
          query: request.query,
          nodes: filteredResults.map((r) => r.node),
          scores: filteredResults.map((r) => r.score),
          model: this.config.summarization.model,
          temperature: 0.3,
        });
        summary = summaryResponse.summary;
      }

      // Update metrics
      this.queryCount++;
      this.totalQueryTime += Date.now() - startTime;
      this.lastActivity = new Date();

      return {
        results: filteredResults,
        summary,
        metadata: {
          duration: Date.now() - startTime,
          provider: embedResponse.provider,
          cacheHit: false, // TODO: Implement caching
        },
      };
    } catch (error) {
      throw new Error(
        `Query failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Ingest documents into knowledge graph
   * @param documents - Documents to ingest
   * @returns Ingestion result
   */
  async ingest(documents: IngestDocument[]): Promise<IngestionResult> {
    if (!this.initialized) {
      throw new Error("Knowledge Base not initialized. Call initialize() first.");
    }

    const startTime = Date.now();
    const errors: string[] = [];
    let nodesCreated = 0;
    let relationshipsCreated = 0;

    try {
      console.log(`Ingesting ${documents.length} documents...`);

      // Generate embeddings for all documents
      const texts = documents.map((d) => d.content);
      const embedResponse = await this.fallbackManager.embed({
        texts,
      });

      // Create KG nodes
      const nodes: KGNode[] = documents.map((doc, index) => {
        const now = new Date();
        const createdAt = doc.metadata?.createdAt
          ? new Date(doc.metadata.createdAt)
          : now;
        const updatedAt = doc.metadata?.updatedAt
          ? new Date(doc.metadata.updatedAt)
          : now;

        return {
          id: this.generateNodeId(doc),
          type: this.inferNodeType(doc),
          content: doc.content,
          source: doc.source,
          vector: embedResponse.embeddings[index],
          relationships: [], // TODO: Extract relationships
          metadata: {
            createdAt: doc.metadata?.createdAt || new Date().toISOString(),
            updatedAt: doc.metadata?.updatedAt || new Date().toISOString(),
            ...doc.metadata,
          },
          createdAt,
          updatedAt,
        };
      });

      // Upsert nodes to Qdrant
      await this.qdrantProvider.upsertNodes(nodes);

      nodesCreated = nodes.length;
      relationshipsCreated = 0; // TODO: Count relationships

      // Update metrics
      this.ingestCount++;
      this.totalIngestTime += Date.now() - startTime;
      this.lastActivity = new Date();

      return {
        status: IngestionStatus.COMPLETED,
        documentsProcessed: documents.length,
        nodesCreated,
        relationshipsCreated,
        errors,
        duration: Date.now() - startTime,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      errors.push(errorMessage);

      return {
        status: IngestionStatus.FAILED,
        documentsProcessed: 0,
        nodesCreated,
        relationshipsCreated,
        errors,
        duration: Date.now() - startTime,
      };
    }
  }

  /**
   * Get statistics
   * @returns Knowledge base statistics
   */
  async getStats(): Promise<StatsResponse> {
    const collectionInfo = await this.qdrantProvider.getCollectionInfo();
    // const fallbackStats = this.fallbackManager.getStats();

    return {
      nodes: collectionInfo.count,
      relationships: 0, // TODO: Count from nodes
      collections: [this.config.qdrant.collection],
      cache: {
        size: 0, // TODO: Track cache size
        documentCount: 0,
        hitRate: 0,
        avgLatency: 0,
        promotions: 0,
        evictions: 0,
      },
      ingestion: {
        totalProcessed: this.ingestCount,
        lastIngestionAt: this.lastActivity.toISOString(),
      },
    };
  }

  /**
   * Health check
   * @returns Health status
   */
  async healthCheck(): Promise<{
    status: "healthy" | "degraded" | "unhealthy";
    services: {
      qdrant: boolean;
      ollama: boolean;
      fallbackManager: boolean;
    };
  }> {
    const healthStatus = await this.fallbackManager.getHealthStatus();

    return {
      status: healthStatus["ollama_vps"]?.available ? "healthy" : "degraded",
      services: {
        qdrant: this.initialized,
        ollama: healthStatus["ollama_vps"]?.available || false,
        fallbackManager: true,
      },
    };
  }

  /**
   * Generate unique node ID from document
   * Uses UUID v4 as required by Qdrant for string point IDs
   * @param _document - Ingest document (parameter kept for future use)
   * @returns Unique node ID (UUID)
   */
  private generateNodeId(_document: IngestDocument): string {
    // Generate UUID v4 as required by Qdrant for string point IDs
    // Qdrant accepts only: unsigned integers or UUID strings
    return crypto.randomUUID();
  }

  /**
   * Infer node type from document
   * @param document - Ingest document
   * @returns Node type
   */
  private inferNodeType(document: IngestDocument): any {
    const { path } = document.source;

    // Infer from file extension
    if (path.endsWith(".md")) {
      return "MARKDOWN";
    }
    if (path.match(/\.(ts|js|tsx|jsx|py|go|rs)$/)) {
      return "CODE";
    }
    if (path.match(/\.(txt|json|yaml|yml)$/)) {
      return "DOCUMENT";
    }

    // Default
    return "DOCUMENT";
  }

  /**
   * Shutdown gracefully
   */
  async shutdown(): Promise<void> {
    console.log("Shutting down Knowledge Base...");
    // TODO: Clean up resources
    this.initialized = false;
    console.log("Knowledge Base shut down");
  }
}
