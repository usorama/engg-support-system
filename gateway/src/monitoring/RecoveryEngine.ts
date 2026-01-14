/**
 * Recovery Engine - Self-Healing Service Recovery
 *
 * Executes automated recovery actions when services fail.
 * Supports container restarts, cache clearing, and reconnection attempts.
 * Tracks recovery attempts to prevent infinite loops.
 */

import { exec } from "child_process";
import { promisify } from "util";
import type { Redis } from "ioredis";
import type { ServiceHealth } from "./HealthMonitor.js";
import type { AlertManager, Alert } from "./AlertManager.js";

const execAsync = promisify(exec);

// ============================================================================
// Types
// ============================================================================

/**
 * Recovery action types
 */
export type RecoveryAction =
  | "restart_container"
  | "clear_cache"
  | "reconnect"
  | "escalate"
  | "noop";

/**
 * Recovery rule definition
 */
export interface RecoveryRule {
  /** Service name pattern (exact or wildcard) */
  service: string;
  /** Condition to trigger recovery */
  condition: "consecutive_failures" | "high_latency" | "error_pattern";
  /** Threshold value for condition */
  threshold: number;
  /** Action to take */
  action: RecoveryAction;
  /** Maximum recovery attempts before escalation */
  maxAttempts: number;
  /** Error pattern (for error_pattern condition) */
  errorPattern?: string;
}

/**
 * Recovery attempt record
 */
export interface RecoveryAttempt {
  /** Service name */
  service: string;
  /** Action taken */
  action: RecoveryAction;
  /** Timestamp */
  timestamp: string;
  /** Whether recovery succeeded */
  success: boolean;
  /** Error message if failed */
  error?: string | undefined;
  /** Attempt number */
  attemptNumber: number;
}

/**
 * Service container mapping
 */
export interface ContainerMapping {
  /** Service name */
  service: string;
  /** Docker container name */
  containerName: string;
  /** Docker compose service name */
  composeService?: string;
}

/**
 * Recovery engine configuration
 */
export interface RecoveryEngineConfig {
  /** Recovery rules */
  rules?: RecoveryRule[] | undefined;
  /** Container mappings */
  containers?: ContainerMapping[] | undefined;
  /** Max total attempts per service per hour */
  maxAttemptsPerHour?: number | undefined;
  /** Cooldown between recovery attempts (ms) */
  cooldown?: number | undefined;
  /** Redis client for cache operations */
  redis?: Redis | undefined;
  /** Alert manager for escalation */
  alertManager?: AlertManager | undefined;
  /** Docker compose file path */
  composeFile?: string | undefined;
}

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_RULES: RecoveryRule[] = [
  {
    service: "neo4j",
    condition: "consecutive_failures",
    threshold: 5,
    action: "restart_container",
    maxAttempts: 3,
  },
  {
    service: "qdrant",
    condition: "consecutive_failures",
    threshold: 5,
    action: "restart_container",
    maxAttempts: 3,
  },
  {
    service: "redis",
    condition: "consecutive_failures",
    threshold: 3,
    action: "restart_container",
    maxAttempts: 2,
  },
  {
    service: "ollama",
    condition: "consecutive_failures",
    threshold: 5,
    action: "restart_container",
    maxAttempts: 3,
  },
  {
    service: "gateway",
    condition: "high_latency",
    threshold: 10000,
    action: "clear_cache",
    maxAttempts: 1,
  },
];

const DEFAULT_CONTAINERS: ContainerMapping[] = [
  { service: "neo4j", containerName: "ess-neo4j", composeService: "neo4j" },
  { service: "qdrant", containerName: "ess-qdrant", composeService: "qdrant" },
  { service: "redis", containerName: "ess-redis", composeService: "redis" },
  { service: "ollama", containerName: "ess-ollama", composeService: "ollama" },
  { service: "gateway", containerName: "ess-gateway", composeService: "gateway" },
];

// ============================================================================
// Recovery Engine
// ============================================================================

/**
 * Recovery Engine Service
 *
 * Executes self-healing actions for failing services.
 */
export class RecoveryEngine {
  private rules: RecoveryRule[];
  private containers: Map<string, ContainerMapping>;
  private recoveryAttempts: Map<string, RecoveryAttempt[]>;
  private maxAttemptsPerHour: number;
  private cooldown: number;
  private lastRecovery: Map<string, number>;
  private redis: Redis | null;
  private alertManager: AlertManager | null;
  private composeFile: string;

  constructor(config: RecoveryEngineConfig = {}) {
    this.rules = config.rules ?? DEFAULT_RULES;
    this.containers = new Map(
      (config.containers ?? DEFAULT_CONTAINERS).map((c) => [c.service, c])
    );
    this.recoveryAttempts = new Map();
    this.maxAttemptsPerHour = config.maxAttemptsPerHour ?? 5;
    this.cooldown = config.cooldown ?? 60000; // 1 minute default
    this.lastRecovery = new Map();
    this.redis = config.redis ?? null;
    this.alertManager = config.alertManager ?? null;
    this.composeFile = config.composeFile ?? "/home/devuser/docker-compose.prod.yml";
  }

