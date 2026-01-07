"""
Shared embedding utilities for Veracity Engine.

This module provides consistent embedding generation across all components,
consolidating the previously duplicated get_embedding() implementations from
build_graph.py and ask_codebase.py.

Configuration is loaded from ConfigLoader (STORY-001).
"""
import logging
from typing import List, Optional

import ollama

from core.config import get_config

logger = logging.getLogger(__name__)


def get_embedding(
    text: str,
    prefix: Optional[str] = None,
    for_query: bool = False
) -> List[float]:
    """
    Generate embedding vector for text using Ollama.

    This is the single source of truth for embedding generation across
    the Veracity Engine. Use this function instead of calling ollama.embeddings
    directly to ensure consistent behavior and error handling.

    Configuration (model, prefixes) is loaded from ConfigLoader.

    Args:
        text: The text to embed.
        prefix: Optional explicit prefix override. If provided, this takes
                precedence over the for_query flag.
        for_query: If True, uses query prefix from config.
                   If False (default), uses document prefix from config.
                   Ignored if prefix is explicitly provided.

    Returns:
        List of floats representing the embedding vector.
        Returns empty list on failure (with warning logged).

    Example:
        # For indexing documents during graph build:
        embedding = get_embedding("class MyClass: ...")

        # For query embeddings during search:
        embedding = get_embedding("how does authentication work?", for_query=True)

        # With explicit prefix override:
        embedding = get_embedding("custom text", prefix="clustering:")

    Note:
        Per Nomic documentation, using consistent prefixes is important for
        optimal similarity scores. The default (document_prefix) is suitable
        for indexing; use for_query=True when generating query embeddings.
    """
    try:
        # Get configuration
        config = get_config()
        embed_config = config.embedding

        # Determine prefix to use
        if prefix is not None:
            use_prefix = prefix
        elif for_query:
            use_prefix = embed_config.query_prefix
        else:
            use_prefix = embed_config.document_prefix

        # Build prompt with prefix
        prompt = f"{use_prefix} {text}" if use_prefix else text

        # Generate embedding using configured model
        response = ollama.embeddings(model=embed_config.model, prompt=prompt)
        return response["embedding"]

    except Exception as e:
        logger.warning(f"Failed to generate embedding: {e}")
        return []


def get_document_embedding(text: str) -> List[float]:
    """
    Generate embedding for document indexing.

    Convenience wrapper that explicitly uses the document prefix.
    Use this when indexing code, documentation, or other content.

    Args:
        text: The document text to embed.

    Returns:
        List of floats representing the embedding vector.
    """
    return get_embedding(text, for_query=False)


def get_query_embedding(text: str) -> List[float]:
    """
    Generate embedding for search queries.

    Convenience wrapper that explicitly uses the query prefix.
    Use this when generating embeddings for user queries.

    Args:
        text: The query text to embed.

    Returns:
        List of floats representing the embedding vector.
    """
    return get_embedding(text, for_query=True)
