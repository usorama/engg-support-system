"""
Tests for Deterministic Chunking Module (STORY-008).

Tests cover:
1. Chunk ID generation (determinism)
2. Chunking with various strategies
3. Configuration validation
4. Content hashing
5. Overlap handling
"""
import pytest

from core.chunking import (
    SplitStrategy,
    ChunkMetadata,
    Chunk,
    ChunkingConfig,
    ChunkingResult,
    compute_content_hash,
    generate_chunk_id,
    find_split_points,
    find_best_split_point,
    chunk_text,
    rechunk_if_changed,
    chunk_file_content,
    get_config_for_extension,
    DEFAULT_CONFIGS,
)


class TestContentHashing:
    """Tests for content hashing."""

    def test_hash_is_sha256(self):
        """Hash should be a valid SHA256 hex string."""
        hash_val = compute_content_hash("test content")
        assert len(hash_val) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in hash_val)

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        content = "Deterministic test content"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        hash1 = compute_content_hash("content A")
        hash2 = compute_content_hash("content B")
        assert hash1 != hash2


class TestChunkIdGeneration:
    """Tests for chunk ID generation."""

    def test_id_is_deterministic(self):
        """Same inputs should produce same ID."""
        id1 = generate_chunk_id("file.py", 0, "abc123")
        id2 = generate_chunk_id("file.py", 0, "abc123")
        assert id1 == id2

    def test_different_index_different_id(self):
        """Different chunk index should produce different ID."""
        id1 = generate_chunk_id("file.py", 0, "abc123")
        id2 = generate_chunk_id("file.py", 1, "abc123")
        assert id1 != id2

    def test_different_path_different_id(self):
        """Different source path should produce different ID."""
        id1 = generate_chunk_id("file_a.py", 0, "abc123")
        id2 = generate_chunk_id("file_b.py", 0, "abc123")
        assert id1 != id2

    def test_different_content_different_id(self):
        """Different content hash should produce different ID."""
        id1 = generate_chunk_id("file.py", 0, "hash_a")
        id2 = generate_chunk_id("file.py", 0, "hash_b")
        assert id1 != id2

    def test_id_length(self):
        """ID should be 16 characters (truncated SHA256)."""
        chunk_id = generate_chunk_id("file.py", 0, "abc123")
        assert len(chunk_id) == 16


class TestChunkingConfig:
    """Tests for chunking configuration."""

    def test_default_values(self):
        """Default config should have valid values."""
        config = ChunkingConfig()
        assert config.chunk_size == 1200
        assert config.overlap == 200
        assert config.min_chunk_size == 100
        config.validate()  # Should not raise

    def test_invalid_chunk_size(self):
        """Zero or negative chunk size should fail validation."""
        config = ChunkingConfig(chunk_size=0)
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            config.validate()

    def test_overlap_exceeds_size(self):
        """Overlap >= chunk size should fail validation."""
        config = ChunkingConfig(chunk_size=100, overlap=100)
        with pytest.raises(ValueError, match="overlap must be less than"):
            config.validate()

    def test_negative_overlap(self):
        """Negative overlap should fail validation."""
        config = ChunkingConfig(overlap=-1)
        with pytest.raises(ValueError, match="overlap cannot be negative"):
            config.validate()


