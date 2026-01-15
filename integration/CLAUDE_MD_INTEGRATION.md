# ESS Integration for Project CLAUDE.md

Add this section to your project's `CLAUDE.md` file to enable Claude Code agents to use the Engineering Support System (ESS) for dev context tracking.

---

## Copy This Section to Your CLAUDE.md

```markdown
## Engineering Support System (ESS) Integration

This project is tracked by ESS for work item management and code traceability.

### MCP Tools Available

When ESS MCP server is connected, these tools are automatically available:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `query_codebase` | Query knowledge graph for code evidence | Before making architecture assumptions |
| `create_work_item` | Create new work item (feature, bug, task) | When starting new work or discovering bugs |
| `query_work_items` | List work items with filters (status, priority) | To check project status and outstanding work |
| `get_work_context` | Get comprehensive context for a work item | To understand what code relates to a work item |
| `trace_file_to_work` | Find work items related to a file | When modifying a file, understand its history |
| `update_work_item` | Update status, priority, assignees | When work progresses or is completed |
| `record_code_change` | Record git commits | Automatic via git watcher (or manual) |
| `link_code_to_work` | Link commits to work items | Manual linking when auto-link fails |
| `analyze_code_for_work` | Auto-detect TODOs/FIXMEs and create work items | During code review or cleanup |
| `register_project` | Register new project with ESS | One-time setup for new projects |
| `index_project` | Index/re-index project in knowledge graph | After major changes or initial setup |
| `list_projects` | List all indexed projects | To verify project is registered |

### Before Making Changes

Use MCP tools to understand work context:

```
# Check related work items for a file
trace_file_to_work(file_path="src/path/to/file.ts", project_name="YOUR_PROJECT")

# Get outstanding work items
query_work_items(project_name="YOUR_PROJECT", status="open")

# Understand codebase structure
query_codebase(project_name="YOUR_PROJECT", question="What components handle authentication?")
```

### After Making Changes

1. **Auto-linking**: Git watcher automatically detects commits and links them to work items
2. **Manual linking**: Use `link_code_to_work` if auto-link fails
3. **Status updates**: Use `update_work_item` when work is completed

### Commit Message Convention

Use conventional commits for automatic work type detection:

- `feat: description` → Creates/links to feature work item
- `fix: description` → Creates/links to bug work item
- `refactor: description` → Creates/links to refactor work item
- `chore: description` → Creates/links to chore work item
- `docs: description` → Creates/links to docs work item

### Kanban Board

View project status at: http://localhost:5173 (or https://ess.ping-gadgets.com/ui)

### GitHub Integration

If GitHub webhooks are configured:
- Issues sync bidirectionally with work items
- PRs link to work items automatically
- Labels map to priorities (critical, high, medium, low)
```

---

## Configuration Required

### 1. Add MCP Server to Claude Code

#### Local Development (stdio transport)

Add to your project's `.mcp.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ess-veracity": {
      "command": "python3",
      "args": ["/path/to/engg-support-system/veracity-engine/core/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password"
      }
    }
  }
}
```

#### Production (HTTP transport)

```json
{
  "mcpServers": {
    "ess-veracity": {
      "type": "http",
      "url": "https://ess.ping-gadgets.com/mcp",
      "env": {
        "ESS_API_KEY": "${ESS_API_KEY}"
      }
    }
  }
}
```

### 2. Register Project with ESS

Use the MCP tool (no local scripts needed):

```
# Via MCP (recommended)
register_project(
    project_name="your-project",
    root_dir="/path/to/your/project",
    watch_mode="lazy"
)

# Then index the project
index_project(project_name="your-project")
```

Or use the convenience script for initial setup:

```bash
cd ~/Projects/engg-support-system/integration
./register-project.sh your-project /path/to/your/project
```

### 3. Configure Git Watcher (Optional)

The git watcher automatically detects commits and creates work items.

Add to your project's `.env`:
```bash
ESS_PROJECT_NAME=your-project
ESS_WATCHED_BRANCHES=main,develop
```

### 4. Setup GitHub Webhook (Optional)

For bidirectional GitHub issue sync:

1. Go to https://github.com/OWNER/REPO/settings/hooks
2. Add webhook:
   - Payload URL: `https://ess.ping-gadgets.com/api/webhooks/github`
   - Content type: `application/json`
   - Secret: Generate with `openssl rand -hex 32`
   - Events: Issues, Pull requests

---

## Verification

Test ESS integration via MCP tools:

```
# List indexed projects
list_projects()

# Check project is indexed
query_codebase(project_name="YOUR_PROJECT", question="List all files")

# View work items
query_work_items(project_name="YOUR_PROJECT", limit=5)
```

Or via HTTP (when deployed):

```bash
# Health check
curl http://localhost:8000/health

# List work items
curl "http://localhost:8000/api/work-items?project=YOUR_PROJECT&limit=5"
```

---

## Automatic Integration (Hooks)

For fully automatic ESS integration, install the Claude Code hooks.

### What the Hooks Do

| Hook | When | What |
|------|------|------|
| Session Start | New session | Injects work items summary |
| Pre-Edit | Before file changes | Shows related work items |
| Post-Commit | After git commit | Records commit in ESS |

### Quick Setup

1. Copy the example settings:
```bash
cp ~/Projects/engg-support-system/integration/claude-code-hooks/settings.example.json \
   .claude/settings.json
```

2. Update paths in the file to match your ESS location

3. Set environment variables:
```bash
export ESS_URL="http://localhost:8000"
export ESS_PROJECT="your-project"  # Optional
```

4. Start ESS HTTP server:
```bash
cd ~/Projects/engg-support-system/veracity-engine
python -m core.http_server
```

### Full Hook Documentation

See `integration/claude-code-hooks/README.md` for detailed setup and troubleshooting.

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────────┐
│                    ESS MCP TOOLS QUICK REFERENCE                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUERY & UNDERSTAND                                             │
│  ─────────────────                                              │
│  query_codebase         → Search code structure & relationships │
│  query_work_items       → List work items with filters          │
│  get_work_context       → Full context for a work item          │
│  trace_file_to_work     → What work items touched this file?    │
│                                                                 │
│  CREATE & UPDATE                                                │
│  ───────────────                                                │
│  create_work_item       → Create feature/bug/task               │
│  update_work_item       → Update status/priority/assignees      │
│  record_code_change     → Record git commit (usually auto)      │
│  link_code_to_work      → Link commit to work item              │
│                                                                 │
│  ANALYZE & SETUP                                                │
│  ───────────────                                                │
│  analyze_code_for_work  → Detect TODOs/FIXMEs → work items      │
│  register_project       → Register new project                  │
│  index_project          → Index/re-index codebase               │
│  list_projects          → List all indexed projects             │
│                                                                 │
│  AUTOMATIC (via hooks)                                          │
│  ────────────────────                                           │
│  SessionStart           → Auto-inject project context           │
│  PreToolUse (Edit)      → Auto-show related work items          │
│  PostToolUse (Bash)     → Auto-track git commits                │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```
