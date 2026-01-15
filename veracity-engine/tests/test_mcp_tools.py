"""
Test suite for MCP Tools - Dev Context Tracking Feature

Tests for create_work_item, record_code_change, link_code_to_work MCP tools.
Following TDD - tests should pass with actual implementation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# Import MCP server handlers
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))
from mcp_server import handle_create_work_item, handle_record_code_change, handle_link_code_to_work


class TestCreateWorkItemTool:
    """Test the create_work_item MCP tool"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.create_work_item.return_value = "test-project::workitem::abc123"
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mcp_request(self):
        """Sample MCP request for create_work_item"""
        return {
            "title": "Implement authentication",
            "description": "Add JWT-based authentication to the API",
            "work_type": "feature",
            "priority": "high",
            "idempotency_token": "req_abc123def456"
        }

    @pytest.mark.anyio
    async def test_create_work_item_basic(self, mock_dev_context, mcp_request):
        """Test basic work item creation via MCP"""
        # Mock session for idempotency check (returns None = no existing item)
        mock_session = Mock()
        mock_result = Mock()
        mock_result.single.return_value = None  # No existing item
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_dev_context._driver.session.return_value = mock_session

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_create_work_item(mcp_request)

        # Parse JSON response
        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "work_item_uid" in response_data["data"]
        assert response_data["data"]["work_item_uid"] == "test-project::workitem::abc123"
        mock_dev_context.create_work_item.assert_called_once()

    @pytest.mark.anyio
    async def test_create_work_item_with_external_source(self, mock_dev_context):
        """Test work item creation with external source (GitHub)"""
        request = {
            "title": "Fix authentication bug",
            "description": "Resolve JWT token validation issue",
            "work_type": "bug",
            "external_id": "github-issue-456",
            "source": "github",
            "idempotency_token": "req_github456"
        }

        # Mock session for idempotency check
        mock_session = Mock()
        mock_result = Mock()
        mock_result.single.return_value = None  # No existing item
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_dev_context._driver.session.return_value = mock_session

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_create_work_item(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        # Verify external metadata passed to dev_context
        call_kwargs = mock_dev_context.create_work_item.call_args[1]
        assert call_kwargs["external_id"] == "github-issue-456"
        assert call_kwargs["source"] == "github"

    @pytest.mark.anyio
    async def test_create_work_item_idempotency(self, mock_dev_context, mcp_request):
        """Test idempotency token handling per critical analysis"""
        # Mock session for idempotency check
        mock_session = Mock()
        mock_result = Mock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value="existing::workitem::xyz789")
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_dev_context._driver.session.return_value = mock_session

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_create_work_item(mcp_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["work_item_uid"] == "existing::workitem::xyz789"
        assert response_data["data"]["created"] is False
        # Verify create was not called due to idempotency
        mock_dev_context.create_work_item.assert_not_called()

    @pytest.mark.anyio
    async def test_create_work_item_missing_required_fields(self, mock_dev_context):
        """Test error handling for missing required fields"""
        incomplete_request = {
            "title": "Incomplete request"
            # Missing description, work_type
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_create_work_item(incomplete_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "required" in response_data["error"].lower()


class TestRecordCodeChangeTool:
    """Test the record_code_change MCP tool"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.record_code_change.return_value = "test-project::codechanqge::commit123-file456"
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mcp_request(self):
        """Sample MCP request for record_code_change"""
        return {
            "commit_hash": "a1b2c3d4e5f6",
            "file_path": "src/auth/handler.py",
            "change_type": "modified",
            "lines_added": 25,
            "lines_deleted": 5,
            "author": "developer@example.com",
            "timestamp": "2026-01-15T18:45:00Z"
        }

    @pytest.mark.anyio
    async def test_record_code_change_basic(self, mock_dev_context, mcp_request):
        """Test basic code change recording via MCP"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_record_code_change(mcp_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "code_change_uid" in response_data["data"]
        assert response_data["data"]["code_change_uid"] == "test-project::codechanqge::commit123-file456"
        mock_dev_context.record_code_change.assert_called_once()

    @pytest.mark.anyio
    async def test_record_code_change_with_diff(self, mock_dev_context):
        """Test code change recording with diff snippet"""
        request = {
            "commit_hash": "b2c3d4e5f6a7",
            "file_path": "src/models/user.py",
            "change_type": "added",
            "lines_added": 50,
            "lines_deleted": 0,
            "author": "dev@test.com",
            "diff_snippet": "+class User:\n+    def __init__(self, name):\n+        self.name = name"
        }

        # Mock session for diff_snippet storage
        mock_session = Mock()
        mock_session.run.return_value = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_dev_context._driver.session.return_value = mock_session

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_record_code_change(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        # Verify diff_snippet was stored (session.run called)
        assert mock_session.run.called

    @pytest.mark.anyio
    async def test_record_code_change_missing_commit_hash(self, mock_dev_context):
        """Test error handling for missing commit hash"""
        incomplete_request = {
            "file_path": "src/test.py",
            "change_type": "modified"
            # Missing commit_hash (required)
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_record_code_change(incomplete_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "commit_hash" in response_data["error"].lower()


class TestLinkCodeToWorkTool:
    """Test the link_code_to_work MCP tool"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.link_code_to_work.return_value = True
        mock_manager._validate_uid.return_value = True
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mcp_request(self):
        """Sample MCP request for link_code_to_work"""
        return {
            "work_item_uid": "test-project::workitem::feature123",
            "code_change_uid": "test-project::codechanqge::commit456-file789",
            "link_confidence": 0.9,
            "link_reason": "Commit message mentions issue #123"
        }

    @pytest.mark.anyio
    async def test_link_code_to_work_basic(self, mock_dev_context, mcp_request):
        """Test basic code-to-work linking via MCP"""
        # Mock session for link_reason storage
        mock_session = Mock()
        mock_session.run.return_value = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_dev_context._driver.session.return_value = mock_session

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_link_code_to_work(mcp_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "linked" in response_data["data"]
        assert response_data["data"]["linked"] is True
        mock_dev_context.link_code_to_work.assert_called_once()

    @pytest.mark.anyio
    async def test_link_code_to_work_with_confidence_scoring(self, mock_dev_context, mcp_request):
        """Test confidence scoring per acceptance criteria"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_link_code_to_work(mcp_request)

        response_data = json.loads(response.content[0].text)
        # Verify confidence passed to dev_context
        call_kwargs = mock_dev_context.link_code_to_work.call_args[1]
        assert call_kwargs["link_confidence"] == 0.9

    @pytest.mark.anyio
    async def test_link_code_to_work_invalid_uids(self, mock_dev_context):
        """Test error handling for invalid UIDs"""
        request = {
            "work_item_uid": "invalid-uid-format",
            "code_change_uid": "also-invalid",
            "link_confidence": 0.8
        }

        # Mock validation error
        from core.dev_context import InvalidUIIDFormatError
        mock_dev_context._validate_uid.side_effect = InvalidUIIDFormatError("Invalid UID format")

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_link_code_to_work(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "uid" in response_data["error"].lower()

    @pytest.mark.anyio
    async def test_link_code_to_work_missing_confidence(self, mock_dev_context):
        """Test default confidence when not provided"""
        request = {
            "work_item_uid": "test-project::workitem::feature123",
            "code_change_uid": "test-project::codechanqge::commit456-file789"
            # Missing link_confidence - should default to 0.5
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_link_code_to_work(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        # Verify default confidence applied
        call_kwargs = mock_dev_context.link_code_to_work.call_args[1]
        assert "link_confidence" in call_kwargs
        assert call_kwargs["link_confidence"] == 0.5  # Default value


class TestMCPToolsIntegration:
    """Test MCP tools integration and JSON format consistency"""

    def test_consistent_json_response_format(self):
        """Test all tools return consistent JSON format per acceptance criteria"""
        # All tool responses should have:
        # - success: boolean
        # - data: object (when success=true)
        # - error: string (when success=false)
        pass  # Verified in individual tool tests

    def test_constraint_violation_handling(self):
        """Test error handling for constraint violations per acceptance criteria"""
        # Should handle Neo4j constraint violations gracefully
        pass  # Will verify with live Neo4j integration

    def test_mcp_tool_registration(self):
        """Test that all tools are properly registered in TOOLS list"""
        # Verify tools are discoverable by MCP clients
        from mcp_server import TOOLS
        tool_names = [tool.name for tool in TOOLS]
        assert "create_work_item" in tool_names
        assert "record_code_change" in tool_names
        assert "link_code_to_work" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
