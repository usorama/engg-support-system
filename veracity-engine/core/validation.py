"""
Input validation utilities for Veracity Engine.

Provides security-focused validation for user inputs to prevent:
- Path traversal attacks
- Injection attacks
- Resource exhaustion

TODO: STORY-003 - Security hardening review
"""
import os
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Validation constants
MAX_PROJECT_NAME_LENGTH = 64
# Project name format: lowercase slug with alphanumeric, dots, underscores, hyphens
# Must start with a letter or number
PROJECT_NAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
FORBIDDEN_PATH_CHARS = ['..', '~', '\x00']


def validate_project_name(name: str) -> str:
    """
    Validate and normalize project name (tenant identifier).

    Project names are immutable identifiers used for multitenancy isolation.
    Format: lowercase slug [a-z0-9._-]+, max 64 chars.

    Args:
        name: Raw project name from user input

    Returns:
        Validated project name (lowercased)

    Raises:
        ValueError: If project name is invalid
    """
    if not name:
        raise ValueError("Project name cannot be empty")

    # Check for null bytes first (security)
    if '\x00' in name:
        raise ValueError("Project name cannot contain null bytes")

    # Normalize to lowercase
    normalized = name.lower()

    if len(normalized) > MAX_PROJECT_NAME_LENGTH:
        raise ValueError(f"Project name exceeds maximum length of {MAX_PROJECT_NAME_LENGTH}")

    # Check for path traversal attempts (consecutive dots)
    if '..' in normalized:
        raise ValueError("Project name cannot contain consecutive dots")

    if not PROJECT_NAME_PATTERN.match(normalized):
        raise ValueError(
            f"Project name must start with a letter or number and contain only "
            f"lowercase alphanumeric characters, dots, underscores, and hyphens. Got: '{name}'"
        )

    logger.debug(f"Validated project name: {normalized}")
    return normalized


def validate_path(path: str, must_exist: bool = False, must_be_dir: bool = False) -> str:
    """
    Validate and normalize a filesystem path.

    Args:
        path: Raw path from user input
        must_exist: If True, path must exist
        must_be_dir: If True, path must be a directory

    Returns:
        Normalized absolute path

    Raises:
        ValueError: If path is invalid or doesn't meet requirements
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Check for null bytes (common injection attack)
    if '\x00' in path:
        raise ValueError("Path contains null bytes")

    # Normalize and make absolute
    normalized = os.path.abspath(os.path.normpath(path))

    # Check for path traversal after normalization
    if '..' in path and not normalized.startswith(os.getcwd()):
        logger.warning(f"Potential path traversal detected: {path} -> {normalized}")

    if must_exist and not os.path.exists(normalized):
        raise ValueError(f"Path does not exist: {normalized}")

    if must_be_dir and not os.path.isdir(normalized):
        raise ValueError(f"Path is not a directory: {normalized}")

    return normalized


def validate_target_dirs(dirs: List[str], root_dir: str) -> List[str]:
    """
    Validate target directories are within root directory.

    Args:
        dirs: List of target directory paths (relative to root_dir)
        root_dir: The validated root directory (absolute path)

    Returns:
        List of validated relative paths (same as input if valid)

    Raises:
        ValueError: If any directory would escape root_dir
    """
    validated = []
    root_abs = os.path.abspath(root_dir)

    for d in dirs:
        # Check for forbidden characters in the directory name
        if '\x00' in d:
            raise ValueError(f"Target directory contains null bytes: '{d}'")

        # Construct full path (assume relative to root)
        full_path = os.path.join(root_abs, d)
        normalized = os.path.abspath(os.path.normpath(full_path))

        # Ensure target is within root (prevents path traversal like "../../../etc")
        # Use os.path.commonpath for reliable comparison
        try:
            common = os.path.commonpath([root_abs, normalized])
            if common != root_abs:
                raise ValueError(
                    f"Target directory '{d}' resolves to '{normalized}' "
                    f"which is outside root directory '{root_abs}'"
                )
        except ValueError:
            # commonpath raises ValueError if paths are on different drives (Windows)
            raise ValueError(
                f"Target directory '{d}' resolves to '{normalized}' "
                f"which is outside root directory '{root_abs}'"
            )

        # Return the original relative path (not absolute) for compatibility
        # with existing code that does os.path.join(root_dir, target)
        validated.append(d)

    return validated
