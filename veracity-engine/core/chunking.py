"""
Deterministic Chunking Module for Veracity Engine (STORY-008).

Provides deterministic text chunking with stable IDs:
- Fixed-size chunking with overlap
- Stable chunk ID generation using content hashes
- Metadata for each chunk (offset, size, hash)
- Configurable splitting strategy per file type

Reruns produce identical chunks when inputs are unchanged.
"""
import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SplitStrategy(Enum):
    """Strategies for splitting text into chunks."""
    PARAGRAPH = "paragraph"  # Split on \n\n
    LINE = "line"  # Split on \n
    SENTENCE = "sentence"  # Split on sentence boundaries
    FIXED = "fixed"  # Fixed character split (no delimiter awareness)


@dataclass
class ChunkMetadata:
    """Metadata for a single chunk."""
    chunk_id: str  # Deterministic ID based on content
    chunk_index: int  # 0-based index within source
    start_offset: int  # Character offset in source
    end_offset: int  # End character offset
    content_hash: str  # SHA256 of chunk content
    char_count: int
    line_count: int
    source_path: str  # Path of source file
    project_name: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "content_hash": self.content_hash,
            "char_count": self.char_count,
            "line_count": self.line_count,
            "source_path": self.source_path,
            "project_name": self.project_name,
        }


