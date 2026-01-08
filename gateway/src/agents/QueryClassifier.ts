/**
 * Query Classifier - Detects ambiguity and suggests mode
 *
 * Determines if a query is clear enough for one-shot mode
 * or needs conversational mode for clarification.
 */

import type { QueryIntent } from "../types/agent-contracts.js";

/**
 * Query classification result
 */
export interface QueryClassification {
  /** Detected query intent */
  intent: QueryIntent;

  /** Clarity level */
  clarity: "clear" | "ambiguous" | "requires_context";

  /** Confidence score (0-1) */
  confidence: number;

  /** Suggested mode */
  suggestedMode: "one-shot" | "conversational";

  /** Reasons for ambiguity (if applicable) */
  ambiguityReasons?: string[];
}

/**
 * Ambiguity indicators
 */
const AMBIGUITY_INDICATORS = {
  pronouns: ["it", "they", "that", "this thing", "these", "those"],
  vague: ["something", "anything", "stuff", "whatever", "things", "thing"],
  broad: ["all", "everything", "the whole", "each", "any"],
  context_dependent: ["the ", "a ", "an "],
};

/**
 * Non-ambiguous words (override false positives)
 */
const CLEAR_INDICATORS = [
  "show me",
  "what is",
  "how does",
  "explain",
  "where is",
  "find",
  "locate",
];

/**
 * Classify query and determine mode
 */
export function classifyQuery(query: string): QueryClassification {
  const trimmedQuery = query.trim();

  // Handle empty query
  if (trimmedQuery.length === 0) {
    return {
      intent: "unknown",
      clarity: "requires_context",
      confidence: 0.1,
      suggestedMode: "conversational",
      ambiguityReasons: ["Empty query"],
    };
  }

  const lowerQuery = trimmedQuery.toLowerCase();

  // Collect specific ambiguity reasons first
  const ambiguityReasons = collectAmbiguityReasons(lowerQuery);

  // Detect intent
  const intent = detectIntent(lowerQuery);

  // Check if query starts with clear indicators (only affects confidence, not ambiguity)
  const startsWithClearIndicator = CLEAR_INDICATORS.some((clear) =>
    lowerQuery.startsWith(clear),
  );

  // Classify based on ambiguity count
  const ambiguousCount = ambiguityReasons.length;

  if (ambiguousCount === 0) {
    return {
      intent,
      clarity: "clear",
      confidence: startsWithClearIndicator ? 0.9 : 0.8,
      suggestedMode: "one-shot",
    };
  }

  // 1-2 indicators: ambiguous
  if (ambiguousCount <= 2) {
    return {
      intent,
      clarity: "ambiguous",
      confidence: startsWithClearIndicator ? 0.7 : 0.6,
      suggestedMode: "conversational",
      ambiguityReasons,
    };
  }

  // 3+ indicators: requires_context
  ambiguityReasons.push("High ambiguity - multiple unclear references");
  return {
    intent,
    clarity: "requires_context",
    confidence: 0.3,
    suggestedMode: "conversational",
    ambiguityReasons,
  };
}

/**
 * Collect ambiguity reasons from query
 */
function collectAmbiguityReasons(query: string): string[] {
  const reasons: string[] = [];

  // Check pronouns
  for (const pronoun of AMBIGUITY_INDICATORS.pronouns) {
    const regex = new RegExp(`\\b${pronoun}\\b`, "g");
    if (regex.test(query)) {
      reasons.push(`Contains ambiguous pronoun: "${pronoun}"`);
    }
  }

  // Check vague terms
  for (const vague of AMBIGUITY_INDICATORS.vague) {
    const regex = new RegExp(`\\b${vague}\\b`, "g");
    if (regex.test(query)) {
      reasons.push(`Contains vague term: "${vague}"`);
    }
  }

  // Check broad terms
  for (const broad of AMBIGUITY_INDICATORS.broad) {
    const regex = new RegExp(`\\b${broad}\\b`, "g");
    if (regex.test(query)) {
      reasons.push(`Contains broad term: "${broad}"`);
    }
  }

  return reasons;
}

/**
 * Detect query intent
 */
function detectIntent(query: string): QueryIntent {
  // RELATIONSHIP intent indicators (check first as most specific)
  if (/\b(depend on|depends on|calls|imports|used by|connected to?)\b/.test(query)) {
    return "relationship";
  }

  // CODE intent indicators
  if (/\b(show me|code|implement|function|class|source)\b/.test(query)) {
    return "code";
  }

  // EXPLANATION intent indicators
  if (
    /\b(explain|how does|why|what is|describe|overview|documentation)\b/.test(
      query,
    )
  ) {
    return "explanation";
  }

  // LOCATION intent indicators
  if (/\b(where|find|locate|which file)\b/.test(query)) {
    return "location";
  }

  // Default to both for ambiguous queries
  return "both";
}
