/**
 * MessageBubble - Individual chat message display
 *
 * Renders user and assistant messages with appropriate styling,
 * markdown content, evidence display, and feedback controls.
 */

import { useState, useCallback } from "react";
import {
  User,
  Bot,
  AlertCircle,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Clock,
} from "lucide-react";
import type { ChatMessage, FeedbackType } from "../types/api";
import { MarkdownContent } from "./MarkdownContent";
import { EvidenceDisplay } from "./EvidenceDisplay";
import { ClarificationPrompt } from "./ClarificationPrompt";

export interface MessageBubbleProps {
  /** The message to display */
  message: ChatMessage;
  /** Callback when clarification answers are submitted */
  onClarificationSubmit?: (answers: Record<string, string>) => void;
  /** Callback when clarification is cancelled */
  onClarificationCancel?: () => void;
  /** Callback for feedback submission */
  onFeedback?: (
    requestId: string,
    feedback: FeedbackType,
    comment?: string
  ) => void;
  /** Whether submission is in progress */
  isSubmitting?: boolean;
}

/**
 * Format timestamp for display
 */
function formatTime(date: Date): string {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format latency for display
 */
function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function MessageBubble({
  message,
  onClarificationSubmit,
  onClarificationCancel,
  onFeedback,
  isSubmitting,
}: MessageBubbleProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<FeedbackType | null>(null);

  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const isSystem = message.role === "system";

  const handleFeedback = useCallback(
    (feedback: FeedbackType) => {
      if (!message.requestId || !onFeedback) return;
      setFeedbackGiven(feedback);
      onFeedback(message.requestId, feedback);
    },
    [message.requestId, onFeedback]
  );

  // Loading message
  if (message.type === "loading") {
    return (
      <div className="flex items-start gap-3 animate-slide-up">
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
          <Bot size={18} className="text-cyan-400" />
        </div>
        <div className="flex items-center gap-2 px-4 py-3 bg-slate-800/50 rounded-2xl rounded-tl-sm">
          <Loader2 size={16} className="animate-spin text-cyan-400" />
          <span className="text-slate-300 text-sm animate-pulse-subtle">
            {message.content}
          </span>
        </div>
      </div>
    );
  }

  // Error message
  if (message.type === "error") {
    return (
      <div className="flex items-start gap-3 animate-slide-up">
        {isAssistant && (
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
            <Bot size={18} className="text-cyan-400" />
          </div>
        )}
        <div
          className={`
            flex items-center gap-2 px-4 py-3 rounded-2xl
            ${isSystem ? "bg-red-500/10 border border-red-500/30" : "bg-slate-800/50"}
          `}
        >
          <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
          <span className="text-red-300 text-sm">{message.content}</span>
        </div>
      </div>
    );
  }

  // User message
  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end animate-slide-up">
        <div className="max-w-[80%]">
          <div className="message-user px-4 py-3 rounded-2xl rounded-tr-sm">
            <p className="text-white text-sm whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
          <div className="flex justify-end mt-1 px-1">
            <span className="text-xs text-slate-500">
              {formatTime(message.timestamp)}
            </span>
          </div>
        </div>
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
          <User size={18} className="text-white" />
        </div>
      </div>
    );
  }

  // Assistant message (answer or clarification)
  return (
    <div className="flex items-start gap-3 animate-slide-up">
      <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
        <Bot size={18} className="text-cyan-400" />
      </div>
      <div className="max-w-[85%] flex-1">
        <div className="message-assistant px-4 py-3 rounded-2xl rounded-tl-sm">
          {/* Clarification prompt */}
          {message.type === "clarification" && message.clarifications ? (
            <ClarificationPrompt
              clarifications={message.clarifications}
              onSubmit={onClarificationSubmit || (() => {})}
              onCancel={onClarificationCancel || (() => {})}
              isSubmitting={isSubmitting}
            />
          ) : (
            <>
              {/* Answer content */}
              <MarkdownContent content={message.content} />

              {/* Evidence display */}
              {message.type === "answer" && (
                <EvidenceDisplay
                  citations={message.answer?.citations}
                  results={message.results}
                  confidence={message.answer?.confidence}
                />
              )}
            </>
          )}
        </div>

        {/* Footer with timestamp, latency, and feedback */}
        <div className="flex items-center justify-between mt-1 px-1">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>{formatTime(message.timestamp)}</span>
            {message.latencyMs !== undefined && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {formatLatency(message.latencyMs)}
              </span>
            )}
          </div>

          {/* Feedback buttons for answer messages */}
          {message.type === "answer" && message.requestId && onFeedback && (
            <div className="flex items-center gap-1">
              {feedbackGiven ? (
                <span className="text-xs text-slate-500">Thanks!</span>
              ) : (
                <>
                  <button
                    onClick={() => handleFeedback("useful")}
                    className="p-1.5 text-slate-500 hover:text-green-400 hover:bg-green-400/10 rounded-lg transition-colors"
                    title="Helpful"
                  >
                    <ThumbsUp size={14} />
                  </button>
                  <button
                    onClick={() => handleFeedback("not_useful")}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                    title="Not helpful"
                  >
                    <ThumbsDown size={14} />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MessageBubble;
