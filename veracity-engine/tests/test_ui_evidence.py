"""
Tests for UI Evidence & Provenance Surface (STORY-015).

Tests cover:
1. Evidence packet structure for UI consumption
2. Provenance field formatting
3. Veracity display formatting
4. Evidence sorting and filtering
5. UI data contract validation
"""
import pytest
import json
from datetime import datetime, timedelta

from core.packet_contract import (
    SCHEMA_VERSION,
    PacketMeta,
    CodeResult,
    DocResult,
    VeracityReport,
    EvidencePacketV1,
    validate_packet,
    compute_packet_hash,
)
from core.veracity import (
    FaultType,
    VeracityFault,
    VeracityResult,
    FAULT_PENALTIES,
)


class TestUIPacketStructure:
    """Tests for evidence packet UI data structure."""

    def test_packet_has_ui_required_fields(self):
        """Packet should have all fields required by UI."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test-project",
                question="What is X?",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=85.0,
                is_stale=False,
                faults=[],
            ),
        )
        d = packet.to_dict()

        # UI requires these top-level keys
        assert "meta" in d
        assert "status" in d
        assert "code_truth" in d
        assert "doc_claims" in d
        assert "veracity" in d

    def test_meta_has_ui_fields(self):
        """Meta should have fields needed for UI header."""
        meta = PacketMeta(
            schema_version=SCHEMA_VERSION,
            query_id="ui-test-123",
            timestamp="2025-01-01T12:00:00",
            project="my-project",
            question="How does feature X work?",
            mode="evidence_only",
        )
        d = meta.to_dict()

        # UI header displays these
        assert "schema_version" in d
        assert "query_id" in d
        assert "project" in d
        assert "question" in d

    def test_code_result_has_display_fields(self):
        """Code result should have fields for UI display."""
        result = CodeResult(
            id="test:func:main",
            type=["Function", "Code"],
            path="src/main.py",
            name="main",
            score=0.95,
            start_line=10,
            end_line=25,
            excerpt="def main():\n    pass",
            evidence_hash="abc123",
            docstring="Main entry point",
        )
        d = result.to_dict()

        # UI evidence item displays these
        assert d["id"] == "test:func:main"
        assert d["name"] == "main"
        assert d["path"] == "src/main.py"
        assert d["score"] == 0.95
        assert d["start_line"] == 10
        assert d["end_line"] == 25
        assert "excerpt" in d
        assert "evidence_hash" in d

    def test_doc_result_has_display_fields(self):
        """Doc result should have fields for UI display."""
        result = DocResult(
            id="test:doc:README.md",
            path="README.md",
            name="README.md",
            score=0.85,
            last_modified=1704067200.0,  # 2024-01-01
            doc_type="documentation",
            excerpt="# Project Title",
        )
        d = result.to_dict()

        # UI doc evidence displays these
        assert d["id"] == "test:doc:README.md"
        assert d["name"] == "README.md"
        assert d["score"] == 0.85
        assert "last_modified" in d
        assert "doc_type" in d


class TestUIProvenanceFields:
    """Tests for provenance field formatting for UI."""

    def test_code_result_has_provenance_fields(self):
        """Code result should include provenance for UI."""
        result = CodeResult(
            id="test:func",
            type=["Function"],
            path="main.py",
            name="func",
            score=0.9,
            prov_file_hash="sha1abc123",
            prov_text_hash="sha256def456",
        )
        d = result.to_dict()

        assert "prov_file_hash" in d
        assert "prov_text_hash" in d

    def test_doc_result_has_provenance_fields(self):
        """Doc result should include provenance for UI."""
        result = DocResult(
            id="test:doc",
            path="doc.md",
            name="doc.md",
            score=0.8,
            prov_file_hash="sha1xyz789",
            prov_text_hash="sha256uvw012",
        )
        d = result.to_dict()

        assert "prov_file_hash" in d
        assert "prov_text_hash" in d


class TestUIVeracityDisplay:
    """Tests for veracity data formatting for UI."""

    def test_veracity_report_has_ui_fields(self):
        """Veracity report should have UI display fields."""
        report = VeracityReport(
            confidence_score=75.0,
            is_stale=True,
            faults=["STALE_DOC: old file"],
        )
        d = report.to_dict()

        assert "confidence_score" in d
        assert "is_stale" in d
        assert "faults" in d

    def test_confidence_score_range(self):
        """Confidence score should be 0-100."""
        report = VeracityReport(
            confidence_score=85.5,
            is_stale=False,
            faults=[],
        )
        assert 0 <= report.confidence_score <= 100

    def test_fault_messages_serializable(self):
        """Fault messages should be JSON serializable for UI."""
        faults = [
            "STALE_DOC: README.md is 120 days old",
            "ORPHANED_NODE: isolated_func has low connectivity",
        ]
        report = VeracityReport(
            confidence_score=70.0,
            is_stale=True,
            faults=faults,
        )
        d = report.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["faults"] == faults


class TestUIEvidenceSorting:
    """Tests for evidence sorting as expected by UI."""

    def test_evidence_sortable_by_score(self):
        """Evidence should be sortable by score descending."""
        results = [
            CodeResult(id="a", type=["F"], path="a.py", name="a", score=0.7),
            CodeResult(id="b", type=["F"], path="b.py", name="b", score=0.9),
            CodeResult(id="c", type=["F"], path="c.py", name="c", score=0.8),
        ]
        sorted_results = sorted(results, key=lambda r: -r.score)

        assert sorted_results[0].score == 0.9
        assert sorted_results[1].score == 0.8
        assert sorted_results[2].score == 0.7

    def test_evidence_sortable_by_path(self):
        """Evidence with equal scores should sort by path."""
        results = [
            CodeResult(id="c", type=["F"], path="c.py", name="c", score=0.8),
            CodeResult(id="a", type=["F"], path="a.py", name="a", score=0.8),
            CodeResult(id="b", type=["F"], path="b.py", name="b", score=0.8),
        ]
        sorted_results = sorted(results, key=lambda r: (-r.score, r.path))

        assert sorted_results[0].path == "a.py"
        assert sorted_results[1].path == "b.py"
        assert sorted_results[2].path == "c.py"


class TestUIDataContract:
    """Tests for UI data contract validation."""

    def test_packet_to_json_serializable(self):
        """Complete packet should be JSON serializable."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="json-test",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[
                CodeResult(
                    id="test:func",
                    type=["Function"],
                    path="main.py",
                    name="func",
                    score=0.9,
                )
            ],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        d = packet.to_dict()

        # Should serialize without error
        json_str = json.dumps(d)
        assert json_str is not None

        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"

    def test_empty_evidence_arrays_valid(self):
        """Empty evidence arrays should be valid for UI."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="empty-test",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test",
            ),
            status="insufficient_evidence",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=50.0,
                is_stale=False,
                faults=["LOW_COVERAGE: Only 0 results found"],
            ),
        )
        errors = validate_packet(packet)
        assert errors == []

    def test_type_labels_are_arrays(self):
        """Type labels should be arrays for UI badge display."""
        result = CodeResult(
            id="test",
            type=["Function", "Code", "Async"],
            path="main.py",
            name="func",
            score=0.9,
        )
        d = result.to_dict()

        assert isinstance(d["type"], list)
        assert len(d["type"]) == 3

    def test_neighbors_list_serializable(self):
        """Neighbors list should be serializable."""
        result = CodeResult(
            id="test",
            type=["Function"],
            path="main.py",
            name="func",
            score=0.9,
            neighbors=["helper", "util", "config"],
        )
        d = result.to_dict()

        assert isinstance(d["neighbors"], list)
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["neighbors"] == ["helper", "util", "config"]


class TestUIFreshnessCalculation:
    """Tests for freshness calculation matching UI logic."""

    def test_fresh_document(self):
        """Document modified recently should be fresh."""
        now = datetime.now().timestamp()
        result = DocResult(
            id="test:doc",
            path="fresh.md",
            name="fresh.md",
            score=0.9,
            last_modified=now - (3 * 86400),  # 3 days ago
        )

        # UI considers <7 days as fresh (green)
        age_days = (now - result.last_modified) / 86400
        assert age_days < 7

    def test_recent_document(self):
        """Document modified within month should be recent."""
        now = datetime.now().timestamp()
        result = DocResult(
            id="test:doc",
            path="recent.md",
            name="recent.md",
            score=0.9,
            last_modified=now - (15 * 86400),  # 15 days ago
        )

        # UI considers 7-30 days as recent (yellow)
        age_days = (now - result.last_modified) / 86400
        assert 7 <= age_days < 30

    def test_stale_document(self):
        """Document modified long ago should be stale."""
        now = datetime.now().timestamp()
        result = DocResult(
            id="test:doc",
            path="stale.md",
            name="stale.md",
            score=0.9,
            last_modified=now - (100 * 86400),  # 100 days ago
        )

        # UI considers >30 days as stale (red)
        age_days = (now - result.last_modified) / 86400
        assert age_days > 30


class TestUIFaultDisplay:
    """Tests for fault display formatting."""

    def test_fault_type_extractable(self):
        """Fault type should be extractable from message."""
        fault_messages = [
            "STALE_DOC: README.md is old",
            "ORPHANED_NODE: func has low connectivity",
            "CONTRADICTION: doc/code mismatch",
            "LOW_COVERAGE: insufficient results",
        ]

        for msg in fault_messages:
            # UI extracts type before colon
            fault_type = msg.split(":")[0]
            assert fault_type in ["STALE_DOC", "ORPHANED_NODE", "CONTRADICTION", "LOW_COVERAGE"]

    def test_fault_penalties_match_ui_display(self):
        """Fault penalties should be displayable."""
        # UI might show penalty impact
        assert FAULT_PENALTIES[FaultType.STALE_DOC] == 15
        assert FAULT_PENALTIES[FaultType.ORPHANED_NODE] == 5
        assert FAULT_PENALTIES[FaultType.CONTRADICTION] == 20
        assert FAULT_PENALTIES[FaultType.LOW_COVERAGE] == 10

    def test_veracity_fault_to_dict(self):
        """VeracityFault should convert to UI-friendly dict."""
        fault = VeracityFault(
            fault_type=FaultType.STALE_DOC,
            message="README.md is 100 days old",
            evidence={"node_id": "test:doc", "days_old": 100},
        )
        d = fault.to_dict()

        assert d["type"] == "STALE_DOC"
        assert "message" in d
        assert "evidence" in d
