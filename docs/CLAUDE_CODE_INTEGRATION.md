# Claude Code Integration with ESS Veracity Engine

**Status**: Phase 2 - Claude Code MCP Integration Complete
**Date**: 2026-01-15
**VPS**: ess.ping-gadgets.com (72.60.204.156)

---

## Overview

This guide shows how to use the ESS (Engineering Support System) veracity-engine from Claude Code via the Model Context Protocol (MCP). You can query both local and VPS-hosted codebases for evidence-based architectural insights.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
├─────────────────────────────────────────────────────────────────┤
│  MCP Servers (configured in ~/.config/claude-code/config.json) │
│                                                                  │
│  ├─ veracity-local  → bolt://localhost:7687                    │
│  │   └─ Local Neo4j for dev/test projects                      │
│  │                                                              │
│  └─ veracity-ess    → bolt://localhost:7688                    │
│      └─ SSH tunnel to VPS Neo4j (ESS codebase indexed)         │
└─────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
    ┌────────────┐                 ┌─────────────┐
    │ Local Neo4j│                 │ SSH Tunnel  │
    │ (port 7687)│                 │ (port 7688) │
    └────────────┘                 └──────┬──────┘
                                          │
                                          ▼
                                   ┌──────────────────┐
                                   │ VPS Neo4j        │
                                   │ 72.60.204.156    │
                                   │ Port 7687        │
                                   │                  │
                                   │ Contains:        │
                                   │ - ESS codebase   │
                                   │ - 1,750 nodes    │
                                   └──────────────────┘
```

---

## Setup

### 1. SSH Tunnel to ESS VPS

Before using the `veracity-ess` server, establish an SSH tunnel:

```bash
# Forward VPS Neo4j (7687) to local port 7688
ssh -L 7688:ess-neo4j:7687 -L 6334:ess-qdrant:6333 root@72.60.204.156 -N -f

# Verify tunnel is active
ps aux | grep "ssh.*7688"
```

**Why?**
- VPS Neo4j is not publicly exposed (security)
- SSH tunnel provides encrypted access
- Port 7688 avoids conflict with local Neo4j (7687)

**Tunnel Mapping**:
- `localhost:7688` → VPS Neo4j (`ess-neo4j:7687`)
- `localhost:6334` → VPS Qdrant (`ess-qdrant:6333`)

### 2. Verify Configuration

Claude Code should auto-load `~/.config/claude-code/config.json`:

```json
{
  "mcpServers": {
    "veracity-local": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["/Users/umasankr/Projects/engg-support-system/veracity-engine/core/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_PASSWORD": "password",
        "NEO4J_USER": "neo4j"
      }
    },
    "veracity-ess": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["/Users/umasankr/Projects/engg-support-system/veracity-engine/core/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J_PASSWORD": "password123",
        "NEO4J_USER": "neo4j"
      }
    }
  }
}
```

**Key Details**:
- `veracity-local`: For local projects (e.g., dev work on other codebases)
- `veracity-ess`: For querying the ESS codebase itself on VPS
- Different passwords: local uses `password`, VPS uses `password123`

### 3. Test Connection

In a Claude Code session:

```
Use the veracity-ess MCP server to list_projects
```

Expected response:
```
# Indexed Projects

