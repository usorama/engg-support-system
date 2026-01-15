# ESS Current State Report

**Date**: 2026-01-15
**Generated**: Post Phase 1-4 Implementation

---

## Projects Currently in ESS

### VPS (ess.ping-gadgets.com) - Production
**Total Projects**: 2

| Project | Nodes | Auto-Indexing | Watcher | Status |
|---------|-------|---------------|---------|--------|
| **ess** | 1,750 | ❌ No | N/A | Indexed once, static |
| **rad-engineer** | 564 | ✅ Yes | Running | Actively maintained |

**Watcher Daemon**: ✅ Running (PID 3458520)

**Registered Projects** (`/root/.veracity/projects.yaml`):
```yaml
rad-engineer-v2:
  root_dir: /home/devuser/Projects/rad-engineer-v2
  target_dirs: [rad-engineer/src, docs]
  watch_mode: realtime
  debounce: 10
  enabled: true
  file_patterns: [*.ts, *.tsx, *.md]
```

### Local Machine - Development
**Total Projects**: 1 (likely)

**Watcher Daemon**: ✅ Running (PID 847)

**Registered Projects** (`~/.veracity/projects.yaml`):
```yaml
pinglearn:
  root_dir: /Users/umasankr/Projects/pinglearn/pinglearn-app
  target_dirs: [tests, scripts, docs, src]
  watch_mode: realtime
  debounce: 5
  enabled: true
  file_patterns: [*.py, *.md, *.ts, *.tsx, *.js, *.jsx]
```

---

## Auto-Indexing Status

### Projects with Active Auto-Indexing: **2 of 3** (66%)

1. **rad-engineer-v2** (VPS)
   - ✅ Registered in veracity registry
   - ✅ Watcher daemon monitoring
   - ✅ Realtime file system events
   - ✅ Auto-indexes on every change (10s debounce)

2. **pinglearn** (Local)
   - ✅ Registered in veracity registry
   - ✅ Watcher daemon monitoring
   - ✅ Realtime file system events
   - ✅ Auto-indexes on every change (5s debounce)

### Projects WITHOUT Auto-Indexing: **1 of 3** (33%)

1. **ess** (VPS)
   - ❌ Not registered in veracity registry
   - ❌ No watcher monitoring
   - Status: Static snapshot, will become stale

---

## What Needs to Change for Projects to Stay Current

### Option 1: Register Existing Projects (Recommended)

For projects already indexed (like `ess`), register them for auto-indexing:

```bash
# On VPS
ssh root@72.60.204.156
cd /home/devuser/Projects/engg-support-system/veracity-engine

# Register ess project
python3 core/project_registry.py register ess \
  /home/devuser/Projects/engg-support-system \
  --target-dirs veracity-engine/core veracity-engine/tests gateway/src knowledge-base/src docs \
  --watch-mode realtime

# Restart watcher daemon to pick up new project
pkill -f watcher_daemon.py
python3 core/watcher_daemon.py --daemon
```

### Option 2: Git Commit Hooks (Per-Project)

Alternative to daemon, use git hooks for incremental indexing:

```bash
# In project repo
cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
# Auto-index to ESS on commit

cd /path/to/engg-support-system/veracity-engine
python3 core/build_graph.py \
  --project-name $(basename $(git rev-parse --show-toplevel)) \
  --root-dir $(git rev-parse --show-toplevel) \
  --incremental
EOF

chmod +x .git/hooks/post-commit
```

### Option 3: Scheduled Cron Jobs (Periodic)

For projects that change infrequently:

```bash
# Cron job (re-index every 6 hours)
0 */6 * * * cd /path/to/veracity-engine && python3 core/build_graph.py --project-name myproject --root-dir /path/to/project
```

---

## For ping-learn-pwa: What Needs to Happen

### Step 1: Deploy Code to VPS

```bash
# On VPS
cd /home/devuser/Projects
git clone <ping-learn-pwa-repo-url> ping-learn-pwa
# OR
rsync -avz --exclude node_modules ~/Projects/ping-learn-pwa/ root@72.60.204.156:/home/devuser/Projects/ping-learn-pwa/
```

### Step 2: Register with ESS

```bash
# On VPS
cd /home/devuser/Projects/engg-support-system/veracity-engine

python3 core/project_registry.py register ping-learn-pwa \
  /home/devuser/Projects/ping-learn-pwa \
  --target-dirs app/src app/prisma docs \
  --watch-mode realtime
```

### Step 3: Initial Indexing

```bash
# On VPS (inside Docker network)
NEO4J_URI="bolt://ess-neo4j:7687" \
NEO4J_PASSWORD="password123" \
python3 core/build_graph.py \
  --project-name ping-learn-pwa \
  --root-dir /home/devuser/Projects/ping-learn-pwa \
  --target-dirs app/src app/prisma docs
```

### Step 4: Sync to Qdrant

```bash
# On VPS
NEO4J_URI="bolt://ess-neo4j:7687" \
QDRANT_URL="http://ess-qdrant:6333" \
PROJECT_NAME="ping-learn-pwa" \
python3 scripts/sync-neo4j-to-qdrant.py
```

### Step 5: Restart Watcher (Pick Up New Project)

```bash
# On VPS
pkill -f watcher_daemon.py
cd /home/devuser/Projects/engg-support-system/veracity-engine
python3 core/watcher_daemon.py --daemon
```

### Step 6: Verify Auto-Indexing

