/**
 * API Types - Mirrors gateway/src/types/agent-contracts.ts
 *
 * These types define the exact contracts for communication with the ESS Gateway API.
 * Any changes to the Gateway must be reflected here.
 */

// ============================================================================
// QUERY TYPES
// ============================================================================

export type QueryIntent =
  | "code"
  | "explanation"
  | "both"
  | "location"
  | "relationship"
  | "unknown";

export type QueryStatus = "success" | "partial" | "unavailable";

export type QueryMode = "one-shot" | "conversational";

export type SynthesisMode = "synthesized" | "raw";

export type FeedbackType = "useful" | "not_useful" | "partial";

// ============================================================================
// REQUEST TYPES
// ============================================================================

export interface QueryRequest {
  query: string;
  project?: string;
  context?: string[];
  mode?: QueryMode;
  synthesisMode?: SynthesisMode;
}

export interface ConversationContinueRequest {
  answers: Record<string, string>;
}

export interface FeedbackRequest {
  requestId: string;
  feedback: FeedbackType;
  comment?: string;
}

// ============================================================================
// RESPONSE TYPES
// ============================================================================

export interface SemanticMatch {
  content: string;
  score: number;
  source: string;
  type: "code" | "doc" | "comment";
  lineStart?: number;
  lineEnd?: number;
  language?: string;
}

export interface SemanticResult {
  summary: string;
  matches: SemanticMatch[];
}

export interface StructuralRelationship {
  source: string;
  target: string;
  type: string;
  path: string[];
  explanation?: string;
}

export interface StructuralResult {
  summary: string;
  relationships: StructuralRelationship[];
}

export interface CombinedInsights {
  summary: string;
  keyFindings: string[];
  recommendations?: string[];
}

export interface SynthesisCitation {
  source: string;
  lineStart?: number;
  lineEnd?: number;
  relevance: number;
  type: "code" | "doc" | "graph";
}

export interface SynthesizedAnswer {
  text: string;
  confidence: number;
  citations: SynthesisCitation[];
}

export interface QueryResults {
  semantic: SemanticResult;
  structural: StructuralResult;
  insights?: CombinedInsights;
}

export interface QueryMetadata {
  qdrantQueried: boolean;
  neo4jQueried: boolean;
  qdrantLatency: number;
  neo4jLatency: number;
  totalLatency: number;
  cacheHit: boolean;
}

export interface QueryResponse {
  requestId: string;
  status: QueryStatus;
  timestamp: string;
  queryType: QueryIntent;
  answer?: SynthesizedAnswer;
  results: QueryResults;
  meta: QueryMetadata;
  warnings?: string[];
  fallbackMessage?: string;
}

// ============================================================================
// CONVERSATION TYPES
// ============================================================================

export interface ClarificationQuestion {
  id: string;
  question: string;
  options: string[];
  multipleChoice: boolean;
  required: boolean;
}

export interface ClarificationData {
  questions: ClarificationQuestion[];
  message: string;
}

export interface ConversationResponse {
  type: "conversation";
  conversationId: string;
  round: number;
  maxRounds: number;
  phase: "analyzing" | "clarifying" | "executing" | "completed";
  clarifications: ClarificationData;
  meta: {
    originalQuery: string;
    detectedIntent: QueryIntent;
    confidence: number;
    collectedContext?: Record<string, unknown>;
  };
}

export type GatewayResponse = QueryResponse | ConversationResponse;

// Type guard to check if response is a conversation response
export function isConversationResponse(
  response: GatewayResponse
): response is ConversationResponse {
  return "type" in response && response.type === "conversation";
}

// Type guard to check if response is a query response
export function isQueryResponse(
  response: GatewayResponse
): response is QueryResponse {
  return "results" in response && !("type" in response);
}

// ============================================================================
// HEALTH CHECK TYPES
// ============================================================================

export interface ServiceHealth {
  status: "ok" | "error" | "unknown";
  latency?: number;
  error?: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  services: {
    neo4j: ServiceHealth;
    qdrant: ServiceHealth;
    redis: ServiceHealth;
    ollama: ServiceHealth;
  };
}

// ============================================================================
// PROJECTS TYPES
// ============================================================================

export interface ProjectsResponse {
  projects: string[];
  message?: string;
}

// ============================================================================
// ERROR TYPES
// ============================================================================

export interface APIError {
  error: string;
  message: string;
  retryAfter?: number;
}

// ============================================================================
// UI STATE TYPES (for Chat UI)
// ============================================================================

export type MessageRole = "user" | "assistant" | "system";

export type MessageType =
  | "query"
  | "answer"
  | "clarification"
  | "error"
  | "loading";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  type: MessageType;
  content: string;
  timestamp: Date;
  // For answer messages
  answer?: SynthesizedAnswer;
  results?: QueryResults;
  // For clarification messages
  clarifications?: ClarificationData;
  conversationId?: string;
  // Metadata
  requestId?: string;
  latencyMs?: number;
}

export interface ConversationState {
  conversationId: string | null;
  isActive: boolean;
  currentRound: number;
  maxRounds: number;
  phase: ConversationResponse["phase"] | "idle";
  pendingClarifications: ClarificationQuestion[] | null;
  collectedAnswers: Record<string, string>;
}
