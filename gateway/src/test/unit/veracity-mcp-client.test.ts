/**
 * Tests for VeracityMCPClient
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { VeracityMCPClient } from "../../services/VeracityMCPClient.js";
import type { StructuralRelationship } from "../../types/agent-contracts.js";

describe("VeracityMCPClient", () => {
  describe("parseEvidencePacket", () => {
    it("should parse evidence packet with relationships", () => {
      const client = new VeracityMCPClient({
        pythonPath: "python3",
        serverPath: "/path/to/mcp_server.py",
        env: {},
      });

      const evidenceText = `## Evidence Packet
**Query**: test query
**Confidence**: 85%

### Code Evidence
- File: src/test.ts (line 10-20)

### Graph Relationships
- ComponentA -> ComponentB (DEPENDS_ON)
- ComponentB -> ComponentC (CALLS)
`;

      // Access private method through type assertion
      const result = (client as any).parseEvidencePacket(evidenceText);

      expect(result.relationships).toHaveLength(2);
      expect(result.relationships[0]).toEqual({
        source: "ComponentA",
        target: "ComponentB",
        type: "DEPENDS_ON",
        path: ["ComponentA", "DEPENDS_ON", "ComponentB"],
      });
      expect(result.summary).toContain("Found 2 relationship");
      expect(result.summary).toContain("confidence: 85%");
    });

    it("should handle evidence packet with no relationships", () => {
      const client = new VeracityMCPClient({
        pythonPath: "python3",
        serverPath: "/path/to/mcp_server.py",
        env: {},
      });

      const evidenceText = `## Evidence Packet
**Query**: test query
**Confidence**: 0%

### Code Evidence
- File: src/test.ts (line 10-20)
`;

      const result = (client as any).parseEvidencePacket(evidenceText);

      expect(result.relationships).toHaveLength(0);
      expect(result.summary).toBe("No structural relationships found.");
    });

    it("should handle malformed relationship lines", () => {
      const client = new VeracityMCPClient({
        pythonPath: "python3",
        serverPath: "/path/to/mcp_server.py",
        env: {},
      });

      const evidenceText = `## Evidence Packet
**Query**: test query
**Confidence**: 50%

### Graph Relationships
- ComponentA -> ComponentB (DEPENDS_ON)
- Invalid line without arrow
- AnotherComp -> Target (TYPE)
`;

      const result = (client as any).parseEvidencePacket(evidenceText);

      // Should only parse valid relationship lines
      expect(result.relationships).toHaveLength(2);
    });
  });

  describe("configuration", () => {
    it("should filter out undefined env values", () => {
      const client = new VeracityMCPClient({
        pythonPath: "python3",
        serverPath: "/path/to/mcp_server.py",
        env: {
          NEO4J_URI: "bolt://localhost:7687",
          NEO4J_USER: "neo4j",
          NEO4J_PASSWORD: undefined as any,
        },
      });

      expect(client).toBeDefined();
    });

    it("should accept timeout configuration", () => {
      const client = new VeracityMCPClient({
        pythonPath: "python3",
        serverPath: "/path/to/mcp_server.py",
        env: {},
        timeout: 60000,
      });

      expect(client).toBeDefined();
    });
  });

  describe("isConnected", () => {
    it("should return false before connection", () => {
      const client = new VeracityMCPClient({
        pythonPath: "python3",
        serverPath: "/path/to/mcp_server.py",
        env: {},
      });

      expect(client.isConnected()).toBe(false);
    });
  });
});