class TestSplitPoints:
    """Tests for split point detection."""

    def test_paragraph_splits(self):
        """Should find paragraph boundaries."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird."
        splits = find_split_points(text, SplitStrategy.PARAGRAPH)
        assert len(splits) == 2

    def test_line_splits(self):
        """Should find line boundaries."""
        text = "Line 1\nLine 2\nLine 3"
        splits = find_split_points(text, SplitStrategy.LINE)
        assert len(splits) == 2

    def test_sentence_splits(self):
        """Should find sentence boundaries."""
        text = "First sentence. Second sentence! Third sentence?"
        splits = find_split_points(text, SplitStrategy.SENTENCE)
        assert len(splits) >= 2

    def test_fixed_strategy_no_splits(self):
        """FIXED strategy should return no split points."""
        text = "Some text\n\nwith breaks"
        splits = find_split_points(text, SplitStrategy.FIXED)
        assert splits == []


class TestBestSplitPoint:
    """Tests for finding best split point."""

    def test_finds_nearby_split(self):
        """Should find split point within tolerance."""
        split_points = [100, 200, 300]
        result = find_best_split_point("text", 195, split_points, tolerance=50)
        assert result == 200

    def test_falls_back_to_target(self):
        """Should use target when no splits in tolerance."""
        split_points = [50, 300]
        result = find_best_split_point("text", 150, split_points, tolerance=10)
        assert result == 150

    def test_chooses_closest(self):
        """Should choose closest split point."""
        split_points = [95, 105]
        result = find_best_split_point("text", 100, split_points, tolerance=20)
        # Either 95 or 105 is valid (both same distance)
        assert result in [95, 105]


class TestChunkText:
    """Tests for text chunking."""

    def test_small_text_single_chunk(self):
        """Text smaller than chunk size should be single chunk."""
        text = "Small text content."
        chunks = chunk_text(text, "file.txt", "project")
        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_chunk_metadata(self):
        """Chunks should have correct metadata."""
        text = "Test content for chunking."
        chunks = chunk_text(text, "file.py", "myproject")
        assert len(chunks) == 1

        meta = chunks[0].metadata
        assert meta.chunk_index == 0
        assert meta.start_offset == 0
        assert meta.end_offset == len(text)
        assert meta.source_path == "file.py"
        assert meta.project_name == "myproject"
        assert meta.char_count == len(text)

    def test_chunking_determinism(self):
        """Same input should produce same chunks."""
        text = "A" * 3000  # Large enough to chunk
        chunks1 = chunk_text(text, "file.txt", "project")
        chunks2 = chunk_text(text, "file.txt", "project")

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.metadata.chunk_id == c2.metadata.chunk_id
            assert c1.content == c2.content

    def test_empty_text(self):
        """Empty text should return no chunks."""
        chunks = chunk_text("", "file.txt", "project")
        assert chunks == []

    def test_overlap_applied(self):
        """Chunks should overlap correctly."""
        # Create text that will produce multiple chunks
        text = "A" * 1000 + "\n\n" + "B" * 1000 + "\n\n" + "C" * 1000
        config = ChunkingConfig(chunk_size=800, overlap=100)
        chunks = chunk_text(text, "file.txt", "project", config=config)

        assert len(chunks) > 1
        # Verify chunks cover full content
        # (overlap means chunks may share content)
        all_starts = [c.metadata.start_offset for c in chunks]
        all_ends = [c.metadata.end_offset for c in chunks]
        assert min(all_starts) == 0
        assert max(all_ends) == len(text)


class TestRechunkIfChanged:
    """Tests for change detection in chunking."""

    def test_chunks_when_no_previous_hash(self):
        """Should chunk when no previous hash provided."""
        text = "New content"
        chunks, changed = rechunk_if_changed(text, "file.txt", "project")
        assert changed is True
        assert len(chunks) > 0

    def test_skips_when_unchanged(self):
        """Should skip chunking when content unchanged."""
        text = "Same content"
        content_hash = compute_content_hash(text)
        chunks, changed = rechunk_if_changed(
            text, "file.txt", "project", previous_hash=content_hash
        )
        assert changed is False
        assert chunks == []

    def test_chunks_when_changed(self):
        """Should chunk when content changed."""
        text = "New content"
        chunks, changed = rechunk_if_changed(
            text, "file.txt", "project", previous_hash="old_hash"
        )
        assert changed is True
        assert len(chunks) > 0


class TestChunkFileContent:
    """Tests for file content chunking."""

    def test_successful_chunking(self):
        """Should return result with chunks."""
        content = "Python code here"
        result = chunk_file_content(content, "file.py", "project", ".py")

        assert result.source_path == "file.py"
        assert result.chunk_count >= 1
        assert result.total_chars == len(content)
        assert result.error is None

    def test_result_to_dict(self):
        """Result should convert to dictionary."""
        content = "Test content"
        result = chunk_file_content(content, "file.txt", "project", ".txt")
        d = result.to_dict()

        assert "source_path" in d
        assert "content_hash" in d
        assert "chunk_count" in d


class TestConfigForExtension:
    """Tests for extension-based configuration."""

    def test_python_config(self):
        """Python files should use code config."""
        config = get_config_for_extension(".py")
        assert config.chunk_size == 1000
        assert config.split_strategy == SplitStrategy.LINE

    def test_markdown_config(self):
        """Markdown files should use doc config."""
        config = get_config_for_extension(".md")
        assert config.chunk_size == 1500
        assert config.split_strategy == SplitStrategy.PARAGRAPH

    def test_json_config(self):
        """JSON files should use smaller config."""
        config = get_config_for_extension(".json")
        assert config.chunk_size == 800

    def test_unknown_extension_uses_default(self):
        """Unknown extensions should use default config."""
        config = get_config_for_extension(".xyz")
        default = DEFAULT_CONFIGS["_default"]
        assert config.chunk_size == default.chunk_size


class TestChunkMetadata:
    """Tests for ChunkMetadata dataclass."""

    def test_to_dict(self):
        """Metadata should convert to dictionary."""
        meta = ChunkMetadata(
            chunk_id="abc123",
            chunk_index=0,
            start_offset=0,
            end_offset=100,
            content_hash="hash",
            char_count=100,
            line_count=5,
            source_path="file.py",
            project_name="project",
        )
        d = meta.to_dict()

        assert d["chunk_id"] == "abc123"
        assert d["chunk_index"] == 0
        assert d["source_path"] == "file.py"


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_to_dict(self):
        """Chunk should convert to dictionary."""
        meta = ChunkMetadata(
            chunk_id="abc123",
            chunk_index=0,
            start_offset=0,
            end_offset=10,
            content_hash="hash",
            char_count=10,
            line_count=1,
            source_path="file.py",
            project_name="project",
        )
        chunk = Chunk(content="Test", metadata=meta)
        d = chunk.to_dict()

        assert d["content"] == "Test"
        assert "metadata" in d
        assert d["metadata"]["chunk_id"] == "abc123"


class TestSplitStrategies:
    """Tests for different split strategies producing consistent results."""

    def test_paragraph_strategy(self):
        """Paragraph strategy should split on double newlines."""
        text = "Para 1\n\nPara 2\n\nPara 3"
        config = ChunkingConfig(
            chunk_size=10,
            overlap=0,
            min_chunk_size=1,
            split_strategy=SplitStrategy.PARAGRAPH
        )
        chunks = chunk_text(text, "file.txt", "project", config=config)
        # Should create chunks at paragraph boundaries
        assert len(chunks) >= 2

    def test_line_strategy(self):
        """Line strategy should split on newlines."""
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        config = ChunkingConfig(
            chunk_size=15,
            overlap=0,
            min_chunk_size=1,
            split_strategy=SplitStrategy.LINE
        )
        chunks = chunk_text(text, "file.txt", "project", config=config)
        assert len(chunks) >= 2
