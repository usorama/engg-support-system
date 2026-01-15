#!/usr/bin/env python3
"""
Veracity Engine MCP Server (STORY-018)

Exposes the knowledge graph to AI agents via Model Context Protocol.
Provides deterministic, evidence-based responses - NO LLM hallucination.

Usage:
    # Direct execution
    python3 core/mcp_server.py

    # Via MCP CLI
    mcp dev core/mcp_server.py

    # Claude Code config (claude_desktop_config.json)
    {
        "mcpServers": {
            "veracity": {
                "command": "/opt/homebrew/bin/python3.11",
                "args": ["/path/to/veracity-engine/core/mcp_server.py"],
                "env": {"NEO4J_URI": "bolt://localhost:7687"}
            }
        }
    }
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Literal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)
from pydantic import BaseModel, Field

# Import core query engine
from core.ask_codebase import query_graph
from core.evidence_query import EvidenceQueryConfig, EvidenceOutputMode
from core.config import get_config
from core.conversation import ConversationManager, build_context_aware_query
from core.project_registry import register_project, WatchMode, get_project
from core.build_graph import CodeGraphBuilder
from core.file_ingestion import extract_file_metadata, extract_text_content
from core.metrics.query_metrics import QueryMetrics
from core.dev_context import DevContextManager, WorkItemNotFoundError

# Configure logging to stderr (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("veracity-mcp")

# Initialize MCP server
server = Server("veracity-engine")


# ============================================================================
# Tool Definitions
# ============================================================================

TOOLS = [
    Tool(
        name="query_codebase",
        description="""Query the Veracity Engine knowledge graph for code evidence.

Returns DETERMINISTIC, evidence-based results with:
- Exact file paths and line numbers
- Code relationships (calls, imports, defines)
- Veracity score (confidence, staleness, orphans)

NO LLM synthesis - only graph-derived facts.

