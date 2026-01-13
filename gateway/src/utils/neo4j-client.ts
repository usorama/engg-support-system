/**
 * Neo4j Client Utility
 * Handles structural graph queries to Neo4j database
 */

import neo4j, { Driver, int } from "neo4j-driver";
import type { StructuralResult, StructuralRelationship } from "../types/agent-contracts.js";

export interface Neo4jClientConfig {
  uri: string;
  user: string;
  password: string;
  database?: string;
  timeout?: number;
}

/**
 * Neo4j client for structural graph queries
 */
export class Neo4jGatewayClient {
  private driver: Driver;
  private database: string;
  private timeout: number;

  constructor(config: Neo4jClientConfig) {
    this.driver = neo4j.driver(
      config.uri,
      neo4j.auth.basic(config.user, config.password),
      {
        maxTransactionRetryTime: config.timeout || 30000,
      },
    );
    this.database = config.database || "neo4j";
    this.timeout = config.timeout || 30000;
  }

  /**
   * Check if Neo4j is available
   */
  async isAvailable(): Promise<boolean> {
    try {
      const session = this.driver.session();
      try {
        await session.run("RETURN 1 AS n");
        return true;
      } finally {
        await session.close();
      }
    } catch {
      return false;
    }
  }

  /**
   * Perform structural search
   * Find relationships connected to a query term
   */
  async structuralSearch(
    query: string,
    options: {
      limit?: number;
      project?: string;
    } = {},
  ): Promise<{ results: StructuralResult; latency: number }> {
    const startTime = Date.now();

    try {
      const session = this.driver.session({ database: this.database });
      try {
        // Search for nodes/relationships related to the query
        // Schema aligned with veracity-engine build_graph.py:
        // - path: file path (not "file")
        // - uid: unique id (not "id")
        // - start_line: line number (not "line")
        // - qualified_name: full qualified name for code elements
        const cypher = `
          MATCH (source)-[r]->(target)
          WHERE (
            source.name CONTAINS $query
            OR source.path CONTAINS $query
            OR source.qualified_name CONTAINS $query
            OR type(r) CONTAINS $query
          )
          ${options.project ? `AND source.project = $project` : ""}
          RETURN source.name AS source,
                 target.name AS target,
                 type(r) AS type,
                 source.path AS sourceFile,
                 target.path AS targetFile,
                 source.start_line AS sourceLine,
                 [source.name, type(r), target.name] AS path
          LIMIT $limit
        `;

        const result = await session.run(cypher, {
          query,
          limit: int(options.limit || 10),
          project: options.project,
        });

        const latency = Date.now() - startTime;

        const relationships: StructuralRelationship[] = result.records.map(
          (record) => ({
            source: record.get("source"),
            target: record.get("target"),
            type: record.get("type"),
            path: record.get("path"),
          }),
        );

        const summary = this.generateSummary(relationships);

        return {
          results: {
            summary,
            relationships,
          },
          latency,
        };
      } finally {
        await session.close();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`[Neo4j] structuralSearch failed for query "${query}":`, errorMessage);
      throw new Error(`Neo4j search failed: ${errorMessage}`);
    }
  }

  /**
   * Generate summary from relationships
   */
  private generateSummary(relationships: StructuralRelationship[]): string {
    if (relationships.length === 0) {
      return "No structural relationships found.";
    }

    const uniqueTypes = new Set(relationships.map((r) => r.type));

    return `## Code Relationships\n\nFound ${relationships.length} relationship${relationships.length > 1 ? "s" : ""} across ${uniqueTypes.size} types`;
  }

  /**
   * Close the driver
   */
  async close(): Promise<void> {
    await this.driver.close();
  }
}
