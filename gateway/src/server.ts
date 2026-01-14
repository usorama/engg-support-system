/**
 * HTTP Gateway Server for Engineering Support System
 *
 * Wraps existing EnggContextAgent in an Express HTTP server
 * for easy integration with external systems like rad-engineer-v2.
 *
 * Endpoints:
 * - GET /health     - Health check for all services
 * - POST /query     - One-shot query to both Qdrant and Neo4j
 * - POST /conversation - Multi-round conversational query
 * - POST /conversation/:id/continue - Continue an existing conversation
 */

import express, { type Request, type Response, type NextFunction } from "express";
import cors from "cors";
import { Redis } from "ioredis";
import { EnggContextAgent, type EnggContextAgentConfig } from "./agents/EnggContextAgent.js";
import { conversationManager } from "./agents/ConversationManager.js";
import { QueryMetricsStore, type FeedbackType } from "./metrics/QueryMetrics.js";
import { createAuthMiddleware } from "./middleware/auth.js";
import { createQueryRateLimiter, createConversationRateLimiter } from "./middleware/rateLimit.js";
import {
  HealthMonitor,
  createESSHealthMonitor,
  AlertManager,
  createAlertManagerFromEnv,
  RecoveryEngine,
  createESSRecoveryEngine,
  type ServiceHealth as MonitoringServiceHealth,
} from "./monitoring/index.js";
import {
  CircuitBreakerRegistry,
  createESSCircuitBreakers,
} from "./utils/CircuitBreaker.js";
import type {
  QueryRequest,
  QueryRequestWithMode,
  ConversationRequest,
  GatewayResponse,
} from "./types/agent-contracts.js";
import * as fs from "fs";
import * as path from "path";

// =============================================================================
// Environment validation - fail fast if required vars missing
// =============================================================================
function requireEnv(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function warnWeakCredential(name: string, value: string): void {
  const weakPatterns = ["password", "123", "test", "secret", "admin", "changeme"];
  const isWeak = weakPatterns.some((p) => value.toLowerCase().includes(p));
  if (isWeak && process.env.NODE_ENV === "production") {
    console.error(`[SECURITY WARNING] ${name} appears to be a weak credential. Change it immediately!`);
  }
}

// Environment configuration with validation
const qdrantConfig: EnggContextAgentConfig["qdrant"] = {
  url: requireEnv("QDRANT_URL", "http://localhost:6333"),
  collection: requireEnv("QDRANT_COLLECTION", "engineering_kb"),
};

// Only add apiKey if it's defined
if (process.env.QDRANT_API_KEY) {
  qdrantConfig.apiKey = process.env.QDRANT_API_KEY;
}

// Neo4j password is required - no fallback to weak default
const neo4jPassword = requireEnv("NEO4J_PASSWORD");
warnWeakCredential("NEO4J_PASSWORD", neo4jPassword);

const config: EnggContextAgentConfig = {
  qdrant: qdrantConfig,
  neo4j: {
    uri: requireEnv("NEO4J_URI", "bolt://localhost:7687"),
    user: requireEnv("NEO4J_USER", "neo4j"),
    password: neo4jPassword,
  },
  ollama: {
    url: requireEnv("OLLAMA_URL", "http://localhost:11434"),
    embedModel: requireEnv("EMBEDDING_MODEL", "nomic-embed-text"),
    synthesisModel: requireEnv("SYNTHESIS_MODEL", "llama3.2"),
  },
};

// Configure synthesis provider (zAI uses OpenAI-compatible API)
const synthesisApiUrl = process.env.SYNTHESIS_API_URL || process.env.ANTHROPIC_BASE_URL;
const synthesisApiKey = process.env.SYNTHESIS_API_KEY || process.env.ANTHROPIC_API_KEY;
const synthesisProvider = process.env.SYNTHESIS_PROVIDER as "ollama" | "anthropic" | "openai" | undefined;

if (synthesisApiUrl && synthesisApiKey) {
  // Auto-detect provider: use "openai" for zAI URLs, otherwise use explicit provider or "anthropic"
  const provider = synthesisProvider ?? (synthesisApiUrl.includes("api.z.ai") ? "openai" : "anthropic");
  config.synthesis = {
    provider,
    baseUrl: synthesisApiUrl,
    apiKey: synthesisApiKey,
    model: process.env.SYNTHESIS_MODEL || process.env.ANTHROPIC_MODEL || "glm-4.7",
    timeout: process.env.SYNTHESIS_TIMEOUT ? parseInt(process.env.SYNTHESIS_TIMEOUT, 10) : 60000,
  };
}

// Initialize agent and metrics store
let agent: EnggContextAgent;
const metricsStore = new QueryMetricsStore(7); // 7-day TTL

// Initialize monitoring components
let healthMonitor: HealthMonitor;
let alertManager: AlertManager;
let recoveryEngine: RecoveryEngine;
let circuitBreakers: CircuitBreakerRegistry;
let monitoringRedis: Redis | null = null;

// Load confidence weights config
function loadConfidenceWeights(): {
  weights: { semanticScore: number; structuralPresence: number; citationCoverage: number };
  thresholds: { high: number; medium: number; low: number };
} {
  try {
    const configPath = new URL("./config/confidence-weights.json", import.meta.url);
    const data = fs.readFileSync(configPath, "utf-8");
    return JSON.parse(data);
  } catch {
    // Return defaults if config not found
    return {
      weights: { semanticScore: 0.7, structuralPresence: 0.1, citationCoverage: 0.2 },
      thresholds: { high: 0.8, medium: 0.5, low: 0.3 },
    };
  }
}

const app = express();
app.use(cors());
app.use(express.json());

// Serve static files from public directory (dashboard, etc.)
const publicDir = path.join(path.dirname(new URL(import.meta.url).pathname), "../public");
app.use(express.static(publicDir));

// Dashboard route
app.get("/dashboard", (_req, res) => {
  res.sendFile(path.join(publicDir, "dashboard.html"));
});

// =============================================================================
// SECURITY MIDDLEWARE
// =============================================================================

// API key authentication (skipped for /health endpoint)
const authMiddleware = createAuthMiddleware({
  excludePaths: ["/health", "/"],
});

// Rate limiting
const queryRateLimiter = createQueryRateLimiter();
const conversationRateLimiter = createConversationRateLimiter();

// Error handling middleware
const asyncHandler = (fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    fn(req, res, next).catch(next);
  };
};

