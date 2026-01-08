/**
 * Conversation Manager - Manages conversation state
 *
 * Tracks active conversations, collects context,
 * and enforces round limits for Phase 0b.
 */

/**
 * Conversation message in history
 */
export interface ConversationMessage {
  /** Round number */
  round: number;

  /** Message type */
  type: "query" | "clarification" | "answer" | "response";

  /** Message content */
  content: unknown;

  /** Timestamp */
  timestamp: number;
}

/**
 * Conversation state
 */
export interface ConversationState {
  /** Unique conversation ID (UUID v4) */
  conversationId: string;

  /** Original query that started conversation */
  originalQuery: string;

  /** Current round number */
  round: number;

  /** Maximum rounds allowed */
  maxRounds: number;

  /** Current conversation phase */
  phase: "analyzing" | "clarifying" | "executing" | "completed";

  /** Collected context from user */
  collectedContext: Record<string, unknown>;

  /** Message history */
  history: ConversationMessage[];

  /** Start timestamp */
  startTime: number;
}

/**
 * Conversation Manager class
 */
class ConversationManager {
  private activeConversations = new Map<string, ConversationState>();

  /**
   * Start a new conversation
   */
  startConversation(query: string): ConversationState {
    const conversationId = this.generateUUID();
    const state: ConversationState = {
      conversationId,
      originalQuery: query,
      round: 1,
      maxRounds: 2, // Phase 0b: 2 rounds max
      phase: "analyzing",
      collectedContext: {},
      history: [],
      startTime: Date.now(),
    };

    this.activeConversations.set(conversationId, state);
    return state;
  }

  /**
   * Advance to next round
   */
  advanceRound(conversationId: string): ConversationState | null {
    const state = this.activeConversations.get(conversationId);
    if (!state) return null;

    if (state.round >= state.maxRounds) {
      // Force completion
      state.phase = "completed";
      return state;
    }

    state.round++;
    return state;
  }

  /**
   * Add context to conversation
   */
  addContext(conversationId: string, key: string, value: unknown): void {
    const state = this.activeConversations.get(conversationId);
    if (state) {
      state.collectedContext[key] = value;
    }
  }

  /**
   * End conversation
   */
  endConversation(conversationId: string): ConversationState | null {
    const state = this.activeConversations.get(conversationId);
    if (!state) return null;

    state.phase = "completed";
    this.activeConversations.delete(conversationId);
    return state;
  }

  /**
   * Get conversation state
   */
  getConversation(conversationId: string): ConversationState | undefined {
    return this.activeConversations.get(conversationId);
  }

  /**
   * Generate UUID v4
   */
  private generateUUID(): string {
    // Simple UUID v4 generation
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }
}

// Export singleton instance
export const conversationManager = new ConversationManager();
