/**
 * Monitoring Module - Centralized exports
 *
 * Provides unified access to all monitoring components:
 * - HealthMonitor: Service health polling
 * - AlertManager: Multi-channel alerting
 * - RecoveryEngine: Self-healing actions
 */

export {
  HealthMonitor,
  createESSHealthMonitor,
  type HealthStatus,
  type ServiceHealth,
  type ServiceConfig,
  type AlertThresholds,
  type HealthMonitorConfig,
  type HealthCheckResult,
} from "./HealthMonitor.js";

export {
  AlertManager,
  createAlertManagerFromEnv,
  loadAlertConfig,
  type AlertChannel,
  type AlertSeverity,
  type Alert,
  type EmailConfig,
  type SlackConfig,
  type WebhookConfig,
  type AlertManagerConfig,
} from "./AlertManager.js";

export {
  RecoveryEngine,
  createESSRecoveryEngine,
  type RecoveryAction,
  type RecoveryRule,
  type RecoveryAttempt,
  type ContainerMapping,
  type RecoveryEngineConfig,
} from "./RecoveryEngine.js";

export {
  metrics,
  metricsHandler,
  metricsMiddleware,
  register,
} from "./metrics.js";