Use this tool BEFORE making assumptions about code architecture.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The indexed project name (e.g., 'pinglearn', 'veracity-engine')"
                },
                "question": {
                    "type": "string",
                    "description": "Your question about the codebase. Be specific about what you need to know."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum evidence items to return (default: 20)",
                    "default": 20
                }
            },
            "required": ["project_name", "question"]
        }
    ),
    Tool(
        name="get_component_map",
        description="""Generate a comprehensive component architecture map.

Returns:
- Direct imports (what the component imports)
- Reverse dependencies (what imports this component)
- Type definitions used
- Relationships (CALLS, DEFINES, IMPORTS)

Similar to static analysis tools like madge.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The indexed project name"
                },
                "component_path": {
                    "type": "string",
                    "description": "Path to the component (e.g., 'src/components/UnifiedTeachingBoard.tsx')"
                }
            },
            "required": ["project_name", "component_path"]
        }
    ),
    Tool(
        name="list_projects",
        description="""List all indexed projects in the knowledge graph.

Returns project names, node counts, and last indexed timestamps.""",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="get_file_relationships",
        description="""Get all relationships for a specific file.

Returns:
- Functions/classes defined in the file
- What the file imports
- What imports this file
- Call relationships""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The indexed project name"
                },
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file from project root"
                }
            },
            "required": ["project_name", "file_path"]
        }
    ),
    Tool(
        name="provide_feedback",
        description="""Record user feedback on query results.

Stores feedback in Neo4j for continuous improvement of query quality.
Feedback is linked to the original query via query_id.

Rating values:
- "useful": The query results were helpful
- "not_useful": The query results were not helpful
- "partial": The query results were partially helpful""",
        inputSchema={
            "type": "object",
            "properties": {
                "query_id": {
                    "type": "string",
                    "description": "The query_id from the original query response"
                },
                "rating": {
                    "type": "string",
                    "description": "Feedback rating: 'useful', 'not_useful', or 'partial'",
                    "enum": ["useful", "not_useful", "partial"]
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment explaining the feedback"
                }
            },
            "required": ["query_id", "rating"]
        }
    ),
    Tool(
        name="register_project",
        description="""Register a new project for indexing and monitoring.

Adds the project to the registry (~/.veracity/projects.yaml) for automatic indexing.
The project will be tracked for changes and can be queried via other tools.

Watch modes:
- "realtime": File system events (watchdog) - recommended
- "polling": Periodic git HEAD check
- "git-only": Only on git commits""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Unique name for the project (used as tenant identifier)"
                },
                "root_dir": {
                    "type": "string",
                    "description": "Absolute path to project root directory"
                },
                "target_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Directories to index (relative to root). Default: ['src', 'core', 'lib', 'tests', 'docs']"
                },
                "watch_mode": {
                    "type": "string",
                    "description": "How to monitor for changes",
                    "enum": ["realtime", "polling", "git-only"],
                    "default": "realtime"
                }
            },
            "required": ["project_name", "root_dir"]
        }
    ),
    Tool(
        name="index_project",
        description="""Run full indexing of a registered project.

Builds/updates the Neo4j knowledge graph for the specified project.
This performs AST parsing, relationship extraction, and embedding generation.

Use incremental=false to force a full rebuild (clears existing data).
Use force=true to rebuild even if no changes detected.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The project name (must be registered first)"
                },
                "incremental": {
                    "type": "boolean",
                    "description": "Only process changed files (default: true)",
                    "default": True
                },
                "force": {
                    "type": "boolean",
                    "description": "Force rebuild even if no changes detected (default: false)",
                    "default": False
                }
            },
            "required": ["project_name"]
        }
    ),
    Tool(
        name="ingest_files",
        description="""Ingest specific files for real-time updates.

Use this for incremental updates when files change in a watched project.
Faster than full indexing - only processes the specified files.

Files are identified by path relative to project root.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The project name"
                },
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path from project root"
                            },
                            "content": {
                                "type": "string",
                                "description": "Optional file content (if not provided, will read from disk)"
                            },
                            "language": {
                                "type": "string",
                                "description": "File language (py, ts, js, go, etc.)"
                            }
                        },
                        "required": ["path"]
                    },
                    "description": "List of files to ingest"
                }
            },
            "required": ["project_name", "files"]
        }
    ),
    Tool(
        name="create_conversation",
        description="""Start a new conversation session for multi-turn queries.

Returns a session_id that should be used for follow-up queries.
Conversations maintain query history and enable context-aware responses.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The project this conversation is about"
                }
            },
            "required": ["project_name"]
        }
    ),
    Tool(
        name="continue_conversation",
        description="""Continue an existing conversation with context-aware query.

Uses conversation history to provide better context for follow-up questions.
Automatically links new queries to previous evidence for query provenance.

Use this instead of query_codebase when you have a session_id.""",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Conversation session ID from create_conversation"
                },
                "project_name": {
                    "type": "string",
                    "description": "The project name"
                },
                "question": {
                    "type": "string",
                    "description": "Your follow-up question"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum evidence items to return (default: 20)",
                    "default": 20
                }
            },
            "required": ["session_id", "project_name", "question"]
        }
    ),
    Tool(
        name="get_conversation_history",
        description="""Get the query history for a conversation.

Returns recent queries and their results for context.""",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Conversation session ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of queries to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["session_id"]
        }
    ),
    Tool(
        name="list_conversations",
        description="""List all conversations, optionally filtered by project.

Shows conversation metadata including query counts and timestamps.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Optional: filter by project name"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="create_work_item",
        description="""Create a new work item (feature, bug, task) in the dev context graph.

Supports idempotency via optional idempotency_token to prevent duplicate work items.
External system integration via external_id and source fields (e.g., github-issue-123).

Returns:
- work_item_uid: Generated UID for the work item
- created: Boolean indicating if item was newly created (false if idempotent duplicate)""",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Work item title"
                },
                "description": {
                    "type": "string",
                    "description": "Work item description"
                },
                "work_type": {
                    "type": "string",
                    "description": "Type of work: feature, bug, task, etc.",
                    "enum": ["feature", "bug", "task", "enhancement", "refactor"]
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level (default: medium)",
                    "enum": ["low", "medium", "high", "critical"],
                    "default": "medium"
                },
                "external_id": {
                    "type": "string",
                    "description": "External system ID (e.g., github-issue-123)"
                },
                "source": {
                    "type": "string",
                    "description": "External system name (e.g., github, jira)"
                },
                "idempotency_token": {
                    "type": "string",
                    "description": "Optional token for idempotent creation"
                }
            },
            "required": ["title", "description", "work_type"]
        }
    ),
    Tool(
        name="record_code_change",
        description="""Record a code change (git commit) in the dev context graph.

Tracks file changes with git metadata including commit hash, author, and diff statistics.
Links to File nodes in the knowledge graph for complete traceability.

Returns:
- code_change_uid: Generated UID for the code change""",
        inputSchema={
            "type": "object",
            "properties": {
                "commit_hash": {
                    "type": "string",
                    "description": "Git commit hash"
                },
                "file_path": {
                    "type": "string",
                    "description": "File path changed (relative to project root)"
                },
                "change_type": {
                    "type": "string",
                    "description": "Type of change",
                    "enum": ["modified", "added", "deleted", "renamed"]
                },
                "lines_added": {
                    "type": "integer",
                    "description": "Number of lines added (default: 0)",
                    "default": 0
                },
                "lines_deleted": {
                    "type": "integer",
                    "description": "Number of lines deleted (default: 0)",
                    "default": 0
                },
                "author": {
                    "type": "string",
                    "description": "Commit author email"
                },
                "timestamp": {
                    "type": "string",
                    "description": "Commit timestamp (ISO 8601 format)"
                },
                "diff_snippet": {
                    "type": "string",
                    "description": "Optional diff snippet (first 1000 chars)"
                }
            },
            "required": ["commit_hash", "file_path", "change_type"]
        }
    ),
    Tool(
        name="link_code_to_work",
        description="""Link a code change to a work item with confidence scoring.

Creates LINKS_TO relationship between CodeChange and WorkItem nodes.
Confidence score indicates link strength (1.0 = explicit reference, <1.0 = inferred).

Returns:
- linked: Boolean indicating if link was created successfully""",
        inputSchema={
            "type": "object",
            "properties": {
                "work_item_uid": {
                    "type": "string",
                    "description": "WorkItem UID (from create_work_item)"
                },
                "code_change_uid": {
                    "type": "string",
                    "description": "CodeChange UID (from record_code_change)"
                },
                "link_confidence": {
                    "type": "number",
                    "description": "Confidence score for the link (0.0-1.0, default: 0.5)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                },
                "link_reason": {
                    "type": "string",
                    "description": "Optional reason for the link (e.g., 'Commit message mentions issue #123')"
                }
            },
            "required": ["work_item_uid", "code_change_uid"]
        }
    ),
    Tool(
        name="query_work_items",
        description="""Query work items with pagination and filtering.

Supports:
- Pagination via offset/limit
- Filtering by status, priority, work_type
- Deterministic ordering by field (created_at, updated_at, title, etc.)

Returns paginated list of work items matching criteria.""",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Project name for scoped queries"
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default: 0)",
                    "default": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 20)",
                    "default": 20
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (open, in_progress, done, etc.)"
                },
                "priority": {
                    "type": "string",
                    "description": "Filter by priority (low, medium, high, critical)"
                },
                "work_type": {
                    "type": "string",
                    "description": "Filter by work_type (feature, bug, task, etc.)"
                },
                "order_by": {
                    "type": "string",
                    "description": "Field to order by (default: created_at)",
                    "enum": ["created_at", "updated_at", "title", "priority", "status"],
                    "default": "created_at"
                },
                "order_direction": {
                    "type": "string",
                    "description": "Sort direction (default: DESC)",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC"
                }
            },
            "required": ["project_name"]
        }
    ),
    Tool(
        name="get_work_context",
        description="""Get comprehensive context for a work item.

Returns:
- Work item details
- Related commits (CodeChange nodes)
- Related file paths
- Complete traceability chain

Use this to understand what code changes relate to a work item.""",
        inputSchema={
            "type": "object",
            "properties": {
                "work_item_uid": {
                    "type": "string",
                    "description": "WorkItem UID to query"
                },
                "include_related_commits": {
                    "type": "boolean",
                    "description": "Include related CodeChange nodes (default: true)",
                    "default": True
                },
                "include_related_files": {
                    "type": "boolean",
                    "description": "Include related file paths (default: true)",
                    "default": True
                }
            },
            "required": ["work_item_uid"]
        }
    ),
    Tool(
        name="trace_file_to_work",
        description="""Trace a file to related work items (backward tracing).

Finds all work items that affected a specific file through code changes.
Useful for understanding 'why was this file changed?'

Supports:
- Confidence filtering (only show high-confidence links)
- Backward tracing from file to work items
- Commit history per work item

Returns list of work items with trace metadata.""",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "File path to trace (relative to project root)"
                },
                "project_name": {
                    "type": "string",
                    "description": "Project name for scoped queries"
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence score for links (default: 0.5)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                },
                "trace_direction": {
                    "type": "string",
                    "description": "Direction of trace (default: backward)",
                    "enum": ["backward"],
                    "default": "backward"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth of traversal (default: 3)",
                    "default": 3
                }
            },
            "required": ["file_path", "project_name"]
        }
    ),
    Tool(
        name="update_work_item",
        description="""Update work item metadata (status, priority, assignees, labels).

Allows modification of work item fields without recreating the item.
Supports partial updates - only provided fields will be modified.

Fields that can be updated:
- status: open, in_progress, closed, blocked
- priority: critical, high, medium, low
- assignees: List of assignee identifiers
- labels: List of label strings
- closure_reason: Reason for closing (when status=closed)

Returns updated work item details.""",
        inputSchema={
            "type": "object",
            "properties": {
                "work_item_uid": {
                    "type": "string",
                    "description": "WorkItem UID to update"
                },
                "status": {
                    "type": "string",
                    "description": "New status value",
                    "enum": ["open", "in_progress", "closed", "blocked"]
                },
                "priority": {
                    "type": "string",
                    "description": "New priority value",
                    "enum": ["critical", "high", "medium", "low"]
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of assignee identifiers"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels"
                },
                "closure_reason": {
                    "type": "string",
                    "description": "Reason for closing (when status=closed)"
                }
            },
            "required": ["work_item_uid"]
        }
    )
]


# ============================================================================
# Tool Handlers
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of available tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool invocations."""
    logger.info(f"Tool called: {name} with args: {arguments}")

    try:
        if name == "query_codebase":
            return await handle_query_codebase(arguments)
        elif name == "get_component_map":
            return await handle_get_component_map(arguments)
        elif name == "list_projects":
            return await handle_list_projects(arguments)
        elif name == "get_file_relationships":
            return await handle_get_file_relationships(arguments)
        elif name == "provide_feedback":
            return await handle_provide_feedback(arguments)
        elif name == "register_project":
            return await handle_register_project(arguments)
        elif name == "index_project":
            return await handle_index_project(arguments)
        elif name == "ingest_files":
            return await handle_ingest_files(arguments)
        elif name == "create_conversation":
            return await handle_create_conversation(arguments)
        elif name == "continue_conversation":
            return await handle_continue_conversation(arguments)
        elif name == "get_conversation_history":
            return await handle_get_conversation_history(arguments)
        elif name == "list_conversations":
            return await handle_list_conversations(arguments)
        elif name == "create_work_item":
            return await handle_create_work_item(arguments)
        elif name == "record_code_change":
            return await handle_record_code_change(arguments)
        elif name == "link_code_to_work":
            return await handle_link_code_to_work(arguments)
        elif name == "query_work_items":
            return await handle_query_work_items(arguments)
        elif name == "get_work_context":
            return await handle_get_work_context(arguments)
        elif name == "trace_file_to_work":
            return await handle_trace_file_to_work(arguments)
        elif name == "update_work_item":
            return await handle_update_work_item(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    except Exception as e:
        logger.error(f"Tool error: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def handle_query_codebase(args: dict) -> CallToolResult:
    """Execute knowledge graph query and return evidence packet."""
    import time

    project_name = args.get("project_name")
    question = args.get("question")
    max_results = args.get("max_results", 20)

    if not project_name or not question:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name and question")],
            isError=True
        )

    # Configure for evidence-only mode (no LLM synthesis)
    config = EvidenceQueryConfig(
        mode=EvidenceOutputMode.EVIDENCE_ONLY,
        max_results=max_results
    )

    # Execute query with timing
    start_time = time.time()
    try:
        packet = query_graph(
            question=question,
            project_name=project_name,
            evidence_config=config
        )
        execution_time_ms = (time.time() - start_time) * 1000

        # Track query metrics
        try:
            with QueryMetrics() as metrics:
                query_id = packet.get("meta", {}).get("query_id")
                confidence = packet.get("context_veracity", {}).get("confidence_score", 0)
                result_count = len(packet.get("code_truth", [])) + len(packet.get("doc_claims", []))
                evidence_count = result_count

                metrics.track_query(
                    query_id=query_id,
                    project=project_name,
                    execution_time_ms=execution_time_ms,
                    result_count=result_count,
                    confidence_score=confidence,
                    evidence_count=evidence_count
                )
        except Exception as e:
            logger.warning(f"Failed to track query metrics: {e}")
            # Don't fail the query - metrics tracking is non-critical

    except Exception as e:
        logger.error(f"Query failed: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Query failed: {str(e)}")],
            isError=True
        )

    # Format response as structured evidence
    response = format_evidence_packet(packet)

    return CallToolResult(
        content=[TextContent(type="text", text=response)]
    )