// ============================================================================
// HEALTH CHECK ENDPOINT
// ============================================================================

interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  services: {
    neo4j: ServiceHealth;
    qdrant: ServiceHealth;
    redis: ServiceHealth;
    ollama: ServiceHealth;
  };
}

interface ServiceHealth {
  status: "ok" | "error" | "unknown";
  latency?: number;
  error?: string;
}

app.get("/health", asyncHandler(async (_req: Request, res: Response) => {
  const startTime = Date.now();
  const services: HealthResponse["services"] = {
    neo4j: { status: "unknown" },
    qdrant: { status: "unknown" },
    redis: { status: "unknown" },
    ollama: { status: "unknown" },
  };

  // Check Neo4j
  try {
    const neo4jStart = Date.now();
    const neo4jResponse = await fetch(`${config.neo4j.uri.replace("bolt://", "http://").replace(":7687", ":7474")}`);
    services.neo4j = {
      status: neo4jResponse.ok ? "ok" : "error",
      latency: Date.now() - neo4jStart,
    };
  } catch (error) {
    services.neo4j = {
      status: "error",
      error: error instanceof Error ? error.message : "Connection failed",
    };
  }

  // Check Qdrant
  try {
    const qdrantStart = Date.now();
    const qdrantResponse = await fetch(`${config.qdrant.url}/`);
    services.qdrant = {
      status: qdrantResponse.ok ? "ok" : "error",
      latency: Date.now() - qdrantStart,
    };
  } catch (error) {
    services.qdrant = {
      status: "error",
      error: error instanceof Error ? error.message : "Connection failed",
    };
  }

  // Check Redis
  try {
    const redisUrl = process.env.REDIS_URL ?? "redis://localhost:6380";
    const redisHost = redisUrl.replace("redis://", "").split(":")[0];
    const redisPort = redisUrl.split(":").pop() ?? "6380";

    // Simple TCP check (Redis doesn't have HTTP endpoint)
    // For now, mark as ok if conversation manager initializes
    services.redis = {
      status: conversationManager !== undefined ? "ok" : "error",
    };
  } catch (error) {
    services.redis = {
      status: "error",
      error: error instanceof Error ? error.message : "Connection failed",
    };
  }

  // Check Ollama
  try {
    const ollamaStart = Date.now();
    const ollamaResponse = await fetch(`${config.ollama?.url}/api/tags`);
    if (ollamaResponse.ok) {
      const data = await ollamaResponse.json() as { models?: unknown[] };
      services.ollama = {
        status: "ok",
        latency: Date.now() - ollamaStart,
      };
    } else {
      services.ollama = { status: "error", error: "Ollama not responding" };
    }
  } catch (error) {
    services.ollama = {
      status: "error",
      error: error instanceof Error ? error.message : "Connection failed",
    };
  }

  // Determine overall status
  const serviceStatuses = Object.values(services).map(s => s.status);
  let overallStatus: HealthResponse["status"];

  if (serviceStatuses.every(s => s === "ok")) {
    overallStatus = "healthy";
  } else if (serviceStatuses.some(s => s === "ok")) {
    overallStatus = "degraded";
  } else {
    overallStatus = "unhealthy";
  }

  const response: HealthResponse = {
    status: overallStatus,
    timestamp: new Date().toISOString(),
    services,
  };

  const statusCode = overallStatus === "healthy" ? 200 : overallStatus === "degraded" ? 207 : 503;
  res.status(statusCode).json(response);
}));

