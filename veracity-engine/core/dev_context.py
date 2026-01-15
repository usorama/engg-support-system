"""
Dev Context Tracking - Enhanced Neo4j Schema

Implements WorkItem, CodeChange, WorkItemEvent, and SyncQueue nodes
with deterministic UID generation and comprehensive indexing.

Schema follows project::type::<hash> UID pattern for determinism.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


class WorkItemNotFoundError(Exception):
    """Raised when a work item UID is not found in the graph"""
    pass


class InvalidUIIDFormatError(Exception):
    """Raised when a UID does not follow the project::type::<hash> pattern"""
    pass


class SchemaCreationError(Exception):
    """Raised when schema/constraint/index creation fails"""
    pass


class DevContextManager:
    """
    Manages development context tracking in Neo4j graph.

    Provides:
    - WorkItem node creation and management
    - CodeChange node creation and linking
    - WorkItemEvent audit log tracking
    - SyncQueue for webhook persistence
    - Enhanced indexing per critical analysis
    """

    def __init__(self, project_name: str, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j", neo4j_password: str = "password"):
        """
        Initialize DevContextManager with Neo4j connection.

        Args:
            project_name: Project identifier for UID generation
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.project_name = project_name
        self._driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def close(self):
        """Close Neo4j driver connection"""
        if self._driver:
            self._driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _generate_work_item_uid(self, title: str, content: str) -> str:
        """
        Generate deterministic UID for WorkItem.

        Pattern: project::workitem::<hash>
        Hash is SHA-256 of title + content for determinism.

        Args:
            title: Work item title
            content: Work item content/description

        Returns:
            Deterministic UID string
        """
        combined = f"{title}::{content}"
        hash_digest = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return f"{self.project_name}::workitem::{hash_digest}"

    def _generate_code_change_uid(self, commit_hash: str, file_path: str,
                                   change_type: str) -> str:
        """
        Generate deterministic UID for CodeChange.

        Pattern: project::codechanqge::<commit_hash>-<file_hash>
        Uses commit hash for determinism and traceability.

        Args:
            commit_hash: Git commit hash
            file_path: File path changed
            change_type: Type of change (modified, added, deleted)

        Returns:
            Deterministic UID string
        """
        # Include file path and change type in hash for uniqueness per file per commit
        combined = f"{file_path}::{change_type}"
        file_hash = hashlib.sha256(combined.encode()).hexdigest()[:8]
        return f"{self.project_name}::codechanqge::{commit_hash}-{file_hash}"

    def _validate_uid(self, uid: str) -> bool:
        """
        Validate UID follows project::type::<hash> pattern.

        Args:
            uid: UID string to validate

        Returns:
            True if valid

        Raises:
            InvalidUIIDFormatError: If UID format is invalid
        """
        parts = uid.split("::")
        if len(parts) != 3:
            raise InvalidUIIDFormatError(
                f"UID must have 3 parts (project::type::hash), got: {uid}"
            )

        project, node_type, hash_part = parts

        if not project:
            raise InvalidUIIDFormatError(f"Project name is empty in UID: {uid}")

        valid_types = ["workitem", "codechanqge", "event", "syncqueue"]
        if node_type not in valid_types:
            raise InvalidUIIDFormatError(
                f"Node type must be one of {valid_types}, got: {node_type}"
            )

        if len(hash_part) < 8:
            raise InvalidUIIDFormatError(
                f"Hash part must be at least 8 characters, got: {hash_part}"
            )

        return True

    def create_schema(self):
        """
        Create enhanced Neo4j schema with constraints and indexes.

        Creates:
        - Unique constraints on WorkItem.uid, CodeChange.uid, etc.
        - Composite index on external_id + source
        - Index on source field
        - Index on updated_at field

        Raises:
            SchemaCreationError: If schema creation fails
        """
        schema_queries = [
            # Unique constraints
            "CREATE CONSTRAINT work_item_uid_unique IF NOT EXISTS "
            "FOR (w:WorkItem) REQUIRE w.uid IS UNIQUE",

            "CREATE CONSTRAINT code_change_uid_unique IF NOT EXISTS "
            "FOR (c:CodeChange) REQUIRE c.uid IS UNIQUE",

            "CREATE CONSTRAINT work_item_event_uid_unique IF NOT EXISTS "
            "FOR (e:WorkItemEvent) REQUIRE e.uid IS UNIQUE",

            "CREATE CONSTRAINT sync_queue_uid_unique IF NOT EXISTS "
            "FOR (s:SyncQueue) REQUIRE s.uid IS UNIQUE",

            # Enhanced indexes per critical analysis
            "CREATE INDEX work_item_external_source IF NOT EXISTS "
            "FOR (w:WorkItem) ON (w.external_id, w.source)",

            "CREATE INDEX work_item_source IF NOT EXISTS "
            "FOR (w:WorkItem) ON (w.source)",

            "CREATE INDEX work_item_updated_at IF NOT EXISTS "
            "FOR (w:WorkItem) ON (w.updated_at)",
        ]

        with self._driver.session() as session:
            try:
                for query in schema_queries:
                    session.run(query)
            except Neo4jError as e:
                raise SchemaCreationError(f"Failed to create schema: {str(e)}") from e

    def create_work_item(self, title: str, description: str, work_type: str,
                         priority: str = "medium", status: str = "open",
                         external_id: Optional[str] = None,
                         source: Optional[str] = None) -> str:
        """
        Create a new WorkItem node in the graph.

        Args:
            title: Work item title
            description: Work item description
            work_type: Type (feature, bug, task, etc.)
            priority: Priority level (low, medium, high, critical)
            status: Current status (open, in_progress, done, etc.)
            external_id: External system ID (e.g., github-issue-123)
            source: External system name (e.g., github, jira)

        Returns:
            Generated work item UID
        """
        uid = self._generate_work_item_uid(title, description)
        now = datetime.now(timezone.utc).isoformat()

        query = """
        CREATE (w:WorkItem {
            uid: $uid,
            title: $title,
            description: $description,
            work_type: $work_type,
            status: $status,
            priority: $priority,
            external_id: $external_id,
            source: $source,
            created_at: $created_at,
            updated_at: $updated_at
        })
        RETURN w.uid AS uid
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": uid,
                "title": title,
                "description": description,
                "work_type": work_type,
                "status": status,
                "priority": priority,
                "external_id": external_id,
                "source": source,
                "created_at": now,
                "updated_at": now
            })
            record = result.single()
            return record["uid"] if record else uid

    def record_code_change(self, commit_hash: str, file_path: str,
                          change_type: str, lines_added: int = 0,
                          lines_deleted: int = 0, author: Optional[str] = None) -> str:
        """
        Record a code change (git commit) in the graph.

        Args:
            commit_hash: Git commit hash
            file_path: File path changed
            change_type: Type of change (modified, added, deleted)
            lines_added: Number of lines added
            lines_deleted: Number of lines deleted
            author: Commit author

        Returns:
            Generated code change UID
        """
        uid = self._generate_code_change_uid(commit_hash, file_path, change_type)
        now = datetime.now(timezone.utc).isoformat()

        query = """
        CREATE (c:CodeChange {
            uid: $uid,
            commit_hash: $commit_hash,
            file_path: $file_path,
            change_type: $change_type,
            lines_added: $lines_added,
            lines_deleted: $lines_deleted,
            author: $author,
            timestamp: $timestamp
        })
        RETURN c.uid AS uid
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": uid,
                "commit_hash": commit_hash,
                "file_path": file_path,
                "change_type": change_type,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
                "author": author,
                "timestamp": now
            })
            record = result.single()
            return record["uid"] if record else uid

    def link_code_to_work(self, work_item_uid: str, code_change_uid: str,
                         link_confidence: float = 1.0) -> bool:
        """
        Create LINKS_TO relationship between CodeChange and WorkItem.

        Args:
            work_item_uid: WorkItem UID
            code_change_uid: CodeChange UID
            link_confidence: Confidence score for the link (0.0-1.0)

        Returns:
            True if link created successfully
        """
        query = """
        MATCH (c:CodeChange {uid: $code_change_uid})
        MATCH (w:WorkItem {uid: $work_item_uid})
        CREATE (c)-[r:LINKS_TO {
            confidence: $confidence,
            linked_at: $linked_at
        }]->(w)
        RETURN r
        """

        now = datetime.now(timezone.utc).isoformat()

        with self._driver.session() as session:
            result = session.run(query, {
                "code_change_uid": code_change_uid,
                "work_item_uid": work_item_uid,
                "confidence": link_confidence,
                "linked_at": now
            })
            return result.single() is not None

    def get_work_item(self, uid: str) -> Dict[str, Any]:
        """
        Retrieve a work item by UID.

        Args:
            uid: WorkItem UID

        Returns:
            Dictionary of work item properties

        Raises:
            WorkItemNotFoundError: If work item not found
        """
        query = """
        MATCH (w:WorkItem {uid: $uid})
        RETURN w
        """

        with self._driver.session() as session:
            result = session.run(query, {"uid": uid})
            record = result.single()

            if not record:
                raise WorkItemNotFoundError(f"Work item not found: {uid}")

            return dict(record["w"])

    def _create_audit_event(self, work_item_uid: str, event_type: str,
                           old_value: Optional[str], new_value: Optional[str],
                           changed_by: str) -> str:
        """
        Create WorkItemEvent audit log node.

        Args:
            work_item_uid: Associated WorkItem UID
            event_type: Type of event (status_changed, priority_changed, etc.)
            old_value: Previous value
            new_value: New value
            changed_by: Actor who made the change

        Returns:
            Generated event UID
        """
        event_uid = f"{self.project_name}::event::{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        query = """
        CREATE (e:WorkItemEvent {
            uid: $uid,
            work_item_uid: $work_item_uid,
            event_type: $event_type,
            old_value: $old_value,
            new_value: $new_value,
            changed_by: $changed_by,
            changed_at: $changed_at
        })
        RETURN e.uid AS uid
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": event_uid,
                "work_item_uid": work_item_uid,
                "event_type": event_type,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by,
                "changed_at": now
            })
            record = result.single()
            return record["uid"] if record else event_uid

    def _enqueue_sync_action(self, work_item_uid: str, action: str,
                            target_system: str, payload: Dict[str, Any]) -> str:
        """
        Create SyncQueue node for webhook persistence.

        Args:
            work_item_uid: Associated WorkItem UID
            action: Sync action type (create, update, delete)
            target_system: Target system name (github, jira, etc.)
            payload: Action payload data

        Returns:
            Generated sync queue UID
        """
        queue_uid = f"{self.project_name}::syncqueue::{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        query = """
        CREATE (s:SyncQueue {
            uid: $uid,
            work_item_uid: $work_item_uid,
            action: $action,
            target_system: $target_system,
            status: $status,
            retry_count: $retry_count,
            next_retry_at: $next_retry_at,
            error_message: $error_message,
            payload: $payload,
            created_at: $created_at
        })
        RETURN s.uid AS uid
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "uid": queue_uid,
                "work_item_uid": work_item_uid,
                "action": action,
                "target_system": target_system,
                "status": "pending",
                "retry_count": 0,
                "next_retry_at": None,
                "error_message": None,
                "payload": str(payload),  # Serialize dict to string for Neo4j
                "created_at": now
            })
            record = result.single()
            return record["uid"] if record else queue_uid
