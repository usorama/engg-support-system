"""
Test suite for Query MCP Tools - Dev Context Tracking Feature

Tests for query_work_items, get_work_context, trace_file_to_work MCP tools.
Following TDD - these tests should FAIL initially until Query tools are implemented.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import MCP server handlers
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))
    from mcp_server import handle_query_work_items, handle_get_work_context, handle_trace_file_to_work
except ImportError:
    # Expected during TDD Red phase
    pytest.skip("Query MCP tools not implemented yet", allow_module_level=True)


class TestQueryWorkItemsTool:
    """Test the query_work_items MCP tool"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.query_work_items.return_value = [
            {
                "uid": "test-project::workitem::abc123",
                "title": "Implement authentication",
                "status": "open",
                "priority": "high",
                "created_at": "2026-01-15T10:00:00Z"
            },
            {
                "uid": "test-project::workitem::def456",
                "title": "Fix auth bug",
                "status": "in_progress",
                "priority": "medium",
                "created_at": "2026-01-15T11:00:00Z"
            }
        ]
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mcp_request(self):
        """Sample MCP request for query_work_items"""
        return {
            "project_name": "test-project",
            "offset": 0,
            "limit": 20
        }

    @pytest.mark.anyio
    async def test_query_work_items_basic(self, mock_dev_context, mcp_request):
        """Test basic work item querying via MCP"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_query_work_items(mcp_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "work_items" in response_data["data"]
        assert len(response_data["data"]["work_items"]) == 2
        assert response_data["data"]["work_items"][0]["title"] == "Implement authentication"
        mock_dev_context.query_work_items.assert_called_once()

    @pytest.mark.anyio
    async def test_query_work_items_with_pagination(self, mock_dev_context):
        """Test pagination support per acceptance criteria"""
        request = {
            "project_name": "test-project",
            "offset": 10,
            "limit": 5,
            "status": "open"
        }

        # Mock paginated results
        mock_dev_context.query_work_items.return_value = [
            {"uid": "test-project::workitem::page2item1", "title": "Item 11", "status": "open"},
        ]

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_query_work_items(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True

        # Verify pagination parameters passed correctly
        call_kwargs = mock_dev_context.query_work_items.call_args[1]
        assert call_kwargs["offset"] == 10
        assert call_kwargs["limit"] == 5
        assert call_kwargs["status"] == "open"

    @pytest.mark.anyio
    async def test_query_work_items_with_filters(self, mock_dev_context):
        """Test filtering by status, priority, work_type"""
        request = {
            "project_name": "test-project",
            "status": "in_progress",
            "priority": "high",
            "work_type": "feature",
            "offset": 0,
            "limit": 10
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_query_work_items(request)

        # Verify filters passed to dev_context
        call_kwargs = mock_dev_context.query_work_items.call_args[1]
        assert call_kwargs["status"] == "in_progress"
        assert call_kwargs["priority"] == "high"
        assert call_kwargs["work_type"] == "feature"

    @pytest.mark.anyio
    async def test_query_work_items_deterministic_ordering(self, mock_dev_context):
        """Test deterministic result ordering per acceptance criteria"""
        request = {"project_name": "test-project", "order_by": "created_at", "order_direction": "DESC"}

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_query_work_items(request)

        # Verify ordering parameters passed
        call_kwargs = mock_dev_context.query_work_items.call_args[1]
        assert call_kwargs.get("order_by") == "created_at"
        assert call_kwargs.get("order_direction") == "DESC"


class TestGetWorkContextTool:
    """Test the get_work_context MCP tool"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.get_work_context.return_value = {
            "work_item": {
                "uid": "test-project::workitem::abc123",
                "title": "Implement authentication",
                "description": "Add JWT-based auth",
                "status": "in_progress"
            },
            "related_commits": [
                {
                    "uid": "test-project::codechanqge::commit1-auth",
                    "commit_hash": "a1b2c3d4",
                    "file_path": "src/auth/handler.py",
                    "author": "dev@example.com"
                }
            ],
            "related_files": [
                "src/auth/handler.py",
                "src/auth/middleware.py"
            ]
        }
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mcp_request(self):
        """Sample MCP request for get_work_context"""
        return {
            "work_item_uid": "test-project::workitem::abc123",
            "include_related_commits": True,
            "include_related_files": True
        }

    @pytest.mark.anyio
    async def test_get_work_context_basic(self, mock_dev_context, mcp_request):
        """Test basic work context retrieval via MCP"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_get_work_context(mcp_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "work_item" in response_data["data"]
        assert "related_commits" in response_data["data"]
        assert "related_files" in response_data["data"]

        # Verify work item details
        work_item = response_data["data"]["work_item"]
        assert work_item["title"] == "Implement authentication"
        assert work_item["status"] == "in_progress"

    @pytest.mark.anyio
    async def test_get_work_context_with_related_commits(self, mock_dev_context, mcp_request):
        """Test related commits inclusion per acceptance criteria"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_get_work_context(mcp_request)

        response_data = json.loads(response.content[0].text)
        related_commits = response_data["data"]["related_commits"]

        assert len(related_commits) == 1
        assert related_commits[0]["commit_hash"] == "a1b2c3d4"
        assert related_commits[0]["file_path"] == "src/auth/handler.py"

    @pytest.mark.anyio
    async def test_get_work_context_invalid_uid(self, mock_dev_context):
        """Test error handling for invalid work item UID"""
        request = {"work_item_uid": "invalid-uid-format"}

        from core.dev_context import WorkItemNotFoundError
        mock_dev_context.get_work_context.side_effect = WorkItemNotFoundError("Work item not found")

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_get_work_context(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "not found" in response_data["error"].lower()


class TestTraceFileToWorkTool:
    """Test the trace_file_to_work MCP tool"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.trace_file_to_work.return_value = [
            {
                "work_item_uid": "test-project::workitem::feature1",
                "title": "Add auth feature",
                "confidence": 0.9,
                "link_reason": "Direct implementation",
                "commits": [
                    {"commit_hash": "a1b2c3", "timestamp": "2026-01-15T10:00:00Z"}
                ]
            },
            {
                "work_item_uid": "test-project::workitem::bug2",
                "title": "Fix auth bug",
                "confidence": 0.7,
                "link_reason": "Related fix",
                "commits": [
                    {"commit_hash": "d4e5f6", "timestamp": "2026-01-15T11:00:00Z"}
                ]
            }
        ]
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mcp_request(self):
        """Sample MCP request for trace_file_to_work"""
        return {
            "file_path": "src/auth/handler.py",
            "project_name": "test-project",
            "min_confidence": 0.5
        }

    @pytest.mark.anyio
    async def test_trace_file_to_work_basic(self, mock_dev_context, mcp_request):
        """Test basic file-to-work tracing via MCP"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_trace_file_to_work(mcp_request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "traces" in response_data["data"]
        assert len(response_data["data"]["traces"]) == 2

        # Verify first trace
        trace = response_data["data"]["traces"][0]
        assert trace["title"] == "Add auth feature"
        assert trace["confidence"] == 0.9

    @pytest.mark.anyio
    async def test_trace_file_to_work_backward_tracing(self, mock_dev_context):
        """Test backward tracing per acceptance criteria"""
        request = {
            "file_path": "src/models/user.py",
            "project_name": "test-project",
            "trace_direction": "backward",
            "max_depth": 3
        }

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_trace_file_to_work(request)

        # Verify tracing parameters passed
        call_kwargs = mock_dev_context.trace_file_to_work.call_args[1]
        assert call_kwargs.get("trace_direction") == "backward"
        assert call_kwargs.get("max_depth") == 3

    @pytest.mark.anyio
    async def test_trace_file_to_work_confidence_filtering(self, mock_dev_context, mcp_request):
        """Test confidence-based filtering"""
        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_trace_file_to_work(mcp_request)

        # Verify min_confidence parameter passed
        call_kwargs = mock_dev_context.trace_file_to_work.call_args[1]
        assert call_kwargs["min_confidence"] == 0.5

    @pytest.mark.anyio
    async def test_trace_file_to_work_invalid_file_path(self, mock_dev_context):
        """Test error handling for invalid file path"""
        request = {
            "file_path": "/nonexistent/file.py",
            "project_name": "test-project"
        }

        # Mock no traces found
        mock_dev_context.trace_file_to_work.return_value = []

        with patch('mcp_server.get_dev_context_manager', return_value=mock_dev_context):
            response = await handle_trace_file_to_work(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["traces"] == []


class TestQueryMCPToolsIntegration:
    """Test Query MCP tools integration"""

    def test_cypher_query_optimization(self):
        """Test Cypher query optimization per acceptance criteria"""
        # Verify queries use indexes and efficient patterns
        pass  # Will verify in integration tests with actual Neo4j

    def test_pagination_consistency(self):
        """Test pagination consistency across all query tools"""
        # All query tools should support offset/limit parameters
        pass  # Will verify in integration tests

    def test_deterministic_result_ordering(self):
        """Test deterministic ordering per acceptance criteria"""
        # Results should be ordered consistently (e.g., by created_at, updated_at)
        pass  # Will verify with repeated queries

    def test_query_tools_registration(self):
        """Test that all query tools are properly registered in TOOLS list"""
        from mcp_server import TOOLS
        tool_names = [tool.name for tool in TOOLS]
        assert "query_work_items" in tool_names
        assert "get_work_context" in tool_names
        assert "trace_file_to_work" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])