"""
Test suite for auto_link_orphan_commits MCP tool - STORY-010

Tests the automatic linking of orphaned Git commits to existing work items.
Following TDD - this test should FAIL initially until the tool is implemented.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import MCP server handler
try:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../core')))

    # Mock MCP dependencies if they're not available (for TDD in Python 3.9 environment)
    import importlib.util
    if importlib.util.find_spec("mcp") is None:
        from unittest.mock import MagicMock

        # Mock all MCP modules and submodules
        sys.modules['mcp'] = MagicMock()
        sys.modules['mcp.server'] = MagicMock()
        sys.modules['mcp.server.stdio'] = MagicMock()
        sys.modules['mcp.types'] = MagicMock()

        # Create mock classes that the mcp_server module expects
        class MockTextContent:
            def __init__(self, type="text", text=""):
                self.type = type
                self.text = text

        class MockCallToolResult:
            def __init__(self, content=None, isError=False):
                self.content = content or []
                self.isError = isError

        class MockTool:
            def __init__(self, name=None, description=None, inputSchema=None):
                self.name = name
                self.description = description
                self.inputSchema = inputSchema

        mock_server = MagicMock()
        mock_stdio_server = MagicMock()

        sys.modules['mcp.server'].Server = mock_server
        sys.modules['mcp.server.stdio'].stdio_server = mock_stdio_server
        sys.modules['mcp.types'].Tool = MockTool
        sys.modules['mcp.types'].TextContent = MockTextContent
        sys.modules['mcp.types'].CallToolResult = MockCallToolResult

    # Also mock github_client and git_analyzer since they might be imported
    from unittest.mock import MagicMock

    # Create realistic exception classes for mocking
    class MockGitAnalysisError(Exception):
        pass

    # Create the mock modules
    github_client_mock = MagicMock()
    git_analyzer_mock = MagicMock()
    git_analyzer_mock.GitAnalysisError = MockGitAnalysisError

    sys.modules['github_client'] = github_client_mock
    sys.modules['git_analyzer'] = git_analyzer_mock

    from mcp_server import handle_auto_link_orphan_commits
except ImportError as e:
    # Expected during TDD Red phase
    pytest.skip(f"auto_link_orphan_commits MCP tool not implemented yet: {e}", allow_module_level=True)


class TestAutoLinkOrphanCommitsTool:
    """Test the auto_link_orphan_commits MCP tool"""

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = Mock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        config.github.token.get_secret_value.return_value = "ghp_test_token"
        return config

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()

        # Mock work items for matching
        mock_manager.query_work_items.return_value = [
            {
                "uid": "test-project::workitem::abc123",
                "title": "Implement authentication",
                "description": "Add JWT-based auth",
                "status": "in_progress",
                "priority": "high",
                "work_type": "feature",
                "source": "manual",
                "created_at": "2026-01-15T10:00:00Z",
                "updated_at": "2026-01-15T10:00:00Z"
            },
            {
                "uid": "test-project::workitem::def456",
                "title": "Fix memory leak in parser",
                "description": "Parser doesn't release memory properly",
                "status": "open",
                "priority": "high",
                "work_type": "bug",
                "source": "code_analyzer",
                "created_at": "2026-01-15T11:00:00Z",
                "updated_at": "2026-01-15T11:00:00Z"
            }
        ]

        # Mock orphan commits query with smart parameter handling
        all_commits = [
            {
                "commit_hash": "a1b2c3d4e5f6",
                "message": "feat: add JWT authentication middleware",
                "author": "dev@example.com",
                "timestamp": "2026-01-15T14:00:00Z",
                "files_changed": ["src/middleware/auth.js", "src/utils/jwt.js"],
                "lines_added": 45,
                "lines_deleted": 2
            },
            {
                "commit_hash": "f6e5d4c3b2a1",
                "message": "fix: resolve parser memory leak in tokenizer",
                "author": "dev@example.com",
                "timestamp": "2026-01-15T15:00:00Z",
                "files_changed": ["src/parser/tokenizer.py", "tests/parser_test.py"],
                "lines_added": 12,
                "lines_deleted": 8
            },
            {
                "commit_hash": "9876543210ab",
                "message": "chore: update dependencies and cleanup",
                "author": "dev@example.com",
                "timestamp": "2026-01-15T16:00:00Z",
                "files_changed": ["package.json", "package-lock.json", "README.md"],
                "lines_added": 3,
                "lines_deleted": 1
            }
        ]

        def mock_get_orphan_commits(max_count=100, age_days=30):
            # Return commits limited by max_count parameter
            return all_commits[:max_count]

        mock_manager.get_orphan_commits.side_effect = mock_get_orphan_commits

        mock_manager.link_code_to_work.return_value = True
        mock_manager._driver = Mock()

        return mock_manager

    @pytest.fixture
    def mock_git_analyzer(self):
        """Mock GitAnalyzer for commit analysis"""
        mock_analyzer = Mock()

        # Mock analysis results for different commit types
        def mock_analysis(commit, work_items):
            results = {
                "a1b2c3d4e5f6": {  # auth commit
                    "best_match": "test-project::workitem::abc123",
                    "confidence": 0.85,
                    "reasons": ["keyword_match: authentication", "file_pattern_match: auth middleware"],
                    "commit_type": "feature",
                    "semantic_similarity": 0.82
                },
                "f6e5d4c3b2a1": {  # parser commit
                    "best_match": "test-project::workitem::def456",
                    "confidence": 0.92,
                    "reasons": ["keyword_match: parser memory leak", "file_pattern_match: parser/tokenizer"],
                    "commit_type": "bugfix",
                    "semantic_similarity": 0.89
                },
                "9876543210ab": {  # maintenance commit
                    "best_match": None,
                    "confidence": 0.15,
                    "reasons": ["generic_maintenance"],
                    "commit_type": "chore",
                    "semantic_similarity": 0.12
                }
            }
            return results.get(commit["commit_hash"], {
                "best_match": None,
                "confidence": 0.0,
                "reasons": ["no_match"],
                "commit_type": "unknown",
                "semantic_similarity": 0.0
            })

        mock_analyzer.analyze_commit_work_relation.side_effect = mock_analysis

        return mock_analyzer

    @pytest.fixture
    def mcp_request_basic(self):
        """Basic MCP request for auto_link_orphan_commits"""
        return {
            "project_name": "test-project",
            "min_confidence": 0.7,
            "dry_run": False
        }

    @pytest.fixture
    def mcp_request_dry_run(self):
        """MCP request for dry run mode"""
        return {
            "project_name": "test-project",
            "min_confidence": 0.8,
            "dry_run": True
        }

    @pytest.fixture
    def mcp_request_high_confidence(self):
        """MCP request with high confidence threshold"""
        return {
            "project_name": "test-project",
            "min_confidence": 0.9,
            "max_commits": 50,
            "commit_age_days": 30
        }

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_basic_linking(self, mock_dev_context, mock_git_analyzer, mcp_request_basic):
        """Test basic orphan commit linking with moderate confidence threshold"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "link_results" in response_data["data"]

        # Should link 2 commits (confidence >= 0.7: auth=0.85, parser=0.92)
        assert response_data["data"]["commits_analyzed"] == 3
        assert response_data["data"]["links_created"] == 2
        assert response_data["data"]["links_skipped"] == 1

        # Verify specific links were created
        links = response_data["data"]["link_results"]
        auth_link = next(l for l in links if l["commit_hash"] == "a1b2c3d4e5f6")
        assert auth_link["work_item_uid"] == "test-project::workitem::abc123"
        assert auth_link["confidence"] == 0.85
        assert auth_link["action"] == "linked"

        parser_link = next(l for l in links if l["commit_hash"] == "f6e5d4c3b2a1")
        assert parser_link["work_item_uid"] == "test-project::workitem::def456"
        assert parser_link["confidence"] == 0.92
        assert parser_link["action"] == "linked"

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_dry_run_mode(self, mock_dev_context, mock_git_analyzer, mcp_request_dry_run):
        """Test dry run mode (preview links without creating them)"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_dry_run)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["dry_run"] is True
        assert "preview" in response_data["data"]

        # Should preview 2 links (confidence >= 0.8: auth=0.85, parser=0.92)
        assert response_data["data"]["commits_analyzed"] == 3
        assert response_data["data"]["potential_links"] == 2

        # Should not call link_code_to_work in dry run
        mock_dev_context.link_code_to_work.assert_not_called()

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_high_confidence_threshold(self, mock_dev_context, mock_git_analyzer, mcp_request_high_confidence):
        """Test with high confidence threshold filtering"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_high_confidence)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True

        # Should link 1 commit (confidence >= 0.9: only parser=0.92)
        assert response_data["data"]["commits_analyzed"] == 3
        assert response_data["data"]["links_created"] == 1
        assert response_data["data"]["links_skipped"] == 2

        # Verify only high-confidence link was created
        links = response_data["data"]["link_results"]
        created_links = [l for l in links if l["action"] == "linked"]
        assert len(created_links) == 1
        assert created_links[0]["commit_hash"] == "f6e5d4c3b2a1"
        assert created_links[0]["confidence"] == 0.92

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_semantic_analysis(self, mock_dev_context, mock_git_analyzer, mcp_request_basic):
        """Test that commit analysis considers semantic similarity and file patterns"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        links = response_data["data"]["link_results"]

        # Verify analysis reasons are captured
        auth_link = next(l for l in links if l["commit_hash"] == "a1b2c3d4e5f6")
        assert "keyword_match: authentication" in auth_link["reasons"]
        assert "file_pattern_match: auth middleware" in auth_link["reasons"]

        parser_link = next(l for l in links if l["commit_hash"] == "f6e5d4c3b2a1")
        assert "keyword_match: parser memory leak" in parser_link["reasons"]
        assert "file_pattern_match: parser/tokenizer" in parser_link["reasons"]

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_commit_type_detection(self, mock_dev_context, mock_git_analyzer, mcp_request_basic):
        """Test that commit types are correctly detected from conventional commit format"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        links = response_data["data"]["link_results"]

        # Verify commit types were detected
        auth_link = next(l for l in links if l["commit_hash"] == "a1b2c3d4e5f6")
        assert auth_link["commit_type"] == "feature"

        parser_link = next(l for l in links if l["commit_hash"] == "f6e5d4c3b2a1")
        assert parser_link["commit_type"] == "bugfix"

        chore_link = next(l for l in links if l["commit_hash"] == "9876543210ab")
        assert chore_link["commit_type"] == "chore"

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_no_orphan_commits(self, mock_dev_context, mock_git_analyzer, mcp_request_basic):
        """Test handling when no orphan commits exist"""
        # Mock no orphan commits - clear side_effect first
        mock_dev_context.get_orphan_commits.side_effect = None
        mock_dev_context.get_orphan_commits.return_value = []

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["commits_analyzed"] == 0
        assert response_data["data"]["links_created"] == 0
        assert response_data["data"]["message"] == "No orphan commits found"

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_no_matching_work_items(self, mock_dev_context, mock_git_analyzer, mcp_request_basic):
        """Test handling when no work items match the commits"""
        # Mock no work items
        mock_dev_context.query_work_items.return_value = []

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["commits_analyzed"] == 3
        assert response_data["data"]["links_created"] == 0
        assert response_data["data"]["message"] == "No matching work items found for any commits"

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_git_analysis_error(self, mock_dev_context, mock_git_analyzer, mcp_request_basic):
        """Test error handling when Git analysis fails"""
        mock_git_analyzer.analyze_commit_work_relation.side_effect = Exception("Git repository not found")

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True  # Overall operation succeeds
        assert response_data["data"]["links_created"] == 0  # But no links created
        assert response_data["data"]["links_skipped"] == 3  # All commits skipped due to errors

        # Check that individual commit errors are recorded
        link_results = response_data["data"]["link_results"]
        assert all(result["action"] == "failed" for result in link_results)
        assert all("Git repository not found" in result["error"] for result in link_results)

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_invalid_project(self):
        """Test error handling for invalid project name"""
        request = {
            "project_name": "nonexistent-project",
            "min_confidence": 0.7
        }

        with patch('mcp_server.get_dev_context_manager', side_effect=KeyError("Project not found")):
            response = await handle_auto_link_orphan_commits(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "not found" in response_data["error"].lower()

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_commit_age_filtering(self, mock_dev_context, mock_git_analyzer):
        """Test filtering commits by age"""
        request = {
            "project_name": "test-project",
            "commit_age_days": 7,  # Only commits from last 7 days
            "min_confidence": 0.7
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(request)

        # Verify get_orphan_commits was called with age filter
        call_kwargs = mock_dev_context.get_orphan_commits.call_args[1]
        assert "age_days" in call_kwargs or "since_date" in call_kwargs

    @pytest.mark.anyio
    async def test_auto_link_orphan_commits_max_commits_limit(self, mock_dev_context, mock_git_analyzer):
        """Test limiting the maximum number of commits to process"""
        request = {
            "project_name": "test-project",
            "max_commits": 2,  # Process only 2 commits
            "min_confidence": 0.7
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('git_analyzer.GitAnalyzer', return_value=mock_git_analyzer):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_auto_link_orphan_commits(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["data"]["commits_analyzed"] <= 2


class TestAutoLinkOrphanCommitsIntegration:
    """Integration tests for auto_link_orphan_commits MCP tool"""

    @pytest.mark.anyio
    async def test_tool_registration(self):
        """Test that auto_link_orphan_commits tool is properly registered in TOOLS list"""
        from mcp_server import TOOLS
        tool_names = [tool.name for tool in TOOLS]
        assert "auto_link_orphan_commits" in tool_names

    @pytest.mark.anyio
    async def test_tool_schema_validation(self):
        """Test that tool schema is properly defined"""
        from mcp_server import TOOLS

        link_tool = None
        for tool in TOOLS:
            if tool.name == "auto_link_orphan_commits":
                link_tool = tool
                break

        assert link_tool is not None
        assert link_tool.description is not None
        assert "project_name" in link_tool.inputSchema["properties"]
        assert "min_confidence" in link_tool.inputSchema["properties"]
        assert "dry_run" in link_tool.inputSchema["properties"]
        assert link_tool.inputSchema["required"] == ["project_name"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])