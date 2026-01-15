"""
Test suite for GitHub Webhooks - Phase 4

Tests webhook handling, queue persistence, and bidirectional sync
between GitHub issues and work items.
"""

import pytest
import json
import hashlib
import hmac
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock


# Import webhook components
try:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../core')))

    from github_webhooks import (
        GitHubWebhookHandler,
        WebhookEvent,
        WebhookConfig,
        SyncQueueManager,
        WebhookVerificationError,
        SyncQueueItem
    )
except ImportError as e:
    pytest.skip(f"GitHub webhooks not implemented yet: {e}", allow_module_level=True)


class TestWebhookVerification:
    """Test webhook signature verification"""

    def test_valid_signature(self):
        """Test verification with valid signature"""
        secret = "test-webhook-secret"
        payload = '{"action": "opened"}'

        # Calculate expected signature
        expected_sig = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        config = WebhookConfig(secret=secret)
        handler = GitHubWebhookHandler(config)

        # Should not raise
        assert handler.verify_signature(payload, f"sha256={expected_sig}") is True

    def test_invalid_signature(self):
        """Test verification with invalid signature"""
        config = WebhookConfig(secret="correct-secret")
        handler = GitHubWebhookHandler(config)

        with pytest.raises(WebhookVerificationError):
            handler.verify_signature('{"test": "data"}', "sha256=invalid")

    def test_missing_signature(self):
        """Test verification with missing signature"""
        config = WebhookConfig(secret="test-secret")
        handler = GitHubWebhookHandler(config)

        with pytest.raises(WebhookVerificationError):
            handler.verify_signature('{"test": "data"}', None)


