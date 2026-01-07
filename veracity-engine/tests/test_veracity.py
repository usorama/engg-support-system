"""
Tests for Veracity Logic Expansion (STORY-012).

Tests cover:
1. Staleness detection (configurable thresholds)
2. Orphan detection (connectivity checks)
3. Contradiction detection (doc vs code timestamps)
4. Coverage scoring
5. Deterministic confidence scoring
6. Evidence citations in faults
"""
import pytest
import time
from datetime import datetime, timedelta

from core.veracity import (
    VeracityConfig,
    VeracityFault,
    FaultType,
    VeracityResult,
    check_staleness,
    check_orphans,
    check_contradictions,
    check_coverage,
    compute_confidence_score,
    validate_veracity,
    DEFAULT_STALENESS_DAYS,
    DEFAULT_ORPHAN_THRESHOLD,
    DEFAULT_CONTRADICTION_DAYS,
    FAULT_PENALTIES,
)


class TestVeracityConfig:
    """Tests for veracity configuration."""

    def test_default_config(self):
        """Default config should have valid values."""
        config = VeracityConfig()
        assert config.staleness_days == DEFAULT_STALENESS_DAYS
        assert config.orphan_threshold == DEFAULT_ORPHAN_THRESHOLD
        assert config.contradiction_days == DEFAULT_CONTRADICTION_DAYS

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = VeracityConfig(
            staleness_days=60,
            orphan_threshold=3,
            contradiction_days=15,
        )
        assert config.staleness_days == 60
        assert config.orphan_threshold == 3
        assert config.contradiction_days == 15


class TestFaultType:
    """Tests for fault type enum."""

    def test_fault_types_defined(self):
        """All fault types should be defined."""
        assert FaultType.STALE_DOC is not None
        assert FaultType.ORPHANED_NODE is not None
        assert FaultType.CONTRADICTION is not None
        assert FaultType.LOW_COVERAGE is not None

    def test_fault_penalties_defined(self):
        """All fault types should have penalties."""
        for fault_type in FaultType:
            assert fault_type in FAULT_PENALTIES


class TestVeracityFault:
    """Tests for veracity fault structure."""

    def test_fault_has_required_fields(self):
        """Fault should have type, message, and evidence."""
        fault = VeracityFault(
            fault_type=FaultType.STALE_DOC,
            message="Document is stale",
            evidence={"node_id": "test:doc", "days_old": 100},
        )
        assert fault.fault_type == FaultType.STALE_DOC
        assert fault.message is not None
        assert fault.evidence is not None

    def test_fault_to_string(self):
        """Fault should convert to descriptive string."""
        fault = VeracityFault(
            fault_type=FaultType.STALE_DOC,
            message="README.md is 100 days old",
            evidence={"node_id": "test:doc:README.md"},
        )
        fault_str = str(fault)
        assert "STALE_DOC" in fault_str
        assert "README.md" in fault_str

    def test_fault_to_dict(self):
        """Fault should convert to dictionary."""
        fault = VeracityFault(
            fault_type=FaultType.ORPHANED_NODE,
            message="Node has low connectivity",
            evidence={"node_id": "test:func", "neighbor_count": 1},
        )
        d = fault.to_dict()
        assert d["type"] == "ORPHANED_NODE"
        assert "message" in d
        assert "evidence" in d


class TestStalenessDetection:
    """Tests for staleness checking."""

    def test_fresh_doc_not_stale(self):
        """Recent document should not be flagged as stale."""
        now = time.time()
        records = [{
            "node": MockNode(
                labels=["Document"],
                properties={"name": "README.md", "last_modified": now - (10 * 24 * 3600)}
            ),
            "id": "test:doc:README.md",
            "name": "README.md",
        }]
        faults = check_staleness(records)
        assert len(faults) == 0

    def test_old_doc_is_stale(self):
        """Document older than threshold should be flagged."""
        now = time.time()
        records = [{
            "node": MockNode(
                labels=["Document"],
                properties={"name": "OLD.md", "last_modified": now - (100 * 24 * 3600)}
            ),
            "id": "test:doc:OLD.md",
            "name": "OLD.md",
        }]
        faults = check_staleness(records, staleness_days=90)
        assert len(faults) == 1
        assert faults[0].fault_type == FaultType.STALE_DOC
        assert "OLD.md" in faults[0].message

    def test_code_not_checked_for_staleness(self):
        """Code nodes should not be checked for staleness."""
        now = time.time()
        records = [{
            "node": MockNode(
                labels=["Function", "Code"],
                properties={"name": "old_func", "last_modified": now - (200 * 24 * 3600)}
            ),
            "id": "test:func",
            "name": "old_func",
        }]
        faults = check_staleness(records)
        assert len(faults) == 0

    def test_configurable_threshold(self):
        """Staleness threshold should be configurable."""
        now = time.time()
        records = [{
            "node": MockNode(
                labels=["Document"],
                properties={"name": "SPEC.md", "last_modified": now - (45 * 24 * 3600)}
            ),
            "id": "test:doc:SPEC.md",
            "name": "SPEC.md",
        }]
        # Should be stale with 30-day threshold
        faults_30 = check_staleness(records, staleness_days=30)
        assert len(faults_30) == 1

        # Should not be stale with 60-day threshold
        faults_60 = check_staleness(records, staleness_days=60)
        assert len(faults_60) == 0


