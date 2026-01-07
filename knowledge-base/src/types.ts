/**
 * Core Type Definitions for Knowledge Graph System
 * Defines all data structures for nodes, relationships, queries, and operations
 */

// ============================================================================
// ENUMS
// ============================================================================

/**
 * Node types in the knowledge graph
 */
export enum NodeType {
  CODE = "code",
  MARKDOWN = "markdown",
  DOCUMENT = "document",
  ISSUE = "issue",
  COMMIT = "commit",
  CONCEPT = "concept",
}

/**
 * Relationship types between nodes
 * Matches relationships.schema.yaml
 */
export enum RelationshipType {
  // Document relationships
  REFERENCES = "REFERENCES",
  IS_REFERENCED_BY = "IS_REFERENCED_BY",
  RELATED_TO = "RELATED_TO",
  EXTENDS = "EXTENDS",
  IS_EXTENDED_BY = "IS_EXTENDED_BY",
  SUPERSEDES = "SUPERSEDES",
  IS_SUPERSEDED_BY = "IS_SUPERSEDED_BY",

  // Code relationships
  DEPENDS_ON = "DEPENDS_ON",
  IS_DEPENDENCY_OF = "IS_DEPENDENCY_OF",
  IMPLEMENTS = "IMPLEMENTS",
  IS_IMPLEMENTED_BY = "IS_IMPLEMENTED_BY",
  EXTENDS_CLASS = "EXTENDS_CLASS",
  IS_EXTENDED_BY_CLASS = "IS_EXTENDED_BY_CLASS",
  CALLS = "CALLS",
  IS_CALLED_BY = "IS_CALLED_BY",

  // Temporal relationships
  PRECEDES = "PRECEDES",
  FOLLOWS = "FOLLOWS",

  // Concept relationships
  CONCEPT_RELATES = "CONCEPT_RELATES",
  CONCEPT_SIMILAR = "CONCEPT_SIMILAR",

  // Part-whole relationships
  PART_OF = "PART_OF",
  HAS_PART = "HAS_PART",

  // Example relationships
  EXAMPLE_OF = "EXAMPLE_OF",
  HAS_EXAMPLE = "HAS_EXAMPLE",

  // Documentation relationships
  DESCRIBES = "DESCRIBES",
  IS_DESCRIBED_BY = "IS_DESCRIBED_BY",

  // Test relationships
  TESTS = "TESTS",
  IS_TESTED_BY = "IS_TESTED_BY",

  // Configuration relationships
  CONFIGURES = "CONFIGURES",
  IS_CONFIGURED_BY = "IS_CONFIGURED_BY",
}

/**
 * Ingestion status
 */
export enum IngestionStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed",
}

// ============================================================================
// INTERFACES
// ============================================================================

/**
 * Source location for a node
 */
export interface SourceLocation {
  repo: string;
  path: string;
  branch?: string;
  language?: string;
  lineStart?: number;
  lineEnd?: number;
}

/**
 * Metadata attached to nodes
 */
export interface NodeMetadata {
  createdAt: string;
  updatedAt: string;
  author?: string;
  commitHash?: string;
  tags?: string[];
  symbols?: string[];
}

/**
 * Relationship between nodes
 */
export interface Relationship {
  id: string;
  type: RelationshipType;
  targetNodeId: string;
  strength: number; // 0-1
  metadata?: Record<string, unknown>;
  createdAt: Date;
}

/**
 * Knowledge Graph Node
 */