@dataclass
class Chunk:
    """A text chunk with content and metadata."""
    content: str
    metadata: ChunkMetadata

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class ChunkingConfig:
    """Configuration for chunking behavior."""
    chunk_size: int = 1200  # Target chunk size in characters
    overlap: int = 200  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum chunk size (avoid tiny chunks)
    max_chunk_size: int = 2000  # Maximum chunk size (hard limit)
    split_strategy: SplitStrategy = SplitStrategy.PARAGRAPH

    def validate(self) -> None:
        """Validate configuration values."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.overlap < 0:
            raise ValueError("overlap cannot be negative")
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        if self.min_chunk_size < 0:
            raise ValueError("min_chunk_size cannot be negative")
        if self.max_chunk_size < self.chunk_size:
            raise ValueError("max_chunk_size must be >= chunk_size")


# Default configurations per file type
DEFAULT_CONFIGS = {
    # Code files: smaller chunks, paragraph splitting
    ".py": ChunkingConfig(chunk_size=1000, overlap=150, split_strategy=SplitStrategy.LINE),
    ".js": ChunkingConfig(chunk_size=1000, overlap=150, split_strategy=SplitStrategy.LINE),
    ".ts": ChunkingConfig(chunk_size=1000, overlap=150, split_strategy=SplitStrategy.LINE),
    ".go": ChunkingConfig(chunk_size=1000, overlap=150, split_strategy=SplitStrategy.LINE),
    ".java": ChunkingConfig(chunk_size=1000, overlap=150, split_strategy=SplitStrategy.LINE),
    ".rs": ChunkingConfig(chunk_size=1000, overlap=150, split_strategy=SplitStrategy.LINE),
    # Documentation: larger chunks, paragraph splitting
    ".md": ChunkingConfig(chunk_size=1500, overlap=200, split_strategy=SplitStrategy.PARAGRAPH),
    ".txt": ChunkingConfig(chunk_size=1500, overlap=200, split_strategy=SplitStrategy.PARAGRAPH),
    ".rst": ChunkingConfig(chunk_size=1500, overlap=200, split_strategy=SplitStrategy.PARAGRAPH),
    # Config files: smaller chunks, line splitting
    ".json": ChunkingConfig(chunk_size=800, overlap=100, split_strategy=SplitStrategy.LINE),
    ".yaml": ChunkingConfig(chunk_size=800, overlap=100, split_strategy=SplitStrategy.LINE),
    ".yml": ChunkingConfig(chunk_size=800, overlap=100, split_strategy=SplitStrategy.LINE),
    ".toml": ChunkingConfig(chunk_size=800, overlap=100, split_strategy=SplitStrategy.LINE),
    # Default for unknown types
    "_default": ChunkingConfig(chunk_size=1200, overlap=200, split_strategy=SplitStrategy.PARAGRAPH),
}


def get_config_for_extension(extension: str) -> ChunkingConfig:
    """Get chunking configuration for a file extension."""
    ext_lower = extension.lower()
    return DEFAULT_CONFIGS.get(ext_lower, DEFAULT_CONFIGS["_default"])


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_chunk_id(source_path: str, chunk_index: int, content_hash: str) -> str:
    """
    Generate a deterministic chunk ID.

    Format: SHA256(source_path + ":" + chunk_index + ":" + content_hash)

    This ensures:
    1. Same content at same position = same ID
    2. Different positions = different IDs
    3. Different content = different IDs
    """
    composite = f"{source_path}:{chunk_index}:{content_hash}"
    return hashlib.sha256(composite.encode('utf-8')).hexdigest()[:16]  # Use first 16 chars


def find_split_points(text: str, strategy: SplitStrategy) -> List[int]:
    """
    Find natural split points in text based on strategy.

    Returns list of character offsets where splits can occur.
    """
    if strategy == SplitStrategy.PARAGRAPH:
        # Split on double newlines
        pattern = r'\n\n+'
        matches = list(re.finditer(pattern, text))
        return [m.end() for m in matches]

    elif strategy == SplitStrategy.LINE:
        # Split on single newlines
        pattern = r'\n'
        matches = list(re.finditer(pattern, text))
        return [m.end() for m in matches]

    elif strategy == SplitStrategy.SENTENCE:
        # Split on sentence boundaries (., !, ?) followed by space/newline
        pattern = r'[.!?]\s+'
        matches = list(re.finditer(pattern, text))
        return [m.end() for m in matches]

    else:  # FIXED
        return []


def find_best_split_point(
    text: str,
    target_offset: int,
    split_points: List[int],
    tolerance: int = 100
) -> int:
    """
    Find the best split point near the target offset.

    Prefers natural break points within tolerance, falls back to hard split.
    """
    # Find split points within tolerance of target
    candidates = [
        sp for sp in split_points
        if abs(sp - target_offset) <= tolerance
    ]

    if candidates:
        # Return the one closest to target
        return min(candidates, key=lambda x: abs(x - target_offset))

    # No natural break point, use hard split
    return target_offset


def chunk_text(
    text: str,
    source_path: str,
    project_name: str,
    config: Optional[ChunkingConfig] = None,
    extension: Optional[str] = None,
) -> List[Chunk]:
    """
    Split text into deterministic chunks.

    Args:
        text: Text content to chunk
        source_path: Path of source file (for ID generation)
        project_name: Project name (for ID generation)
        config: Optional chunking configuration
        extension: File extension (used if config not provided)

    Returns:
        List of Chunk objects with deterministic IDs and metadata
    """
    if not text:
        return []

    # Get configuration
    if config is None:
        ext = extension or ""
        config = get_config_for_extension(ext)

    config.validate()

    chunks = []
    text_length = len(text)

    # If text is smaller than chunk size, return single chunk
    if text_length <= config.chunk_size:
        content_hash = compute_content_hash(text)
        chunk_id = generate_chunk_id(source_path, 0, content_hash)
        line_count = text.count('\n') + 1

        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            chunk_index=0,
            start_offset=0,
            end_offset=text_length,
            content_hash=content_hash,
            char_count=text_length,
            line_count=line_count,
            source_path=source_path,
            project_name=project_name,
        )
        return [Chunk(content=text, metadata=metadata)]

    # Find all natural split points
    split_points = find_split_points(text, config.split_strategy)

    # Add fallback split points (line breaks) if using paragraph strategy
    if config.split_strategy == SplitStrategy.PARAGRAPH:
        line_splits = find_split_points(text, SplitStrategy.LINE)
        split_points = sorted(set(split_points + line_splits))

    # Create chunks
    current_offset = 0
    chunk_index = 0

    while current_offset < text_length:
        # Calculate target end offset
        target_end = min(current_offset + config.chunk_size, text_length)

        # Find best split point
        if target_end < text_length:
            end_offset = find_best_split_point(
                text, target_end, split_points, tolerance=100
            )
            # Ensure we don't exceed max chunk size
            if end_offset - current_offset > config.max_chunk_size:
                end_offset = current_offset + config.max_chunk_size
            # Ensure we make progress
            if end_offset <= current_offset:
                end_offset = min(current_offset + config.chunk_size, text_length)
        else:
            end_offset = text_length

        # Extract chunk content
        chunk_content = text[current_offset:end_offset]

        # Skip if chunk is too small (unless it's the last chunk)
        if len(chunk_content) < config.min_chunk_size and end_offset < text_length:
            # Merge with next chunk by not advancing
            pass
        else:
            # Create chunk
            content_hash = compute_content_hash(chunk_content)
            chunk_id = generate_chunk_id(source_path, chunk_index, content_hash)
            line_count = chunk_content.count('\n') + 1

            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                start_offset=current_offset,
                end_offset=end_offset,
                content_hash=content_hash,
                char_count=len(chunk_content),
                line_count=line_count,
                source_path=source_path,
                project_name=project_name,
            )
            chunks.append(Chunk(content=chunk_content, metadata=metadata))
            chunk_index += 1

        # Move to next position (with overlap)
        if end_offset >= text_length:
            break

        # Calculate next start position (with overlap)
        next_start = end_offset - config.overlap
        if next_start <= current_offset:
            # Ensure we make progress
            next_start = end_offset

        current_offset = next_start

    logger.debug(f"Created {len(chunks)} chunks from {source_path}")
    return chunks


def rechunk_if_changed(
    text: str,
    source_path: str,
    project_name: str,
    previous_hash: Optional[str] = None,
    **kwargs
) -> Tuple[List[Chunk], bool]:
    """
    Chunk text only if content has changed.

    Args:
        text: Text content to chunk
        source_path: Path of source file
        project_name: Project name
        previous_hash: Hash of previous content (for change detection)
        **kwargs: Additional arguments passed to chunk_text

    Returns:
        Tuple of (chunks, changed) where changed indicates if rechunking occurred
    """
    current_hash = compute_content_hash(text)

    if previous_hash is not None and current_hash == previous_hash:
        logger.debug(f"Content unchanged for {source_path}, skipping rechunk")
        return [], False

    chunks = chunk_text(text, source_path, project_name, **kwargs)
    return chunks, True


@dataclass
class ChunkingResult:
    """Result of chunking operation for a file."""
    source_path: str
    content_hash: str
    chunk_count: int
    total_chars: int
    chunks: List[Chunk] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "chunk_count": self.chunk_count,
            "total_chars": self.total_chars,
            "error": self.error,
        }


def chunk_file_content(
    content: str,
    file_path: str,
    project_name: str,
    extension: str,
) -> ChunkingResult:
    """
    Chunk file content and return result.

    Args:
        content: File content
        file_path: Path to file
        project_name: Project name
        extension: File extension

    Returns:
        ChunkingResult with chunks and metadata
    """
    try:
        content_hash = compute_content_hash(content)
        chunks = chunk_text(
            text=content,
            source_path=file_path,
            project_name=project_name,
            extension=extension,
        )

        return ChunkingResult(
            source_path=file_path,
            content_hash=content_hash,
            chunk_count=len(chunks),
            total_chars=len(content),
            chunks=chunks,
        )

    except Exception as e:
        logger.error(f"Failed to chunk {file_path}: {e}")
        return ChunkingResult(
            source_path=file_path,
            content_hash="",
            chunk_count=0,
            total_chars=len(content),
            error=str(e),
        )