async def handle_get_component_map(args: dict) -> CallToolResult:
    """Generate component architecture map via Cypher queries."""
    from neo4j import GraphDatabase

    project_name = args.get("project_name")
    component_path = args.get("component_path")

    if not project_name or not component_path:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name and component_path")],
            isError=True
        )

    config = get_config()
    # Convert SecretStr to string if needed
    password = config.neo4j.password
    if hasattr(password, 'get_secret_value'):
        password = password.get_secret_value()
    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.user, password)
    )

    try:
        with driver.session() as session:
            # Find the file node
            file_result = session.run("""
                MATCH (f:File {project: $project})
                WHERE f.path CONTAINS $component
                RETURN f.path as path, f.name as name
                LIMIT 1
            """, project=project_name, component=component_path)

            file_record = file_result.single()
            if not file_record:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Component not found: {component_path}")],
                    isError=True
                )

            file_path = file_record["path"]

            # Get definitions (classes, functions)
            definitions = session.run("""
                MATCH (f:File {path: $path, project: $project})-[:DEFINES]->(d)
                RETURN labels(d)[0] as type, d.name as name, d.docstring as doc
                ORDER BY d.name
            """, path=file_path, project=project_name)

            # Get imports (what this file depends on)
            imports = session.run("""
                MATCH (f:File {path: $path, project: $project})-[:DEPENDS_ON]->(target)
                RETURN DISTINCT target.name as name, labels(target)[0] as type
                ORDER BY target.name
            """, path=file_path, project=project_name)

            # Get reverse dependencies (what imports this file)
            dependents = session.run("""
                MATCH (other)-[:DEPENDS_ON]->(f:File {path: $path, project: $project})
                RETURN DISTINCT other.path as path, other.name as name
                ORDER BY other.path
            """, path=file_path, project=project_name)

            # Get call relationships
            calls = session.run("""
                MATCH (f:File {path: $path, project: $project})-[:DEFINES]->(fn)-[:CALLS]->(target)
                RETURN fn.name as caller, target.name as callee
                LIMIT 50
            """, path=file_path, project=project_name)

            # Format the component map
            response = format_component_map(
                file_path=file_path,
                definitions=list(definitions),
                imports=list(imports),
                dependents=list(dependents),
                calls=list(calls)
            )

            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
    finally:
        driver.close()


