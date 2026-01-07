"""
Evidence-Only Query Output Module (STORY-010).

Provides structured, evidence-based query output without LLM synthesis.
All content is graph-derived with explicit source citations.

Key features:
- Evidence-only mode is the default (no LLM synthesis)
- Deterministic ordering (score DESC, path ASC, id ASC)
- Explicit provenance and source citations
- Optional synthesis mode via flag
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class EvidenceOutputMode(Enum):
    """Output mode for query results."""
    EVIDENCE_ONLY = "evidence_only"  # Default: no LLM synthesis
    SYNTHESIS = "synthesis"  # Opt-in: includes LLM-generated brief


# Predefined suggested actions (not LLM-generated)
DEFAULT_SUGGESTED_ACTIONS = [
    "Run build_graph.py to index the codebase.",
    "Check that the project name is correct.",
    "Try a more specific query with file or function names.",
    "Verify Neo4j connection and data availability.",
    "Review .gitignore to ensure target files are not excluded.",
]


@dataclass
class EvidenceQueryConfig:
    """Configuration for evidence-based queries."""
    mode: EvidenceOutputMode = EvidenceOutputMode.EVIDENCE_ONLY
    max_results: int = 20
    include_provenance: bool = True
    include_neighbors: bool = True


@dataclass
class QueryMeta:
    """Metadata for a query response."""
    query_id: str
    timestamp: str
    project: str
    question: str
    mode: EvidenceOutputMode

    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id,
            "timestamp": self.timestamp,
            "project": self.project,
            "question": self.question,
            "mode": self.mode.value,
        }


@dataclass
class CodeEvidence:
    """
    Evidence from code nodes.

    Required fields (DoD-3):
    - id: Neo4j node uid
    - path: Source file path
    - name: Entity name
    - type: Node labels (e.g., ["Function", "Code"])

    Optional fields:
    - start_line, end_line: Line numbers
    - docstring: Function/class documentation
    - score: Relevance score from query
    - neighbors: Connected entities
    - prov_*: Provenance fields
    """
    id: str
    path: str
    name: str
    type: List[str]
    score: float = 0.0
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    neighbors: List[str] = field(default_factory=list)
    # Provenance fields
    prov_file_hash: Optional[str] = None
    prov_text_hash: Optional[str] = None
    prov_last_modified: Optional[float] = None
    prov_extractor: Optional[str] = None
    prov_extractor_version: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None values."""
        result = {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "type": self.type,
            "score": self.score,
        }
        if self.start_line is not None:
            result["start_line"] = self.start_line
        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.docstring is not None:
            result["docstring"] = self.docstring
        if self.neighbors:
            result["neighbors"] = self.neighbors
        # Provenance fields
        if self.prov_file_hash:
            result["prov_file_hash"] = self.prov_file_hash
        if self.prov_text_hash:
            result["prov_text_hash"] = self.prov_text_hash
        if self.prov_last_modified is not None:
            result["prov_last_modified"] = self.prov_last_modified
        if self.prov_extractor:
            result["prov_extractor"] = self.prov_extractor
        if self.prov_extractor_version:
            result["prov_extractor_version"] = self.prov_extractor_version
        return result


