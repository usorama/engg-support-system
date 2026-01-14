/**
 * useConversation Hook - Complete conversation state management
 *
 * Handles the full conversation lifecycle:
 * - One-shot queries
 * - Multi-round conversations with clarifications
 * - Message history
 * - Error handling and retry
 * - Feedback submission
 */

import { useState, useCallback, useRef } from "react";
import { apiClient, APIClientError } from "../utils/api-client";
import type {
  ChatMessage,
  ConversationState,
  GatewayResponse,
  QueryRequest,
  FeedbackType,
} from "../types/api";
import { isConversationResponse, isQueryResponse } from "../types/api";

export interface UseConversationOptions {
  /** Default project to use */
  defaultProject?: string | null;
  /** Default synthesis mode */
  synthesisMode?: "synthesized" | "raw";
}

export interface UseConversationResult {
  /** All chat messages */
  messages: ChatMessage[];
  /** Current conversation state */
  conversationState: ConversationState;
  /** Is a request in progress */
  isLoading: boolean;
  /** Current error message */
  error: string | null;
  /** Send a new query */
  sendQuery: (query: string, project?: string | null) => Promise<void>;
  /** Answer clarification questions */
  answerClarifications: (answers: Record<string, string>) => Promise<void>;
  /** Cancel current conversation */
  cancelConversation: () => Promise<void>;
  /** Submit feedback for a response */
  submitFeedback: (
    requestId: string,
    feedback: FeedbackType,
    comment?: string
  ) => Promise<void>;
  /** Clear all messages and start fresh */
  clearChat: () => void;
  /** Retry last failed request */
  retry: () => Promise<void>;
}

// Generate unique IDs for messages
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

// Create initial conversation state
function createInitialState(): ConversationState {
  return {
    conversationId: null,
    isActive: false,
    currentRound: 0,
    maxRounds: 3,
    phase: "idle",
    pendingClarifications: null,
    collectedAnswers: {},
  };
}

/**
 * Hook for managing conversation state and messages
 */
