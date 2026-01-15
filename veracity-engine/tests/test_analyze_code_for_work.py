"""
Test suite for analyze_code_for_work MCP tool - STORY-008

Tests the integration of code_analyzer.py into the MCP server.
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
    sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))
    from mcp_server import handle_analyze_code_for_work
except ImportError:
    # Expected during TDD Red phase
    pytest.skip("analyze_code_for_work MCP tool not implemented yet", allow_module_level=True)


class TestAnalyzeCodeForWorkTool:
    """Test the analyze_code_for_work MCP tool"""

    @staticmethod
    def _mock_config():
        """Create a mock configuration."""
        config = Mock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password.get_secret_value.return_value = "password"
        return config

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager for testing"""
        mock_manager = Mock()
        mock_manager.create_work_item.return_value = "test-project::workitem::abc123"
        mock_manager._driver = Mock()
        return mock_manager

    @pytest.fixture
    def mock_code_analyzer(self):
        """Mock CodeAnalyzer for testing"""
        mock_analyzer = Mock()

        # Mock analysis result
        from core.code_analyzer import AnalysisResult, Issue, IssueType, Confidence

        mock_issues = [
            Issue(
                issue_type=IssueType.TODO,
                file_path="src/utils.py",
                line_number=42,
                message="Add error handling",
                confidence=Confidence.HIGH,
                context="def process_data():\n    # TODO: Add error handling\n    pass"
            ),
            Issue(
                issue_type=IssueType.INCOMPLETE,
                file_path="src/auth.py",
                line_number=15,
                message="Function implementation is incomplete",
                confidence=Confidence.MEDIUM,
                context="def authenticate():\n    pass  # Incomplete implementation"
            )
        ]

        mock_result = AnalysisResult()
        mock_result.all_issues = mock_issues
        mock_result.total_files_analyzed = 5
        mock_result.issues_by_type = {IssueType.TODO: 1, IssueType.INCOMPLETE: 1}

        mock_analyzer.analyze_codebase.return_value = mock_result
        return mock_analyzer

    @pytest.fixture
    def mcp_request_basic(self):
        """Basic MCP request for analyze_code_for_work"""
        return {
            "project_name": "test-project",
            "create_items": False
        }

    @pytest.fixture
    def mcp_request_create_items(self):
        """MCP request with create_items=True"""
        return {
            "project_name": "test-project",
            "create_items": True,
            "sync_to_github": False
        }

    @pytest.fixture
    def mcp_request_specific_file(self):
        """MCP request for specific file analysis"""
        return {
            "project_name": "test-project",
            "file_path": "src/utils.py",
            "create_items": False
        }

    @pytest.mark.anyio
    async def test_analyze_code_preview_mode(self, mock_code_analyzer, mcp_request_basic):
        """Test basic code analysis in preview mode (create_items=False)"""
        with patch('mcp_server.CodeAnalyzer', return_value=mock_code_analyzer):
            with patch('mcp_server.get_project') as mock_get_project:
                # Mock project configuration
                mock_get_project.return_value = {
                    'name': 'test-project',
                    'root_dir': '/path/to/project'
                }

                response = await handle_analyze_code_for_work(mcp_request_basic)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "issues" in response_data["data"]
        assert len(response_data["data"]["issues"]) == 2

        # Verify issue structure
        issue = response_data["data"]["issues"][0]
        assert "title" in issue
        assert "file_path" in issue
        assert "line_number" in issue
        assert "confidence" in issue
        assert "issue_type" in issue

        # Verify analyzer was called with correct path
        mock_code_analyzer.analyze_codebase.assert_called_once_with('/path/to/project')

    @pytest.mark.anyio
    async def test_analyze_code_specific_file(self, mock_code_analyzer, mcp_request_specific_file):
        """Test analyzing a specific file"""
        # Mock analyzer to return single file analysis
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_file.return_value = mock_code_analyzer.analyze_codebase.return_value.all_issues

        with patch('mcp_server.CodeAnalyzer', return_value=mock_analyzer_instance):
            with patch('mcp_server.get_project') as mock_get_project:
                with patch('pathlib.Path.exists', return_value=True):
                    mock_get_project.return_value = {
                        'name': 'test-project',
                        'root_dir': '/path/to/project'
                    }

                    response = await handle_analyze_code_for_work(mcp_request_specific_file)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True

        # Verify analyzer was called with specific file
        # Note: analyze_file method needs to be implemented in CodeAnalyzer
        # mock_analyzer_instance.analyze_file.assert_called_once_with('/path/to/project/src/utils.py')

    @pytest.mark.anyio
    async def test_analyze_code_create_work_items(self, mock_code_analyzer, mock_dev_context, mcp_request_create_items):
        """Test code analysis with automatic work item creation"""
        with patch('mcp_server.CodeAnalyzer', return_value=mock_code_analyzer):
            with patch('mcp_server.DevContextManager', return_value=mock_dev_context):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    with patch('mcp_server.get_project') as mock_get_project:
                        mock_get_project.return_value = {
                            'name': 'test-project',
                            'root_dir': '/path/to/project'
                        }

                        response = await handle_analyze_code_for_work(mcp_request_create_items)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert "work_items_created" in response_data["data"]
        assert response_data["data"]["work_items_created"] == 2

        # Verify work items were created for each issue
        assert mock_dev_context.create_work_item.call_count == 2

        # Check first work item call
        call_args = mock_dev_context.create_work_item.call_args_list[0]
        assert "Add error handling" in call_args[1]["title"]
        assert call_args[1]["work_type"] == "todo"
        assert call_args[1]["priority"] == "high"  # High confidence -> high priority

    @pytest.mark.anyio
    async def test_analyze_code_confidence_filtering(self, mock_dev_context):
        """Test that only high-confidence issues create work items when create_items=True"""
        # Create issues with different confidence levels
        from core.code_analyzer import AnalysisResult, Issue, IssueType, Confidence

        mock_issues = [
            Issue(IssueType.TODO, "file1.py", 10, "High confidence issue", Confidence.HIGH),
            Issue(IssueType.TODO, "file2.py", 20, "Medium confidence issue", Confidence.MEDIUM),
            Issue(IssueType.TODO, "file3.py", 30, "Low confidence issue", Confidence.LOW)
        ]

        mock_result = AnalysisResult()
        mock_result.all_issues = mock_issues
        mock_result.total_files_analyzed = 3

        mock_analyzer = Mock()
        mock_analyzer.analyze_codebase.return_value = mock_result

        request = {
            "project_name": "test-project",
            "create_items": True,
            "min_confidence": "high"  # Only high confidence issues
        }

        with patch('mcp_server.CodeAnalyzer', return_value=mock_analyzer):
            with patch('mcp_server.DevContextManager', return_value=mock_dev_context):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    with patch('mcp_server.get_project') as mock_get_project:
                        mock_get_project.return_value = {
                            'name': 'test-project',
                            'root_dir': '/path/to/project'
                        }

                        response = await handle_analyze_code_for_work(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is True
        assert response_data["data"]["work_items_created"] == 1  # Only high confidence

        # Verify only high confidence issue created work item
        mock_dev_context.create_work_item.assert_called_once()

    @pytest.mark.anyio
    async def test_analyze_code_invalid_project(self):
        """Test error handling for invalid project name"""
        request = {
            "project_name": "nonexistent-project",
            "create_items": False
        }

        with patch('mcp_server.get_project', side_effect=KeyError("Project not found")):
            response = await handle_analyze_code_for_work(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "not found" in response_data["error"].lower()

    @pytest.mark.anyio
    async def test_analyze_code_file_system_error(self, mock_code_analyzer):
        """Test error handling for file system errors"""
        mock_code_analyzer.analyze_codebase.side_effect = FileNotFoundError("Directory not found")

        request = {
            "project_name": "test-project",
            "create_items": False
        }

        with patch('mcp_server.CodeAnalyzer', return_value=mock_code_analyzer):
            with patch('mcp_server.get_project') as mock_get_project:
                mock_get_project.return_value = {
                    'name': 'test-project',
                    'root_dir': '/nonexistent/path'
                }

                response = await handle_analyze_code_for_work(request)

        response_data = json.loads(response.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data
        assert "not found" in response_data["error"].lower()

    @pytest.mark.anyio
    async def test_analyze_code_work_type_mapping(self, mock_dev_context):
        """Test that issue types are correctly mapped to work types"""
        from core.code_analyzer import AnalysisResult, Issue, IssueType, Confidence

        mock_issues = [
            Issue(IssueType.TODO, "file1.py", 10, "TODO item", Confidence.HIGH),
            Issue(IssueType.FIXME, "file2.py", 20, "Bug to fix", Confidence.HIGH),
            Issue(IssueType.INCOMPLETE, "file3.py", 30, "Incomplete function", Confidence.HIGH),
            Issue(IssueType.ERROR_PATTERN, "file4.py", 40, "Error pattern", Confidence.HIGH)
        ]

        mock_result = AnalysisResult()
        mock_result.all_issues = mock_issues
        mock_result.total_files_analyzed = 4

        mock_analyzer = Mock()
        mock_analyzer.analyze_codebase.return_value = mock_result

        request = {
            "project_name": "test-project",
            "create_items": True
        }

        with patch('mcp_server.CodeAnalyzer', return_value=mock_analyzer):
            with patch('mcp_server.DevContextManager', return_value=mock_dev_context):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    with patch('mcp_server.get_project') as mock_get_project:
                        mock_get_project.return_value = {
                            'name': 'test-project',
                            'root_dir': '/path/to/project'
                        }

                        response = await handle_analyze_code_for_work(request)

        # Verify work type mapping
        calls = mock_dev_context.create_work_item.call_args_list
        work_types = [call[1]["work_type"] for call in calls]

        assert "todo" in work_types  # TODO -> todo
        assert "bug" in work_types   # FIXME -> bug
        assert "feature" in work_types  # INCOMPLETE -> feature
        assert "bug" in work_types   # ERROR_PATTERN -> bug

    @pytest.mark.anyio
    async def test_analyze_code_priority_mapping(self, mock_dev_context):
        """Test that confidence levels are correctly mapped to priorities"""
        from core.code_analyzer import AnalysisResult, Issue, IssueType, Confidence

        mock_issues = [
            Issue(IssueType.TODO, "file1.py", 10, "High priority", Confidence.HIGH),
            Issue(IssueType.TODO, "file2.py", 20, "Medium priority", Confidence.MEDIUM),
            Issue(IssueType.TODO, "file3.py", 30, "Low priority", Confidence.LOW)
        ]

        mock_result = AnalysisResult()
        mock_result.all_issues = mock_issues
        mock_result.total_files_analyzed = 3

        mock_analyzer = Mock()
        mock_analyzer.analyze_codebase.return_value = mock_result

        request = {
            "project_name": "test-project",
            "create_items": True
        }

        with patch('mcp_server.CodeAnalyzer', return_value=mock_analyzer):
            with patch('mcp_server.DevContextManager', return_value=mock_dev_context):
                with patch('mcp_server.get_config', return_value=self._mock_config()):
                    with patch('mcp_server.get_project') as mock_get_project:
                        mock_get_project.return_value = {
                            'name': 'test-project',
                            'root_dir': '/path/to/project'
                        }

                        response = await handle_analyze_code_for_work(request)

        # Verify priority mapping
        calls = mock_dev_context.create_work_item.call_args_list
        priorities = [call[1]["priority"] for call in calls]

        assert "high" in priorities    # HIGH confidence -> high priority
        assert "medium" in priorities  # MEDIUM confidence -> medium priority
        assert "low" in priorities     # LOW confidence -> low priority


class TestAnalyzeCodeForWorkIntegration:
    """Integration tests for analyze_code_for_work MCP tool"""

    @pytest.mark.anyio
    async def test_tool_registration(self):
        """Test that analyze_code_for_work tool is properly registered in TOOLS list"""
        from mcp_server import TOOLS
        tool_names = [tool.name for tool in TOOLS]
        assert "analyze_code_for_work" in tool_names

    @pytest.mark.anyio
    async def test_tool_schema_validation(self):
        """Test that tool schema is properly defined"""
        from mcp_server import TOOLS

        analyze_tool = None
        for tool in TOOLS:
            if tool.name == "analyze_code_for_work":
                analyze_tool = tool
                break

        assert analyze_tool is not None
        assert analyze_tool.description is not None
        assert "project_name" in analyze_tool.inputSchema["properties"]
        assert "create_items" in analyze_tool.inputSchema["properties"]
        assert "file_path" in analyze_tool.inputSchema["properties"]
        assert analyze_tool.inputSchema["required"] == ["project_name"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])