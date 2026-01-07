"""
Tests for Evidence Packet Contract (STORY-011).

Tests cover:
1. Schema validation (required/optional fields)
2. Schema versioning
3. Packet hash stability
4. Audit logging format
5. Validation error handling
"""
import pytest
import json
import hashlib
from datetime import datetime

from core.packet_contract import (
    SCHEMA_VERSION,
    PacketMeta,
    CodeResult,
    DocResult,
    VeracityReport,
    EvidencePacketV1,
    validate_packet,
    compute_packet_hash,
    create_audit_entry,
    ValidationError,
    REQUIRED_META_FIELDS,
    REQUIRED_CODE_RESULT_FIELDS,
    REQUIRED_DOC_RESULT_FIELDS,
)


class TestSchemaVersion:
    """Tests for schema versioning."""

    def test_schema_version_is_defined(self):
        """Schema version should be defined."""
        assert SCHEMA_VERSION is not None
        assert isinstance(SCHEMA_VERSION, str)

    def test_schema_version_format(self):
        """Schema version should be in semver format (major.minor)."""
        parts = SCHEMA_VERSION.split(".")
        assert len(parts) == 2
        assert all(p.isdigit() for p in parts)


class TestPacketMeta:
    """Tests for packet metadata."""

    def test_required_fields(self):
        """Meta should have all required fields."""
        meta = PacketMeta(
            schema_version=SCHEMA_VERSION,
            query_id="test-id",
            timestamp="2025-01-01T00:00:00",
            project="test",
            question="test query",
        )
        assert meta.schema_version == SCHEMA_VERSION
        assert meta.query_id == "test-id"
        assert meta.project == "test"

    def test_to_dict(self):
        """Meta should convert to dictionary."""
        meta = PacketMeta(
            schema_version=SCHEMA_VERSION,
            query_id="test-id",
            timestamp="2025-01-01T00:00:00",
            project="test",
            question="test query",
        )
        d = meta.to_dict()
        for field in REQUIRED_META_FIELDS:
            assert field in d


class TestCodeResult:
    """Tests for code result structure."""

    def test_required_fields(self):
        """Code result should have all required fields."""
        result = CodeResult(
            id="test:main.py",
            type=["Function", "Code"],
            path="main.py",
            name="main",
            score=0.95,
        )
        assert result.id == "test:main.py"
        assert result.path == "main.py"

    def test_optional_fields(self):
        """Code result can have optional fields."""
        result = CodeResult(
            id="test:main.py",
            type=["Function"],
            path="main.py",
            name="main",
            score=0.95,
            start_line=10,
            end_line=25,
            excerpt="def main():",
            evidence_hash="abc123",
        )
        assert result.start_line == 10
        assert result.evidence_hash == "abc123"

    def test_to_dict_includes_required(self):
        """to_dict should include all required fields."""
        result = CodeResult(
            id="test:main.py",
            type=["Function"],
            path="main.py",
            name="main",
            score=0.95,
        )
        d = result.to_dict()
        for field in REQUIRED_CODE_RESULT_FIELDS:
            assert field in d


class TestDocResult:
    """Tests for document result structure."""

    def test_required_fields(self):
        """Doc result should have all required fields."""
        result = DocResult(
            id="test:doc:README.md",
            path="README.md",
            name="README.md",
            score=0.85,
        )
        assert result.id == "test:doc:README.md"
        assert result.path == "README.md"

    def test_to_dict_includes_required(self):
        """to_dict should include all required fields."""
        result = DocResult(
            id="test:doc:README.md",
            path="README.md",
            name="README.md",
            score=0.85,
        )
        d = result.to_dict()
        for field in REQUIRED_DOC_RESULT_FIELDS:
            assert field in d


