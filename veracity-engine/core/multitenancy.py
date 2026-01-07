"""
Multitenancy Isolation Module for Veracity Engine (STORY-006).

Provides strict tenant isolation at schema and query layers:
- Project identity contracts
- Query guards for project scoping
- Cross-project edge validation
- Schema constraint management

All nodes and relationships must be tagged with a project identifier.
Queries cannot return data outside the requested project.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TenantViolationType(Enum):
    """Types of tenant isolation violations."""
    MISSING_PROJECT = "missing_project"
    CROSS_PROJECT_EDGE = "cross_project_edge"
    INVALID_PROJECT_ID = "invalid_project_id"
    QUERY_SCOPE_LEAK = "query_scope_leak"


@dataclass
class TenantViolation:
    """Record of a tenant isolation violation."""
    violation_type: TenantViolationType
    message: str
    source_project: Optional[str] = None
    target_project: Optional[str] = None
    node_uid: Optional[str] = None
    relationship_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary for logging/serialization."""
        return {
            "type": self.violation_type.value,
            "message": self.message,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "node_uid": self.node_uid,
            "relationship_type": self.relationship_type,
            "details": self.details,
        }


@dataclass
class TenantValidationResult:
    """Result of tenant isolation validation."""
    valid: bool
    violations: List[TenantViolation] = field(default_factory=list)
    nodes_checked: int = 0
    relationships_checked: int = 0

    def add_violation(self, violation: TenantViolation) -> None:
        """Add a violation and mark as invalid."""
        self.violations.append(violation)
        self.valid = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "nodes_checked": self.nodes_checked,
            "relationships_checked": self.relationships_checked,
        }


# Schema constraint queries for Neo4j
SCHEMA_CONSTRAINTS = [
    # Composite uniqueness: (project, uid) must be unique per node
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE (n.project, n.uid) IS UNIQUE",
    # Index on project for fast tenant-scoped queries
    "CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.project)",
    # Index for File nodes (frequently queried)
    "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.project)",
    # Index for Class nodes
    "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.project)",
    # Index for Function nodes
    "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.project)",
    # Index for Document nodes
    "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.project)",
]


def get_schema_constraints() -> List[str]:
    """Return list of schema constraint queries for tenant isolation."""
    return SCHEMA_CONSTRAINTS.copy()


def build_project_scoped_query(
    base_query: str,
    project_name: str,
    project_param: str = "project"
) -> Tuple[str, Dict[str, Any]]:
    """
    Ensure a Cypher query is properly scoped to a project.

    This is a guard function that validates the query includes project filtering.
    It does NOT modify the query - it raises an error if the query lacks scoping.

    Args:
        base_query: The Cypher query to validate
        project_name: The project name to scope to
        project_param: The parameter name for project in the query

    Returns:
        Tuple of (query, params) with project parameter added

    Raises:
        ValueError: If query appears to lack project scoping
    """
    # Check if query has project filtering
    project_patterns = [
        r'\.\s*project\s*=',  # .project =
        r'\{\s*project\s*:',  # {project:
        r'WHERE.*project',    # WHERE ... project
        r'MATCH.*project',    # MATCH with project in property
    ]

    has_project_scope = any(re.search(p, base_query, re.IGNORECASE) for p in project_patterns)

    if not has_project_scope:
        logger.warning(f"Query may lack project scoping: {base_query[:100]}...")
        raise ValueError(
            f"Query must include project scoping. Add 'WHERE n.project = ${project_param}' "
            f"or equivalent to ensure tenant isolation."
        )

    params = {project_param: project_name}
    return base_query, params


def validate_node_has_project(node: Dict[str, Any]) -> Optional[TenantViolation]:
    """
    Validate that a node has a project property.

    Args:
        node: Node dictionary with properties

    Returns:
        TenantViolation if node lacks project, None otherwise
    """
    if "project" not in node or not node.get("project"):
        return TenantViolation(
            violation_type=TenantViolationType.MISSING_PROJECT,
            message="Node is missing required 'project' property",
            node_uid=node.get("uid"),
            details={"node_labels": node.get("labels", [])},
        )
    return None


def validate_relationship_projects(
    start_project: Optional[str],
    end_project: Optional[str],
    relationship_type: str,
    start_uid: str,
    end_uid: str,
) -> Optional[TenantViolation]:
    """
    Validate that a relationship does not cross project boundaries.

    Args:
        start_project: Project of the start node
        end_project: Project of the end node
        relationship_type: Type of the relationship
        start_uid: UID of the start node
        end_uid: UID of the end node

    Returns:
        TenantViolation if cross-project edge detected, None otherwise
    """
    if not start_project or not end_project:
        return TenantViolation(
            violation_type=TenantViolationType.MISSING_PROJECT,
            message="Relationship endpoint missing project property",
            node_uid=start_uid if not start_project else end_uid,
            relationship_type=relationship_type,
        )

    if start_project != end_project:
        return TenantViolation(
            violation_type=TenantViolationType.CROSS_PROJECT_EDGE,
            message=f"Cross-project edge detected: {start_project} -> {end_project}",
            source_project=start_project,
            target_project=end_project,
            relationship_type=relationship_type,
            details={
                "start_uid": start_uid,
                "end_uid": end_uid,
            },
        )

    return None


