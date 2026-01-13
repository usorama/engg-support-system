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
import { EnggContextAgent, type EnggContextAgentConfig } from "./agents/EnggContextAgent.js";
import { conversationManager } from "./agents/ConversationManager.js";
import type {
  QueryRequest,
  QueryRequestWithMode,
  ConversationRequest,
  GatewayResponse,
} from "./types/agent-contracts.js";

// Environment configuration with defaults
const qdrantConfig: EnggContextAgentConfig["qdrant"] = {
  url: process.env.QDRANT_URL ?? "http://localhost:6333",
  collection: process.env.QDRANT_COLLECTION ?? "engineering_kb",
};

// Only add apiKey if it's defined
if (process.env.QDRANT_API_KEY) {
  qdrantConfig.apiKey = process.env.QDRANT_API_KEY;
}

const config: EnggContextAgentConfig = {
  qdrant: qdrantConfig,
  neo4j: {
    uri: process.env.NEO4J_URI ?? "bolt://localhost:7687",
    user: process.env.NEO4J_USER ?? "neo4j",
    password: process.env.NEO4J_PASSWORD ?? "password123",
  },
  ollama: {
    url: process.env.OLLAMA_URL ?? "http://localhost:11434",
    embedModel: process.env.EMBEDDING_MODEL ?? "nomic-embed-text",
    synthesisModel: process.env.SYNTHESIS_MODEL ?? "llama3.2",
  },
};

// Initialize agent
let agent: EnggContextAgent;

const app = express();
app.use(cors());
app.use(express.json());

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

app.post("/query", asyncHandler(async (req: Request, res: Response) => {
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
    mode: body.mode ?? "one-shot",
    synthesisMode: body.synthesisMode ?? "synthesized", // Default to synthesized mode
    ...(body.project !== undefined && { project: body.project }),
    ...(body.context !== undefined && { context: body.context }),
  };

  const response: GatewayResponse = await agent.query(request);
  res.json(response);
}));

// ============================================================================
// CONVERSATION ENDPOINTS
// ============================================================================

// Start a new conversation
app.post("/conversation", asyncHandler(async (req: Request, res: Response) => {
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

  const response: GatewayResponse = await agent.query(request);
  res.json(response);
}));

// Continue an existing conversation
interface ContinueConversationBody {
  answers: Record<string, string>;
}

app.post("/conversation/:id/continue", asyncHandler(async (req: Request, res: Response) => {
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

  const request: ConversationRequest = {
    conversationId,
    answers: body.answers,
    requestId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  };

  const response: GatewayResponse = await agent.continueConversation(request);
  res.json(response);
}));

// Abort a conversation
app.delete("/conversation/:id", asyncHandler(async (req: Request, res: Response) => {
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

  app.listen(PORT, () => {
    console.log(`ESS Gateway running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`Query endpoint: POST http://localhost:${PORT}/query`);
    console.log(`Conversation: POST http://localhost:${PORT}/conversation`);
    console.log("");
    console.log("Configuration:");
    console.log(`  Qdrant: ${config.qdrant.url}`);
    console.log(`  Neo4j: ${config.neo4j.uri}`);
    console.log(`  Ollama: ${config.ollama?.url}`);
    console.log(`  Redis: ${process.env.REDIS_URL ?? "redis://localhost:6380"}`);
  });
}

// Graceful shutdown
process.on("SIGTERM", async () => {
  console.log("SIGTERM received, shutting down...");
  await agent.close();
  process.exit(0);
});

process.on("SIGINT", async () => {
  console.log("SIGINT received, shutting down...");
  await agent.close();
  process.exit(0);
});

startServer().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