export function useConversation(
  options: UseConversationOptions = {}
): UseConversationResult {
  const { defaultProject = null, synthesisMode = "synthesized" } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationState, setConversationState] = useState<ConversationState>(
    createInitialState
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Store last request for retry
  const lastRequestRef = useRef<{
    type: "query" | "clarification";
    query?: string;
    project?: string | null;
    answers?: Record<string, string>;
  } | null>(null);

  /**
   * Add a message to the chat
   */
  const addMessage = useCallback(
    (
      message: Omit<ChatMessage, "id" | "timestamp">
    ): string => {
      const id = generateId();
      setMessages((prev) => [
        ...prev,
        {
          ...message,
          id,
          timestamp: new Date(),
        },
      ]);
      return id;
    },
    []
  );

  /**
   * Update a message by ID
   */
  const updateMessage = useCallback(
    (id: string, updates: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
      );
    },
    []
  );

  /**
   * Remove a message by ID
   */
  const removeMessage = useCallback((id: string) => {
    setMessages((prev) => prev.filter((msg) => msg.id !== id));
  }, []);

  /**
   * Process a gateway response
   */
  const processResponse = useCallback(
    (response: GatewayResponse, loadingMessageId: string) => {
      if (isConversationResponse(response)) {
        // This is a clarification request
        setConversationState({
          conversationId: response.conversationId,
          isActive: true,
          currentRound: response.round,
          maxRounds: response.maxRounds,
          phase: response.phase,
          pendingClarifications: response.clarifications.questions,
          collectedAnswers: {},
        });

        // Update loading message to clarification
        updateMessage(loadingMessageId, {
          type: "clarification",
          content: response.clarifications.message,
          clarifications: response.clarifications,
          conversationId: response.conversationId,
        });
      } else if (isQueryResponse(response)) {
        // This is a final answer
        const answerText =
          response.answer?.text ||
          response.results?.semantic?.summary ||
          "No answer available";

        // Update loading message to answer
        updateMessage(loadingMessageId, {
          type: "answer",
          content: answerText,
          answer: response.answer,
          results: response.results,
          requestId: response.requestId,
          latencyMs: response.meta.totalLatency,
        });

        // Add any warnings
        if (response.warnings && response.warnings.length > 0) {
          addMessage({
            role: "system",
            type: "error",
            content: `Note: ${response.warnings.join(". ")}`,
          });
        }

        // Reset conversation state (answer received)
        setConversationState(createInitialState());
      }
    },
    [updateMessage, addMessage]
  );

  /**
   * Send a new query
   */
  const sendQuery = useCallback(
    async (query: string, project?: string | null) => {
      const effectiveProject = project ?? defaultProject;

      // Store for retry
      lastRequestRef.current = { type: "query", query, project: effectiveProject };

      // Add user message
      addMessage({
        role: "user",
        type: "query",
        content: query,
      });

      // Add loading message
      const loadingId = addMessage({
        role: "assistant",
        type: "loading",
        content: "Searching knowledge base...",
      });

      setIsLoading(true);
      setError(null);

      try {
        const request: QueryRequest = {
          query,
          synthesisMode,
          mode: "conversational",
          ...(effectiveProject && { project: effectiveProject }),
        };

        const response = await apiClient.startConversation(request);
        processResponse(response, loadingId);
      } catch (err) {
        // Remove loading message
        removeMessage(loadingId);

        const errorMessage =
          err instanceof APIClientError
            ? err.message
            : "Failed to process query";

        setError(errorMessage);

        addMessage({
          role: "assistant",
          type: "error",
          content: `Error: ${errorMessage}`,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [
      defaultProject,
      synthesisMode,
      addMessage,
      removeMessage,
      processResponse,
    ]
  );

  /**
   * Answer clarification questions
   */
  const answerClarifications = useCallback(
    async (answers: Record<string, string>) => {
      const { conversationId, pendingClarifications } = conversationState;

      if (!conversationId || !pendingClarifications) {
        setError("No active conversation to continue");
        return;
      }

      // Store for retry
      lastRequestRef.current = { type: "clarification", answers };

      // Format user's answers as a message
      const answerSummary = pendingClarifications
        .map((q) => {
          const answer = answers[q.id];
          return answer ? `${q.question}: ${answer}` : null;
        })
        .filter(Boolean)
        .join("\n");

      // Add user's answers as a message
      addMessage({
        role: "user",
        type: "query",
        content: answerSummary,
      });

      // Add loading message
      const loadingId = addMessage({
        role: "assistant",
        type: "loading",
        content: "Processing your answers...",
      });

      setIsLoading(true);
      setError(null);

      try {
        const response = await apiClient.continueConversation(conversationId, {
          answers,
        });
        processResponse(response, loadingId);
      } catch (err) {
        // Remove loading message
        removeMessage(loadingId);

        const errorMessage =
          err instanceof APIClientError
            ? err.message
            : "Failed to continue conversation";

        setError(errorMessage);

        addMessage({
          role: "assistant",
          type: "error",
          content: `Error: ${errorMessage}`,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [conversationState, addMessage, removeMessage, processResponse]
  );

  /**
   * Cancel current conversation
   */
  const cancelConversation = useCallback(async () => {
    const { conversationId } = conversationState;

    if (!conversationId) return;

    try {
      await apiClient.abortConversation(conversationId);
    } catch {
      // Ignore errors when canceling
    }

    setConversationState(createInitialState());

    addMessage({
      role: "system",
      type: "error",
      content: "Conversation cancelled.",
    });
  }, [conversationState, addMessage]);

  /**
   * Submit feedback for a response
   */
  const submitFeedback = useCallback(
    async (
      requestId: string,
      feedback: FeedbackType,
      comment?: string
    ) => {
      try {
        await apiClient.submitFeedback({ requestId, feedback, comment });
      } catch (err) {
        const errorMessage =
          err instanceof APIClientError
            ? err.message
            : "Failed to submit feedback";
        setError(errorMessage);
      }
    },
    []
  );

  /**
   * Clear all messages and start fresh
   */
  const clearChat = useCallback(() => {
    // Cancel any active conversation
    const { conversationId } = conversationState;
    if (conversationId) {
      apiClient.abortConversation(conversationId).catch(() => {});
    }

    setMessages([]);
    setConversationState(createInitialState());
    setError(null);
    lastRequestRef.current = null;
  }, [conversationState]);

  /**
   * Retry last failed request
   */
  const retry = useCallback(async () => {
    const lastRequest = lastRequestRef.current;
    if (!lastRequest) return;

    if (lastRequest.type === "query" && lastRequest.query) {
      await sendQuery(lastRequest.query, lastRequest.project);
    } else if (lastRequest.type === "clarification" && lastRequest.answers) {
      await answerClarifications(lastRequest.answers);
    }
  }, [sendQuery, answerClarifications]);

  return {
    messages,
    conversationState,
    isLoading,
    error,
    sendQuery,
    answerClarifications,
    cancelConversation,
    submitFeedback,
    clearChat,
    retry,
  };
}

export default useConversation;
