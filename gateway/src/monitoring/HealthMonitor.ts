/**
 * Health Monitor - Continuous Service Health Checking
 *
 * Polls all ESS services at regular intervals and tracks health status.
 * Integrates with AlertManager for notifications and RecoveryEngine for self-healing.
 */

import { Redis } from "ioredis";

// ============================================================================
// Types
// ============================================================================

/**
 * Service health status
 */
export type HealthStatus = "healthy" | "degraded" | "unhealthy";

/**
 * Individual service health record
 */
export interface ServiceHealth {
  /** Service name */
  service: string;
  /** Current health status */
  status: HealthStatus;
  /** Response latency in ms */
  latency: number;
  /** Last check timestamp */
  lastCheck: string;
  /** Consecutive failure count */
  consecutiveFailures: number;
  /** Last error message (if any) */
  lastError?: string | undefined;
  /** HTTP status code from health check */
  httpStatus?: number | undefined;
}

/**
 * Service configuration for monitoring
 */
export interface ServiceConfig {
  /** Service name */
  name: string;
  /** Health check URL */
  url: string;
  /** Check timeout in ms */
  timeout?: number;
  /** Custom health check function (optional) */
  customCheck?: () => Promise<boolean>;
}

/**
 * Alert thresholds configuration
 */
export interface AlertThresholds {
  /** Consecutive failures before alerting */
  consecutiveFailures: number;
  /** Latency warning threshold (ms) */
  latencyWarning: number;
  /** Latency critical threshold (ms) */
  latencyCritical: number;
}

/**
 * Health monitor configuration
 */
export interface HealthMonitorConfig {
  /** Services to monitor */
  services: ServiceConfig[];
  /** Alert thresholds */
  thresholds?: AlertThresholds | undefined;
  /** Check interval in ms */
  checkInterval?: number | undefined;
  /** Redis for storing health history */
  redis?: Redis | undefined;
}

/**
 * Health check result with alert info
 */
export interface HealthCheckResult {
  /** All service health records */
  services: ServiceHealth[];
  /** Overall system status */
  overallStatus: HealthStatus;
  /** Services requiring alerts */
  alertRequired: ServiceHealth[];
  /** Services requiring recovery */
  recoveryRequired: ServiceHealth[];
  /** Timestamp */
  timestamp: string;
}

// ============================================================================
// Health Monitor
// ============================================================================

/**
 * Health Monitor Service
 *
 * Continuously monitors ESS services and tracks health history.
 */
export class HealthMonitor {
  private serviceConfigs: ServiceConfig[];
  private healthHistory: Map<string, ServiceHealth>;
  private thresholds: AlertThresholds;
  private checkInterval: number;
  private redis: Redis | null;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private onAlert?: (services: ServiceHealth[]) => void;
  private onRecovery?: (services: ServiceHealth[]) => void;

  constructor(config: HealthMonitorConfig) {
    this.serviceConfigs = config.services;
    this.healthHistory = new Map();
    this.thresholds = config.thresholds ?? {
      consecutiveFailures: 3,
      latencyWarning: 5000,
      latencyCritical: 10000,
    };
    this.checkInterval = config.checkInterval ?? 30000;
    this.redis = config.redis ?? null;

    // Initialize health history
    for (const service of this.serviceConfigs) {
      this.healthHistory.set(service.name, {
        service: service.name,
        status: "healthy",
        latency: 0,
        lastCheck: new Date().toISOString(),
        consecutiveFailures: 0,
      });
    }
  }

  /**
   * Set alert callback
   */
  setAlertCallback(callback: (services: ServiceHealth[]) => void): void {
    this.onAlert = callback;
  }

  /**
   * Set recovery callback
   */
  setRecoveryCallback(callback: (services: ServiceHealth[]) => void): void {
    this.onRecovery = callback;
  }

  /**
   * Start continuous monitoring
   */
  start(): void {
    if (this.intervalId) {
      console.warn("[HealthMonitor] Already running");
      return;
    }

    console.log(`[HealthMonitor] Starting with ${this.checkInterval}ms interval`);

    // Run immediately
    this.checkAll().catch((err) => {
      console.error("[HealthMonitor] Initial check failed:", err);
    });

    // Schedule periodic checks
    this.intervalId = setInterval(() => {
      this.checkAll().catch((err) => {
        console.error("[HealthMonitor] Check failed:", err);
      });
    }, this.checkInterval);
  }

