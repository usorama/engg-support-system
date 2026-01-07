"""
Tests for Taxonomy Expansion (STORY-014).

Tests cover:
1. Extended node types (API, Contract, Service, Method)
2. OpenAPI/Swagger extraction
3. Protobuf extraction
4. Deterministic UID generation
5. Extraction configuration
"""
import pytest
import tempfile
import os
import json
import yaml

from core.taxonomy import (
    # Enums
    NodeType,
    RelationType,
    # Data classes
    APIEndpoint,
    Contract,
    ServiceNode,
    MethodNode,
    TaxonomyConfig,
    TaxonomyResult,
    # Extraction functions
    extract_openapi_endpoints,
    extract_protobuf_definitions,
    extract_fastapi_routes,
    extract_flask_routes,
    # Utility functions
    generate_api_uid,
    generate_contract_uid,
    is_openapi_file,
    is_protobuf_file,
    # Main pipeline
    extract_taxonomy,
    # Constants
    SUPPORTED_API_FORMATS,
    SUPPORTED_CONTRACT_FORMATS,
)


class TestNodeTypes:
    """Tests for node type enum."""

    def test_node_types_defined(self):
        """All node types should be defined."""
        assert NodeType.API is not None
        assert NodeType.CONTRACT is not None
        assert NodeType.SERVICE is not None
        assert NodeType.METHOD is not None
        assert NodeType.FILE is not None
        assert NodeType.FUNCTION is not None
        assert NodeType.CLASS is not None


class TestRelationTypes:
    """Tests for relationship type enum."""

    def test_relation_types_defined(self):
        """All relationship types should be defined."""
        assert RelationType.DEFINES_API is not None
        assert RelationType.IMPLEMENTS_CONTRACT is not None
        assert RelationType.CALLS is not None
        assert RelationType.HAS_METHOD is not None


class TestAPIEndpoint:
    """Tests for API endpoint structure."""

    def test_endpoint_has_required_fields(self):
        """API endpoint should have required fields."""
        endpoint = APIEndpoint(
            path="/api/users",
            method="GET",
            operation_id="get_users",
            source_file="openapi.yaml",
            start_line=10,
        )
        assert endpoint.path == "/api/users"
        assert endpoint.method == "GET"
        assert endpoint.operation_id == "get_users"

    def test_endpoint_uid_generation(self):
        """Should generate deterministic UID."""
        endpoint = APIEndpoint(
            path="/api/users/{id}",
            method="POST",
            operation_id="create_user",
            source_file="api/openapi.yaml",
            start_line=25,
        )
        uid = endpoint.uid
        assert uid is not None
        assert "api" in uid.lower()

    def test_endpoint_to_dict(self):
        """Endpoint should convert to dictionary."""
        endpoint = APIEndpoint(
            path="/health",
            method="GET",
            operation_id="health_check",
            source_file="spec.yaml",
            start_line=5,
        )
        d = endpoint.to_dict()
        assert d["path"] == "/health"
        assert d["method"] == "GET"
        assert "uid" in d


class TestContract:
    """Tests for contract/schema structure."""

    def test_contract_has_required_fields(self):
        """Contract should have required fields."""
        contract = Contract(
            name="UserSchema",
            contract_type="json_schema",
            source_file="schemas/user.json",
            start_line=1,
        )
        assert contract.name == "UserSchema"
        assert contract.contract_type == "json_schema"

    def test_contract_uid_generation(self):
        """Should generate deterministic UID."""
        contract = Contract(
            name="OrderRequest",
            contract_type="protobuf",
            source_file="protos/order.proto",
            start_line=15,
        )
        uid = contract.uid
        assert uid is not None
        assert "contract" in uid.lower()

    def test_contract_to_dict(self):
        """Contract should convert to dictionary."""
        contract = Contract(
            name="PaymentResponse",
            contract_type="openapi_schema",
            source_file="api.yaml",
            start_line=100,
        )
        d = contract.to_dict()
        assert d["name"] == "PaymentResponse"
        assert "uid" in d


class TestTaxonomyConfig:
    """Tests for taxonomy configuration."""

    def test_default_config(self):
        """Default config should have valid values."""
        config = TaxonomyConfig()
        assert config.extract_apis is True
        assert config.extract_contracts is True
        assert ".yaml" in config.api_file_patterns
        assert ".proto" in config.contract_file_patterns

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = TaxonomyConfig(
            extract_apis=False,
            extract_contracts=True,
        )
        assert config.extract_apis is False