def create_node_with_project(
    labels: List[str],
    properties: Dict[str, Any],
    project_name: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a MERGE query that ensures project property is set.

    Args:
        labels: List of node labels
        properties: Node properties (must include 'uid')
        project_name: Project name to tag the node with

    Returns:
        Tuple of (query, params)

    Raises:
        ValueError: If properties missing 'uid'
    """
    if "uid" not in properties:
        raise ValueError("Node properties must include 'uid'")

    # Ensure project is in properties
    properties = properties.copy()
    properties["project"] = project_name

    label_str = ":".join(labels) if labels else "Node"
    prop_keys = list(properties.keys())

    # Build SET clause
    set_parts = [f"n.{k} = ${k}" for k in prop_keys]
    set_clause = ", ".join(set_parts)

    query = f"MERGE (n:{label_str} {{uid: $uid}}) SET {set_clause}"
    return query, properties


def create_relationship_with_guard(
    start_uid: str,
    end_uid: str,
    relationship_type: str,
    project_name: str,
    properties: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a relationship creation query with project guard.

    The query ensures both endpoints belong to the same project before
    creating the relationship.

    Args:
        start_uid: UID of the start node
        end_uid: UID of the end node
        relationship_type: Type of relationship to create
        project_name: Project name for validation
        properties: Optional relationship properties

    Returns:
        Tuple of (query, params)
    """
    props = properties.copy() if properties else {}
    props["project"] = project_name  # Tag relationship with project too

    # Build relationship property string
    if props:
        prop_parts = [f"{k}: ${k}" for k in props.keys()]
        prop_str = " {" + ", ".join(prop_parts) + "}"
    else:
        prop_str = ""

    # Query that guards against cross-project edges
    query = f"""
    MATCH (a {{uid: $start_uid, project: $project}})
    MATCH (b {{uid: $end_uid, project: $project}})
    MERGE (a)-[r:{relationship_type}{prop_str}]->(b)
    RETURN r
    """

    params = {
        "start_uid": start_uid,
        "end_uid": end_uid,
        "project": project_name,
        **props,
    }

    return query, params


def check_cross_project_edges(session, project_name: str) -> TenantValidationResult:
    """
    Check for any cross-project edges in the database.

    This is an integrity check that should be run periodically or after
    bulk operations to ensure no cross-tenant data leakage.

    Args:
        session: Neo4j session
        project_name: Project to check

    Returns:
        TenantValidationResult with any violations found
    """
    result = TenantValidationResult(valid=True)

    # Query to find cross-project edges involving this project
    query = """
    MATCH (a {project: $project})-[r]->(b)
    WHERE a.project <> b.project
    RETURN a.uid as start_uid, a.project as start_project,
           type(r) as rel_type,
           b.uid as end_uid, b.project as end_project
    LIMIT 100
    """

    records = session.run(query, {"project": project_name})

    for record in records:
        result.relationships_checked += 1
        violation = validate_relationship_projects(
            start_project=record["start_project"],
            end_project=record["end_project"],
            relationship_type=record["rel_type"],
            start_uid=record["start_uid"],
            end_uid=record["end_uid"],
        )
        if violation:
            result.add_violation(violation)
            logger.warning(f"Cross-project edge violation: {violation.message}")

    # Also check for incoming edges from other projects
    query_incoming = """
    MATCH (a)-[r]->(b {project: $project})
    WHERE a.project <> b.project
    RETURN a.uid as start_uid, a.project as start_project,
           type(r) as rel_type,
           b.uid as end_uid, b.project as end_project
    LIMIT 100
    """

    records_incoming = session.run(query_incoming, {"project": project_name})

    for record in records_incoming:
        result.relationships_checked += 1
        violation = validate_relationship_projects(
            start_project=record["start_project"],
            end_project=record["end_project"],
            relationship_type=record["rel_type"],
            start_uid=record["start_uid"],
            end_uid=record["end_uid"],
        )
        if violation:
            result.add_violation(violation)
            logger.warning(f"Cross-project edge violation: {violation.message}")

    return result


def check_nodes_without_project(session, limit: int = 100) -> TenantValidationResult:
    """
    Find nodes that are missing the project property.

    Args:
        session: Neo4j session
        limit: Maximum number of violations to return

    Returns:
        TenantValidationResult with any violations found
    """
    result = TenantValidationResult(valid=True)

    query = """
    MATCH (n:Node)
    WHERE n.project IS NULL
    RETURN n.uid as uid, labels(n) as labels
    LIMIT $limit
    """

    records = session.run(query, {"limit": limit})

    for record in records:
        result.nodes_checked += 1
        violation = TenantViolation(
            violation_type=TenantViolationType.MISSING_PROJECT,
            message="Node is missing required 'project' property",
            node_uid=record["uid"],
            details={"labels": record["labels"]},
        )
        result.add_violation(violation)
        logger.warning(f"Node without project: {record['uid']}")

    return result


def run_tenant_integrity_check(session, project_name: str) -> TenantValidationResult:
    """
    Run full tenant isolation integrity check.

    Checks for:
    1. Nodes missing project property
    2. Cross-project edges

    Args:
        session: Neo4j session
        project_name: Project to check

    Returns:
        TenantValidationResult with all violations found
    """
    result = TenantValidationResult(valid=True)

    # Check for nodes without project
    orphan_result = check_nodes_without_project(session)
    result.nodes_checked = orphan_result.nodes_checked
    for violation in orphan_result.violations:
        result.add_violation(violation)

    # Check for cross-project edges
    edge_result = check_cross_project_edges(session, project_name)
    result.relationships_checked = edge_result.relationships_checked
    for violation in edge_result.violations:
        result.add_violation(violation)

    logger.info(
        f"Tenant integrity check complete: valid={result.valid}, "
        f"nodes_checked={result.nodes_checked}, "
        f"relationships_checked={result.relationships_checked}, "
        f"violations={len(result.violations)}"
    )

    return result
