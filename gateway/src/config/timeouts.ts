/**
 * Centralized timeout configuration for all ESS services
 *
 * This ensures consistent timeout behavior across:
 * - SynthesisAgent (9 instantiation sites)
 * - EnggContextAgent
 * - Neo4j client
 * - Qdrant client
 * - Health checks
 * - Circuit breakers
 *
 * All timeouts are configurable via environment variables with sensible defaults.
 */

/**
 * Default timeout values (in milliseconds)
 */
export const DEFAULT_TIMEOUTS = {
  /**
   * LLM synthesis operations (Anthropic, OpenAI, Ollama)
   * Default: 60000ms (60 seconds) - allows for cold starts and complex queries
   */
  synthesis: parseInt(process.env.SYNTHESIS_TIMEOUT ?? "60000", 10),

  /**
   * Neo4j database operations
   * Default: 30000ms (30 seconds)
   */
  neo4j: parseInt(process.env.NEO4J_TIMEOUT ?? "30000", 10),

  /**
   * Qdrant vector database operations
   * Default: 30000ms (30 seconds)
   */
  qdrant: parseInt(process.env.QDRANT_TIMEOUT ?? "30000", 10),

  /**
   * Redis cache operations
   * Default: 5000ms (5 seconds)
   */
  redis: parseInt(process.env.REDIS_TIMEOUT ?? "5000", 10),

  /**
   * Health check probes
   * Default: 10000ms (10 seconds)
   */
  healthCheck: parseInt(process.env.HEALTH_CHECK_TIMEOUT ?? "10000", 10),

  /**
   * Circuit breaker reset timeout
   * Default: 30000ms (30 seconds)
   */
  circuitBreakerReset: parseInt(
    process.env.CIRCUIT_BREAKER_RESET ?? "30000",
    10
  ),

  /**
   * API request timeout for external services
   * Default: 60000ms (60 seconds)
   */
  apiRequest: parseInt(process.env.API_REQUEST_TIMEOUT ?? "60000", 10),
} as const;

/**
 * Get the synthesis timeout value
 * Used by SynthesisAgent for LLM operations
 */
export function getSynthesisTimeout(): number {
  return DEFAULT_TIMEOUTS.synthesis;
}

/**
 * Get the Neo4j timeout value
 */
export function getNeo4jTimeout(): number {
  return DEFAULT_TIMEOUTS.neo4j;
}

/**
 * Get the Qdrant timeout value
 */
export function getQdrantTimeout(): number {
  return DEFAULT_TIMEOUTS.qdrant;
}

/**
 * Get the Redis timeout value
 */
export function getRedisTimeout(): number {
  return DEFAULT_TIMEOUTS.redis;
}

/**
 * Get the health check timeout value
 */
export function getHealthCheckTimeout(): number {
  return DEFAULT_TIMEOUTS.healthCheck;
}

/**
 * Get the circuit breaker reset timeout value
 */
export function getCircuitBreakerResetTimeout(): number {
  return DEFAULT_TIMEOUTS.circuitBreakerReset;
}

/**
 * Get the API request timeout value
 */
export function getApiRequestTimeout(): number {
  return DEFAULT_TIMEOUTS.apiRequest;
}