async def handle_list_projects(args: dict) -> CallToolResult:
    """List all indexed projects."""
    from neo4j import GraphDatabase

    config = get_config()
    password = config.neo4j.password
    if hasattr(password, 'get_secret_value'):
        password = password.get_secret_value()
    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.user, password)
    )

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.project IS NOT NULL
                WITH n.project as project, count(*) as node_count
                RETURN project, node_count
                ORDER BY node_count DESC
            """)

            projects = []
            for record in result:
                projects.append({
                    "name": record["project"],
                    "node_count": record["node_count"]
                })

            if not projects:
                return CallToolResult(
                    content=[TextContent(type="text", text="No indexed projects found. Run build_graph.py to index a project.")]
                )

            response = "# Indexed Projects\n\n"
            response += "| Project | Nodes |\n|---------|-------|\n"
            for p in projects:
                response += f"| {p['name']} | {p['node_count']:,} |\n"

            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
    finally:
        driver.close()


async def handle_get_file_relationships(args: dict) -> CallToolResult:
    """Get all relationships for a specific file."""
    from neo4j import GraphDatabase

    project_name = args.get("project_name")
    file_path = args.get("file_path")

    if not project_name or not file_path:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name and file_path")],
            isError=True
        )

    config = get_config()
    password = config.neo4j.password
    if hasattr(password, 'get_secret_value'):
        password = password.get_secret_value()
    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.user, password)
    )

    try:
        with driver.session() as session:
            # Find file by partial path match
            file_result = session.run("""
                MATCH (f:File {project: $project})
                WHERE f.path CONTAINS $path OR f.name = $path
                RETURN f.path as path, f.name as name
                LIMIT 1
            """, project=project_name, path=file_path)

            file_record = file_result.single()
            if not file_record:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"File not found: {file_path}")],
                    isError=True
                )

            actual_path = file_record["path"]

            # Get all outgoing relationships
            outgoing = session.run("""
                MATCH (f:File {path: $path, project: $project})-[r]->(target)
                RETURN type(r) as rel_type, labels(target)[0] as target_type,
                       target.name as target_name, target.path as target_path
                ORDER BY type(r), target.name
            """, path=actual_path, project=project_name)

            # Get all incoming relationships
            incoming = session.run("""
                MATCH (source)-[r]->(f:File {path: $path, project: $project})
                RETURN type(r) as rel_type, labels(source)[0] as source_type,
                       source.name as source_name, source.path as source_path
                ORDER BY type(r), source.name
            """, path=actual_path, project=project_name)

            response = f"# File Relationships: {actual_path}\n\n"

            response += "## Outgoing Relationships\n\n"
            for r in outgoing:
                target = r["target_path"] or r["target_name"]
                response += f"- **{r['rel_type']}** → {r['target_type']}: `{target}`\n"

            response += "\n## Incoming Relationships\n\n"
            for r in incoming:
                source = r["source_path"] or r["source_name"]
                response += f"- **{r['rel_type']}** ← {r['source_type']}: `{source}`\n"

            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
    finally:
        driver.close()


async def handle_provide_feedback(args: dict) -> CallToolResult:
    """Store user feedback on query results in Neo4j."""
    from neo4j import GraphDatabase

    query_id = args.get("query_id")
    rating = args.get("rating")
    comment = args.get("comment", "")

    if not query_id or not rating:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: query_id and rating")],
            isError=True
        )

    # Validate rating enum
    if rating not in ["useful", "not_useful", "partial"]:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Invalid rating: {rating}. Must be 'useful', 'not_useful', or 'partial'")],
            isError=True
        )

    config = get_config()
    password = config.neo4j.password
    if hasattr(password, 'get_secret_value'):
        password = password.get_secret_value()
    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.user, password)
    )

    try:
        with driver.session() as session:
            # First check if the query exists
            query_check = session.run("""
                MATCH (r:VeracityReport {query_id: $query_id})
                RETURN r.query_id as id, r.question as question
            """, query_id=query_id)

            query_record = query_check.single()
            if not query_record:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Query not found: {query_id}. Query must be executed before providing feedback.")],
                    isError=True
                )

            # Store feedback as a relationship and node
            result = session.run("""
                MATCH (q:VeracityReport {query_id: $query_id})
                CREATE (f:Feedback {
                    rating: $rating,
                    comment: $comment,
                    timestamp: datetime()
                })
                CREATE (q)-[:RATED_AS]->(f)
                RETURN f.rating as rating, f.timestamp as timestamp
            """, query_id=query_id, rating=rating, comment=comment)

            feedback_record = result.single()

            if feedback_record:
                timestamp = feedback_record["timestamp"]
                response = f"# Feedback Recorded\n\n"
                response += f"**Query ID**: {query_id}\n"
                response += f"**Rating**: {rating}\n"
                if comment:
                    response += f"**Comment**: {comment}\n"
                response += f"**Timestamp**: {timestamp}\n"
                response += f"\nThank you for helping improve query quality!"

                logger.info(f"Feedback stored: query_id={query_id}, rating={rating}")

                # Update QueryMetric with feedback
                try:
                    with QueryMetrics() as metrics:
                        metrics.update_feedback(query_id, rating)
                except Exception as e:
                    logger.warning(f"Failed to update query metrics with feedback: {e}")
                    # Don't fail the feedback operation - metrics update is non-critical

                return CallToolResult(
                    content=[TextContent(type="text", text=response)]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text="Failed to store feedback")],
                    isError=True
                )
    except Exception as e:
        logger.error(f"Failed to store feedback: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error storing feedback: {str(e)}")],
            isError=True
        )
    finally:
        driver.close()


async def handle_create_conversation(args: dict) -> CallToolResult:
    """Create a new conversation session."""
    project_name = args.get("project_name")

    if not project_name:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name")],
            isError=True
        )

    try:
        mgr = ConversationManager()
        session_id = mgr.create_conversation(project_name)
        mgr.close()

        response = f"""# Conversation Created