```bash
# Make a test change
ssh root@72.60.204.156
cd /home/devuser/Projects/ping-learn-pwa
echo "// Test" >> app/src/test.ts

# Watch logs (should trigger re-index within 10s)
tail -f /home/devuser/Projects/engg-support-system/veracity-engine/logs/watcher.log
```

---

## MCP Server Configuration

### Current Setup

**Local Machine MCP Server**:
- Path: `/Users/umasankr/Projects/veracity-engine/core/mcp_server.py`
- Neo4j: `bolt://localhost:7687`
- Status: ✅ Running (multiple instances for Claude Code)

**VPS MCP Server**:
- Not currently exposed (runs via SSH tunnel only)
- Neo4j: `bolt://ess-neo4j:7687` (internal Docker network)
- Access: Via SSH tunnel on port 7688

### Recommended: Root-Level MCP Server

To make agent queries flow naturally, the MCP server should be accessible at Claude Code root level.

**Current Issue**: MCP server path is project-specific:
```json
{
  "veracity": {
    "command": "/opt/homebrew/bin/python3.11",
    "args": ["/Users/umasankr/Projects/veracity-engine/core/mcp_server.py"]
  }
}
```

**Recommendation**: Install veracity-engine globally or symlink:

```bash
# Option 1: Global Python package
cd /Users/umasankr/Projects/engg-support-system/veracity-engine
pip install -e .

# Then Claude Code config:
{
  "veracity": {
    "command": "veracity-mcp",  # Installed globally
    "env": {...}
  }
}

# Option 2: Symlink to Claude Code root
ln -s /Users/umasankr/Projects/engg-support-system/veracity-engine/core/mcp_server.py \
      ~/.claude/mcp-servers/veracity.py

# Then Claude Code config:
{
  "veracity": {
    "command": "/opt/homebrew/bin/python3.11",
    "args": ["~/.claude/mcp-servers/veracity.py"]
  }
}
```

---

## Project Management Tracking in ESS

### Current State: ❌ NO PROJECT MANAGEMENT FEATURES

ESS currently has:
- ✅ Code structure tracking (files, functions, classes)
- ✅ Dependency tracking (CALLS, DEPENDS_ON relationships)
- ✅ Conversation tracking (multi-turn queries)
- ✅ Feedback tracking (query ratings)
- ✅ Metrics tracking (query performance)

ESS does NOT have:
- ❌ Task/issue tracking
- ❌ Progress tracking
- ❌ Sprint/milestone tracking
- ❌ Story/epic management
- ❌ Time tracking
- ❌ Burndown charts
- ❌ Development lifecycle tracking

### Why This Is Missing

ESS was designed as a **code intelligence system**, not a project management tool. It focuses on:
- "What is the code structure?"
- "How do components relate?"
- "What does this function do?"

It does NOT focus on:
- "What tasks are incomplete?"
- "What's our sprint velocity?"
- "Who's working on what?"

### Should ESS Have Project Management?

**Arguments FOR**:
1. **Context for AI Agents**: Agents could understand current work status
2. **Development Progress**: Track what's built vs. what's planned
3. **Traceability**: Link code changes to user stories/issues
4. **Complete Picture**: Architecture + development status = full context

**Arguments AGAINST**:
1. **Scope Creep**: ESS is for code intelligence, not PM
2. **Tool Overlap**: GitHub Issues, Linear, Jira already exist
3. **Maintenance Burden**: More features = more complexity
4. **Integration Better**: Integrate with existing PM tools instead

### Recommendation: NEW FEATURE - "Dev Context Tracking"

Instead of full project management, add **lightweight development context**:

**New Node Types**:
```cypher
:WorkItem {
  id: str,
  type: enum(feature|bug|refactor|docs|test),
  title: str,
  status: enum(planned|in_progress|blocked|done),
  priority: enum(critical|high|medium|low),
  created_at: datetime,
  updated_at: datetime,
  github_issue_url: str?
}

:CodeChange {
  commit_sha: str,
  message: str,
  timestamp: datetime,
  author: str,
  files_changed: [str]
}
```

**New Relationships**:
```cypher
(:WorkItem)-[:IMPLEMENTED_BY]->(:File)
(:WorkItem)-[:BLOCKED_BY]->(:WorkItem)
(:WorkItem)-[:DEPENDS_ON]->(:WorkItem)
(:CodeChange)-[:ADDRESSES]->(:WorkItem)
(:CodeChange)-[:MODIFIED]->(:File)
```

**Benefits**:
- Lightweight (not a full PM system)
- Integrates with GitHub Issues (via URL)
- Provides context for agents
- Shows what code relates to what work
- Tracks development progress naturally

**Next Step**: This should be planned as a new feature after current tasks are complete.

---

## Summary

**Projects in ESS**: 3 total (2 VPS + 1 local)
**Auto-Indexing**: 2 of 3 (66%)
**Need to Register**: `ess` project on VPS
**ping-learn-pwa**: Ready to register and index on VPS

**Project Management**: ❌ Not currently implemented
**Recommendation**: Add lightweight "Dev Context Tracking" feature

**MCP Server**: Currently project-specific, should be root-level for natural agent queries

---

**Next Actions**:
1. Register `ess` project for auto-indexing on VPS
2. Deploy and register `ping-learn-pwa` on VPS
3. Plan "Dev Context Tracking" feature
4. Consider global MCP server installation

**Document Status**: CURRENT
**Last Updated**: 2026-01-15
