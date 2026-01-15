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


def main():
    parser = argparse.ArgumentParser(description="Veracity Engine HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