  /**
   * Stop monitoring
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      console.log("[HealthMonitor] Stopped");
    }
  }

  /**
   * Check all services
   */
  async checkAll(): Promise<HealthCheckResult> {
    const timestamp = new Date().toISOString();
    const services: ServiceHealth[] = [];
    const alertRequired: ServiceHealth[] = [];
    const recoveryRequired: ServiceHealth[] = [];

    // Check all services in parallel
    const checks = this.serviceConfigs.map((config) =>
      this.checkService(config)
    );
    const results = await Promise.allSettled(checks);

    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      const config = this.serviceConfigs[i];

      if (!config || !result) continue;

      let health: ServiceHealth;

      if (result.status === "fulfilled") {
        health = result.value;
      } else {
        // Promise rejected - service check failed completely
        const previous = this.healthHistory.get(config.name);
        const reason = result.reason;
        health = {
          service: config.name,
          status: "unhealthy",
          latency: -1,
          lastCheck: timestamp,
          consecutiveFailures: (previous?.consecutiveFailures ?? 0) + 1,
          lastError: reason instanceof Error ? reason.message : "Unknown error",
        };
      }

      // Update history
      this.healthHistory.set(config.name, health);
      services.push(health);

      // Check if alert required
      if (this.isAlertRequired(health)) {
        alertRequired.push(health);
      }

      // Check if recovery required
      if (this.isRecoveryRequired(health)) {
        recoveryRequired.push(health);
      }
    }

    // Store in Redis if available
    if (this.redis) {
      await this.storeHealthHistory(services);
    }

    // Calculate overall status
    const overallStatus = this.calculateOverallStatus(services);

    // Trigger callbacks
    if (alertRequired.length > 0 && this.onAlert) {
      this.onAlert(alertRequired);
    }
    if (recoveryRequired.length > 0 && this.onRecovery) {
      this.onRecovery(recoveryRequired);
    }

