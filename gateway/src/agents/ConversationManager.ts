/**
 * Conversation Manager - Manages conversation state
 *
 * Phase 1: Redis Integration
 * - Persistent storage via RedisConversationStore
 * - Local cache for fast access
 * - 3 rounds max (increased from 2)
 * - Async methods for Redis operations
 */

import { RedisConversationStore } from "../storage/RedisConversationStore.js";

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
 * Phase 1: Redis-backed persistence with local caching
 */
export class ConversationManager {
  private redisStore: RedisConversationStore;
  private localCache = new Map<string, ConversationState>();

  constructor() {
    this.redisStore = new RedisConversationStore();
  }

  /**
   * Start a new conversation
   * - Creates conversation state
   * - Saves to Redis for persistence
   * - Caches locally for fast access
   */
  async startConversation(query: string): Promise<ConversationState> {
    const conversationId = this.generateUUID();
    const state: ConversationState = {
      conversationId,
      originalQuery: query,
      round: 1,
      maxRounds: 3, // Phase 1: 3 rounds max
      phase: "analyzing",
      collectedContext: {},
      history: [],
      startTime: Date.now(),
    };

    // Save to Redis for persistence
    await this.redisStore.save(state);

    // Cache locally for fast access
    this.localCache.set(conversationId, state);

    return state;
  }

  /**
   * Advance to next round
   * - Updates round in state
   * - Persists to Redis
   * - Updates local cache
   */
  async advanceRound(
    conversationId: string,
  ): Promise<ConversationState | undefined> {
    // Try local cache first
    let state: ConversationState | undefined | null =
      this.localCache.get(conversationId);

    // Fallback to Redis if not in cache
    if (!state) {
      state = await this.redisStore.load(conversationId);
      if (!state) return undefined;
    }

    if (state.round >= state.maxRounds) {
      // Force completion
      state.phase = "completed";
      await this.redisStore.save(state);
      this.localCache.set(conversationId, state);
      return state;
    }

    state.round++;
    await this.redisStore.save(state);
    this.localCache.set(conversationId, state);
    return state;
  }

  /**
   * Add context to conversation
   * - Updates collected context
   * - Persists to Redis
   * - Updates local cache
   */
  async addContext(
    conversationId: string,
    key: string,
    value: unknown,
  ): Promise<void> {
    // Try local cache first
    let state: ConversationState | undefined | null =
      this.localCache.get(conversationId);

    // Fallback to Redis if not in cache
    if (!state) {
      state = await this.redisStore.load(conversationId);
      if (!state) return;
    }

    state.collectedContext[key] = value;
    await this.redisStore.save(state);
    this.localCache.set(conversationId, state);
  }

  /**
   * End conversation
   * - Marks as completed
   * - Deletes from Redis
   * - Removes from local cache
   */
  async endConversation(
    conversationId: string,
  ): Promise<ConversationState | undefined> {
    // Try local cache first
    let state: ConversationState | undefined | null =
      this.localCache.get(conversationId);

    // Fallback to Redis if not in cache
    if (!state) {
      state = await this.redisStore.load(conversationId);
      if (!state) return undefined;
    }

    state.phase = "completed";
    await this.redisStore.delete(conversationId);
    this.localCache.delete(conversationId);
    return state;
  }

  /**
   * Get conversation state
   * - Returns from local cache if available
   * - Falls back to Redis if not cached
   * - Populates cache on Redis retrieval
   */
  async getConversation(
    conversationId: string,
  ): Promise<ConversationState | undefined> {
    // Check local cache first
    const cached = this.localCache.get(conversationId);
    if (cached) {
      return cached;
    }

    // Fallback to Redis
    const state = await this.redisStore.load(conversationId);
    if (state) {
      // Populate local cache
      this.localCache.set(conversationId, state);
    }

    return state ?? undefined;
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

  /**
   * Clean up resources
   */
  async close(): Promise<void> {
    this.localCache.clear();
    await this.redisStore.close();
  }
}

// Export singleton instance
export const conversationManager = new ConversationManager();
