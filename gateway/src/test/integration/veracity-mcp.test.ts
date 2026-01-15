/**
 * Integration tests for VeracityMCPClient
 *
 * These tests verify the MCP client can communicate with veracity-engine
 * NOTE: Requires veracity-engine to be running locally
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { VeracityMCPClient } from "../../services/VeracityMCPClient.js";

// Skip these tests if environment variables not set
const shouldRun =
  process.env.RUN_MCP_INTEGRATION_TESTS === "true" &&
  process.env.VERACITY_MCP_SERVER &&
  process.env.NEO4J_PASSWORD;

describe.skipIf(!shouldRun)("VeracityMCPClient Integration", () => {
  let client: VeracityMCPClient;

  beforeAll(async () => {
    client = new VeracityMCPClient({
      pythonPath: process.env.VERACITY_PYTHON_PATH || "python3",
      serverPath: process.env.VERACITY_MCP_SERVER!,
      env: {
        NEO4J_URI: process.env.NEO4J_URI || "bolt://localhost:7687",
        NEO4J_USER: process.env.NEO4J_USER || "neo4j",
        NEO4J_PASSWORD: process.env.NEO4J_PASSWORD!,
      },
      timeout: 30000,
    });

    await client.connect();
  });

  afterAll(async () => {
    await client.close();
  });

  it("should connect to MCP server", () => {
    expect(client.isConnected()).toBe(true);
  });

  it("should check availability", async () => {
    const available = await client.isAvailable();
    expect(available).toBe(true);
  });

  it("should query veracity engine", async () => {
    const result = await client.query("test query", {
      project: "test-project",
      maxResults: 5,
      synthesize: false,
    });

    expect(result).toBeDefined();
    expect(result.results).toBeDefined();
    expect(result.results.summary).toBeDefined();
    expect(result.results.relationships).toBeDefined();
    expect(result.latency).toBeGreaterThan(0);
  });

  it("should handle queries with no results", async () => {
    const result = await client.query("nonexistent-query-xyz-123", {
      project: "test-project",
      maxResults: 5,
      synthesize: false,
    });

    expect(result).toBeDefined();
    expect(result.results.relationships).toHaveLength(0);
  });
});
