"""
GitHub API Client for ESS Dev Context Tracking - STORY-009

Provides GitHub API integration for syncing work items to GitHub issues.
Handles authentication, rate limiting, and API interactions.
"""

import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitInfo:
    """GitHub API rate limit information"""
    limit: int
    remaining: int
    reset_time: datetime


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors"""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded"""

    def __init__(self, message: str, reset_time: datetime):
        super().__init__(message)
        self.reset_time = reset_time


class GitHubClient:
    """GitHub API client with rate limiting and error handling"""

    def __init__(self, token: str, user_agent: str = "ESS-Dev-Context-Tracker/1.0"):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            user_agent: User-Agent header for requests
        """
        self.token = token
        self.user_agent = user_agent
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": user_agent
        })

        # Rate limiting tracking
        self._rate_limit_remaining = None
        self._rate_limit_reset = None

        logger.info("GitHub client initialized")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to GitHub API with rate limiting.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            JSON response data

        Raises:
            GitHubRateLimitError: When rate limit is exceeded
            GitHubAPIError: For other API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Check rate limit before making request
        if self._rate_limit_remaining is not None and self._rate_limit_remaining <= 1:
            if self._rate_limit_reset and datetime.now() < self._rate_limit_reset:
                wait_time = (self._rate_limit_reset - datetime.now()).total_seconds()
                raise GitHubRateLimitError(
                    f"Rate limit exceeded. Resets at {self._rate_limit_reset}",
                    self._rate_limit_reset
                )

        try:
            response = self.session.request(method, url, **kwargs)

            # Update rate limit info from headers
            if "X-RateLimit-Remaining" in response.headers:
                self._rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
                reset_timestamp = int(response.headers["X-RateLimit-Reset"])
                self._rate_limit_reset = datetime.fromtimestamp(reset_timestamp)

            # Handle rate limiting
            if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                reset_time = self._rate_limit_reset or datetime.now() + timedelta(hours=1)
                raise GitHubRateLimitError("GitHub API rate limit exceeded", reset_time)

            # Raise for other HTTP errors
            response.raise_for_status()

            return response.json()

        except requests.RequestException as e:
            logger.error("GitHub API request failed", error=str(e), url=url)
            raise GitHubAPIError(f"GitHub API request failed: {str(e)}")

    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit information"""
        data = self._make_request("GET", "/rate_limit")
        core_info = data["resources"]["core"]

        return RateLimitInfo(
            limit=core_info["limit"],
            remaining=core_info["remaining"],
            reset_time=datetime.fromtimestamp(core_info["reset"])
        )

    def create_issue(self, repo: str, title: str, body: str = "", labels: Optional[List[str]] = None,
                    assignees: Optional[List[str]] = None, milestone: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new GitHub issue.

        Args:
            repo: Repository in format "owner/repo"
            title: Issue title
            body: Issue description/body
            labels: List of label names to apply
            assignees: List of usernames to assign
            milestone: Milestone number

        Returns:
            Created issue data
        """
        if "/" not in repo:
            raise GitHubAPIError(f"Invalid repo format: {repo}. Expected 'owner/repo'")

        issue_data = {
            "title": title,
            "body": body or "",
        }

        if labels:
            issue_data["labels"] = labels
        if assignees:
            issue_data["assignees"] = assignees
        if milestone:
            issue_data["milestone"] = milestone

        logger.info("Creating GitHub issue", repo=repo, title=title)

        response = self._make_request("POST", f"/repos/{repo}/issues", json=issue_data)

        logger.info("GitHub issue created",
                   issue_number=response["number"],
                   url=response["html_url"])

        return response

    def update_issue(self, repo: str, issue_number: int, title: Optional[str] = None,
                    body: Optional[str] = None, state: Optional[str] = None,
                    labels: Optional[List[str]] = None, assignees: Optional[List[str]] = None,
                    milestone: Optional[int] = None) -> Dict[str, Any]:
        """
        Update an existing GitHub issue.

        Args:
            repo: Repository in format "owner/repo"
            issue_number: Issue number to update
            title: New issue title
            body: New issue description/body
            state: New state ("open" or "closed")
            labels: List of label names to apply
            assignees: List of usernames to assign
            milestone: Milestone number

        Returns:
            Updated issue data
        """
        if "/" not in repo:
            raise GitHubAPIError(f"Invalid repo format: {repo}. Expected 'owner/repo'")

        update_data = {}

        if title is not None:
            update_data["title"] = title
        if body is not None:
            update_data["body"] = body
        if state is not None:
            update_data["state"] = state
        if labels is not None:
            update_data["labels"] = labels
        if assignees is not None:
            update_data["assignees"] = assignees
        if milestone is not None:
            update_data["milestone"] = milestone

        logger.info("Updating GitHub issue",
                   repo=repo,
                   issue_number=issue_number,
                   updates=list(update_data.keys()))

        response = self._make_request("PATCH", f"/repos/{repo}/issues/{issue_number}",
                                    json=update_data)

        logger.info("GitHub issue updated",
                   issue_number=issue_number,
                   url=response["html_url"])

        return response

    def get_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
        """
        Get a specific GitHub issue.

        Args:
            repo: Repository in format "owner/repo"
            issue_number: Issue number to retrieve

        Returns:
            Issue data
        """
        if "/" not in repo:
            raise GitHubAPIError(f"Invalid repo format: {repo}. Expected 'owner/repo'")

        return self._make_request("GET", f"/repos/{repo}/issues/{issue_number}")

    def list_issues(self, repo: str, state: str = "open", labels: Optional[str] = None,
                   sort: str = "created", direction: str = "desc",
                   since: Optional[str] = None, per_page: int = 30, page: int = 1) -> List[Dict[str, Any]]:
        """
        List issues for a repository.

        Args:
            repo: Repository in format "owner/repo"
            state: Issue state ("open", "closed", "all")
            labels: Label names to filter by (comma-separated)
            sort: Sort field ("created", "updated", "comments")
            direction: Sort direction ("asc", "desc")
            since: Only issues updated at or after this time (ISO 8601)
            per_page: Results per page (1-100)
            page: Page number

        Returns:
            List of issue data
        """
        if "/" not in repo:
            raise GitHubAPIError(f"Invalid repo format: {repo}. Expected 'owner/repo'")

        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page
        }

        if labels:
            params["labels"] = labels
        if since:
            params["since"] = since

        return self._make_request("GET", f"/repos/{repo}/issues", params=params)

    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
            logger.info("GitHub client session closed")


# Work item type to GitHub label mapping
WORK_TYPE_LABELS = {
    "bug": "bug",
    "feature": "enhancement",
    "todo": "todo",
    "chore": "chore",
    "docs": "documentation"
}

# Priority to GitHub label mapping
PRIORITY_LABELS = {
    "high": "high-priority",
    "medium": "medium-priority",
    "low": "low-priority"
}


def map_work_item_to_github_issue(work_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a work item to GitHub issue format.

    Args:
        work_item: Work item data from Neo4j

    Returns:
        GitHub issue creation/update data
    """
    # Create labels from work type and priority
    labels = []

    work_type = work_item.get("work_type")
    if work_type and work_type in WORK_TYPE_LABELS:
        labels.append(WORK_TYPE_LABELS[work_type])

    priority = work_item.get("priority")
    if priority and priority in PRIORITY_LABELS:
        labels.append(PRIORITY_LABELS[priority])

    # Add source label if auto-generated
    source = work_item.get("source")
    if source == "code_analyzer":
        labels.append("auto-generated")

    # Map status to GitHub state
    status = work_item.get("status", "open")
    github_state = "closed" if status in ["closed", "resolved", "done"] else "open"

    return {
        "title": work_item["title"],
        "body": work_item.get("description", ""),
        "labels": labels,
        "state": github_state
    }