// ============================================================================
// QUERY ENDPOINT (One-shot)
// ============================================================================

interface QueryRequestBody {
  query: string;
  project?: string;
  context?: string[];
  mode?: "one-shot" | "conversational";
  /** Synthesis mode: "synthesized" (default) returns intelligent answer, "raw" returns search results only */
  synthesisMode?: "synthesized" | "raw";
}

// Apply auth + rate limiting to query endpoint
app.post("/query", authMiddleware, queryRateLimiter, asyncHandler(async (req: Request, res: Response) => {
  const body = req.body as QueryRequestBody;
  const startTime = Date.now();

  if (!body.query || typeof body.query !== "string") {
    res.status(400).json({
      error: "Missing required field: query",
      message: "Request body must include a 'query' string field",
    });
    return;
  }

  const request: QueryRequestWithMode = {
    query: body.query,
    requestId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    mode: body.mode ?? "one-shot",
    synthesisMode: body.synthesisMode ?? "synthesized", // Default to synthesized mode
    ...(body.project !== undefined && { project: body.project }),
    ...(body.context !== undefined && { context: body.context }),
  };

  const response: GatewayResponse = await agent.query(request);

  // Log metrics for confidence tuning (async, don't block response)
  // Only log for QueryResponse (has results), not ConversationResponse
  const latencyMs = Date.now() - startTime;
  if ("results" in response) {
    const queryResponse = response;
    const matches = queryResponse.results?.semantic?.matches ?? [];
    metricsStore.log({
      requestId: request.requestId,
      timestamp: request.timestamp,
      query: request.query,
      semanticMatchCount: matches.length,
      structuralMatchCount: queryResponse.results?.structural?.relationships?.length ?? 0,
      avgSemanticScore: matches.length > 0
        ? matches.reduce((sum: number, m: { score: number }) => sum + m.score, 0) / matches.length
        : 0,
      confidence: queryResponse.answer?.confidence ?? 0,
      answerLength: queryResponse.answer?.text?.length ?? 0,
      citationCount: queryResponse.answer?.citations?.length ?? 0,
      latencyMs,
    }).catch(err => {
      console.warn("[Metrics] Failed to log query metrics:", err);
    });
  }

  res.json(response);
}));

// ============================================================================
// CONVERSATION ENDPOINTS
// ============================================================================

// Start a new conversation (auth + rate limiting)
app.post("/conversation", authMiddleware, conversationRateLimiter, asyncHandler(async (req: Request, res: Response) => {
  console.log("[DEBUG] POST /conversation hit - starting NEW conversation");
  const body = req.body as QueryRequestBody;

  if (!body.query || typeof body.query !== "string") {
    res.status(400).json({
      error: "Missing required field: query",
      message: "Request body must include a 'query' string field",
    });
    return;
  }

  const request: QueryRequestWithMode = {
    query: body.query,
    requestId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    mode: "conversational",
    synthesisMode: body.synthesisMode ?? "synthesized", // Default to synthesized mode
    ...(body.project !== undefined && { project: body.project }),
    ...(body.context !== undefined && { context: body.context }),
  };

  console.log("[DEBUG] Calling agent.query() with:", JSON.stringify(request));
  const response: GatewayResponse = await agent.query(request);
  console.log("[DEBUG] Response from agent.query():", JSON.stringify(response).slice(0, 500));
  res.json(response);
}));

