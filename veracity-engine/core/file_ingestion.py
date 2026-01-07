"""
File Ingestion Module for Veracity Engine (STORY-007).

Provides evidence-first file indexing capabilities:
- File discovery with ignore rules (.gitignore + secrets)
- Deterministic file classification (text vs binary)
- Text extraction adapters for supported formats
- Metadata extraction for binary files

Every file becomes a KG node with stable, deterministic metadata.
"""
import os
import hashlib
import mimetypes
import logging
import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class FileCategory(Enum):
    """File classification categories."""
    CODE = "Code"
    DOCUMENTATION = "Documentation"
    CONFIG = "Config"
    DATA = "Data"
    INFRASTRUCTURE = "Infrastructure"
    BINARY = "Binary"
    UNKNOWN = "Unknown"


@dataclass
class FileMetadata:
    """Deterministic metadata for a file."""
    path: str  # Relative path from root
    absolute_path: str
    name: str
    extension: str
    size_bytes: int
    content_hash: str  # SHA1 of raw bytes
    mime_type: str
    category: FileCategory
    is_binary: bool
    last_modified: datetime
    encoding: Optional[str] = None
    line_count: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "mime_type": self.mime_type,
            "category": self.category.value,
            "is_binary": self.is_binary,
            "last_modified": self.last_modified.isoformat(),
            "encoding": self.encoding,
            "line_count": self.line_count,
        }


# Text file extensions that should be parsed for content
TEXT_EXTENSIONS = {
    # Code
    ".py", ".pyw", ".pyi",  # Python
    ".js", ".jsx", ".mjs", ".cjs",  # JavaScript
    ".ts", ".tsx", ".mts", ".cts",  # TypeScript
    ".go",  # Go
    ".rs",  # Rust
    ".java", ".kt", ".kts",  # Java/Kotlin
    ".c", ".h", ".cpp", ".hpp", ".cc", ".hh",  # C/C++
    ".cs",  # C#
    ".rb",  # Ruby
    ".php",  # PHP
    ".swift",  # Swift
    ".scala",  # Scala
    ".r", ".R",  # R
    ".lua",  # Lua
    ".pl", ".pm",  # Perl
    ".sh", ".bash", ".zsh", ".fish",  # Shell
    ".ps1", ".psm1",  # PowerShell
    ".sql",  # SQL
    ".graphql", ".gql",  # GraphQL
    # Markup/Documentation
    ".md", ".markdown",  # Markdown
    ".rst",  # reStructuredText
    ".txt",  # Plain text
    ".adoc", ".asciidoc",  # AsciiDoc
    ".tex", ".latex",  # LaTeX
    ".html", ".htm",  # HTML
    ".xml", ".xsl", ".xslt",  # XML
    ".svg",  # SVG
    # Data/Config
    ".json",  # JSON
    ".yaml", ".yml",  # YAML
    ".toml",  # TOML
    ".ini", ".cfg",  # INI/Config
    ".env", ".env.example",  # Environment (but .env itself excluded)
    ".properties",  # Java properties
    ".csv", ".tsv",  # Delimited data
    # Styles
    ".css", ".scss", ".sass", ".less",  # CSS
    # Build/Config
    ".dockerfile", ".containerfile",  # Container
    ".makefile",  # Make
    ".cmake",  # CMake
    ".gradle", ".gradle.kts",  # Gradle
}

# Files without extensions that are text
TEXT_FILENAMES = {
    "Dockerfile",
    "Containerfile",
    "Makefile",
    "Rakefile",
    "Gemfile",
    "Procfile",
    "Vagrantfile",
    "Brewfile",
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    ".editorconfig",
    ".prettierrc",
    ".eslintrc",
    ".babelrc",
    "LICENSE",
    "README",
    "CHANGELOG",
    "CONTRIBUTING",
    "AUTHORS",
    "CODEOWNERS",
    "requirements.txt",
    "setup.py",
    "pyproject.toml",
    "package.json",
    "tsconfig.json",
    "docker-compose.yml",
    "docker-compose.yaml",
}

# Known binary extensions (not exhaustive, but common)
BINARY_EXTENSIONS = {
    # Images (note: .svg is text-based XML, not binary)
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    # Executables
    ".exe", ".dll", ".so", ".dylib", ".bin",
    # Compiled
    ".pyc", ".pyo", ".class", ".o", ".obj", ".a",
    # Media
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Other
    ".db", ".sqlite", ".sqlite3",
    ".jar", ".war", ".ear",
    ".whl", ".egg",
}

