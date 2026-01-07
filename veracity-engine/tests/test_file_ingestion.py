"""
Tests for File Ingestion Module (STORY-007).

Tests cover:
1. File classification (text vs binary, categories)
2. File discovery with ignore rules
3. Metadata extraction
4. UID generation
5. Content extraction
"""
import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from core.file_ingestion import (
    FileCategory,
    FileMetadata,
    IngestionResult,
    compute_file_hash,
    is_binary_file,
    classify_file,
    get_mime_type,
    count_lines,
    detect_encoding,
    extract_file_metadata,
    parse_gitignore,
    should_exclude,
    discover_files,
    extract_text_content,
    generate_file_uid,
    TEXT_EXTENSIONS,
    BINARY_EXTENSIONS,
    ALWAYS_EXCLUDE_PATTERNS,
)


class TestFileClassification:
    """Tests for file classification functions."""

    def test_python_file_is_code(self):
        """Python files should be classified as Code."""
        category, is_binary = classify_file("test.py", "test.py", ".py")
        assert category == FileCategory.CODE
        assert is_binary is False

    def test_markdown_is_documentation(self):
        """Markdown files should be classified as Documentation."""
        category, is_binary = classify_file("README.md", "README.md", ".md")
        assert category == FileCategory.DOCUMENTATION
        assert is_binary is False

    def test_json_is_config(self):
        """JSON files should be classified as Config."""
        category, is_binary = classify_file("config.json", "config.json", ".json")
        assert category == FileCategory.CONFIG
        assert is_binary is False

    def test_png_is_binary(self):
        """PNG files should be classified as Binary."""
        category, is_binary = classify_file("image.png", "image.png", ".png")
        assert category == FileCategory.BINARY
        assert is_binary is True

    def test_dockerfile_is_infrastructure(self):
        """Dockerfile should be classified as Infrastructure."""
        category, is_binary = classify_file("Dockerfile", "Dockerfile", "")
        assert category == FileCategory.INFRASTRUCTURE
        assert is_binary is False

    def test_makefile_is_infrastructure(self):
        """Makefile should be classified as Infrastructure."""
        category, is_binary = classify_file("Makefile", "Makefile", "")
        assert category == FileCategory.INFRASTRUCTURE
        assert is_binary is False

    def test_csv_is_data(self):
        """CSV files should be classified as Data."""
        category, is_binary = classify_file("data.csv", "data.csv", ".csv")
        assert category == FileCategory.DATA
        assert is_binary is False

    def test_typescript_is_code(self):
        """TypeScript files should be classified as Code."""
        category, is_binary = classify_file("app.tsx", "app.tsx", ".tsx")
        assert category == FileCategory.CODE
        assert is_binary is False


class TestBinaryDetection:
    """Tests for binary file detection."""

    def test_text_file_not_binary(self):
        """Text files should not be detected as binary."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World!\nThis is a test file.\n")
            temp_path = f.name

        try:
            assert is_binary_file(temp_path) is False
        finally:
            os.unlink(temp_path)

    def test_binary_file_detected(self):
        """Binary files with null bytes should be detected."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')
            temp_path = f.name

        try:
            assert is_binary_file(temp_path) is True
        finally:
            os.unlink(temp_path)


