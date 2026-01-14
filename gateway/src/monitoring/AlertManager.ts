/**
 * Alert Manager - Multi-Channel Alert Routing
 *
 * Routes alerts to configured channels (email, Slack, webhook, log).
 * Implements cooldown to prevent alert fatigue from repeated notifications.
 */

import * as fs from "fs";
import * as path from "path";
import type { ServiceHealth } from "./HealthMonitor.js";

// ============================================================================
// Types
// ============================================================================

/**
 * Alert notification channels
 */
export type AlertChannel = "email" | "slack" | "webhook" | "log";

/**
 * Alert severity levels
 */
export type AlertSeverity = "info" | "warning" | "critical";

/**
 * Individual alert record
 */
export interface Alert {
  /** Unique alert ID */
  id: string;
  /** Service that triggered the alert */
  service: string;
  /** Alert severity */
  severity: AlertSeverity;
  /** Alert message */
  message: string;
  /** Alert timestamp */
  timestamp: string;
  /** Whether alert has been acknowledged */
  acknowledged: boolean;
  /** Service health data at time of alert */
  healthData?: ServiceHealth;
}

/**
 * Email configuration
 */
export interface EmailConfig {
  /** SMTP host */
  smtp: string;
  /** SMTP port */
  port: number;
  /** Sender email */
  from: string;
  /** Recipient emails */
  to: string[];
  /** SMTP auth user */
  user?: string | undefined;
  /** SMTP auth password */
  password?: string | undefined;
  /** Use TLS */
  secure?: boolean | undefined;
}

/**
 * Slack configuration
 */
export interface SlackConfig {
  /** Webhook URL */
  webhookUrl: string;
  /** Channel override (optional) */
  channel?: string | undefined;
  /** Bot username */
  username?: string | undefined;
}

/**
 * Webhook configuration
 */
export interface WebhookConfig {
  /** Webhook URL */
  url: string;
  /** HTTP method */
  method?: "POST" | "PUT" | undefined;
  /** Custom headers */
  headers?: Record<string, string> | undefined;
}

/**
 * Alert manager configuration
 */
export interface AlertManagerConfig {
  /** Enabled channels */
  channels: AlertChannel[];
  /** Email configuration */
  email?: EmailConfig | undefined;
  /** Slack configuration */
  slack?: SlackConfig | undefined;
  /** Webhook configuration */
  webhook?: WebhookConfig | undefined;
  /** Cooldown between duplicate alerts (ms) */
  cooldown?: number | undefined;
  /** Max alerts to retain in history */
  maxHistory?: number | undefined;
}

// ============================================================================
// Alert Manager
// ============================================================================

/**
 * Alert Manager Service
 *
 * Routes alerts to multiple channels with cooldown protection.
 */
export class AlertManager {
  private config: AlertManagerConfig;
  private lastAlerts: Map<string, number>;
  private alertHistory: Alert[];
  private cooldown: number;
  private maxHistory: number;

  constructor(config: AlertManagerConfig) {
    this.config = config;
    this.lastAlerts = new Map();
    this.alertHistory = [];
    this.cooldown = config.cooldown ?? 300000; // 5 minutes default
    this.maxHistory = config.maxHistory ?? 1000;
  }

  /**
   * Create alert from service health
   */
  createAlert(health: ServiceHealth, severity?: AlertSeverity): Alert {
    const alertSeverity = severity ?? this.determineSeverity(health);
    const message = this.formatAlertMessage(health, alertSeverity);

    return {
      id: `alert-${health.service}-${Date.now()}`,
      service: health.service,
      severity: alertSeverity,
      message,
      timestamp: new Date().toISOString(),
      acknowledged: false,
      healthData: health,
    };
  }

  /**
   * Determine alert severity from health data
   */
  private determineSeverity(health: ServiceHealth): AlertSeverity {
    if (health.status === "unhealthy" && health.consecutiveFailures >= 5) {
      return "critical";
    }
    if (health.status === "unhealthy" || health.consecutiveFailures >= 3) {
      return "warning";
    }
    return "info";
  }

  /**
   * Format alert message
   */
  private formatAlertMessage(health: ServiceHealth, severity: AlertSeverity): string {
    const severityEmoji = {
      critical: "🚨",
      warning: "⚠️",
      info: "ℹ️",
    };

    let message = `${severityEmoji[severity]} [ESS] ${health.service.toUpperCase()} is ${health.status}`;

    if (health.consecutiveFailures > 0) {
      message += ` (${health.consecutiveFailures} consecutive failures)`;
    }

    if (health.lastError) {
      message += `\nError: ${health.lastError}`;
    }

    if (health.latency > 0) {
      message += `\nLatency: ${health.latency}ms`;
    }

    return message;
  }

