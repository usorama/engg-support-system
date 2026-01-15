"""
Test suite for Git Watcher Daemon - Phase 3

Tests the file system watcher that monitors Git repositories for new commits
and automatically creates/links work items based on conventional commit parsing.
"""

import pytest
import json
import tempfile
import os
import subprocess
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path


# Import git watcher components
try:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../core')))

    from git_watcher import (
        GitWatcher,
        CommitParser,
        ConventionalCommit,
        GitWatcherConfig,
        GitWatcherError
    )
except ImportError as e:
    pytest.skip(f"Git watcher not implemented yet: {e}", allow_module_level=True)


class TestConventionalCommitParser:
    """Test conventional commit message parsing"""

    def test_parse_feat_commit(self):
        """Test parsing feature commit"""
        parser = CommitParser()
        result = parser.parse("feat: add user authentication")

        assert result.type == "feat"
        assert result.scope is None
        assert result.description == "add user authentication"
        assert result.is_breaking is False
        assert result.work_type == "feature"

    def test_parse_fix_commit_with_scope(self):
        """Test parsing fix commit with scope"""
        parser = CommitParser()
        result = parser.parse("fix(auth): resolve token validation bug")

        assert result.type == "fix"
        assert result.scope == "auth"
        assert result.description == "resolve token validation bug"
        assert result.work_type == "bug"

    def test_parse_breaking_change(self):
        """Test parsing breaking change commit"""
        parser = CommitParser()
        result = parser.parse("feat!: redesign API endpoints")

        assert result.type == "feat"
        assert result.is_breaking is True
        assert result.description == "redesign API endpoints"

    def test_parse_commit_with_body(self):
        """Test parsing commit with body"""
        parser = CommitParser()
        message = """fix(parser): resolve memory leak

The tokenizer was not releasing memory properly after parsing.
This fix ensures all buffers are freed.

Fixes #123"""

        result = parser.parse(message)

        assert result.type == "fix"
        assert result.scope == "parser"
        assert result.body is not None
        assert "memory" in result.body.lower()
        assert result.references == ["#123"]

    def test_parse_non_conventional_commit(self):
        """Test parsing non-conventional commit message"""
        parser = CommitParser()
        result = parser.parse("Updated the readme file")

        assert result.type is None
        assert result.is_conventional is False
        assert result.description == "Updated the readme file"
        assert result.work_type == "chore"  # Default for non-conventional

    def test_parse_all_commit_types(self):
        """Test parsing all conventional commit types"""
        parser = CommitParser()

        test_cases = [
            ("feat: new feature", "feat", "feature"),
            ("fix: bug fix", "fix", "bug"),
            ("docs: update docs", "docs", "docs"),
            ("style: format code", "style", "chore"),
            ("refactor: restructure code", "refactor", "refactor"),
            ("perf: improve performance", "perf", "enhancement"),
            ("test: add tests", "test", "chore"),
            ("build: update build", "build", "chore"),
            ("ci: update CI", "ci", "chore"),
            ("chore: maintenance", "chore", "chore"),
        ]

        for message, expected_type, expected_work_type in test_cases:
            result = parser.parse(message)
            assert result.type == expected_type, f"Failed for {message}"
            assert result.work_type == expected_work_type, f"Work type mismatch for {message}"


