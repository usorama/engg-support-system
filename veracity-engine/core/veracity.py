"""
Veracity Logic Module (STORY-012).

Provides deterministic veracity checking for knowledge graph results:
1. Staleness detection (configurable thresholds)
2. Orphan detection (connectivity checks)
3. Contradiction detection (doc vs code timestamps)
4. Coverage scoring
5. Deterministic confidence scoring

All scoring is formula-based (no LLM involvement) for reproducibility.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# Default thresholds (days)
DEFAULT_STALENESS_DAYS = 90
DEFAULT_ORPHAN_THRESHOLD = 2
DEFAULT_CONTRADICTION_DAYS = 30

# Minimum results for good coverage
DEFAULT_MIN_RESULTS = 5


class FaultType(Enum):
    """Types of veracity faults."""
    STALE_DOC = "STALE_DOC"
    ORPHANED_NODE = "ORPHANED_NODE"
    CONTRADICTION = "CONTRADICTION"
    LOW_COVERAGE = "LOW_COVERAGE"


# Penalty points per fault type (deducted from 100)
FAULT_PENALTIES = {
    FaultType.STALE_DOC: 15,
    FaultType.ORPHANED_NODE: 5,
    FaultType.CONTRADICTION: 20,
    FaultType.LOW_COVERAGE: 10,
}


@dataclass
class VeracityConfig:
    """Configuration for veracity checks."""
    staleness_days: int = DEFAULT_STALENESS_DAYS
    orphan_threshold: int = DEFAULT_ORPHAN_THRESHOLD
    contradiction_days: int = DEFAULT_CONTRADICTION_DAYS
    min_results: int = DEFAULT_MIN_RESULTS


@dataclass
class VeracityFault:
    """
    A detected veracity fault with evidence.

    Attributes:
        fault_type: Type of fault detected
        message: Human-readable description
        evidence: Dictionary of evidence details (node_id, timestamps, etc.)
    """
    fault_type: FaultType
    message: str
    evidence: Dict[str, Any]

    def __str__(self) -> str:
        return f"[{self.fault_type.value}] {self.message}"

    def to_dict(self) -> Dict:
        return {
            "type": self.fault_type.value,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass
class VeracityResult:
    """
    Complete veracity validation result.

    Attributes:
        confidence_score: 0-100 score (100 = perfect, 0 = no confidence)
        is_stale: Whether any stale documents were found
        faults: List of detected faults
    """
    confidence_score: float
    is_stale: bool
    faults: List[VeracityFault]

    def to_dict(self) -> Dict:
        return {
            "confidence_score": self.confidence_score,
            "is_stale": self.is_stale,
            "faults": [f.to_dict() for f in self.faults],
        }


def _get_node_labels(record: Dict) -> List[str]:
    """Extract labels from a record's node."""
    node = record.get("node")
    if node is None:
        return []
    if hasattr(node, "labels"):
        return list(node.labels)
    return []


def _get_node_property(record: Dict, key: str, default: Any = None) -> Any:
    """Get a property from a record's node."""
    node = record.get("node")
    if node is None:
        return default
    if hasattr(node, "get"):
        return node.get(key, default)
    return default


def check_staleness(
    records: List[Dict],
    staleness_days: int = DEFAULT_STALENESS_DAYS
) -> List[VeracityFault]:
    """
    Check for stale documents.

    Only Document nodes are checked for staleness. Code nodes are excluded
    as they represent current implementation.

    Args:
        records: List of query result records
        staleness_days: Threshold in days (default: 90)

    Returns:
        List of VeracityFault for stale documents
    """
    faults = []
    now = time.time()
    threshold_seconds = staleness_days * 24 * 3600

    for record in records:
        labels = _get_node_labels(record)

        # Only check Document nodes for staleness
        if "Document" not in labels:
            continue

        last_modified = _get_node_property(record, "last_modified", 0)
        if last_modified == 0:
            continue

        age_seconds = now - last_modified
        if age_seconds > threshold_seconds:
            days_old = int(age_seconds / (24 * 3600))
            node_name = _get_node_property(record, "name", record.get("name", "unknown"))
            node_id = record.get("id", "unknown")

            faults.append(VeracityFault(
                fault_type=FaultType.STALE_DOC,
                message=f"'{node_name}' is {days_old} days old (threshold: {staleness_days})",
                evidence={
                    "node_id": node_id,
                    "days_old": days_old,
                    "threshold_days": staleness_days,
                }
            ))

    return faults


def check_orphans(
    records: List[Dict],
    orphan_threshold: int = DEFAULT_ORPHAN_THRESHOLD
) -> List[VeracityFault]:
    """
    Check for orphaned (poorly connected) nodes.

    Nodes with fewer neighbors than the threshold are flagged as orphans,
    indicating they may lack context or be disconnected from the codebase.

    Args:
        records: List of query result records
        orphan_threshold: Minimum neighbors required (default: 2)

    Returns:
        List of VeracityFault for orphaned nodes
    """
    faults = []

    for record in records:
        neighbors = record.get("neighbors", [])
        neighbor_count = len(neighbors) if neighbors else 0

        if neighbor_count < orphan_threshold:
            node_name = record.get("name", _get_node_property(record, "name", "unknown"))
            node_id = record.get("id", "unknown")

            faults.append(VeracityFault(
                fault_type=FaultType.ORPHANED_NODE,
                message=f"'{node_name}' has only {neighbor_count} connection(s) (threshold: {orphan_threshold})",
                evidence={
                    "node_id": node_id,
                    "neighbor_count": neighbor_count,
                    "threshold": orphan_threshold,
                }
            ))

    return faults