**Session ID**: `{session_id}`
**Project**: {project_name}

Use this session_id with `continue_conversation` for follow-up queries."""

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error creating conversation: {str(e)}")],
            isError=True
        )


async def handle_continue_conversation(args: dict) -> CallToolResult:
    """Continue an existing conversation with context-aware query."""
    session_id = args.get("session_id")
    project_name = args.get("project_name")
    question = args.get("question")
    max_results = args.get("max_results", 20)

    if not session_id or not project_name or not question:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: session_id, project_name, question")],
            isError=True
        )

    try:
        # Get conversation context
        mgr = ConversationManager()
        context = mgr.get_conversation_context(session_id, limit=5)

        # Build context-aware query
        enhanced_query = build_context_aware_query(question, context)

        # Execute query
        config = EvidenceQueryConfig(
            mode=EvidenceOutputMode.EVIDENCE_ONLY,
            max_results=max_results
        )

        packet = query_graph(
            question=enhanced_query,
            project_name=project_name,
            evidence_config=config
        )

        # Add query to conversation history
        mgr.add_query_to_conversation(session_id, question, packet)
        mgr.close()

        # Add session info to response
        response = format_evidence_packet(packet)
        response += f"\n\n---\n**Session**: `{session_id}` | **Query**: {len(context) + 1}"

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )
    except Exception as e:
        logger.error(f"Failed to continue conversation: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def handle_get_conversation_history(args: dict) -> CallToolResult:
    """Get conversation history."""
    session_id = args.get("session_id")
    limit = args.get("limit", 5)

    if not session_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: session_id")],
            isError=True
        )

    try:
        mgr = ConversationManager()
        queries = mgr.get_conversation_context(session_id, limit=limit)
        metadata = mgr.get_conversation_metadata(session_id)
        mgr.close()

        if not metadata:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Conversation not found: {session_id}")],
                isError=True
            )

        response = [
            f"# Conversation History: {session_id}",
            "",
            f"**Project**: {metadata['project']}",
            f"**Started**: {metadata['started_at']}",
            f"**Last Activity**: {metadata['last_activity']}",
            f"**Total Queries**: {metadata['query_count']}",
            "",
            "## Recent Queries",
            ""
        ]

        for i, query in enumerate(queries, 1):
            response.append(f"### {i}. {query['text']}")
            response.append(f"- **Timestamp**: {query['timestamp']}")
            response.append(f"- **Confidence**: {query['confidence_score']:.0f}%")
            response.append(f"- **Evidence**: {query['evidence_count']} items")
            response.append("")

        return CallToolResult(
            content=[TextContent(type="text", text="\n".join(response))]
        )
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def handle_list_conversations(args: dict) -> CallToolResult:
    """List all conversations."""
    project_name = args.get("project_name")

    try:
        mgr = ConversationManager()
        conversations = mgr.list_conversations(project_name)
        mgr.close()

        if not conversations:
            msg = f"No conversations found for project: {project_name}" if project_name else "No conversations found"
            return CallToolResult(
                content=[TextContent(type="text", text=msg)]
            )

        response = ["# Conversations", ""]
        if project_name:
            response.append(f"**Project Filter**: {project_name}")
            response.append("")

        response.append("| Session ID | Project | Queries | Last Activity |")
        response.append("|------------|---------|---------|---------------|")

        for conv in conversations:
            session_short = conv['id'][:8] + "..."
            response.append(
                f"| `{session_short}` | {conv['project']} | {conv['query_count']} | {conv['last_activity'][:19]} |"
            )

        return CallToolResult(
            content=[TextContent(type="text", text="\n".join(response))]
        )
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


# ============================================================================
# Formatting Helpers
# ============================================================================

def format_evidence_packet(packet: dict) -> str:
    """Format evidence packet as structured markdown for agents."""
    response = []

    # Header with veracity info
    veracity = packet.get("context_veracity", {})
    confidence = veracity.get("confidence_score", 0)
    faults = veracity.get("faults", [])
    meta = packet.get("meta", {})
    query_id = meta.get("query_id", "N/A")

    response.append(f"# Knowledge Graph Evidence (Confidence: {confidence:.0f}%)")
    response.append(f"**Query ID**: {query_id}")
    response.append(f"**Query**: {meta.get('question', 'N/A')}")
    response.append(f"**Project**: {meta.get('project', 'N/A')}")
    response.append("")

    if faults:
        response.append("## Veracity Warnings")
        for fault in faults:
            response.append(f"- {fault}")
        response.append("")

    # Code evidence
    code_truth = packet.get("code_truth", [])
    if code_truth:
        response.append("## Code Evidence")
        response.append("")
        for item in code_truth[:20]:  # Limit output
            node_type = item.get("node_type", "Node")
            name = item.get("name", "unknown")
            path = item.get("file_path", "")
            doc = item.get("docstring", "")

            response.append(f"### [{node_type}] `{name}`")
            response.append(f"**File**: `{path}`")
            if doc:
                # Truncate long docstrings
                doc_preview = doc[:200] + "..." if len(doc) > 200 else doc
                response.append(f"**Doc**: {doc_preview}")
            response.append("")

    # Document evidence
    doc_claims = packet.get("doc_claims", [])
    if doc_claims:
        response.append("## Documentation Evidence")
        response.append("")
        for item in doc_claims[:10]:
            name = item.get("name", "unknown")
            path = item.get("file_path", "")
            response.append(f"- **{name}** (`{path}`)")
        response.append("")

    # Suggested actions
    actions = packet.get("suggested_actions", [])
    if actions:
        response.append("## Suggested Actions")
        for action in actions:
            response.append(f"- {action}")

    return "\n".join(response)


def format_component_map(
    file_path: str,
    definitions: list,
    imports: list,
    dependents: list,
    calls: list
) -> str:
    """Format component map as structured markdown."""
    response = []

    response.append(f"# Component Map: {file_path}")
    response.append("")
    response.append("**Generated**: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    response.append("**Method**: Static analysis (Neo4j graph query)")
    response.append("")

    # Definitions
    response.append("## Definitions (What This File Defines)")
    response.append("")
    if definitions:
        for d in definitions:
            doc = d.get("doc", "")
            doc_preview = doc[:100] + "..." if doc and len(doc) > 100 else (doc or "No documentation")
            response.append(f"- **{d['type']}**: `{d['name']}` - {doc_preview}")
    else:
        response.append("*No definitions found*")
    response.append("")

    # Imports
    response.append("## Imports (What This File Depends On)")
    response.append("")
    if imports:
        for i in imports:
            response.append(f"- {i['type']}: `{i['name']}`")
    else:
        response.append("*No imports tracked*")
    response.append("")

    # Reverse dependencies
    response.append("## Dependents (What Imports This File)")
    response.append("")
    if dependents:
        for d in dependents:
            response.append(f"- `{d['path']}`")
    else:
        response.append("*No dependents found*")
    response.append("")

    # Call graph
    response.append("## Call Relationships")
    response.append("")
    if calls:
        for c in calls:
            response.append(f"- `{c['caller']}` → `{c['callee']}`")
    else:
        response.append("*No call relationships tracked*")

    return "\n".join(response)


# ============================================================================
# Dev Context Tracking Handlers
# ============================================================================

# Global DevContextManager instances (cached per project)
_dev_context_managers: dict[str, DevContextManager] = {}


def get_dev_context_manager(project_name: str) -> DevContextManager:
    """Get or create DevContextManager for a project."""
    if project_name not in _dev_context_managers:
        config = get_config()
        password = config.neo4j.password
        if hasattr(password, 'get_secret_value'):
            password = password.get_secret_value()

        manager = DevContextManager(
            project_name=project_name,
            neo4j_uri=config.neo4j.uri,
            neo4j_user=config.neo4j.user,
            neo4j_password=password
        )
        # Create schema on first access
        manager.create_schema()
        _dev_context_managers[project_name] = manager

    return _dev_context_managers[project_name]


async def handle_create_work_item(args: dict) -> CallToolResult:
    """Create a new work item with idempotency support."""
    # Extract required fields
    title = args.get("title")
    description = args.get("description")
    work_type = args.get("work_type")

    if not title or not description or not work_type:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required fields: title, description, work_type"
                })
            )],
            isError=True
        )

    # Extract optional fields
    priority = args.get("priority", "medium")
    external_id = args.get("external_id")
    source = args.get("source")
    idempotency_token = args.get("idempotency_token")

    try:
        # Use project from config or args (for multi-project support)
        project_name = args.get("project_name", "default")
        manager = get_dev_context_manager(project_name)

        # Check idempotency token if provided
        if idempotency_token:
            try:
                # Query for existing work item with same token
                with manager._driver.session() as session:
                    result = session.run("""
                        MATCH (w:WorkItem)
                        WHERE w.idempotency_token = $token
                        RETURN w.uid AS uid
                        LIMIT 1
                    """, token=idempotency_token)
                    record = result.single()

                    if record:
                        # Return existing work item (idempotent)
                        return CallToolResult(
                            content=[TextContent(
                                type="text",
                                text=json.dumps({
                                    "success": True,
                                    "data": {
                                        "work_item_uid": record["uid"],
                                        "created": False,
                                        "message": "Work item already exists (idempotent)"
                                    }
                                })
                            )]
                        )
            except Exception as e:
                logger.warning(f"Idempotency check failed: {e}")
                # Continue with creation if check fails

        # Create new work item
        work_item_uid = manager.create_work_item(
            title=title,
            description=description,
            work_type=work_type,
            priority=priority,
            external_id=external_id,
            source=source
        )

        # Store idempotency token if provided
        if idempotency_token:
            with manager._driver.session() as session:
                session.run("""
                    MATCH (w:WorkItem {uid: $uid})
                    SET w.idempotency_token = $token
                """, uid=work_item_uid, token=idempotency_token)

        logger.info(f"Created work item: {work_item_uid}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": {
                        "work_item_uid": work_item_uid,
                        "created": True,
                        "title": title,
                        "work_type": work_type,
                        "priority": priority
                    }
                })
            )]
        )

    except Exception as e:
        logger.error(f"Failed to create work item: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


async def handle_record_code_change(args: dict) -> CallToolResult:
    """Record a code change (git commit) in the graph."""
    # Extract required fields
    commit_hash = args.get("commit_hash")
    file_path = args.get("file_path")
    change_type = args.get("change_type")

    if not commit_hash or not file_path or not change_type:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required fields: commit_hash, file_path, change_type"
                })
            )],
            isError=True
        )

    # Extract optional fields
    lines_added = args.get("lines_added", 0)
    lines_deleted = args.get("lines_deleted", 0)
    author = args.get("author")
    timestamp = args.get("timestamp")
    diff_snippet = args.get("diff_snippet")

    try:
        project_name = args.get("project_name", "default")
        manager = get_dev_context_manager(project_name)

        # Record the code change
        code_change_uid = manager.record_code_change(
            commit_hash=commit_hash,
            file_path=file_path,
            change_type=change_type,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            author=author
        )

        # Store diff snippet if provided
        if diff_snippet:
            with manager._driver.session() as session:
                session.run("""
                    MATCH (c:CodeChange {uid: $uid})
                    SET c.diff_snippet = $diff_snippet
                """, uid=code_change_uid, diff_snippet=diff_snippet[:1000])  # Limit to 1000 chars

        logger.info(f"Recorded code change: {code_change_uid}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": {
                        "code_change_uid": code_change_uid,
                        "commit_hash": commit_hash,
                        "file_path": file_path,
                        "change_type": change_type,
                        "lines_added": lines_added,
                        "lines_deleted": lines_deleted
                    }
                })
            )]
        )

    except Exception as e:
        logger.error(f"Failed to record code change: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


async def handle_link_code_to_work(args: dict) -> CallToolResult:
    """Link a code change to a work item with confidence scoring."""
    # Extract required fields
    work_item_uid = args.get("work_item_uid")
    code_change_uid = args.get("code_change_uid")

    if not work_item_uid or not code_change_uid:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required fields: work_item_uid, code_change_uid"
                })
            )],
            isError=True
        )

    # Extract optional fields
    link_confidence = args.get("link_confidence", 0.5)
    link_reason = args.get("link_reason", "")

    try:
        project_name = args.get("project_name", "default")
        manager = get_dev_context_manager(project_name)

        # Validate UIDs
        try:
            manager._validate_uid(work_item_uid)
            manager._validate_uid(code_change_uid)
        except Exception as e:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Invalid UID format: {str(e)}"
                    })
                )],
                isError=True
            )

        # Create the link
        linked = manager.link_code_to_work(
            work_item_uid=work_item_uid,
            code_change_uid=code_change_uid,
            link_confidence=link_confidence
        )

        # Store link reason if provided
        if link_reason:
            with manager._driver.session() as session:
                session.run("""
                    MATCH (c:CodeChange {uid: $code_uid})-[r:LINKS_TO]->(w:WorkItem {uid: $work_uid})
                    SET r.reason = $reason
                """, code_uid=code_change_uid, work_uid=work_item_uid, reason=link_reason)

        logger.info(f"Linked code change {code_change_uid} to work item {work_item_uid}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": {
                        "linked": linked,
                        "work_item_uid": work_item_uid,
                        "code_change_uid": code_change_uid,
                        "link_confidence": link_confidence
                    }
                })
            )]
        )

    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error linking code to work: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )
    except Exception as e:
        logger.error(f"Failed to link code to work: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


async def handle_query_work_items(args: dict) -> CallToolResult:
    """Query work items with pagination and filtering."""
    project_name = args.get("project_name")

    if not project_name:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required field: project_name"
                })
            )],
            isError=True
        )

    # Extract query parameters with defaults
    offset = args.get("offset", 0)
    limit = args.get("limit", 20)
    status = args.get("status")
    priority = args.get("priority")
    work_type = args.get("work_type")
    order_by = args.get("order_by", "created_at")
    order_direction = args.get("order_direction", "DESC")

    try:
        manager = get_dev_context_manager(project_name)

        # Execute query
        work_items = manager.query_work_items(
            offset=offset,
            limit=limit,
            status=status,
            priority=priority,
            work_type=work_type,
            order_by=order_by,
            order_direction=order_direction
        )

        logger.info(f"Queried {len(work_items)} work items for project {project_name}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": {
                        "work_items": work_items,
                        "count": len(work_items),
                        "offset": offset,
                        "limit": limit
                    }
                })
            )]
        )

    except Exception as e:
        logger.error(f"Failed to query work items: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


async def handle_get_work_context(args: dict) -> CallToolResult:
    """Get comprehensive context for a work item."""
    work_item_uid = args.get("work_item_uid")

    if not work_item_uid:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required field: work_item_uid"
                })
            )],
            isError=True
        )

    include_related_commits = args.get("include_related_commits", True)
    include_related_files = args.get("include_related_files", True)

    try:
        # Extract project from UID
        project_name = work_item_uid.split("::")[0]
        manager = get_dev_context_manager(project_name)

        # Get work context
        context = manager.get_work_context(
            work_item_uid=work_item_uid,
            include_related_commits=include_related_commits,
            include_related_files=include_related_files
        )

        logger.info(f"Retrieved context for work item {work_item_uid}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": context
                })
            )]
        )

    except WorkItemNotFoundError as e:
        logger.error(f"Work item not found: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )
    except Exception as e:
        logger.error(f"Failed to get work context: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


async def handle_trace_file_to_work(args: dict) -> CallToolResult:
    """Trace a file to related work items."""
    file_path = args.get("file_path")
    project_name = args.get("project_name")

    if not file_path or not project_name:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required fields: file_path, project_name"
                })
            )],
            isError=True
        )

    min_confidence = args.get("min_confidence", 0.5)
    trace_direction = args.get("trace_direction", "backward")
    max_depth = args.get("max_depth", 3)

    try:
        manager = get_dev_context_manager(project_name)

        # Execute trace
        traces = manager.trace_file_to_work(
            file_path=file_path,
            min_confidence=min_confidence,
            trace_direction=trace_direction,
            max_depth=max_depth
        )

        logger.info(f"Traced {len(traces)} work items for file {file_path}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": {
                        "traces": traces,
                        "file_path": file_path,
                        "count": len(traces)
                    }
                })
            )]
        )

    except Exception as e:
        logger.error(f"Failed to trace file to work: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


async def handle_update_work_item(args: dict) -> CallToolResult:
    """Update work item metadata (status, priority, assignees, labels)."""
    # Extract required field
    work_item_uid = args.get("work_item_uid")

    if not work_item_uid:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "Missing required field: work_item_uid"
                })
            )],
            isError=True
        )

    # Extract optional fields
    status = args.get("status")
    priority = args.get("priority")
    assignees = args.get("assignees")
    labels = args.get("labels")
    closure_reason = args.get("closure_reason")

    try:
        # Extract project from UID
        project_name = work_item_uid.split("::")[0]
        manager = get_dev_context_manager(project_name)

        # Build kwargs for only provided fields
        update_kwargs = {"work_item_uid": work_item_uid}
        if status is not None:
            update_kwargs["status"] = status
        if priority is not None:
            update_kwargs["priority"] = priority
        if assignees is not None:
            update_kwargs["assignees"] = assignees
        if labels is not None:
            update_kwargs["labels"] = labels
        if closure_reason is not None:
            update_kwargs["closure_reason"] = closure_reason

        # Update the work item
        success = manager.update_work_item(**update_kwargs)

        if not success:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Failed to update work item"
                    })
                )],
                isError=True
            )

        # Retrieve the updated work item
        updated_work_item = manager.get_work_item(work_item_uid)

        logger.info(f"Updated work item: {work_item_uid}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": updated_work_item
                })
            )]
        )

    except WorkItemNotFoundError as e:
        logger.error(f"Work item not found: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )
    except ValueError as e:
        # Handle InvalidUIIDFormatError (which is a ValueError subclass)
        logger.error(f"Validation error updating work item: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )
    except Exception as e:
        logger.error(f"Failed to update work item: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )],
            isError=True
        )


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server."""
    logger.info("Starting Veracity Engine MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

# ============================================================================
# Project Registration and Indexing Handlers
# ============================================================================

async def handle_register_project(args: dict) -> CallToolResult:
    """Register a new project for indexing."""
    project_name = args.get("project_name")
    root_dir = args.get("root_dir")
    target_dirs = args.get("target_dirs")
    watch_mode_str = args.get("watch_mode", "realtime")

    if not project_name or not root_dir:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name and root_dir")],
            isError=True
        )

    # Validate root directory exists
    if not os.path.exists(root_dir):
        return CallToolResult(
            content=[TextContent(type="text", text=f"Directory does not exist: {root_dir}")],
            isError=True
        )

    if not os.path.isdir(root_dir):
        return CallToolResult(
            content=[TextContent(type="text", text=f"Not a directory: {root_dir}")],
            isError=True
        )

    try:
        # Convert watch mode string to enum
        watch_mode = WatchMode(watch_mode_str)

        # Register the project
        project_config = register_project(
            name=project_name,
            root_dir=root_dir,
            target_dirs=target_dirs,
            watch_mode=watch_mode
        )

        response = f"# Project Registered Successfully\n\n"
        response += f"**Name**: {project_name}\n"
        response += f"**Root**: {project_config.root_dir}\n"
        response += f"**Target Dirs**: {', '.join(project_config.target_dirs)}\n"
        response += f"**Watch Mode**: {project_config.watch_mode.value}\n\n"
        response += f"Next steps:\n"
        response += f"1. Run `index_project` to build the knowledge graph\n"
        response += f"2. Query the codebase with `query_codebase`\n"

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )
    except Exception as e:
        logger.error(f"Failed to register project: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Registration failed: {str(e)}")],
            isError=True
        )


