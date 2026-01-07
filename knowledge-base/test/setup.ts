/**
 * Test Setup
 * Global test configuration for Bun Test
 */

// Set test environment variables
// Use localhost for VPS testing, or external IP for local testing
const isVPS = process.env.VPS === "true" || process.env.NODE_ENV === "production";

process.env.QDRANT_URL = isVPS ? "http://127.0.0.1:6333" : (process.env.QDRANT_URL || "http://72.60.204.156:6333");
process.env.OLLAMA_URL = isVPS ? "http://127.0.0.1:11434" : (process.env.OLLAMA_URL || "http://72.60.204.156:11434");
process.env.LOG_LEVEL = "error";

console.log(`Test environment: ${isVPS ? "VPS (localhost)" : "remote"}`);
console.log(`QDRANT_URL: ${process.env.QDRANT_URL}`);
console.log(`OLLAMA_URL: ${process.env.OLLAMA_URL}`);

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: () => {}, // Silence regular logs in tests
  info: () => {},
  warn: () => {},
};

console.log("Test environment configured");
