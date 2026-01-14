/**
 * ClarificationPrompt - Multi-choice clarification UI
 *
 * Displays clarification questions with option selection,
 * handles both single and multi-select questions,
 * and submits answers back to the conversation.
 */

import { useState, useCallback } from "react";
import { HelpCircle, Check, X, ChevronRight, Loader2 } from "lucide-react";
import type { ClarificationQuestion, ClarificationData } from "../types/api";

export interface ClarificationPromptProps {
  /** Clarification data from conversation response */
  clarifications: ClarificationData;
  /** Callback when user submits answers */
  onSubmit: (answers: Record<string, string>) => void;
  /** Callback when user cancels */
  onCancel: () => void;
  /** Whether submission is in progress */
  isSubmitting?: boolean;
}

/**
 * Single question component
 */
function QuestionCard({
  question,
  selectedValues,
  onSelect,
}: {
  question: ClarificationQuestion;
  selectedValues: string[];
  onSelect: (questionId: string, value: string) => void;
}) {
  return (
    <div className="bg-slate-800/30 rounded-lg p-4 space-y-3">
      <div className="flex items-start gap-2">
        <HelpCircle size={18} className="text-cyan-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-slate-200 font-medium">{question.question}</p>
          {question.multipleChoice && (
            <p className="text-xs text-slate-500 mt-1">
              Select all that apply
            </p>
          )}
          {question.required && (
            <span className="inline-block text-xs text-red-400 mt-1">
              Required
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-2">
        {question.options.map((option, optionIndex) => {
          const isSelected = selectedValues.includes(option);

          return (
            <button
              key={optionIndex}
              onClick={() => onSelect(question.id, option)}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all
                ${
                  isSelected
                    ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-100"
                    : "bg-slate-700/30 border-slate-600/50 text-slate-300 hover:bg-slate-700/50"
                }
                border
              `}
            >
              <div
                className={`
                  w-5 h-5 rounded flex items-center justify-center flex-shrink-0
                  ${
                    question.multipleChoice
                      ? "rounded"
                      : "rounded-full"
                  }
                  ${
                    isSelected
                      ? "bg-cyan-500 text-white"
                      : "border-2 border-slate-500"
                  }
                `}
              >
                {isSelected && <Check size={12} />}
              </div>
              <span className="text-sm">{option}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ClarificationPrompt({
  clarifications,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: ClarificationPromptProps) {
  // Track selected answers per question
  const [answers, setAnswers] = useState<Record<string, string[]>>(() => {
    // Initialize empty arrays for each question
    const initial: Record<string, string[]> = {};
    clarifications.questions.forEach((q) => {
      initial[q.id] = [];
    });
    return initial;
  });

  /**
   * Handle option selection
   */
  const handleSelect = useCallback(
    (questionId: string, value: string) => {
      const question = clarifications.questions.find((q) => q.id === questionId);
      if (!question) return;

      setAnswers((prev) => {
        const current = prev[questionId] || [];

        if (question.multipleChoice) {
          // Toggle selection for multi-select
          if (current.includes(value)) {
            return { ...prev, [questionId]: current.filter((v) => v !== value) };
          } else {
            return { ...prev, [questionId]: [...current, value] };
          }
        } else {
          // Replace selection for single-select
          return { ...prev, [questionId]: [value] };
        }
      });
    },
    [clarifications.questions]
  );

  /**
   * Check if all required questions are answered
   */
  const isValid = clarifications.questions.every((q) => {
    if (!q.required) return true;
    const selected = answers[q.id] || [];
    return selected.length > 0;
  });

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback(() => {
    if (!isValid || isSubmitting) return;

    // Convert arrays to comma-separated strings for the API
    const formattedAnswers: Record<string, string> = {};
    Object.entries(answers).forEach(([questionId, values]) => {
      if (values.length > 0) {
        formattedAnswers[questionId] = values.join(", ");
      }
    });

    onSubmit(formattedAnswers);
  }, [answers, isValid, isSubmitting, onSubmit]);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header message */}
      {clarifications.message && (
        <p className="text-slate-300 text-sm leading-relaxed">
          {clarifications.message}
        </p>
      )}

      {/* Questions */}
      <div className="space-y-4">
        {clarifications.questions.map((question) => (
          <QuestionCard
            key={question.id}
            question={question}
            selectedValues={answers[question.id] || []}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onCancel}
          disabled={isSubmitting}
          className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-colors disabled:opacity-50"
        >
          <X size={16} />
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!isValid || isSubmitting}
          className={`
            flex items-center gap-2 px-5 py-2 text-sm font-medium rounded-lg transition-all
            ${
              isValid && !isSubmitting
                ? "bg-cyan-500 hover:bg-cyan-400 text-white"
                : "bg-slate-600 text-slate-400 cursor-not-allowed"
            }
          `}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Processing...
            </>
          ) : (
            <>
              Continue
              <ChevronRight size={16} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default ClarificationPrompt;