async def handle_index_project(args: dict) -> CallToolResult:
    """Index a project by running the build_graph logic."""
    project_name = args.get("project_name")
    incremental = args.get("incremental", True)
    force = args.get("force", False)

    if not project_name:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name")],
            isError=True
        )

    # Get project configuration
    project_config = get_project(project_name)
    if not project_config:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Project '{project_name}' not registered. Use register_project first.")],
            isError=True
        )

    # Get Neo4j credentials from config
    config = get_config()
    neo4j_uri = config.neo4j.uri
    neo4j_user = config.neo4j.user
    neo4j_password = config.neo4j.password
    if hasattr(neo4j_password, 'get_secret_value'):
        neo4j_password = neo4j_password.get_secret_value()

    try:
        # Initialize builder
        builder = CodeGraphBuilder(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            project_name,
            project_config.root_dir
        )

        try:
            # Clear database if not incremental
            if not incremental or force:
                builder.clear_database()

            # Create constraints
            builder.create_constraints()

            # Build list of files to index
            EXCLUDE_DIRS = {'venv', '.venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', 'dist', 'build', 'egg-info', '.next'}
            CODE_EXTENSIONS = {
                '.py', '.pyi', '.pyx',
                '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
                '.vue', '.svelte',
                '.go',
                '.java', '.kt', '.kts', '.scala', '.groovy',
                '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
                '.rs',
                '.swift', '.m', '.mm',
                '.cs', '.fs',
                '.rb', '.rake',
                '.php',
                '.dart',
                '.sh', '.bash', '.zsh',
            }

            current_files = []
            for target in project_config.target_dirs:
                t_path = os.path.join(project_config.root_dir, target)
                if os.path.exists(t_path):
                    for root, dirs, filenames in os.walk(t_path):
                        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith('.egg-info')]
                        for f in filenames:
                            ext = os.path.splitext(f)[1].lower()
                            if ext in CODE_EXTENSIONS and not f.startswith('.'):
                                current_files.append(os.path.join(root, f))

            # Process hierarchy and documents
            builder.process_hierarchy(project_config.target_dirs)
            builder.index_documents(project_config.target_dirs)

            # Parse files
            changed_count = 0
            for f in current_files:
                if builder.parse_file(f):
                    changed_count += 1

            # Commit if changes detected
            if changed_count > 0 or force:
                builder.batch_process_embeddings()
                builder.commit_to_neo4j()
                builder.save_hashes()

                response = f"# Indexing Complete\n\n"
                response += f"**Project**: {project_name}\n"
                response += f"**Files Processed**: {changed_count}\n"
                response += f"**Mode**: {'Full rebuild' if not incremental else 'Incremental'}\n\n"
                response += f"The knowledge graph is now ready for queries.\n"
            else:
                response = f"# Project Up to Date\n\n"
                response += f"**Project**: {project_name}\n"
                response += f"No changes detected. Use force=true to rebuild.\n"

            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        finally:
            builder.close()

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Indexing failed: {str(e)}")],
            isError=True
        )


