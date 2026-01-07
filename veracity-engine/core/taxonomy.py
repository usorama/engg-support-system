"""
Taxonomy Expansion Module (STORY-014).

Extends KG taxonomy to cover:
1. API endpoints (OpenAPI, FastAPI, Flask)
2. Contracts/schemas (Protobuf, JSON Schema)
3. Services and methods
4. Deterministic extraction with evidence backing

All extractions are evidence-based (no inference without source).
"""
import ast
import hashlib
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Supported formats
SUPPORTED_API_FORMATS = [".yaml", ".yml", ".json"]
SUPPORTED_CONTRACT_FORMATS = [".proto", ".json"]

# File patterns for detection
OPENAPI_PATTERNS = ["openapi", "swagger", "api-spec", "api_spec"]
PROTOBUF_EXTENSION = ".proto"


class NodeType(Enum):
    """Extended node types for KG taxonomy."""
    # Original types
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    DOCUMENT = "Document"
    # New types
    API = "API"
    CONTRACT = "Contract"
    SERVICE = "Service"
    METHOD = "Method"
    ENDPOINT = "Endpoint"
    SCHEMA = "Schema"


class RelationType(Enum):
    """Relationship types between nodes."""
    DEFINES = "DEFINES"
    CALLS = "CALLS"
    DEPENDS_ON = "DEPENDS_ON"
    # New types
    DEFINES_API = "DEFINES_API"
    IMPLEMENTS_CONTRACT = "IMPLEMENTS_CONTRACT"
    HAS_METHOD = "HAS_METHOD"
    HAS_ENDPOINT = "HAS_ENDPOINT"
    USES_SCHEMA = "USES_SCHEMA"


@dataclass
class APIEndpoint:
    """
    An API endpoint extracted from source.

    Attributes:
        path: URL path (e.g., /api/users/{id})
        method: HTTP method (GET, POST, etc.)
        operation_id: Unique operation identifier
        source_file: Source file path
        start_line: Line number in source
        description: Optional description
        parameters: Optional parameter list
    """
    path: str
    method: str
    operation_id: str
    source_file: str
    start_line: int
    description: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    responses: List[str] = field(default_factory=list)

    @property
    def uid(self) -> str:
        """Generate deterministic UID."""
        return generate_api_uid(self.source_file, self.path, self.method)

    def to_dict(self) -> Dict:
        return {
            "uid": self.uid,
            "path": self.path,
            "method": self.method,
            "operation_id": self.operation_id,
            "source_file": self.source_file,
            "start_line": self.start_line,
            "description": self.description,
            "parameters": self.parameters,
            "responses": self.responses,
        }


@dataclass
class Contract:
    """
    A contract/schema extracted from source.

    Attributes:
        name: Contract/schema name
        contract_type: Type (protobuf_message, json_schema, etc.)
        source_file: Source file path
        start_line: Line number in source
        fields: List of field names
        description: Optional description
    """
    name: str
    contract_type: str
    source_file: str
    start_line: int
    fields: List[str] = field(default_factory=list)
    description: Optional[str] = None

    @property
    def uid(self) -> str:
        """Generate deterministic UID."""
        return generate_contract_uid(self.source_file, self.name)

    def to_dict(self) -> Dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "contract_type": self.contract_type,
            "source_file": self.source_file,
            "start_line": self.start_line,
            "fields": self.fields,
            "description": self.description,
        }


@dataclass
class ServiceNode:
    """
    A service definition.

    Attributes:
        name: Service name
        source_file: Source file path
        methods: List of method names
    """
    name: str
    source_file: str
    start_line: int
    methods: List[str] = field(default_factory=list)

    @property
    def uid(self) -> str:
        """Generate deterministic UID."""
        content = f"{self.source_file}::{self.name}"
        return f"service::{hashlib.sha256(content.encode()).hexdigest()[:12]}"

    def to_dict(self) -> Dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "source_file": self.source_file,
            "start_line": self.start_line,
            "methods": self.methods,
        }


@dataclass
class MethodNode:
    """
    A method definition within a service or class.

    Attributes:
        name: Method name
        parent: Parent service/class name
        source_file: Source file path
    """
    name: str
    parent: str
    source_file: str
    start_line: int
    signature: Optional[str] = None

    @property
    def uid(self) -> str:
        """Generate deterministic UID."""
        content = f"{self.source_file}::{self.parent}::{self.name}"
        return f"method::{hashlib.sha256(content.encode()).hexdigest()[:12]}"

    def to_dict(self) -> Dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "parent": self.parent,
            "source_file": self.source_file,
            "start_line": self.start_line,
            "signature": self.signature,
        }


