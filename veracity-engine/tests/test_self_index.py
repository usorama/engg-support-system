"""
Tests for Self-Indexing Configuration and Automation (STORY-017).

Tests cover:
1. Self-index configuration defaults
2. Repo hash computation for change detection
3. Index result serialization
4. Git hook installation/uninstallation
5. Command generation
"""
import pytest
import os
import tempfile
import json
from pathlib import Path

from core.self_index import (
    SELF_PROJECT_NAME,
    DEFAULT_EXCLUSIONS,
    SelfIndexConfig,
    IndexingResult,
    compute_repo_hash,
    should_reindex,
    save_index_result,
    get_self_index_command,
    install_git_hook,
    uninstall_git_hook,
)


class TestSelfIndexConfig:
    """Tests for SelfIndexConfig dataclass."""

    def test_default_project_name(self):
        """Default project name should be veracity-engine."""
        config = SelfIndexConfig()
        assert config.project_name == SELF_PROJECT_NAME
        assert config.project_name == "veracity-engine"

    def test_default_exclusions(self):
        """Default exclusions should include common patterns."""
        config = SelfIndexConfig()
        assert ".git" in config.exclusions
        assert "__pycache__" in config.exclusions
        assert "node_modules" in config.exclusions

    def test_default_deterministic(self):
        """Deterministic mode should be enabled by default."""
        config = SelfIndexConfig()
        assert config.deterministic is True

    def test_default_verify_after_index(self):
        """Verify after index should be enabled by default."""
        config = SelfIndexConfig()
        assert config.verify_after_index is True

    def test_exclude_tests_by_default(self):
        """Tests should be excluded by default."""
        config = SelfIndexConfig()
        assert config.include_tests is False

    def test_include_docs_by_default(self):
        """Docs should be included by default."""
        config = SelfIndexConfig()
        assert config.include_docs is True

    def test_custom_project_name(self):
        """Custom project name should be accepted."""
        config = SelfIndexConfig(project_name="custom-project")
        assert config.project_name == "custom-project"

    def test_custom_root_dir(self):
        """Custom root directory should be accepted."""
        config = SelfIndexConfig(root_dir="/custom/path")
        assert config.root_dir == "/custom/path"

    def test_to_dict(self):
        """Config should serialize to dictionary."""
        config = SelfIndexConfig(project_name="test")
        result = config.to_dict()
        assert result["project_name"] == "test"
        assert "exclusions" in result
        assert "deterministic" in result


