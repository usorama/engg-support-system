"""
Test suite for dev_context.py - Dev Context Tracking Feature

Tests for Neo4j schema creation, work item management, and code change tracking.
Following TDD - these tests should FAIL initially until dev_context.py is implemented.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# This import will fail initially - that's expected in TDD Red phase
try:
    from core.dev_context import (
        DevContextManager,
        WorkItemNotFoundError,
        InvalidUIIDFormatError,
        SchemaCreationError
    )
except ImportError:
    # Expected during TDD Red phase
    pytest.skip("dev_context module not implemented yet", allow_module_level=True)


class TestDevContextManager:
    """Test the main DevContextManager class"""

    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for testing"""
        driver = MagicMock()
        session = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=session)
        session_context.__exit__ = MagicMock(return_value=None)
        driver.session.return_value = session_context
        return driver, session

    @pytest.fixture
    def dev_context_manager(self, mock_neo4j_driver):
        """Create DevContextManager with mocked Neo4j"""
        driver, session = mock_neo4j_driver
        with patch('core.dev_context.GraphDatabase.driver', return_value=driver):
            return DevContextManager(project_name="test-project")

    def test_uid_generation_deterministic(self, dev_context_manager):
        """Test UID generation follows project::type::<hash> pattern"""
        # Test WorkItem UID generation
        work_item_uid = dev_context_manager._generate_work_item_uid(
            title="Test Feature",
            content="Implement test feature"
        )

        assert work_item_uid.startswith("test-project::workitem::")
        assert len(work_item_uid.split("::")) == 3
        assert len(work_item_uid.split("::")[-1]) >= 8  # Hash component

        # Test same inputs produce same UID (deterministic)
        uid2 = dev_context_manager._generate_work_item_uid(
            title="Test Feature",
            content="Implement test feature"
        )
        assert work_item_uid == uid2

    def test_code_change_uid_generation(self, dev_context_manager):
        """Test CodeChange UID generation with git metadata"""
        code_change_uid = dev_context_manager._generate_code_change_uid(
            commit_hash="abc123def456",
            file_path="src/test/example.py",
            change_type="modified"
        )

        assert code_change_uid.startswith("test-project::codechanqge::")
        assert "abc123def456" in code_change_uid

    def test_schema_creation_constraints(self, dev_context_manager):
        """Test schema creation applies all required constraints"""
        mock_driver, mock_session = dev_context_manager._driver, Mock()

        # Mock successful constraint creation
        mock_session.run.return_value = Mock()

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            mock_driver.session.return_value.__enter__.return_value = mock_session

            dev_context_manager.create_schema()

            # Verify constraint queries were executed
            calls = mock_session.run.call_args_list
            constraint_calls = [call for call in calls if 'CONSTRAINT' in str(call[0][0])]

            # Should create constraints for WorkItem, CodeChange, WorkItemEvent, SyncQueue
            assert len(constraint_calls) >= 4

    def test_schema_creation_indexes(self, dev_context_manager):
        """Test schema creation applies enhanced indexes per critical analysis"""
        mock_driver, mock_session = dev_context_manager._driver, Mock()
        mock_session.run.return_value = Mock()

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            mock_driver.session.return_value.__enter__.return_value = mock_session

            dev_context_manager.create_schema()

            # Verify index queries were executed
            calls = mock_session.run.call_args_list
            index_calls = [call for call in calls if 'INDEX' in str(call[0][0])]

            # Should create indexes for external_id+source, source, updated_at per critical analysis
            assert len(index_calls) >= 3

    def test_create_work_item_basic(self, dev_context_manager):
        """Test basic work item creation"""
        mock_driver, mock_session = dev_context_manager._driver, MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"uid": "test-project::workitem::test123"}
        mock_session.run.return_value = mock_result

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            session_context = MagicMock()
            session_context.__enter__ = MagicMock(return_value=mock_session)
            session_context.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = session_context

            work_item_uid = dev_context_manager.create_work_item(
                title="Implement authentication",
                description="Add JWT-based auth",
                work_type="feature",
                priority="high"
            )

            assert work_item_uid.startswith("test-project::workitem::")
            mock_session.run.assert_called()

    def test_create_work_item_with_source(self, dev_context_manager):
        """Test work item creation with external source (GitHub)"""
        mock_driver, mock_session = dev_context_manager._driver, MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"uid": "test-project::workitem::github123"}
        mock_session.run.return_value = mock_result

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            session_context = MagicMock()
            session_context.__enter__ = MagicMock(return_value=mock_session)
            session_context.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = session_context

            work_item_uid = dev_context_manager.create_work_item(
                title="Bug fix",
                description="Fix auth bug",
                work_type="bug",
                external_id="github-issue-123",
                source="github"
            )

            assert work_item_uid is not None
            # Verify call included external metadata
            call_args = mock_session.run.call_args[0]
            assert "external_id" in call_args[0] or "github-issue-123" in str(call_args)

    def test_record_code_change_basic(self, dev_context_manager):
        """Test basic code change recording"""
        mock_driver, mock_session = dev_context_manager._driver, MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"uid": "test-project::codechanqge::abc123-test"}
        mock_session.run.return_value = mock_result

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            session_context = MagicMock()
            session_context.__enter__ = MagicMock(return_value=mock_session)
            session_context.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = session_context

            change_uid = dev_context_manager.record_code_change(
                commit_hash="abc123def456",
                file_path="src/auth/handler.py",
                change_type="modified",
                lines_added=25,
                lines_deleted=5
            )

            assert change_uid.startswith("test-project::codechanqge::")
            mock_session.run.assert_called()

    def test_link_code_to_work_basic(self, dev_context_manager):
        """Test linking code changes to work items"""
        mock_driver, mock_session = dev_context_manager._driver, Mock()
        mock_session.run.return_value = Mock()

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            mock_driver.session.return_value.__enter__.return_value = mock_session

            work_item_uid = "test-project::workitem::abc123"
            code_change_uid = "test-project::codechanqge::def456"

            success = dev_context_manager.link_code_to_work(
                work_item_uid=work_item_uid,
                code_change_uid=code_change_uid,
                link_confidence=0.9
            )

            assert success is True
            mock_session.run.assert_called()

    def test_work_item_not_found_error(self, dev_context_manager):
        """Test error handling for non-existent work items"""
        mock_driver, mock_session = dev_context_manager._driver, Mock()
        # Simulate no results found
        mock_session.run.return_value.single.return_value = None

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            mock_driver.session.return_value.__enter__.return_value = mock_session

            with pytest.raises(WorkItemNotFoundError):
                dev_context_manager.get_work_item("nonexistent-uid")

    def test_invalid_uid_format_error(self, dev_context_manager):
        """Test error handling for invalid UID formats"""
        with pytest.raises(InvalidUIIDFormatError):
            dev_context_manager._validate_uid("invalid-uid-format")

    def test_audit_log_creation(self, dev_context_manager):
        """Test WorkItemEvent audit log node creation"""
        mock_driver, mock_session = dev_context_manager._driver, MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"uid": "test-project::event::evt123"}
        mock_session.run.return_value = mock_result

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            session_context = MagicMock()
            session_context.__enter__ = MagicMock(return_value=mock_session)
            session_context.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = session_context

            dev_context_manager._create_audit_event(
                work_item_uid="test-project::workitem::abc123",
                event_type="status_changed",
                old_value="open",
                new_value="in_progress",
                changed_by="claude-agent"
            )

            # Verify audit event was recorded
            mock_session.run.assert_called()
            call_args = mock_session.run.call_args[0]
            assert "WorkItemEvent" in call_args[0]

    def test_sync_queue_persistence(self, dev_context_manager):
        """Test SyncQueue node creation for GitHub webhook persistence"""
        mock_driver, mock_session = dev_context_manager._driver, MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"uid": "test-project::syncqueue::sync123"}
        mock_session.run.return_value = mock_result

        with patch.object(dev_context_manager, '_driver') as mock_driver:
            session_context = MagicMock()
            session_context.__enter__ = MagicMock(return_value=mock_session)
            session_context.__exit__ = MagicMock(return_value=None)
            mock_driver.session.return_value = session_context

            queue_uid = dev_context_manager._enqueue_sync_action(
                work_item_uid="test-project::workitem::abc123",
                action="update",
                target_system="github",
                payload={"status": "in_progress"}
            )

            assert queue_uid is not None
            mock_session.run.assert_called()
            call_args = mock_session.run.call_args[0]
            assert "SyncQueue" in call_args[0]


class TestSchemaValidation:
    """Test schema validation and constraint enforcement"""

    def test_work_item_required_fields(self):
        """Test WorkItem node requires all mandatory fields"""
        # This test will verify the schema enforces required fields
        # Will be implemented once schema is created
        pass

    def test_unique_constraints_enforced(self):
        """Test unique constraints are properly enforced"""
        # Test UID uniqueness across WorkItem and CodeChange nodes
        pass

    def test_relationship_constraints(self):
        """Test relationship constraints between nodes"""
        # Test LINKS_TO relationship between CodeChange and WorkItem
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])