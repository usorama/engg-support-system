/**
 * useChatHistory Hook - Chat history persistence using localStorage
 *
 * Provides functionality to:
 * - Save chat sessions to localStorage
 * - Load previous chat sessions
 * - List all saved sessions
 * - Delete sessions
 */

import { useState, useCallback, useEffect } from "react";
import type { ChatMessage } from "../types/api";

const CHAT_HISTORY_KEY = "ess-chat-history";
const MAX_SESSIONS = 50; // Limit stored sessions to prevent localStorage bloat

// Generate unique session IDs
function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Represents a saved chat session
 */
export interface ChatSession {
  /** Unique session identifier */
  id: string;
  /** Session title (derived from first query) */
  title: string;
  /** All messages in the session */
  messages: ChatMessage[];
  /** Associated project (if any) */
  project: string | null;
  /** When the session was created */
  createdAt: string; // ISO string for JSON serialization
  /** When the session was last updated */
  updatedAt: string; // ISO string for JSON serialization
}

/**
 * Serialized format for localStorage (dates as strings)
 */
interface StoredChatSession {
  id: string;
  title: string;
  messages: Array<Omit<ChatMessage, "timestamp"> & { timestamp: string }>;
  project: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface UseChatHistoryResult {
  /** All saved chat sessions */
  sessions: ChatSession[];
  /** Currently active session ID */
  currentSessionId: string | null;
  /** Save current messages to a session */
  saveSession: (
    messages: ChatMessage[],
    project: string | null,
    sessionId?: string
  ) => string;
  /** Load a session by ID */
  loadSession: (sessionId: string) => ChatSession | null;
  /** Delete a session by ID */
  deleteSession: (sessionId: string) => void;
  /** Clear all sessions */
  clearAllSessions: () => void;
  /** Start a new session */
  startNewSession: () => void;
  /** Set current session */
  setCurrentSessionId: (id: string | null) => void;
}

/**
 * Parse stored sessions from localStorage
 */
function parseStoredSessions(): ChatSession[] {
  try {
    const stored = localStorage.getItem(CHAT_HISTORY_KEY);
    if (!stored) return [];

    const parsed = JSON.parse(stored) as StoredChatSession[];
    return parsed.map((session) => ({
      ...session,
      messages: session.messages.map((msg) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      })),
    }));
  } catch {
    // If parsing fails, return empty array
    return [];
  }
}

/**
 * Serialize sessions for localStorage
 */
function serializeSessions(sessions: ChatSession[]): string {
  const serialized: StoredChatSession[] = sessions.map((session) => ({
    ...session,
    messages: session.messages.map((msg) => ({
      ...msg,
      timestamp: msg.timestamp.toISOString(),
    })),
  }));
  return JSON.stringify(serialized);
}

/**
 * Derive a title from the first user query
 */
function deriveTitle(messages: ChatMessage[]): string {
  const firstUserMessage = messages.find(
    (msg) => msg.role === "user" && msg.type === "query"
  );
  if (firstUserMessage) {
    // Truncate to 50 chars max
    const content = firstUserMessage.content;
    return content.length > 50 ? content.slice(0, 47) + "..." : content;
  }
  return "New conversation";
}

/**
 * Hook for managing chat history persistence
 */
export function useChatHistory(): UseChatHistoryResult {
  const [sessions, setSessions] = useState<ChatSession[]>(() =>
    parseStoredSessions()
  );
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Persist sessions to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(CHAT_HISTORY_KEY, serializeSessions(sessions));
  }, [sessions]);

  /**
   * Save current messages to a session
   * Creates a new session if sessionId is not provided
   */
  const saveSession = useCallback(
    (
      messages: ChatMessage[],
      project: string | null,
      sessionId?: string
    ): string => {
      const now = new Date().toISOString();
      const id = sessionId ?? generateSessionId();
      const title = deriveTitle(messages);

      setSessions((prev) => {
        // Check if session already exists
        const existingIndex = prev.findIndex((s) => s.id === id);

        if (existingIndex >= 0) {
          // Update existing session
          const updated = [...prev];
          updated[existingIndex] = {
            ...updated[existingIndex],
            title,
            messages,
            project,
            updatedAt: now,
          };
          return updated;
        }

        // Create new session
        const newSession: ChatSession = {
          id,
          title,
          messages,
          project,
          createdAt: now,
          updatedAt: now,
        };

        // Add to beginning of list, limit total sessions
        const updated = [newSession, ...prev].slice(0, MAX_SESSIONS);
        return updated;
      });

      setCurrentSessionId(id);
      return id;
    },
    []
  );

  /**
   * Load a session by ID
   */
  const loadSession = useCallback(
    (sessionId: string): ChatSession | null => {
      const session = sessions.find((s) => s.id === sessionId);
      if (session) {
        setCurrentSessionId(sessionId);
      }
      return session ?? null;
    },
    [sessions]
  );

  /**
   * Delete a session by ID
   */
  const deleteSession = useCallback((sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    setCurrentSessionId((current) =>
      current === sessionId ? null : current
    );
  }, []);

  /**
   * Clear all sessions
   */
  const clearAllSessions = useCallback(() => {
    setSessions([]);
    setCurrentSessionId(null);
  }, []);

  /**
   * Start a new session (clears current session ID)
   */
  const startNewSession = useCallback(() => {
    setCurrentSessionId(null);
  }, []);

  return {
    sessions,
    currentSessionId,
    saveSession,
    loadSession,
    deleteSession,
    clearAllSessions,
    startNewSession,
    setCurrentSessionId,
  };
}

export default useChatHistory;
