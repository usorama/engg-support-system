/**
 * Veracity MCP Client
 *
 * Connects to veracity-engine MCP server for deterministic graph queries.
 * Uses stdio transport for local MCP communication.
 *
 * NOTE: This uses the MCP SDK's StdioClientTransport which handles
 * subprocess spawning securely. We don't use exec() directly.
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { StructuralResult, StructuralRelationship } from "../types/agent-contracts.js";

export interface VeracityMCPConfig {
  /** Python executable path */
  pythonPath: string;

  /** Path to veracity-engine mcp_server.py */
  serverPath: string;

  /** Environment variables */
  env?: Record<string, string>;

  /** Timeout for MCP operations (ms) */
  timeout?: number;
}

export interface VeracityQueryOptions {
  /** Project name in Neo4j */
  project: string;

  /** Maximum results to return */
  maxResults?: number;

  /** Include synthesis (LLM explanation) */
  synthesize?: boolean;
}

/**
 * MCP client for veracity-engine
 */
export class VeracityMCPClient {
  private client: Client;
  private transport: StdioClientTransport | null = null;
  private config: VeracityMCPConfig;
  private connected = false;
  private timeout: number;

  constructor(config: VeracityMCPConfig) {
    this.config = config;
    this.timeout = config.timeout ?? 30000;

    // Initialize MCP client
    this.client = new Client(
      {
        name: "gateway-veracity-client",
        version: "1.0.0",
      },
      {
        capabilities: {},
      },
    );
  }

  /**
   * Connect to MCP server
   */
  async connect(): Promise<void> {
    if (this.connected) {
      return;
    }

    try {
      // Create stdio transport (securely spawns subprocess)
      // Filter out undefined values from env
      const filteredEnv: Record<string, string> = {};
      const envToMerge = { ...process.env, ...this.config.env };
      for (const [key, value] of Object.entries(envToMerge)) {
        if (value !== undefined) {
          filteredEnv[key] = value;
        }
      }

      this.transport = new StdioClientTransport({
        command: this.config.pythonPath,
        args: [this.config.serverPath],
        env: filteredEnv,
      });

      // Connect client to transport
      await this.client.connect(this.transport);
      this.connected = true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to connect to veracity MCP: ${errorMessage}`);
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connected;
  }

  /**
   * Query veracity engine
   */
  async query(
    query: string,
    options: VeracityQueryOptions,
  ): Promise<{ results: StructuralResult; latency: number }> {
    if (!this.connected) {
      await this.connect();
    }

    const startTime = Date.now();

    try {
      // Call query_codebase tool
      const response = await this.client.callTool({
        name: "query_codebase",
        arguments: {
          project_name: options.project,
          question: query,
          max_results: options.maxResults ?? 20,
        },
      });

      const latency = Date.now() - startTime;

      // Parse response - content is an array of ContentItem
      const content = (response.content ?? []) as Array<{ type: string; text?: string }>;

      if (content.length === 0) {
        return {
          results: {
            summary: "No results found.",
            relationships: [],
          },
          latency,
        };
      }

      // Extract text content
      const textContent = content.find((c) => c.type === "text");
      if (!textContent || !textContent.text) {
        throw new Error("No text content in MCP response");
      }

      // Parse evidence packet into StructuralResult
      const results = this.parseEvidencePacket(textContent.text);

      return { results, latency };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Veracity query failed: ${errorMessage}`);
    }
  }

  /**
   * Parse evidence packet from veracity MCP into StructuralResult
   */
  private parseEvidencePacket(text: string): StructuralResult {
    // Evidence packet format from veracity-engine:
    // ## Evidence Packet
    // **Query**: ...
    // **Confidence**: ...%
    // ### Code Evidence
    // - File: path (line X-Y)
    //   ```language
    //   code block
    //   ```
    // ### Graph Relationships
    // - source -> target (type)

    const relationships: StructuralRelationship[] = [];
    let summary = "No structural relationships found.";

    // Extract relationships from "Graph Relationships" section
    const graphMatch = text.match(/### Graph Relationships\s+([\s\S]*?)(?=###|$)/);
    if (graphMatch && graphMatch[1]) {
      const graphSection = graphMatch[1];
      const relationshipPattern = /- (.+?) -> (.+?) \((.+?)\)/g;
      let match: RegExpExecArray | null;

      while ((match = relationshipPattern.exec(graphSection)) !== null) {
        const source = match[1];
        const target = match[2];
        const type = match[3];

        if (source && target && type) {
          relationships.push({
            source: source.trim(),
            target: target.trim(),
            type: type.trim(),
            path: [source.trim(), type.trim(), target.trim()],
          });
        }
      }
    }

    // Extract confidence from packet
    const confidenceMatch = text.match(/\*\*Confidence\*\*: (\d+)%/);
    const confidence = confidenceMatch && confidenceMatch[1] ? parseInt(confidenceMatch[1]) : 0;

    if (relationships.length > 0) {
      const uniqueTypes = new Set(relationships.map((r) => r.type));
      summary = `## Code Relationships\n\nFound ${relationships.length} relationship${relationships.length > 1 ? "s" : ""} across ${uniqueTypes.size} types (confidence: ${confidence}%)`;
    }

    return {
      summary,
      relationships,
    };
  }

  /**
   * Check if veracity engine is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      if (!this.connected) {
        await this.connect();
      }

      // Try to list projects as a health check
      const response = await this.client.callTool({
        name: "list_projects",
        arguments: {},
      });

      const content = (response.content ?? []) as Array<{ type: string }>;
      return content.length > 0;
    } catch {
      return false;
    }
  }

  /**
   * Close connection
   */
  async close(): Promise<void> {
    if (this.transport) {
      await this.transport.close();
      this.transport = null;
      this.connected = false;
    }
  }
}

/**
 * Create VeracityMCPClient from environment
 */
export function createVeracityMCPClient(): VeracityMCPClient {
  const pythonPath = process.env.VERACITY_PYTHON_PATH ?? "python3";
  const serverPath =
    process.env.VERACITY_MCP_SERVER ??
    "/Users/umasankr/Projects/engg-support-system/veracity-engine/core/mcp_server.py";

  const neo4jUri = process.env.NEO4J_URI ?? "bolt://localhost:7687";
  const neo4jUser = process.env.NEO4J_USER ?? "neo4j";
  const neo4jPassword = process.env.NEO4J_PASSWORD ?? "";

  return new VeracityMCPClient({
    pythonPath,
    serverPath,
    env: {
      NEO4J_URI: neo4jUri,
      NEO4J_USER: neo4jUser,
      NEO4J_PASSWORD: neo4jPassword,
    },
    timeout: 30000,
  });
}