@dataclass
class DocEvidence:
    """
    Evidence from document nodes.

    Required fields (DoD-3):
    - id: Neo4j node uid
    - path: Document file path

    Optional fields:
    - last_modified: Unix timestamp
    - doc_type: Document type classification
    - prov_*: Provenance fields
    """
    id: str
    path: str
    name: str
    score: float = 0.0
    last_modified: Optional[float] = None
    doc_type: Optional[str] = None
    neighbors: List[str] = field(default_factory=list)
    # Provenance fields
    prov_file_hash: Optional[str] = None
    prov_text_hash: Optional[str] = None
    prov_last_modified: Optional[float] = None
    prov_extractor: Optional[str] = None
    prov_extractor_version: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None values."""
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
        if self.neighbors:
            result["neighbors"] = self.neighbors
        # Provenance fields
        if self.prov_file_hash:
            result["prov_file_hash"] = self.prov_file_hash
        if self.prov_text_hash:
            result["prov_text_hash"] = self.prov_text_hash
        if self.prov_last_modified is not None:
            result["prov_last_modified"] = self.prov_last_modified
        if self.prov_extractor:
            result["prov_extractor"] = self.prov_extractor
        if self.prov_extractor_version:
            result["prov_extractor_version"] = self.prov_extractor_version
        return result


@dataclass
class EvidenceResult:
    """Combined evidence result for sorting."""
    evidence: Any  # CodeEvidence or DocEvidence
    score: float
    path: str
    id: str


@dataclass
class EvidencePacket:
    """
    Complete evidence packet for query response.

    Evidence-only mode:
    - status: "success" | "insufficient_evidence"
    - code_truth: List of CodeEvidence
    - doc_claims: List of DocEvidence
    - context_veracity: Confidence score and faults
    - NO technical_brief field

    Synthesis mode (opt-in):
    - Adds technical_brief field with LLM-generated content
    - Each claim cites evidence sources
    """
    meta: QueryMeta
    status: str
    code_truth: List[CodeEvidence]
    doc_claims: List[DocEvidence]
    context_veracity: Dict
    graph_relationships: List[Dict] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    technical_brief: Optional[str] = None  # Only present in synthesis mode

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "meta": self.meta.to_dict(),
            "status": self.status,
            "code_truth": [e.to_dict() for e in self.code_truth],
            "doc_claims": [e.to_dict() for e in self.doc_claims],
            "context_veracity": self.context_veracity,
        }
        if self.graph_relationships:
            result["graph_relationships"] = self.graph_relationships
        if self.suggested_actions:
            result["suggested_actions"] = self.suggested_actions
        # Only include technical_brief if present (synthesis mode)
        if self.technical_brief is not None:
            result["technical_brief"] = self.technical_brief
        return result


def sort_evidence_deterministically(
    evidence: List[Any],
) -> List[Any]:
    """
    Sort evidence deterministically.

    Order: score DESC, path ASC, id ASC

    This ensures identical inputs always produce identical ordering,
    making output reproducible across runs.
    """
    return sorted(
        evidence,
        key=lambda e: (-e.score, e.path, e.id)
    )


def format_insufficient_evidence_response(
    query: str,
    project: str,
    query_id: Optional[str] = None,
) -> Dict:
    """
    Format response when no evidence is found.

    Uses predefined suggested actions (not LLM-generated).
    """
    return {
        "meta": {
            "query_id": query_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "project": project,
            "question": query,
            "mode": EvidenceOutputMode.EVIDENCE_ONLY.value,
        },
        "status": "insufficient_evidence",
        "code_truth": [],
        "doc_claims": [],
        "context_veracity": {
            "confidence_score": 0,
            "is_stale": False,
            "faults": ["No relevant context found in knowledge graph."],
        },
        "suggested_actions": [
            DEFAULT_SUGGESTED_ACTIONS[0],  # Run build_graph.py
            DEFAULT_SUGGESTED_ACTIONS[1],  # Check project name
            DEFAULT_SUGGESTED_ACTIONS[2],  # Try more specific query
        ],
    }


def validate_evidence_packet(packet: EvidencePacket) -> List[str]:
    """
    Validate an evidence packet.

    Checks (DoD-3):
    - All code_truth entries have: id, path, type, name
    - All doc_claims entries have: id, path

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Validate code evidence
    for i, evidence in enumerate(packet.code_truth):
        if not evidence.id:
            errors.append(f"code_truth[{i}]: id is required")
        if not evidence.path:
            errors.append(f"code_truth[{i}]: path is required")
        if not evidence.name:
            errors.append(f"code_truth[{i}]: name is required")
        if not evidence.type:
            errors.append(f"code_truth[{i}]: type is required")

    # Validate doc evidence
    for i, evidence in enumerate(packet.doc_claims):
        if not evidence.id:
            errors.append(f"doc_claims[{i}]: id is required")
        if not evidence.path:
            errors.append(f"doc_claims[{i}]: path is required")

    return errors


