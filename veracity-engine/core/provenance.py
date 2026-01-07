"""
Provenance Module for Veracity Engine (STORY-009).

Provides explicit provenance tracking for all KG nodes and evidence:
- Source path tracking
- File hash (SHA1 of raw bytes)
- Text hash (SHA256 of normalized content)
- Extraction method and version
- Timestamps for auditing

Enables deterministic replay and auditable retrieval.
"""
import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Default extractor identification
DEFAULT_EXTRACTOR_NAME = "veracity-engine"
DEFAULT_EXTRACTOR_VERSION = "0.1.0-dev"


@dataclass
class ProvenanceConfig:
    """Configuration for provenance generation."""
    extractor_name: str = DEFAULT_EXTRACTOR_NAME
    normalize_line_endings: bool = True
    include_text_hash: bool = True


@dataclass
class ProvenanceRecord:
    """
    Provenance information for a source file or content.

    Attributes:
        path: Relative or absolute path to the source file
        file_hash: SHA1 hash of raw file bytes
        text_hash: SHA256 hash of normalized text content (empty for binary)
        last_modified: Unix timestamp of last modification
        extractor: Name of the extraction tool/system
        extractor_version: Version of the extraction tool
    """
    path: str
    file_hash: str
    text_hash: str
    last_modified: float
    extractor: str
    extractor_version: str


def normalize_text_content(text: str) -> str:
    """
    Normalize text content for cross-platform deterministic hashing.

    Normalizes all line endings to LF (Unix-style):
    - CRLF (Windows) -> LF
    - CR (old Mac) -> LF
    - LF (Unix) -> LF (unchanged)

    Does NOT strip trailing whitespace to preserve original formatting.

    Args:
        text: Raw text content

    Returns:
        Normalized text with consistent LF line endings
    """
    # First normalize CRLF to LF
    normalized = text.replace('\r\n', '\n')
    # Then normalize remaining CR to LF
    normalized = normalized.replace('\r', '\n')
    return normalized


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA1 hash of raw file bytes.

    Uses SHA1 for speed and compatibility with git change detection.
    Reads file in binary mode to capture exact bytes.

    Args:
        file_path: Path to file

    Returns:
        SHA1 hex digest (40 characters)
    """
    hasher = hashlib.sha1()
    with open(file_path, 'rb') as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_text_hash(text: str) -> str:
    """
    Compute SHA256 hash of normalized text content.

    Normalizes line endings before hashing for cross-platform consistency.
    Uses SHA256 for stronger integrity verification.

    Args:
        text: Text content (will be normalized)

    Returns:
        SHA256 hex digest (64 characters)
    """
    normalized = normalize_text_content(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def get_extractor_version() -> str:
    """
    Get the current extractor version.

    Checks VERACITY_VERSION environment variable first,
    falls back to DEFAULT_EXTRACTOR_VERSION.

    Returns:
        Version string
    """
    return os.environ.get("VERACITY_VERSION", DEFAULT_EXTRACTOR_VERSION)


def create_provenance_record(
    file_path: str,
    relative_path: Optional[str] = None,
    is_binary: bool = False,
    config: Optional[ProvenanceConfig] = None,
) -> ProvenanceRecord:
    """
    Create a provenance record for a file.

    Args:
        file_path: Absolute path to the file
        relative_path: Optional relative path to store (uses file_path if None)
        is_binary: If True, skip text hash computation
        config: Optional provenance configuration

    Returns:
        ProvenanceRecord with all fields populated
    """
    if config is None:
        config = ProvenanceConfig()

    # Compute file hash (always, even for binary)
    file_hash = compute_file_hash(file_path)

    # Compute text hash (only for text files)
    text_hash = ""
    if not is_binary and config.include_text_hash:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            text_hash = compute_text_hash(content)
        except (UnicodeDecodeError, IOError):
            # Binary file or read error - no text hash
            pass

    # Get last modified timestamp
    last_modified = os.path.getmtime(file_path)

    return ProvenanceRecord(
        path=relative_path if relative_path else file_path,
        file_hash=file_hash,
        text_hash=text_hash,
        last_modified=last_modified,
        extractor=config.extractor_name,
        extractor_version=get_extractor_version(),
    )


def validate_provenance(record: ProvenanceRecord) -> List[str]:
    """
    Validate a provenance record.

    Checks:
    - Path is not empty
    - File hash is valid SHA1 length (40 chars)
    - Text hash is valid SHA256 length (64 chars) or empty
    - Timestamp is non-negative
    - Extractor and version are not empty

    Args:
        record: ProvenanceRecord to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not record.path:
        errors.append("Path cannot be empty")

    if len(record.file_hash) != 40:
        errors.append(f"file_hash must be 40 characters (SHA1), got {len(record.file_hash)}")

    if record.text_hash and len(record.text_hash) != 64:
        errors.append(f"text_hash must be 64 characters (SHA256) or empty, got {len(record.text_hash)}")

    if record.last_modified < 0:
        errors.append("last_modified timestamp cannot be negative")

    if not record.extractor:
        errors.append("Extractor name cannot be empty")

    if not record.extractor_version:
        errors.append("Extractor version cannot be empty")

    return errors


