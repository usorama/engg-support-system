/**
 * Clarification Generator - Generates clarification questions
 *
 * Creates targeted questions to resolve query ambiguity
 * and gather missing context for better results.
 */

import type { ClarificationQuestion } from "../types/agent-contracts.js";
import type { QueryClassification } from "./QueryClassifier.js";

/**
 * Generate clarification questions based on query and classification
 */
export function generateClarifications(
  query: string,
  classification: QueryClassification,
): ClarificationQuestion[] {
  // Clear queries don't need clarification
  if (classification.clarity === "clear") {
    return [];
  }

  const questions: ClarificationQuestion[] = [];
  const lowerQuery = query.toLowerCase();

  // Aspect clarification (for auth-related queries)
  if (lowerQuery.includes("auth")) {
    questions.push({
      id: "aspect",
      question: "What aspect of authentication are you asking about?",
      options: [
        "How it works (explanation)",
        "Code implementation",
        "Configuration",
        "Recent changes",
        "Troubleshooting",
      ],
      multipleChoice: false,
      required: true,
    });
  }

  // Scope clarification (always included for ambiguous queries)
  questions.push({
    id: "scope",
    question: "Which scope should I focus on?",
    options: [
      "Entire system",
      "Specific component(s)",
      "Specific file(s)",
      "Recent changes only",
    ],
    multipleChoice: false,
    required: classification.clarity === "requires_context",
  });

  // Context clarification (optional, multiple choice)
  questions.push({
    id: "context",
    question: "What is your goal with this information?",
    options: [
      "Understanding/learning",
      "Implementation",
      "Debugging",
      "Documentation",
      "Refactoring",
    ],
    multipleChoice: true,
    required: false,
  });

  return questions;
}

// Re-export ClarificationQuestion for convenience
export type { ClarificationQuestion } from "../types/agent-contracts.js";
