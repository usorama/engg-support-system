/**
 * Prometheus Metrics Endpoint
 *
 * Exposes application metrics for monitoring and alerting.
 */

import {
  Registry,
  Counter,
  Histogram,
  Gauge,
  collectDefaultMetrics,
} from "prom-client";
import type { Request, Response } from "express";
import { defaultRegistry } from "../utils/CircuitBreaker.js";

// Create a custom registry
const register = new Registry();

// Collect default Node.js metrics
collectDefaultMetrics({ register });

// ============================================================================
// CUSTOM METRICS
// ============================================================================

// Request metrics
const httpRequestsTotal = new Counter({
  name: "ess_http_requests_total",
  help: "Total number of HTTP requests",
  labelNames: ["method", "path", "status"],
  registers: [register],
});

const httpRequestDuration = new Histogram({
  name: "ess_http_request_duration_seconds",
  help: "HTTP request duration in seconds",
  labelNames: ["method", "path"],
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60],
  registers: [register],
});

// Query metrics
const queriesTotal = new Counter({
  name: "ess_queries_total",
  help: "Total number of queries processed",
  labelNames: ["type", "project", "status"],
  registers: [register],
});

const queryDuration = new Histogram({
  name: "ess_query_duration_seconds",
  help: "Query processing duration in seconds",
  labelNames: ["type"],
  buckets: [0.5, 1, 2, 5, 10, 30, 60],
  registers: [register],
});

const queryConfidence = new Histogram({
  name: "ess_query_confidence",
  help: "Distribution of query confidence scores",
  buckets: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
  registers: [register],
});

// Conversation metrics
const conversationsActive = new Gauge({
  name: "ess_conversations_active",
  help: "Number of active conversations",
  registers: [register],
});

const conversationsTotal = new Counter({
  name: "ess_conversations_total",
  help: "Total number of conversations started",
  labelNames: ["outcome"],
  registers: [register],
});

// Service health metrics
const serviceHealth = new Gauge({
  name: "ess_service_health",
  help: "Service health status (1=ok, 0=error)",
  labelNames: ["service"],
  registers: [register],
});

// Circuit breaker metrics
const circuitBreakerState = new Gauge({
  name: "ess_circuit_breaker_state",
  help: "Circuit breaker state (0=closed, 1=halfOpen, 2=open)",
  labelNames: ["name"],
  registers: [register],
});

const circuitBreakerRequests = new Counter({
  name: "ess_circuit_breaker_requests_total",
  help: "Circuit breaker request counts",
  labelNames: ["name", "result"],
  registers: [register],
});

// Rate limiting metrics
const rateLimitHits = new Counter({
  name: "ess_rate_limit_hits_total",
  help: "Number of rate limit hits",
  labelNames: ["path"],
  registers: [register],
});

// ============================================================================
// METRIC RECORDING FUNCTIONS
// ============================================================================

export const metrics = {
  // HTTP request tracking
  recordRequest(method: string, path: string, status: number, duration: number) {
    httpRequestsTotal.labels(method, path, String(status)).inc();
    httpRequestDuration.labels(method, path).observe(duration / 1000);
  },

  // Query tracking
  recordQuery(type: string, project: string, status: string, duration: number) {
    queriesTotal.labels(type, project, status).inc();
    queryDuration.labels(type).observe(duration / 1000);
  },

  recordQueryConfidence(confidence: number) {
    queryConfidence.observe(confidence);
  },

  // Conversation tracking
  setActiveConversations(count: number) {
    conversationsActive.set(count);
  },

  recordConversation(outcome: "completed" | "aborted" | "timeout") {
    conversationsTotal.labels(outcome).inc();
  },

  // Service health tracking
  setServiceHealth(service: string, healthy: boolean) {
    serviceHealth.labels(service).set(healthy ? 1 : 0);
  },

  // Rate limit tracking
  recordRateLimitHit(path: string) {
    rateLimitHits.labels(path).inc();
  },

  // Update circuit breaker metrics from stats
  updateCircuitBreakerMetrics() {
    const stats = defaultRegistry.getAllStats();
    for (const [name, stat] of Object.entries(stats)) {
      const stateValue =
        stat.state === "closed" ? 0 : stat.state === "half_open" ? 1 : 2;
      circuitBreakerState.labels(name).set(stateValue);
    }
  },
};

// ============================================================================
// EXPRESS MIDDLEWARE
// ============================================================================

/**
 * Middleware to track request metrics
 */
export function metricsMiddleware(
  req: Request,
  res: Response,
  next: () => void
) {
  const start = Date.now();

  res.on("finish", () => {
    const duration = Date.now() - start;
    const path = req.route?.path || req.path;
    metrics.recordRequest(req.method, path, res.statusCode, duration);
  });

  next();
}

/**
 * Metrics endpoint handler
 */
export async function metricsHandler(
  _req: Request,
  res: Response
): Promise<void> {
  // Update circuit breaker metrics before serving
  metrics.updateCircuitBreakerMetrics();

  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
}

export { register };
export default metrics;
