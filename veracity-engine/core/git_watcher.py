"""
Git Watcher Daemon - Phase 3

Monitors Git repositories for new commits and automatically creates/links work items
based on conventional commit parsing and semantic analysis.
"""

import re
import asyncio
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


class GitWatcherError(Exception):
    """Base exception for Git watcher errors"""
    pass


@dataclass
class ConventionalCommit:
    """Parsed conventional commit data"""
    type: Optional[str] = None
    scope: Optional[str] = None
    description: str = ""
    body: Optional[str] = None
    footer: Optional[str] = None
    is_breaking: bool = False
    is_conventional: bool = True
    references: List[str] = field(default_factory=list)
    work_type: str = "chore"  # Default work type

    # Mapping from conventional commit type to work type
    TYPE_TO_WORK_TYPE = {
        "feat": "feature",
        "fix": "bug",
        "docs": "docs",
        "style": "chore",
        "refactor": "refactor",
        "perf": "enhancement",
        "test": "chore",
        "build": "chore",
        "ci": "chore",
        "chore": "chore",
        "revert": "bug"
    }


class CommitParser:
    """
    Parser for conventional commit messages.

    Supports the Conventional Commits specification:
    https://www.conventionalcommits.org/

    Format: <type>[optional scope][!]: <description>
            [optional body]
            [optional footer(s)]
    """

    # Pattern for conventional commit header
    HEADER_PATTERN = re.compile(
        r'^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)'
        r'(?:\((?P<scope>[^)]+)\))?'
        r'(?P<breaking>!)?'
        r':\s*'
        r'(?P<description>.+)$',
        re.IGNORECASE
    )

    # Pattern for issue/PR references
    REFERENCE_PATTERN = re.compile(r'#(\d+)')

    # Pattern for "Fixes/Closes/Resolves #123" footers
    FOOTER_REFERENCE_PATTERN = re.compile(
        r'(?:fix(?:es)?|close[sd]?|resolve[sd]?)\s+#(\d+)',
        re.IGNORECASE
    )

    def parse(self, message: str) -> ConventionalCommit:
        """
        Parse a commit message into a ConventionalCommit object.

        Args:
            message: Full commit message (may include body and footer)

        Returns:
            ConventionalCommit object with parsed data
        """
        # Split message into parts
        parts = message.strip().split('\n\n', 2)
        header = parts[0].strip()
        body = parts[1].strip() if len(parts) > 1 else None
        footer = parts[2].strip() if len(parts) > 2 else None

        # Try to parse as conventional commit
        match = self.HEADER_PATTERN.match(header)

        if match:
            commit_type = match.group('type').lower()
            scope = match.group('scope')
            is_breaking = match.group('breaking') == '!'
            description = match.group('description')

            # Determine work type from commit type
            work_type = ConventionalCommit.TYPE_TO_WORK_TYPE.get(commit_type, "chore")

            # Extract references from entire message
            references = self._extract_references(message)

            return ConventionalCommit(
                type=commit_type,
                scope=scope,
                description=description,
                body=body,
                footer=footer,
                is_breaking=is_breaking,
                is_conventional=True,
                references=references,
                work_type=work_type
            )
        else:
            # Non-conventional commit
            references = self._extract_references(message)

            return ConventionalCommit(
                type=None,
                scope=None,
                description=header,
                body=body,
                footer=footer,
                is_breaking=False,
                is_conventional=False,
                references=references,
                work_type="chore"  # Default for non-conventional
            )

    def _extract_references(self, message: str) -> List[str]:
        """Extract issue/PR references from message."""
        references = set()

        # Find all #123 style references
        for match in self.REFERENCE_PATTERN.finditer(message):
            references.add(f"#{match.group(1)}")

        return sorted(list(references))


@dataclass
class GitWatcherConfig:
    """Configuration for Git watcher daemon"""
    project_name: str
    repo_path: str
    poll_interval: int = 30  # seconds
    auto_create_work_items: bool = True
    auto_link_commits: bool = True
    min_confidence: float = 0.7
    branch_filter: List[str] = field(default_factory=list)  # Empty = all branches
    ignore_patterns: List[str] = field(default_factory=lambda: [
        r'^Merge\s+',  # Ignore merge commits
        r'^Revert\s+"',  # Ignore revert commits (handled separately)
    ])


