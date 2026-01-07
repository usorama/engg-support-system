"""
Evidence Packet Contract Module (STORY-011).

Defines the versioned schema for evidence packets and provides
validation, hashing, and audit logging utilities.

Schema Version: 1.0
- All outputs conform to this schema
- Validation fails hard on invalid packets
- Packet hashes are stable for identical inputs
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Schema version (major.minor format)
SCHEMA_VERSION = "1.0"

# Required fields for validation
REQUIRED_META_FIELDS = ["schema_version", "query_id", "timestamp", "project", "question"]
REQUIRED_CODE_RESULT_FIELDS = ["id", "type", "path", "name", "score"]
REQUIRED_DOC_RESULT_FIELDS = ["id", "path", "name", "score"]
REQUIRED_VERACITY_FIELDS = ["confidence_score", "is_stale", "faults"]


class ValidationError(Exception):
    """Raised when packet validation fails."""
    pass


@dataclass
class PacketMeta:
    """
    Metadata for evidence packet.

    Required fields:
    - schema_version: Version of the packet schema
    - query_id: Unique identifier for the query
    - timestamp: ISO format timestamp
    - project: Project name
    - question: Original query string
    """
    schema_version: str
    query_id: str
    timestamp: str
    project: str
    question: str
    mode: Optional[str] = None  # evidence_only or synthesis

    def to_dict(self) -> Dict:
        result = {
            "schema_version": self.schema_version,
            "query_id": self.query_id,
            "timestamp": self.timestamp,
            "project": self.project,
            "question": self.question,
        }
        if self.mode:
            result["mode"] = self.mode
        return result


@dataclass
class CodeResult:
    """
    Code evidence result.

    Required fields:
    - id: Neo4j node uid
    - type: Node labels
    - path: Source file path
    - name: Entity name
    - score: Relevance score

    Optional fields:
    - start_line, end_line: Line numbers
    - excerpt: Code snippet
    - evidence_hash: Hash of evidence content
    - sources: Search sources (vector, keyword)
    - neighbors: Connected nodes
    """
    id: str
    type: List[str]
    path: str
    name: str
    score: float
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    excerpt: Optional[str] = None
    evidence_hash: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    neighbors: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    # Provenance fields
    prov_file_hash: Optional[str] = None
    prov_text_hash: Optional[str] = None

    def to_dict(self) -> Dict:
        result = {
            "id": self.id,
            "type": self.type,
            "path": self.path,
            "name": self.name,
            "score": self.score,
        }
        if self.start_line is not None:
            result["start_line"] = self.start_line
        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.excerpt:
            result["excerpt"] = self.excerpt
        if self.evidence_hash:
            result["evidence_hash"] = self.evidence_hash
        if self.sources:
            result["sources"] = self.sources
        if self.neighbors:
            result["neighbors"] = self.neighbors
        if self.docstring:
            result["docstring"] = self.docstring
        if self.prov_file_hash:
            result["prov_file_hash"] = self.prov_file_hash
        if self.prov_text_hash:
            result["prov_text_hash"] = self.prov_text_hash
        return result


@dataclass
class DocResult:
    """
    Document evidence result.

    Required fields:
    - id: Neo4j node uid
    - path: Document file path
    - name: Document name
    - score: Relevance score

    Optional fields:
    - last_modified: Unix timestamp
    - doc_type: Document classification
    - excerpt: Content snippet
    """
    id: str
    path: str
    name: str
    score: float
    last_modified: Optional[float] = None
    doc_type: Optional[str] = None
    excerpt: Optional[str] = None
    evidence_hash: Optional[str] = None
    neighbors: List[str] = field(default_factory=list)
    # Provenance fields
    prov_file_hash: Optional[str] = None
    prov_text_hash: Optional[str] = None

    def to_dict(self) -> Dict:
        result = {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "score": self.score,
        }
        if self.last_modified is not None:
            result["last_modified"] = self.last_modified
        if self.doc_type:
            result["doc_type"] = self.doc_type
        if self.excerpt:
            result["excerpt"] = self.excerpt
        if self.evidence_hash:
            result["evidence_hash"] = self.evidence_hash
        if self.neighbors:
            result["neighbors"] = self.neighbors
        if self.prov_file_hash:
            result["prov_file_hash"] = self.prov_file_hash
        if self.prov_text_hash:
            result["prov_text_hash"] = self.prov_text_hash
        return result


@dataclass
class VeracityReport:
    """
    Veracity validation report.

    Required fields:
    - confidence_score: 0-100 score
    - is_stale: Whether results contain stale data
    - faults: List of detected faults
    """
    confidence_score: float
    is_stale: bool
    faults: List[str]

    def to_dict(self) -> Dict:
        return {
            "confidence_score": self.confidence_score,
            "is_stale": self.is_stale,
            "faults": self.faults,
        }


@dataclass
class EvidencePacketV1:
    """
    Evidence packet v1.0 schema.

    Required sections:
    - meta: Query metadata with schema version
    - status: "success" | "insufficient_evidence"
    - code_truth: List of code evidence
    - doc_claims: List of document evidence
    - veracity: Validation report

    Optional sections:
    - graph_relationships: List of graph edges
    - suggested_actions: List of action suggestions
    - technical_brief: LLM synthesis (only in synthesis mode)
    """
    meta: PacketMeta
    status: str
    code_truth: List[CodeResult]
    doc_claims: List[DocResult]
    veracity: VeracityReport
    graph_relationships: List[Dict] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    technical_brief: Optional[str] = None

    def to_dict(self) -> Dict:
        result = {
            "meta": self.meta.to_dict(),
            "status": self.status,
            "code_truth": [r.to_dict() for r in self.code_truth],
            "doc_claims": [r.to_dict() for r in self.doc_claims],
            "veracity": self.veracity.to_dict(),
        }
        if self.graph_relationships:
            result["graph_relationships"] = self.graph_relationships
        if self.suggested_actions:
            result["suggested_actions"] = self.suggested_actions
        if self.technical_brief is not None:
            result["technical_brief"] = self.technical_brief
        return result


def _validate_dict_packet(packet_dict: Dict) -> List[str]:
    """Validate a packet dictionary."""
    errors = []

    # Check meta
    meta = packet_dict.get("meta", {})
    for field in REQUIRED_META_FIELDS:
        if field not in meta or not meta[field]:
            errors.append(f"meta.{field} is required")

    # Check schema version
    if meta.get("schema_version") and meta["schema_version"] != SCHEMA_VERSION:
        errors.append(f"Schema version mismatch: expected {SCHEMA_VERSION}, got {meta.get('schema_version')}")

    # Check code_truth
    for i, result in enumerate(packet_dict.get("code_truth", [])):
        for field in REQUIRED_CODE_RESULT_FIELDS:
            if field not in result or (field == "type" and not result.get(field)):
                errors.append(f"code_truth[{i}].{field} is required")
            elif field in ["id", "path", "name"] and not result.get(field):
                errors.append(f"code_truth[{i}].{field} cannot be empty")

    # Check doc_claims
    for i, result in enumerate(packet_dict.get("doc_claims", [])):
        for field in REQUIRED_DOC_RESULT_FIELDS:
            if field not in result:
                errors.append(f"doc_claims[{i}].{field} is required")
            elif field in ["id", "path", "name"] and not result.get(field):
                errors.append(f"doc_claims[{i}].{field} cannot be empty")

    # Check veracity
    veracity = packet_dict.get("veracity", {})
    for field in REQUIRED_VERACITY_FIELDS:
        if field not in veracity:
            errors.append(f"veracity.{field} is required")

    return errors


def _validate_packet_object(packet: EvidencePacketV1) -> List[str]:
    """Validate a packet object."""
    errors = []

    # Check meta
    if not packet.meta.schema_version:
        errors.append("meta.schema_version is required")
    elif packet.meta.schema_version != SCHEMA_VERSION:
        errors.append(f"Schema version mismatch: expected {SCHEMA_VERSION}, got {packet.meta.schema_version}")
    if not packet.meta.query_id:
        errors.append("meta.query_id is required")
    if not packet.meta.project:
        errors.append("meta.project is required")

    # Check code_truth
    for i, result in enumerate(packet.code_truth):
        if not result.id:
            errors.append(f"code_truth[{i}].id is required")
        if not result.path:
            errors.append(f"code_truth[{i}].path is required")
        if not result.name:
            errors.append(f"code_truth[{i}].name is required")
        if not result.type:
            errors.append(f"code_truth[{i}].type is required")

    # Check doc_claims
    for i, result in enumerate(packet.doc_claims):
        if not result.id:
            errors.append(f"doc_claims[{i}].id is required")
        if not result.path:
            errors.append(f"doc_claims[{i}].path is required")

    return errors


def validate_packet(packet: Union[EvidencePacketV1, Dict]) -> List[str]:
    """
    Validate an evidence packet.

    Args:
        packet: EvidencePacketV1 object or dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    if isinstance(packet, dict):
        return _validate_dict_packet(packet)
    else:
        return _validate_packet_object(packet)