def create_evidence_packet(
    query: str,
    project: str,
    code_truth: List[CodeEvidence],
    doc_claims: List[DocEvidence],
    veracity: Dict,
    config: Optional[EvidenceQueryConfig] = None,
    query_id: Optional[str] = None,
    graph_relationships: Optional[List[Dict]] = None,
) -> EvidencePacket:
    """
    Create an evidence packet from query results.

    Args:
        query: Original query string
        project: Project name
        code_truth: List of code evidence
        doc_claims: List of doc evidence
        veracity: Veracity validation results
        config: Query configuration (defaults to evidence-only)
        query_id: Optional query ID (generates UUID if not provided)
        graph_relationships: Optional list of graph relationships

    Returns:
        EvidencePacket with deterministically ordered results
    """
    if config is None:
        config = EvidenceQueryConfig()

    # Sort evidence deterministically
    sorted_code = sort_evidence_deterministically(code_truth)
    sorted_docs = sort_evidence_deterministically(doc_claims)

    # Determine status
    has_results = len(sorted_code) > 0 or len(sorted_docs) > 0
    status = "success" if has_results else "insufficient_evidence"

    # Create meta
    meta = QueryMeta(
        query_id=query_id or str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        project=project,
        question=query,
        mode=config.mode,
    )

    # Build suggested actions for insufficient evidence
    suggested_actions = []
    if not has_results:
        suggested_actions = [
            DEFAULT_SUGGESTED_ACTIONS[0],
            DEFAULT_SUGGESTED_ACTIONS[1],
            DEFAULT_SUGGESTED_ACTIONS[2],
        ]

    return EvidencePacket(
        meta=meta,
        status=status,
        code_truth=sorted_code,
        doc_claims=sorted_docs,
        context_veracity=veracity,
        graph_relationships=graph_relationships or [],
        suggested_actions=suggested_actions,
        technical_brief=None,  # Never set in evidence-only mode
    )


def neo4j_record_to_code_evidence(
    record: Dict,
    include_provenance: bool = True,
) -> CodeEvidence:
    """
    Convert a Neo4j record to CodeEvidence.

    Extracts all required and optional fields including provenance.
    """
    node = record.get('node', {})

    return CodeEvidence(
        id=record.get('id', ''),
        path=node.get('path', 'unknown'),
        name=record.get('name', ''),
        type=list(node.labels) if hasattr(node, 'labels') else [],
        score=record.get('score', 0.0),
        start_line=node.get('start_line'),
        end_line=node.get('end_line'),
        docstring=record.get('doc'),
        neighbors=record.get('neighbors', []),
        # Provenance fields (if available)
        prov_file_hash=node.get('prov_file_hash') if include_provenance else None,
        prov_text_hash=node.get('prov_text_hash') if include_provenance else None,
        prov_last_modified=node.get('prov_last_modified') if include_provenance else None,
        prov_extractor=node.get('prov_extractor') if include_provenance else None,
        prov_extractor_version=node.get('prov_extractor_version') if include_provenance else None,
    )


def neo4j_record_to_doc_evidence(
    record: Dict,
    include_provenance: bool = True,
) -> DocEvidence:
    """
    Convert a Neo4j record to DocEvidence.

    Extracts all required and optional fields including provenance.
    """
    node = record.get('node', {})

    return DocEvidence(
        id=record.get('id', ''),
        path=node.get('path', 'unknown'),
        name=record.get('name', ''),
        score=record.get('score', 0.0),
        last_modified=node.get('last_modified'),
        doc_type=node.get('doc_type'),
        neighbors=record.get('neighbors', []),
        # Provenance fields (if available)
        prov_file_hash=node.get('prov_file_hash') if include_provenance else None,
        prov_text_hash=node.get('prov_text_hash') if include_provenance else None,
        prov_last_modified=node.get('prov_last_modified') if include_provenance else None,
        prov_extractor=node.get('prov_extractor') if include_provenance else None,
        prov_extractor_version=node.get('prov_extractor_version') if include_provenance else None,
    )