// Continue an existing conversation
interface ContinueConversationBody {
  answers: Record<string, string>;
}

app.post("/conversation/:id/continue", authMiddleware, conversationRateLimiter, asyncHandler(async (req: Request, res: Response) => {
  console.log("[DEBUG] POST /conversation/:id/continue hit - CONTINUING conversation");
  console.log("[DEBUG] URL params:", req.params);
  console.log("[DEBUG] Full URL:", req.originalUrl);

  const conversationId = req.params.id;
  const body = req.body as ContinueConversationBody;

  if (!conversationId) {
    res.status(400).json({
      error: "Missing conversation ID",
      message: "Conversation ID is required in the URL path",
    });
    return;
  }

  if (!body.answers || typeof body.answers !== "object") {
    res.status(400).json({
      error: "Missing required field: answers",
      message: "Request body must include an 'answers' object",
    });
    return;
  }

  console.log("[DEBUG] Conversation ID from URL:", conversationId);
  console.log("[DEBUG] Answers:", JSON.stringify(body.answers));

  const request: ConversationRequest = {
    conversationId,
    answers: body.answers,
    requestId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  };

  console.log("[DEBUG] Calling agent.continueConversation() with:", JSON.stringify(request));
  const response: GatewayResponse = await agent.continueConversation(request);
  console.log("[DEBUG] Response from agent.continueConversation():", JSON.stringify(response).slice(0, 500));
  res.json(response);
}));

// Abort a conversation (auth required)
app.delete("/conversation/:id", authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  const conversationId = req.params.id;

  if (!conversationId) {
    res.status(400).json({
      error: "Missing conversation ID",
      message: "Conversation ID is required in the URL path",
    });
    return;
  }

  await conversationManager.endConversation(conversationId);
  res.json({
    status: "aborted",
    conversationId,
    timestamp: new Date().toISOString(),
  });
}));

// ============================================================================
// PROJECTS ENDPOINT
// ============================================================================

