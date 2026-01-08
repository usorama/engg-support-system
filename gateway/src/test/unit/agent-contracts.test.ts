/**
 * Unit Tests: Agent Contracts
 * TDD RED Phase - These tests MUST fail initially
 */

import { describe, it, expect } from "vitest";
import {
  QueryRequest,
  QueryResponse,
  QueryIntent,
  SemanticResult,
  StructuralResult,
  QueryMetadata,
} from "../../types/agent-contracts.js";

describe("Agent Contracts - Type Validation", () => {
  describe("QueryRequest", () => {
    it("should validate valid QueryRequest structure", () => {
      const request: QueryRequest = {
        query: "How does authentication work?",
        requestId: "req-001",
        timestamp: "2026-01-07T10:30:00Z",
      };

      expect(request.query).toBeDefined();
      expect(request.requestId).toBeDefined();
      expect(request.timestamp).toBeDefined();
    });

    it("should accept optional project field", () => {
      const request: QueryRequest = {
        query: "Show me the auth service",
        requestId: "req-002",
        timestamp: "2026-01-07T10:30:00Z",
        project: "knowledge-base",
      };

      expect(request.project).toBe("knowledge-base");
    });

    it("should accept optional context field", () => {
      const request: QueryRequest = {
        query: "What about the login flow?",
        requestId: "req-003",
        timestamp: "2026-01-07T10:30:00Z",
        context: ["user is asking about authentication", "focus on TypeScript code"],
      };

      expect(request.context).toHaveLength(2);
    });
  });

  describe("QueryIntent", () => {
    it("should support all intent types", () => {
      const intents: QueryIntent[] = [
        "code",
        "explanation",
        "both",
        "location",
        "relationship",
        "unknown",
      ];

      expect(intents).toHaveLength(6);
    });
  });

  describe("QueryResponse", () => {
    it("should validate success response structure", () => {
      const response: QueryResponse = {
        requestId: "req-001",
        status: "success",
        timestamp: "2026-01-07T10:30:00.250Z",
        queryType: "both",
        results: {
          semantic: {
            summary: "## Authentication System\n\nJWT-based authentication...",
            matches: [
              {
                content: "```typescript\nexport class AuthService { ... }\n```",
                score: 0.95,
                source: "src/auth/AuthService.ts",
                type: "code",
                language: "typescript",
              },
            ],
          },
          structural: {
            summary: "Code structure",
            relationships: [
              {
                source: "AuthService.ts",
                target: "JWTUtils.ts",
                type: "CALLS",
                path: ["AuthService.ts:15", "JWTUtils.ts:signToken"],
              },
            ],
          },
        },
        meta: {
          qdrantQueried: true,
          neo4jQueried: true,
          qdrantLatency: 45,
          neo4jLatency: 32,
          totalLatency: 120,
          cacheHit: false,
        },
      };

      expect(response.status).toBe("success");
      expect(response.results.semantic.matches).toHaveLength(1);
      expect(response.results.structural.relationships).toHaveLength(1);
    });

    it("should validate partial response when one DB is down", () => {
      const response: QueryResponse = {
        requestId: "req-002",
        status: "partial",
        timestamp: "2026-01-07T10:31:00.100Z",
        queryType: "both",
        results: {
          semantic: {
            summary: "Found matches",
            matches: [
              {
                content: "Auth code here",
                score: 0.88,
                source: "src/auth/AuthService.ts",
                type: "code",
              },
            ],
          },
          structural: {
            summary: "No structural data available",
            relationships: [],
          },
        },
        warnings: [
          "⚠️ Neo4j structural search unavailable - returning semantic results only",
        ],
        meta: {
          qdrantQueried: true,
          neo4jQueried: false,
          qdrantLatency: 50,
          neo4jLatency: 0,
          totalLatency: 60,
          cacheHit: false,
        },
      };

      expect(response.status).toBe("partial");
      expect(response.warnings).toBeDefined();
      expect(response.warnings).toHaveLength(1);
    });

    it("should validate unavailable response when both DBs are down", () => {
      const response: QueryResponse = {
        requestId: "req-003",
        status: "unavailable",
        timestamp: "2026-01-07T10:32:00.050Z",
        queryType: "unknown",
        results: {
          semantic: {
            summary: "No results available",
            matches: [],
          },
          structural: {
            summary: "No structural data available",
            relationships: [],
          },
        },
        warnings: [
          "❌ Engineering context system temporarily unavailable",
          "❌ Both Qdrant and Neo4j databases are unreachable",
        ],
        fallbackMessage: "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH",
        meta: {
          qdrantQueried: false,
          neo4jQueried: false,
          qdrantLatency: 0,
          neo4jLatency: 0,
          totalLatency: 50,
          cacheHit: false,
        },
      };

      expect(response.status).toBe("unavailable");
      expect(response.fallbackMessage).toBe(
        "SYSTEM IS UNAVAILABLE, USE WEB & CODEBASE RESEARCH",
      );
    });
  });

  describe("SemanticResult", () => {
    it("should validate semantic result with all fields", () => {
      const result: SemanticResult = {
        summary: "Found 3 authentication-related files",
        matches: [
          {
            content: "AuthService code",
            score: 0.92,
            source: "src/auth/AuthService.ts",
            type: "code",
            lineStart: 10,
            lineEnd: 45,
            language: "typescript",
          },
          {
            content: "# Authentication Guide\n\nDocs here...",
            score: 0.88,
            source: "docs/auth-guide.md",
            type: "doc",
          },
        ],
      };

      expect(result.matches).toHaveLength(2);
      expect(result.matches[0]?.lineStart).toBe(10);
      expect(result.matches[1]?.language).toBeUndefined();
    });
  });

  describe("StructuralResult", () => {
    it("should validate structural result with path relationships", () => {
      const result: StructuralResult = {
        summary: "## Code Relationships\n\nComponents and their connections",
        relationships: [
          {
            source: "LoginPage.tsx",
            target: "AuthService",
            type: "CALLS",
            path: ["LoginPage.tsx", "AuthService.authenticate", "Database.verifyUser"],
            explanation: "Login page calls authentication service to validate credentials",
          },
        ],
      };

      expect(result.relationships).toHaveLength(1);
      expect(result.relationships[0]?.path).toHaveLength(3);
    });
  });

  describe("QueryMetadata", () => {
    it("should track latency for both databases", () => {
      const meta: QueryMetadata = {
        qdrantQueried: true,
        neo4jQueried: true,
        qdrantLatency: 45,
        neo4jLatency: 32,
        totalLatency: 120,
        cacheHit: false,
      };

      expect(meta.totalLatency).toBeGreaterThan(meta.qdrantLatency);
      expect(meta.totalLatency).toBeGreaterThan(meta.neo4jLatency);
    });

    it("should show zero latency when database not queried", () => {
      const meta: QueryMetadata = {
        qdrantQueried: false,
        neo4jQueried: true,
        qdrantLatency: 0,
        neo4jLatency: 32,
        totalLatency: 35,
        cacheHit: false,
      };

      expect(meta.qdrantLatency).toBe(0);
      expect(meta.neo4jLatency).toBeGreaterThan(0);
    });
  });
});