export interface KGNode {
  id: string;
  type: NodeType;
  content: string;
  source: SourceLocation;
  vector?: number[];
  relationships: Relationship[];
  metadata: NodeMetadata;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Node in Qdrant format
 */
export interface QdrantPoint {
  id: string;
  vector: number[];
  payload: {
    node_id: string;
    type: NodeType;
    content: string;
    source: SourceLocation;
    relationships: Relationship[];
    metadata: NodeMetadata;
    created_at: string;
    updated_at: string;
  };
}

// ============================================================================
// SEARCH & QUERY
// ============================================================================

/**
 * Search request with filters
 */
export interface SearchRequest {
  query: string;
  collection?: string;
  topK?: number;
  minScore?: number;
  filters?: SearchFilter;
  includeGraph?: boolean;
  maxDepth?: number;
}

/**
 * Filters for search
 */
export interface SearchFilter {
  nodeTypes?: NodeType[];
  relationshipTypes?: RelationshipType[];
  sourceRepos?: string[];
  languages?: string[];
  tags?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
}

/**
 * Search result with score
 */
export interface SearchResult {
  node: KGNode;
  score: number;
  matchedRelationships?: Relationship[];
}

/**
 * Graph traversal result
 */
export interface GraphTraversalResult {
  nodes: KGNode[];
  edges: Relationship[];
  paths: TraversalPath[];
}

/**
 * A traversal path through the graph
 */
export interface TraversalPath {
  nodes: string[];
  edges: Relationship[];
  totalStrength: number;
}

// ============================================================================
// SUMMARIZATION
// ============================================================================

/**
 * Citation for evidence-based summarization
 */
export interface Citation {
  nodeId: string;
  source: SourceLocation;
  excerpt: string;
  confidence: number;
}

/**
 * Evidence-based summary
 */
export interface EvidenceSummary {
  text: string;
  citations: Citation[];
  confidence: number;
  metadata: {
    query: string;
    nodeCount: number;
    model: string;
    generatedAt: string;
  };
}

// ============================================================================
// INGESTION
// ============================================================================

/**
 * Document to ingest
 */
export interface IngestDocument {
  source: SourceLocation;
  content: string;
  metadata?: Partial<NodeMetadata>;
}

/**
 * Chunk of a document
 */
export interface DocumentChunk {
  id: string;
  documentId: string;
  content: string;
  vector?: number[];
  chunkIndex: number;
  metadata: {
    tokens: number;
    startLine?: number;
    endLine?: number;
  };
}

/**
 * Ingestion result
 */
export interface IngestionResult {
  status: IngestionStatus;
  documentsProcessed: number;
  nodesCreated: number;
  relationshipsCreated: number;
  errors: string[];
  duration: number;
}

/**
 * GitHub webhook payload
 */
export interface GitHubWebhookPayload {
  repository: {
    name: string;
    full_name: string;
    clone_url: string;
    default_branch: string;
  };
  ref: string;
  before: string;
  after: string;
  commits: Array<{
    id: string;
    added: string[];
    modified: string[];
    removed: string[];
  }>;
}

// ============================================================================
// CACHING
// ============================================================================

/**
 * Cache metrics
 */
export interface CacheMetrics {
  size: number; // MB
  documentCount: number;
  hitRate: number;
  avgLatency: number;
  promotions: number;
  evictions: number;
}

/**
 * Temperature score for cache promotion
 */
export interface TemperatureScore {
  nodeId: string;
  temperature: number; // 0-1
  band: "hot" | "warm" | "cold";
  components: {
    recency: number;
    frequency: number;
    hitRatio: number;
    speed: number;
  };
  lastCalculated: string;
}

/**
 * Cache entry
 */
export interface CacheEntry {
  nodeId: string;
  node: KGNode;
  accessedAt: string;
  accessCount: number;
  temperature: number;
}

// ============================================================================
// FALLBACK & RETRY
// ============================================================================

/**
 * Fallback provider types
 */
export enum FallbackProvider {
  OLLAMA_VPS = "ollama_vps",
  OLLAMA_LOCAL = "ollama_local",
  OPENAI = "openai",
}

/**
 * Fallback trigger type
 */
export enum FallbackTrigger {
  TIMEOUT = "timeout",
  CONTAINER_DOWN = "container_down",
  RETRY_EXCEEDED = "retry_exceeded",
  MODEL_NOT_FOUND = "model_not_found",
}

/**
 * Embedding request
 */
export interface EmbeddingRequest {
  texts: string[];
  model?: string;
  batchSize?: number;
}

/**
 * Embedding response
 */
export interface EmbeddingResponse {
  embeddings: number[][];
  model: string;
  provider: FallbackProvider;
  duration: number;
}

/**
 * Summarization request
 */
export interface SummarizationRequest {
  query: string;
  nodes: KGNode[];
  scores: number[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
}

/**
 * Summarization response
 */
export interface SummarizationResponse {
  summary: EvidenceSummary;
  model: string;
  provider: FallbackProvider;
  duration: number;
}

/**
 * Fallback attempt
 */
export interface FallbackAttempt {
  provider: FallbackProvider;
  success: boolean;
  error?: string;
  duration: number;
  trigger?: FallbackTrigger;
}

// ============================================================================
// MCP & API
// ============================================================================

/**
 * MCP query request
 */
export interface MCPQueryRequest {
  query: string;
  collection?: string;
  topK?: number;
  includeCitations?: boolean;
  filters?: SearchFilter;
}

/**
 * MCP query response
 */
export interface MCPQueryResponse {
  results: SearchResult[];
  summary?: EvidenceSummary;
  metadata: {
    query: string;
    duration: number;
    cacheHit: boolean;
    provider: FallbackProvider;
  };
}

/**
 * MCP ingest request
 */
export interface MCPIngestRequest {
  source: SourceLocation;
  content?: string; // If not provided, fetch from source
  force?: boolean; // Force re-ingest even if exists
}

/**
 * Health check response
 */
export interface HealthCheckResponse {
  status: "healthy" | "degraded" | "unhealthy";
  services: {
    qdrant: boolean;
    ollama: boolean;
    localCache: boolean;
  };
  uptime: number;
  version: string;
}

/**
 * Statistics response
 */
export interface StatsResponse {
  nodes: number;
  relationships: number;
  collections: string[];
  cache: CacheMetrics;
  ingestion: {
    totalProcessed: number;
    lastIngestionAt: string;
  };
}

// ============================================================================
// CONFIGURATION
// ============================================================================

/**
 * KB configuration
 */
export interface KBConfig {
  qdrant: {
    url: string;
    apiKey?: string;
    collection: string;
    timeout: number;
    vectorSize: number;
  };
  ollama: {
    vps: {
      url: string;
      embedModel: string;
      summarizeModel: string;
      timeout: number;
      maxRetries: number;
    };
    local: {
      enabled: boolean;
      url: string;
      embedModel: string;
      summarizeModel: string;
      timeout: number;
    };
  };
  openai: {
    enabled: boolean;
    apiKey?: string;
    embedModel: string;
    summarizeModel: string;
    timeout: number;
    fallbackTriggers: FallbackTrigger[];
    maxRetriesBeforeFallback: number;
  };
  localCache: {
    enabled: boolean;
    path: string;
    maxSize: number;
    maxDocuments: number;
    promotionThreshold: number;
    demotionThreshold: number;
  };
  knowledgeGraph: {
    enabled: boolean;
    relationshipSchema: string;
    maxTraversalDepth: number;
    minRelationshipStrength: number;
  };
  search: {
    semantic: {
      enabled: boolean;
      weight: number;
      topK: number;
      minScore: number;
    };
    graph: {
      enabled: boolean;
      weight: number;
      maxDepth: number;
      followRelationships: RelationshipType[];
    };
  };
  summarization: {
    enabled: boolean;
    provider: "ollama" | "openai";
    model: string;
    citationRequired: boolean;
  };
  mcp: {
    enabled: boolean;
    port: number;
    auth: {
      enabled: boolean;
      apiKey?: string;
    };
  };
  logging: {
    level: string;
    format: string;
  };
}