| Project | Nodes |
|---------|-------|
| ess     | 1,750 |
```

---

## When to Use Local vs ESS Search

### Use `veracity-local` When:
- ✅ Querying your local development projects
- ✅ Testing new indexing on a codebase
- ✅ Experimenting with graph queries
- ✅ Working on projects NOT deployed to VPS

### Use `veracity-ess` When:
- ✅ Querying the ESS codebase architecture
- ✅ Understanding gateway/veracity-engine/knowledge-base structure
- ✅ Finding where specific ESS features are implemented
- ✅ Analyzing ESS dependencies and relationships

**Example Decision**:
- Question: "Where is the ESS gateway health endpoint defined?"
  - Answer: Use `veracity-ess` (ESS codebase is on VPS)
- Question: "What are the main components of my pinglearn project?"
  - Answer: Use `veracity-local` (assuming pinglearn is indexed locally)

---

## Conversation Workflows

### Workflow 1: Simple Query (One-Shot)

**Scenario**: Quick architectural question

```
# In Claude Code chat:
Use veracity-ess to query_codebase:
- project_name: ess
- question: What is the gateway architecture?
- max_results: 20
```

**Expected Result**:
- Evidence-based response with file paths
- Code snippets with line numbers
- Confidence score (0-100%)
- Query ID for feedback

**When to Use**: Single factual questions that don't need follow-up

---

### Workflow 2: Multi-Turn Conversation

**Scenario**: Exploring a topic with follow-up questions

#### Step 1: Create Conversation

```
Use veracity-ess to create_conversation:
- project_name: ess
```

**Response**:
```
Session ID: `abc123-def456-...`
Project: ess
```

**Save the session_id** for follow-up queries.

#### Step 2: Ask Initial Question

```
Use veracity-ess to continue_conversation:
- session_id: abc123-def456-...
- project_name: ess
- question: What are the main gateway components?
```

#### Step 3: Ask Follow-Up Questions

```
Use veracity-ess to continue_conversation:
- session_id: abc123-def456-...
- project_name: ess
- question: How does the health endpoint work?
```

**Context-Aware Benefits**:
- "health endpoint" is understood in context of previous "gateway components"
- Evidence is linked across queries (query provenance)
- Session history maintained in Neo4j

#### Step 4: Review History

```
Use veracity-ess to get_conversation_history:
- session_id: abc123-def456-...
- limit: 5
```

**When to Use**: Exploratory analysis, debugging flows, understanding complex systems

---

### Workflow 3: Provide Feedback

After receiving query results, improve future queries:

```
Use veracity-ess to provide_feedback:
- query_id: [from previous query response]
- rating: useful | not_useful | partial
- comment: "Results were accurate but missing X..."
```

**Feedback Types**:
- `useful`: Query results were helpful
- `not_useful`: Query results didn't answer the question
- `partial`: Some relevant results, but incomplete

**Impact**: Feedback stored in Neo4j for continuous improvement

---

## Example Conversations

### Example 1: Understanding Gateway Health Checks

```plaintext
You: Use veracity-ess to create_conversation for project "ess"

Claude: Session ID: `550e8400-e29b-41d4-a716-446655440000`

You: Use veracity-ess to continue_conversation:
     - session_id: 550e8400-e29b-41d4-a716-446655440000
     - project_name: ess
     - question: Where is the gateway health endpoint defined?

Claude: [Evidence packet showing:]
       - File: gateway/src/routes/health.ts
       - Function: healthCheckHandler
       - Dependencies: Neo4j, Qdrant, Redis clients
       - Confidence: 92%

You: Use veracity-ess to continue_conversation:
     - session_id: 550e8400-e29b-41d4-a716-446655440000
     - project_name: ess
     - question: What services does the health check test?

Claude: [Context-aware evidence showing:]
       - Neo4j connection test
       - Qdrant connection test
       - Redis connection test
       - Ollama availability check
       - Related files: src/db/neo4j.ts, src/db/qdrant.ts
```

**Key Points**:
- First query establishes context (health endpoint location)
- Second query benefits from context (knows we're discussing health checks)
- Evidence is linked across both queries

---

### Example 2: Finding Feature Implementation

```plaintext
You: Use veracity-ess to query_codebase:
     - project_name: ess
     - question: How is conversation state managed in veracity-engine?
     - max_results: 15

Claude: [Evidence packet showing:]
       - File: veracity-engine/core/conversation.py
       - Class: ConversationManager
       - Methods: create_conversation, add_query_to_conversation
       - Neo4j storage: Conversation nodes, CONTAINS relationships
       - Query ID: qry_abc123

You: Use veracity-ess to provide_feedback:
     - query_id: qry_abc123
     - rating: useful
     - comment: Found exactly what I needed

