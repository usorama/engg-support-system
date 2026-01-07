"""
Tests for Provenance Module (STORY-009).

Tests cover:
1. Content normalization (LF vs CRLF)
2. Hash computation (file hash, text hash)
3. Provenance record creation
4. Determinism and stability
5. Extractor version tracking
"""
import os
import tempfile
import pytest
from datetime import datetime

from core.provenance import (
    ProvenanceRecord,
    ProvenanceConfig,
    normalize_text_content,
    compute_file_hash,
    compute_text_hash,
    create_provenance_record,
    get_extractor_version,
    validate_provenance,
    provenance_to_dict,
    DEFAULT_EXTRACTOR_NAME,
    DEFAULT_EXTRACTOR_VERSION,
)


class TestContentNormalization:
    """Tests for content normalization."""

    def test_crlf_to_lf(self):
        """CRLF line endings should be normalized to LF."""
        text = "Line 1\r\nLine 2\r\nLine 3"
        normalized = normalize_text_content(text)
        assert "\r\n" not in normalized
        assert normalized == "Line 1\nLine 2\nLine 3"

    def test_cr_to_lf(self):
        """CR line endings should be normalized to LF."""
        text = "Line 1\rLine 2\rLine 3"
        normalized = normalize_text_content(text)
        assert "\r" not in normalized
        assert normalized == "Line 1\nLine 2\nLine 3"

    def test_mixed_endings(self):
        """Mixed line endings should all become LF."""
        text = "Line 1\r\nLine 2\rLine 3\nLine 4"
        normalized = normalize_text_content(text)
        assert "\r" not in normalized
        assert normalized.count("\n") == 3

    def test_lf_unchanged(self):
        """LF line endings should remain unchanged."""
        text = "Line 1\nLine 2\nLine 3"
        normalized = normalize_text_content(text)
        assert normalized == text

    def test_trailing_whitespace_preserved(self):
        """Trailing whitespace should be preserved (no trimming)."""
        text = "Line 1  \nLine 2\t\n"
        normalized = normalize_text_content(text)
        assert "  \n" in normalized
        assert "\t\n" in normalized


class TestFileHash:
    """Tests for file hash computation."""

    def test_hash_is_sha1(self):
        """File hash should be SHA1 hex string."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"Test content")
            temp_path = f.name

        try:
            hash_val = compute_file_hash(temp_path)
            assert len(hash_val) == 40  # SHA1 hex length
            assert all(c in '0123456789abcdef' for c in hash_val)
        finally:
            os.unlink(temp_path)

    def test_same_bytes_same_hash(self):
        """Same bytes should produce same hash."""
        content = b"Deterministic test content"

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(content)
            path2 = f2.name

        try:
            assert compute_file_hash(path1) == compute_file_hash(path2)
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_different_bytes_different_hash(self):
        """Different bytes should produce different hash."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f1:
            f1.write(b"Content A")
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
            f2.write(b"Content B")
            path2 = f2.name

        try:
            assert compute_file_hash(path1) != compute_file_hash(path2)
        finally:
            os.unlink(path1)
            os.unlink(path2)


class TestTextHash:
    """Tests for text hash computation."""

    def test_hash_is_sha256(self):
        """Text hash should be SHA256 hex string."""
        hash_val = compute_text_hash("Test content")
        assert len(hash_val) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in hash_val)

    def test_same_text_same_hash(self):
        """Same text should produce same hash."""
        text = "Deterministic test"
        assert compute_text_hash(text) == compute_text_hash(text)

    def test_different_endings_same_hash(self):
        """Different line endings should produce same hash after normalization."""
        text_lf = "Line 1\nLine 2\nLine 3"
        text_crlf = "Line 1\r\nLine 2\r\nLine 3"
        assert compute_text_hash(text_lf) == compute_text_hash(text_crlf)

    def test_normalize_before_hash(self):
        """Hash should normalize content before computation."""
        text_mixed = "Line 1\r\nLine 2\rLine 3\n"
        text_normalized = "Line 1\nLine 2\nLine 3\n"
        assert compute_text_hash(text_mixed) == compute_text_hash(text_normalized)


class TestProvenanceRecord:
    """Tests for ProvenanceRecord dataclass."""

    def test_record_creation(self):
        """Should create record with all required fields."""
        record = ProvenanceRecord(
            path="src/main.py",
            file_hash="abc123def456",
            text_hash="fedcba654321",
            last_modified=1234567890.0,
            extractor="veracity-engine",
            extractor_version="0.1.0",
        )
        assert record.path == "src/main.py"
        assert record.file_hash == "abc123def456"
        assert record.text_hash == "fedcba654321"
        assert record.last_modified == 1234567890.0
        assert record.extractor == "veracity-engine"
        assert record.extractor_version == "0.1.0"

    def test_record_to_dict(self):
        """Record should convert to dictionary."""
        record = ProvenanceRecord(
            path="test.py",
            file_hash="hash1",
            text_hash="hash2",
            last_modified=1000.0,
            extractor="test",
            extractor_version="1.0",
        )
        d = provenance_to_dict(record)
        assert d["path"] == "test.py"
        assert d["file_hash"] == "hash1"
        assert d["text_hash"] == "hash2"
        assert d["last_modified"] == 1000.0
        assert d["extractor"] == "test"
        assert d["extractor_version"] == "1.0"