class GitWatcher:
    """
    Git repository watcher daemon.

    Monitors a Git repository for new commits and automatically:
    - Parses conventional commit messages
    - Creates work items for feature/fix commits
    - Links commits to existing work items based on semantic analysis
    """

    def __init__(self, config: GitWatcherConfig):
        """
        Initialize Git watcher.

        Args:
            config: Watcher configuration
        """
        self.config = config
        self.is_running = False
        self.last_commit_hash: Optional[str] = None
        self._processed_commits: Set[str] = set()
        self._parser = CommitParser()
        self._dev_context = None
        self._git_analyzer = None

        # Compile ignore patterns
        self._ignore_patterns = [
            re.compile(pattern) for pattern in config.ignore_patterns
        ]

        logger.info("Git watcher initialized",
                   project=config.project_name,
                   repo=config.repo_path)

    def _run_git_command(self, *args) -> subprocess.CompletedProcess:
        """Run a git command in the repository."""
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.config.repo_path,
            capture_output=True,
            text=True
        )

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run_git_command("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()

    def get_new_commits(self, since_hash: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get new commits since the last check.

        Args:
            since_hash: Only return commits after this hash

        Returns:
            List of commit dictionaries
        """
        # Build git log command
        log_format = "--format=%H|%an|%ae|%aI|%s"

        if since_hash or self.last_commit_hash:
            ref = since_hash or self.last_commit_hash
            result = self._run_git_command("log", log_format, f"{ref}..HEAD")
        else:
            # First run - get recent commits
            result = self._run_git_command("log", log_format, "-10")

        if result.returncode != 0:
            logger.warning("Git log failed", error=result.stderr)
            return []

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|', 4)
            if len(parts) < 5:
                continue

            commit_hash, author_name, author_email, timestamp, subject = parts

            # Skip if already processed
            if commit_hash in self._processed_commits:
                continue

            # Check branch filter
            if self.config.branch_filter:
                current_branch = self.get_current_branch()
                if current_branch not in self.config.branch_filter:
                    continue

            # Check ignore patterns
            if self._should_ignore(subject):
                self._processed_commits.add(commit_hash)
                continue

            # Get full commit message
            msg_result = self._run_git_command("log", "-1", "--format=%B", commit_hash)
            full_message = msg_result.stdout.strip()

            # Get files changed
            files_result = self._run_git_command(
                "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash
            )
            files_changed = [f for f in files_result.stdout.strip().split('\n') if f]

            commits.append({
                "hash": commit_hash,
                "author_name": author_name,
                "author_email": author_email,
                "timestamp": timestamp,
                "subject": subject,
                "message": full_message,
                "files_changed": files_changed
            })

        # Update last commit hash
        if commits:
            self.last_commit_hash = commits[0]["hash"]

        return commits

    def _should_ignore(self, message: str) -> bool:
        """Check if commit should be ignored based on patterns."""
        for pattern in self._ignore_patterns:
            if pattern.search(message):
                return True
        return False

    async def process_commit(self, commit: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single commit.

        Args:
            commit: Commit dictionary

        Returns:
            Processing result dictionary
        """
        commit_hash = commit["hash"]
        message = commit["message"]

        # Parse the commit message
        parsed = self._parser.parse(message)

        result = {
            "commit_hash": commit_hash,
            "parsed_type": parsed.type,
            "work_type": parsed.work_type,
            "is_conventional": parsed.is_conventional,
            "action": "skipped",
            "reason": None
        }

        # Mark as processed
        self._processed_commits.add(commit_hash)

        # Record the code change
        if self._dev_context:
            for file_path in commit.get("files_changed", []):
                try:
                    self._dev_context.record_code_change(
                        commit_hash=commit_hash,
                        file_path=file_path,
                        change_type="modified",
                        author=commit.get("author_email")
                    )
                except Exception as e:
                    logger.warning(f"Failed to record code change: {e}")

        # Try to link to existing work item first
        if self.config.auto_link_commits and self._git_analyzer and self._dev_context:
            work_items = self._dev_context.query_work_items(
                project_name=self.config.project_name
            )

            if work_items:
                analysis = self._git_analyzer.analyze_commit_work_relation(
                    commit, work_items
                )

                if analysis["confidence"] >= self.config.min_confidence and analysis["best_match"]:
                    # Link to existing work item
                    try:
                        self._dev_context.link_code_to_work(
                            commit_hash=commit_hash,
                            work_item_uid=analysis["best_match"],
                            confidence=analysis["confidence"]
                        )
                        result["action"] = "linked_to_existing"
                        result["work_item_uid"] = analysis["best_match"]
                        result["confidence"] = analysis["confidence"]
                        return result
                    except Exception as e:
                        logger.warning(f"Failed to link commit: {e}")

        # Create new work item if enabled and commit type warrants it
        if self.config.auto_create_work_items and parsed.is_conventional:
            if parsed.type in ["feat", "fix"]:
                try:
                    title = self._generate_work_item_title(parsed)
                    description = self._generate_work_item_description(commit, parsed)

                    work_item_uid = self._dev_context.create_work_item(
                        title=title,
                        description=description,
                        work_type=parsed.work_type,
                        priority=self._infer_priority(parsed),
                        source="git_watcher"
                    )

                    # Link the commit to the new work item
                    self._dev_context.link_code_to_work(
                        commit_hash=commit_hash,
                        work_item_uid=work_item_uid,
                        confidence=1.0
                    )

                    result["action"] = "created_work_item"
                    result["work_item_uid"] = work_item_uid
                    return result

                except Exception as e:
                    logger.error(f"Failed to create work item: {e}")
                    result["action"] = "failed"
                    result["error"] = str(e)
                    return result

        # No action taken
        if not parsed.is_conventional:
            result["reason"] = "non_conventional_commit"
        elif parsed.type not in ["feat", "fix"]:
            result["reason"] = "non_trackable_type"
        else:
            result["reason"] = "low_confidence"

        return result

    def _generate_work_item_title(self, parsed: ConventionalCommit) -> str:
        """Generate work item title from parsed commit."""
        type_prefix = {
            "feat": "Feature:",
            "fix": "Bug:",
        }.get(parsed.type, "")

        scope_part = f" [{parsed.scope}]" if parsed.scope else ""

        return f"{type_prefix}{scope_part} {parsed.description}"

    def _generate_work_item_description(self, commit: Dict[str, Any],
                                       parsed: ConventionalCommit) -> str:
        """Generate work item description from commit."""
        parts = [parsed.description]

        if parsed.body:
            parts.append(f"\n\n{parsed.body}")

        if parsed.references:
            parts.append(f"\n\nReferences: {', '.join(parsed.references)}")

        parts.append(f"\n\nSource: Git commit {commit['hash'][:8]}")
        parts.append(f"Author: {commit.get('author_name', 'Unknown')}")

        if commit.get("files_changed"):
            files_list = "\n".join(f"  - {f}" for f in commit["files_changed"][:10])
            parts.append(f"\n\nFiles changed:\n{files_list}")

        return "".join(parts)

    def _infer_priority(self, parsed: ConventionalCommit) -> str:
        """Infer priority from commit."""
        if parsed.is_breaking:
            return "critical"
        elif parsed.type == "fix":
            return "high"
        elif parsed.type == "feat":
            return "medium"
        return "low"

    async def watch_once(self) -> List[Dict[str, Any]]:
        """
        Run one iteration of the watch loop.

        Returns:
            List of processing results
        """
        commits = self.get_new_commits()
        results = []

        for commit in commits:
            try:
                result = await self.process_commit(commit)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process commit {commit['hash']}: {e}")
                results.append({
                    "commit_hash": commit["hash"],
                    "action": "failed",
                    "error": str(e)
                })

        return results

    async def start(self):
        """Start the watch loop."""
        self.is_running = True
        logger.info("Git watcher started", project=self.config.project_name)

        while self.is_running:
            try:
                results = await self.watch_once()
                if results:
                    logger.info(f"Processed {len(results)} commits",
                               project=self.config.project_name)
            except Exception as e:
                logger.error(f"Watch loop error: {e}")

            await asyncio.sleep(self.config.poll_interval)

    def stop(self):
        """Stop the watch loop."""
        self.is_running = False
        logger.info("Git watcher stopped", project=self.config.project_name)
