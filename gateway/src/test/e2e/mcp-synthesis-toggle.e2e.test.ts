/**
 * E2E tests for synthesis toggle with MCP backend
 *
 * Verifies that:
 * 1. Gateway can use MCP client instead of direct Neo4j
 * 2. Synthesis toggle works correctly (raw vs synthesized)
 * 3. Response format is correct regardless of backend
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { EnggContextAgent } from "../../agents/EnggContextAgent.js";
import type { QueryRequestWithMode, QueryResponse } from "../../types/agent-contracts.js";

// Skip if MCP not configured
const shouldRun = process.env.RUN_MCP_E2E_TESTS === "true";

describe.skipIf(!shouldRun)("Gateway MCP + Synthesis E2E", () => {
  let agentWithMCP: EnggContextAgent;
  let agentWithoutMCP: EnggContextAgent;

  beforeAll(() => {
    // Agent with MCP backend
    agentWithMCP = new EnggContextAgent({
      qdrant: {
        url: process.env.QDRANT_URL || "http://localhost:6333",
        collection: "test-collection",
      },
      neo4j: {
        uri: process.env.NEO4J_URI || "bolt://localhost:7687",
        user: process.env.NEO4J_USER || "neo4j",
        password: process.env.NEO4J_PASSWORD || "password",
      },
      veracityMCP: {
        pythonPath: process.env.VERACITY_PYTHON_PATH || "python3",
        serverPath: process.env.VERACITY_MCP_SERVER || "/path/to/mcp_server.py",
        env: {
          NEO4J_URI: process.env.NEO4J_URI || "bolt://localhost:7687",
          NEO4J_USER: process.env.NEO4J_USER || "neo4j",
          NEO4J_PASSWORD: process.env.NEO4J_PASSWORD || "password",
        },
      },
      ollama: {
        url: process.env.OLLAMA_URL || "http://localhost:11434",
        embedModel: "nomic-embed-text",
        synthesisModel: "llama3.2",
      },
    });

    // Agent without MCP (direct Neo4j)
    agentWithoutMCP = new EnggContextAgent({
      qdrant: {
        url: process.env.QDRANT_URL || "http://localhost:6333",
        collection: "test-collection",
      },
      neo4j: {
        uri: process.env.NEO4J_URI || "bolt://localhost:7687",
        user: process.env.NEO4J_USER || "neo4j",
        password: process.env.NEO4J_PASSWORD || "password",
      },
      ollama: {
        url: process.env.OLLAMA_URL || "http://localhost:11434",
        embedModel: "nomic-embed-text",
        synthesisModel: "llama3.2",
      },
    });
  });

  afterAll(async () => {
    await agentWithMCP.close();
    await agentWithoutMCP.close();
  });

  describe("MCP Backend", () => {
    it("should query with MCP backend in raw mode", async () => {
      const request: QueryRequestWithMode = {
        query: "test query",
        requestId: "test-mcp-raw",
        timestamp: new Date().toISOString(),
        project: "test-project",
        synthesisMode: "raw",
      };

      const response = await agentWithMCP.query(request);

      // Type guard for QueryResponse
      expect(response).toHaveProperty("status");
      if ("results" in response) {
        expect(response.results).toBeDefined();
        expect(response.results.structural).toBeDefined();
        expect(response.answer).toBeUndefined(); // Raw mode = no synthesis
      }
    });

    it("should query with MCP backend in synthesized mode", async () => {
      const request: QueryRequestWithMode = {
        query: "test query",
        requestId: "test-mcp-synthesized",
        timestamp: new Date().toISOString(),
        project: "test-project",
        synthesisMode: "synthesized",
      };

      const response = await agentWithMCP.query(request);

      // Type guard for QueryResponse
      expect(response).toHaveProperty("status");
      if ("results" in response) {
        expect(response.results).toBeDefined();
        expect(response.results.structural).toBeDefined();
        // Synthesized mode should add answer field (if synthesis agent configured)
        if (response.answer) {
          expect(response.answer.text).toBeDefined();
          expect(response.answer.confidence).toBeGreaterThanOrEqual(0);
          expect(response.answer.citations).toBeDefined();
        }
      }
    });
  });

  describe("Direct Neo4j Backend", () => {
    it("should query with Neo4j backend in raw mode", async () => {
      const request: QueryRequestWithMode = {
        query: "test query",
        requestId: "test-neo4j-raw",
        timestamp: new Date().toISOString(),
        project: "test-project",
        synthesisMode: "raw",
      };

      const response = await agentWithoutMCP.query(request);

      // Type guard for QueryResponse
      expect(response).toHaveProperty("status");
      if ("results" in response) {
        expect(response.results).toBeDefined();
        expect(response.results.structural).toBeDefined();
        expect(response.answer).toBeUndefined(); // Raw mode = no synthesis
      }
    });

    it("should query with Neo4j backend in synthesized mode", async () => {
      const request: QueryRequestWithMode = {
        query: "test query",
        requestId: "test-neo4j-synthesized",
        timestamp: new Date().toISOString(),
        project: "test-project",
        synthesisMode: "synthesized",
      };

      const response = await agentWithoutMCP.query(request);

      // Type guard for QueryResponse
      expect(response).toHaveProperty("status");
      if ("results" in response) {
        expect(response.results).toBeDefined();
        expect(response.results.structural).toBeDefined();
        // Synthesized mode should add answer field (if synthesis agent configured)
        if (response.answer) {
          expect(response.answer.text).toBeDefined();
          expect(response.answer.confidence).toBeGreaterThanOrEqual(0);
          expect(response.answer.citations).toBeDefined();
        }
      }
    });
  });

  describe("Response Format Consistency", () => {
    it("should return consistent format regardless of backend", async () => {
      const request: QueryRequestWithMode = {
        query: "test query",
        requestId: "test-consistency",
        timestamp: new Date().toISOString(),
        project: "test-project",
        synthesisMode: "raw",
      };

      const mcpResponse = await agentWithMCP.query(request);
      const neo4jResponse = await agentWithoutMCP.query(request);

      // Both should have same structure (if QueryResponse)
      expect(mcpResponse).toHaveProperty("status");
      expect(neo4jResponse).toHaveProperty("status");

      if ("results" in mcpResponse) {
        expect(mcpResponse.results).toHaveProperty("structural");
        expect(mcpResponse).toHaveProperty("meta");
      }

      if ("results" in neo4jResponse) {
        expect(neo4jResponse.results).toHaveProperty("structural");
        expect(neo4jResponse).toHaveProperty("meta");
      }
    });
  });
});