  /**
   * Send alert to all configured channels
   */
  async send(alert: Alert): Promise<void> {
    // Check cooldown
    const alertKey = `${alert.service}-${alert.severity}`;
    const lastSent = this.lastAlerts.get(alertKey);

    if (lastSent && Date.now() - lastSent < this.cooldown) {
      console.log(`[AlertManager] Skipping alert (cooldown): ${alertKey}`);
      return;
    }

    // Update last sent time
    this.lastAlerts.set(alertKey, Date.now());

    // Add to history
    this.alertHistory.push(alert);
    if (this.alertHistory.length > this.maxHistory) {
      this.alertHistory.shift();
    }

    // Send to all channels
    const sendPromises: Promise<void>[] = [];

    for (const channel of this.config.channels) {
      switch (channel) {
        case "email":
          if (this.config.email) {
            sendPromises.push(this.sendEmail(alert));
          }
          break;
        case "slack":
          if (this.config.slack) {
            sendPromises.push(this.sendSlack(alert));
          }
          break;
        case "webhook":
          if (this.config.webhook) {
            sendPromises.push(this.sendWebhook(alert));
          }
          break;
        case "log":
          sendPromises.push(this.sendLog(alert));
          break;
      }
    }

    await Promise.allSettled(sendPromises);
  }

  /**
   * Send multiple alerts (batch)
   */
  async sendBatch(alerts: Alert[]): Promise<void> {
    for (const alert of alerts) {
      await this.send(alert);
    }
  }

  /**
   * Send alert via email using nodemailer
   */
  private async sendEmail(alert: Alert): Promise<void> {
    if (!this.config.email) return;

    try {
      // Dynamic import nodemailer (optional dependency)
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const nodemailer = await import("nodemailer" as string) as {
        createTransport: (options: unknown) => {
          sendMail: (options: unknown) => Promise<void>;
        };
      };

      const transporter = nodemailer.createTransport({
        host: this.config.email.smtp,
        port: this.config.email.port,
        secure: this.config.email.secure ?? false,
        auth: this.config.email.user
          ? {
              user: this.config.email.user,
              pass: this.config.email.password,
            }
          : undefined,
      });

      const subject = `[ESS Alert] ${alert.severity.toUpperCase()}: ${alert.service}`;

      await transporter.sendMail({
        from: this.config.email.from,
        to: this.config.email.to.join(", "),
        subject,
        text: alert.message,
        html: this.formatEmailHtml(alert),
      });

      console.log(`[AlertManager] Email sent for ${alert.service}`);
    } catch (error) {
      console.error("[AlertManager] Email send failed:", error);
    }
  }

  /**
   * Format alert as HTML email
   */
  private formatEmailHtml(alert: Alert): string {
    const severityColors = {
      critical: "#dc3545",
      warning: "#ffc107",
      info: "#17a2b8",
    };

    return `
      <div style="font-family: sans-serif; max-width: 600px;">
        <div style="background: ${severityColors[alert.severity]}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
          <h2 style="margin: 0;">${alert.severity.toUpperCase()}: ${alert.service}</h2>
        </div>
        <div style="border: 1px solid #ddd; border-top: none; padding: 15px; border-radius: 0 0 5px 5px;">
          <p style="white-space: pre-wrap;">${alert.message}</p>
          <hr style="border: none; border-top: 1px solid #eee;">
          <p style="color: #666; font-size: 12px;">
            Alert ID: ${alert.id}<br>
            Time: ${alert.timestamp}
          </p>
        </div>
      </div>
    `;
  }