# Files/patterns to always exclude (security)
ALWAYS_EXCLUDE_PATTERNS = [
    ".git",
    ".git/*",
    ".git/**",
    "*.pyc",
    "__pycache__",
    "__pycache__/*",
    "*.pyo",
    ".env",
    ".env.*",
    ".env.local",
    ".env.*.local",
    "*.pem",
    "*.key",
    "*.p12",
    "*.keystore",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    ".graph_hashes_*.json",
    "node_modules",
    "node_modules/*",
    "node_modules/**",
    "venv",
    "venv/*",
    ".venv",
    ".venv/*",
    "*.egg-info",
    "*.egg-info/*",
    "dist",
    "dist/*",
    "build",
    "build/*",
    ".pytest_cache",
    ".pytest_cache/*",
    ".mypy_cache",
    ".mypy_cache/*",
    ".tox",
    ".tox/*",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
]

# Extension to category mapping
EXTENSION_CATEGORIES = {
    # Code
    ".py": FileCategory.CODE,
    ".pyw": FileCategory.CODE,
    ".pyi": FileCategory.CODE,
    ".js": FileCategory.CODE,
    ".jsx": FileCategory.CODE,
    ".ts": FileCategory.CODE,
    ".tsx": FileCategory.CODE,
    ".go": FileCategory.CODE,
    ".rs": FileCategory.CODE,
    ".java": FileCategory.CODE,
    ".kt": FileCategory.CODE,
    ".c": FileCategory.CODE,
    ".cpp": FileCategory.CODE,
    ".h": FileCategory.CODE,
    ".hpp": FileCategory.CODE,
    ".cs": FileCategory.CODE,
    ".rb": FileCategory.CODE,
    ".php": FileCategory.CODE,
    ".swift": FileCategory.CODE,
    ".scala": FileCategory.CODE,
    ".lua": FileCategory.CODE,
    ".pl": FileCategory.CODE,
    ".sh": FileCategory.CODE,
    ".bash": FileCategory.CODE,
    ".ps1": FileCategory.CODE,
    ".sql": FileCategory.CODE,
    ".graphql": FileCategory.CODE,
    ".r": FileCategory.CODE,
    ".R": FileCategory.CODE,
    # Documentation
    ".md": FileCategory.DOCUMENTATION,
    ".markdown": FileCategory.DOCUMENTATION,
    ".rst": FileCategory.DOCUMENTATION,
    ".txt": FileCategory.DOCUMENTATION,
    ".adoc": FileCategory.DOCUMENTATION,
    ".tex": FileCategory.DOCUMENTATION,
    ".html": FileCategory.DOCUMENTATION,
    ".htm": FileCategory.DOCUMENTATION,
    # Config
    ".json": FileCategory.CONFIG,
    ".yaml": FileCategory.CONFIG,
    ".yml": FileCategory.CONFIG,
    ".toml": FileCategory.CONFIG,
    ".ini": FileCategory.CONFIG,
    ".cfg": FileCategory.CONFIG,
    ".properties": FileCategory.CONFIG,
    ".xml": FileCategory.CONFIG,
    ".env.example": FileCategory.CONFIG,
    # Data
    ".csv": FileCategory.DATA,
    ".tsv": FileCategory.DATA,
    ".db": FileCategory.DATA,
    ".sqlite": FileCategory.DATA,
    # Infrastructure
    ".dockerfile": FileCategory.INFRASTRUCTURE,
    ".tf": FileCategory.INFRASTRUCTURE,
    ".hcl": FileCategory.INFRASTRUCTURE,
    # Styles (treat as code)
    ".css": FileCategory.CODE,
    ".scss": FileCategory.CODE,
    ".sass": FileCategory.CODE,
    ".less": FileCategory.CODE,
}

