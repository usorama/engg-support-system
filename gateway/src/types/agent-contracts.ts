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

// ============================================================================
// SYNTHESIS TYPES (Answer Generation)
// ============================================================================

/**
 * Citation from synthesized answer
 */
export interface SynthesisCitation {
  /** Source file path or graph reference */
  source: string;

  /** Line start (for code sources) */
  lineStart?: number;

  /** Line end (for code sources) */
  lineEnd?: number;

  /** Relevance score (0-1) */
  relevance: number;

  /** Source type */
  type: "code" | "doc" | "graph";
}

/**
 * Synthesized answer from SynthesisAgent
 */
export interface SynthesizedAnswer {
  /** The synthesized answer text (Markdown) */
  text: string;

  /** Confidence score (0-1) */
  confidence: number;

  /** Evidence citations */
  citations: SynthesisCitation[];
}

/**
 * Synthesis mode for query requests
 */
export type SynthesisMode = "synthesized" | "raw";

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

  /** Synthesized answer (when synthesisMode !== "raw") */
  answer?: SynthesizedAnswer;

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

// ============================================================================
// CONVERSATION TYPES (Phase 0b)
// ============================================================================

/**
 * Query mode (one-shot or conversational)
 */
export type QueryMode = "one-shot" | "conversational";

/**
 * Enhanced query request with optional mode
 */
export interface QueryRequestWithMode extends QueryRequest {
  /** Query mode (optional - auto-detected if not specified) */
  mode?: QueryMode;

  /** Synthesis mode: "synthesized" (default) returns intelligent answer, "raw" returns search results only */
  synthesisMode?: SynthesisMode;
}

/**
 * Conversation clarification question
 */
export interface ClarificationQuestion {
  /** Question ID */
  id: string;

  /** Question text */
  question: string;

  /** Available options */
  options: string[];

  /** Allow multiple selections */
  multipleChoice: boolean;

  /** Is this question required */
  required: boolean;
}

/**
 * Clarification response data
 */
export interface ClarificationData {
  /** Questions to ask user */
  questions: ClarificationQuestion[];

  /** Message to user */
  message: string;
}

/**
 * Conversation request (continuation)
 */
export interface ConversationRequest {
  /** Conversation ID */
  conversationId: string;

  /** User's answers to clarification questions */
  answers: Record<string, string>;

  /** Request ID */
  requestId: string;

  /** Timestamp */
  timestamp: string;
}

/**
 * Conversation response (when clarification needed)
 */
export interface ConversationResponse {
  /** Response type discriminator */
  type: "conversation";

  /** Conversation ID */
  conversationId: string;

  /** Current round number */
  round: number;

  /** Maximum rounds allowed */
  maxRounds: number;

  /** Conversation phase */
  phase: "analyzing" | "clarifying" | "executing" | "completed";

  /** Clarification questions */
  clarifications: ClarificationData;

  /** Metadata */
  meta: {
    /** Original query */
    originalQuery: string;

    /** Detected intent */
    detectedIntent: QueryIntent;

    /** Confidence score */
    confidence: number;

    /** Collected context so far */
    collectedContext?: Record<string, unknown>;
  };
}

/**
 * Unified response type (one-shot or conversation)
 */
export type GatewayResponse = QueryResponse | ConversationResponse;
