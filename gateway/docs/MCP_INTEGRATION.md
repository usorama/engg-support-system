# MCP Integration - Phase 4 Gateway Enhancement

## Overview

The gateway now supports connecting to veracity-engine via MCP (Model Context Protocol) instead of direct Neo4j queries. This provides:

1. **Optional Layer**: Can use MCP or direct Neo4j (configurable)
2. **Synthesis Toggle**: Control whether to return raw evidence or synthesized answers
3. **Unified Interface**: Same response format regardless of backend

## Architecture

```
┌─────────────────┐
│  HTTP Gateway   │
└────────┬────────┘
         │
         ├─ QdrantClient (semantic search)
         │
         └─ StructuralClient (configurable):
            ├─ VeracityMCPClient → veracity-engine MCP → Neo4j
            └─ Neo4jGatewayClient → Neo4j (direct)
```

## Configuration

### Environment Variables

```bash
# Optional: Enable MCP backend
VERACITY_PYTHON_PATH=python3
VERACITY_MCP_SERVER=/path/to/veracity-engine/core/mcp_server.py

# Neo4j credentials (required for both backends)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Qdrant configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=engineering_kb

# Ollama for embeddings
OLLAMA_URL=http://localhost:11434
```

### Code Configuration

#### With MCP Backend

```typescript
import { EnggContextAgent } from "./agents/EnggContextAgent.js";

const agent = new EnggContextAgent({
  qdrant: {
    url: "http://localhost:6333",
    collection: "engineering_kb",
  },
  neo4j: {
    uri: "bolt://localhost:7687",
    user: "neo4j",
    password: "password",
  },
  veracityMCP: {
    pythonPath: "python3",
    serverPath: "/path/to/veracity-engine/core/mcp_server.py",
    env: {
      NEO4J_URI: "bolt://localhost:7687",
      NEO4J_USER: "neo4j",
      NEO4J_PASSWORD: "password",
    },
    timeout: 30000,
  },
  ollama: {
    url: "http://localhost:11434",
    embedModel: "nomic-embed-text",
    synthesisModel: "llama3.2",
  },
});
```

#### Without MCP Backend (Direct Neo4j)

```typescript
const agent = new EnggContextAgent({
  qdrant: {
    url: "http://localhost:6333",
    collection: "engineering_kb",
  },
  neo4j: {
    uri: "bolt://localhost:7687",
    user: "neo4j",
    password: "password",
  },
  ollama: {
    url: "http://localhost:11434",
    embedModel: "nomic-embed-text",
    synthesisModel: "llama3.2",
  },
});
```

## Synthesis Toggle

### Raw Mode (Evidence Only)

Returns unprocessed search results from both Qdrant and Neo4j/MCP:

```typescript
const request: QueryRequestWithMode = {
  query: "How does authentication work?",
  requestId: "req-123",
  timestamp: new Date().toISOString(),
  project: "my-project",
  synthesisMode: "raw", // Return raw evidence
};

const response = await agent.query(request);
// response.answer will be undefined
// response.results contains raw search results
```

### Synthesized Mode (Default)

Returns LLM-synthesized answer with citations:

```typescript
const request: QueryRequestWithMode = {
  query: "How does authentication work?",
  requestId: "req-123",
  timestamp: new Date().toISOString(),
  project: "my-project",
  synthesisMode: "synthesized", // Or omit for default
};

const response = await agent.query(request);
// response.answer contains synthesized answer
// response.answer.text - The answer
// response.answer.confidence - Confidence score
// response.answer.citations - Evidence used
// response.results contains raw search results
```

## API Usage

### HTTP Endpoint

```bash
# Raw mode
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does authentication work?",
    "requestId": "req-123",
    "timestamp": "2024-01-15T10:00:00Z",
    "project": "my-project",
    "synthesisMode": "raw"
  }'

# Synthesized mode (default)
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does authentication work?",
    "requestId": "req-123",
    "timestamp": "2024-01-15T10:00:00Z",
    "project": "my-project",
    "synthesisMode": "synthesized"
  }'
```

## Testing

### Unit Tests

```bash
npm test -- src/test/unit/veracity-mcp-client.test.ts
```

### Integration Tests (Requires MCP Server)

```bash
export RUN_MCP_INTEGRATION_TESTS=true
export VERACITY_MCP_SERVER=/path/to/mcp_server.py
export NEO4J_PASSWORD=your-password

npm test -- src/test/integration/veracity-mcp.test.ts
```

### E2E Tests (Requires Full Stack)

```bash
export RUN_MCP_E2E_TESTS=true
export VERACITY_MCP_SERVER=/path/to/mcp_server.py
export NEO4J_PASSWORD=your-password
export QDRANT_URL=http://localhost:6333

npm test -- src/test/e2e/mcp-synthesis-toggle.e2e.test.ts
```

## MCP Protocol Details

### Tools Used

- `query_codebase`: Main query tool for evidence retrieval
- `list_projects`: Health check to verify MCP connectivity

### Evidence Packet Format

Veracity-engine returns evidence in this format:

```markdown
## Evidence Packet

**Query**: your query here
**Confidence**: 85%

### Code Evidence

- File: src/auth/middleware.ts (line 45-67)
  ```typescript
  // code snippet
  ```

### Graph Relationships

- AuthMiddleware -> UserService (DEPENDS_ON)
- UserService -> Database (CALLS)
```

The gateway parses this and converts to `StructuralResult` format.

## Benefits of MCP Backend

1. **Deterministic**: MCP always returns raw evidence, no LLM hallucination
2. **Veracity Checking**: Built-in staleness and orphan detection
3. **Conversation Support**: MCP server maintains conversation context
4. **Isolation**: Gateway doesn't need direct Neo4j driver
5. **Future-proof**: Can swap MCP implementation without gateway changes

## Migration Path

Existing deployments continue working with direct Neo4j. To migrate:

1. Deploy veracity-engine with MCP server
2. Add `veracityMCP` config to gateway
3. Test with both backends (A/B testing)
4. Switch to MCP backend when confident
5. Optional: Remove direct Neo4j dependency

## Troubleshooting

### MCP Connection Failed

```
Error: Failed to connect to veracity MCP: spawn python3 ENOENT
```

**Solution**: Check `VERACITY_PYTHON_PATH` is correct

### No Results from MCP

```
Found 0 relationships
```

**Solution**: Ensure project is indexed in veracity-engine:

```bash
python3 core/build_graph.py --project-name my-project --root-dir /path/to/code
```

### Synthesis Not Working

```
response.answer is undefined
```

**Solution**: Check Ollama or synthesis provider is configured and running

## Performance

- **MCP Overhead**: ~50-100ms additional latency vs direct Neo4j
- **Synthesis Overhead**: ~500-2000ms depending on model (llama3.2 vs glm-4.7)
- **Recommendation**: Use raw mode for latency-sensitive queries

## Future Enhancements

- [ ] Connection pooling for MCP clients
- [ ] Caching MCP responses
- [ ] Fallback to direct Neo4j if MCP fails
- [ ] Multiple MCP servers for load balancing
- [ ] WebSocket transport for MCP (vs stdio)