    return {
      services,
      overallStatus,
      alertRequired,
      recoveryRequired,
      timestamp,
    };
  }

  /**
   * Check a single service
   */
  async checkService(config: ServiceConfig): Promise<ServiceHealth> {
    const startTime = Date.now();
    const previous = this.healthHistory.get(config.name);
    const timeout = config.timeout ?? 10000;

    try {
      // Use custom check if provided
      if (config.customCheck) {
        const isHealthy = await config.customCheck();
        const latency = Date.now() - startTime;

        const health: ServiceHealth = {
          service: config.name,
          status: isHealthy ? "healthy" : "unhealthy",
          latency,
          lastCheck: new Date().toISOString(),
          consecutiveFailures: isHealthy ? 0 : (previous?.consecutiveFailures ?? 0) + 1,
        };
        if (!isHealthy) {
          health.lastError = "Custom health check failed";
        }
        return health;
      }

      // HTTP health check
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(config.url, {
        method: "GET",
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const latency = Date.now() - startTime;
      const isHealthy = response.ok;
      const isDegraded = response.status === 207;

      let status: HealthStatus;
      if (isHealthy) {
        status = isDegraded ? "degraded" : "healthy";
      } else {
        status = "unhealthy";
      }

      const health: ServiceHealth = {
        service: config.name,
        status,
        latency,
        lastCheck: new Date().toISOString(),
        consecutiveFailures: isHealthy || isDegraded ? 0 : (previous?.consecutiveFailures ?? 0) + 1,
        httpStatus: response.status,
      };
      if (!isHealthy && !isDegraded) {
        health.lastError = `HTTP ${response.status}`;
      }
      return health;
    } catch (error) {
      const latency = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : "Unknown error";

      return {
        service: config.name,
        status: "unhealthy",
        latency,
        lastCheck: new Date().toISOString(),
        consecutiveFailures: (previous?.consecutiveFailures ?? 0) + 1,
        lastError: errorMessage.includes("abort") ? "Timeout" : errorMessage,
      };
    }
  }

  /**
   * Check if alert is required for a service
   */
  isAlertRequired(health: ServiceHealth): boolean {
    // Alert on consecutive failures
    if (health.consecutiveFailures >= this.thresholds.consecutiveFailures) {
      return true;
    }

    // Alert on critical latency
    if (health.latency >= this.thresholds.latencyCritical) {
      return true;
    }

    return false;
  }

  /**
   * Check if recovery is required for a service
   */
  isRecoveryRequired(health: ServiceHealth): boolean {
    // Recovery on consecutive failures beyond threshold
    return health.consecutiveFailures >= this.thresholds.consecutiveFailures + 2;
  }

  /**
   * Calculate overall system status
   */
  private calculateOverallStatus(services: ServiceHealth[]): HealthStatus {
    const statuses = services.map((s) => s.status);

    if (statuses.every((s) => s === "healthy")) {
      return "healthy";
    }

    if (statuses.some((s) => s === "unhealthy")) {
      return "unhealthy";
    }

    return "degraded";
  }

  /**
   * Store health history in Redis
   */
  private async storeHealthHistory(services: ServiceHealth[]): Promise<void> {
    if (!this.redis) return;

    try {
      const key = "monitoring:health:latest";
      const historyKey = `monitoring:health:history:${Date.now()}`;

      // Store latest status
      await this.redis.set(key, JSON.stringify(services), "EX", 300);

      // Store in history (keep 1 hour)
      await this.redis.set(historyKey, JSON.stringify(services), "EX", 3600);
    } catch (err) {
      console.warn("[HealthMonitor] Failed to store in Redis:", err);
    }
  }

  /**
   * Get current health status
   */
  getHealthStatus(): ServiceHealth[] {
    return Array.from(this.healthHistory.values());
  }

  /**
   * Get health history from Redis
   */
  async getHealthHistory(limit = 100): Promise<ServiceHealth[][]> {
    if (!this.redis) return [];

    try {
      const keys = await this.redis.keys("monitoring:health:history:*");
      const sortedKeys = keys.sort().slice(-limit);

      if (sortedKeys.length === 0) return [];

      const values = await this.redis.mget(sortedKeys);
      return values
        .filter((v): v is string => v !== null)
        .map((v) => JSON.parse(v) as ServiceHealth[]);
    } catch (err) {
      console.warn("[HealthMonitor] Failed to get history:", err);
      return [];
    }
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * Create a HealthMonitor configured for ESS services
 */
export function createESSHealthMonitor(
  redis?: Redis,
  checkInterval = 30000
): HealthMonitor {
  const qdrantUrl = process.env.QDRANT_URL ?? "http://localhost:6333";
  const neo4jUri = process.env.NEO4J_URI ?? "bolt://localhost:7687";
  const neo4jHttpUrl = neo4jUri.replace("bolt://", "http://").replace(":7687", ":7474").replace(":7688", ":7475");
  const ollamaUrl = process.env.OLLAMA_URL ?? "http://localhost:11434";
  const redisHost = process.env.REDIS_HOST ?? "localhost";
  const redisPort = process.env.REDIS_PORT ?? "6379";

  const services: ServiceConfig[] = [
    {
      name: "gateway",
      url: "http://localhost:3001/health",
      timeout: 10000,
    },
    {
      name: "qdrant",
      url: qdrantUrl,
      timeout: 10000,
    },
    {
      name: "neo4j",
      url: neo4jHttpUrl,
      timeout: 10000,
    },
    {
      name: "ollama",
      url: `${ollamaUrl}/api/tags`,
      timeout: 10000,
    },
    {
      name: "redis",
      url: `http://${redisHost}:${redisPort}`,
      timeout: 5000,
      customCheck: async () => {
        // Redis doesn't have HTTP endpoint, use TCP check via ioredis
        if (redis) {
          try {
            await redis.ping();
            return true;
          } catch {
            return false;
          }
        }
        return true; // Assume healthy if no Redis client
      },
    },
  ];

  return new HealthMonitor({
    services,
    checkInterval,
    redis,
    thresholds: {
      consecutiveFailures: 3,
      latencyWarning: 5000,
      latencyCritical: 10000,
    },
  });
}