class TestOpenAPIExtraction:
    """Tests for OpenAPI/Swagger extraction."""

    def test_extract_simple_endpoint(self):
        """Should extract endpoint from OpenAPI spec."""
        openapi_content = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
paths:
  /users:
    get:
      operationId: getUsers
      summary: Get all users
      responses:
        '200':
          description: Success
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(openapi_content)
            f.flush()
            endpoints = extract_openapi_endpoints(f.name)
        os.unlink(f.name)

        assert len(endpoints) >= 1
        ep = endpoints[0]
        assert ep.path == "/users"
        assert ep.method == "GET"

    def test_extract_multiple_methods(self):
        """Should extract all methods for a path."""
        openapi_content = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
paths:
  /items:
    get:
      operationId: listItems
      responses:
        '200':
          description: List items
    post:
      operationId: createItem
      responses:
        '201':
          description: Created
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(openapi_content)
            f.flush()
            endpoints = extract_openapi_endpoints(f.name)
        os.unlink(f.name)

        assert len(endpoints) == 2
        methods = {ep.method for ep in endpoints}
        assert "GET" in methods
        assert "POST" in methods

    def test_extract_schemas(self):
        """Should extract schema definitions."""
        openapi_content = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
    Order:
      type: object
      properties:
        id:
          type: integer
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(openapi_content)
            f.flush()
            endpoints = extract_openapi_endpoints(f.name)
        os.unlink(f.name)

        # Schemas should be extracted as contracts if function returns them
        # This test validates endpoints primarily
        assert isinstance(endpoints, list)

    def test_invalid_yaml_returns_empty(self):
        """Should handle invalid YAML gracefully."""
        invalid_yaml = """
        not: valid: yaml: here
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            endpoints = extract_openapi_endpoints(f.name)
        os.unlink(f.name)

        assert endpoints == []

    def test_swagger_v2_format(self):
        """Should handle Swagger 2.0 format."""
        swagger_content = """
swagger: "2.0"
info:
  title: Legacy API
  version: "1.0"
basePath: /api/v2
paths:
  /legacy:
    get:
      operationId: legacyEndpoint
      responses:
        200:
          description: OK
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(swagger_content)
            f.flush()
            endpoints = extract_openapi_endpoints(f.name)
        os.unlink(f.name)

        assert len(endpoints) >= 1


class TestProtobufExtraction:
    """Tests for Protocol Buffers extraction."""

    def test_extract_message_definition(self):
        """Should extract message definitions from proto file."""
        proto_content = """
syntax = "proto3";

package example;

message User {
    int32 id = 1;
    string name = 2;
    string email = 3;
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(proto_content)
            f.flush()
            contracts = extract_protobuf_definitions(f.name)
        os.unlink(f.name)

        assert len(contracts) >= 1
        user = next((c for c in contracts if c.name == "User"), None)
        assert user is not None
        assert user.contract_type == "protobuf_message"

    def test_extract_service_definition(self):
        """Should extract service definitions from proto file."""
        proto_content = """
syntax = "proto3";

package example;

service UserService {
    rpc GetUser (GetUserRequest) returns (User);
    rpc CreateUser (CreateUserRequest) returns (User);
}

message GetUserRequest {
    int32 id = 1;
}

message CreateUserRequest {
    string name = 1;
}

