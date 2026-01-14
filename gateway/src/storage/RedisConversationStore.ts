/**
 * Redis Conversation Store - Persistent state storage
 *
 * Stores conversation state in Redis for persistence
 * and distributed support. Falls back to in-memory
 * storage if Redis is unavailable.
 */

import { Redis } from "ioredis";
import type { ConversationState } from "../agents/ConversationManager.js";

/**
 * Redis Conversation Store
 *
 * Provides persistent storage for conversation state with:
 * - Redis backend for persistence
 * - 1-hour TTL for automatic cleanup
 * - In-memory fallback when Redis unavailable
 * - Graceful error handling
 */
export class RedisConversationStore {
  private redis: Redis | null = null;
  private fallback = new Map<string, ConversationState>();
  private keyPrefix = "conversation:";
  private ttlSeconds = 3600; // 1 hour
  private redisAvailable = false;
  private initPromise: Promise<void>;

  constructor() {
    // Start Redis connection and store promise
    this.initPromise = this.initializeRedis().catch(() => {
      // Errors handled in initializeRedis
    });
  }

  /**
   * Initialize Redis connection with fallback handling
   * Runs asynchronously in background
   */
  private async initializeRedis(): Promise<void> {
    const redisHost = process.env.REDIS_HOST || "localhost";
    const redisPort = parseInt(process.env.REDIS_PORT || "6379", 10);

    try {
      this.redis = new Redis({
        host: redisHost,
        port: redisPort,
        retryStrategy: (times) => {
          if (times > 3) {
            // After 3 retries, stop trying
            return null;
          }
          return Math.min(times * 100, 2000); // Exponential backoff
        },
        maxRetriesPerRequest: 3,
        enableReadyCheck: false, // Don't wait for ready check
        lazyConnect: false, // Connect immediately
      });

      // Wait for connection to be ready with timeout
      const redisClient = this.redis;
      await Promise.race([
        new Promise<void>((resolve, reject) => {
          if (redisClient) {
            redisClient.once("ready", () => resolve());
            redisClient.once("error", (err) => reject(err));
          } else {
            reject(new Error("Redis client not initialized"));
          }
        }),
        new Promise<void>((_, reject) =>
          setTimeout(() => reject(new Error("Redis connection timeout")), 2000),
        ),
      ]);

      this.redisAvailable = true;
      console.log("[RedisConversationStore] Redis connection established");
    } catch (err) {
      this.redisAvailable = false;
      this.redis = null;
      console.warn(
        "[RedisConversationStore] Redis unavailable, using in-memory fallback",
      );
    }
  }

  /**
   * Check if Redis is available
   * Waits for initialization to complete first
   */
  private async checkRedisAvailable(): Promise<boolean> {
    // Wait for initialization to complete
    await this.initPromise;

    if (!this.redis || this.redisAvailable === false) {
      return false;
    }

    try {
      await this.redis.ping();
      return true;
    } catch {
      this.redisAvailable = false;
      return false;
    }
  }

  /**
   * Save conversation state to Redis or fallback
   */
  async save(state: ConversationState): Promise<void> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + state.conversationId;
        const serialized = JSON.stringify(state);
        await this.redis.setex(key, this.ttlSeconds, serialized);
        return;
      } catch (err) {
        console.warn(
          "[RedisConversationStore] Redis save failed, using fallback:",
          (err as Error).message,
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory
    this.fallback.set(state.conversationId, state);
  }

  /**
   * Load conversation state from Redis or fallback
   */
  async load(
    conversationId: string,
  ): Promise<ConversationState | null> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + conversationId;
        const data = await this.redis.get(key);

        if (!data) {
          return null;
        }

        try {
          return JSON.parse(data) as ConversationState;
        } catch {
          return null;
        }
      } catch (err) {
        console.warn(
          "[RedisConversationStore] Redis load failed, using fallback:",
          (err as Error).message,
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory - return null if not found
    return this.fallback.get(conversationId) ?? null;
  }

  /**
   * Delete conversation from Redis or fallback
   */
  async delete(conversationId: string): Promise<void> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + conversationId;
        await this.redis.del(key);
      } catch (err) {
        console.warn(
          "[RedisConversationStore] Redis delete failed, using fallback:",
          (err as Error).message,
        );
        this.redisAvailable = false;
      }
    }

    // Always remove from fallback
    this.fallback.delete(conversationId);
  }

  /**
   * Get all active conversations from Redis or fallback
   */
  async getAllActive(): Promise<ConversationState[]> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const keys = await this.redis.keys(this.keyPrefix + "*");

        if (keys.length === 0) {
          return [];
        }

        const values = await this.redis.mget(keys);
        const states: ConversationState[] = [];

        for (const value of values) {
          if (value) {
            try {
              states.push(JSON.parse(value) as ConversationState);
            } catch {
              // Skip invalid JSON
              continue;
            }
          }
        }

        return states;
      } catch (err) {
        console.warn(
          "[RedisConversationStore] Redis getAllActive failed, using fallback:",
          (err as Error).message,
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory
    return Array.from(this.fallback.values());
  }

  /**
   * Check if conversation exists in Redis or fallback
   */
  async exists(conversationId: string): Promise<boolean> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + conversationId;
        const result = await this.redis.exists(key);
        return result === 1;
      } catch (err) {
        console.warn(
          "[RedisConversationStore] Redis exists failed, using fallback:",
          (err as Error).message,
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory
    return this.fallback.has(conversationId);
  }

  /**
   * Get TTL for conversation (Redis only)
   */
  async getTTL(conversationId: string): Promise<number> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + conversationId;
        return await this.redis.ttl(key);
      } catch (err) {
        console.warn(
          "[RedisConversationStore] Redis getTTL failed:",
          (err as Error).message,
        );
        return -1;
      }
    }

    // Fallback doesn't support TTL
    return -1;
  }

  /**
   * Close Redis connection
   */
  async close(): Promise<void> {
    if (this.redis) {
      try {
        await this.redis.quit();
      } catch {
        // Ignore close errors
      }
    }
    this.fallback.clear();
  }
}
