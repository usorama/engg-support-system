/**
 * Test Setup for Gateway Tests
 */

// Set test environment variables
process.env.QDRANT_URL = process.env.QDRANT_URL || "http://localhost:6333";
process.env.NEO4J_URI = process.env.NEO4J_URI || "bolt://localhost:7687";
process.env.NEO4J_USER = process.env.NEO4J_USER || "neo4j";
process.env.NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || "password";

// Global test configuration
export const testConfig = {
  qdrant: {
    url: process.env.QDRANT_URL,
    timeout: 5000,
  },
  neo4j: {
    uri: process.env.NEO4J_URI || "",
    user: process.env.NEO4J_USER || "",
    password: process.env.NEO4J_PASSWORD || "",
  },
};