class TestCreateProvenanceRecord:
    """Tests for provenance record creation from files."""

    def test_create_from_text_file(self):
        """Should create provenance from text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')\n")
            temp_path = f.name

        try:
            record = create_provenance_record(temp_path)
            assert record.path == temp_path
            assert len(record.file_hash) == 40  # SHA1
            assert len(record.text_hash) == 64  # SHA256
            assert record.last_modified > 0
            assert record.extractor == DEFAULT_EXTRACTOR_NAME
            assert record.extractor_version is not None
        finally:
            os.unlink(temp_path)

    def test_determinism(self):
        """Same file should produce same provenance."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Stable content")
            temp_path = f.name

        try:
            record1 = create_provenance_record(temp_path)
            record2 = create_provenance_record(temp_path)
            assert record1.file_hash == record2.file_hash
            assert record1.text_hash == record2.text_hash
        finally:
            os.unlink(temp_path)

    def test_with_relative_path(self):
        """Should support relative path in record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "src", "app.py")
            os.makedirs(os.path.dirname(file_path))
            with open(file_path, 'w') as f:
                f.write("app = 1")

            record = create_provenance_record(file_path, relative_path="src/app.py")
            assert record.path == "src/app.py"

    def test_binary_file_no_text_hash(self):
        """Binary files should have empty text hash."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
            f.write(b'\x00\x01\x02\x03')
            temp_path = f.name

        try:
            record = create_provenance_record(temp_path, is_binary=True)
            assert len(record.file_hash) == 40  # Still has file hash
            assert record.text_hash == ""  # No text hash for binary
        finally:
            os.unlink(temp_path)


class TestExtractorVersion:
    """Tests for extractor version tracking."""

    def test_default_version(self):
        """Should return default version when env var not set."""
        # Save and clear env var if exists
        old_val = os.environ.get("VERACITY_VERSION")
        if old_val:
            del os.environ["VERACITY_VERSION"]

        try:
            version = get_extractor_version()
            assert version == DEFAULT_EXTRACTOR_VERSION
        finally:
            if old_val:
                os.environ["VERACITY_VERSION"] = old_val

    def test_env_var_version(self):
        """Should use env var when set."""
        old_val = os.environ.get("VERACITY_VERSION")
        os.environ["VERACITY_VERSION"] = "1.2.3-test"

        try:
            version = get_extractor_version()
            assert version == "1.2.3-test"
        finally:
            if old_val:
                os.environ["VERACITY_VERSION"] = old_val
            else:
                del os.environ["VERACITY_VERSION"]


class TestProvenanceValidation:
    """Tests for provenance validation."""

    def test_valid_provenance(self):
        """Valid provenance should pass validation."""
        record = ProvenanceRecord(
            path="test.py",
            file_hash="a" * 40,
            text_hash="b" * 64,
            last_modified=1000.0,
            extractor="test",
            extractor_version="1.0",
        )
        errors = validate_provenance(record)
        assert errors == []

    def test_empty_path_invalid(self):
        """Empty path should fail validation."""
        record = ProvenanceRecord(
            path="",
            file_hash="a" * 40,
            text_hash="b" * 64,
            last_modified=1000.0,
            extractor="test",
            extractor_version="1.0",
        )
        errors = validate_provenance(record)
        assert any("path" in e.lower() for e in errors)

    def test_invalid_file_hash_length(self):
        """Invalid file hash length should fail validation."""
        record = ProvenanceRecord(
            path="test.py",
            file_hash="too_short",
            text_hash="b" * 64,
            last_modified=1000.0,
            extractor="test",
            extractor_version="1.0",
        )
        errors = validate_provenance(record)
        assert any("file_hash" in e.lower() for e in errors)

    def test_negative_timestamp_invalid(self):
        """Negative timestamp should fail validation."""
        record = ProvenanceRecord(
            path="test.py",
            file_hash="a" * 40,
            text_hash="b" * 64,
            last_modified=-1000.0,
            extractor="test",
            extractor_version="1.0",
        )
        errors = validate_provenance(record)
        assert any("modified" in e.lower() for e in errors)


class TestProvenanceConfig:
    """Tests for ProvenanceConfig."""

    def test_default_config(self):
        """Default config should have valid values."""
        config = ProvenanceConfig()
        assert config.extractor_name == DEFAULT_EXTRACTOR_NAME
        assert config.normalize_line_endings is True

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = ProvenanceConfig(
            extractor_name="custom-extractor",
            normalize_line_endings=False,
        )
        assert config.extractor_name == "custom-extractor"
        assert config.normalize_line_endings is False


class TestProvenanceStability:
    """Tests for provenance stability across runs."""

    def test_stable_hashes_same_content(self):
        """Same content should always produce same hashes."""
        content = "def hello():\n    print('world')\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f2:
            f2.write(content)
            path2 = f2.name

        try:
            record1 = create_provenance_record(path1)
            record2 = create_provenance_record(path2)
            assert record1.file_hash == record2.file_hash
            assert record1.text_hash == record2.text_hash
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_content_change_changes_hash(self):
        """Content change should change hashes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("version 1")
            temp_path = f.name

        try:
            record1 = create_provenance_record(temp_path)

            # Modify content
            with open(temp_path, 'w') as f:
                f.write("version 2")

            record2 = create_provenance_record(temp_path)
            assert record1.file_hash != record2.file_hash
            assert record1.text_hash != record2.text_hash
        finally:
            os.unlink(temp_path)

    def test_cross_platform_text_hash(self):
        """Text hash should be consistent regardless of platform line endings."""
        # Simulate content written with different line endings
        content_unix = "line 1\nline 2\nline 3"
        content_windows = "line 1\r\nline 2\r\nline 3"
        content_old_mac = "line 1\rline 2\rline 3"

        hash_unix = compute_text_hash(content_unix)
        hash_windows = compute_text_hash(content_windows)
        hash_old_mac = compute_text_hash(content_old_mac)

        assert hash_unix == hash_windows == hash_old_mac