app.get("/projects", asyncHandler(async (_req: Request, res: Response) => {
  // Query Neo4j for list of projects
  // This is a simplified implementation - the full version would use the Neo4j client
  try {
    const neo4jUri = config.neo4j.uri.replace("bolt://", "http://").replace(":7687", ":7474");

    // For now, return a placeholder - in production, query Neo4j directly
    res.json({
      projects: [],
      message: "Project listing endpoint - use Neo4j browser at http://localhost:7474 for now",
    });
  } catch (error) {
    res.status(500).json({
      error: "Failed to list projects",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
}));

// ============================================================================
// QUEUE STATS ENDPOINT (for LLM request queue monitoring)
// ============================================================================

app.get("/queue/stats", asyncHandler(async (_req: Request, res: Response) => {
  // Placeholder for queue stats - will be implemented with BullMQ queue
  res.json({
    waiting: 0,
    active: 0,
    completed: 0,
    failed: 0,
    message: "Queue stats - LLM request queue not yet implemented",
  });
}));

// ============================================================================
// FEEDBACK ENDPOINT
// ============================================================================

interface FeedbackRequestBody {
  requestId: string;
  feedback: FeedbackType;
  comment?: string;
}

// Feedback requires auth
app.post("/feedback", authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  const body = req.body as FeedbackRequestBody;

  if (!body.requestId || typeof body.requestId !== "string") {
    res.status(400).json({
      error: "Missing required field: requestId",
      message: "Request body must include a 'requestId' string field",
    });
    return;
  }

  if (!body.feedback || !["useful", "not_useful", "partial"].includes(body.feedback)) {
    res.status(400).json({
      error: "Invalid feedback value",
      message: "Feedback must be one of: 'useful', 'not_useful', 'partial'",
    });
    return;
  }

  const success = await metricsStore.updateFeedback(
    body.requestId,
    body.feedback,
    body.comment
  );

  if (!success) {
    res.status(404).json({
      error: "Request not found",
      message: `No query found with requestId: ${body.requestId}`,
    });
    return;
  }

  res.json({
    status: "recorded",
    requestId: body.requestId,
    feedback: body.feedback,
    timestamp: new Date().toISOString(),
  });
}));

// ============================================================================
// ADMIN ENDPOINTS (Metrics & Weights)
// ============================================================================

// Get metrics summary
app.get("/admin/metrics", asyncHandler(async (req: Request, res: Response) => {
  const sinceParam = req.query.since as string | undefined;
  let sinceDays = 7;

  if (sinceParam) {
    // Parse "Xh" for hours, "Xd" for days
    const match = sinceParam.match(/^(\d+)([hd])$/);
    if (match && match[1] && match[2]) {
      const value = parseInt(match[1], 10);
      const unit = match[2];
      sinceDays = unit === "h" ? value / 24 : value;
    }
  }

  const summary = await metricsStore.getSummary(sinceDays);
  res.json(summary);
}));

// Get detailed metrics
app.get("/admin/metrics/details", asyncHandler(async (req: Request, res: Response) => {
  const limitParam = req.query.limit as string | undefined;
  const limit = limitParam ? parseInt(limitParam, 10) : 100;

  const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  const metrics = await metricsStore.getMetricsSince(since, limit);

  res.json({
    count: metrics.length,
    metrics,
  });
}));

// Get current confidence weights
app.get("/admin/weights", asyncHandler(async (_req: Request, res: Response) => {
  const config = loadConfidenceWeights();
  res.json(config);
}));

// Update confidence weights (requires verification)
interface UpdateWeightsBody {
  weights?: { semanticScore?: number; structuralPresence?: number; citationCoverage?: number };
  thresholds?: { high?: number; medium?: number; low?: number };
  verificationToken?: string;
}

app.post("/admin/weights", asyncHandler(async (req: Request, res: Response) => {
  const body = req.body as UpdateWeightsBody;

  // Token-based protection - no weak default in production
  const expectedToken = process.env.ADMIN_TOKEN;
  if (!expectedToken) {
    console.warn("[SECURITY] ADMIN_TOKEN not configured - admin endpoints disabled");
    res.status(503).json({
      error: "Admin endpoints disabled",
      message: "ADMIN_TOKEN environment variable not configured",
    });
    return;
  }
  if (body.verificationToken !== expectedToken) {
    res.status(403).json({
      error: "Unauthorized",
      message: "Invalid or missing verificationToken",
    });
    return;
  }

  try {
    const currentConfig = loadConfidenceWeights();

    // Merge new values with current
    const newConfig = {
      version: (currentConfig as { version?: number }).version ?? 1,
      updatedAt: new Date().toISOString(),
      updatedBy: "admin-api",
      weights: {
        ...currentConfig.weights,
        ...body.weights,
      },
      thresholds: {
        ...currentConfig.thresholds,
        ...body.thresholds,
      },
      behavior: (currentConfig as { behavior?: unknown }).behavior ?? {
        belowLow: "warn",
        belowMedium: "include_raw",
      },
    };

    // Write to config file
    const configPath = new URL("./config/confidence-weights.json", import.meta.url);
    fs.writeFileSync(configPath, JSON.stringify(newConfig, null, 2));

    res.json({
      status: "updated",
      config: newConfig,
    });
  } catch (error) {
    res.status(500).json({
      error: "Failed to update weights",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
}));

// ============================================================================
// PROMETHEUS METRICS ENDPOINT
// ============================================================================

app.get("/metrics", asyncHandler(async (_req: Request, res: Response) => {
  const healthStatus = healthMonitor?.getHealthStatus() ?? [];
  const circuitStats = circuitBreakers?.getAllStats() ?? {};

  // Prometheus format metrics
  let metrics = "";

  // Health status metrics
  metrics += "# HELP ess_health_status Service health status (1=healthy, 0=unhealthy)\n";
  metrics += "# TYPE ess_health_status gauge\n";
  for (const service of healthStatus) {
    const value = service.status === "healthy" ? 1 : service.status === "degraded" ? 0.5 : 0;
    metrics += `ess_health_status{service="${service.service}"} ${value}\n`;
  }

  // Latency metrics
  metrics += "\n# HELP ess_service_latency_ms Service response latency in milliseconds\n";
  metrics += "# TYPE ess_service_latency_ms gauge\n";
  for (const service of healthStatus) {
    if (service.latency >= 0) {
      metrics += `ess_service_latency_ms{service="${service.service}"} ${service.latency}\n`;
    }
  }

  // Consecutive failures
  metrics += "\n# HELP ess_consecutive_failures Number of consecutive health check failures\n";
  metrics += "# TYPE ess_consecutive_failures gauge\n";
  for (const service of healthStatus) {
    metrics += `ess_consecutive_failures{service="${service.service}"} ${service.consecutiveFailures}\n`;
  }

  // Circuit breaker metrics
  metrics += "\n# HELP ess_circuit_state Circuit breaker state (0=closed, 0.5=half_open, 1=open)\n";
  metrics += "# TYPE ess_circuit_state gauge\n";
  for (const [name, stats] of Object.entries(circuitStats)) {
    const value = stats.state === "open" ? 1 : stats.state === "half_open" ? 0.5 : 0;
    metrics += `ess_circuit_state{circuit="${name}"} ${value}\n`;
  }

  metrics += "\n# HELP ess_circuit_total_opens Total times circuit has opened\n";
  metrics += "# TYPE ess_circuit_total_opens counter\n";
  for (const [name, stats] of Object.entries(circuitStats)) {
    metrics += `ess_circuit_total_opens{circuit="${name}"} ${stats.totalOpens}\n`;
  }

  res.set("Content-Type", "text/plain; version=0.0.4");
  res.send(metrics);
}));

// ============================================================================
// MONITORING STATUS ENDPOINTS
// ============================================================================

// Get monitoring health status
app.get("/monitoring/health", asyncHandler(async (_req: Request, res: Response) => {
  if (!healthMonitor) {
    res.status(503).json({
      error: "Monitoring not initialized",
      message: "Health monitoring is not yet available",
    });
    return;
  }

  const healthStatus = healthMonitor.getHealthStatus();
  const circuitStats = circuitBreakers?.getAllStats() ?? {};

  res.json({
    timestamp: new Date().toISOString(),
    services: healthStatus,
    circuits: circuitStats,
    monitoring: {
      enabled: true,
      checkInterval: process.env.HEALTH_CHECK_INTERVAL ?? "30000",
    },
  });
}));

// Get alert history
app.get("/monitoring/alerts", asyncHandler(async (req: Request, res: Response) => {
  if (!alertManager) {
    res.status(503).json({
      error: "Alert manager not initialized",
    });
    return;
  }

  const limitParam = req.query.limit as string | undefined;
  const limit = limitParam ? parseInt(limitParam, 10) : 50;

  const alerts = alertManager.getHistory(limit);
  const unacknowledged = alertManager.getUnacknowledged();

  res.json({
    timestamp: new Date().toISOString(),
    totalAlerts: alerts.length,
    unacknowledgedCount: unacknowledged.length,
    alerts,
  });
}));

// Acknowledge an alert
app.post("/monitoring/alerts/:id/acknowledge", authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  if (!alertManager) {
    res.status(503).json({
      error: "Alert manager not initialized",
    });
    return;
  }

  const alertId = req.params.id;
  if (!alertId) {
    res.status(400).json({ error: "Missing alert ID" });
    return;
  }
  const success = alertManager.acknowledge(alertId);

  if (success) {
    res.json({
      status: "acknowledged",
      alertId,
      timestamp: new Date().toISOString(),
    });
  } else {
    res.status(404).json({
      error: "Alert not found",
      alertId,
    });
  }
}));

// Get recovery history
app.get("/monitoring/recovery", asyncHandler(async (req: Request, res: Response) => {
  if (!recoveryEngine) {
    res.status(503).json({
      error: "Recovery engine not initialized",
    });
    return;
  }

  const service = req.query.service as string | undefined;
  const history = recoveryEngine.getRecoveryHistory(service);

  res.json({
    timestamp: new Date().toISOString(),
    recoveryAttempts: history,
  });
}));

// Get circuit breaker status
app.get("/monitoring/circuits", asyncHandler(async (_req: Request, res: Response) => {
  if (!circuitBreakers) {
    res.status(503).json({
      error: "Circuit breakers not initialized",
    });
    return;
  }

  const stats = circuitBreakers.getAllStats();
  const summary = circuitBreakers.getSummary();

  res.json({
    timestamp: new Date().toISOString(),
    summary,
    circuits: stats,
  });
}));

// Reset a circuit breaker
app.post("/monitoring/circuits/:name/reset", authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  if (!circuitBreakers) {
    res.status(503).json({
      error: "Circuit breakers not initialized",
    });
    return;
  }

  const name = req.params.name;
  if (!name) {
    res.status(400).json({ error: "Missing circuit name" });
    return;
  }
  const breaker = circuitBreakers.has(name) ? circuitBreakers.get(name) : null;

  if (!breaker) {
    res.status(404).json({
      error: "Circuit breaker not found",
      name,
    });
    return;
  }

  breaker.reset();
  res.json({
    status: "reset",
    circuit: name,
    newState: breaker.getState(),
    timestamp: new Date().toISOString(),
  });
}));

