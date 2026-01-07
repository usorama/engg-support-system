"""
Tests for Evidence-Only Query Output (STORY-010).

Tests cover:
1. Evidence-only mode default behavior
2. Output schema validation
3. Deterministic ordering
4. Insufficient evidence handling
5. Opt-in synthesis mode
6. Provenance fields in output
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.evidence_query import (
    EvidenceOutputMode,
    EvidenceQueryConfig,
    EvidencePacket,
    CodeEvidence,
    DocEvidence,
    EvidenceResult,
    QueryMeta,
    create_evidence_packet,
    sort_evidence_deterministically,
    format_insufficient_evidence_response,
    validate_evidence_packet,
    DEFAULT_SUGGESTED_ACTIONS,
)


class TestEvidenceOutputMode:
    """Tests for evidence output mode enum."""

    def test_evidence_only_is_default(self):
        """Evidence-only should be the default mode."""
        config = EvidenceQueryConfig()
        assert config.mode == EvidenceOutputMode.EVIDENCE_ONLY

    def test_synthesis_mode_available(self):
        """Synthesis mode should be available as opt-in."""
        config = EvidenceQueryConfig(mode=EvidenceOutputMode.SYNTHESIS)
        assert config.mode == EvidenceOutputMode.SYNTHESIS


class TestEvidenceQueryConfig:
    """Tests for query configuration."""

    def test_default_config(self):
        """Default config should have evidence-only mode."""
        config = EvidenceQueryConfig()
        assert config.mode == EvidenceOutputMode.EVIDENCE_ONLY
        assert config.max_results == 20
        assert config.include_provenance is True

    def test_synthesis_requires_explicit_flag(self):
        """Synthesis mode should require explicit configuration."""
        # Default should not be synthesis
        config = EvidenceQueryConfig()
        assert config.mode != EvidenceOutputMode.SYNTHESIS

        # Explicit synthesis
        config = EvidenceQueryConfig(mode=EvidenceOutputMode.SYNTHESIS)
        assert config.mode == EvidenceOutputMode.SYNTHESIS


class TestCodeEvidence:
    """Tests for code evidence structure."""

    def test_required_fields(self):
        """Code evidence should have required fields."""
        evidence = CodeEvidence(
            id="test:src/main.py",
            path="src/main.py",
            name="main",
            type=["Function", "Code"],
            score=0.95,
        )
        assert evidence.id is not None
        assert evidence.path is not None
        assert evidence.name is not None
        assert evidence.type is not None

    def test_optional_fields(self):
        """Code evidence can have optional fields."""
        evidence = CodeEvidence(
            id="test:src/main.py",
            path="src/main.py",
            name="main",
            type=["Function", "Code"],
            score=0.95,
            start_line=10,
            end_line=25,
            docstring="Main function",
            prov_file_hash="abc123",
        )
        assert evidence.start_line == 10
        assert evidence.end_line == 25
        assert evidence.docstring == "Main function"
        assert evidence.prov_file_hash == "abc123"

    def test_to_dict(self):
        """Code evidence should convert to dictionary."""
        evidence = CodeEvidence(
            id="test:src/main.py",
            path="src/main.py",
            name="main",
            type=["Function"],
            score=0.95,
        )
        d = evidence.to_dict()
        assert d["id"] == "test:src/main.py"
        assert d["path"] == "src/main.py"
        assert d["name"] == "main"


class TestDocEvidence:
    """Tests for document evidence structure."""

    def test_required_fields(self):
        """Doc evidence should have required fields."""
        evidence = DocEvidence(
            id="test:doc:README.md",
            path="README.md",
            name="README.md",
            score=0.85,
        )
        assert evidence.id is not None
        assert evidence.path is not None

    def test_last_modified_field(self):
        """Doc evidence should include last_modified."""
        evidence = DocEvidence(
            id="test:doc:README.md",
            path="README.md",
            name="README.md",
            score=0.85,
            last_modified=1234567890.0,
        )
        assert evidence.last_modified == 1234567890.0


class TestDeterministicOrdering:
    """Tests for deterministic result ordering."""

    def test_sort_by_score_desc(self):
        """Results should be sorted by score descending."""
        evidence = [
            CodeEvidence(id="a", path="a.py", name="a", type=["Code"], score=0.5),
            CodeEvidence(id="b", path="b.py", name="b", type=["Code"], score=0.9),
            CodeEvidence(id="c", path="c.py", name="c", type=["Code"], score=0.7),
        ]
        sorted_evidence = sort_evidence_deterministically(evidence)
        scores = [e.score for e in sorted_evidence]
        assert scores == [0.9, 0.7, 0.5]

    def test_sort_by_path_asc_when_score_equal(self):
        """Equal scores should sort by path ascending."""
        evidence = [
            CodeEvidence(id="c", path="z.py", name="z", type=["Code"], score=0.8),
            CodeEvidence(id="a", path="a.py", name="a", type=["Code"], score=0.8),
            CodeEvidence(id="b", path="m.py", name="m", type=["Code"], score=0.8),
        ]
        sorted_evidence = sort_evidence_deterministically(evidence)
        paths = [e.path for e in sorted_evidence]
        assert paths == ["a.py", "m.py", "z.py"]

    def test_sort_by_id_when_score_and_path_equal(self):
        """Equal scores and paths should sort by id ascending."""
        evidence = [
            CodeEvidence(id="c:same.py", path="same.py", name="x", type=["Code"], score=0.8),
            CodeEvidence(id="a:same.py", path="same.py", name="x", type=["Code"], score=0.8),
            CodeEvidence(id="b:same.py", path="same.py", name="x", type=["Code"], score=0.8),
        ]
        sorted_evidence = sort_evidence_deterministically(evidence)
        ids = [e.id for e in sorted_evidence]
        assert ids == ["a:same.py", "b:same.py", "c:same.py"]

    def test_deterministic_ordering_reproducible(self):
        """Same input should always produce same output."""
        evidence = [
            CodeEvidence(id="x", path="x.py", name="x", type=["Code"], score=0.5),
            CodeEvidence(id="y", path="y.py", name="y", type=["Code"], score=0.9),
            CodeEvidence(id="z", path="a.py", name="z", type=["Code"], score=0.9),
        ]

        sorted1 = sort_evidence_deterministically(evidence)
        sorted2 = sort_evidence_deterministically(evidence)

        assert [e.id for e in sorted1] == [e.id for e in sorted2]


class TestInsufficientEvidence:
    """Tests for insufficient evidence handling."""

    def test_insufficient_evidence_status(self):
        """Should return insufficient_evidence status when no results."""
        response = format_insufficient_evidence_response(
            query="nonexistent query",
            project="test",
        )
        assert response["status"] == "insufficient_evidence"

    def test_suggested_actions_not_llm_generated(self):
        """Suggested actions should be predefined, not LLM-generated."""
        response = format_insufficient_evidence_response(
            query="test",
            project="test",
        )
        for action in response["suggested_actions"]:
            assert action in DEFAULT_SUGGESTED_ACTIONS

    def test_empty_results_arrays(self):
        """Insufficient evidence should have empty result arrays."""
        response = format_insufficient_evidence_response(
            query="test",
            project="test",
        )
        assert response["code_truth"] == []
        assert response["doc_claims"] == []


class TestEvidencePacket:
    """Tests for evidence packet structure."""

    def test_packet_has_meta(self):
        """Packet should include meta information."""
        packet = EvidencePacket(
            meta=QueryMeta(
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
                mode=EvidenceOutputMode.EVIDENCE_ONLY,
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            context_veracity={"confidence_score": 100, "faults": []},
        )
        assert packet.meta.query_id == "test-id"
        assert packet.meta.mode == EvidenceOutputMode.EVIDENCE_ONLY

    def test_packet_no_technical_brief_in_evidence_only(self):
        """Evidence-only packet should not have technical_brief."""
        packet = EvidencePacket(
            meta=QueryMeta(
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
                mode=EvidenceOutputMode.EVIDENCE_ONLY,
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            context_veracity={"confidence_score": 100, "faults": []},
        )
        assert packet.technical_brief is None

    def test_packet_to_dict(self):
        """Packet should convert to dictionary."""
        packet = EvidencePacket(
            meta=QueryMeta(
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
                mode=EvidenceOutputMode.EVIDENCE_ONLY,
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            context_veracity={"confidence_score": 100, "faults": []},
        )
        d = packet.to_dict()
        assert "meta" in d
        assert "status" in d
        assert "code_truth" in d
        assert "technical_brief" not in d  # Should not include None fields


class TestPacketValidation:
    """Tests for evidence packet validation."""

    def test_valid_packet_passes(self):
        """Valid packet should pass validation."""
        packet = EvidencePacket(
            meta=QueryMeta(
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
                mode=EvidenceOutputMode.EVIDENCE_ONLY,
            ),
            status="success",
            code_truth=[
                CodeEvidence(
                    id="test:file.py",
                    path="file.py",
                    name="func",
                    type=["Function"],
                    score=0.9,
                )
            ],
            doc_claims=[],
            context_veracity={"confidence_score": 100, "faults": []},
        )
        errors = validate_evidence_packet(packet)
        assert errors == []

    def test_missing_id_fails(self):
        """Evidence without id should fail validation."""
        packet = EvidencePacket(
            meta=QueryMeta(
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
                mode=EvidenceOutputMode.EVIDENCE_ONLY,
            ),
            status="success",
            code_truth=[
                CodeEvidence(
                    id="",  # Empty id
                    path="file.py",
                    name="func",
                    type=["Function"],
                    score=0.9,
                )
            ],
            doc_claims=[],
            context_veracity={"confidence_score": 100, "faults": []},
        )
        errors = validate_evidence_packet(packet)
        assert len(errors) > 0
        assert any("id" in e.lower() for e in errors)

    def test_missing_path_fails(self):
        """Evidence without path should fail validation."""
        packet = EvidencePacket(
            meta=QueryMeta(
                query_id="test-id",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="test query",
                mode=EvidenceOutputMode.EVIDENCE_ONLY,
            ),
            status="success",
            code_truth=[
                CodeEvidence(
                    id="test:file.py",
                    path="",  # Empty path
                    name="func",
                    type=["Function"],
                    score=0.9,
                )
            ],
            doc_claims=[],
            context_veracity={"confidence_score": 100, "faults": []},
        )
        errors = validate_evidence_packet(packet)
        assert len(errors) > 0
        assert any("path" in e.lower() for e in errors)


class TestCreateEvidencePacket:
    """Tests for evidence packet creation."""

    def test_creates_valid_packet(self):
        """Should create a valid evidence packet."""
        code_evidence = [
            CodeEvidence(
                id="test:main.py",
                path="main.py",
                name="main",
                type=["Function"],
                score=0.95,
            )
        ]
        packet = create_evidence_packet(
            query="test query",
            project="test",
            code_truth=code_evidence,
            doc_claims=[],
            veracity={"confidence_score": 100, "faults": []},
        )
        assert packet.status == "success"
        assert len(packet.code_truth) == 1

    def test_evidence_only_mode_set(self):
        """Packet should have evidence-only mode by default."""
        packet = create_evidence_packet(
            query="test query",
            project="test",
            code_truth=[],
            doc_claims=[],
            veracity={"confidence_score": 0, "faults": []},
        )
        assert packet.meta.mode == EvidenceOutputMode.EVIDENCE_ONLY


class TestProvenanceInOutput:
    """Tests for provenance fields in evidence output."""

    def test_code_evidence_includes_provenance(self):
        """Code evidence can include provenance fields."""
        evidence = CodeEvidence(
            id="test:src/main.py",
            path="src/main.py",
            name="main",
            type=["Function"],
            score=0.95,
            prov_file_hash="abc123def456",
            prov_text_hash="fedcba654321",
            prov_extractor_version="0.1.0",
        )
        d = evidence.to_dict()
        assert d.get("prov_file_hash") == "abc123def456"
        assert d.get("prov_text_hash") == "fedcba654321"
        assert d.get("prov_extractor_version") == "0.1.0"

    def test_doc_evidence_includes_provenance(self):
        """Doc evidence can include provenance fields."""
        evidence = DocEvidence(
            id="test:doc:README.md",
            path="README.md",
            name="README.md",
            score=0.85,
            prov_file_hash="abc123",
            prov_last_modified=1234567890.0,
        )
        d = evidence.to_dict()
        assert d.get("prov_file_hash") == "abc123"
        assert d.get("prov_last_modified") == 1234567890.0
