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

    def update_work_item(self, work_item_uid: str,
                        status: Optional[str] = None,
                        priority: Optional[str] = None,
                        assignees: Optional[List[str]] = None,
                        labels: Optional[List[str]] = None,
                        closure_reason: Optional[str] = None,
                        changed_by: str = "system") -> bool:
        """
        Update WorkItem node properties.

        Args:
            work_item_uid: WorkItem UID to update
            status: New status value (optional)
            priority: New priority value (optional)
            assignees: List of assignee identifiers (optional)
            labels: List of labels/tags (optional)
            closure_reason: Reason for closure if status is closed (optional)
            changed_by: Actor who made the change (default: "system")

        Returns:
            True if update successful, False otherwise

        Raises:
            InvalidUIIDFormatError: If UID format is invalid
            WorkItemNotFoundError: If work item not found
        """
        # Validate UID format
        self._validate_uid(work_item_uid)

        # Get current work item to compare for audit events
        try:
            current_item = self.get_work_item(work_item_uid)
        except WorkItemNotFoundError:
            raise

        # Build SET clauses dynamically for provided fields
        set_clauses = ["w.updated_at = $updated_at"]
        params = {
            "uid": work_item_uid,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if status is not None:
            set_clauses.append("w.status = $status")
            params["status"] = status

        if priority is not None:
            set_clauses.append("w.priority = $priority")
            params["priority"] = priority

        if assignees is not None:
            set_clauses.append("w.assignees = $assignees")
            params["assignees"] = assignees

        if labels is not None:
            set_clauses.append("w.labels = $labels")
            params["labels"] = labels

        if closure_reason is not None:
            set_clauses.append("w.closure_reason = $closure_reason")
            params["closure_reason"] = closure_reason

        # Build and execute update query
        set_clause = ", ".join(set_clauses)
        query = f"""
        MATCH (w:WorkItem {{uid: $uid}})
        SET {set_clause}
        RETURN w
        """

        with self._driver.session() as session:
            result = session.run(query, params)
            record = result.single()

            if not record:
                return False

            # Create audit event for status changes
            if status is not None and current_item.get("status") != status:
                self._create_audit_event(
                    work_item_uid=work_item_uid,
                    event_type="status_changed",
                    old_value=current_item.get("status"),
                    new_value=status,
                    changed_by=changed_by
                )

            # Create audit event for priority changes
            if priority is not None and current_item.get("priority") != priority:
                self._create_audit_event(
                    work_item_uid=work_item_uid,
                    event_type="priority_changed",
                    old_value=current_item.get("priority"),
                    new_value=priority,
                    changed_by=changed_by
                )

            return True

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

    def query_work_items(self, offset: int = 0, limit: int = 20,
                         status: Optional[str] = None,
                         priority: Optional[str] = None,
                         work_type: Optional[str] = None,
                         order_by: str = "created_at",
                         order_direction: str = "DESC") -> List[Dict[str, Any]]:
        """
        Query work items with pagination and filtering.

        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum results to return (default: 20)
            status: Filter by status (optional)
            priority: Filter by priority (optional)
            work_type: Filter by work_type (optional)
            order_by: Field to order by (default: created_at)
            order_direction: Sort direction ASC/DESC (default: DESC)

        Returns:
            List of work item dictionaries
        """
        # Build WHERE clause based on filters
        where_clauses = []
        params = {
            "offset": offset,
            "limit": limit
        }

        if status:
            where_clauses.append("w.status = $status")
            params["status"] = status

        if priority:
            where_clauses.append("w.priority = $priority")
            params["priority"] = priority

        if work_type:
            where_clauses.append("w.work_type = $work_type")
            params["work_type"] = work_type

        where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # Validate order_by to prevent injection
        valid_order_fields = ["created_at", "updated_at", "title", "priority", "status"]
        if order_by not in valid_order_fields:
            order_by = "created_at"

        # Validate order_direction
        order_direction = order_direction.upper()
        if order_direction not in ["ASC", "DESC"]:
            order_direction = "DESC"

        query = f"""
        MATCH (w:WorkItem)
        WHERE {where_clause}
        RETURN w
        ORDER BY w.{order_by} {order_direction}
        SKIP $offset
        LIMIT $limit
        """

        with self._driver.session() as session:
            result = session.run(query, params)
            work_items = []
            for record in result:
                work_item = dict(record["w"])
                work_items.append(work_item)
            return work_items

    def get_work_context(self, work_item_uid: str,
                         include_related_commits: bool = True,
                         include_related_files: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive context for a work item.

        Args:
            work_item_uid: WorkItem UID
            include_related_commits: Include related CodeChange nodes (default: True)
            include_related_files: Include related file paths (default: True)

        Returns:
            Dictionary with work_item, related_commits, and related_files

        Raises:
            WorkItemNotFoundError: If work item not found
        """
        # Get work item
        work_item = self.get_work_item(work_item_uid)

        context = {
            "work_item": work_item,
            "related_commits": [],
            "related_files": []
        }

        # Get related commits via LINKS_TO relationship
        if include_related_commits:
            commit_query = """
            MATCH (c:CodeChange)-[:LINKS_TO]->(w:WorkItem {uid: $uid})
            RETURN c
            ORDER BY c.timestamp DESC
            LIMIT 50
            """

            with self._driver.session() as session:
                result = session.run(commit_query, {"uid": work_item_uid})
                for record in result:
                    commit = dict(record["c"])
                    context["related_commits"].append(commit)

        # Get related files from CodeChange nodes
        if include_related_files:
            file_query = """
            MATCH (c:CodeChange)-[:LINKS_TO]->(w:WorkItem {uid: $uid})
            RETURN DISTINCT c.file_path AS file_path
            ORDER BY c.file_path
            LIMIT 100
            """

            with self._driver.session() as session:
                result = session.run(file_query, {"uid": work_item_uid})
                for record in result:
                    context["related_files"].append(record["file_path"])

        return context

    def trace_file_to_work(self, file_path: str,
                          min_confidence: float = 0.5,
                          trace_direction: str = "backward",
                          max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Trace a file to related work items (backward tracing).

        Args:
            file_path: File path to trace
            min_confidence: Minimum confidence score for links (default: 0.5)
            trace_direction: Direction of trace (backward only for now)
            max_depth: Maximum depth of traversal (default: 3)

        Returns:
            List of work items with trace metadata
        """
        # Query for CodeChange nodes affecting this file, then traverse to WorkItems
        query = """
        MATCH (c:CodeChange)-[r:LINKS_TO]->(w:WorkItem)
        WHERE c.file_path = $file_path
          AND r.confidence >= $min_confidence
        WITH w, r, c
        ORDER BY r.confidence DESC, c.timestamp DESC
        RETURN w.uid AS work_item_uid,
               w.title AS title,
               w.status AS status,
               w.priority AS priority,
               r.confidence AS confidence,
               coalesce(r.reason, 'Direct implementation') AS link_reason,
               collect({
                   commit_hash: c.commit_hash,
                   timestamp: c.timestamp,
                   change_type: c.change_type,
                   lines_added: c.lines_added,
                   lines_deleted: c.lines_deleted
               }) AS commits
        LIMIT 50
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "file_path": file_path,
                "min_confidence": min_confidence
            })

            traces = []
            for record in result:
                trace = {
                    "work_item_uid": record["work_item_uid"],
                    "title": record["title"],
                    "status": record["status"],
                    "priority": record["priority"],
                    "confidence": record["confidence"],
                    "link_reason": record["link_reason"],
                    "commits": record["commits"]
                }
                traces.append(trace)

            return traces

    def get_orphan_commits(self, max_count: int = 100, age_days: int = 30) -> List[Dict[str, Any]]:
        """
        Get Git commits that are not linked to any work items.

        Orphaned commits are CodeChange nodes that don't have LINKS_TO relationships
        with WorkItem nodes. These commits represent work that may need to be
        categorized and tracked.

        Args:
            max_count: Maximum number of orphan commits to return
            age_days: Only include commits newer than this many days

        Returns:
            List of commit dictionaries with commit_hash, message, author, etc.
        """
        # Calculate cutoff date
        from datetime import datetime, timezone, timedelta
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()

        query = """
        MATCH (c:CodeChange)
        WHERE NOT (c)-[:LINKS_TO]->(:WorkItem)
          AND c.timestamp >= $cutoff_date
        RETURN DISTINCT c.commit_hash AS commit_hash,
               c.author AS author,
               c.timestamp AS timestamp,
               count(c) AS file_changes
        ORDER BY c.timestamp DESC
        LIMIT $max_count
        """

        with self._driver.session() as session:
            result = session.run(query, {
                "cutoff_date": cutoff_date,
                "max_count": max_count
            })

            orphan_commits = []
            for record in result:
                commit = {
                    "commit_hash": record["commit_hash"],
                    "author": record["author"],
                    "timestamp": record["timestamp"],
                    "file_changes": record["file_changes"],
                    "message": ""  # Will be populated by GitAnalyzer from actual git repo
                }
                orphan_commits.append(commit)

            return orphan_commits

    def link_code_to_work(self, work_item_uid: str = None, code_change_uid: str = None,
                         commit_hash: str = None, link_type: str = "direct",
                         confidence: float = 1.0) -> bool:
        """
        Create LINKS_TO relationship between CodeChange and WorkItem.

        Supports linking by either code_change_uid or commit_hash.

        Args:
            work_item_uid: WorkItem UID
            code_change_uid: CodeChange UID (alternative to commit_hash)
            commit_hash: Git commit hash (alternative to code_change_uid)
            link_type: Type of link (direct, commit, inferred)
            confidence: Confidence score for the link (0.0-1.0)

        Returns:
            True if link created successfully
        """
        if code_change_uid:
            # Original behavior - link by code_change_uid
            query = """
            MATCH (c:CodeChange {uid: $code_change_uid})
            MATCH (w:WorkItem {uid: $work_item_uid})
            MERGE (c)-[r:LINKS_TO {
                confidence: $confidence,
                link_type: $link_type,
                linked_at: $linked_at
            }]->(w)
            RETURN r
            """

            params = {
                "code_change_uid": code_change_uid,
                "work_item_uid": work_item_uid,
                "confidence": confidence,
                "link_type": link_type,
                "linked_at": datetime.now(timezone.utc).isoformat()
            }

        elif commit_hash:
            # New behavior - link by commit_hash (for orphan commits)
            query = """
            MATCH (c:CodeChange {commit_hash: $commit_hash})
            MATCH (w:WorkItem {uid: $work_item_uid})
            MERGE (c)-[r:LINKS_TO {
                confidence: $confidence,
                link_type: $link_type,
                linked_at: $linked_at
            }]->(w)
            RETURN count(r) AS links_created
            """

            params = {
                "commit_hash": commit_hash,
                "work_item_uid": work_item_uid,
                "confidence": confidence,
                "link_type": link_type,
                "linked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise ValueError("Either code_change_uid or commit_hash must be provided")

        with self._driver.session() as session:
            result = session.run(query, params)
            record = result.single()

            if commit_hash:
                # For commit_hash linking, check if any links were created
                return record and record["links_created"] > 0
            else:
                # For code_change_uid linking, check if relationship exists
                return record is not None
