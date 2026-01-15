#!/usr/bin/env python3
"""
ESS SessionStart Hook - Auto-inject project context at session start

This hook queries ESS at the start of each Claude Code session and injects
relevant project context (open work items, high priority items, blocked items).

Hook Type: SessionStart
Output: Context injection message
"""

import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import quote

# Configuration
ESS_URL = os.getenv("ESS_URL", "http://localhost:8000")
ESS_PROJECT = os.getenv("ESS_PROJECT", "")


def get_project_from_cwd() -> str:
    """Extract project name from current working directory."""
    if ESS_PROJECT:
        return ESS_PROJECT

    cwd = os.getcwd()
    parts = cwd.split("/")

    # Try to extract from path (e.g., /Users/.../Projects/project-name)
    if "Projects" in parts:
        idx = parts.index("Projects")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    # Use last directory component as project name
    return parts[-1] if parts else ""


def get_project_context(project_name: str) -> dict:
    """Query ESS for project context."""
    if not project_name:
        return None

    try:
        url = f"{ESS_URL}/api/project-context/{quote(project_name)}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        # Silently fail - don't block session start
        return None
    except Exception:
        return None


def check_ess_health() -> bool:
    """Check if ESS is available."""
    try:
        url = f"{ESS_URL}/health"
        req = urllib.request.Request(url, method="GET")

        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get("status") in ("healthy", "degraded")
    except Exception:
        return False


def format_session_context(project_name: str, context: dict) -> str:
    """Format project context for session injection."""
    if not context:
        return ""

    lines = []

    # Header
    lines.append(f"## ESS Dev Context: {project_name}")
    lines.append("")

    # Summary
    summary = context.get("summary", {})
    open_count = summary.get("open", 0)
    in_progress = summary.get("in_progress", 0)
    blocked = summary.get("blocked", 0)

    if open_count or in_progress or blocked:
        lines.append(f"**Work Items:** {open_count} open | {in_progress} in progress | {blocked} blocked")
        lines.append("")

    # High priority items
    priority_items = context.get("high_priority_items", [])
    if priority_items:
        lines.append("**High Priority:**")
        for item in priority_items[:5]:
            title = item.get("title", "Unknown")[:60]
            status = item.get("status", "open")
            work_type = item.get("work_type", "task")
            uid = item.get("uid", "")[:12]
            lines.append(f"- [{work_type}] {title} ({status}) `{uid}`")
        lines.append("")

    # Tips
    lines.append("**Tips:**")
    lines.append("- Use `trace_file_to_work(file_path, project)` before modifying files")
    lines.append("- Use `query_work_items(project, status='open')` to see all open items")
    lines.append("- Commits with conventional prefixes (feat:, fix:) auto-link to work items")

    return "\n".join(lines)


def main():
    """Main hook entry point."""
    # Get project name
    project_name = get_project_from_cwd()

    if not project_name:
        # No project detected - output nothing
        return

    # Check if ESS is available
    if not check_ess_health():
        # ESS not available - output a hint
        print("**Note:** ESS not available. Start with: `python -m core.http_server`", file=sys.stderr)
        return

    # Get project context
    context = get_project_context(project_name)

    if not context or context.get("error"):
        # Project not indexed or error
        error = context.get("error", "") if context else ""
        if "not found" in error.lower() or not context:
            print(f"**ESS:** Project '{project_name}' not indexed. Run: `index_project(project_name='{project_name}')`", file=sys.stderr)
        return

    # Format and output context
    message = format_session_context(project_name, context)

    if message:
        # SessionStart hooks output context to stdout for injection
        print(message)


if __name__ == "__main__":
    main()
