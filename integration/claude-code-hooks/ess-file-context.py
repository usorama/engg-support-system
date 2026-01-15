#!/usr/bin/env python3
"""
ESS PreToolUse Hook - Auto-inject file context before Edit/Write

This hook queries ESS for related work items whenever an agent is about
to modify a file. The context is injected into the conversation to help
agents understand the history and purpose of the file.

Hook Type: PreToolUse
Matches: Edit, Write
"""

import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import quote

# Configuration
ESS_URL = os.getenv("ESS_URL", "http://localhost:8000")
ESS_PROJECT = os.getenv("ESS_PROJECT", "")  # Set in project .claude/settings.json


def get_file_context(project_name: str, file_path: str) -> dict:
    """Query ESS for file context."""
    if not project_name:
        return None

    try:
        url = f"{ESS_URL}/api/file-context/{quote(project_name)}?file_path={quote(file_path)}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        # Silently fail - don't block the edit
        return None
    except Exception:
        return None


def format_context_message(context: dict) -> str:
    """Format context for injection into conversation."""
    if not context:
        return ""

    lines = []
    file_path = context.get("file_path", "unknown")

    # Related work items
    related = context.get("related_work_items", [])
    if related:
        lines.append(f"**ESS Context for `{file_path}`:**")
        lines.append("Related work items:")
        for item in related[:3]:
            title = item.get("title", "Unknown")[:50]
            status = item.get("status", "unknown")
            work_type = item.get("work_type", "task")
            lines.append(f"  - [{work_type}] {title} ({status})")

    # Suggestion
    suggestion = context.get("suggestion")
    if suggestion:
        lines.append(f"\n{suggestion}")

    # Open work items (if no related items)
    if not related:
        open_items = context.get("open_work_items", [])
        if open_items:
            lines.append(f"**Note:** {len(open_items)} open work items in project.")
            lines.append("Consider linking your changes to a work item.")

    return "\n".join(lines) if lines else ""


def main():
    """Main hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # Invalid input - allow the operation
        print(json.dumps({"decision": "allow"}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only process Edit and Write tools
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({"decision": "allow"}))
        return

    # Get file path from tool input
    file_path = tool_input.get("file_path", "")
    if not file_path:
        print(json.dumps({"decision": "allow"}))
        return

    # Normalize file path (extract relative path from absolute)
    # Try to get project name from environment or path
    project_name = ESS_PROJECT
    if not project_name:
        # Try to extract from file path (e.g., /Users/.../project-name/src/...)
        parts = file_path.split("/")
        if "Projects" in parts:
            idx = parts.index("Projects")
            if idx + 1 < len(parts):
                project_name = parts[idx + 1]

    if not project_name:
        print(json.dumps({"decision": "allow"}))
        return

    # Query ESS for file context
    context = get_file_context(project_name, file_path)

    if not context:
        print(json.dumps({"decision": "allow"}))
        return

    # Format context message
    message = format_context_message(context)

    if message:
        # Allow with context injection
        print(json.dumps({
            "decision": "allow",
            "message": message
        }))
    else:
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