class TestVeracityReport:
    """Tests for veracity report structure."""

    def test_required_fields(self):
        """Veracity report should have required fields."""
        report = VeracityReport(
            confidence_score=95.0,
            is_stale=False,
            faults=[],
        )
        assert report.confidence_score == 95.0
        assert report.is_stale is False

    def test_faults_list(self):
        """Veracity report should support fault list."""
        report = VeracityReport(
            confidence_score=70.0,
            is_stale=True,
            faults=["STALE_DOC: old file", "ORPHANED_NODE: isolated"],
        )
        assert len(report.faults) == 2


class TestEvidencePacketV1:
    """Tests for complete evidence packet."""

    def test_packet_structure(self):
        """Packet should have required structure."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        assert packet.status == "success"
        assert packet.meta.schema_version == SCHEMA_VERSION

    def test_to_dict(self):
        """Packet should convert to dictionary."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        d = packet.to_dict()
        assert "meta" in d
        assert "status" in d
        assert "code_truth" in d
        assert "doc_claims" in d
        assert "veracity" in d


class TestPacketValidation:
    """Tests for packet validation."""

    def test_valid_packet_passes(self):
        """Valid packet should pass validation."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[
                CodeResult(
                    id="test:file.py",
                    type=["Function"],
                    path="file.py",
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
        errors = validate_packet(packet)
        assert errors == []

    def test_missing_meta_field_fails(self):
        """Missing meta field should fail validation."""
        # Create packet with missing project
        packet_dict = {
            "meta": {
                "schema_version": SCHEMA_VERSION,
                "query_id": "test-id",
                "timestamp": "2025-01-01T00:00:00",
                # "project" is missing
                "question": "test query",
            },
            "status": "success",
            "code_truth": [],
            "doc_claims": [],
            "veracity": {
                "confidence_score": 100.0,
                "is_stale": False,
                "faults": [],
            },
        }
        errors = validate_packet(packet_dict)
        assert len(errors) > 0
        assert any("project" in e.lower() for e in errors)

    def test_missing_code_result_field_fails(self):
        """Missing required field in code result should fail."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[
                CodeResult(
                    id="",  # Empty id
                    type=["Function"],
                    path="file.py",
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
        errors = validate_packet(packet)
        assert len(errors) > 0
        assert any("id" in e.lower() for e in errors)

    def test_invalid_schema_version_fails(self):
        """Invalid schema version should fail validation."""
        packet_dict = {
            "meta": {
                "schema_version": "99.99",  # Invalid version
                "query_id": "test-id",
                "timestamp": "2025-01-01T00:00:00",
                "project": "test",
                "question": "test query",
            },
            "status": "success",
            "code_truth": [],
            "doc_claims": [],
            "veracity": {
                "confidence_score": 100.0,
                "is_stale": False,
                "faults": [],
            },
        }
        errors = validate_packet(packet_dict)
        assert len(errors) > 0
        assert any("version" in e.lower() for e in errors)


class TestPacketHash:
    """Tests for packet hash computation."""

    def test_hash_is_sha256(self):
        """Packet hash should be SHA256."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        packet_hash = compute_packet_hash(packet)
        assert len(packet_hash) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in packet_hash)

    def test_same_packet_same_hash(self):
        """Same packet content should produce same hash."""
        packet1 = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="same-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="same query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        packet2 = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="same-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="same query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        assert compute_packet_hash(packet1) == compute_packet_hash(packet2)

    def test_different_content_different_hash(self):
        """Different packet content should produce different hash."""
        packet1 = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="id-1",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="query 1",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        packet2 = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="id-2",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="query 2",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        assert compute_packet_hash(packet1) != compute_packet_hash(packet2)


class TestAuditEntry:
    """Tests for audit log entry creation."""

    def test_audit_entry_structure(self):
        """Audit entry should have required fields."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        entry = create_audit_entry(packet)
        assert "packet_hash" in entry
        assert "logged_at" in entry
        assert "packet" in entry

    def test_audit_entry_includes_hash(self):
        """Audit entry should include packet hash."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(
                confidence_score=100.0,
                is_stale=False,
                faults=[],
            ),
        )
        entry = create_audit_entry(packet)
        expected_hash = compute_packet_hash(packet)
        assert entry["packet_hash"] == expected_hash