class TestOrphanDetection:
    """Tests for orphan node checking."""

    def test_connected_node_not_orphan(self):
        """Node with sufficient connections should not be orphan."""
        records = [{
            "node": MockNode(labels=["Function", "Code"], properties={"name": "func"}),
            "id": "test:func",
            "name": "func",
            "neighbors": ["a", "b", "c"],
        }]
        faults = check_orphans(records)
        assert len(faults) == 0

    def test_isolated_node_is_orphan(self):
        """Node with few connections should be flagged."""
        records = [{
            "node": MockNode(labels=["Function", "Code"], properties={"name": "lonely_func"}),
            "id": "test:lonely",
            "name": "lonely_func",
            "neighbors": ["only_one"],
        }]
        faults = check_orphans(records, orphan_threshold=2)
        assert len(faults) == 1
        assert faults[0].fault_type == FaultType.ORPHANED_NODE

    def test_no_neighbors_is_orphan(self):
        """Node with no neighbors should be flagged."""
        records = [{
            "node": MockNode(labels=["Function", "Code"], properties={"name": "isolated"}),
            "id": "test:isolated",
            "name": "isolated",
            "neighbors": [],
        }]
        faults = check_orphans(records)
        assert len(faults) == 1

    def test_configurable_threshold(self):
        """Orphan threshold should be configurable."""
        records = [{
            "node": MockNode(labels=["Class", "Code"], properties={"name": "MyClass"}),
            "id": "test:class",
            "name": "MyClass",
            "neighbors": ["a", "b"],
        }]
        # Should be orphan with threshold 3
        faults_3 = check_orphans(records, orphan_threshold=3)
        assert len(faults_3) == 1

        # Should not be orphan with threshold 2
        faults_2 = check_orphans(records, orphan_threshold=2)
        assert len(faults_2) == 0


class TestContradictionDetection:
    """Tests for contradiction checking."""

    def test_no_contradiction_when_doc_newer(self):
        """No contradiction when doc is newer than linked code."""
        now = time.time()
        records = [
            {
                "node": MockNode(
                    labels=["Document"],
                    properties={
                        "name": "API.md",
                        "last_modified": now - (10 * 24 * 3600),  # 10 days old
                    }
                ),
                "id": "test:doc:API.md",
                "name": "API.md",
                "neighbors": ["api_handler"],
            },
            {
                "node": MockNode(
                    labels=["Function", "Code"],
                    properties={
                        "name": "api_handler",
                        "last_modified": now - (20 * 24 * 3600),  # 20 days old
                    }
                ),
                "id": "test:func",
                "name": "api_handler",
                "neighbors": ["API.md"],
            },
        ]
        faults = check_contradictions(records)
        assert len(faults) == 0

    def test_contradiction_when_code_much_newer(self):
        """Contradiction when code is significantly newer than linked doc."""
        now = time.time()
        records = [
            {
                "node": MockNode(
                    labels=["Document"],
                    properties={
                        "name": "DESIGN.md",
                        "last_modified": now - (60 * 24 * 3600),  # 60 days old
                    }
                ),
                "id": "test:doc:DESIGN.md",
                "name": "DESIGN.md",
                "neighbors": ["new_feature"],
            },
            {
                "node": MockNode(
                    labels=["Function", "Code"],
                    properties={
                        "name": "new_feature",
                        "last_modified": now - (5 * 24 * 3600),  # 5 days old
                    }
                ),
                "id": "test:func:new",
                "name": "new_feature",
                "neighbors": ["DESIGN.md"],
            },
        ]
        faults = check_contradictions(records, contradiction_days=30)
        assert len(faults) == 1
        assert faults[0].fault_type == FaultType.CONTRADICTION


