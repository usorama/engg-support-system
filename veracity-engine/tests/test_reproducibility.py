"""
Tests for Reproducibility and Determinism (STORY-016).

Tests cover:
1. File ingestion determinism (same inputs = same outputs)
2. Chunking determinism (stable chunk IDs)
3. Provenance hashing determinism (cross-platform stability)
4. Evidence packet determinism (stable hashes)
5. Veracity scoring determinism (same faults = same score)
6. Repo map determinism (stable ranking)
"""
import pytest
import os
import tempfile
from pathlib import Path

from core.file_ingestion import (
    discover_files,
    classify_file,
    extract_file_metadata,
    FileCategory,
)
from core.chunking import (
    ChunkingConfig,
    SplitStrategy,
    generate_chunk_id,
    chunk_text,
    chunk_file_content,
)
from core.provenance import (
    normalize_text_content,
    compute_file_hash,
    compute_text_hash,
    create_provenance_record,
)
from core.packet_contract import (
    EvidencePacketV1,
    PacketMeta,
    CodeResult,
    DocResult,
    VeracityReport,
    compute_packet_hash,
    SCHEMA_VERSION,
)
from core.veracity import (
    VeracityConfig,
    VeracityFault,
    FaultType,
    check_staleness,
    check_orphans,
    compute_confidence_score,
    validate_veracity,
)
from core.repo_map import (
    extract_symbols_from_file,
    compute_pagerank,
    generate_repo_map,
    DependencyEdge,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_repo"


class TestFileIngestionDeterminism:
    """Tests for file ingestion reproducibility."""

    def test_discover_files_same_order(self):
        """File discovery should return same order on repeated calls."""
        if not FIXTURE_DIR.exists():
            pytest.skip("Fixture directory not available")

        files1 = discover_files(str(FIXTURE_DIR))
        files2 = discover_files(str(FIXTURE_DIR))

        assert files1 == files2

    def test_file_classification_deterministic(self):
        """File classification should be deterministic."""
        test_cases = [
            ("/path/to/main.py", "main.py", ".py", FileCategory.CODE),
            ("/path/to/README.md", "README.md", ".md", FileCategory.DOCUMENTATION),
            ("/path/to/config.yaml", "config.yaml", ".yaml", FileCategory.CONFIG),
            ("/path/to/data.csv", "data.csv", ".csv", FileCategory.DATA),
        ]

        for path, name, ext, expected in test_cases:
            result1, _ = classify_file(path, name, ext)
            result2, _ = classify_file(path, name, ext)
            assert result1 == result2 == expected

    def test_metadata_extraction_stable(self):
        """File metadata should be identical on repeated extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, 'w') as f:
                f.write("def test(): pass\n")

            meta1 = extract_file_metadata(tmpdir, file_path)
            meta2 = extract_file_metadata(tmpdir, file_path)

            # Hash and size should be identical
            assert meta1.content_hash == meta2.content_hash
            assert meta1.size_bytes == meta2.size_bytes
            assert meta1.mime_type == meta2.mime_type


class TestChunkingDeterminism:
    """Tests for chunking reproducibility."""

    def test_chunk_id_deterministic(self):
        """Chunk IDs should be identical for same inputs."""
        id1 = generate_chunk_id("test.py", 0, "content hash")
        id2 = generate_chunk_id("test.py", 0, "content hash")
        assert id1 == id2

    def test_chunk_id_different_for_different_index(self):
        """Different chunk indices should produce different IDs."""
        id1 = generate_chunk_id("test.py", 0, "hash")
        id2 = generate_chunk_id("test.py", 1, "hash")
        assert id1 != id2

    def test_chunk_text_deterministic(self):
        """Text chunking should be deterministic."""
        content = "Line 1\n\nLine 2\n\nLine 3"
        config = ChunkingConfig(
            chunk_size=500,
            overlap=50,
            split_strategy=SplitStrategy.PARAGRAPH
        )

        result1 = chunk_text(content, "test.py", "test-project", config)
        result2 = chunk_text(content, "test.py", "test-project", config)

        assert len(result1) == len(result2)
        for c1, c2 in zip(result1, result2):
            assert c1.content == c2.content
            assert c1.metadata.chunk_index == c2.metadata.chunk_index

    def test_chunk_file_content_stable_ids(self):
        """File chunking should produce stable IDs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            content = "def a(): pass\n\ndef b(): pass\n\ndef c(): pass\n"
            f.write(content)
            f.flush()

            result1 = chunk_file_content(content, f.name, "test-project", ".py")
            result2 = chunk_file_content(content, f.name, "test-project", ".py")

        os.unlink(f.name)

        assert len(result1.chunks) == len(result2.chunks)
        for c1, c2 in zip(result1.chunks, result2.chunks):
            assert c1.metadata.chunk_id == c2.metadata.chunk_id


class TestProvenanceDeterminism:
    """Tests for provenance hashing reproducibility."""

    def test_normalize_text_idempotent(self):
        """Text normalization should be idempotent."""
        text = "Line 1\r\nLine 2\rLine 3\n"
        normalized1 = normalize_text_content(text)
        normalized2 = normalize_text_content(normalized1)
        assert normalized1 == normalized2

    def test_file_hash_stable(self):
        """File hash should be stable for unchanged file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            f.flush()

            hash1 = compute_file_hash(f.name)
            hash2 = compute_file_hash(f.name)

        os.unlink(f.name)
        assert hash1 == hash2

    def test_text_hash_cross_platform(self):
        """Text hash should be identical regardless of line endings."""
        content_lf = "Line 1\nLine 2\n"
        content_crlf = "Line 1\r\nLine 2\r\n"
        content_cr = "Line 1\rLine 2\r"

        hash_lf = compute_text_hash(content_lf)
        hash_crlf = compute_text_hash(content_crlf)
        hash_cr = compute_text_hash(content_cr)

        assert hash_lf == hash_crlf == hash_cr

    def test_provenance_record_stable(self):
        """Provenance record should be stable for unchanged file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass\n")
            f.flush()

            record1 = create_provenance_record(f.name)
            record2 = create_provenance_record(f.name)

        os.unlink(f.name)

        assert record1.file_hash == record2.file_hash
        assert record1.text_hash == record2.text_hash


class TestPacketDeterminism:
    """Tests for evidence packet reproducibility."""

    def test_packet_hash_deterministic(self):
        """Same packet content should produce same hash."""
        packet = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="determinism-test",
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
                    name="main",
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

        hash1 = compute_packet_hash(packet)
        hash2 = compute_packet_hash(packet)
        assert hash1 == hash2

    def test_packet_hash_different_for_different_content(self):
        """Different packet content should produce different hash."""
        packet1 = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-1",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="query 1",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(confidence_score=100.0, is_stale=False, faults=[]),
        )
        packet2 = EvidencePacketV1(
            meta=PacketMeta(
                schema_version=SCHEMA_VERSION,
                query_id="test-2",
                timestamp="2025-01-01T00:00:00",
                project="test",
                question="query 2",
            ),
            status="success",
            code_truth=[],
            doc_claims=[],
            veracity=VeracityReport(confidence_score=100.0, is_stale=False, faults=[]),
        )

        hash1 = compute_packet_hash(packet1)
        hash2 = compute_packet_hash(packet2)
        assert hash1 != hash2