@dataclass
class TaxonomyConfig:
    """Configuration for taxonomy extraction."""
    extract_apis: bool = True
    extract_contracts: bool = True
    extract_services: bool = True
    api_file_patterns: List[str] = field(default_factory=lambda: [".yaml", ".yml", ".json", ".py"])
    contract_file_patterns: List[str] = field(default_factory=lambda: [".proto", ".json"])
    python_frameworks: List[str] = field(default_factory=lambda: ["fastapi", "flask"])


@dataclass
class TaxonomyResult:
    """
    Complete taxonomy extraction result.

    Attributes:
        endpoints: Extracted API endpoints
        contracts: Extracted contracts/schemas
        services: Extracted services
        methods: Extracted methods
    """
    endpoints: List[APIEndpoint]
    contracts: List[Contract]
    services: List[ServiceNode]
    methods: List[MethodNode]

    def to_dict(self) -> Dict:
        return {
            "endpoints": [e.to_dict() for e in self.endpoints],
            "contracts": [c.to_dict() for c in self.contracts],
            "services": [s.to_dict() for s in self.services],
            "methods": [m.to_dict() for m in self.methods],
        }


def generate_api_uid(source_file: str, path: str, method: str) -> str:
    """
    Generate deterministic UID for API endpoint.

    Format: api::<hash>
    Hash is SHA256 of source_file::path::method
    """
    content = f"{source_file}::{path}::{method}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"api::{hash_val}"


def generate_contract_uid(source_file: str, name: str) -> str:
    """
    Generate deterministic UID for contract/schema.

    Format: contract::<hash>
    Hash is SHA256 of source_file::name
    """
    content = f"{source_file}::{name}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"contract::{hash_val}"


def is_openapi_file(file_path: str) -> bool:
    """Check if file is likely an OpenAPI/Swagger spec."""
    name = os.path.basename(file_path).lower()
    stem = Path(file_path).stem.lower()

    # Check extension
    if not any(file_path.lower().endswith(ext) for ext in [".yaml", ".yml", ".json"]):
        return False

    # Check patterns
    for pattern in OPENAPI_PATTERNS:
        if pattern in stem:
            return True

    return False


def is_protobuf_file(file_path: str) -> bool:
    """Check if file is a Protocol Buffers definition."""
    return file_path.lower().endswith(PROTOBUF_EXTENSION)


def extract_openapi_endpoints(file_path: str) -> List[APIEndpoint]:
    """
    Extract API endpoints from OpenAPI/Swagger specification.

    Args:
        file_path: Path to OpenAPI YAML/JSON file

    Returns:
        List of APIEndpoint objects
    """
    if not YAML_AVAILABLE:
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    try:
        spec = yaml.safe_load(content)
    except yaml.YAMLError:
        return []

    if not isinstance(spec, dict):
        return []

    endpoints = []
    paths = spec.get("paths", {})

    if not isinstance(paths, dict):
        return []

    rel_path = file_path  # Will be made relative by caller

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
            operation = path_item.get(method)
            if not operation:
                continue

            operation_id = operation.get("operationId", f"{method}_{path}")
            description = operation.get("summary") or operation.get("description")

            # Extract parameter names
            params = []
            for param in operation.get("parameters", []):
                if isinstance(param, dict) and "name" in param:
                    params.append(param["name"])

            # Extract response codes
            responses = []
            for code in operation.get("responses", {}).keys():
                responses.append(str(code))

            endpoints.append(APIEndpoint(
                path=path,
                method=method.upper(),
                operation_id=operation_id,
                source_file=rel_path,
                start_line=1,  # YAML doesn't provide line numbers easily
                description=description,
                parameters=params,
                responses=responses,
            ))

    return endpoints