Claude: Feedback recorded. Thank you!
```

---

### Example 3: Multi-Project Query

```plaintext
# Query local project
You: Use veracity-local to query_codebase:
     - project_name: pinglearn
     - question: What are the main quiz components?

Claude: [Evidence from local Neo4j]

# Query ESS architecture (same conversation)
You: Use veracity-ess to query_codebase:
     - project_name: ess
     - question: How does ESS handle multi-project indexing?

Claude: [Evidence from VPS Neo4j showing project registry]
```

---

## Available MCP Tools

### Core Query Tools

1. **query_codebase**
   - One-shot evidence-based queries
   - Returns: code locations, relationships, confidence score
   - Use for: Quick factual questions

2. **create_conversation**
   - Start multi-turn session
   - Returns: session_id
   - Use for: Exploratory analysis

3. **continue_conversation**
   - Context-aware follow-up queries
   - Requires: session_id from create_conversation
   - Use for: Building on previous queries

4. **get_conversation_history**
   - Review past queries in a session
   - Shows: questions, confidence, evidence counts
   - Use for: Recalling previous context

5. **list_conversations**
   - View all conversation sessions
   - Filter by project
   - Use for: Finding old exploration sessions

### Component Analysis Tools

6. **get_component_map**
   - Static analysis of a file
   - Returns: imports, dependents, definitions, calls
   - Use for: Understanding component structure

7. **get_file_relationships**
   - All relationships for a specific file
   - Returns: DEFINES, CALLS, DEPENDS_ON edges
   - Use for: Dependency analysis

8. **list_projects**
   - Show all indexed projects
   - Returns: project names, node counts
   - Use for: Discovering available projects

### Feedback & Management Tools

9. **provide_feedback**
   - Rate query results
   - Options: useful, not_useful, partial
   - Use for: Improving future queries

10. **register_project**
    - Add new project to registry
    - Requires: name, root directory
    - Use for: Setting up new codebases

11. **index_project**
    - Build/update knowledge graph
    - Options: incremental, force rebuild
    - Use for: Keeping index up-to-date

12. **ingest_files**
    - Incremental file updates
    - Faster than full re-index
    - Use for: Real-time updates

---

## Best Practices

### 1. Start with Simple Queries

Before diving into conversations, test with one-shot queries:

```
Use veracity-ess to query_codebase:
- project_name: ess
- question: List all gateway routes
```

### 2. Use Conversations for Exploration

When you need multiple related queries:

```
# Step 1: Create session
Use veracity-ess to create_conversation for "ess"

# Step 2-N: Ask related questions
Use continue_conversation with same session_id
```

### 3. Provide Feedback

Help improve the system:

```
After every query, consider:
- Was the evidence accurate?
- Was it complete?
- Was it relevant?

Then use provide_feedback with the query_id
```

### 4. Check Confidence Scores

Evidence packets include confidence (0-100%):
- **90-100%**: Highly reliable
- **70-89%**: Good confidence
- **50-69%**: Moderate confidence
- **<50%**: Low confidence (verify manually)

### 5. Use Component Maps for Architecture

For understanding file structure:

```
Use veracity-ess to get_component_map:
- project_name: ess
- component_path: gateway/src/routes/health.ts
```

Returns:
- What the file imports
- What imports this file
- Functions/classes defined
- Call relationships

---

## Troubleshooting

### Issue 1: "Connection refused" on veracity-ess

**Cause**: SSH tunnel not established

**Fix**:
```bash
# Start tunnel
ssh -L 7688:ess-neo4j:7687 -L 6334:ess-qdrant:6333 root@72.60.204.156 -N -f

