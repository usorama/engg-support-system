#!/usr/bin/env python3
"""
Model Verification Script for Veracity Engine (STORY-002).

Verifies Ollama models and Python dependencies are correctly configured.

Usage:
    python3 scripts/verify_models.py
    python3 scripts/verify_models.py --config config/veracity.yaml
    python3 scripts/verify_models.py --export > model-digests.txt
"""
import argparse
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import ConfigLoader
from core.models import (
    get_model_info,
    get_all_model_digests,
    verify_models_on_startup,
    log_model_versions,
    ModelNotFoundError
)


def verify_ollama_models(config) -> bool:
    """Verify Ollama models match configuration."""
    print("\n" + "=" * 60)
    print("OLLAMA MODEL VERIFICATION")
    print("=" * 60)

    all_passed = True

    # Verify embedding model
    embed_model = config.embedding.model
    print(f"\nEmbedding Model: {embed_model}")
    print(f"  Expected version: {config.embedding.version or 'any'}")
    print(f"  Expected digest: {config.embedding.digest or 'any'}")

    try:
        embed_info = get_model_info(embed_model)
        if embed_info:
            print(f"  Actual: {embed_info.name}")
            print(f"  Actual digest: {embed_info.digest[:12]}...")
            print(f"  Size: {embed_info.size / 1e6:.1f} MB")

            if config.embedding.digest:
                if embed_info.digest.startswith(config.embedding.digest.replace('sha256:', '')):
                    print("  [PASS] Digest matches")
                else:
                    print("  [FAIL] Digest mismatch!")
                    all_passed = False
            else:
                print("  [INFO] No digest configured for verification")
        else:
            print("  [FAIL] Model not found!")
            all_passed = False
    except ModelNotFoundError:
        print(f"  [FAIL] Model '{embed_model}' not found in Ollama")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False

    # Verify LLM model
    llm_model = config.llm.model
    print(f"\nLLM Model: {llm_model}")
    print(f"  Expected version: {config.llm.version or 'any'}")
    print(f"  Expected digest: {config.llm.digest or 'any'}")

    try:
        llm_info = get_model_info(llm_model)
        if llm_info:
            print(f"  Actual: {llm_info.name}")
            print(f"  Actual digest: {llm_info.digest[:12]}...")
            print(f"  Size: {llm_info.size / 1e6:.1f} MB")

            if config.llm.digest:
                if llm_info.digest.startswith(config.llm.digest.replace('sha256:', '')):
                    print("  [PASS] Digest matches")
                else:
                    print("  [FAIL] Digest mismatch!")
                    all_passed = False
            else:
                print("  [INFO] No digest configured for verification")
        else:
            print("  [FAIL] Model not found!")
            all_passed = False
    except ModelNotFoundError:
        print(f"  [FAIL] Model '{llm_model}' not found in Ollama")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False

    return all_passed


def list_all_models() -> None:
    """List all available Ollama models."""
    print("\n" + "=" * 60)
    print("AVAILABLE OLLAMA MODELS")
    print("=" * 60)

    digests = get_all_model_digests()
    if not digests:
        print("No models found or Ollama not running")
        return

    for name, digest in digests.items():
        print(f"  {name}: {digest[:12]}...")


def export_digests() -> None:
    """Export all model digests as JSON."""
    digests = get_all_model_digests()
    output = {
        "models": [
            {"name": name, "digest": digest}
            for name, digest in digests.items()
        ]
    }
    print(json.dumps(output, indent=2))


def verify_python_deps() -> bool:
    """Verify Python dependencies are installed correctly."""
    print("\n" + "=" * 60)
    print("PYTHON DEPENDENCY VERIFICATION")
    print("=" * 60)

    required = {
        "neo4j": "5.28.2",
        "ollama": "0.6.1",
        "pydantic": "2.12.5",
        "pydantic-settings": "2.11.0",
        "PyYAML": "6.0.3",
        "pytest": "8.4.2",
    }

    all_passed = True
    for package, expected_version in required.items():
        try:
            import importlib.metadata
            actual_version = importlib.metadata.version(package)
            if actual_version == expected_version:
                print(f"  [PASS] {package}=={actual_version}")
            else:
                print(f"  [WARN] {package}: expected {expected_version}, got {actual_version}")
                # Don't fail for minor version differences
        except importlib.metadata.PackageNotFoundError:
            print(f"  [FAIL] {package} not installed!")
            all_passed = False

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify Ollama models and Python dependencies"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file (YAML)"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export model digests as JSON"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available models"
    )
    args = parser.parse_args()

    # Export mode
    if args.export:
        export_digests()
        return 0

    # List mode
    if args.list:
        list_all_models()
        return 0

    # Load configuration
    config = ConfigLoader.load(config_file=args.config)

    print("\n" + "=" * 60)
    print("VERACITY ENGINE MODEL VERIFICATION")
    print("=" * 60)

    # Verify Python dependencies
    deps_ok = verify_python_deps()

    # Verify Ollama models
    models_ok = verify_ollama_models(config)

    # List all models
    list_all_models()

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  Python dependencies: {'PASS' if deps_ok else 'FAIL'}")
    print(f"  Ollama models: {'PASS' if models_ok else 'FAIL'}")

    if deps_ok and models_ok:
        print("\n[SUCCESS] All verifications passed!")
        return 0
    else:
        print("\n[FAILURE] Some verifications failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
