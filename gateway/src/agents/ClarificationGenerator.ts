/**
 * Clarification Generator - Generates clarification questions
 *
 * Creates targeted questions to resolve query ambiguity
 * and gather missing context for better results.
 */

import type { ClarificationQuestion } from "../types/agent-contracts.js";
import type { QueryClassification } from "./QueryClassifier.js";

/**
 * Generate clarification questions based on query, classification, round, and collected context
 *
 * This function is context-aware and filters out already-answered questions,
 * generating different follow-up questions for subsequent rounds.
 *
 * @param query - The original user query
 * @param classification - Query classification result
 * @param round - Current conversation round (1-indexed, default 1)
 * @param collectedContext - Previously collected answers (default empty)
 */
export function generateClarifications(
  query: string,
  classification: QueryClassification,
  round: number = 1,
  collectedContext: Record<string, unknown> = {},
): ClarificationQuestion[] {
  // Clear queries don't need clarification
  if (classification.clarity === "clear") {
    return [];
  }

  const questions: ClarificationQuestion[] = [];
  const lowerQuery = query.toLowerCase();

  // Helper to check if question was already answered
  const alreadyAnswered = (id: string): boolean => {
    return id in collectedContext && collectedContext[id] !== undefined;
  };

  // Round 1: Initial clarification questions
  if (round === 1) {
    // Aspect clarification (for auth-related queries)
    if (lowerQuery.includes("auth") && !alreadyAnswered("aspect")) {
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
    if (!alreadyAnswered("scope")) {
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
    }

    // Context clarification (optional, multiple choice)
    if (!alreadyAnswered("context")) {
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
    }
  }

  // Round 2+: Follow-up questions based on previous answers
  if (round >= 2) {
    // Ask for specific component if they chose "Specific component(s)"
    if (
      collectedContext.scope === "Specific component(s)" &&
      !alreadyAnswered("component_name")
    ) {
      questions.push({
        id: "component_name",
        question: "Which specific component?",
        options: ["Frontend", "Backend/Gateway", "Database", "API", "Other"],
        multipleChoice: false,
        required: true,
      });
    }

    // Ask for specific file if they chose "Specific file(s)"
    if (
      collectedContext.scope === "Specific file(s)" &&
      !alreadyAnswered("file_hint")
    ) {
      questions.push({
        id: "file_hint",
        question: "Can you provide a file name or path hint?",
        options: [],
        multipleChoice: false,
        required: true,
      });
    }

    // Ask for timeframe if they chose "Recent changes only"
    if (
      collectedContext.scope === "Recent changes only" &&
      !alreadyAnswered("timeframe")
    ) {
      questions.push({
        id: "timeframe",
        question: "How recent should the changes be?",
        options: ["Last 24 hours", "Last week", "Last month", "Last quarter"],
        multipleChoice: false,
        required: true,
      });
    }

    // Ask for error details if debugging
    if (
      (collectedContext.context === "Debugging" ||
        (Array.isArray(collectedContext.context) &&
          collectedContext.context.includes("Debugging"))) &&
      !alreadyAnswered("error_type")
    ) {
      questions.push({
        id: "error_type",
        question: "What type of issue are you debugging?",
        options: [
          "Error/Exception",
          "Performance issue",
          "Unexpected behavior",
          "Integration issue",
        ],
        multipleChoice: false,
        required: true,
      });
    }
  }

  // Round 3: Final refinement questions (if still have unanswered aspects)
  if (round >= 3) {
    // If we still have no specific focus, ask for more detail
    if (
      !alreadyAnswered("additional_context") &&
      questions.length === 0
    ) {
      questions.push({
        id: "additional_context",
        question:
          "Is there any additional context that would help me answer your question?",
        options: [],
        multipleChoice: false,
        required: false,
      });
    }
  }

  return questions;
}

// Re-export ClarificationQuestion for convenience
export type { ClarificationQuestion } from "../types/agent-contracts.js";