# Verify
ps aux | grep "ssh.*7688"
```

### Issue 2: "Project not found: ess"

**Cause**: Wrong MCP server or tunnel pointing to wrong Neo4j

**Fix**:
- Verify using `veracity-ess` (not `veracity-local`)
- Verify tunnel is to correct VPS
- Test with: `Use veracity-ess to list_projects`

### Issue 3: Low Confidence Scores (<50%)

**Causes**:
- Query too vague
- Relevant code not indexed
- Project recently updated (index stale)

**Fix**:
1. Make query more specific
2. Run `index_project` with `force=true`
3. Check if file extensions are supported (see veracity-engine/CLAUDE.md)

### Issue 4: Empty Results

**Causes**:
- Project not indexed
- Wrong project name
- Code doesn't exist

**Fix**:
1. Run `list_projects` to verify name
2. Check project is indexed: `query_codebase` with known file
3. Re-index: `index_project`

### Issue 5: MCP Server Won't Start

**Cause**: Python dependencies missing or wrong Python version

**Fix**:
```bash
# Verify Python version
/opt/homebrew/bin/python3.11 --version

# Install dependencies
cd /Users/umasankr/Projects/engg-support-system/veracity-engine
pip install -r requirements.txt
```

---

## Performance Tips

### 1. Limit Results

For faster responses:
```
query_codebase with max_results: 10  # Instead of default 20
```

### 2. Use Specific Queries

Instead of:
```
question: Tell me about the gateway
```

Use:
```
question: What routes are defined in gateway/src/routes/?
```

### 3. Reuse Conversations

Creating a conversation has overhead. Reuse session_id for multiple queries.

### 4. Close Tunnels When Done

SSH tunnels consume resources:
```bash
# Find tunnel PID
ps aux | grep "ssh.*7688"

# Kill it
kill <PID>
```

---

## Security Considerations

### 1. Credentials in Config

The config file contains Neo4j passwords. Protect it:
```bash
chmod 600 ~/.config/claude-code/config.json
```

### 2. SSH Key Protection

Ensure your SSH key is secure:
```bash
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### 3. Tunnel Security

SSH tunnels are encrypted, but:
- Don't share tunnel ports with others
- Close tunnels when not in use
- Use key-based auth (not passwords)

### 4. VPS Access

The VPS password is in `~/Projects/.creds/ess-vps.txt`:
- Keep file permissions: `chmod 600`
- Don't commit to git
- Rotate password periodically

---

## Advanced Usage

### Query Provenance

Conversations link queries together:

```cypher
// In Neo4j browser (local:7474 or via tunnel)
MATCH (c:Conversation)-[:CONTAINS]->(q:Query)
WHERE c.id = 'session-id-here'
RETURN c, q
ORDER BY q.timestamp
```

Shows full query chain with evidence links.

### Custom Cypher Queries

For advanced users, query Neo4j directly:

```bash
# Via tunnel to VPS
ssh root@72.60.204.156

# Inside VPS
docker exec -it ess-neo4j cypher-shell -u neo4j -p password123

# Run Cypher
MATCH (n:File {project: 'ess'})
WHERE n.path CONTAINS 'gateway'
RETURN n.path, n.name
LIMIT 10;
```

### Bulk Indexing

For multiple projects:

```bash
# SSH to VPS
ssh root@72.60.204.156

# Run indexing
cd /home/devuser/Projects/engg-support-system/veracity-engine
python3 core/build_graph.py --project-name project1 --root-dir /path/to/project1
python3 core/build_graph.py --project-name project2 --root-dir /path/to/project2
```

---

## Related Documentation

- **VPS Deployment**: See `docs/VPS_DEPLOYMENT_STATUS.md`
- **Veracity Engine**: See `veracity-engine/CLAUDE.md`
- **Gateway API**: See `gateway/README.md`
- **Integration Plan**: See `docs/plans/INTEGRATION_PLAN.md`

---

## Support

### Logs

MCP server logs to stderr (Claude Code will show errors).

### Manual Testing

Test MCP server directly:
```bash
cd /Users/umasankr/Projects/engg-support-system/veracity-engine
python3 core/mcp_server.py
# Should start without errors
```

### Neo4j Browser

Access Neo4j directly:
- Local: http://localhost:7474
- VPS (via tunnel): http://localhost:7474 (forward port 7474 in SSH tunnel)

---

**Document Status**: Complete
**Last Updated**: 2026-01-15
**Maintained By**: ESS Project
**Phase**: 2 - Claude Code Integration