class TestCoverageScoring:
    """Tests for coverage scoring."""

    def test_good_coverage(self):
        """Many results should indicate good coverage."""
        records = [{"id": f"test:{i}"} for i in range(15)]
        faults = check_coverage(records, min_results=5)
        assert len(faults) == 0

    def test_low_coverage(self):
        """Few results should flag low coverage."""
        records = [{"id": "test:1"}, {"id": "test:2"}]
        faults = check_coverage(records, min_results=5)
        assert len(faults) == 1
        assert faults[0].fault_type == FaultType.LOW_COVERAGE

    def test_empty_results_low_coverage(self):
        """Empty results should flag low coverage."""
        faults = check_coverage([], min_results=1)
        assert len(faults) == 1


class TestConfidenceScoring:
    """Tests for confidence score computation."""

    def test_no_faults_full_confidence(self):
        """No faults should give 100% confidence."""
        score = compute_confidence_score([])
        assert score == 100.0

    def test_stale_reduces_score(self):
        """STALE_DOC should reduce score by 15."""
        faults = [VeracityFault(FaultType.STALE_DOC, "test", {})]
        score = compute_confidence_score(faults)
        assert score == 100 - FAULT_PENALTIES[FaultType.STALE_DOC]

    def test_orphan_reduces_score(self):
        """ORPHANED_NODE should reduce score by 5."""
        faults = [VeracityFault(FaultType.ORPHANED_NODE, "test", {})]
        score = compute_confidence_score(faults)
        assert score == 100 - FAULT_PENALTIES[FaultType.ORPHANED_NODE]

    def test_contradiction_reduces_score(self):
        """CONTRADICTION should reduce score by 20."""
        faults = [VeracityFault(FaultType.CONTRADICTION, "test", {})]
        score = compute_confidence_score(faults)
        assert score == 100 - FAULT_PENALTIES[FaultType.CONTRADICTION]

    def test_multiple_faults_cumulative(self):
        """Multiple faults should have cumulative effect."""
        faults = [
            VeracityFault(FaultType.STALE_DOC, "doc 1", {}),
            VeracityFault(FaultType.STALE_DOC, "doc 2", {}),
            VeracityFault(FaultType.ORPHANED_NODE, "node", {}),
        ]
        expected = 100 - (2 * FAULT_PENALTIES[FaultType.STALE_DOC]) - FAULT_PENALTIES[FaultType.ORPHANED_NODE]
        score = compute_confidence_score(faults)
        assert score == max(0, expected)

    def test_score_floors_at_zero(self):
        """Score should not go below 0."""
        # Create many faults to exceed 100 penalty points
        faults = [VeracityFault(FaultType.CONTRADICTION, f"test {i}", {}) for i in range(10)]
        score = compute_confidence_score(faults)
        assert score == 0.0

    def test_deterministic_scoring(self):
        """Same faults should produce same score."""
        faults = [
            VeracityFault(FaultType.STALE_DOC, "doc", {}),
            VeracityFault(FaultType.ORPHANED_NODE, "node", {}),
        ]
        score1 = compute_confidence_score(faults)
        score2 = compute_confidence_score(faults)
        assert score1 == score2


class TestValidateVeracity:
    """Tests for complete veracity validation."""

    def test_complete_validation(self):
        """Should run all checks and return result."""
        now = time.time()
        records = [{
            "node": MockNode(
                labels=["Document"],
                properties={"name": "TEST.md", "last_modified": now - (10 * 24 * 3600)}
            ),
            "id": "test:doc",
            "name": "TEST.md",
            "neighbors": ["a", "b", "c"],
        }]
        result = validate_veracity(records)
        assert isinstance(result, VeracityResult)
        assert result.confidence_score >= 0
        assert result.confidence_score <= 100

    def test_result_includes_faults(self):
        """Result should include detected faults."""
        now = time.time()
        records = [{
            "node": MockNode(
                labels=["Document"],
                properties={"name": "OLD.md", "last_modified": now - (200 * 24 * 3600)}
            ),
            "id": "test:doc",
            "name": "OLD.md",
            "neighbors": [],
        }]
        result = validate_veracity(records)
        assert len(result.faults) > 0

    def test_result_to_dict(self):
        """Result should convert to dictionary."""
        result = VeracityResult(
            confidence_score=85.0,
            is_stale=True,
            faults=[VeracityFault(FaultType.STALE_DOC, "test", {})],
        )
        d = result.to_dict()
        assert d["confidence_score"] == 85.0
        assert d["is_stale"] is True
        assert len(d["faults"]) == 1


# Mock class for testing
class MockNode:
    """Mock Neo4j node for testing."""

    def __init__(self, labels, properties):
        self.labels = labels
        self._properties = properties

    def get(self, key, default=None):
        return self._properties.get(key, default)

    def __getitem__(self, key):
        return self._properties[key]
