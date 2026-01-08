/**
 * Agent Contracts - Deterministic Input/Output for EnggContextAgent
 *
 * These contracts define the EXACT structure that the Internal Query Agent
 * must use for all communication with external agents.
 */

// ============================================================================
// QUERY TYPES
// ============================================================================

/**
 * Query intent classification
 * Determines what type of results to return
 */
export type QueryIntent =
  | "code" // Just show me the code
  | "explanation" // Explain how it works
  | "both" // Code + explanation
  | "location" // Where is this thing?
  | "relationship" // What connects to this?
  | "unknown"; // Ambiguous, return both

/**
 * Query status
 */
export type QueryStatus = "success" | "partial" | "unavailable";

// ============================================================================
// REQUEST CONTRACTS
// ============================================================================

/**
 * Input contract for EnggContextAgent
 * External agents MUST send requests in this format
 */
export interface QueryRequest {
  /** Natural language query */
  query: string;

  /** Unique request ID for tracking */
  requestId: string;

  /** ISO timestamp of request */
  timestamp: string;

  /** Optional: specific project to query */
  project?: string;

  /** Optional: additional context */
  context?: string[];
}

// ============================================================================
// RESPONSE CONTRACTS
// ============================================================================

/**
 * Semantic match from Qdrant
 */
export interface SemanticMatch {
  /** Content (Markdown formatted: code blocks, text, etc.) */
  content: string;

  /** Confidence score (0-1) */
  score: number;

  /** Source file path */
  source: string;

  /** Type of content */
  type: "code" | "doc" | "comment";

  /** Line numbers for code blocks (optional) */
  lineStart?: number;

  lineEnd?: number;

  /** Programming language (for code blocks) */
  language?: string;
}

/**
 * Semantic results from Qdrant
 */
export interface SemanticResult {
  /** Markdown summary */
  summary: string;

  /** Matching documents */
  matches: SemanticMatch[];
}

/**
 * Structural relationship from Neo4j
 */
export interface StructuralRelationship {
  /** Source node */
  source: string;

  /** Target node */
  target: string;

  /** Relationship type */
  type: string;

  /** Full traversal path */
  path: string[];

  /** Markdown explanation (optional) */
  explanation?: string;
}

/**
 * Structural results from Neo4j
 */
export interface StructuralResult {
  /** Markdown summary */
  summary: string;

  /** Relationships found */
  relationships: StructuralRelationship[];
}

/**
 * Combined insights (optional - for "both" and "explanation" queries)
 */
export interface CombinedInsights {
  /** Executive summary (Markdown) */
  summary: string;

  /** Key findings (bullet points in Markdown) */
  keyFindings: string[];

  /** Optional recommendations */
  recommendations?: string[];
}

/**
 * Query results from both databases
 */
export interface QueryResults {
  /** Semantic search results from Qdrant */
  semantic: SemanticResult;

  /** Structural search results from Neo4j */
  structural: StructuralResult;

  /** Combined insights (optional) */
  insights?: CombinedInsights;
}

/**
 * Query metadata for debugging
 */
export interface QueryMetadata {
  /** Was Qdrant queried? */
  qdrantQueried: boolean;

  /** Was Neo4j queried? */
  neo4jQueried: boolean;

  /** Qdrant latency (ms) */
  qdrantLatency: number;

  /** Neo4j latency (ms) */
  neo4jLatency: number;

  /** Total latency (ms) */
  totalLatency: number;

  /** Was result served from cache? */
  cacheHit: boolean;
}

/**
 * Output contract from EnggContextAgent
 * External agents will ALWAYS receive responses in this format
 */
export type QueryResponse =
  | QueryResponseBase
  | QueryResponseWithWarnings
  | QueryResponseWithFallback;

/**
 * Base response (successful queries)
 */
export interface QueryResponseBase {
  /** Echo request ID */
  requestId: string;

  /** Query status */
  status: QueryStatus;

  /** Response timestamp */
  timestamp: string;

  /** Query type classification */
  queryType: QueryIntent;

  /** Query results */
  results: QueryResults;

  /** Metadata */
  meta: QueryMetadata;
}

/**
 * Response with warnings (partial results)
 */
export interface QueryResponseWithWarnings extends QueryResponseBase {
  /** Warnings (if partial/unavailable) */
  warnings: string[];
}

/**
 * Response with fallback (unavailable)
 */
export interface QueryResponseWithFallback extends QueryResponseBase {
  /** Warnings (if unavailable) */
  warnings: string[];

  /** Fallback message (if unavailable) */
  fallbackMessage: string;
}
