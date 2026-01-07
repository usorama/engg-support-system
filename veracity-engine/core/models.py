"""
Model Version Management for Veracity Engine (STORY-002).

This module provides utilities for:
- Verifying Ollama model versions and digests
- Ensuring deterministic model selection
- Logging model versions for audit trail

Usage:
    from core.models import verify_models_on_startup, get_model_info

    # Verify models match expected configuration
    verify_models_on_startup(config)

    # Get model information
    info = get_model_info("nomic-embed-text")
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import ollama

from core.config import get_config, VeracityConfig

logger = logging.getLogger(__name__)


class ModelVersionMismatchError(Exception):
    """Raised when model version doesn't match expected configuration."""
    pass


class ModelNotFoundError(Exception):
    """Raised when model is not found in Ollama."""
    pass


@dataclass
class ModelInfo:
    """Information about an Ollama model."""
    name: str
    digest: str
    size: int
    modified_at: str
    details: Dict[str, Any]

    @property
    def short_digest(self) -> str:
        """Return short form of digest (first 12 chars)."""
        return self.digest[:12] if self.digest else ""


def get_model_info(model_name: str) -> Optional[ModelInfo]:
    """
    Get information about an Ollama model.

    Args:
        model_name: Name of the model (e.g., "nomic-embed-text", "llama3.2")

    Returns:
        ModelInfo with model details, or None if not found

    Raises:
        ModelNotFoundError: If the model is not found in Ollama
    """
    try:
        # List all models
        models = ollama.list()

        # Find the matching model
        for model in models.get('models', []):
            name = model.get('name', '')
            # Match by name (ignore tag for base comparison)
            base_name = name.split(':')[0]
            if base_name == model_name or name == model_name:
                return ModelInfo(
                    name=name,
                    digest=model.get('digest', ''),
                    size=model.get('size', 0),
                    modified_at=model.get('modified_at', ''),
                    details=model.get('details', {})
                )

        raise ModelNotFoundError(f"Model '{model_name}' not found in Ollama")

    except Exception as e:
        if isinstance(e, ModelNotFoundError):
            raise
        logger.warning(f"Failed to get model info for '{model_name}': {e}")
        return None


def verify_model_digest(model_name: str, expected_digest: str) -> bool:
    """
    Verify that a model's digest matches the expected value.

    Args:
        model_name: Name of the model to verify
        expected_digest: Expected SHA256 digest (can be short or full form)

    Returns:
        True if digest matches, False otherwise

    Raises:
        ModelNotFoundError: If the model is not found
        ModelVersionMismatchError: If digest doesn't match and strict mode
    """
    info = get_model_info(model_name)
    if info is None:
        raise ModelNotFoundError(f"Model '{model_name}' not found")

    # Compare digests (support both short and full forms)
    actual_digest = info.digest
    if expected_digest.startswith('sha256:'):
        expected_digest = expected_digest[7:]

    # Short form comparison (first N chars)
    if len(expected_digest) < len(actual_digest):
        matches = actual_digest.startswith(expected_digest)
    else:
        matches = actual_digest == expected_digest

    if not matches:
        logger.warning(
            f"Model digest mismatch for '{model_name}': "
            f"expected '{expected_digest[:12]}...', got '{actual_digest[:12]}...'"
        )

    return matches


def verify_models_on_startup(config: Optional[VeracityConfig] = None) -> Dict[str, bool]:
    """
    Verify all configured models on startup.

    Args:
        config: Configuration to use. If None, uses singleton.

    Returns:
        Dictionary mapping model names to verification status

    Logs:
        - Model versions for audit trail
        - Warnings for any mismatches
    """
    if config is None:
        config = get_config()

    results = {}

    # Verify embedding model
    embed_model = config.embedding.model
    try:
        embed_info = get_model_info(embed_model)
        if embed_info:
            logger.info(
                f"Embedding model: {embed_info.name} "
                f"(digest: {embed_info.short_digest})"
            )

            # Verify digest if configured
            if config.embedding.digest and config.embedding.verify_on_startup:
                matches = verify_model_digest(embed_model, config.embedding.digest)
                results[embed_model] = matches
                if not matches:
                    logger.warning(
                        f"Embedding model digest mismatch! "
                        f"Expected: {config.embedding.digest[:12]}..., "
                        f"Actual: {embed_info.short_digest}"
                    )
            else:
                results[embed_model] = True
        else:
            results[embed_model] = False
            logger.error(f"Embedding model '{embed_model}' not found in Ollama")
    except Exception as e:
        results[embed_model] = False
        logger.error(f"Failed to verify embedding model: {e}")

    # Verify LLM model
    llm_model = config.llm.model
    try:
        llm_info = get_model_info(llm_model)
        if llm_info:
            logger.info(
                f"LLM model: {llm_info.name} "
                f"(digest: {llm_info.short_digest})"
            )

            # Verify digest if configured
            if config.llm.digest and config.llm.verify_on_startup:
                matches = verify_model_digest(llm_model, config.llm.digest)
                results[llm_model] = matches
                if not matches:
                    logger.warning(
                        f"LLM model digest mismatch! "
                        f"Expected: {config.llm.digest[:12]}..., "
                        f"Actual: {llm_info.short_digest}"
                    )
            else:
                results[llm_model] = True
        else:
            results[llm_model] = False
            logger.error(f"LLM model '{llm_model}' not found in Ollama")
    except Exception as e:
        results[llm_model] = False
        logger.error(f"Failed to verify LLM model: {e}")

    return results


def get_all_model_digests() -> Dict[str, str]:
    """
    Get digests for all available Ollama models.

    Returns:
        Dictionary mapping model names to their digests
    """
    try:
        models = ollama.list()
        return {
            model.get('name', ''): model.get('digest', '')
            for model in models.get('models', [])
        }
    except Exception as e:
        logger.error(f"Failed to list Ollama models: {e}")
        return {}


def log_model_versions(config: Optional[VeracityConfig] = None) -> None:
    """
    Log all model versions for audit trail.

    Args:
        config: Configuration to use. If None, uses singleton.
    """
    if config is None:
        config = get_config()

    logger.info("=" * 50)
    logger.info("MODEL VERSION AUDIT")
    logger.info("=" * 50)

    # Log configured models
    logger.info(f"Configured embedding model: {config.embedding.model}")
    if config.embedding.version:
        logger.info(f"  Version: {config.embedding.version}")
    if config.embedding.digest:
        logger.info(f"  Expected digest: {config.embedding.digest[:12]}...")

    logger.info(f"Configured LLM model: {config.llm.model}")
    if config.llm.version:
        logger.info(f"  Version: {config.llm.version}")
    if config.llm.digest:
        logger.info(f"  Expected digest: {config.llm.digest[:12]}...")

    # Log actual Ollama models
    digests = get_all_model_digests()
    logger.info("Available Ollama models:")
    for name, digest in digests.items():
        logger.info(f"  {name}: {digest[:12]}...")

    logger.info("=" * 50)
