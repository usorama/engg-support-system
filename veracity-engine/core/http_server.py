#!/usr/bin/env python3
"""
HTTP Server for Veracity Engine

Provides health checks and HTTP endpoints for Docker deployment.
Runs alongside the MCP server for production monitoring.

Usage:
    python -m core.http_server --host 0.0.0.0 --port 8000
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="Veracity Engine API",
    description="HTTP endpoints for Dev Context Tracking",
    version="1.0.0"
)

# Configuration from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def check_neo4j_health() -> Dict[str, Any]:
    """Check Neo4j connectivity and return status."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("RETURN 1 AS health")
            result.single()
        driver.close()
        return {"status": "healthy", "latency_ms": 0}
    except ServiceUnavailable as e:
        return {"status": "unhealthy", "error": str(e)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker/k8s.

    Returns 200 if service is healthy, 503 if degraded.
    """
    neo4j_status = check_neo4j_health()

    overall_status = "healthy" if neo4j_status["status"] == "healthy" else "degraded"
    status_code = 200 if overall_status == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "neo4j": neo4j_status
            }
        }
    )


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Veracity Engine",
        "version": "1.0.0",
        "description": "Dev Context Tracking for ESS",
        "endpoints": {
            "health": "/health",
            "work_items": "/api/work-items",
            "webhooks": "/api/webhooks/github"
        }
    }


@app.get("/api/work-items")
async def list_work_items(
    status: str = None,
    priority: str = None,
    limit: int = 20,
    offset: int = 0
):
    """
    List work items from the graph database.

    Query parameters:
    - status: Filter by status (open, in_progress, blocked, closed)
    - priority: Filter by priority (low, medium, high, critical)
    - limit: Max items to return (default: 20)
    - offset: Pagination offset (default: 0)
    """
    try:
        from core.dev_context import DevContextManager

        project_name = os.getenv("PROJECT_NAME", "default")

        with DevContextManager(
            project_name=project_name,
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD
        ) as manager:
            work_items = manager.query_work_items(
                offset=offset,
                limit=limit,
                status=status,
                priority=priority
            )

        return {
            "work_items": work_items,
            "count": len(work_items),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhooks/github")
async def github_webhook():
    """
    GitHub webhook endpoint for issue/PR events.

    Configured at: https://github.com/<owner>/<repo>/settings/hooks
    Content-Type: application/json
    Secret: Set GITHUB_WEBHOOK_SECRET environment variable
    """
    # TODO: Implement webhook handling when request body is available
    return {"status": "received", "message": "Webhook endpoint ready"}


# ============================================================================
# Hook Support Endpoints (for Claude Code auto-integration)
# ============================================================================

@app.get("/api/file-context/{project_name}")
async def get_file_context(
    project_name: str,
    file_path: str,
    min_confidence: float = 0.5
):
    """
    Get dev context for a file - used by PreToolUse hook.

    Returns related work items, recent commits, and suggestions.
    """
    try:
        from core.dev_context import DevContextManager

        with DevContextManager(
            project_name=project_name,
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD
        ) as manager:
            # Trace file to work items
            work_items = manager.trace_file_to_work(
                file_path=file_path,
                min_confidence=min_confidence
            )

            # Get open work items for project
            open_items = manager.query_work_items(
                status="open",
                limit=5
            )

        return {
            "file_path": file_path,
            "project": project_name,
            "related_work_items": work_items,
            "open_work_items": open_items,
            "suggestion": _generate_suggestion(file_path, work_items, open_items)
        }
    except Exception as e:
        # Return empty context on error (don't block the hook)
        return {
            "file_path": file_path,
            "project": project_name,
            "related_work_items": [],
            "open_work_items": [],
            "suggestion": None,
            "error": str(e)
        }


@app.get("/api/project-context/{project_name}")
async def get_project_context(project_name: str):
    """
    Get project summary - used by SessionStart hook.

    Returns work item counts, recent activity, and key stats.
    """
    try:
        from core.dev_context import DevContextManager

        with DevContextManager(
            project_name=project_name,
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD
        ) as manager:
            # Get work item counts by status
            open_items = manager.query_work_items(status="open", limit=100)
            in_progress = manager.query_work_items(status="in_progress", limit=100)
            blocked = manager.query_work_items(status="blocked", limit=100)

            # Get high priority items
            high_priority = manager.query_work_items(priority="high", limit=5)
            critical = manager.query_work_items(priority="critical", limit=5)

        return {
            "project": project_name,
            "summary": {
                "open": len(open_items),
                "in_progress": len(in_progress),
                "blocked": len(blocked)
            },
            "high_priority_items": critical + high_priority,
            "context_prompt": _generate_session_context(
                project_name, open_items, in_progress, blocked, critical + high_priority
            )
        }
    except Exception as e:
        return {
            "project": project_name,
            "summary": {"open": 0, "in_progress": 0, "blocked": 0},
            "high_priority_items": [],
            "context_prompt": None,
            "error": str(e)
        }


@app.post("/api/record-commit/{project_name}")
async def record_commit(
    project_name: str,
    commit_hash: str,
    message: str,
    author: str,
    files_changed: str = ""
):
    """
    Record a git commit - used by PostToolUse hook.

    Automatically infers work type from conventional commit message.
    """
    try:
        from core.dev_context import DevContextManager
        from core.git_analyzer import GitAnalyzer

        with DevContextManager(
            project_name=project_name,
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD
        ) as manager:
            # Parse files changed
            files = [f.strip() for f in files_changed.split(",") if f.strip()]

            # Record each file change
            code_change_uids = []
            for file_path in files:
                uid = manager.record_code_change(
                    commit_hash=commit_hash,
                    file_path=file_path,
                    change_type="modified",
                    author=author
                )
                code_change_uids.append(uid)

            # Try to auto-link to work items based on commit message
            linked_work_items = []
            # Look for work item references in commit message (e.g., WORK-123, #123)
            import re
            work_refs = re.findall(r'(?:WORK-|#)(\d+)', message, re.IGNORECASE)
            # Also check conventional commit for auto-creating work items
            analyzer = GitAnalyzer(project_name)
            work_type, confidence = analyzer.infer_work_type(message, files)

        return {
            "commit_hash": commit_hash,
            "project": project_name,
            "files_recorded": len(code_change_uids),
            "inferred_work_type": work_type,
            "confidence": confidence,
            "work_refs_found": work_refs,
            "linked_work_items": linked_work_items
        }
    except Exception as e:
        return {
            "commit_hash": commit_hash,
            "project": project_name,
            "error": str(e)
        }


def _generate_suggestion(file_path: str, related_work: list, open_work: list) -> str:
    """Generate a contextual suggestion for the agent."""
    if related_work:
        items = ", ".join([w.get("title", w.get("uid", "unknown"))[:30] for w in related_work[:3]])
        return f"This file is related to: {items}. Consider updating these work items."
    elif open_work:
        return f"There are {len(open_work)} open work items. Consider linking your changes."
    return None


def _generate_session_context(project: str, open_items: list, in_progress: list,
                               blocked: list, priority_items: list) -> str:
    """Generate session context prompt for injection."""
    lines = [f"## ESS Dev Context for {project}"]

    if priority_items:
        lines.append(f"\n**High Priority ({len(priority_items)}):**")
        for item in priority_items[:5]:
            lines.append(f"- [{item.get('work_type', 'task')}] {item.get('title', 'Unknown')}")

    if blocked:
        lines.append(f"\n**Blocked ({len(blocked)}):**")
        for item in blocked[:3]:
            lines.append(f"- {item.get('title', 'Unknown')}")

    lines.append(f"\n**Summary:** {len(open_items)} open, {len(in_progress)} in progress, {len(blocked)} blocked")
    lines.append("\nUse `trace_file_to_work()` before modifying files to understand context.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Veracity Engine HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
