"""
Test suite for sync_work_to_github MCP tool - STORY-009

Tests the integration of GitHub API client into the MCP server for syncing work items.
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

        mock_server = MagicMock()
        mock_tool = MagicMock()
        mock_stdio_server = MagicMock()

        sys.modules['mcp.server'].Server = mock_server
        sys.modules['mcp.server.stdio'].stdio_server = mock_stdio_server
        sys.modules['mcp.types'].Tool = mock_tool
        sys.modules['mcp.types'].TextContent = MockTextContent
        sys.modules['mcp.types'].CallToolResult = MockCallToolResult

    # Also mock github_client since it's imported with relative imports
    from unittest.mock import MagicMock

    # Create realistic exception classes for mocking
    class MockGitHubAPIError(Exception):
        pass

    class MockGitHubRateLimitError(Exception):
        pass

    # Create the mock module with proper exception types
    github_client_mock = MagicMock()
    github_client_mock.GitHubAPIError = MockGitHubAPIError
    github_client_mock.GitHubRateLimitError = MockGitHubRateLimitError

    # Mock map_work_item_to_github_issue to return proper GitHub issue format
    def mock_map_work_item_to_github_issue(work_item):
        return {
            "title": work_item["title"],
            "body": work_item.get("description", ""),
            "labels": ["feature" if work_item.get("work_type") == "feature" else "bug"],
            "state": "open"
        }

    github_client_mock.map_work_item_to_github_issue = mock_map_work_item_to_github_issue

    sys.modules['github_client'] = github_client_mock

    from mcp_server import handle_sync_work_to_github
except ImportError as e:
    # Expected during TDD Red phase
    pytest.skip(f"sync_work_to_github MCP tool not implemented yet: {e}", allow_module_level=True)


class TestSyncWorkToGitHubTool:
    """Test the sync_work_to_github MCP tool"""

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
        mock_manager.query_work_items.return_value = [
            {
                "uid": "test-project::workitem::abc123",
                "title": "Implement authentication",
                "description": "Add JWT-based auth",
                "status": "open",
                "priority": "high",
                "work_type": "feature",
                "source": "code_analyzer",
                "external_id": None,
                "created_at": "2026-01-15T10:00:00Z",
                "updated_at": "2026-01-15T10:00:00Z"
            },
            {
                "uid": "test-project::workitem::def456",
                "title": "Fix auth bug",
                "description": "JWT token validation fails",
                "status": "in_progress",
                "priority": "high",
                "work_type": "bug",
                "source": "code_analyzer",
                "external_id": "123",  # Already synced
                "created_at": "2026-01-15T11:00:00Z",
                "updated_at": "2026-01-15T11:30:00Z"
            }
        ]
        mock_manager._driver = Mock()

        # Mock update_work_item to return success response (not MagicMock)
        mock_manager.update_work_item.return_value = True

        return mock_manager

    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHubClient for testing"""
        mock_client = Mock()

        # Mock create issue response
        mock_client.create_issue.return_value = {
            "number": 124,
            "html_url": "https://github.com/test/repo/issues/124",
            "state": "open",
            "created_at": "2026-01-15T12:00:00Z"
        }

        # Mock update issue response
        mock_client.update_issue.return_value = {
            "number": 123,
            "html_url": "https://github.com/test/repo/issues/123",
            "state": "open",
            "updated_at": "2026-01-15T12:30:00Z"
        }

        return mock_client

    @pytest.fixture
    def mcp_request_basic(self):
        """Basic MCP request for sync_work_to_github"""
        return {
            "project_name": "test-project",
            "github_repo": "test/repo",
            "create_issues": True,
            "update_existing": False
        }

    @pytest.fixture
    def mcp_request_update_existing(self):
        """MCP request with update_existing=True"""
        return {
            "project_name": "test-project",
            "github_repo": "test/repo",
            "create_issues": True,
            "update_existing": True,
            "close_resolved": True
        }

    @pytest.fixture
    def mcp_request_dry_run(self):
        """MCP request for dry run mode"""
        return {
            "project_name": "test-project",
            "github_repo": "test/repo",
            "dry_run": True
        }

    @pytest.mark.anyio
    async def test_sync_work_to_github_create_new_issues(self, mock_dev_context, mock_github_client, mcp_request_basic):
        """Test creating new GitHub issues from work items"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "sync_results" in response_data["data"]

        # Should create 1 new issue (the one without external_id)
        assert response_data["data"]["issues_created"] == 1
        assert response_data["data"]["issues_updated"] == 0

        # Verify GitHub client was called correctly
        mock_github_client.create_issue.assert_called_once()
        create_call = mock_github_client.create_issue.call_args
        assert "Implement authentication" in create_call[1]["title"]
        assert "feature" in create_call[1]["labels"]

    @pytest.mark.anyio
    async def test_sync_work_to_github_update_existing_issues(self, mock_dev_context, mock_github_client, mcp_request_update_existing):
        """Test updating existing GitHub issues"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(mcp_request_update_existing)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True

        # Should create 1 new issue and update 1 existing
        assert response_data["data"]["issues_created"] == 1
        assert response_data["data"]["issues_updated"] == 1

        # Verify update was called for existing issue
        mock_github_client.update_issue.assert_called_once_with(
            repo="test/repo",
            issue_number=123,
            title="Fix auth bug",
            body="JWT token validation fails",
            state="open",
            labels=["bug", "high-priority"]
        )

    @pytest.mark.anyio
    async def test_sync_work_to_github_dry_run_mode(self, mock_dev_context, mock_github_client, mcp_request_dry_run):
        """Test dry run mode (preview changes without executing)"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(mcp_request_dry_run)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["dry_run"] is True
        assert "preview" in response_data["data"]

        # Should not call GitHub API in dry run
        mock_github_client.create_issue.assert_not_called()
        mock_github_client.update_issue.assert_not_called()

    @pytest.mark.anyio
    async def test_sync_work_to_github_labels_mapping(self, mock_dev_context, mock_github_client, mcp_request_basic):
        """Test that work item types and priorities map to correct GitHub labels"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(mcp_request_basic)

        # Check that labels are mapped correctly
        create_call = mock_github_client.create_issue.call_args
        labels = create_call[1]["labels"]
        assert "feature" in labels  # work_type -> label
        assert "high-priority" in labels  # priority -> label

    @pytest.mark.anyio
    async def test_sync_work_to_github_work_item_update_after_sync(self, mock_dev_context, mock_github_client, mcp_request_basic):
        """Test that work items are updated with external_id after successful sync"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True

        # Verify work item was updated with GitHub issue number
        mock_dev_context.update_work_item.assert_called_once()
        update_call = mock_dev_context.update_work_item.call_args
        assert update_call[0][0] == "test-project::workitem::abc123"  # work_item_uid
        assert update_call[1]["external_id"] == "124"  # GitHub issue number

    @pytest.mark.anyio
    async def test_sync_work_to_github_error_handling_github_api_failure(self, mock_dev_context, mock_github_client, mcp_request_basic):
        """Test error handling when GitHub API fails"""
        mock_github_client.create_issue.side_effect = Exception("GitHub API rate limited")

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "GitHub API rate limited" in response_data["error"]

    @pytest.mark.anyio
    async def test_sync_work_to_github_filter_by_status(self, mock_dev_context, mock_github_client):
        """Test filtering work items by status"""
        # Add work item filter parameter
        request = {
            "project_name": "test-project",
            "github_repo": "test/repo",
            "status_filter": "open,in_progress"
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(request)

        # Verify query was called with status filter
        call_kwargs = mock_dev_context.query_work_items.call_args[1]
        assert "status" in call_kwargs or "status_filter" in call_kwargs

    @pytest.mark.anyio
    async def test_sync_work_to_github_invalid_repo_format(self, mock_dev_context, mock_github_client):
        """Test error handling for invalid GitHub repo format"""
        request = {
            "project_name": "test-project",
            "github_repo": "invalid-repo-format",  # Should be "owner/repo"
            "create_issues": True
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            with patch('core.github_client.GitHubClient', return_value=mock_github_client):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    response = await handle_sync_work_to_github(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "invalid repo format" in response_data["error"].lower()


class TestSyncWorkToGitHubIntegration:
    """Integration tests for sync_work_to_github MCP tool"""

    @pytest.mark.anyio
    async def test_tool_registration(self):
        """Test that sync_work_to_github tool is properly registered in TOOLS list"""
        from mcp_server import TOOLS
        tool_names = [tool.name for tool in TOOLS]
        assert "sync_work_to_github" in tool_names

    @pytest.mark.anyio
    async def test_tool_schema_validation(self):
        """Test that tool schema is properly defined"""
        from mcp_server import TOOLS

        sync_tool = None
        for tool in TOOLS:
            if tool.name == "sync_work_to_github":
                sync_tool = tool
                break

        assert sync_tool is not None
        assert sync_tool.description is not None
        assert "project_name" in sync_tool.inputSchema["properties"]
        assert "github_repo" in sync_tool.inputSchema["properties"]
        assert "create_issues" in sync_tool.inputSchema["properties"]
        assert sync_tool.inputSchema["required"] == ["project_name", "github_repo"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])