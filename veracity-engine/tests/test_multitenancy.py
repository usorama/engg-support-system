"""
Tests for Multitenancy Isolation (STORY-006).

Tests cover:
1. Project name validation (updated format)
2. Query guard functions
3. Cross-project edge validation
4. Node validation
5. Tenant violation reporting
"""
import pytest
from unittest.mock import MagicMock, patch

from core.validation import validate_project_name, MAX_PROJECT_NAME_LENGTH
from core.multitenancy import (
    TenantViolationType,
    TenantViolation,
    TenantValidationResult,
    get_schema_constraints,
    build_project_scoped_query,
    validate_node_has_project,
    validate_relationship_projects,
    create_node_with_project,
    create_relationship_with_guard,
)


class TestProjectNameValidation:
    """Tests for project name validation."""

    def test_valid_lowercase_name(self):
        """Simple lowercase name should pass."""
        assert validate_project_name("myproject") == "myproject"

    def test_valid_name_with_numbers(self):
        """Name with numbers should pass."""
        assert validate_project_name("project123") == "project123"

    def test_valid_name_with_underscore(self):
        """Name with underscore should pass."""
        assert validate_project_name("my_project") == "my_project"

    def test_valid_name_with_hyphen(self):
        """Name with hyphen should pass."""
        assert validate_project_name("my-project") == "my-project"

    def test_valid_name_with_dot(self):
        """Name with dot should pass."""
        assert validate_project_name("my.project") == "my.project"

    def test_uppercase_normalized_to_lowercase(self):
        """Uppercase letters should be normalized to lowercase."""
        assert validate_project_name("MyProject") == "myproject"

    def test_mixed_case_normalized(self):
        """Mixed case should be normalized."""
        assert validate_project_name("My-Project_123") == "my-project_123"

    def test_empty_name_rejected(self):
        """Empty name should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_project_name("")

    def test_max_length_exceeded_rejected(self):
        """Name exceeding max length should be rejected."""
        long_name = "a" * (MAX_PROJECT_NAME_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_project_name(long_name)

    def test_exactly_max_length_accepted(self):
        """Name at exactly max length should pass."""
        exact_name = "a" * MAX_PROJECT_NAME_LENGTH
        assert validate_project_name(exact_name) == exact_name

    def test_consecutive_dots_rejected(self):
        """Consecutive dots (path traversal) should be rejected."""
        with pytest.raises(ValueError, match="consecutive dots"):
            validate_project_name("my..project")

    def test_null_byte_rejected(self):
        """Null bytes should be rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            validate_project_name("project\x00name")

    def test_starting_with_special_char_rejected(self):
        """Name starting with special character should be rejected."""
        with pytest.raises(ValueError, match="must start with"):
            validate_project_name("_project")
        with pytest.raises(ValueError, match="must start with"):
            validate_project_name("-project")
        with pytest.raises(ValueError, match="must start with"):
            validate_project_name(".project")

    def test_spaces_rejected(self):
        """Name with spaces should be rejected."""
        with pytest.raises(ValueError, match="must start with"):
            validate_project_name("my project")


class TestTenantViolation:
    """Tests for TenantViolation dataclass."""

    def test_violation_creation(self):
        """Should create violation with required fields."""
        violation = TenantViolation(
            violation_type=TenantViolationType.MISSING_PROJECT,
            message="Test message"
        )
        assert violation.violation_type == TenantViolationType.MISSING_PROJECT
        assert violation.message == "Test message"
        assert violation.source_project is None

    def test_violation_to_dict(self):
        """Should convert to dictionary correctly."""
        violation = TenantViolation(
            violation_type=TenantViolationType.CROSS_PROJECT_EDGE,
            message="Cross project detected",
            source_project="project_a",
            target_project="project_b",
        )
        d = violation.to_dict()
        assert d["type"] == "cross_project_edge"
        assert d["source_project"] == "project_a"
        assert d["target_project"] == "project_b"


class TestTenantValidationResult:
    """Tests for TenantValidationResult."""

    def test_initial_state_valid(self):
        """Result should start valid."""
        result = TenantValidationResult(valid=True)
        assert result.valid is True
        assert result.violations == []

    def test_add_violation_marks_invalid(self):
        """Adding a violation should mark result as invalid."""
        result = TenantValidationResult(valid=True)
        violation = TenantViolation(
            violation_type=TenantViolationType.MISSING_PROJECT,
            message="Test"
        )
        result.add_violation(violation)
        assert result.valid is False
        assert len(result.violations) == 1

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        result = TenantValidationResult(valid=True, nodes_checked=10)
        d = result.to_dict()
        assert d["valid"] is True
        assert d["nodes_checked"] == 10
        assert d["violations"] == []


class TestSchemaConstraints:
    """Tests for schema constraint utilities."""

    def test_get_schema_constraints_returns_list(self):
        """Should return a list of constraint queries."""
        constraints = get_schema_constraints()
        assert isinstance(constraints, list)
        assert len(constraints) > 0

    def test_constraints_include_project_uniqueness(self):
        """Should include composite uniqueness constraint."""
        constraints = get_schema_constraints()
        has_uniqueness = any("UNIQUE" in c and "project" in c for c in constraints)
        assert has_uniqueness, "Missing composite uniqueness constraint"

    def test_constraints_include_project_index(self):
        """Should include index on project."""
        constraints = get_schema_constraints()
        has_index = any("INDEX" in c and "project" in c for c in constraints)
        assert has_index, "Missing project index"


