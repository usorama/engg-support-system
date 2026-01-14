/**
 * Query Metrics Store - Logs and tracks query performance for confidence tuning
 *
 * Stores query metrics in Redis for analysis and feedback collection.
 * Falls back to in-memory storage if Redis is unavailable.
 *
 * Used for deterministic confidence threshold tuning based on feedback.
 */

import { Redis } from "ioredis";

// ============================================================================
// Types
// ============================================================================

/**
 * Feedback type from rad-engineer or users
 */
export type FeedbackType = "useful" | "not_useful" | "partial";

/**
 * Query metric record
 */
export interface QueryMetric {
  /** Unique request identifier */
  requestId: string;
  /** Timestamp of the query */
  timestamp: string;
  /** Original query text */
  query: string;
  /** Hash of query for deduplication */
  queryHash: string;

  // Input metrics
  /** Number of semantic matches from Qdrant */
  semanticMatchCount: number;
  /** Number of structural relationships from Neo4j */
  structuralMatchCount: number;
  /** Average semantic score (0-1) */
  avgSemanticScore: number;

  // Output metrics
  /** Calculated confidence score (0-1) */
  confidence: number;
  /** Length of generated answer */
  answerLength: number;
  /** Number of citations in answer */
  citationCount: number;
  /** Total latency in ms */
  latencyMs: number;

  // Feedback (populated later via updateFeedback)
  /** User/rad-engineer feedback */
  feedback?: FeedbackType;
  /** When feedback was recorded */
  feedbackTimestamp?: string;
  /** Optional comment with feedback */
  feedbackComment?: string;
}

/**
 * Summary statistics for metrics
 */
export interface MetricsSummary {
  /** Total queries logged */
  totalQueries: number;
  /** Queries with feedback */
  queriesWithFeedback: number;
  /** Average confidence score */
  avgConfidence: number;
  /** Average latency in ms */
  avgLatencyMs: number;
  /** Feedback breakdown */
  feedbackCounts: {
    useful: number;
    not_useful: number;
    partial: number;
  };
}

// ============================================================================
// Query Metrics Store
// ============================================================================

/**
 * Query Metrics Store
 *
 * Provides persistent storage for query metrics with:
 * - Redis backend for persistence
 * - 7-day TTL for automatic cleanup (configurable)
 * - In-memory fallback when Redis unavailable
 * - Graceful error handling
 */
export class QueryMetricsStore {
  private redis: Redis | null = null;
  private fallback = new Map<string, QueryMetric>();
  private keyPrefix = "metrics:query:";
  private feedbackIndexKey = "metrics:feedback:pending";
  private ttlSeconds: number;
  private redisAvailable = false;
  private initPromise: Promise<void>;

  constructor(ttlDays = 7) {
    this.ttlSeconds = ttlDays * 24 * 60 * 60; // Convert days to seconds
    // Start Redis connection and store promise
    this.initPromise = this.initializeRedis().catch(() => {
      // Errors handled in initializeRedis
    });
  }