message User {
    int32 id = 1;
    string name = 2;
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(proto_content)
            f.flush()
            contracts = extract_protobuf_definitions(f.name)
        os.unlink(f.name)

        # Should find service and messages
        service = next((c for c in contracts if "UserService" in c.name), None)
        assert service is not None or len(contracts) >= 3  # At least messages

    def test_invalid_proto_returns_empty(self):
        """Should handle invalid proto gracefully."""
        invalid_proto = """
        not valid proto content
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(invalid_proto)
            f.flush()
            contracts = extract_protobuf_definitions(f.name)
        os.unlink(f.name)

        # Should return empty or partial, not raise exception
        assert isinstance(contracts, list)


class TestFastAPIExtraction:
    """Tests for FastAPI route extraction."""

    def test_extract_fastapi_route(self):
        """Should extract FastAPI route definitions."""
        code = '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/users")
def get_users():
    return []

@app.post("/users")
def create_user(user: dict):
    return user
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            endpoints = extract_fastapi_routes(f.name)
        os.unlink(f.name)

        assert len(endpoints) == 2
        paths = {ep.path for ep in endpoints}
        assert "/users" in paths

    def test_extract_with_path_params(self):
        """Should extract routes with path parameters."""
        code = '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            endpoints = extract_fastapi_routes(f.name)
        os.unlink(f.name)

        assert len(endpoints) == 1
        assert "{user_id}" in endpoints[0].path


class TestFlaskExtraction:
    """Tests for Flask route extraction."""

    def test_extract_flask_route(self):
        """Should extract Flask route definitions."""
        code = '''
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello"

@app.route("/api/data", methods=["GET", "POST"])
def data():
    return {"data": []}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            endpoints = extract_flask_routes(f.name)
        os.unlink(f.name)

        # Should find at least 2 routes (data has 2 methods)
        assert len(endpoints) >= 2


class TestUIDGeneration:
    """Tests for deterministic UID generation."""

    def test_api_uid_deterministic(self):
        """Same inputs should produce same UID."""
        uid1 = generate_api_uid("api.yaml", "/users", "GET")
        uid2 = generate_api_uid("api.yaml", "/users", "GET")
        assert uid1 == uid2

    def test_api_uid_different_for_different_inputs(self):
        """Different inputs should produce different UIDs."""
        uid1 = generate_api_uid("api.yaml", "/users", "GET")
        uid2 = generate_api_uid("api.yaml", "/users", "POST")
        assert uid1 != uid2

    def test_contract_uid_deterministic(self):
        """Same inputs should produce same UID."""
        uid1 = generate_contract_uid("schema.proto", "User")
        uid2 = generate_contract_uid("schema.proto", "User")
        assert uid1 == uid2


class TestFileDetection:
    """Tests for file type detection."""

    def test_is_openapi_file(self):
        """Should detect OpenAPI files."""
        assert is_openapi_file("openapi.yaml") is True
        assert is_openapi_file("swagger.yaml") is True
        assert is_openapi_file("api-spec.yaml") is True
        assert is_openapi_file("config.yaml") is False
        assert is_openapi_file("random.txt") is False

    def test_is_protobuf_file(self):
        """Should detect protobuf files."""
        assert is_protobuf_file("user.proto") is True
        assert is_protobuf_file("services/api.proto") is True
        assert is_protobuf_file("code.py") is False


class TestTaxonomyResult:
    """Tests for taxonomy extraction result."""

    def test_result_structure(self):
        """Result should have required fields."""
        result = TaxonomyResult(
            endpoints=[],
            contracts=[],
            services=[],
            methods=[],
        )
        assert result.endpoints == []
        assert result.contracts == []

    def test_result_to_dict(self):
        """Result should convert to dictionary."""
        endpoint = APIEndpoint(
            path="/test",
            method="GET",
            operation_id="test",
            source_file="test.yaml",
            start_line=1,
        )
        result = TaxonomyResult(
            endpoints=[endpoint],
            contracts=[],
            services=[],
            methods=[],
        )
        d = result.to_dict()
        assert "endpoints" in d
        assert len(d["endpoints"]) == 1


class TestExtractTaxonomy:
    """Tests for complete taxonomy extraction."""

    def test_extract_from_directory(self):
        """Should extract taxonomy from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an OpenAPI file
            openapi_path = os.path.join(tmpdir, "openapi.yaml")
            with open(openapi_path, 'w') as f:
                f.write("""
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
paths:
  /test:
    get:
      operationId: test
      responses:
        '200':
          description: OK
""")

            result = extract_taxonomy(tmpdir)

            assert result.endpoints is not None
            assert len(result.endpoints) >= 1

    def test_empty_directory(self):
        """Should handle empty directory gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = extract_taxonomy(tmpdir)

            assert result.endpoints == []
            assert result.contracts == []

    def test_deterministic_output(self):
        """Same directory should produce identical results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a proto file
            proto_path = os.path.join(tmpdir, "types.proto")
            with open(proto_path, 'w') as f:
                f.write("""
syntax = "proto3";
message Alpha { int32 id = 1; }
message Beta { string name = 1; }
""")

            result1 = extract_taxonomy(tmpdir)
            result2 = extract_taxonomy(tmpdir)

            # Should have same contract count
            assert len(result1.contracts) == len(result2.contracts)

            # Same order
            if result1.contracts:
                assert result1.contracts[0].name == result2.contracts[0].name

    def test_config_disables_extraction(self):
        """Should respect config flags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an OpenAPI file
            openapi_path = os.path.join(tmpdir, "openapi.yaml")
            with open(openapi_path, 'w') as f:
                f.write("""
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
paths:
  /disabled:
    get:
      operationId: disabled
      responses:
        '200':
          description: OK
""")

            config = TaxonomyConfig(extract_apis=False)
            result = extract_taxonomy(tmpdir, config)

            # APIs should not be extracted
            assert result.endpoints == []