  /**
   * Set alert manager for escalation
   */
  setAlertManager(alertManager: AlertManager): void {
    this.alertManager = alertManager;
  }

  /**
   * Set Redis client for cache operations
   */
  setRedis(redis: Redis): void {
    this.redis = redis;
  }

  /**
   * Evaluate service health and execute recovery if needed
   */
  async evaluateAndRecover(health: ServiceHealth): Promise<RecoveryAttempt | null> {
    // Find matching rule
    const rule = this.findMatchingRule(health);
    if (!rule) {
      return null;
    }

    // Check cooldown
    const lastTime = this.lastRecovery.get(health.service);
    if (lastTime && Date.now() - lastTime < this.cooldown) {
      console.log(`[RecoveryEngine] Skipping ${health.service} (cooldown)`);
      return null;
    }

    // Check attempt limits
    const attempts = this.getRecentAttempts(health.service);
    if (attempts.length >= this.maxAttemptsPerHour) {
      console.log(`[RecoveryEngine] ${health.service} exceeded max attempts, escalating`);
      await this.escalate(health, attempts);
      return null;
    }

    // Check max attempts for this rule
    const ruleAttempts = attempts.filter((a) => a.action === rule.action);
    if (ruleAttempts.length >= rule.maxAttempts) {
      console.log(`[RecoveryEngine] ${health.service} exceeded max ${rule.action} attempts`);
      return null;
    }

    // Execute recovery
    return this.executeRecovery(health.service, rule.action);
  }

  /**
   * Find rule matching service health
   */
  private findMatchingRule(health: ServiceHealth): RecoveryRule | null {
    for (const rule of this.rules) {
      // Check service match
      if (rule.service !== health.service && rule.service !== "*") {
        continue;
      }

      // Check condition
      switch (rule.condition) {
        case "consecutive_failures":
          if (health.consecutiveFailures >= rule.threshold) {
            return rule;
          }
          break;

        case "high_latency":
          if (health.latency >= rule.threshold) {
            return rule;
          }
          break;

        case "error_pattern":
          if (
            rule.errorPattern &&
            health.lastError?.includes(rule.errorPattern)
          ) {
            return rule;
          }
          break;
      }
    }

    return null;
  }

  /**
   * Get recent recovery attempts for a service (last hour)
   */
  private getRecentAttempts(service: string): RecoveryAttempt[] {
    const attempts = this.recoveryAttempts.get(service) ?? [];
    const oneHourAgo = Date.now() - 3600000;

    return attempts.filter(
      (a) => new Date(a.timestamp).getTime() > oneHourAgo
    );
  }

  /**
   * Execute recovery action
   */
  async executeRecovery(
    service: string,
    action: RecoveryAction
  ): Promise<RecoveryAttempt> {
    const attempts = this.getRecentAttempts(service);
    const attemptNumber = attempts.length + 1;

    console.log(`[RecoveryEngine] Executing ${action} for ${service} (attempt ${attemptNumber})`);

    let success = false;
    let error: string | undefined;

    try {
      switch (action) {
        case "restart_container":
          success = await this.restartContainer(service);
          break;

        case "clear_cache":
          success = await this.clearCache(service);
          break;

        case "reconnect":
          success = await this.reconnect(service);
          break;

        case "escalate":
          await this.escalate({ service } as ServiceHealth, attempts);
          success = true;
          break;

        case "noop":
          success = true;
          break;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "Unknown error";
      console.error(`[RecoveryEngine] ${action} failed for ${service}:`, error);
    }

    // Record attempt
    const attempt: RecoveryAttempt = {
      service,
      action,
      timestamp: new Date().toISOString(),
      success,
      attemptNumber,
    };
    if (error) {
      attempt.error = error;
    }

    // Store attempt
    const serviceAttempts = this.recoveryAttempts.get(service) ?? [];
    serviceAttempts.push(attempt);
    this.recoveryAttempts.set(service, serviceAttempts);

    // Update last recovery time
    this.lastRecovery.set(service, Date.now());

    return attempt;
  }

  /**
   * Restart container via Docker
   */
  private async restartContainer(service: string): Promise<boolean> {
    const container = this.containers.get(service);
    if (!container) {
      console.error(`[RecoveryEngine] No container mapping for ${service}`);
      return false;
    }

    try {
      // Try docker restart first
      console.log(`[RecoveryEngine] Restarting container: ${container.containerName}`);
      await execAsync(`docker restart ${container.containerName}`, {
        timeout: 60000,
      });

      // Wait for container to be healthy
      await this.waitForContainerHealth(container.containerName);

      console.log(`[RecoveryEngine] Successfully restarted ${container.containerName}`);
      return true;
    } catch (err) {
      // If simple restart fails, try compose up
      if (container.composeService) {
        try {
          console.log(`[RecoveryEngine] Trying docker compose up for ${container.composeService}`);
          await execAsync(
            `docker compose -f ${this.composeFile} up -d --force-recreate ${container.composeService}`,
            { timeout: 120000 }
          );
          return true;
        } catch (composeErr) {
          console.error(`[RecoveryEngine] Docker compose failed:`, composeErr);
        }
      }
      throw err;
    }
  }

  /**
   * Wait for container to become healthy
   */
  private async waitForContainerHealth(
    containerName: string,
    timeout = 30000
  ): Promise<boolean> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      try {
        const { stdout } = await execAsync(
          `docker inspect --format='{{.State.Health.Status}}' ${containerName}`
        );

        if (stdout.trim() === "healthy") {
          return true;
        }

        // Also accept running if no healthcheck defined
        const { stdout: status } = await execAsync(
          `docker inspect --format='{{.State.Status}}' ${containerName}`
        );

        if (status.trim() === "running" && stdout.trim() === "") {
          return true;
        }
      } catch {
        // Container not ready yet
      }

      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    return false;
  }

