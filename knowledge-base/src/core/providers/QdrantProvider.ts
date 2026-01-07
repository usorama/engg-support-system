/**
 * Qdrant Provider
 * Qdrant client wrapper for vector + graph storage
 *
 * VPS Endpoint: http://72.60.204.156:6333
 * Vector Size: 768 (nomic-embed-text)
 * Distance: Cosine
 * Features: Vector embeddings + graph relationships in payload
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import type {
  KGNode,
  SearchResult,
  GraphTraversalResult,
  TraversalPath,
  Relationship,
  NodeType,
} from "../types.js";

// Qdrant types - simplified for this implementation
type Distance = "Cosine" | "Euclid" | "Dot";

// Use 'any' for complex Qdrant types to avoid type complexity
type PointStruct = any;
type ScoredPoint = any;
type Filter = any;

// Search parameters for Qdrant
interface SearchParams {
  vector: number[];
  limit: number;
  with_payload?: boolean | string[];
  with_vector?: boolean | string[];
  filter?: Filter;
  score_threshold?: number;
}

/**
 * Qdrant provider configuration
 */
export interface QdrantProviderConfig {
  /** Qdrant API URL */
  url: string;
  /** API key (optional, for authenticated Qdrant) */
  apiKey?: string;
  /** Collection name */
  collection: string;
  /** Vector size */
  vectorSize: number;
  /** Distance metric */
  distance: Distance;
  /** Request timeout in milliseconds */
  timeout: number;
}

/**
 * QdrantProvider - Vector + graph storage client
 */
export class QdrantProvider {
  private client: QdrantClient;
  private config: QdrantProviderConfig;
  private collectionExists: boolean = false;

  constructor(config: QdrantProviderConfig) {
    this.config = {
      ...config,
      timeout: config.timeout || 30000,
    };

    this.client = new QdrantClient({
      url: this.config.url,
      apiKey: this.config.apiKey,
      timeout: this.config.timeout,
      checkCompatibility: false, // Disable version check
    });
  }