class TestFileHash:
    """Tests for file hashing."""

    def test_hash_is_sha1(self):
        """Hash should be a valid SHA1 hex string."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            hash_val = compute_file_hash(temp_path)
            assert len(hash_val) == 40  # SHA1 hex length
            assert all(c in '0123456789abcdef' for c in hash_val)
        finally:
            os.unlink(temp_path)

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        content = "Deterministic test content"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f1:
            f1.write(content)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f2:
            f2.write(content)
            path2 = f2.name

        try:
            assert compute_file_hash(path1) == compute_file_hash(path2)
        finally:
            os.unlink(path1)
            os.unlink(path2)


class TestMetadataExtraction:
    """Tests for metadata extraction."""

    def test_extract_text_file_metadata(self):
        """Should extract metadata from text files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, 'w') as f:
                f.write("print('hello')\nprint('world')\n")

            metadata = extract_file_metadata(tmpdir, file_path)

            assert metadata.name == "test.py"
            assert metadata.extension == ".py"
            assert metadata.category == FileCategory.CODE
            assert metadata.is_binary is False
            assert metadata.line_count == 2
            assert metadata.encoding == "utf-8"
            assert len(metadata.content_hash) == 40

    def test_metadata_to_dict(self):
        """Metadata should convert to dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            with open(file_path, 'w') as f:
                f.write("Test content")

            metadata = extract_file_metadata(tmpdir, file_path)
            d = metadata.to_dict()

            assert "path" in d
            assert "name" in d
            assert "content_hash" in d
            assert "category" in d
            assert d["category"] == "Documentation"


class TestGitignoreParsing:
    """Tests for .gitignore parsing."""

    def test_parse_gitignore(self):
        """Should parse .gitignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore_path = os.path.join(tmpdir, ".gitignore")
            with open(gitignore_path, 'w') as f:
                f.write("# Comment\n")
                f.write("*.pyc\n")
                f.write("__pycache__\n")
                f.write("\n")  # Empty line
                f.write("node_modules/\n")

            patterns = parse_gitignore(gitignore_path)

            assert "*.pyc" in patterns
            assert "__pycache__" in patterns
            assert "node_modules/" in patterns
            assert "# Comment" not in patterns
            assert "" not in patterns

    def test_nonexistent_gitignore(self):
        """Should return empty list for nonexistent file."""
        patterns = parse_gitignore("/nonexistent/.gitignore")
        assert patterns == []


class TestExclusionPatterns:
    """Tests for file exclusion."""

    def test_exclude_pyc(self):
        """Should exclude .pyc files."""
        assert should_exclude("cache/test.pyc", "test.pyc", ALWAYS_EXCLUDE_PATTERNS)

    def test_exclude_git_dir(self):
        """Should exclude .git directory."""
        assert should_exclude(".git", ".git", ALWAYS_EXCLUDE_PATTERNS)

    def test_exclude_env_file(self):
        """Should exclude .env files."""
        assert should_exclude(".env", ".env", ALWAYS_EXCLUDE_PATTERNS)
        assert should_exclude(".env.local", ".env.local", ALWAYS_EXCLUDE_PATTERNS)

    def test_exclude_pem_files(self):
        """Should exclude .pem files (secrets)."""
        assert should_exclude("certs/server.pem", "server.pem", ALWAYS_EXCLUDE_PATTERNS)

    def test_exclude_node_modules(self):
        """Should exclude node_modules."""
        assert should_exclude("node_modules", "node_modules", ALWAYS_EXCLUDE_PATTERNS)

    def test_include_normal_files(self):
        """Should include normal source files."""
        assert should_exclude("src/main.py", "main.py", ALWAYS_EXCLUDE_PATTERNS) is False
        assert should_exclude("README.md", "README.md", ALWAYS_EXCLUDE_PATTERNS) is False