  /**
   * Clear cache for a service
   */
  private async clearCache(service: string): Promise<boolean> {
    if (!this.redis) {
      console.warn("[RecoveryEngine] No Redis client for cache clearing");
      return false;
    }

    try {
      // Clear service-specific cache keys
      const pattern = `${service}:*`;
      const keys = await this.redis.keys(pattern);

      if (keys.length > 0) {
        await this.redis.del(...keys);
        console.log(`[RecoveryEngine] Cleared ${keys.length} cache keys for ${service}`);
      }

      // Also clear general monitoring cache
      const monitoringKeys = await this.redis.keys(`monitoring:${service}:*`);
      if (monitoringKeys.length > 0) {
        await this.redis.del(...monitoringKeys);
      }

      return true;
    } catch (err) {
      console.error(`[RecoveryEngine] Cache clear failed:`, err);
      return false;
    }
  }

  /**
   * Attempt to reconnect to a service
   */
  private async reconnect(service: string): Promise<boolean> {
    // This is a placeholder - actual reconnection logic depends on the service
    // In practice, this might trigger connection pool refresh, etc.
    console.log(`[RecoveryEngine] Reconnect requested for ${service}`);

    // For Redis, we can ping to test connection
    if (service === "redis" && this.redis) {
      try {
        await this.redis.ping();
        return true;
      } catch {
        return false;
      }
    }

    // For other services, consider this a noop
    return true;
  }

  /**
   * Escalate to human intervention
   */
  private async escalate(
    health: ServiceHealth,
    attempts: RecoveryAttempt[]
  ): Promise<void> {
    console.error(`[RecoveryEngine] ESCALATION: ${health.service} requires manual intervention`);

    if (this.alertManager) {
      const alert: Alert = {
        id: `escalation-${health.service}-${Date.now()}`,
        service: health.service,
        severity: "critical",
        message: `🚨 ESCALATION: ${health.service.toUpperCase()} requires manual intervention!\n\nRecovery attempts exhausted (${attempts.length} attempts in last hour).\n\nLast error: ${health.lastError ?? "Unknown"}\n\nPlease investigate immediately.`,
        timestamp: new Date().toISOString(),
        acknowledged: false,
        healthData: health,
      };

      // Clear cooldown for escalation alerts
      this.alertManager.clearCooldown(health.service);
      await this.alertManager.send(alert);
    }
  }

  /**
   * Get recovery history for a service
   */
  getRecoveryHistory(service?: string): RecoveryAttempt[] {
    if (service) {
      return this.recoveryAttempts.get(service) ?? [];
    }

    // Return all attempts
    const allAttempts: RecoveryAttempt[] = [];
    for (const attempts of this.recoveryAttempts.values()) {
      allAttempts.push(...attempts);
    }
    return allAttempts.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  /**
   * Clear recovery history
   */
  clearHistory(service?: string): void {
    if (service) {
      this.recoveryAttempts.delete(service);
      this.lastRecovery.delete(service);
    } else {
      this.recoveryAttempts.clear();
      this.lastRecovery.clear();
    }
  }

  /**
   * Add custom recovery rule
   */
  addRule(rule: RecoveryRule): void {
    this.rules.push(rule);
  }

  /**
   * Update container mapping
   */
  setContainerMapping(mapping: ContainerMapping): void {
    this.containers.set(mapping.service, mapping);
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * Create RecoveryEngine with ESS defaults
 */
export function createESSRecoveryEngine(
  redis?: Redis,
  alertManager?: AlertManager,
  composeFile?: string
): RecoveryEngine {
  return new RecoveryEngine({
    redis,
    alertManager,
    composeFile: composeFile ?? "/home/devuser/docker-compose.prod.yml",
    maxAttemptsPerHour: 5,
    cooldown: 60000,
  });
}