  /**
   * Initialize Redis connection with fallback handling
   */
  private async initializeRedis(): Promise<void> {
    const redisHost = process.env.REDIS_HOST || "localhost";
    const redisPort = parseInt(process.env.REDIS_PORT || "6379", 10);

    try {
      this.redis = new Redis({
        host: redisHost,
        port: redisPort,
        retryStrategy: (times) => {
          if (times > 3) return null;
          return Math.min(times * 100, 2000);
        },
        maxRetriesPerRequest: 3,
        enableReadyCheck: false,
        lazyConnect: false,
      });

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
          setTimeout(() => reject(new Error("Redis connection timeout")), 2000)
        ),
      ]);

      this.redisAvailable = true;
      console.log("[QueryMetricsStore] Redis connection established");
    } catch {
      this.redisAvailable = false;
      this.redis = null;
      console.warn(
        "[QueryMetricsStore] Redis unavailable, using in-memory fallback"
      );
    }
  }

  /**
   * Check if Redis is available
   */
  private async checkRedisAvailable(): Promise<boolean> {
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
   * Generate a simple hash for query deduplication
   */
  private hashQuery(query: string): string {
    let hash = 0;
    for (let i = 0; i < query.length; i++) {
      const char = query.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16);
  }

  /**
   * Log a new query metric
   */
  async log(metric: Omit<QueryMetric, "queryHash">): Promise<void> {
    const fullMetric: QueryMetric = {
      ...metric,
      queryHash: this.hashQuery(metric.query),
    };

    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + metric.requestId;
        const serialized = JSON.stringify(fullMetric);
        await this.redis.setex(key, this.ttlSeconds, serialized);

        // Add to feedback pending index if no feedback yet
        if (!fullMetric.feedback) {
          await this.redis.zadd(
            this.feedbackIndexKey,
            Date.now(),
            metric.requestId
          );
        }
        return;
      } catch (err) {
        console.warn(
          "[QueryMetricsStore] Redis log failed, using fallback:",
          (err as Error).message
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory
    this.fallback.set(metric.requestId, fullMetric);
  }

  /**
   * Update feedback for a query
   */
  async updateFeedback(
    requestId: string,
    feedback: FeedbackType,
    comment?: string
  ): Promise<boolean> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + requestId;
        const data = await this.redis.get(key);

        if (!data) {
          return false;
        }

        const metric = JSON.parse(data) as QueryMetric;
        metric.feedback = feedback;
        metric.feedbackTimestamp = new Date().toISOString();
        if (comment) {
          metric.feedbackComment = comment;
        }

        // Update the record
        const ttl = await this.redis.ttl(key);
        await this.redis.setex(key, ttl > 0 ? ttl : this.ttlSeconds, JSON.stringify(metric));

        // Remove from pending feedback index
        await this.redis.zrem(this.feedbackIndexKey, requestId);

        return true;
      } catch (err) {
        console.warn(
          "[QueryMetricsStore] Redis updateFeedback failed:",
          (err as Error).message
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory
    const metric = this.fallback.get(requestId);
    if (!metric) return false;

    metric.feedback = feedback;
    metric.feedbackTimestamp = new Date().toISOString();
    if (comment) {
      metric.feedbackComment = comment;
    }
    return true;
  }

  /**
   * Get a specific metric by requestId
   */
  async get(requestId: string): Promise<QueryMetric | null> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const key = this.keyPrefix + requestId;
        const data = await this.redis.get(key);
        if (!data) return null;
        return JSON.parse(data) as QueryMetric;
      } catch (err) {
        console.warn(
          "[QueryMetricsStore] Redis get failed:",
          (err as Error).message
        );
        this.redisAvailable = false;
      }
    }

    return this.fallback.get(requestId) ?? null;
  }

  /**
   * Get metrics since a specific date
   */
  async getMetricsSince(since: Date, limit = 1000): Promise<QueryMetric[]> {
    const sinceTime = since.getTime();
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        const keys = await this.redis.keys(this.keyPrefix + "*");
        if (keys.length === 0) return [];

        const values = await this.redis.mget(keys);
        const metrics: QueryMetric[] = [];

        for (const value of values) {
          if (value && metrics.length < limit) {
            try {
              const metric = JSON.parse(value) as QueryMetric;
              const metricTime = new Date(metric.timestamp).getTime();
              if (metricTime >= sinceTime) {
                metrics.push(metric);
              }
            } catch {
              continue;
            }
          }
        }

        // Sort by timestamp descending
        return metrics.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );
      } catch (err) {
        console.warn(
          "[QueryMetricsStore] Redis getMetricsSince failed:",
          (err as Error).message
        );
        this.redisAvailable = false;
      }
    }

    // Fallback to in-memory
    return Array.from(this.fallback.values())
      .filter((m) => new Date(m.timestamp).getTime() >= sinceTime)
      .sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      .slice(0, limit);
  }

  /**
   * Get metrics with feedback for tuning analysis
   */
  async getMetricsWithFeedback(limit = 500): Promise<QueryMetric[]> {
    const metrics = await this.getMetricsSince(
      new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      limit * 2
    );
    return metrics.filter((m) => m.feedback !== undefined).slice(0, limit);
  }

  /**
   * Get requests pending feedback
   */
  async getFeedbackPending(limit = 100): Promise<string[]> {
    const isAvailable = await this.checkRedisAvailable();

    if (isAvailable && this.redis) {
      try {
        // Get oldest pending feedback requests
        const requestIds = await this.redis.zrange(
          this.feedbackIndexKey,
          0,
          limit - 1
        );
        return requestIds;
      } catch (err) {
        console.warn(
          "[QueryMetricsStore] Redis getFeedbackPending failed:",
          (err as Error).message
        );
        this.redisAvailable = false;
      }
    }

    // Fallback: return requests without feedback
    return Array.from(this.fallback.values())
      .filter((m) => !m.feedback)
      .slice(0, limit)
      .map((m) => m.requestId);
  }

  /**
   * Get summary statistics
   */
  async getSummary(sinceDays = 7): Promise<MetricsSummary> {
    const since = new Date(Date.now() - sinceDays * 24 * 60 * 60 * 1000);
    const metrics = await this.getMetricsSince(since);

    const withFeedback = metrics.filter((m) => m.feedback !== undefined);

    const feedbackCounts = {
      useful: withFeedback.filter((m) => m.feedback === "useful").length,
      not_useful: withFeedback.filter((m) => m.feedback === "not_useful").length,
      partial: withFeedback.filter((m) => m.feedback === "partial").length,
    };

    return {
      totalQueries: metrics.length,
      queriesWithFeedback: withFeedback.length,
      avgConfidence:
        metrics.length > 0
          ? metrics.reduce((sum, m) => sum + m.confidence, 0) / metrics.length
          : 0,
      avgLatencyMs:
        metrics.length > 0
          ? metrics.reduce((sum, m) => sum + m.latencyMs, 0) / metrics.length
          : 0,
      feedbackCounts,
    };
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

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a QueryMetricsStore with default settings
 */
export function createQueryMetricsStore(ttlDays = 7): QueryMetricsStore {
  return new QueryMetricsStore(ttlDays);
}