# Filename to category mapping
FILENAME_CATEGORIES = {
    "Dockerfile": FileCategory.INFRASTRUCTURE,
    "docker-compose.yml": FileCategory.INFRASTRUCTURE,
    "docker-compose.yaml": FileCategory.INFRASTRUCTURE,
    "Makefile": FileCategory.INFRASTRUCTURE,
    ".gitignore": FileCategory.CONFIG,
    ".gitattributes": FileCategory.CONFIG,
    ".dockerignore": FileCategory.CONFIG,
    ".editorconfig": FileCategory.CONFIG,
    "requirements.txt": FileCategory.CONFIG,
    "pyproject.toml": FileCategory.CONFIG,
    "setup.py": FileCategory.CODE,
    "package.json": FileCategory.CONFIG,
    "tsconfig.json": FileCategory.CONFIG,
    "LICENSE": FileCategory.DOCUMENTATION,
    "README": FileCategory.DOCUMENTATION,
    "CHANGELOG": FileCategory.DOCUMENTATION,
    "CONTRIBUTING": FileCategory.DOCUMENTATION,
}


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA1 hash of file contents for change detection.

    This matches the existing hash function in build_graph.py for compatibility.
    """
    hasher = hashlib.sha1()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def is_binary_file(file_path: str, sample_size: int = 8192) -> bool:
    """
    Determine if a file is binary by checking for null bytes.

    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample

    Returns:
        True if file appears to be binary
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(sample_size)
            # Check for null bytes (common in binary files)
            if b'\x00' in chunk:
                return True
            # Try to decode as UTF-8
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
    except (IOError, OSError):
        return True


def classify_file(path: str, name: str, extension: str) -> Tuple[FileCategory, bool]:
    """
    Classify a file by category and determine if it's binary.

    Args:
        path: File path
        name: File name
        extension: File extension (lowercase with dot)

    Returns:
        Tuple of (category, is_binary)
    """
    # Check by filename first
    if name in FILENAME_CATEGORIES:
        return FILENAME_CATEGORIES[name], False

    # Check by extension
    ext_lower = extension.lower()

    # Known binary extensions
    if ext_lower in BINARY_EXTENSIONS:
        return FileCategory.BINARY, True

    # Known text extensions
    if ext_lower in EXTENSION_CATEGORIES:
        return EXTENSION_CATEGORIES[ext_lower], False

    # Known text files without extension
    if name in TEXT_FILENAMES:
        return FileCategory.DOCUMENTATION, False

    # Known text extensions not in category map
    if ext_lower in TEXT_EXTENSIONS:
        return FileCategory.CODE, False

    # Fallback: check file content
    if os.path.exists(path) and os.path.isfile(path):
        if is_binary_file(path):
            return FileCategory.BINARY, True
        else:
            return FileCategory.UNKNOWN, False

    return FileCategory.UNKNOWN, False


def get_mime_type(path: str, extension: str) -> str:
    """Get MIME type for a file."""
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        return mime_type
    # Fallback for unknown types
    if extension.lower() in TEXT_EXTENSIONS:
        return "text/plain"
    return "application/octet-stream"


def count_lines(path: str) -> Optional[int]:
    """Count lines in a text file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except (IOError, OSError):
        return None


def detect_encoding(path: str) -> str:
    """Detect file encoding (simple approach)."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'ascii']
    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, IOError):
            continue
    return 'binary'


def extract_file_metadata(root_dir: str, file_path: str) -> FileMetadata:
    """
    Extract deterministic metadata from a file.

    Args:
        root_dir: Project root directory
        file_path: Absolute path to the file

    Returns:
        FileMetadata object with all extracted information
    """
    rel_path = os.path.relpath(file_path, root_dir)
    name = os.path.basename(file_path)
    _, extension = os.path.splitext(name)

    stat = os.stat(file_path)
    size_bytes = stat.st_size
    last_modified = datetime.fromtimestamp(stat.st_mtime)

    # Classify file
    category, is_binary = classify_file(file_path, name, extension)

    # Compute content hash
    content_hash = compute_file_hash(file_path)

    # Get MIME type
    mime_type = get_mime_type(file_path, extension)

    # Extract text-specific metadata
    encoding = None
    line_count = None
    if not is_binary:
        encoding = detect_encoding(file_path)
        if encoding != 'binary':
            line_count = count_lines(file_path)

    return FileMetadata(
        path=rel_path,
        absolute_path=file_path,
        name=name,
        extension=extension,
        size_bytes=size_bytes,
        content_hash=content_hash,
        mime_type=mime_type,
        category=category,
        is_binary=is_binary,
        last_modified=last_modified,
        encoding=encoding,
        line_count=line_count,
    )


