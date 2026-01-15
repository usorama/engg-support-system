"""
GitHub Client Integration for Veracity Engine.

Provides robust GitHub API integration with:
- PAT and OAuth token authentication
- Issue creation and updates (status, labels, assignees)
- Rate limiting detection and exponential backoff
- Comprehensive error handling
- Work item to GitHub issue mapping
"""

import time
import re
from typing import Dict, List, Optional, Any
import requests
from requests.exceptions import ConnectionError, Timeout


# Custom Exceptions
class GitHubAuthenticationError(Exception):
    """Raised when GitHub authentication fails (401)."""
    pass


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded (403 with rate limit headers)."""
    pass


class GitHubAPIError(Exception):
    """Raised for other GitHub API errors (403, 404, 422, 500, etc)."""
    pass


class WorkItemMapper:
    """
    Handles bidirectional mapping between work items and GitHub issues.

    Converts work item data to GitHub issue format and vice versa,
    including metadata preservation via issue body formatting.
    """

    def work_item_to_issue(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert work item to GitHub issue format.

        Args:
            work_item: Work item data with fields:
                - title: Issue title
                - description: Issue description
                - uid: Unique work item identifier
                - work_type: Type of work (feature, bug, etc)
                - status: Work item status
                - priority: Priority level
                - assignee: Assignee username
                - labels: List of labels

        Returns:
            Dict with GitHub issue fields: title, body, labels, assignees, state
        """
        # Map status to GitHub state
        status = work_item.get("status", "open")
        state = "closed" if status in ["completed", "done", "closed"] else "open"

        # Build labels list: original labels + work_type + priority
        labels = list(work_item.get("labels", []))
        if work_item.get("work_type"):
            labels.append(work_item["work_type"])
        if work_item.get("priority"):
            labels.append(f"priority:{work_item['priority']}")

        # Build assignees list
        assignees = []
        if work_item.get("assignee"):
            assignees.append(work_item["assignee"])

        # Format body with metadata
        body = self.format_issue_body(work_item)

        return {
            "title": work_item["title"],
            "body": body,
            "labels": labels,
            "assignees": assignees,
            "state": state
        }

    def issue_to_work_item(self, github_issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert GitHub issue to work item format.

        Args:
            github_issue: GitHub issue API response

        Returns:
            Dict with work item fields
        """
        return {
            "title": github_issue["title"],
            "description": github_issue["body"],
            "external_id": str(github_issue["number"]),
            "source": "github",
            "status": "closed" if github_issue["state"] == "closed" else "open",
            "labels": [label["name"] for label in github_issue.get("labels", [])],
            "assignees": [assignee["login"] for assignee in github_issue.get("assignees", [])],
            "created_at": github_issue.get("created_at"),
            "updated_at": github_issue.get("updated_at"),
            "html_url": github_issue.get("html_url")
        }

    def extract_work_item_uid(self, issue_body: str) -> Optional[str]:
        """
        Extract work item UID from GitHub issue body.

        Looks for pattern: **Work Item UID**: <uid>

        Args:
            issue_body: GitHub issue body text

        Returns:
            Work item UID if found, None otherwise
        """
        pattern = r'\*\*Work Item UID\*\*:\s*([^\s\n]+)'
        match = re.search(pattern, issue_body)
        return match.group(1) if match else None

    def format_issue_body(self, work_item: Dict[str, Any]) -> str:
        """
        Format work item data into GitHub issue body with metadata.

        Args:
            work_item: Work item data

        Returns:
            Formatted issue body string
        """
        description = work_item.get("description", "")
        uid = work_item.get("uid", "")
        work_type = work_item.get("work_type", "")

        body_parts = [description]

        if uid or work_type:
            body_parts.append("\n\n---\n")

        if uid:
            body_parts.append(f"**Work Item UID**: {uid}")

        if work_type:
            body_parts.append(f"\n**Work Type**: {work_type}")

        return "".join(body_parts)


class GitHubClient:
    """
    GitHub API client with rate limiting, retries, and error handling.

    Features:
    - PAT and OAuth token authentication
    - Issue creation and updates
    - Rate limit detection from X-RateLimit-* headers
    - Exponential backoff retry on rate limits
    - Comprehensive error handling for all HTTP status codes
    - Network error handling (ConnectionError, Timeout)
    """

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        api_base_url: str = "https://api.github.com",
        auth_type: str = "bearer",
        max_retries: int = 3,
        backoff_factor: int = 2,
        retry_on_rate_limit: bool = False,
        timeout: int = 30
    ):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token or OAuth token
            owner: Repository owner (org or user)
            repo: Repository name
            api_base_url: GitHub API base URL
            auth_type: Authentication type ("bearer" or "oauth")
            max_retries: Maximum number of retries on rate limit
            backoff_factor: Exponential backoff multiplier
            retry_on_rate_limit: Whether to automatically retry on rate limit
            timeout: Request timeout in seconds

        Raises:
            ValueError: If token is not provided
        """
        if not token:
            raise ValueError("token is required")

        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_base_url = api_base_url
        self.auth_type = auth_type
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_rate_limit = retry_on_rate_limit
        self.timeout = timeout
        self.mapper = WorkItemMapper()

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

    def _is_rate_limit_error(self, response: requests.Response) -> bool:
        """
        Check if response is a rate limit error.

        Rate limit errors have:
        - Status code 403
        - X-RateLimit-Remaining header = 0
        - Message containing "rate limit"
        """
        if response.status_code != 403:
            return False

        # Check X-RateLimit-Remaining header
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            return True

        # Check response message
        try:
            data = response.json()
            message = data.get("message", "").lower()
            if "rate limit" in message:
                return True
        except Exception:
            pass

        return False

    def _get_rate_limit_reset_time(self, response: requests.Response) -> Optional[int]:
        """Get rate limit reset time from response headers."""
        reset_time = response.headers.get("X-RateLimit-Reset")
        return int(reset_time) if reset_time else None

    def _handle_response_errors(self, response: requests.Response):
        """
        Handle HTTP error responses.

        Raises appropriate exceptions based on status code:
        - 401: GitHubAuthenticationError
        - 403 (rate limit): GitHubRateLimitError
        - 403 (other): GitHubAPIError
        - 404, 422, 500+: GitHubAPIError
        """
        if response.status_code < 400:
            return

        # Check for rate limit error first
        if self._is_rate_limit_error(response):
            reset_time = self._get_rate_limit_reset_time(response)
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded. "
                f"Reset at: {reset_time if reset_time else 'unknown'}"
            )

        # Authentication error (401)
        if response.status_code == 401:
            msg = response.json().get('message', 'Invalid credentials')
            raise GitHubAuthenticationError(
                f"GitHub authentication failed: {msg}"
            )

        # Other API errors
        try:
            error_data = response.json()
            message = error_data.get("message", "Unknown error")

            # Include validation errors for 422
            if response.status_code == 422 and "errors" in error_data:
                errors = error_data["errors"]
                message = f"Validation failed: {message}. Errors: {errors}"

            raise GitHubAPIError(
                f"GitHub API error {response.status_code}: {message}"
            )
        except GitHubAPIError:
            raise
        except Exception:
            raise GitHubAPIError(
                f"GitHub API error {response.status_code}: {response.text}"
            )

    def _make_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry on rate limits.

        Args:
            method: HTTP method (GET, POST, PATCH)
            url: Request URL
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            GitHubRateLimitError: If rate limit exceeded and retries exhausted
            GitHubAuthenticationError: If authentication fails
            GitHubAPIError: For other API errors
            ConnectionError: For network connection errors
            Timeout: For request timeout errors
        """
        attempt = 0

        while attempt <= self.max_retries:
            try:
                # Use the specific method function to ensure mocks work correctly
                if method.upper() == 'GET':
                    response = requests.get(url, timeout=self.timeout, **kwargs)
                elif method.upper() == 'POST':
                    response = requests.post(url, timeout=self.timeout, **kwargs)
                elif method.upper() == 'PATCH':
                    response = requests.patch(url, timeout=self.timeout, **kwargs)
                else:
                    response = requests.request(method, url, timeout=self.timeout, **kwargs)

                # Check if it's a rate limit error
                if self._is_rate_limit_error(response):
                    if not self.retry_on_rate_limit or attempt >= self.max_retries:
                        self._handle_response_errors(response)

                    # Calculate backoff delay
                    delay = self.backoff_factor ** attempt
                    time.sleep(delay)
                    attempt += 1
                    continue

                # Handle other errors
                self._handle_response_errors(response)
                return response

            except (ConnectionError, Timeout):
                # Don't retry on network errors, propagate immediately
                raise
            except (GitHubAuthenticationError, GitHubAPIError):
                # Don't retry on auth or API errors (except rate limit)
                raise

        # Should not reach here, but just in case
        raise GitHubRateLimitError("Max retries exceeded for rate limit")

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body/description
            labels: List of label names
            assignees: List of assignee usernames

        Returns:
            GitHub issue API response

        Raises:
            GitHubAuthenticationError: If authentication fails
            GitHubRateLimitError: If rate limit exceeded
            GitHubAPIError: For other API errors
        """
        url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/issues"

        data = {
            "title": title,
            "body": body
        }

        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        response = self._make_request_with_retry(
            "POST",
            url,
            headers=self._get_headers(),
            json=data
        )

        return response.json()

    def create_issue_from_work_item(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a GitHub issue from work item data.

        Args:
            work_item: Work item data dictionary

        Returns:
            GitHub issue API response
        """
        issue_data = self.mapper.work_item_to_issue(work_item)

        return self.create_issue(
            title=issue_data["title"],
            body=issue_data["body"],
            labels=issue_data.get("labels"),
            assignees=issue_data.get("assignees")
        )

    def update_issue(
        self,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update a GitHub issue.

        Args:
            issue_number: Issue number to update
            title: New title (optional)
            body: New body (optional)
            state: New state: "open" or "closed" (optional)
            labels: New labels list (optional)
            assignees: New assignees list (optional)

        Returns:
            Updated GitHub issue API response

        Raises:
            GitHubAuthenticationError: If authentication fails
            GitHubRateLimitError: If rate limit exceeded
            GitHubAPIError: For other API errors
        """
        url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}"

        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        if assignees is not None:
            data["assignees"] = assignees

        response = self._make_request_with_retry(
            "PATCH",
            url,
            headers=self._get_headers(),
            json=data
        )

        return response.json()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status from GitHub API.

        Returns:
            Rate limit status with resources.core.limit, remaining, reset

        Raises:
            GitHubAuthenticationError: If authentication fails
            GitHubAPIError: For other API errors
        """
        url = f"{self.api_base_url}/rate_limit"

        response = self._make_request_with_retry(
            "GET",
            url,
            headers=self._get_headers()
        )

        return response.json()

    def create_issues_batch(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple GitHub issues from work items.

        Args:
            work_items: List of work item dictionaries

        Returns:
            List of created GitHub issue responses
        """
        results = []

        for work_item in work_items:
            issue = self.create_issue(
                title=work_item["title"],
                body=work_item["description"]
            )
            results.append(issue)

        return results
