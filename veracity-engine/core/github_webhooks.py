"""
GitHub Webhooks Handler - Phase 4

Handles incoming GitHub webhook events and manages bidirectional sync
between GitHub issues/PRs and work items with queue persistence.
"""

import re
import json
import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails"""
    pass


class WebhookProcessingError(Exception):
    """Raised when webhook event processing fails"""
    pass


@dataclass
class WebhookConfig:
    """Configuration for GitHub webhook handler"""
    secret: str
    project_name: str = "default"
    sync_issues: bool = True
    sync_prs: bool = True
    auto_create_work_items: bool = True
    auto_update_github: bool = True
    label_to_priority: Dict[str, str] = field(default_factory=lambda: {
        "critical": "critical",
        "high-priority": "high",
        "bug": "high",
        "enhancement": "medium",
        "low-priority": "low"
    })
    label_to_work_type: Dict[str, str] = field(default_factory=lambda: {
        "bug": "bug",
        "enhancement": "feature",
        "feature": "feature",
        "documentation": "docs",
        "refactor": "refactor"
    })


@dataclass
class WebhookEvent:
    """Parsed webhook event data"""
    event_type: str
    action: str
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    title: str = ""
    body: str = ""
    state: str = "open"
    labels: List[str] = field(default_factory=list)
    repository: str = ""
    user: str = ""
    created_at: Optional[str] = None
    html_url: Optional[str] = None
    is_merged: bool = False
    head_sha: Optional[str] = None
    base_ref: Optional[str] = None

    @classmethod
    def from_payload(cls, event_type: str, payload: Dict[str, Any]) -> 'WebhookEvent':
        """Create WebhookEvent from raw payload"""
        action = payload.get("action", "")
        repository = payload.get("repository", {}).get("full_name", "")

        if event_type == "issues":
            issue = payload.get("issue", {})
            return cls(
                event_type=event_type,
                action=action,
                issue_number=issue.get("number"),
                title=issue.get("title", ""),
                body=issue.get("body", "") or "",
                state=issue.get("state", "open"),
                labels=[l.get("name", "") for l in issue.get("labels", [])],
                repository=repository,
                user=issue.get("user", {}).get("login", ""),
                created_at=issue.get("created_at"),
                html_url=issue.get("html_url")
            )
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            return cls(
                event_type=event_type,
                action=action,
                pr_number=pr.get("number"),
                title=pr.get("title", ""),
                body=pr.get("body", "") or "",
                state=pr.get("state", "open"),
                labels=[l.get("name", "") for l in pr.get("labels", [])],
                repository=repository,
                user=pr.get("user", {}).get("login", ""),
                html_url=pr.get("html_url"),
                is_merged=pr.get("merged", False),
                head_sha=pr.get("head", {}).get("sha"),
                base_ref=pr.get("base", {}).get("ref")
            )
        else:
            return cls(
                event_type=event_type,
                action=action,
                repository=repository
            )


@dataclass
class SyncQueueItem:
    """Item in the sync queue"""
    work_item_uid: str
    action: str  # create, update, close, delete
    target_system: str  # github, jira, etc.
    payload: Dict[str, Any]
    priority: str = "normal"  # low, normal, high, critical
    uid: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    error_message: Optional[str] = None


class SyncQueueManager:
    """
    Manages persistent sync queue in Neo4j.

    Provides:
    - Queue persistence across restarts
    - Retry logic with exponential backoff
    - Dead letter queue for failed items
    """

    def __init__(self, driver):
        """Initialize with Neo4j driver."""
        self._driver = driver

    def _generate_uid(self) -> str:
        """Generate unique queue item ID."""
        return f"queue::sync::{uuid.uuid4().hex[:16]}"

    def enqueue(self, item: SyncQueueItem) -> str:
        """
        Add item to sync queue.

        Args:
            item: SyncQueueItem to enqueue

        Returns:
            Generated UID for the queue item
        """
        item.uid = item.uid or self._generate_uid()
        item.created_at = datetime.now(timezone.utc).isoformat()

        query = """
        CREATE (q:SyncQueue {
            uid: $uid,
            work_item_uid: $work_item_uid,
            action: $action,
            target_system: $target_system,
            payload: $payload,
            priority: $priority,
            status: $status,
            retry_count: $retry_count,
            max_retries: $max_retries,
            created_at: $created_at,
            next_retry_at: $next_retry_at,
            error_message: $error_message
        })
        RETURN q.uid AS uid
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": item.uid,
                "work_item_uid": item.work_item_uid,
                "action": item.action,
                "target_system": item.target_system,
                "payload": json.dumps(item.payload),
                "priority": item.priority,
                "status": item.status,
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "created_at": item.created_at,
                "next_retry_at": item.next_retry_at,
                "error_message": item.error_message
            })
            record = result.single()
            return record["uid"] if record else item.uid

    def get_pending(self, limit: int = 10) -> List[SyncQueueItem]:
        """Get pending items from queue."""
        query = """
        MATCH (q:SyncQueue)
        WHERE q.status = 'pending'
        RETURN q
        ORDER BY
            CASE q.priority
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                WHEN 'low' THEN 3
            END,
            q.created_at
        LIMIT $limit
        """

        items = []
        with self._driver.session() as session:
            result = session.run(query, {"limit": limit})
            for record in result:
                q = record["q"]
                items.append(SyncQueueItem(
                    uid=q["uid"],
                    work_item_uid=q["work_item_uid"],
                    action=q["action"],
                    target_system=q["target_system"],
                    payload=json.loads(q["payload"]) if q["payload"] else {},
                    priority=q["priority"],
                    status=q["status"],
                    retry_count=q["retry_count"],
                    created_at=q["created_at"]
                ))

        return items

    def get_for_retry(self, max_retries: int = 3) -> List[SyncQueueItem]:
        """Get failed items eligible for retry."""
        now = datetime.now(timezone.utc).isoformat()

        query = """
        MATCH (q:SyncQueue)
        WHERE q.status = 'failed'
          AND q.retry_count < $max_retries
          AND (q.next_retry_at IS NULL OR q.next_retry_at <= $now)
        RETURN q
        ORDER BY q.created_at
        LIMIT 10
        """

        items = []
        with self._driver.session() as session:
            result = session.run(query, {"max_retries": max_retries, "now": now})
            for record in result:
                q = record["q"]
                items.append(SyncQueueItem(
                    uid=q["uid"],
                    work_item_uid=q["work_item_uid"],
                    action=q["action"],
                    target_system=q["target_system"],
                    payload=json.loads(q["payload"]) if q["payload"] else {},
                    retry_count=q["retry_count"]
                ))

        return items

    def mark_completed(self, uid: str) -> bool:
        """Mark queue item as completed."""
        query = """
        MATCH (q:SyncQueue {uid: $uid})
        SET q.status = 'completed',
            q.completed_at = $completed_at
        RETURN q
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": uid,
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
            return result.single() is not None

    def mark_failed(self, uid: str, error: str, should_retry: bool = True) -> bool:
        """Mark queue item as failed."""
        # Calculate next retry time with exponential backoff
        next_retry = None
        if should_retry:
            # Get current retry count
            get_query = "MATCH (q:SyncQueue {uid: $uid}) RETURN q.retry_count AS count"
            with self._driver.session() as session:
                result = session.run(get_query, {"uid": uid})
                record = result.single()
                retry_count = record["count"] if record else 0

                # Exponential backoff: 1min, 5min, 25min
                backoff_minutes = 5 ** retry_count
                next_retry = (
                    datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                ).isoformat()

        query = """
        MATCH (q:SyncQueue {uid: $uid})
        SET q.status = 'failed',
            q.retry_count = q.retry_count + 1,
            q.error_message = $error,
            q.next_retry_at = $next_retry,
            q.last_failed_at = $failed_at
        RETURN q
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": uid,
                "error": error,
                "next_retry": next_retry,
                "failed_at": datetime.now(timezone.utc).isoformat()
            })
            return result.single() is not None

    def get_dead_letter_items(self) -> List[SyncQueueItem]:
        """Get items that exceeded max retries."""
        query = """
        MATCH (q:SyncQueue)
        WHERE q.status = 'failed'
          AND q.retry_count >= q.max_retries
        RETURN q
        ORDER BY q.last_failed_at DESC
        """

        items = []
        with self._driver.session() as session:
            result = session.run(query)
            for record in result:
                q = record["q"]
                items.append(SyncQueueItem(
                    uid=q["uid"],
                    work_item_uid=q["work_item_uid"],
                    action=q["action"],
                    target_system=q["target_system"],
                    payload=json.loads(q["payload"]) if q["payload"] else {},
                    retry_count=q["retry_count"],
                    error_message=q.get("error_message")
                ))

        return items