class TestVeracityDeterminism:
    """Tests for veracity scoring reproducibility."""

    def test_confidence_score_deterministic(self):
        """Same faults should produce same confidence score."""
        faults = [
            VeracityFault(FaultType.STALE_DOC, "test doc", {}),
            VeracityFault(FaultType.ORPHANED_NODE, "test node", {}),
        ]

        score1 = compute_confidence_score(faults)
        score2 = compute_confidence_score(faults)
        assert score1 == score2

    def test_validate_veracity_deterministic(self):
        """Veracity validation should be deterministic."""
        # Create mock records
        import time
        now = time.time()

        class MockNode:
            def __init__(self, labels, props):
                self.labels = labels
                self._props = props

            def get(self, key, default=None):
                return self._props.get(key, default)

        records = [
            {
                "node": MockNode(
                    ["Document"],
                    {"name": "test.md", "last_modified": now - (100 * 86400)}
                ),
                "id": "test:doc",
                "name": "test.md",
                "neighbors": [],
            }
        ]

        config = VeracityConfig(staleness_days=90)

        result1 = validate_veracity(records, config)
        result2 = validate_veracity(records, config)

        assert result1.confidence_score == result2.confidence_score
        assert result1.is_stale == result2.is_stale
        assert len(result1.faults) == len(result2.faults)


class TestRepoMapDeterminism:
    """Tests for repo map reproducibility."""

    def test_pagerank_deterministic(self):
        """PageRank should produce identical ranks."""
        nodes = ["a.py", "b.py", "c.py"]
        edges = [
            DependencyEdge(source="a.py", target="b.py"),
            DependencyEdge(source="b.py", target="c.py"),
        ]

        ranks1 = compute_pagerank(nodes, edges)
        ranks2 = compute_pagerank(nodes, edges)

        for node in nodes:
            assert ranks1[node] == ranks2[node]

    def test_symbol_extraction_deterministic(self):
        """Symbol extraction should be deterministic."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def alpha(): pass
def beta(): pass
class Gamma:
    def delta(self): pass
''')
            f.flush()

            symbols1 = extract_symbols_from_file(f.name)
            symbols2 = extract_symbols_from_file(f.name)

        os.unlink(f.name)

        assert len(symbols1) == len(symbols2)
        for s1, s2 in zip(symbols1, symbols2):
            assert s1.symbol == s2.symbol
            assert s1.kind == s2.kind

    def test_repo_map_deterministic(self):
        """Repo map generation should be deterministic."""
        if not FIXTURE_DIR.exists():
            pytest.skip("Fixture directory not available")

        result1 = generate_repo_map(str(FIXTURE_DIR))
        result2 = generate_repo_map(str(FIXTURE_DIR))

        assert result1.total_symbols == result2.total_symbols
        assert len(result1.entries) == len(result2.entries)

        for e1, e2 in zip(result1.entries, result2.entries):
            assert e1.symbol == e2.symbol
            assert e1.rank == e2.rank


class TestFixtureIntegrity:
    """Tests for fixture repo integrity."""

    def test_fixture_files_exist(self):
        """Fixture files should exist."""
        if not FIXTURE_DIR.exists():
            pytest.skip("Fixture directory not available")

        expected_files = [
            "README.md",
            "src/main.py",
            "src/utils.py",
            "src/config.py",
            "docs/API.md",
        ]

        for file in expected_files:
            path = FIXTURE_DIR / file
            assert path.exists(), f"Missing fixture file: {file}"

    def test_fixture_python_parseable(self):
        """Fixture Python files should be parseable."""
        if not FIXTURE_DIR.exists():
            pytest.skip("Fixture directory not available")

        python_files = [
            "src/main.py",
            "src/utils.py",
            "src/config.py",
        ]

        import ast
        for file in python_files:
            path = FIXTURE_DIR / file
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()
                # Should not raise
                ast.parse(content)