class TestIndexingResult:
    """Tests for IndexingResult dataclass."""

    def test_success_result(self):
        """Successful result should have success=True."""
        result = IndexingResult(
            success=True,
            project_name="test",
            node_count=100,
            edge_count=50,
        )
        assert result.success is True
        assert result.node_count == 100
        assert result.edge_count == 50

    def test_failure_result(self):
        """Failed result should have error message."""
        result = IndexingResult(
            success=False,
            project_name="test",
            error="Connection failed",
        )
        assert result.success is False
        assert result.error == "Connection failed"

    def test_timestamp_auto_generated(self):
        """Timestamp should be auto-generated."""
        result = IndexingResult(success=True, project_name="test")
        assert result.timestamp != ""
        assert "T" in result.timestamp  # ISO format

    def test_to_dict(self):
        """Result should serialize to dictionary."""
        result = IndexingResult(
            success=True,
            project_name="test",
            node_count=100,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["project_name"] == "test"
        assert d["node_count"] == 100


class TestRepoHashComputation:
    """Tests for repository hash computation."""

    def test_compute_repo_hash_stable(self):
        """Hash should be stable for same content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.py").write_text("content1")
            (Path(tmpdir) / "file2.py").write_text("content2")

            hash1 = compute_repo_hash(tmpdir)
            hash2 = compute_repo_hash(tmpdir)

            assert hash1 == hash2

    def test_compute_repo_hash_different_content(self):
        """Hash should change when content changes (mtime changes)."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "file.py"
            file_path.write_text("content1")

            hash1 = compute_repo_hash(tmpdir)

            # Sleep to ensure mtime changes (hash is based on mtime, not content)
            time.sleep(0.1)
            file_path.write_text("content2")

            hash2 = compute_repo_hash(tmpdir)

            assert hash1 != hash2

    def test_compute_repo_hash_respects_exclusions(self):
        """Hash should exclude specified patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files including one to exclude
            (Path(tmpdir) / "file.py").write_text("content")
            cache_dir = Path(tmpdir) / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "cached.pyc").write_text("cached")

            hash_with_exclusion = compute_repo_hash(tmpdir, ["__pycache__"])

            # Add more cached files
            (cache_dir / "another.pyc").write_text("another")

            hash_after = compute_repo_hash(tmpdir, ["__pycache__"])

            # Hash should be same since __pycache__ is excluded
            assert hash_with_exclusion == hash_after

    def test_hash_is_16_characters(self):
        """Hash should be truncated to 16 characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.py").write_text("content")
            hash_val = compute_repo_hash(tmpdir)
            assert len(hash_val) == 16


class TestShouldReindex:
    """Tests for should_reindex function."""

    def test_should_reindex_no_hash_file(self):
        """Should reindex when no hash file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.py").write_text("content")
            assert should_reindex(tmpdir, "test-project") is True

    def test_should_not_reindex_when_unchanged(self):
        """Should not reindex when content unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.py").write_text("content")

            # Save initial result
            result = IndexingResult(
                success=True,
                project_name="test-project",
                content_hash=compute_repo_hash(tmpdir),
            )
            save_index_result(result, tmpdir)

            # Check - should not need reindex
            assert should_reindex(tmpdir, "test-project") is False

    def test_should_reindex_when_changed(self):
        """Should reindex when content changed (mtime changes)."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "file.py"
            file_path.write_text("content1")

            # Save initial result
            result = IndexingResult(
                success=True,
                project_name="test-project",
                content_hash=compute_repo_hash(tmpdir),
            )
            save_index_result(result, tmpdir)

            # Sleep to ensure mtime changes (hash is based on mtime, not content)
            time.sleep(0.1)

            # Change content
            file_path.write_text("content2")

            # Check - should need reindex
            assert should_reindex(tmpdir, "test-project") is True


class TestSaveIndexResult:
    """Tests for save_index_result function."""

    def test_save_creates_file(self):
        """Save should create hash file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = IndexingResult(
                success=True,
                project_name="test-project",
                node_count=100,
            )
            save_index_result(result, tmpdir)

            hash_file = Path(tmpdir) / ".graph_hashes_test-project.json"
            assert hash_file.exists()

    def test_saved_file_is_valid_json(self):
        """Saved file should be valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = IndexingResult(
                success=True,
                project_name="test-project",
                node_count=100,
            )
            save_index_result(result, tmpdir)

            hash_file = Path(tmpdir) / ".graph_hashes_test-project.json"
            with open(hash_file, "r") as f:
                data = json.load(f)

            assert data["success"] is True
            assert data["project_name"] == "test-project"
            assert data["node_count"] == 100


class TestGetSelfIndexCommand:
    """Tests for get_self_index_command function."""

    def test_default_command(self):
        """Default command should use veracity-engine project name."""
        cmd = get_self_index_command()
        assert "python3" in cmd
        assert "build_graph.py" in cmd[1]
        assert "--project-name" in cmd
        assert "veracity-engine" in cmd

    def test_custom_config_command(self):
        """Command should respect custom config."""
        config = SelfIndexConfig(
            project_name="custom-project",
            root_dir="/custom/path",
        )
        cmd = get_self_index_command(config)
        assert "custom-project" in cmd
        assert "/custom/path" in cmd


class TestGitHookInstallation:
    """Tests for git hook installation."""

    def test_install_hook_creates_file(self):
        """Install should create hook file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory structure
            scripts_dir = Path(tmpdir) / "scripts" / "hooks"
            scripts_dir.mkdir(parents=True)
            git_hooks_dir = Path(tmpdir) / ".git" / "hooks"
            git_hooks_dir.mkdir(parents=True)

            # Create source hook
            hook_source = scripts_dir / "post-commit"
            hook_source.write_text("#!/bin/bash\necho 'hook'")

            # Install
            result = install_git_hook(tmpdir)

            # Check
            hook_dest = git_hooks_dir / "post-commit"
            assert result is True
            assert hook_dest.exists()

    def test_uninstall_hook_removes_file(self):
        """Uninstall should remove hook file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create hook file
            git_hooks_dir = Path(tmpdir) / ".git" / "hooks"
            git_hooks_dir.mkdir(parents=True)
            hook_file = git_hooks_dir / "post-commit"
            hook_file.write_text("#!/bin/bash\necho 'hook'")

            # Uninstall
            result = uninstall_git_hook(tmpdir)

            # Check
            assert result is True
            assert not hook_file.exists()

    def test_uninstall_nonexistent_succeeds(self):
        """Uninstall should succeed if hook doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_hooks_dir = Path(tmpdir) / ".git" / "hooks"
            git_hooks_dir.mkdir(parents=True)

            result = uninstall_git_hook(tmpdir)
            assert result is True


class TestDefaultExclusions:
    """Tests for default exclusion patterns."""

    def test_git_excluded(self):
        """Git directory should be excluded."""
        assert ".git" in DEFAULT_EXCLUSIONS

    def test_pycache_excluded(self):
        """Python cache should be excluded."""
        assert "__pycache__" in DEFAULT_EXCLUSIONS

    def test_node_modules_excluded(self):
        """Node modules should be excluded."""
        assert "node_modules" in DEFAULT_EXCLUSIONS

    def test_env_files_excluded(self):
        """Environment files should be excluded."""
        assert ".env*" in DEFAULT_EXCLUSIONS

    def test_coverage_excluded(self):
        """Coverage reports should be excluded."""
        assert "coverage_report" in DEFAULT_EXCLUSIONS


class TestProjectNameConstant:
    """Tests for project name constant."""

    def test_canonical_name(self):
        """Canonical project name should be veracity-engine."""
        assert SELF_PROJECT_NAME == "veracity-engine"

    def test_name_is_lowercase(self):
        """Project name should be lowercase."""
        assert SELF_PROJECT_NAME == SELF_PROJECT_NAME.lower()

    def test_name_is_slug_format(self):
        """Project name should be slug format."""
        import re
        assert re.match(r'^[a-z0-9-]+$', SELF_PROJECT_NAME)