// ============================================================================
// ERROR HANDLER
// ============================================================================

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error("Server error:", err);
  res.status(500).json({
    error: "Internal server error",
    message: err.message,
  });
});

// ============================================================================
// SERVER STARTUP
// ============================================================================

const PORT = process.env.PORT ?? process.env.ESS_GATEWAY_PORT ?? 3001;

async function startServer(): Promise<void> {
  // Initialize agent
  agent = new EnggContextAgent(config);

  // Initialize monitoring Redis connection
  const redisUrl = process.env.REDIS_URL ?? "redis://localhost:6380";
  try {
    monitoringRedis = new Redis(redisUrl);
    monitoringRedis.on("error", (err) => {
      console.warn("[Monitoring] Redis connection error:", err.message);
    });
    console.log("[Monitoring] Redis connected");
  } catch (err) {
    console.warn("[Monitoring] Redis connection failed, monitoring will run without persistence");
  }

  // Initialize circuit breakers
  circuitBreakers = createESSCircuitBreakers();
  console.log("[Monitoring] Circuit breakers initialized");

  // Initialize alert manager
  alertManager = createAlertManagerFromEnv();
  console.log("[Monitoring] Alert manager initialized");

  // Initialize recovery engine
  recoveryEngine = createESSRecoveryEngine(
    monitoringRedis ?? undefined,
    alertManager,
    process.env.DOCKER_COMPOSE_FILE ?? "/home/devuser/docker-compose.prod.yml"
  );
  console.log("[Monitoring] Recovery engine initialized");

  // Initialize health monitor
  const checkInterval = parseInt(process.env.HEALTH_CHECK_INTERVAL ?? "30000", 10);
  healthMonitor = createESSHealthMonitor(monitoringRedis ?? undefined, checkInterval);

  // Wire up monitoring callbacks
  healthMonitor.setAlertCallback(async (services: MonitoringServiceHealth[]) => {
    for (const service of services) {
      const alert = alertManager.createAlert(service);
      await alertManager.send(alert);
    }
  });

  healthMonitor.setRecoveryCallback(async (services: MonitoringServiceHealth[]) => {
    for (const service of services) {
      const attempt = await recoveryEngine.evaluateAndRecover(service);
      if (attempt) {
        console.log(`[Recovery] ${service.service}: ${attempt.action} - ${attempt.success ? "SUCCESS" : "FAILED"}`);
      }
    }
  });

  // Start health monitoring
  healthMonitor.start();
  console.log(`[Monitoring] Health monitor started (interval: ${checkInterval}ms)`);

  app.listen(PORT, () => {
    console.log(`ESS Gateway running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`Query endpoint: POST http://localhost:${PORT}/query`);
    console.log(`Conversation: POST http://localhost:${PORT}/conversation`);
    console.log(`Metrics: http://localhost:${PORT}/metrics`);
    console.log(`Monitoring: http://localhost:${PORT}/monitoring/health`);
    console.log(`Dashboard: http://localhost:${PORT}/dashboard`);
    console.log("");
    console.log("Configuration:");
    console.log(`  Qdrant: ${config.qdrant.url}`);
    console.log(`  Neo4j: ${config.neo4j.uri}`);
    console.log(`  Ollama: ${config.ollama?.url}`);
    console.log(`  Redis: ${redisUrl}`);
  });
}

// Graceful shutdown
process.on("SIGTERM", async () => {
  console.log("SIGTERM received, shutting down...");
  healthMonitor?.stop();
  await agent.close();
  await monitoringRedis?.quit();
  process.exit(0);
});

process.on("SIGINT", async () => {
  console.log("SIGINT received, shutting down...");
  healthMonitor?.stop();
  await agent.close();
  await monitoringRedis?.quit();
  process.exit(0);
});

startServer().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