def check_contradictions(
    records: List[Dict],
    contradiction_days: int = DEFAULT_CONTRADICTION_DAYS
) -> List[VeracityFault]:
    """
    Check for contradictions between documents and code.

    A contradiction is detected when code has been updated significantly
    more recently than its linked documentation, suggesting the docs
    may be out of sync.

    Args:
        records: List of query result records
        contradiction_days: Days difference to flag (default: 30)

    Returns:
        List of VeracityFault for detected contradictions
    """
    faults = []
    threshold_seconds = contradiction_days * 24 * 3600

    # Build lookup of node timestamps by name
    node_timestamps = {}
    node_types = {}

    for record in records:
        labels = _get_node_labels(record)
        name = record.get("name", _get_node_property(record, "name"))
        last_modified = _get_node_property(record, "last_modified", 0)

        if name:
            node_timestamps[name] = last_modified
            # Classify as doc or code
            if "Document" in labels:
                node_types[name] = "doc"
            elif "Code" in labels or "Function" in labels or "Class" in labels:
                node_types[name] = "code"

    # Check document nodes against their code neighbors
    for record in records:
        labels = _get_node_labels(record)

        if "Document" not in labels:
            continue

        doc_name = record.get("name", _get_node_property(record, "name"))
        doc_modified = _get_node_property(record, "last_modified", 0)
        neighbors = record.get("neighbors", [])
        node_id = record.get("id", "unknown")

        if doc_modified == 0 or not neighbors:
            continue

        # Check each neighbor that's code
        for neighbor_name in neighbors:
            neighbor_type = node_types.get(neighbor_name)
            neighbor_modified = node_timestamps.get(neighbor_name, 0)

            if neighbor_type != "code" or neighbor_modified == 0:
                continue

            # Check if code is significantly newer than doc
            time_diff = neighbor_modified - doc_modified
            if time_diff > threshold_seconds:
                days_diff = int(time_diff / (24 * 3600))

                faults.append(VeracityFault(
                    fault_type=FaultType.CONTRADICTION,
                    message=f"'{doc_name}' may be outdated: linked code '{neighbor_name}' is {days_diff} days newer",
                    evidence={
                        "doc_id": node_id,
                        "doc_name": doc_name,
                        "code_name": neighbor_name,
                        "days_difference": days_diff,
                        "threshold_days": contradiction_days,
                    }
                ))

    return faults


def check_coverage(
    records: List[Dict],
    min_results: int = DEFAULT_MIN_RESULTS
) -> List[VeracityFault]:
    """
    Check for low coverage (insufficient results).

    Low coverage indicates the query may not have found enough relevant
    context to provide a reliable answer.

    Args:
        records: List of query result records
        min_results: Minimum results for good coverage (default: 5)

    Returns:
        List of VeracityFault if coverage is low
    """
    faults = []
    result_count = len(records)

    if result_count < min_results:
        faults.append(VeracityFault(
            fault_type=FaultType.LOW_COVERAGE,
            message=f"Only {result_count} result(s) found (recommended: {min_results}+)",
            evidence={
                "result_count": result_count,
                "min_results": min_results,
            }
        ))

    return faults


def compute_confidence_score(faults: List[VeracityFault]) -> float:
    """
    Compute deterministic confidence score from faults.

    Starts at 100 and deducts penalties for each fault based on type:
    - STALE_DOC: -15
    - ORPHANED_NODE: -5
    - CONTRADICTION: -20
    - LOW_COVERAGE: -10

    Score is floored at 0.

    Args:
        faults: List of detected faults

    Returns:
        Confidence score (0-100)
    """
    score = 100.0

    for fault in faults:
        penalty = FAULT_PENALTIES.get(fault.fault_type, 0)
        score -= penalty

    return max(0.0, score)


def validate_veracity(
    records: List[Dict],
    config: Optional[VeracityConfig] = None
) -> VeracityResult:
    """
    Run complete veracity validation on query results.

    Runs all checks and computes final confidence score.

    Args:
        records: List of query result records
        config: Optional VeracityConfig (uses defaults if not provided)

    Returns:
        VeracityResult with score, staleness flag, and faults
    """
    if config is None:
        config = VeracityConfig()

    all_faults = []

    # Run all checks
    all_faults.extend(check_staleness(records, config.staleness_days))
    all_faults.extend(check_orphans(records, config.orphan_threshold))
    all_faults.extend(check_contradictions(records, config.contradiction_days))
    all_faults.extend(check_coverage(records, config.min_results))

    # Compute score
    score = compute_confidence_score(all_faults)

    # Check for staleness
    is_stale = any(f.fault_type == FaultType.STALE_DOC for f in all_faults)

    return VeracityResult(
        confidence_score=score,
        is_stale=is_stale,
        faults=all_faults,
    )