class GitHubWebhookHandler:
    """
    Handles incoming GitHub webhook events.

    Processes issue and pull request events to sync with work items.
    """

    def __init__(self, config: WebhookConfig):
        """Initialize webhook handler."""
        self.config = config
        self._dev_context = None
        self._queue_manager = None

    def verify_signature(self, payload: str, signature: Optional[str]) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid

        Raises:
            WebhookVerificationError: If signature is invalid or missing
        """
        if not signature:
            raise WebhookVerificationError("Missing signature header")

        if not signature.startswith("sha256="):
            raise WebhookVerificationError("Invalid signature format")

        expected_sig = hmac.new(
            self.config.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        actual_sig = signature[7:]  # Remove "sha256=" prefix

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise WebhookVerificationError("Invalid signature")

        return True

    async def handle_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle a webhook event.

        Args:
            event: Parsed WebhookEvent

        Returns:
            Processing result dictionary
        """
        logger.info("Processing webhook event",
                   event_type=event.event_type,
                   action=event.action)

        if event.event_type == "issues":
            return await self._handle_issue_event(event)
        elif event.event_type == "pull_request":
            return await self._handle_pr_event(event)
        else:
            return {"action": "ignored", "reason": f"Unsupported event type: {event.event_type}"}

    async def _handle_issue_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Handle issue events."""
        external_id = f"github-issue-{event.issue_number}"

        if event.action == "opened":
            # Create new work item
            if self.config.auto_create_work_items and self._dev_context:
                work_type = self._infer_work_type(event.labels)
                priority = self._infer_priority(event.labels)

                work_item_uid = self._dev_context.create_work_item(
                    title=event.title,
                    description=event.body,
                    work_type=work_type,
                    priority=priority,
                    status="open",
                    external_id=external_id,
                    source="github"
                )

                return {
                    "action": "created_work_item",
                    "work_item_uid": work_item_uid,
                    "external_id": external_id
                }

        elif event.action == "closed":
            # Update work item status
            if self._dev_context:
                existing = self._dev_context.get_work_item_by_external_id(external_id)
                if existing:
                    self._dev_context.update_work_item(
                        existing["uid"],
                        status="closed",
                        changed_by="github_webhook"
                    )
                    return {
                        "action": "updated_work_item",
                        "work_item_uid": existing["uid"],
                        "new_status": "closed"
                    }

        elif event.action == "labeled":
            # Update priority based on labels
            if self._dev_context:
                existing = self._dev_context.get_work_item_by_external_id(external_id)
                if existing:
                    priority = self._infer_priority(event.labels)
                    if priority != existing.get("priority"):
                        self._dev_context.update_work_item(
                            existing["uid"],
                            priority=priority,
                            changed_by="github_webhook"
                        )
                        return {
                            "action": "updated_work_item",
                            "work_item_uid": existing["uid"],
                            "new_priority": priority
                        }

        elif event.action == "reopened":
            # Reopen work item
            if self._dev_context:
                existing = self._dev_context.get_work_item_by_external_id(external_id)
                if existing:
                    self._dev_context.update_work_item(
                        existing["uid"],
                        status="open",
                        changed_by="github_webhook"
                    )
                    return {
                        "action": "updated_work_item",
                        "work_item_uid": existing["uid"],
                        "new_status": "open"
                    }

        return {"action": "no_action", "reason": f"Unhandled action: {event.action}"}

    async def _handle_pr_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Handle pull request events."""
        if event.action == "closed" and event.is_merged:
            # PR was merged - try to link to referenced issues
            references = self._extract_issue_references(event.body)

            if references and self._dev_context:
                for issue_num in references:
                    external_id = f"github-issue-{issue_num}"
                    existing = self._dev_context.get_work_item_by_external_id(external_id)

                    if existing and event.head_sha:
                        # Link the merge commit to the work item
                        try:
                            self._dev_context.link_code_to_work(
                                commit_hash=event.head_sha,
                                work_item_uid=existing["uid"],
                                link_type="pr_merge",
                                confidence=1.0
                            )
                        except Exception as e:
                            logger.warning(f"Failed to link PR to work item: {e}")

                return {
                    "action": "linked_to_work_item",
                    "pr_number": event.pr_number,
                    "referenced_issues": references
                }

        return {"action": "processed_pr", "pr_number": event.pr_number}

    def _infer_work_type(self, labels: List[str]) -> str:
        """Infer work type from labels."""
        for label in labels:
            label_lower = label.lower()
            if label_lower in self.config.label_to_work_type:
                return self.config.label_to_work_type[label_lower]

        return "task"  # Default

    def _infer_priority(self, labels: List[str]) -> str:
        """Infer priority from labels."""
        for label in labels:
            label_lower = label.lower()
            if label_lower in self.config.label_to_priority:
                return self.config.label_to_priority[label_lower]

        return "medium"  # Default

    def _extract_issue_references(self, text: str) -> List[int]:
        """Extract issue numbers from text."""
        pattern = r'(?:fix(?:es)?|close[sd]?|resolve[sd]?)\s+#(\d+)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [int(m) for m in matches]


