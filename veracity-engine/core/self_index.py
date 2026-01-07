"""
Self-Indexing Configuration and Automation (STORY-017).

This module provides configuration and utilities for indexing the
veracity-engine repository itself into the knowledge graph.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import os
import hashlib
import json
import time


# Canonical project name for this repository
SELF_PROJECT_NAME = "veracity-engine"

# Default exclusion patterns for self-indexing
DEFAULT_EXCLUSIONS = [
    ".git",
    ".github",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "coverage_report",
    "htmlcov",
    "*.egg-info",
    "dist",
    "build",
    ".venv",
    "venv",
    "node_modules",
    ".env*",
    "*.log",
    ".graph_hashes_*",
]


@dataclass
class SelfIndexConfig:
    """Configuration for self-indexing this repository."""

    project_name: str = SELF_PROJECT_NAME
    root_dir: Optional[str] = None  # Defaults to repo root
    exclusions: List[str] = field(default_factory=lambda: DEFAULT_EXCLUSIONS.copy())
    include_docs: bool = True
    include_tests: bool = False  # Exclude tests by default
    deterministic: bool = True
    verify_after_index: bool = True

    def __post_init__(self):
        """Set default root directory to repo root."""
        if self.root_dir is None:
            # Find repo root by looking for .git directory
            current = Path(__file__).parent.parent
            while current != current.parent:
                if (current / ".git").exists():
                    self.root_dir = str(current)
                    break
                current = current.parent
            if self.root_dir is None:
                self.root_dir = str(Path(__file__).parent.parent)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "project_name": self.project_name,
            "root_dir": self.root_dir,
            "exclusions": self.exclusions,
            "include_docs": self.include_docs,
            "include_tests": self.include_tests,
            "deterministic": self.deterministic,
            "verify_after_index": self.verify_after_index,
        }


@dataclass
class IndexingResult:
    """Result of an indexing operation."""

    success: bool
    project_name: str
    node_count: int = 0
    edge_count: int = 0
    file_count: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    timestamp: str = ""
    content_hash: str = ""

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            from datetime import datetime, timezone
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "project_name": self.project_name,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "file_count": self.file_count,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
        }


def compute_repo_hash(root_dir: str, exclusions: List[str] = None) -> str:
    """
    Compute a hash of the repository content for change detection.

    Args:
        root_dir: Repository root directory
        exclusions: Patterns to exclude

    Returns:
        SHA256 hash of file paths and mtimes
    """
    if exclusions is None:
        exclusions = DEFAULT_EXCLUSIONS

    root_path = Path(root_dir)
    entries = []

    for file_path in sorted(root_path.rglob("*")):
        if not file_path.is_file():
            continue

        # Check exclusions
        rel_path = str(file_path.relative_to(root_path))
        skip = False

        # Always exclude hash files to avoid self-referential issues
        if rel_path.startswith(".graph_hashes_"):
            continue

        for pattern in exclusions:
            if pattern.startswith("*"):
                if rel_path.endswith(pattern[1:]):
                    skip = True
                    break
            elif pattern in rel_path.split(os.sep):
                skip = True
                break
        if skip:
            continue

        # Add path and mtime
        try:
            mtime = file_path.stat().st_mtime
            entries.append(f"{rel_path}:{mtime}")
        except OSError:
            continue

    # Compute hash
    content = "\n".join(entries)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def should_reindex(
    root_dir: str,
    project_name: str = SELF_PROJECT_NAME,
    exclusions: List[str] = None,
) -> bool:
    """
    Check if the repository needs re-indexing based on content hash.

    Args:
        root_dir: Repository root directory
        project_name: Project name in KG
        exclusions: Patterns to exclude

    Returns:
        True if re-indexing is needed
    """
    hash_file = Path(root_dir) / f".graph_hashes_{project_name}.json"

    current_hash = compute_repo_hash(root_dir, exclusions)

    if not hash_file.exists():
        return True

    try:
        with open(hash_file, "r") as f:
            stored = json.load(f)
            stored_hash = stored.get("content_hash", "")
            return stored_hash != current_hash
    except (json.JSONDecodeError, IOError):
        return True


def save_index_result(result: IndexingResult, root_dir: str) -> None:
    """
    Save indexing result to hash file for change detection.

    Args:
        result: Indexing result
        root_dir: Repository root directory
    """
    hash_file = Path(root_dir) / f".graph_hashes_{result.project_name}.json"

    with open(hash_file, "w") as f:
        json.dump(result.to_dict(), f, indent=2)


def get_self_index_command(config: SelfIndexConfig = None) -> List[str]:
    """
    Get the command to run self-indexing.

    Args:
        config: Self-indexing configuration

    Returns:
        Command as list of strings
    """
    if config is None:
        config = SelfIndexConfig()

    cmd = [
        "python3",
        "core/build_graph.py",
        "--project-name",
        config.project_name,
        "--root-dir",
        config.root_dir,
    ]

    return cmd


def verify_indexing(
    project_name: str = SELF_PROJECT_NAME,
    neo4j_uri: str = None,
    neo4j_user: str = None,
    neo4j_password: str = None,
) -> Dict[str, Any]:
    """
    Verify indexing results by querying Neo4j.

    Args:
        project_name: Project name in KG
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Dictionary with verification results
    """
    from neo4j import GraphDatabase

    uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
    password = neo4j_password or os.getenv("NEO4J_PASSWORD", "password")

    result = {
        "project_name": project_name,
        "success": False,
        "node_count": 0,
        "edge_count": 0,
        "nodes_by_type": {},
        "error": None,
    }

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Count nodes
            query_result = session.run(
                "MATCH (n {project: $project}) RETURN count(n) as count",
                project=project_name
            )
            result["node_count"] = query_result.single()["count"]

            # Count relationships
            query_result = session.run(
                "MATCH (n {project: $project})-[r]-() RETURN count(r) as count",
                project=project_name
            )
            result["edge_count"] = query_result.single()["count"]

            # Count by type
            query_result = session.run("""
                MATCH (n {project: $project})
                RETURN labels(n)[0] as type, count(n) as count
                ORDER BY count DESC
            """, project=project_name)
            result["nodes_by_type"] = {
                row["type"]: row["count"]
                for row in query_result
            }

            result["success"] = result["node_count"] > 0

        driver.close()
    except Exception as e:
        result["error"] = str(e)

    return result


def install_git_hook(repo_root: str = None) -> bool:
    """
    Install the post-commit git hook for auto-indexing.

    Args:
        repo_root: Repository root directory

    Returns:
        True if installation succeeded
    """
    if repo_root is None:
        repo_root = str(Path(__file__).parent.parent)

    root_path = Path(repo_root)
    hook_source = root_path / "scripts" / "hooks" / "post-commit"
    hook_dest = root_path / ".git" / "hooks" / "post-commit"

    if not hook_source.exists():
        return False

    try:
        # Read hook content
        with open(hook_source, "r") as f:
            hook_content = f.read()

        # Write to hooks directory
        hook_dest.parent.mkdir(parents=True, exist_ok=True)
        with open(hook_dest, "w") as f:
            f.write(hook_content)

        # Make executable
        hook_dest.chmod(0o755)
        return True
    except OSError:
        return False


def uninstall_git_hook(repo_root: str = None) -> bool:
    """
    Uninstall the post-commit git hook.

    Args:
        repo_root: Repository root directory

    Returns:
        True if uninstallation succeeded
    """
    if repo_root is None:
        repo_root = str(Path(__file__).parent.parent)

    hook_path = Path(repo_root) / ".git" / "hooks" / "post-commit"

    if hook_path.exists():
        try:
            hook_path.unlink()
            return True
        except OSError:
            return False
    return True  # Already uninstalled