def parse_gitignore(gitignore_path: str) -> List[str]:
    """
    Parse .gitignore file and return list of patterns.

    Args:
        gitignore_path: Path to .gitignore file

    Returns:
        List of ignore patterns
    """
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns

    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    except (IOError, OSError) as e:
        logger.warning(f"Failed to read .gitignore: {e}")

    return patterns


def should_exclude(path: str, name: str, exclude_patterns: List[str]) -> bool:
    """
    Check if a file/directory should be excluded.

    Args:
        path: Relative path from root
        name: File/directory name
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if should be excluded
    """
    # Check against all patterns
    for pattern in exclude_patterns:
        # Check filename match
        if fnmatch.fnmatch(name, pattern):
            return True
        # Check path match
        if fnmatch.fnmatch(path, pattern):
            return True
        # Check with ** glob
        if '**' in pattern:
            # Convert ** pattern for fnmatch
            simple_pattern = pattern.replace('**/', '').replace('/**', '')
            if fnmatch.fnmatch(name, simple_pattern):
                return True

    return False


def discover_files(
    root_dir: str,
    use_gitignore: bool = True,
    additional_excludes: Optional[List[str]] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB default
) -> List[str]:
    """
    Discover all files under root directory.

    Args:
        root_dir: Root directory to scan
        use_gitignore: Whether to honor .gitignore patterns
        additional_excludes: Additional patterns to exclude
        max_file_size: Maximum file size to include (bytes)

    Returns:
        Sorted list of absolute file paths
    """
    root_dir = os.path.abspath(root_dir)
    files = []

    # Build exclude patterns
    exclude_patterns = list(ALWAYS_EXCLUDE_PATTERNS)
    if additional_excludes:
        exclude_patterns.extend(additional_excludes)

    # Parse .gitignore if requested
    if use_gitignore:
        gitignore_path = os.path.join(root_dir, '.gitignore')
        gitignore_patterns = parse_gitignore(gitignore_path)
        exclude_patterns.extend(gitignore_patterns)

    logger.debug(f"Exclude patterns: {exclude_patterns}")

    # Walk directory tree
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        # Get relative path
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == '.':
            rel_dir = ''

        # Filter directories in-place (prune excluded dirs)
        dirnames[:] = [
            d for d in dirnames
            if not should_exclude(os.path.join(rel_dir, d), d, exclude_patterns)
        ]

        # Sort directories for deterministic order
        dirnames.sort()

        # Process files
        for filename in sorted(filenames):  # Sort for deterministic order
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename

            # Check exclusion
            if should_exclude(rel_path, filename, exclude_patterns):
                logger.debug(f"Excluding: {rel_path}")
                continue

            abs_path = os.path.join(dirpath, filename)

            # Check file size
            try:
                size = os.path.getsize(abs_path)
                if size > max_file_size:
                    logger.warning(f"Skipping large file ({size} bytes): {rel_path}")
                    continue
            except OSError:
                continue

            files.append(abs_path)

    logger.info(f"Discovered {len(files)} files under {root_dir}")
    return files


def extract_text_content(file_path: str, max_size: int = 1024 * 1024) -> Optional[str]:
    """
    Extract text content from a file.

    Args:
        file_path: Path to the file
        max_size: Maximum content size to extract

    Returns:
        Text content or None if extraction fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_size)
            # Add truncation indicator if needed
            if len(content) == max_size:
                content += "\n... [TRUNCATED]"
            return content
    except (IOError, OSError) as e:
        logger.warning(f"Failed to extract text from {file_path}: {e}")
        return None


def generate_file_uid(project_name: str, rel_path: str) -> str:
    """
    Generate a deterministic UID for a file.

    Args:
        project_name: Project identifier
        rel_path: Relative path from project root

    Returns:
        Deterministic UID string
    """
    # Normalize path separators
    normalized_path = rel_path.replace('\\', '/')
    return f"{project_name}:{normalized_path}"


@dataclass
class IngestionResult:
    """Result of file ingestion operation."""
    files_discovered: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    text_files: int = 0
    binary_files: int = 0
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (path, error)

    def add_error(self, path: str, error: str) -> None:
        """Add an error record."""
        self.errors.append((path, error))
        self.files_skipped += 1

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "files_discovered": self.files_discovered,
            "files_processed": self.files_processed,
            "files_skipped": self.files_skipped,
            "text_files": self.text_files,
            "binary_files": self.binary_files,
            "error_count": len(self.errors),
            "errors": [{"path": p, "error": e} for p, e in self.errors[:10]],
        }