  /**
   * Send alert to Slack webhook
   */
  private async sendSlack(alert: Alert): Promise<void> {
    if (!this.config.slack?.webhookUrl) return;

    try {
      const severityColors = {
        critical: "#dc3545",
        warning: "#ffc107",
        info: "#17a2b8",
      };

      const payload = {
        username: this.config.slack.username ?? "ESS Alert Bot",
        channel: this.config.slack.channel,
        attachments: [
          {
            color: severityColors[alert.severity],
            title: `${alert.severity.toUpperCase()}: ${alert.service}`,
            text: alert.message,
            fields: [
              {
                title: "Service",
                value: alert.service,
                short: true,
              },
              {
                title: "Severity",
                value: alert.severity,
                short: true,
              },
              ...(alert.healthData
                ? [
                    {
                      title: "Failures",
                      value: String(alert.healthData.consecutiveFailures),
                      short: true,
                    },
                    {
                      title: "Latency",
                      value: `${alert.healthData.latency}ms`,
                      short: true,
                    },
                  ]
                : []),
            ],
            footer: "ESS Monitoring",
            ts: Math.floor(Date.now() / 1000).toString(),
          },
        ],
      };

      const response = await fetch(this.config.slack.webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Slack webhook returned ${response.status}`);
      }

      console.log(`[AlertManager] Slack alert sent for ${alert.service}`);
    } catch (error) {
      console.error("[AlertManager] Slack send failed:", error);
    }
  }

  /**
   * Send alert to generic webhook
   */
  private async sendWebhook(alert: Alert): Promise<void> {
    if (!this.config.webhook?.url) return;

    try {
      const response = await fetch(this.config.webhook.url, {
        method: this.config.webhook.method ?? "POST",
        headers: {
          "Content-Type": "application/json",
          ...this.config.webhook.headers,
        },
        body: JSON.stringify(alert),
      });

      if (!response.ok) {
        throw new Error(`Webhook returned ${response.status}`);
      }

      console.log(`[AlertManager] Webhook sent for ${alert.service}`);
    } catch (error) {
      console.error("[AlertManager] Webhook send failed:", error);
    }
  }

  /**
   * Log alert to console/file
   */
  private async sendLog(alert: Alert): Promise<void> {
    const logMessage = `[ALERT] ${alert.timestamp} | ${alert.severity.toUpperCase()} | ${alert.service} | ${alert.message.replace(/\n/g, " ")}`;

    // Console log with color
    switch (alert.severity) {
      case "critical":
        console.error(logMessage);
        break;
      case "warning":
        console.warn(logMessage);
        break;
      default:
        console.log(logMessage);
    }
  }

  /**
   * Acknowledge an alert
   */
  acknowledge(alertId: string): boolean {
    const alert = this.alertHistory.find((a) => a.id === alertId);
    if (alert) {
      alert.acknowledged = true;
      return true;
    }
    return false;
  }

  /**
   * Get alert history
   */
  getHistory(limit?: number): Alert[] {
    const history = [...this.alertHistory].reverse();
    return limit ? history.slice(0, limit) : history;
  }

  /**
   * Get unacknowledged alerts
   */
  getUnacknowledged(): Alert[] {
    return this.alertHistory.filter((a) => !a.acknowledged);
  }

  /**
   * Clear cooldown for a service (allow immediate re-alert)
   */
  clearCooldown(service: string): void {
    for (const key of this.lastAlerts.keys()) {
      if (key.startsWith(`${service}-`)) {
        this.lastAlerts.delete(key);
      }
    }
  }

  /**
   * Clear all cooldowns
   */
  clearAllCooldowns(): void {
    this.lastAlerts.clear();
  }

  /**
   * Send recovery notification
   */
  async sendRecoveryNotification(service: string): Promise<void> {
    const alert: Alert = {
      id: `recovery-${service}-${Date.now()}`,
      service,
      severity: "info",
      message: `✅ [ESS] ${service.toUpperCase()} has recovered and is now healthy`,
      timestamp: new Date().toISOString(),
      acknowledged: false,
    };

    // Clear cooldown for this service to ensure recovery message goes through
    this.clearCooldown(service);

    await this.send(alert);
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * Create AlertManager from environment configuration
 */
export function createAlertManagerFromEnv(): AlertManager {
  const channels: AlertChannel[] = ["log"]; // Always log

  // Email configuration
  let emailConfig: EmailConfig | undefined;
  if (process.env.ALERT_EMAIL_ENABLED === "true") {
    channels.push("email");
    const cfg: EmailConfig = {
      smtp: process.env.ALERT_EMAIL_SMTP ?? "smtp.gmail.com",
      port: parseInt(process.env.ALERT_EMAIL_PORT ?? "587", 10),
      from: process.env.ALERT_EMAIL_FROM ?? "alerts@localhost",
      to: (process.env.ALERT_EMAIL_TO ?? "").split(",").filter(Boolean),
      secure: process.env.ALERT_EMAIL_SECURE === "true",
    };
    if (process.env.ALERT_EMAIL_USER) {
      cfg.user = process.env.ALERT_EMAIL_USER;
    }
    if (process.env.ALERT_EMAIL_PASSWORD) {
      cfg.password = process.env.ALERT_EMAIL_PASSWORD;
    }
    emailConfig = cfg;
  }

  // Slack configuration
  let slackConfig: SlackConfig | undefined;
  if (process.env.ALERT_SLACK_ENABLED === "true" && process.env.ALERT_SLACK_WEBHOOK) {
    channels.push("slack");
    const cfg: SlackConfig = {
      webhookUrl: process.env.ALERT_SLACK_WEBHOOK,
      username: process.env.ALERT_SLACK_USERNAME ?? "ESS Alert Bot",
    };
    if (process.env.ALERT_SLACK_CHANNEL) {
      cfg.channel = process.env.ALERT_SLACK_CHANNEL;
    }
    slackConfig = cfg;
  }

  // Webhook configuration
  let webhookConfig: WebhookConfig | undefined;
  if (process.env.ALERT_WEBHOOK_URL) {
    channels.push("webhook");
    webhookConfig = {
      url: process.env.ALERT_WEBHOOK_URL,
    };
  }

  const cooldown = parseInt(process.env.ALERT_COOLDOWN ?? "300000", 10);

  return new AlertManager({
    channels,
    email: emailConfig,
    slack: slackConfig,
    webhook: webhookConfig,
    cooldown,
  });
}

/**
 * Load AlertManager configuration from JSON file
 */
export function loadAlertConfig(configPath?: string): AlertManagerConfig {
  const filePath = configPath ?? path.join(
    path.dirname(new URL(import.meta.url).pathname),
    "../config/alerts.json"
  );

  try {
    const data = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(data) as AlertManagerConfig;
  } catch {
    // Return minimal default config
    return {
      channels: ["log"],
      cooldown: 300000,
    };
  }
}