async def handle_ingest_files(args: dict) -> CallToolResult:
    """Ingest specific files for incremental updates."""
    project_name = args.get("project_name")
    files = args.get("files", [])

    if not project_name:
        return CallToolResult(
            content=[TextContent(type="text", text="Missing required: project_name")],
            isError=True
        )

    if not files:
        return CallToolResult(
            content=[TextContent(type="text", text="No files provided")],
            isError=True
        )

    # Get project configuration
    project_config = get_project(project_name)
    if not project_config:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Project '{project_name}' not registered. Use register_project first.")],
            isError=True
        )

    # Get Neo4j credentials
    config = get_config()
    neo4j_uri = config.neo4j.uri
    neo4j_user = config.neo4j.user
    neo4j_password = config.neo4j.password
    if hasattr(neo4j_password, 'get_secret_value'):
        neo4j_password = neo4j_password.get_secret_value()

    try:
        # Initialize builder
        builder = CodeGraphBuilder(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            project_name,
            project_config.root_dir
        )

        try:
            processed_count = 0
            failed_files = []

            for file_info in files:
                file_path = file_info.get("path")
                if not file_path:
                    failed_files.append(("unknown", "Missing path"))
                    continue

                # Construct absolute path
                abs_path = os.path.join(project_config.root_dir, file_path)

                # Check if file exists (unless content provided)
                if not file_info.get("content") and not os.path.exists(abs_path):
                    failed_files.append((file_path, "File not found"))
                    continue

                try:
                    # Parse the file
                    if builder.parse_file(abs_path):
                        processed_count += 1
                except Exception as e:
                    failed_files.append((file_path, str(e)))
                    logger.error(f"Failed to parse {file_path}: {e}")

            # Commit changes
            if processed_count > 0:
                builder.batch_process_embeddings()
                builder.commit_to_neo4j()
                builder.save_hashes()

            response = f"# File Ingestion Complete\n\n"
            response += f"**Project**: {project_name}\n"
            response += f"**Files Processed**: {processed_count}\n"
            response += f"**Files Requested**: {len(files)}\n"

            if failed_files:
                response += f"\n## Failed Files\n\n"
                for path, error in failed_files[:10]:
                    response += f"- `{path}`: {error}\n"
                if len(failed_files) > 10:
                    response += f"\n... and {len(failed_files) - 10} more\n"

            return CallToolResult(
                content=[TextContent(type="text", text=response)]
            )
        finally:
            builder.close()

    except Exception as e:
        logger.error(f"File ingestion failed: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"File ingestion failed: {str(e)}")],
            isError=True
        )
