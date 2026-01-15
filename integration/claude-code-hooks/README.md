# ESS Claude Code Hooks

Automatic integration between ESS and Claude Code agents.

## What These Hooks Do

| Hook | Type | Trigger | Action |
|------|------|---------|--------|
| `ess-session-context.py` | SessionStart | Session begins | Injects project work items summary |
| `ess-file-context.py` | PreToolUse | Before Edit/Write | Injects related work items for file |
| `ess-commit-tracker.py` | PostToolUse | After git commit | Records commit in ESS |

## Setup

### 1. Add Hooks to Claude Code Settings

Add to your project's `.claude/settings.json` or global `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "python3 /path/to/engg-support-system/integration/claude-code-hooks/ess-session-context.py"
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "python3 /path/to/engg-support-system/integration/claude-code-hooks/ess-file-context.py"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "command": "python3 /path/to/engg-support-system/integration/claude-code-hooks/ess-commit-tracker.py"
      }
    ]
  }
}
```

### 2. Set Environment Variables

Add to your shell profile (`.zshrc`, `.bashrc`) or project `.env`:

```bash
export ESS_URL="http://localhost:8000"  # ESS HTTP server URL
export ESS_PROJECT="your-project-name"   # Optional: override auto-detection
```

### 3. Start ESS HTTP Server

The hooks require the ESS HTTP server to be running:

```bash
cd /path/to/engg-support-system/veracity-engine
python -m core.http_server --port 8000
```

Or use Docker:

```bash
docker compose -f docker-compose.prod.yml up veracity-engine
```

## How It Works

### Session Start

When you start a Claude Code session:

```
1. Hook runs: ess-session-context.py
2. Queries: GET /api/project-context/{project}
3. Injects: Work item summary into conversation

Example output:
─────────────────────────────────────────
## ESS Dev Context: pinglearn

**Work Items:** 5 open | 2 in progress | 1 blocked

**High Priority:**
- [bug] Fix quiz timer not stopping (open) `WORK-abc123`
- [feature] Add student progress tracking (in_progress) `WORK-def456`

**Tips:**
- Use `trace_file_to_work(file_path, project)` before modifying files
─────────────────────────────────────────
```

### Before File Edits

When an agent is about to modify a file:

```
1. Hook runs: ess-file-context.py
2. Queries: GET /api/file-context/{project}?file_path={path}
3. Injects: Related work items for that file

Example output:
─────────────────────────────────────────
**ESS Context for `src/hooks/useQuiz.ts`:**
Related work items:
  - [bug] Fix quiz timer not stopping (open)
  - [feature] Add quiz analytics (in_progress)

This file is related to: Fix quiz timer, Add quiz analytics. Consider updating these work items.
─────────────────────────────────────────
```

### After Git Commits

When an agent makes a git commit:

```
1. Hook runs: ess-commit-tracker.py
2. Parses: git log for commit info
3. Posts: POST /api/record-commit/{project}
4. Records: Commit in ESS graph

Example output (to stderr):
─────────────────────────────────────────
**ESS Commit Tracked:**
- Commit: `abc12345`
- Files recorded: 3
- Inferred type: bug (confidence: 95%)
─────────────────────────────────────────
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ESS_URL` | `http://localhost:8000` | ESS HTTP server URL |
| `ESS_PROJECT` | Auto-detected | Override project name |

### Auto-Detection

If `ESS_PROJECT` is not set, the hooks attempt to detect the project name from:

1. Current working directory path (looks for `/Projects/` pattern)
2. Git repository name
3. Last directory component

## Troubleshooting

### Hooks not running

1. Check hook files are executable: `chmod +x *.py`
2. Verify Python 3 is available: `which python3`
3. Check Claude Code settings: `cat .claude/settings.json`

### ESS not responding

1. Check ESS is running: `curl http://localhost:8000/health`
2. Check Neo4j is running: `docker ps | grep neo4j`
3. Start ESS: `python -m core.http_server`

### Project not found

1. Index the project: `index_project(project_name="...", root_dir="...")`
2. Or use register script: `./integration/register-project.sh myproject /path`

### No context injected

1. Check ESS_PROJECT env var is set correctly
2. Verify project is indexed: `list_projects()`
3. Check for work items: `query_work_items(project_name="...")`

## Security Notes

- Hooks run locally, no data sent externally
- ESS HTTP server should only be accessible locally
- For production, use authentication (TODO)