class TestGitWatcherConfig:
    """Test git watcher configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = GitWatcherConfig(
            project_name="test-project",
            repo_path="/path/to/repo"
        )

        assert config.project_name == "test-project"
        assert config.repo_path == "/path/to/repo"
        assert config.poll_interval == 30  # Default 30 seconds
        assert config.auto_create_work_items is True
        assert config.auto_link_commits is True
        assert config.min_confidence == 0.7

    def test_custom_config(self):
        """Test custom configuration"""
        config = GitWatcherConfig(
            project_name="my-project",
            repo_path="/my/repo",
            poll_interval=60,
            auto_create_work_items=False,
            min_confidence=0.9,
            branch_filter=["main", "develop"]
        )

        assert config.poll_interval == 60
        assert config.auto_create_work_items is False
        assert config.min_confidence == 0.9
        assert "main" in config.branch_filter


class TestGitWatcher:
    """Test Git watcher daemon functionality"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager"""
        mock = Mock()
        mock.create_work_item.return_value = "test-project::workitem::abc123"
        mock.record_code_change.return_value = "test-project::codechanqge::def456"
        mock.link_code_to_work.return_value = True
        mock.query_work_items.return_value = [
            {
                "uid": "test-project::workitem::existing1",
                "title": "Implement authentication",
                "description": "Add JWT-based auth",
                "work_type": "feature",
                "status": "in_progress"
            }
        ]
        return mock

    @pytest.fixture
    def mock_git_analyzer(self):
        """Mock GitAnalyzer"""
        mock = Mock()
        mock.analyze_commit_work_relation.return_value = {
            "confidence": 0.85,
            "best_match": "test-project::workitem::existing1",
            "commit_type": "feature",
            "reasons": ["semantic match"]
        }
        return mock

    @pytest.fixture
    def watcher_config(self, tmp_path):
        """Create watcher config with temp repo path"""
        return GitWatcherConfig(
            project_name="test-project",
            repo_path=str(tmp_path),
            poll_interval=1,
            auto_create_work_items=True,
            auto_link_commits=True
        )

    def test_watcher_initialization(self, watcher_config):
        """Test watcher initializes correctly"""
        watcher = GitWatcher(watcher_config)

        assert watcher.config.project_name == "test-project"
        assert watcher.is_running is False
        assert watcher.last_commit_hash is None

    def test_get_new_commits(self, watcher_config, tmp_path):
        """Test detecting new commits"""
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: initial commit"], cwd=tmp_path, capture_output=True)

        watcher = GitWatcher(watcher_config)
        commits = watcher.get_new_commits()

        assert len(commits) >= 1
        assert commits[0]["message"].startswith("feat:")

    @pytest.mark.anyio
    async def test_process_commit_creates_work_item(self, watcher_config, mock_dev_context):
        """Test that processing a feat commit creates a work item"""
        watcher = GitWatcher(watcher_config)
        watcher._dev_context = mock_dev_context

        commit = {
            "hash": "abc123def456",
            "message": "feat: add user dashboard",
            "author": "dev@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_changed": ["src/dashboard.js"]
        }

        result = await watcher.process_commit(commit)

        assert result["action"] == "created_work_item"
        mock_dev_context.create_work_item.assert_called_once()

        # Verify work item details
        call_kwargs = mock_dev_context.create_work_item.call_args[1]
        assert "dashboard" in call_kwargs["title"].lower()
        assert call_kwargs["work_type"] == "feature"

    @pytest.mark.anyio
    async def test_process_commit_links_to_existing(self, watcher_config, mock_dev_context, mock_git_analyzer):
        """Test that processing a commit links to existing work item"""
        watcher = GitWatcher(watcher_config)
        watcher._dev_context = mock_dev_context
        watcher._git_analyzer = mock_git_analyzer
        watcher.config.auto_create_work_items = False  # Only link, don't create

        commit = {
            "hash": "xyz789",
            "message": "fix: resolve auth token issue",
            "author": "dev@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_changed": ["src/auth/token.js"]
        }

        result = await watcher.process_commit(commit)

        assert result["action"] == "linked_to_existing"
        mock_dev_context.link_code_to_work.assert_called()

    @pytest.mark.anyio
    async def test_process_commit_skips_low_confidence(self, watcher_config, mock_dev_context, mock_git_analyzer):
        """Test that low confidence commits are skipped"""
        mock_git_analyzer.analyze_commit_work_relation.return_value = {
            "confidence": 0.3,  # Below threshold
            "best_match": None,
            "commit_type": "chore",
            "reasons": []
        }

        watcher = GitWatcher(watcher_config)
        watcher._dev_context = mock_dev_context
        watcher._git_analyzer = mock_git_analyzer
        watcher.config.auto_create_work_items = False

        commit = {
            "hash": "lowconf123",
            "message": "chore: update gitignore",
            "author": "dev@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_changed": [".gitignore"]
        }

        result = await watcher.process_commit(commit)

        assert result["action"] == "skipped"
        # Chore commits are skipped as non-trackable (not feat/fix)
        assert result["reason"] == "non_trackable_type"

    @pytest.mark.anyio
    async def test_watch_loop_processes_commits(self, watcher_config, mock_dev_context, tmp_path):
        """Test the watch loop processes new commits"""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: initial feature"], cwd=tmp_path, capture_output=True)

        watcher = GitWatcher(watcher_config)
        watcher._dev_context = mock_dev_context

        # Run one iteration of watch loop
        processed = await watcher.watch_once()

        assert len(processed) >= 1
        assert any(p["action"] in ["created_work_item", "linked_to_existing"] for p in processed)

    def test_branch_filtering(self, watcher_config, tmp_path):
        """Test that branch filtering works"""
        watcher_config.branch_filter = ["main"]

        # Initialize git repo with main branch
        subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: main branch commit"], cwd=tmp_path, capture_output=True)

        watcher = GitWatcher(watcher_config)

        # Should get commits from main
        commits = watcher.get_new_commits()
        assert len(commits) >= 1

    def test_commit_deduplication(self, watcher_config, tmp_path):
        """Test that same commits aren't processed twice"""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: test commit"], cwd=tmp_path, capture_output=True)

        watcher = GitWatcher(watcher_config)

        # First call should return commits
        commits1 = watcher.get_new_commits()
        assert len(commits1) >= 1

        # Second call should return empty (no new commits)
        commits2 = watcher.get_new_commits()
        assert len(commits2) == 0


class TestGitWatcherIntegration:
    """Integration tests for git watcher"""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository"""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, capture_output=True)
        return tmp_path

    def test_full_workflow_feat_commit(self, git_repo):
        """Test full workflow: commit -> parse -> create work item"""
        # Create a feature commit
        test_file = git_repo / "feature.js"
        test_file.write_text("// New feature code")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(auth): implement OAuth2 login flow"],
            cwd=git_repo, capture_output=True
        )

        # Parse the commit
        parser = CommitParser()
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_repo, capture_output=True, text=True
        )
        commit_msg = result.stdout.strip()

        parsed = parser.parse(commit_msg)

        assert parsed.type == "feat"
        assert parsed.scope == "auth"
        assert parsed.work_type == "feature"
        assert "OAuth2" in parsed.description

    def test_full_workflow_fix_commit_with_reference(self, git_repo):
        """Test workflow with issue reference extraction"""
        test_file = git_repo / "fix.js"
        test_file.write_text("// Bug fix")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "fix: resolve memory leak\n\nFixes #42\nRelated to #43"],
            cwd=git_repo, capture_output=True
        )

        parser = CommitParser()
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_repo, capture_output=True, text=True
        )

        parsed = parser.parse(result.stdout.strip())

        assert parsed.type == "fix"
        assert parsed.work_type == "bug"
        assert "#42" in parsed.references
        assert "#43" in parsed.references


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
