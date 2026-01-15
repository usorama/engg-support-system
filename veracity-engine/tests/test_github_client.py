"""
Comprehensive test suite for GitHub Client Integration.

Tests cover:
1. GitHub issue creation with work item data
2. GitHub issue updates (status, labels, assignees)
3. Rate limiting detection and backoff
4. Authentication failure handling
5. Network error handling
6. GitHub API error responses (404, 403, 422)
7. Work item to GitHub issue mapping
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import time
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

# Expected import - will fail until implementation exists
try:
    from integrations.github_client import (
        GitHubClient,
        GitHubAuthenticationError,
        GitHubRateLimitError,
        GitHubAPIError,
        WorkItemMapper
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    # Define placeholder classes for test structure validation
    class GitHubClient:
        pass

    class GitHubAuthenticationError(Exception):
        pass

    class GitHubRateLimitError(Exception):
        pass

    class GitHubAPIError(Exception):
        pass

    class WorkItemMapper:
        pass


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses."""
    def _create_response(status_code=200, json_data=None, headers=None):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.headers = headers or {}
        response.text = str(json_data)
        response.raise_for_status = Mock()

        if status_code >= 400:
            response.raise_for_status.side_effect = HTTPError(
                f"HTTP {status_code} Error"
            )

        return response
    return _create_response


@pytest.fixture
def github_config():
    """GitHub client configuration for testing."""
    return {
        "token": "ghp_test_token_1234567890abcdef",
        "owner": "test-org",
        "repo": "test-repo",
        "api_base_url": "https://api.github.com",
        "max_retries": 3,
        "backoff_factor": 2
    }