def extract_protobuf_definitions(file_path: str) -> List[Contract]:
    """
    Extract message and service definitions from Protocol Buffers file.

    Uses regex-based parsing (no protobuf compiler required).

    Args:
        file_path: Path to .proto file

    Returns:
        List of Contract objects
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    contracts = []
    rel_path = file_path

    # Extract message definitions
    message_pattern = r'message\s+(\w+)\s*\{([^}]*)\}'
    for match in re.finditer(message_pattern, content, re.MULTILINE | re.DOTALL):
        name = match.group(1)
        body = match.group(2)
        start_pos = match.start()
        line_num = content[:start_pos].count('\n') + 1

        # Extract field names from body
        fields = []
        field_pattern = r'(\w+)\s+(\w+)\s*='
        for field_match in re.finditer(field_pattern, body):
            fields.append(field_match.group(2))

        contracts.append(Contract(
            name=name,
            contract_type="protobuf_message",
            source_file=rel_path,
            start_line=line_num,
            fields=fields,
        ))

    # Extract service definitions
    service_pattern = r'service\s+(\w+)\s*\{([^}]*)\}'
    for match in re.finditer(service_pattern, content, re.MULTILINE | re.DOTALL):
        name = match.group(1)
        body = match.group(2)
        start_pos = match.start()
        line_num = content[:start_pos].count('\n') + 1

        # Extract rpc method names
        methods = []
        rpc_pattern = r'rpc\s+(\w+)'
        for rpc_match in re.finditer(rpc_pattern, body):
            methods.append(rpc_match.group(1))

        contracts.append(Contract(
            name=name,
            contract_type="protobuf_service",
            source_file=rel_path,
            start_line=line_num,
            fields=methods,  # Using fields for method names
            description=f"gRPC service with {len(methods)} methods",
        ))

    return contracts


def extract_fastapi_routes(file_path: str) -> List[APIEndpoint]:
    """
    Extract API endpoints from FastAPI application.

    Args:
        file_path: Path to Python file

    Returns:
        List of APIEndpoint objects
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    endpoints = []
    rel_path = file_path

    # Look for decorated functions
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            # Check for @app.get, @app.post, etc.
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr.upper()
                    if method in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
                        # Get the path argument
                        path = "/"
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Constant):
                                path = decorator.args[0].value

                        endpoints.append(APIEndpoint(
                            path=path,
                            method=method,
                            operation_id=node.name,
                            source_file=rel_path,
                            start_line=node.lineno,
                        ))

    return endpoints


def extract_flask_routes(file_path: str) -> List[APIEndpoint]:
    """
    Extract API endpoints from Flask application.

    Args:
        file_path: Path to Python file

    Returns:
        List of APIEndpoint objects
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    endpoints = []
    rel_path = file_path

    # Look for @app.route decorators
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "route":
                        # Get the path argument
                        path = "/"
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Constant):
                                path = decorator.args[0].value

                        # Get methods from keyword argument
                        methods = ["GET"]  # Default
                        for kw in decorator.keywords:
                            if kw.arg == "methods":
                                if isinstance(kw.value, ast.List):
                                    methods = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            methods.append(elt.value.upper())

                        # Create endpoint for each method
                        for method in methods:
                            endpoints.append(APIEndpoint(
                                path=path,
                                method=method,
                                operation_id=node.name,
                                source_file=rel_path,
                                start_line=node.lineno,
                            ))

    return endpoints


def extract_taxonomy(
    root_dir: str,
    config: Optional[TaxonomyConfig] = None,
) -> TaxonomyResult:
    """
    Extract complete taxonomy from a directory.

    Args:
        root_dir: Root directory to scan
        config: Optional configuration

    Returns:
        TaxonomyResult with all extracted entities
    """
    if config is None:
        config = TaxonomyConfig()

    root_path = Path(root_dir)
    endpoints: List[APIEndpoint] = []
    contracts: List[Contract] = []
    services: List[ServiceNode] = []
    methods: List[MethodNode] = []

    # Scan for files
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(root_path))
        abs_path = str(file_path)

        # Extract APIs from OpenAPI specs
        if config.extract_apis and is_openapi_file(abs_path):
            extracted = extract_openapi_endpoints(abs_path)
            for ep in extracted:
                ep.source_file = rel_path
            endpoints.extend(extracted)

        # Extract APIs from Python files (FastAPI/Flask)
        if config.extract_apis and abs_path.endswith(".py"):
            # Try FastAPI
            fastapi_eps = extract_fastapi_routes(abs_path)
            for ep in fastapi_eps:
                ep.source_file = rel_path
            endpoints.extend(fastapi_eps)

            # Try Flask
            flask_eps = extract_flask_routes(abs_path)
            for ep in flask_eps:
                ep.source_file = rel_path
            endpoints.extend(flask_eps)

        # Extract contracts from protobuf files
        if config.extract_contracts and is_protobuf_file(abs_path):
            extracted = extract_protobuf_definitions(abs_path)
            for c in extracted:
                c.source_file = rel_path
            contracts.extend(extracted)

    # Sort for determinism
    endpoints.sort(key=lambda e: (e.source_file, e.path, e.method))
    contracts.sort(key=lambda c: (c.source_file, c.name))
    services.sort(key=lambda s: (s.source_file, s.name))
    methods.sort(key=lambda m: (m.source_file, m.parent, m.name))

    return TaxonomyResult(
        endpoints=endpoints,
        contracts=contracts,
        services=services,
        methods=methods,
    )