def compute_packet_hash(packet: Union[EvidencePacketV1, Dict]) -> str:
    """
    Compute SHA256 hash of packet content.

    Uses deterministic JSON serialization for consistent hashing.

    Args:
        packet: EvidencePacketV1 object or dictionary

    Returns:
        SHA256 hex digest (64 characters)
    """
    if isinstance(packet, EvidencePacketV1):
        packet_dict = packet.to_dict()
    else:
        packet_dict = packet

    # Serialize with sorted keys for determinism
    json_str = json.dumps(packet_dict, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def create_audit_entry(packet: Union[EvidencePacketV1, Dict]) -> Dict:
    """
    Create an audit log entry for a packet.

    Includes:
    - packet_hash: SHA256 hash of packet content
    - logged_at: Timestamp of audit entry creation
    - packet: The full packet content

    Args:
        packet: EvidencePacketV1 object or dictionary

    Returns:
        Audit entry dictionary
    """
    if isinstance(packet, EvidencePacketV1):
        packet_dict = packet.to_dict()
    else:
        packet_dict = packet

    return {
        "packet_hash": compute_packet_hash(packet),
        "logged_at": datetime.now().isoformat(),
        "packet": packet_dict,
    }


def validate_and_hash(packet: Union[EvidencePacketV1, Dict]) -> tuple:
    """
    Validate packet and compute hash.

    Raises ValidationError if validation fails.

    Args:
        packet: EvidencePacketV1 object or dictionary

    Returns:
        Tuple of (is_valid, packet_hash, errors)
    """
    errors = validate_packet(packet)
    packet_hash = compute_packet_hash(packet)
    return (len(errors) == 0, packet_hash, errors)