def provenance_to_dict(record: ProvenanceRecord) -> Dict:
    """
    Convert provenance record to dictionary for serialization.

    Args:
        record: ProvenanceRecord to convert

    Returns:
        Dictionary with all provenance fields
    """
    return {
        "path": record.path,
        "file_hash": record.file_hash,
        "text_hash": record.text_hash,
        "last_modified": record.last_modified,
        "extractor": record.extractor,
        "extractor_version": record.extractor_version,
    }


def create_node_provenance_fields(
    file_path: str,
    relative_path: str,
    is_binary: bool = False,
) -> Dict:
    """
    Create provenance fields suitable for Neo4j node properties.

    Convenience function that creates a provenance record and converts
    it to a dictionary of fields that can be added to node properties.

    Args:
        file_path: Absolute path to source file
        relative_path: Relative path for storage
        is_binary: Whether the file is binary

    Returns:
        Dictionary with provenance fields prefixed with 'prov_'
    """
    record = create_provenance_record(
        file_path,
        relative_path=relative_path,
        is_binary=is_binary,
    )

    return {
        "prov_path": record.path,
        "prov_file_hash": record.file_hash,
        "prov_text_hash": record.text_hash,
        "prov_last_modified": record.last_modified,
        "prov_extractor": record.extractor,
        "prov_extractor_version": record.extractor_version,
    }


def provenance_matches(record1: ProvenanceRecord, record2: ProvenanceRecord) -> bool:
    """
    Check if two provenance records represent the same content.

    Compares file_hash and text_hash to determine if content is identical.
    Ignores path, timestamps, and extractor info.

    Args:
        record1: First provenance record
        record2: Second provenance record

    Returns:
        True if content hashes match
    """
    return (
        record1.file_hash == record2.file_hash and
        record1.text_hash == record2.text_hash
    )


def has_content_changed(
    file_path: str,
    previous_file_hash: Optional[str] = None,
    previous_text_hash: Optional[str] = None,
) -> bool:
    """
    Check if file content has changed since last provenance.

    Efficient change detection using hashes.

    Args:
        file_path: Path to file to check
        previous_file_hash: Previous SHA1 hash of raw bytes
        previous_text_hash: Previous SHA256 hash of text content

    Returns:
        True if content has changed (or no previous hash provided)
    """
    if previous_file_hash is None and previous_text_hash is None:
        return True  # No previous hash means treat as changed

    current_file_hash = compute_file_hash(file_path)

    if previous_file_hash and current_file_hash != previous_file_hash:
        return True

    # If file hash matches but we have text hash to compare
    if previous_text_hash:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            current_text_hash = compute_text_hash(content)
            if current_text_hash != previous_text_hash:
                return True
        except (UnicodeDecodeError, IOError):
            # Can't read as text, rely on file hash only
            pass

    return False
