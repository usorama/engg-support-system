/**
 * ChatPanel - Main chat interface component
 *
 * Combines message display, input, and conversation management
 * into a complete chat experience.
 */

import { useRef, useEffect, useCallback } from "react";
import { Trash2, RefreshCw, AlertTriangle } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import type { ChatMessage, FeedbackType } from "../types/api";

export interface ChatPanelProps {
  /** All chat messages */
  messages: ChatMessage[];
  /** Is a request in progress */
  isLoading: boolean;
  /** Current error message */
  error: string | null;
  /** Whether we're in an active conversation */
  isConversationActive: boolean;
  /** Has pending clarifications */
  hasClarifications: boolean;
  /** Callback to send a new query */
  onSendQuery: (query: string) => void;
  /** Callback to answer clarifications */
  onAnswerClarifications: (answers: Record<string, string>) => void;
  /** Callback to cancel conversation */
  onCancelConversation: () => void;
  /** Callback to submit feedback */
  onFeedback: (
    requestId: string,
    feedback: FeedbackType,
    comment?: string
  ) => void;
  /** Callback to clear chat */
  onClearChat: () => void;
  /** Callback to retry last request */
  onRetry: () => void;
}

export function ChatPanel({
  messages,
  isLoading,
  error,
  isConversationActive,
  hasClarifications,
  onSendQuery,
  onAnswerClarifications,
  onCancelConversation,
  onFeedback,
  onClearChat,
  onRetry,
}: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleClarificationSubmit = useCallback(
    (answers: Record<string, string>) => {
      onAnswerClarifications(answers);
    },
    [onAnswerClarifications]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-16 h-16 mb-4 rounded-full bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-cyan-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-slate-200 mb-2">
              Engineering Support System
            </h2>
            <p className="text-slate-400 max-w-md">
              Ask questions about your codebase. I can search through code,
              documentation, and graph relationships to provide evidence-based
              answers.
            </p>
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
              {[
                "How does authentication work?",
                "What are the main components?",
                "Show me error handling patterns",
                "What connects to the database?",
              ].map((example, index) => (
                <button
                  key={index}
                  onClick={() => onSendQuery(example)}
                  className="px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-600/50 rounded-lg text-sm text-slate-300 hover:text-slate-200 text-left transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onClarificationSubmit={
              message.type === "clarification" ? handleClarificationSubmit : undefined
            }
            onClarificationCancel={
              message.type === "clarification" ? onCancelConversation : undefined
            }
            onFeedback={onFeedback}
            isSubmitting={isLoading}
          />
        ))}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center justify-between animate-slide-up">
          <div className="flex items-center gap-2 text-red-300">
            <AlertTriangle size={16} />
            <span className="text-sm">{error}</span>
          </div>
          <button
            onClick={onRetry}
            className="flex items-center gap-1 px-3 py-1 text-sm text-red-300 hover:text-red-200 hover:bg-red-500/20 rounded-lg transition-colors"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="p-4 border-t border-slate-700/50">
        {/* Clear chat button */}
        {messages.length > 0 && !isLoading && (
          <div className="flex justify-end mb-2">
            <button
              onClick={onClearChat}
              className="flex items-center gap-1 px-2 py-1 text-xs text-slate-500 hover:text-slate-300 hover:bg-slate-700/50 rounded transition-colors"
            >
              <Trash2 size={12} />
              Clear chat
            </button>
          </div>
        )}

        <ChatInput
          onSubmit={onSendQuery}
          onCancel={isConversationActive ? onCancelConversation : undefined}
          isLoading={isLoading}
          canCancel={isConversationActive && !hasClarifications}
          disabled={hasClarifications}
          placeholder={
            hasClarifications
              ? "Please answer the questions above..."
              : "Ask about your codebase..."
          }
        />
      </div>
    </div>
  );
}

export default ChatPanel;