  /**
   * Initialize Qdrant collection
   * Creates collection with optimized configuration
   */
  async initializeCollection(): Promise<void> {
    try {
      // Check if collection exists
      const collections = await this.client.getCollections();
      const existing = collections.collections.find(
        (c) => c.name === this.config.collection
      );

      if (existing) {
        console.log(`Collection "${this.config.collection}" already exists`);
        this.collectionExists = true;
        return;
      }

      // Create new collection
      await this.client.createCollection(this.config.collection, {
        vectors: {
          size: this.config.vectorSize,
          distance: this.config.distance,
        },
        optimizers_config: {
          default_segment_number: 2,
        },
        replication_factor: 1,
      });

      // Create payload indexes for efficient filtering
      await this.createPayloadIndexes();

      this.collectionExists = true;
      console.log(`Collection "${this.config.collection}" created successfully`);
    } catch (error) {
      throw new Error(
        `Failed to initialize collection: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Create payload indexes for efficient graph traversal
   */
  private async createPayloadIndexes(): Promise<void> {
    const indexes = [
      { field_name: "type", field_schema: "keyword" as const },
      { field_name: "source.repo", field_schema: "keyword" as const },
      { field_name: "source.language", field_schema: "keyword" as const },
      { field_name: "metadata.createdAt", field_schema: "integer" as const },
    ];

    for (const index of indexes) {
      try {
        await this.client.createPayloadIndex(this.config.collection, {
          field_name: index.field_name,
          field_schema: index.field_schema,
        });
      } catch (error) {
        // Index might already exist, log and continue
        console.warn(`Index creation for ${index.field_name} failed:`, error);
      }
    }
  }

  /**
   * Upsert nodes (vectors + relationships in payload)
   * @param nodes - Nodes to upsert
   */
  async upsertNodes(nodes: KGNode[]): Promise<void> {
    if (!this.collectionExists) {
      throw new Error("Collection not initialized. Call initializeCollection() first.");
    }

    if (nodes.length === 0) {
      return;
    }

    try {
      // Convert nodes to Qdrant points with proper serialization
      const points: PointStruct[] = nodes.map((node) => {
        // Serialize relationships - convert Date objects to ISO strings
        const serializedRelationships = (node.relationships || []).map((rel) => ({
          id: rel.id,
          type: rel.type,
          targetNodeId: rel.targetNodeId,
          strength: rel.strength,
          metadata: rel.metadata || {},
          createdAt: rel.createdAt.toISOString(),
        }));

        const point = {
          id: node.id,
          vector: node.vector || [],
          payload: {
            node_id: node.id,
            type: node.type,
            content: node.content,
            source: node.source,
            relationships: serializedRelationships,
            metadata: node.metadata || {},
            created_at: node.createdAt.toISOString(),
            updated_at: node.updatedAt.toISOString(),
          },
        };

        // Log first point for debugging
        if (node === nodes[0]) {
          console.log(`[QdrantProvider] Sample point structure:`, JSON.stringify({
            id: point.id,
            id_type: typeof point.id,
            vector_dim: point.vector.length,
            payload_keys: Object.keys(point.payload),
            relationships_count: serializedRelationships.length,
          }, null, 2));
        }

        return point;
      });

      console.log(`[QdrantProvider] Upserting ${points.length} points to collection "${this.config.collection}"`);

      // Batch upsert
      await this.client.upsert(this.config.collection, {
        points,
      });

      console.log(`Upserted ${nodes.length} nodes to collection "${this.config.collection}"`);
    } catch (error: any) {
      // Enhanced error logging
      console.error(`[QdrantProvider] Upsert failed:`, {
        message: error?.message,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        data: error?.response?.data,
      });

      throw new Error(
        `Failed to upsert nodes: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Semantic search
   * @param vector - Query vector
   * @param topK - Number of results
   * @param filter - Optional filter
   * @returns Search results with scores
   */
  async search(
    vector: number[],
    topK: number = 10,
    filter?: Filter
  ): Promise<SearchResult[]> {
    if (!this.collectionExists) {
      throw new Error("Collection not initialized. Call initializeCollection() first.");
    }

    try {
      const searchParams: SearchParams = {
        vector,
        limit: topK,
        with_payload: true,
        with_vector: false,
      };

      if (filter) {
        searchParams.filter = filter;
      }

      const response = await this.client.search(this.config.collection, searchParams);

      // Convert to SearchResult format
      return response.map((point: ScoredPoint) => ({
        node: this.pointToNode(point),
        score: point.score,
      }));
    } catch (error) {
      throw new Error(
        `Search failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Graph traversal - follow relationships from starting node
   * @param startNodeId - Starting node ID
   * @param maxDepth - Maximum traversal depth
   * @returns Graph traversal result with paths
   */
  async traverseGraph(
    startNodeId: string,
    maxDepth: number = 2
  ): Promise<GraphTraversalResult> {
    if (!this.collectionExists) {
      throw new Error("Collection not initialized. Call initializeCollection() first.");
    }

    const visited = new Set<string>();
    const nodes: KGNode[] = [];
    const edges: Relationship[] = [];
    const paths: TraversalPath[] = [];

    try {
      // Get starting node
      const startNode = await this.getNode(startNodeId);
      if (!startNode) {
        throw new Error(`Starting node "${startNodeId}" not found`);
      }

      // BFS traversal
      const queue: Array<{ nodeId: string; depth: number; path: string[] }> = [
        { nodeId: startNodeId, depth: 0, path: [] },
      ];

      while (queue.length > 0) {
        const { nodeId, depth, path } = queue.shift()!;

        if (visited.has(nodeId) || depth > maxDepth) {
          continue;
        }

        visited.add(nodeId);

        // Get node
        const node = await this.getNode(nodeId);
        if (!node) {
          continue;
        }

        nodes.push(node);

        // Track edges
        for (const relationship of node.relationships) {
          edges.push(relationship);

          // Add relationship to path
          const currentPath = [...path, relationship.targetNodeId];

          // Record path if at max depth
          if (depth === maxDepth) {
            paths.push({
              nodes: [...visited, relationship.targetNodeId],
              edges: [...path as unknown as Relationship[], relationship],
              totalStrength: this.calculatePathStrength(currentPath),
            });
          }

          // Enqueue neighbors for next level
          queue.push({
            nodeId: relationship.targetNodeId,
            depth: depth + 1,
            path: currentPath,
          });
        }
      }

      return {
        nodes,
        edges,
        paths,
      };
    } catch (error) {
      throw new Error(
        `Graph traversal failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Get node by ID
   * @param nodeId - Node ID
   * @returns Node or null if not found
   */
  async getNode(nodeId: string): Promise<KGNode | null> {
    try {
      const response = await this.client.retrieve(this.config.collection, {
        ids: [nodeId],
        with_payload: true,
        with_vector: true,
      }) as any;

      if (response.points.length === 0) {
        return null;
      }

      return this.pointToNode(response.points[0]);
    } catch (error) {
      console.error(`Failed to get node "${nodeId}":`, error);
      return null;
    }
  }

  /**
   * Search by filter (metadata-based)
   * @param filter - Qdrant filter
   * @param limit - Max results
   * @returns Matching nodes
   */
  async searchByFilter(
    filter: Filter,
    limit: number = 100
  ): Promise<KGNode[]> {
    if (!this.collectionExists) {
      throw new Error("Collection not initialized. Call initializeCollection() first.");
    }

    try {
      // Use scroll API for filtering
      const response = await this.client.scroll(this.config.collection, {
        limit,
        filter,
        with_payload: true,
        with_vector: false,
      });

      return response.points.map((point) => this.pointToNode(point));
    } catch (error) {
      throw new Error(
        `Filter search failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Delete nodes by IDs
   * @param nodeIds - Node IDs to delete
   */
  async deleteNodes(nodeIds: string[]): Promise<void> {
    if (!this.collectionExists) {
      throw new Error("Collection not initialized. Call initializeCollection() first.");
    }

    try {
      await this.client.delete(this.config.collection, {
        points: nodeIds,
      });

      console.log(`Deleted ${nodeIds.length} nodes from collection "${this.config.collection}"`);
    } catch (error) {
      throw new Error(
        `Failed to delete nodes: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Get collection info
   * @returns Collection statistics
   */
  async getCollectionInfo(): Promise<{ count: number; points_count: number }> {
    if (!this.collectionExists) {
      throw new Error("Collection not initialized. Call initializeCollection() first.");
    }

    try {
      const info = await this.client.getCollection(this.config.collection);
      return {
        count: info.points_count || 0,
        points_count: info.points_count || 0,
      };
    } catch (error) {
      throw new Error(
        `Failed to get collection info: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Convert Qdrant point to KGNode
   * @param point - Qdrant point (ScoredPoint or PointStruct)
   * @returns Knowledge graph node
   */
  private pointToNode(point: ScoredPoint | PointStruct): KGNode {
    const payload = point.payload as any;

    // Deserialize relationships - convert ISO strings back to Date objects
    const relationships = (payload.relationships || []).map((rel: any) => ({
      id: rel.id,
      type: rel.type,
      targetNodeId: rel.targetNodeId,
      strength: rel.strength,
      metadata: rel.metadata || {},
      createdAt: new Date(rel.createdAt),
    }));

    return {
      id: point.id as string,
      type: payload.type as NodeType,
      content: payload.content as string,
      source: payload.source,
      vector: point.vector as number[] | undefined,
      relationships,
      metadata: payload.metadata,
      createdAt: new Date(payload.created_at),
      updatedAt: new Date(payload.updated_at),
    };
  }

  /**
   * Calculate path strength (average of relationship strengths)
   * @param path - Array of node IDs in path
   * @returns Strength score (0-1)
   */
  private calculatePathStrength(path: string[]): number {
    if (path.length === 0) {
      return 0;
    }

    // Placeholder - would need to fetch actual relationships
    // For now, return a default strength
    return 0.5;
  }

  /**
   * Delete collection (use with caution!)
   */
  async deleteCollection(): Promise<void> {
    try {
      await this.client.deleteCollection(this.config.collection);
      this.collectionExists = false;
      console.log(`Collection "${this.config.collection}" deleted`);
    } catch (error) {
      throw new Error(
        `Failed to delete collection: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }
}
