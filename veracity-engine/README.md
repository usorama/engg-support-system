# Veracity Engine - Deterministic GraphRAG for AI Agents

Veracity Engine is a **Ground-Truth Context System (GTCS)** that indexes codebases into a Neo4j knowledge graph, providing AI agents with deterministic, evidence-based architectural context. Unlike traditional RAG systems, Veracity validates the "veracity" of information (staleness, orphans, contradictions) before delivery.

## Key Features

- **Deterministic Context**: Evidence-only mode with no LLM hallucination
- **Veracity Logic**: Automated detection of `STALE_DOCS`, `ORPHANED_NODES`, and contradictions
- **MCP Server**: Native integration with Claude Code and AI agents
- **Autonomous Sync**: File watcher daemon keeps projects in sync automatically
- **Multi-tenant**: Isolate multiple projects in a single Neo4j instance

## Quick Start

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Docker**: For Neo4j infrastructure
- **Ollama**: For embeddings (`ollama pull nomic-embed-text`)

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/usorama/veracity-engine.git
cd veracity-engine
pip install -r requirements.txt
```

### 2. Start Infrastructure

```bash
cd infra && docker compose up -d
```

This starts:
- Neo4j: `http://localhost:7474` (bolt://localhost:7687)
- NeoDash: `http://localhost:5005`

### 3. Index a Project

```bash
python3 core/build_graph.py \
  --project-name myproject \
  --root-dir /path/to/your/project \
  --target-dirs src tests docs
```

### 4. Query the Knowledge Graph

```bash
python3 core/ask_codebase.py \
  --project-name myproject \
  "What are the main components?"
```

---

## Installation Options

### Option A: Autonomous Daemon (Recommended)

The daemon automatically watches registered projects and re-indexes when files change.

```bash
# Install the daemon
./scripts/install-daemon.sh

# Register a project
veracityd register myproject /path/to/project

# Start watching
veracityd start

# Check status
veracityd status
```

The daemon will:
- Start automatically on login (via launchd on macOS)
- Watch for file changes in real-time
- Debounce rapid changes (5-second delay)
- Re-index incrementally

### Option B: MCP Server for Claude Code

Enable AI agents to query the knowledge graph natively.

```bash
# Install MCP server
./scripts/install-mcp.sh
```

Then add to your Claude config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "veracity": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["/path/to/veracity-engine/core/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "PYTHONPATH": "/path/to/veracity-engine"
      }
    }
  }
}
```

Restart Claude Code. The following tools become available:
- `veracity:query_codebase` - Query for code evidence
- `veracity:get_component_map` - Generate architecture maps
- `veracity:list_projects` - List indexed projects
- `veracity:get_file_relationships` - Get file dependencies

### Option C: Manual Indexing

For one-time or CI/CD integration:

```bash
export PYTHONPATH=/path/to/veracity-engine
python3 core/build_graph.py \
  --project-name myproject \
  --root-dir /path/to/project
```

---

## Usage Examples

### Query with Evidence-Only Mode (Default)

```bash
python3 core/ask_codebase.py \
  --project-name myproject \
  "What functions handle authentication?"
```

Returns deterministic evidence with file paths, line numbers, and confidence scores.

### Query with LLM Synthesis

```bash
python3 core/ask_codebase.py \
  --project-name myproject \
  --allow-synthesis \
  "Explain the authentication flow"
```

### JSON Output for Programmatic Use

```bash
python3 core/ask_codebase.py \
  --project-name myproject \
  --json \
  "List all API endpoints"
```

### Daemon Commands

```bash
veracityd start          # Start watching registered projects
veracityd stop           # Stop the daemon
veracityd status         # Show status and registered projects
veracityd register <name> <path>  # Register a project
veracityd unregister <name>       # Unregister a project
veracityd list           # List all registered projects
veracityd logs           # Tail the daemon log
```

---

## Configuration

### Project Registry

Projects are configured in `~/.veracity/projects.yaml`:

```yaml
version: 1
projects:
  myproject:
    root_dir: /path/to/project
    target_dirs:
      - src
      - tests
      - docs
    watch_mode: realtime  # realtime | polling | git-only
    debounce: 5           # seconds
    file_patterns:
      - "*.py"
      - "*.md"
      - "*.ts"
```

### Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EMBED_MODEL=nomic-embed-text
```

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent / Claude Code                   │
├─────────────────────────────────────────────────────────────┤
│  MCP Tools: query_codebase, get_component_map, etc.         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Veracity Engine                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ MCP Server  │  │   Watcher   │  │  Query      │         │
│  │             │  │   Daemon    │  │  Engine     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│              ┌─────────────────────┐                        │
│              │   Neo4j Graph DB    │                        │
│              │   (Knowledge Graph) │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

- **Nodes**: File, Class, Function, Document, Component
- **Relationships**: DEFINES, CALLS, DEPENDS_ON, HAS_COMPONENT
- **Veracity Fields**: confidence_score, is_stale, faults

---

## Repository Structure

```text
veracity-engine/
├── core/                    # Python engines
│   ├── build_graph.py       # Indexing engine
│   ├── ask_codebase.py      # Query engine
│   ├── mcp_server.py        # MCP server for agents
│   ├── watcher_daemon.py    # File system watcher
│   └── project_registry.py  # Project configuration
├── scripts/
│   ├── veracityd            # Daemon control script
│   ├── install-daemon.sh    # Daemon installation
│   └── install-mcp.sh       # MCP server installation
├── infra/
│   ├── docker-compose.yml   # Neo4j + NeoDash
│   └── com.veracity.daemon.plist  # macOS launchd config
├── ui/                      # React dashboard
├── tests/                   # Test suite (471 tests)
└── docs/                    # Documentation
```

---

## Development

### Run Tests

```bash
python3 -m pytest tests/ -v
```

### Lint

```bash
flake8 core/ tests/
```

---

## Troubleshooting

### Query returns 0% confidence

This usually means the vector search limit is too low for multi-tenant deployments. The default has been increased to 500 results to handle projects with fewer nodes.

### Daemon not detecting changes

1. Check if the project is registered: `veracityd list`
2. Verify the target directories exist
3. Check logs: `veracityd logs`

### Neo4j connection refused

Ensure the infrastructure is running: `cd infra && docker compose up -d`

---

## License

Apache 2.0

---

**Status:** Alpha | **Version:** 0.1.0 | **Updated:** December 2025
