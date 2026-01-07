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

    # Execute query
    try:
        packet = query_graph(
            question=question,
            project_name=project_name,
            evidence_config=config
        )
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

    response.append(f"# Knowledge Graph Evidence (Confidence: {confidence:.0f}%)")
    response.append(f"**Query**: {packet.get('meta', {}).get('question', 'N/A')}")
    response.append(f"**Project**: {packet.get('meta', {}).get('project', 'N/A')}")
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