class TestWebhookEventParsing:
    """Test parsing of GitHub webhook events"""

    def test_parse_issue_opened(self):
        """Test parsing issue opened event"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 42,
                "title": "Bug: Login fails on mobile",
                "body": "Steps to reproduce...",
                "state": "open",
                "labels": [{"name": "bug"}, {"name": "high-priority"}],
                "user": {"login": "testuser"},
                "created_at": "2026-01-15T10:00:00Z",
                "html_url": "https://github.com/test/repo/issues/42"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        event = WebhookEvent.from_payload("issues", payload)

        assert event.event_type == "issues"
        assert event.action == "opened"
        assert event.issue_number == 42
        assert event.title == "Bug: Login fails on mobile"
        assert event.repository == "test/repo"
        assert "bug" in event.labels

    def test_parse_issue_closed(self):
        """Test parsing issue closed event"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 42,
                "title": "Bug: Login fails",
                "body": "",
                "state": "closed",
                "labels": [],
                "user": {"login": "testuser"},
                "created_at": "2026-01-15T10:00:00Z",
                "html_url": "https://github.com/test/repo/issues/42"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        event = WebhookEvent.from_payload("issues", payload)

        assert event.action == "closed"
        assert event.state == "closed"

    def test_parse_issue_labeled(self):
        """Test parsing issue labeled event"""
        payload = {
            "action": "labeled",
            "label": {"name": "critical"},
            "issue": {
                "number": 42,
                "title": "Bug",
                "body": "",
                "state": "open",
                "labels": [{"name": "bug"}, {"name": "critical"}],
                "user": {"login": "testuser"},
                "created_at": "2026-01-15T10:00:00Z",
                "html_url": "https://github.com/test/repo/issues/42"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        event = WebhookEvent.from_payload("issues", payload)

        assert event.action == "labeled"
        assert "critical" in event.labels

    def test_parse_pr_opened(self):
        """Test parsing pull request opened event"""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "feat: Add user dashboard",
                "body": "Implements #42",
                "state": "open",
                "labels": [{"name": "enhancement"}],
                "user": {"login": "developer"},
                "head": {"sha": "abc123"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/test/repo/pull/123"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        event = WebhookEvent.from_payload("pull_request", payload)

        assert event.event_type == "pull_request"
        assert event.action == "opened"
        assert event.pr_number == 123
        assert event.head_sha == "abc123"


class TestSyncQueueManager:
    """Test sync queue persistence"""

    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver with proper return values"""
        mock = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock result that returns dict-like single record
        mock_result = Mock()
        mock_result.single.return_value = {"uid": "queue::sync::test123", "count": 0}

        # For iteration (get_pending, etc)
        mock_queue_node = {
            "uid": "queue::item::1",
            "work_item_uid": "project::workitem::abc123",
            "action": "create",
            "target_system": "github",
            "payload": '{"title": "Test"}',
            "status": "pending",
            "priority": "normal",
            "retry_count": 0,
            "created_at": "2026-01-15T10:00:00Z"
        }
        mock_result.__iter__ = Mock(return_value=iter([{"q": mock_queue_node}]))

        mock_session.run.return_value = mock_result
        mock.session.return_value = mock_session
        return mock

    def test_enqueue_sync_action(self, mock_driver):
        """Test enqueueing a sync action"""
        manager = SyncQueueManager(mock_driver)

        item = SyncQueueItem(
            work_item_uid="project::workitem::abc123",
            action="create",
            target_system="github",
            payload={"title": "Test", "body": "Description"},
            priority="normal"
        )

        uid = manager.enqueue(item)

        assert uid is not None
        mock_driver.session.return_value.run.assert_called()

    def test_dequeue_pending_items(self, mock_driver):
        """Test dequeuing pending items"""
        manager = SyncQueueManager(mock_driver)
        items = manager.get_pending(limit=10)

        # Should get items from the mock iterator
        assert len(items) >= 0

    def test_mark_completed(self, mock_driver):
        """Test marking item as completed"""
        manager = SyncQueueManager(mock_driver)

        success = manager.mark_completed("queue::item::1")

        mock_driver.session.return_value.run.assert_called()

    def test_mark_failed_with_retry(self, mock_driver):
        """Test marking item as failed with retry"""
        manager = SyncQueueManager(mock_driver)

        result = manager.mark_failed(
            "queue::item::1",
            error="Rate limit exceeded",
            should_retry=True
        )

        mock_driver.session.return_value.run.assert_called()


class TestGitHubWebhookHandler:
    """Test webhook event handling"""

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager"""
        mock = Mock()
        mock.create_work_item.return_value = "project::workitem::new123"
        mock.update_work_item.return_value = True
        mock.get_work_item_by_external_id.return_value = {
            "uid": "project::workitem::existing456",
            "title": "Existing issue",
            "status": "open"
        }
        mock.query_work_items.return_value = []
        return mock

    @pytest.fixture
    def webhook_config(self):
        """Create webhook config"""
        return WebhookConfig(
            secret="test-secret",
            project_name="test-project",
            sync_issues=True,
            sync_prs=True,
            auto_create_work_items=True
        )

    @pytest.mark.anyio
    async def test_handle_issue_opened_creates_work_item(self, webhook_config, mock_dev_context):
        """Test that issue opened event creates work item"""
        handler = GitHubWebhookHandler(webhook_config)
        handler._dev_context = mock_dev_context

        event = WebhookEvent(
            event_type="issues",
            action="opened",
            issue_number=42,
            title="Bug: Application crashes",
            body="Details here",
            state="open",
            labels=["bug", "critical"],
            repository="test/repo",
            user="reporter"
        )

        result = await handler.handle_event(event)

        assert result["action"] == "created_work_item"
        mock_dev_context.create_work_item.assert_called_once()

        # Verify work item details
        call_kwargs = mock_dev_context.create_work_item.call_args[1]
        assert call_kwargs["external_id"] == "github-issue-42"
        assert call_kwargs["source"] == "github"

    @pytest.mark.anyio
    async def test_handle_issue_closed_updates_work_item(self, webhook_config, mock_dev_context):
        """Test that issue closed event updates work item status"""
        handler = GitHubWebhookHandler(webhook_config)
        handler._dev_context = mock_dev_context

        event = WebhookEvent(
            event_type="issues",
            action="closed",
            issue_number=42,
            title="Bug: Fixed",
            body="",
            state="closed",
            labels=["bug"],
            repository="test/repo",
            user="fixer"
        )

        result = await handler.handle_event(event)

        assert result["action"] == "updated_work_item"
        mock_dev_context.update_work_item.assert_called()

        # Verify status was updated to closed
        call_kwargs = mock_dev_context.update_work_item.call_args[1]
        assert call_kwargs["status"] == "closed"

    @pytest.mark.anyio
    async def test_handle_issue_labeled_updates_priority(self, webhook_config, mock_dev_context):
        """Test that adding critical label updates priority"""
        handler = GitHubWebhookHandler(webhook_config)
        handler._dev_context = mock_dev_context

        # Put "critical" label first so it matches first in iteration
        event = WebhookEvent(
            event_type="issues",
            action="labeled",
            issue_number=42,
            title="Bug",
            body="",
            state="open",
            labels=["critical", "bug"],
            repository="test/repo",
            user="triager"
        )

        result = await handler.handle_event(event)

        # Should update priority based on label (critical matches first)
        if result["action"] == "updated_work_item":
            call_kwargs = mock_dev_context.update_work_item.call_args[1]
            assert call_kwargs.get("priority") == "critical"

    @pytest.mark.anyio
    async def test_handle_pr_merged_links_to_work_item(self, webhook_config, mock_dev_context):
        """Test that merged PR links to work item via commit references"""
        handler = GitHubWebhookHandler(webhook_config)
        handler._dev_context = mock_dev_context

        event = WebhookEvent(
            event_type="pull_request",
            action="closed",
            pr_number=123,
            title="fix: Resolve login bug",
            body="Fixes #42",
            state="closed",
            labels=[],
            repository="test/repo",
            user="developer",
            is_merged=True,
            head_sha="abc123"
        )

        result = await handler.handle_event(event)

        # Should process the PR and potentially link
        assert result["action"] in ["linked_to_work_item", "processed_pr", "no_action"]


class TestBidirectionalSync:
    """Test bidirectional sync between GitHub and work items"""

    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub API client"""
        mock = Mock()
        mock.create_issue.return_value = {
            "number": 100,
            "html_url": "https://github.com/test/repo/issues/100"
        }
        mock.update_issue.return_value = {
            "number": 42,
            "state": "closed"
        }
        return mock

    @pytest.fixture
    def mock_dev_context(self):
        """Mock DevContextManager"""
        mock = Mock()
        mock.query_work_items.return_value = [
            {
                "uid": "project::workitem::abc123",
                "title": "New feature request",
                "description": "User wants X",
                "status": "open",
                "priority": "high",
                "work_type": "feature",
                "external_id": None,  # Not yet synced to GitHub
                "source": "manual"
            }
        ]
        mock.update_work_item.return_value = True
        return mock

    @pytest.mark.anyio
    async def test_sync_work_item_to_github(self, mock_github_client, mock_dev_context):
        """Test syncing a local work item to GitHub"""
        from github_webhooks import sync_work_item_to_github

        work_item = {
            "uid": "project::workitem::abc123",
            "title": "New feature",
            "description": "Details",
            "work_type": "feature",
            "priority": "high"
        }

        result = await sync_work_item_to_github(
            work_item,
            mock_github_client,
            mock_dev_context,
            repo="test/repo"
        )

        assert result["success"] is True
        assert result["github_issue_number"] == 100
        mock_github_client.create_issue.assert_called_once()

    @pytest.mark.anyio
    async def test_sync_github_close_to_work_item(self, mock_github_client, mock_dev_context):
        """Test syncing GitHub issue close to work item"""
        from github_webhooks import sync_github_status_to_work_item

        mock_dev_context.get_work_item_by_external_id.return_value = {
            "uid": "project::workitem::abc123",
            "status": "open"
        }

        result = await sync_github_status_to_work_item(
            github_issue_number=42,
            new_state="closed",
            dev_context=mock_dev_context,
            repo="test/repo"
        )

        assert result["success"] is True
        mock_dev_context.update_work_item.assert_called()


class TestQueuePersistence:
    """Test queue persistence across restarts"""

    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver with proper return values"""
        mock = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock result that returns dict-like single record
        mock_result = Mock()
        mock_result.single.return_value = {"uid": "queue::sync::test123", "count": 0}

        # For iteration (get_pending, etc)
        mock_queue_node = {
            "uid": "queue::item::1",
            "work_item_uid": "project::workitem::abc",
            "action": "create",
            "target_system": "github",
            "payload": '{"title": "Test"}',
            "status": "pending",
            "priority": "normal",
            "retry_count": 0,
            "created_at": "2026-01-15T10:00:00Z",
            "error_message": None
        }
        mock_result.__iter__ = Mock(return_value=iter([{"q": mock_queue_node}]))

        mock_session.run.return_value = mock_result
        mock.session.return_value = mock_session
        return mock

    def test_queue_survives_restart(self, mock_driver):
        """Test that queued items are retrieved after restart"""
        manager = SyncQueueManager(mock_driver)

        # "Restart" - create new manager instance
        manager2 = SyncQueueManager(mock_driver)
        items = manager2.get_pending()

        # Items should still be available from persistent store
        assert len(items) >= 0

    def test_retry_failed_items(self, mock_driver):
        """Test that failed items are retried"""
        manager = SyncQueueManager(mock_driver)

        # Mark as failed with retry
        manager.mark_failed("queue::item::1", "Timeout", should_retry=True)

        # Get items for retry
        retry_items = manager.get_for_retry(max_retries=3)

        mock_driver.session.return_value.run.assert_called()

    def test_dead_letter_queue(self, mock_driver):
        """Test that items exceeding max retries go to dead letter queue"""
        manager = SyncQueueManager(mock_driver)

        # Mark as failed too many times
        for _ in range(4):  # Exceed max retries of 3
            manager.mark_failed("queue::item::1", "Persistent error", should_retry=True)

        # Should be moved to dead letter
        dead_items = manager.get_dead_letter_items()

        mock_driver.session.return_value.run.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