class TestFileDiscovery:
    """Tests for file discovery."""

    def test_discover_files_in_directory(self):
        """Should discover all files respecting ignore rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "main.py").write_text("print('hello')")
            Path(tmpdir, "README.md").write_text("# Readme")
            Path(tmpdir, "test.pyc").write_bytes(b'\x00\x01\x02')  # Should be excluded

            # Create subdirectory
            subdir = Path(tmpdir, "src")
            subdir.mkdir()
            Path(subdir, "app.py").write_text("app = 'test'")

            files = discover_files(tmpdir, use_gitignore=False)

            # Check results
            file_names = [os.path.basename(f) for f in files]
            assert "main.py" in file_names
            assert "README.md" in file_names
            assert "app.py" in file_names
            assert "test.pyc" not in file_names  # Excluded by default

    def test_discover_respects_gitignore(self):
        """Should respect .gitignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .gitignore
            Path(tmpdir, ".gitignore").write_text("ignored.txt\n")

            # Create files
            Path(tmpdir, "kept.txt").write_text("keep")
            Path(tmpdir, "ignored.txt").write_text("ignore")

            files = discover_files(tmpdir, use_gitignore=True)

            file_names = [os.path.basename(f) for f in files]
            assert "kept.txt" in file_names
            assert "ignored.txt" not in file_names

    def test_discover_files_sorted(self):
        """Discovered files should be in deterministic order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in random order
            Path(tmpdir, "z.txt").write_text("z")
            Path(tmpdir, "a.txt").write_text("a")
            Path(tmpdir, "m.txt").write_text("m")

            files = discover_files(tmpdir, use_gitignore=False)

            # Files should be sorted
            file_names = [os.path.basename(f) for f in files]
            assert file_names == sorted(file_names)


class TestContentExtraction:
    """Tests for content extraction."""

    def test_extract_text_content(self):
        """Should extract text content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = f.name

        try:
            content = extract_text_content(temp_path)
            assert "Line 1" in content
            assert "Line 2" in content
            assert "Line 3" in content
        finally:
            os.unlink(temp_path)

    def test_content_truncation(self):
        """Should truncate large content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            content = extract_text_content(temp_path, max_size=100)
            assert len(content) > 100  # Includes truncation indicator
            assert "[TRUNCATED]" in content
        finally:
            os.unlink(temp_path)


class TestUIDGeneration:
    """Tests for UID generation."""

    def test_uid_format(self):
        """UID should have correct format."""
        uid = generate_file_uid("myproject", "src/main.py")
        assert uid == "myproject:src/main.py"

    def test_uid_normalizes_path(self):
        """UID should normalize path separators."""
        uid = generate_file_uid("myproject", "src\\main.py")
        assert uid == "myproject:src/main.py"

    def test_uid_deterministic(self):
        """Same inputs should produce same UID."""
        uid1 = generate_file_uid("project", "file.py")
        uid2 = generate_file_uid("project", "file.py")
        assert uid1 == uid2


class TestMimeType:
    """Tests for MIME type detection."""

    def test_python_mime_type(self):
        """Python files should have correct MIME type."""
        mime = get_mime_type("test.py", ".py")
        assert "python" in mime.lower() or mime == "text/x-python"

    def test_json_mime_type(self):
        """JSON files should have correct MIME type."""
        mime = get_mime_type("data.json", ".json")
        assert "json" in mime.lower()

    def test_unknown_extension_fallback(self):
        """Unknown extensions should return something (mimetypes may know it)."""
        mime = get_mime_type("file.zzz123", ".zzz123")
        # Should return some valid MIME type string
        assert isinstance(mime, str)
        assert "/" in mime  # Valid MIME format


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_initial_state(self):
        """Result should start with zero counts."""
        result = IngestionResult()
        assert result.files_discovered == 0
        assert result.files_processed == 0
        assert result.errors == []

    def test_add_error(self):
        """Adding error should increment skipped count."""
        result = IngestionResult()
        result.add_error("/path/to/file", "Error message")
        assert result.files_skipped == 1
        assert len(result.errors) == 1

    def test_to_dict(self):
        """Should convert to dictionary."""
        result = IngestionResult(files_discovered=10, files_processed=8)
        result.add_error("/test", "Error")
        d = result.to_dict()

        assert d["files_discovered"] == 10
        assert d["files_processed"] == 8
        assert d["error_count"] == 1


class TestExtensionSets:
    """Tests for extension configuration."""

    def test_text_extensions_include_common(self):
        """Text extensions should include common types."""
        assert ".py" in TEXT_EXTENSIONS
        assert ".js" in TEXT_EXTENSIONS
        assert ".md" in TEXT_EXTENSIONS
        assert ".json" in TEXT_EXTENSIONS
        assert ".yaml" in TEXT_EXTENSIONS

    def test_binary_extensions_include_common(self):
        """Binary extensions should include common types."""
        assert ".png" in BINARY_EXTENSIONS
        assert ".jpg" in BINARY_EXTENSIONS
        assert ".pdf" in BINARY_EXTENSIONS
        assert ".zip" in BINARY_EXTENSIONS
        assert ".exe" in BINARY_EXTENSIONS

    def test_no_overlap(self):
        """Text and binary extensions should not overlap."""
        overlap = TEXT_EXTENSIONS & BINARY_EXTENSIONS
        assert len(overlap) == 0, f"Overlapping extensions: {overlap}"


class TestLineCount:
    """Tests for line counting."""

    def test_count_lines(self):
        """Should count lines correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = f.name

        try:
            count = count_lines(temp_path)
            assert count == 3
        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        """Empty file should have zero lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name

        try:
            count = count_lines(temp_path)
            assert count == 0
        finally:
            os.unlink(temp_path)