@pytest.fixture
def work_item_data():
    """Sample work item data for testing."""
    return {
        "uid": "test-project::workitem::abc123",
        "title": "Implement user authentication",
        "description": "Add OAuth2 authentication flow for users",
        "work_type": "feature",
        "status": "in_progress",
        "priority": "high",
        "assignee": "developer1",
        "labels": ["authentication", "security"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def github_issue_response():
    """Sample GitHub issue API response."""
    return {
        "id": 123456,
        "number": 42,
        "title": "Implement user authentication",
        "body": "Add OAuth2 authentication flow for users",
        "state": "open",
        "html_url": "https://github.com/test-org/test-repo/issues/42",
        "labels": [
            {"name": "authentication"},
            {"name": "security"}
        ],
        "assignees": [
            {"login": "developer1"}
        ],
        "created_at": "2026-01-15T10:00:00Z",
        "updated_at": "2026-01-15T10:00:00Z"
    }


@pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="GitHubClient not implemented yet")
class TestGitHubClient:
    """Test suite for GitHubClient core functionality."""

    def test_client_initialization_with_pat(self, github_config):
        """Test client initialization with Personal Access Token."""
        client = GitHubClient(
            token=github_config["token"],
            owner=github_config["owner"],
            repo=github_config["repo"]
        )

        assert client.token == github_config["token"]
        assert client.owner == github_config["owner"]
        assert client.repo == github_config["repo"]
        assert client.api_base_url == "https://api.github.com"

    def test_client_initialization_with_oauth(self):
        """Test client initialization with OAuth token."""
        oauth_token = "oauth_test_token_xyz"
        client = GitHubClient(
            token=oauth_token,
            owner="test-org",
            repo="test-repo",
            auth_type="oauth"
        )

        assert client.token == oauth_token
        assert client.auth_type == "oauth"

    def test_client_initialization_without_token_fails(self):
        """Test that client initialization without token raises error."""
        with pytest.raises(ValueError, match="token is required"):
            GitHubClient(token=None, owner="test-org", repo="test-repo")

    @patch('requests.post')
    def test_create_issue_success(self, mock_post, github_config,
                                   work_item_data, github_issue_response,
                                   mock_response):
        """Test successful GitHub issue creation from work item."""
        mock_post.return_value = mock_response(201, github_issue_response)

        client = GitHubClient(**github_config)
        result = client.create_issue(
            title=work_item_data["title"],
            body=work_item_data["description"],
            labels=work_item_data["labels"],
            assignees=[work_item_data["assignee"]]
        )

        assert result["number"] == 42
        assert result["title"] == work_item_data["title"]
        assert result["state"] == "open"

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {github_config['token']}"

    @patch('requests.post')
    def test_create_issue_with_work_item_metadata(self, mock_post, github_config,
                                                   work_item_data, github_issue_response,
                                                   mock_response):
        """Test issue creation includes work item UID in body."""
        mock_post.return_value = mock_response(201, github_issue_response)

        client = GitHubClient(**github_config)
        result = client.create_issue_from_work_item(work_item_data)

        # Verify work item UID is included in body
        call_args = mock_post.call_args
        request_body = call_args[1]["json"]["body"]
        assert work_item_data["uid"] in request_body

    @patch('requests.patch')
    def test_update_issue_status(self, mock_patch, github_config,
                                 github_issue_response, mock_response):
        """Test updating GitHub issue status."""
        updated_response = {**github_issue_response, "state": "closed"}
        mock_patch.return_value = mock_response(200, updated_response)

        client = GitHubClient(**github_config)
        result = client.update_issue(
            issue_number=42,
            state="closed"
        )

        assert result["state"] == "closed"
        mock_patch.assert_called_once()

    @patch('requests.patch')
    def test_update_issue_labels(self, mock_patch, github_config,
                                 github_issue_response, mock_response):
        """Test updating GitHub issue labels."""
        updated_response = {
            **github_issue_response,
            "labels": [{"name": "bug"}, {"name": "critical"}]
        }
        mock_patch.return_value = mock_response(200, updated_response)

        client = GitHubClient(**github_config)
        result = client.update_issue(
            issue_number=42,
            labels=["bug", "critical"]
        )

        assert len(result["labels"]) == 2
        assert result["labels"][0]["name"] == "bug"

    @patch('requests.patch')
    def test_update_issue_assignees(self, mock_patch, github_config,
                                    github_issue_response, mock_response):
        """Test updating GitHub issue assignees."""
        updated_response = {
            **github_issue_response,
            "assignees": [{"login": "developer2"}]
        }
        mock_patch.return_value = mock_response(200, updated_response)

        client = GitHubClient(**github_config)
        result = client.update_issue(
            issue_number=42,
            assignees=["developer2"]
        )

        assert result["assignees"][0]["login"] == "developer2"


@pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="GitHubClient not implemented yet")
class TestRateLimiting:
    """Test suite for GitHub API rate limiting and backoff."""

    @patch('requests.post')
    def test_rate_limit_detection_from_headers(self, mock_post, github_config, mock_response):
        """Test rate limit detection from X-RateLimit headers."""
        rate_limit_headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 3600)
        }
        mock_post.return_value = mock_response(
            403,
            {"message": "API rate limit exceeded"},
            rate_limit_headers
        )

        client = GitHubClient(**github_config)

        with pytest.raises(GitHubRateLimitError) as exc_info:
            client.create_issue(title="Test", body="Test body")

        assert "rate limit" in str(exc_info.value).lower()

    @patch('requests.post')
    def test_rate_limit_backoff_retry(self, mock_post, github_config,
                                     github_issue_response, mock_response):
        """Test exponential backoff retry on rate limit."""
        # First call: rate limited
        # Second call: success
        rate_limit_response = mock_response(
            403,
            {"message": "API rate limit exceeded"},
            {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(time.time()) + 1)}
        )
        success_response = mock_response(201, github_issue_response)

        mock_post.side_effect = [rate_limit_response, success_response]

        client = GitHubClient(**github_config, retry_on_rate_limit=True)

        with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
            result = client.create_issue(title="Test", body="Test body")

        assert result["number"] == 42
        assert mock_post.call_count == 2
        mock_sleep.assert_called()  # Verify backoff sleep was called

    @patch('requests.get')
    def test_check_rate_limit_status(self, mock_get, github_config, mock_response):
        """Test checking current rate limit status."""
        rate_limit_status = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                    "reset": int(time.time()) + 3600
                }
            }
        }
        mock_get.return_value = mock_response(200, rate_limit_status)

        client = GitHubClient(**github_config)
        status = client.get_rate_limit_status()

        assert status["resources"]["core"]["remaining"] == 4999
        assert status["resources"]["core"]["limit"] == 5000

    @patch('requests.post')
    def test_max_retries_exhausted(self, mock_post, github_config, mock_response):
        """Test that max retries are respected and error is raised."""
        rate_limit_response = mock_response(
            403,
            {"message": "API rate limit exceeded"},
            {"X-RateLimit-Remaining": "0"}
        )
        mock_post.return_value = rate_limit_response

        # MODIFIED: Fix duplicate keyword argument - merge config with overrides
        # Original: client = GitHubClient(**github_config, max_retries=2, retry_on_rate_limit=True)
        # Changed to: Create config dict with overrides to avoid duplicate keyword args
        config = {**github_config, 'max_retries': 2, 'retry_on_rate_limit': True}
        client = GitHubClient(**config)

        with patch('time.sleep'):
            with pytest.raises(GitHubRateLimitError):
                client.create_issue(title="Test", body="Test")

        # Should try initial + 2 retries = 3 total calls
        assert mock_post.call_count == 3


@pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="GitHubClient not implemented yet")
class TestErrorHandling:
    """Test suite for GitHub API error handling."""

    @patch('requests.post')
    def test_authentication_failure_401(self, mock_post, github_config, mock_response):
        """Test handling of 401 authentication failure."""
        mock_post.return_value = mock_response(
            401,
            {"message": "Bad credentials"}
        )

        client = GitHubClient(**github_config)

        with pytest.raises(GitHubAuthenticationError) as exc_info:
            client.create_issue(title="Test", body="Test")

        assert "authentication" in str(exc_info.value).lower()

    @patch('requests.post')
    def test_forbidden_403_access_denied(self, mock_post, github_config, mock_response):
        """Test handling of 403 forbidden (non-rate-limit)."""
        mock_post.return_value = mock_response(
            403,
            {"message": "Resource not accessible by integration"}
        )

        client = GitHubClient(**github_config)

        with pytest.raises(GitHubAPIError) as exc_info:
            client.create_issue(title="Test", body="Test")

        assert "403" in str(exc_info.value)

    @patch('requests.post')
    def test_not_found_404_error(self, mock_post, github_config, mock_response):
        """Test handling of 404 not found (repo doesn't exist)."""
        mock_post.return_value = mock_response(
            404,
            {"message": "Not Found"}
        )

        client = GitHubClient(**github_config)

        with pytest.raises(GitHubAPIError) as exc_info:
            client.create_issue(title="Test", body="Test")

        assert "404" in str(exc_info.value)

    @patch('requests.post')
    def test_validation_failed_422_error(self, mock_post, github_config, mock_response):
        """Test handling of 422 validation failed (invalid data)."""
        mock_post.return_value = mock_response(
            422,
            {
                "message": "Validation Failed",
                "errors": [
                    {"field": "title", "code": "missing_field"}
                ]
            }
        )

        client = GitHubClient(**github_config)

        with pytest.raises(GitHubAPIError) as exc_info:
            client.create_issue(title="", body="Test")

        assert "validation" in str(exc_info.value).lower()

    @patch('requests.post')
    def test_network_connection_error(self, mock_post, github_config):
        """Test handling of network connection errors."""
        mock_post.side_effect = ConnectionError("Connection refused")

        client = GitHubClient(**github_config)

        with pytest.raises(ConnectionError):
            client.create_issue(title="Test", body="Test")

    @patch('requests.post')
    def test_network_timeout_error(self, mock_post, github_config):
        """Test handling of network timeout errors."""
        mock_post.side_effect = Timeout("Request timed out")

        client = GitHubClient(**github_config, timeout=5)

        with pytest.raises(Timeout):
            client.create_issue(title="Test", body="Test")

    @patch('requests.post')
    def test_server_error_500(self, mock_post, github_config, mock_response):
        """Test handling of 500 internal server error."""
        mock_post.return_value = mock_response(
            500,
            {"message": "Internal Server Error"}
        )

        client = GitHubClient(**github_config)

        with pytest.raises(GitHubAPIError) as exc_info:
            client.create_issue(title="Test", body="Test")

        assert "500" in str(exc_info.value)


@pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="WorkItemMapper not implemented yet")
class TestWorkItemMapper:
    """Test suite for WorkItem to GitHub issue mapping."""

    def test_map_work_item_to_issue_basic(self, work_item_data):
        """Test basic mapping of work item to GitHub issue format."""
        mapper = WorkItemMapper()
        issue_data = mapper.work_item_to_issue(work_item_data)

        assert issue_data["title"] == work_item_data["title"]
        assert work_item_data["description"] in issue_data["body"]
        assert work_item_data["uid"] in issue_data["body"]

    def test_map_work_item_labels(self, work_item_data):
        """Test mapping of work item labels and work_type."""
        mapper = WorkItemMapper()
        issue_data = mapper.work_item_to_issue(work_item_data)

        # Should include original labels + work_type as label
        assert work_item_data["work_type"] in issue_data["labels"]
        assert all(label in issue_data["labels"] for label in work_item_data["labels"])

    def test_map_work_item_priority_to_label(self, work_item_data):
        """Test mapping of work item priority to GitHub label."""
        mapper = WorkItemMapper()
        issue_data = mapper.work_item_to_issue(work_item_data)

        # Priority should be added as label
        assert f"priority:{work_item_data['priority']}" in issue_data["labels"]

    def test_map_work_item_assignee(self, work_item_data):
        """Test mapping of work item assignee to GitHub assignee."""
        mapper = WorkItemMapper()
        issue_data = mapper.work_item_to_issue(work_item_data)

        assert work_item_data["assignee"] in issue_data["assignees"]

    def test_map_work_item_status_to_state(self, work_item_data):
        """Test mapping of work item status to GitHub issue state."""
        mapper = WorkItemMapper()

        # Test in_progress -> open
        work_item_data["status"] = "in_progress"
        issue_data = mapper.work_item_to_issue(work_item_data)
        assert issue_data["state"] == "open"

        # Test completed -> closed
        work_item_data["status"] = "completed"
        issue_data = mapper.work_item_to_issue(work_item_data)
        assert issue_data["state"] == "closed"

    def test_map_github_issue_to_work_item(self, github_issue_response):
        """Test reverse mapping of GitHub issue to work item format."""
        mapper = WorkItemMapper()
        work_item = mapper.issue_to_work_item(github_issue_response)

        assert work_item["title"] == github_issue_response["title"]
        assert work_item["description"] == github_issue_response["body"]
        assert work_item["external_id"] == str(github_issue_response["number"])
        assert work_item["source"] == "github"

    def test_extract_work_item_uid_from_issue_body(self):
        """Test extraction of work item UID from GitHub issue body."""
        mapper = WorkItemMapper()

        issue_body = """
        Add OAuth2 authentication flow for users

        **Work Item UID**: test-project::workitem::abc123
        """

        uid = mapper.extract_work_item_uid(issue_body)
        assert uid == "test-project::workitem::abc123"

    def test_format_work_item_body(self, work_item_data):
        """Test formatting of work item data into GitHub issue body."""
        mapper = WorkItemMapper()
        body = mapper.format_issue_body(work_item_data)

        # Should include description and metadata
        assert work_item_data["description"] in body
        assert work_item_data["uid"] in body
        assert work_item_data["work_type"] in body


@pytest.mark.skipif(not IMPLEMENTATION_EXISTS, reason="GitHubClient not implemented yet")
class TestGitHubClientIntegration:
    """Integration tests for complete workflows."""

    @patch('requests.post')
    @patch('requests.patch')
    def test_create_and_update_issue_workflow(self, mock_patch, mock_post,
                                              github_config, work_item_data,
                                              github_issue_response, mock_response):
        """Test complete workflow: create issue -> update status."""
        # Setup mocks
        mock_post.return_value = mock_response(201, github_issue_response)
        updated_response = {**github_issue_response, "state": "closed"}
        mock_patch.return_value = mock_response(200, updated_response)

        client = GitHubClient(**github_config)

        # Create issue
        created_issue = client.create_issue_from_work_item(work_item_data)
        assert created_issue["number"] == 42

        # Update issue status
        updated_issue = client.update_issue(
            issue_number=created_issue["number"],
            state="closed"
        )
        assert updated_issue["state"] == "closed"

    @patch('requests.post')
    def test_batch_issue_creation(self, mock_post, github_config, mock_response):
        """Test creating multiple issues in batch."""
        mock_post.return_value = mock_response(201, {"number": 1})

        client = GitHubClient(**github_config)

        work_items = [
            {"title": f"Issue {i}", "description": f"Description {i}"}
            for i in range(5)
        ]

        results = client.create_issues_batch(work_items)

        assert len(results) == 5
        assert mock_post.call_count == 5