# Bidirectional sync functions

async def sync_work_item_to_github(
    work_item: Dict[str, Any],
    github_client,
    dev_context,
    repo: str
) -> Dict[str, Any]:
    """
    Sync a work item to GitHub as an issue.

    Args:
        work_item: Work item data
        github_client: GitHub API client
        dev_context: DevContextManager
        repo: Repository in "owner/repo" format

    Returns:
        Sync result dictionary
    """
    # Map work type to labels
    labels = []
    work_type = work_item.get("work_type", "task")
    if work_type == "bug":
        labels.append("bug")
    elif work_type == "feature":
        labels.append("enhancement")

    # Map priority to labels
    priority = work_item.get("priority", "medium")
    if priority in ["critical", "high"]:
        labels.append("high-priority")

    try:
        result = github_client.create_issue(
            repo=repo,
            title=work_item["title"],
            body=work_item.get("description", ""),
            labels=labels
        )

        # Update work item with external ID
        dev_context.update_work_item(
            work_item["uid"],
            external_id=f"github-issue-{result['number']}",
            source="github"
        )

        return {
            "success": True,
            "github_issue_number": result["number"],
            "github_url": result.get("html_url")
        }

    except Exception as e:
        logger.error(f"Failed to sync work item to GitHub: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def sync_github_status_to_work_item(
    github_issue_number: int,
    new_state: str,
    dev_context,
    repo: str
) -> Dict[str, Any]:
    """
    Sync GitHub issue status change to work item.

    Args:
        github_issue_number: GitHub issue number
        new_state: New state ("open" or "closed")
        dev_context: DevContextManager
        repo: Repository name (for logging)

    Returns:
        Sync result dictionary
    """
    external_id = f"github-issue-{github_issue_number}"

    try:
        work_item = dev_context.get_work_item_by_external_id(external_id)

        if not work_item:
            return {
                "success": False,
                "error": f"No work item found for {external_id}"
            }

        # Map GitHub state to work item status
        status = "closed" if new_state == "closed" else "open"

        dev_context.update_work_item(
            work_item["uid"],
            status=status,
            changed_by="github_sync"
        )

        return {
            "success": True,
            "work_item_uid": work_item["uid"],
            "new_status": status
        }

    except Exception as e:
        logger.error(f"Failed to sync GitHub status: {e}")
        return {
            "success": False,
            "error": str(e)
        }
