#!/usr/bin/env python3
"""
ESS PostToolUse Hook - Auto-track git commits

This hook monitors Bash commands for git commits and automatically
records them in ESS for work item tracking.

Hook Type: PostToolUse
Matches: Bash (git commit commands)
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from urllib.parse import quote, urlencode

# Configuration
ESS_URL = os.getenv("ESS_URL", "http://localhost:8000")
ESS_PROJECT = os.getenv("ESS_PROJECT", "")


def is_git_commit_command(command: str) -> bool:
    """Check if the command is a git commit."""
    if not command:
        return False
    # Match: git commit, git commit -m, git commit --amend, etc.
    return bool(re.search(r'\bgit\s+commit\b', command, re.IGNORECASE))


def get_last_commit_info(cwd: str = None) -> dict:
    """Get info about the last git commit."""
    try:
        # Get commit hash
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%s|%ae"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5
        )
        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split("|", 2)
        if len(parts) < 3:
            return None

        commit_hash, message, author = parts

        # Get files changed
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5
        )
        files = result.stdout.strip().split("\n") if result.returncode == 0 else []

        return {
            "commit_hash": commit_hash,
            "message": message,
            "author": author,
            "files_changed": [f for f in files if f]
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def get_project_from_path(cwd: str) -> str:
    """Extract project name from working directory."""
    if ESS_PROJECT:
        return ESS_PROJECT

    if not cwd:
        return ""

    # Try to extract from path (e.g., /Users/.../project-name)
    parts = cwd.split("/")
    if "Projects" in parts:
        idx = parts.index("Projects")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    # Use last directory component as project name
    return parts[-1] if parts else ""


def record_commit_in_ess(project_name: str, commit_info: dict) -> dict:
    """Record the commit in ESS."""
    if not project_name or not commit_info:
        return None

    try:
        url = f"{ESS_URL}/api/record-commit/{quote(project_name)}"

        data = urlencode({
            "commit_hash": commit_info["commit_hash"],
            "message": commit_info["message"],
            "author": commit_info["author"],
            "files_changed": ",".join(commit_info.get("files_changed", []))
        }).encode()

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None
    except Exception:
        return None


def format_tracking_message(result: dict, commit_info: dict) -> str:
    """Format a message about the tracked commit."""
    if not result:
        return ""

    lines = ["**ESS Commit Tracked:**"]

    commit_hash = commit_info.get("commit_hash", "")[:8]
    lines.append(f"- Commit: `{commit_hash}`")

    files_count = result.get("files_recorded", 0)
    if files_count:
        lines.append(f"- Files recorded: {files_count}")

    work_type = result.get("inferred_work_type")
    confidence = result.get("confidence", 0)
    if work_type and confidence > 0.5:
        lines.append(f"- Inferred type: {work_type} (confidence: {confidence:.0%})")

    work_refs = result.get("work_refs_found", [])
    if work_refs:
        lines.append(f"- Work item refs: {', '.join(work_refs)}")

    return "\n".join(lines)


def main():
    """Main hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # Invalid input - silently exit
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    tool_result = hook_input.get("tool_result", {})

    # Only process Bash tool
    if tool_name != "Bash":
        return

    command = tool_input.get("command", "")

    # Only process git commit commands
    if not is_git_commit_command(command):
        return

    # Check if the command succeeded (look for success indicators in result)
    result_text = str(tool_result)
    if "error" in result_text.lower() or "failed" in result_text.lower():
        return

    # Get working directory from tool input or use current
    cwd = tool_input.get("cwd") or os.getcwd()

    # Get project name
    project_name = get_project_from_path(cwd)
    if not project_name:
        return

    # Get commit info
    commit_info = get_last_commit_info(cwd)
    if not commit_info:
        return

    # Record in ESS
    result = record_commit_in_ess(project_name, commit_info)

    # Output tracking message
    message = format_tracking_message(result, commit_info)
    if message:
        # PostToolUse hooks output to stderr for logging
        print(message, file=sys.stderr)


if __name__ == "__main__":
    main()