class TestQueryGuards:
    """Tests for query guard functions."""

    def test_scoped_query_valid(self):
        """Query with project scope should pass."""
        query = "MATCH (n) WHERE n.project = $project RETURN n"
        validated_query, params = build_project_scoped_query(query, "myproject")
        assert params["project"] == "myproject"

    def test_scoped_query_property_filter(self):
        """Query with project in property filter should pass."""
        query = "MATCH (n {project: $project}) RETURN n"
        validated_query, params = build_project_scoped_query(query, "myproject")
        assert params["project"] == "myproject"

    def test_unscoped_query_rejected(self):
        """Query without project scope should be rejected."""
        query = "MATCH (n) RETURN n"
        with pytest.raises(ValueError, match="must include project scoping"):
            build_project_scoped_query(query, "myproject")

    def test_custom_param_name(self):
        """Should support custom parameter names."""
        query = "MATCH (n) WHERE n.project = $tenant_id RETURN n"
        validated_query, params = build_project_scoped_query(
            query, "myproject", project_param="tenant_id"
        )
        assert params["tenant_id"] == "myproject"


class TestNodeValidation:
    """Tests for node validation functions."""

    def test_node_with_project_passes(self):
        """Node with project property should pass."""
        node = {"uid": "test:123", "project": "myproject"}
        violation = validate_node_has_project(node)
        assert violation is None

    def test_node_without_project_fails(self):
        """Node without project property should fail."""
        node = {"uid": "test:123"}
        violation = validate_node_has_project(node)
        assert violation is not None
        assert violation.violation_type == TenantViolationType.MISSING_PROJECT

    def test_node_with_empty_project_fails(self):
        """Node with empty project property should fail."""
        node = {"uid": "test:123", "project": ""}
        violation = validate_node_has_project(node)
        assert violation is not None


class TestRelationshipValidation:
    """Tests for relationship validation functions."""

    def test_same_project_passes(self):
        """Relationship between same-project nodes should pass."""
        violation = validate_relationship_projects(
            start_project="project_a",
            end_project="project_a",
            relationship_type="CALLS",
            start_uid="a:1",
            end_uid="a:2",
        )
        assert violation is None

    def test_cross_project_fails(self):
        """Relationship crossing project boundary should fail."""
        violation = validate_relationship_projects(
            start_project="project_a",
            end_project="project_b",
            relationship_type="CALLS",
            start_uid="a:1",
            end_uid="b:1",
        )
        assert violation is not None
        assert violation.violation_type == TenantViolationType.CROSS_PROJECT_EDGE
        assert violation.source_project == "project_a"
        assert violation.target_project == "project_b"

    def test_missing_project_fails(self):
        """Relationship with missing project should fail."""
        violation = validate_relationship_projects(
            start_project="project_a",
            end_project=None,
            relationship_type="CALLS",
            start_uid="a:1",
            end_uid="x:1",
        )
        assert violation is not None
        assert violation.violation_type == TenantViolationType.MISSING_PROJECT


class TestNodeCreation:
    """Tests for node creation with project."""

    def test_create_node_includes_project(self):
        """Created node should include project property."""
        query, params = create_node_with_project(
            labels=["File", "Node"],
            properties={"uid": "test:file.py", "name": "file.py"},
            project_name="myproject",
        )
        assert params["project"] == "myproject"
        assert "project" in query

    def test_create_node_requires_uid(self):
        """Should require uid in properties."""
        with pytest.raises(ValueError, match="must include 'uid'"):
            create_node_with_project(
                labels=["File"],
                properties={"name": "file.py"},
                project_name="myproject",
            )

    def test_create_node_preserves_properties(self):
        """Should preserve all input properties."""
        query, params = create_node_with_project(
            labels=["Class"],
            properties={"uid": "test:MyClass", "name": "MyClass", "line": 10},
            project_name="myproject",
        )
        assert params["uid"] == "test:MyClass"
        assert params["name"] == "MyClass"
        assert params["line"] == 10
        assert params["project"] == "myproject"


class TestRelationshipCreation:
    """Tests for relationship creation with guard."""

    def test_create_relationship_has_guard(self):
        """Created relationship query should have project guard."""
        query, params = create_relationship_with_guard(
            start_uid="test:a",
            end_uid="test:b",
            relationship_type="CALLS",
            project_name="myproject",
        )
        # Query should match both nodes with project filter
        assert "project: $project" in query or "project = $project" in query.replace(" ", "")
        assert params["project"] == "myproject"
        assert params["start_uid"] == "test:a"
        assert params["end_uid"] == "test:b"

    def test_create_relationship_with_properties(self):
        """Should include relationship properties."""
        query, params = create_relationship_with_guard(
            start_uid="test:a",
            end_uid="test:b",
            relationship_type="CALLS",
            project_name="myproject",
            properties={"line": 42},
        )
        assert params["line"] == 42


class TestEnumValues:
    """Tests for violation type enum values."""

    def test_violation_types_have_string_values(self):
        """All violation types should have string values for serialization."""
        for vtype in TenantViolationType:
            assert isinstance(vtype.value, str)

    def test_violation_types_unique(self):
        """All violation type values should be unique."""
        values = [vtype.value for vtype in TenantViolationType]
        assert len(values) == len(set(values))
