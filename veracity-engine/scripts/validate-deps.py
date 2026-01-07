#!/usr/bin/env python3
"""
Dependency Validation Script for Veracity Engine (STORY-005).

Validates all runtime dependencies before deployment:
- Python version
- Required packages
- Docker availability
- Port availability
- Ollama models

Usage:
    python3 scripts/validate-deps.py
    python3 scripts/validate-deps.py --json
    python3 scripts/validate-deps.py --strict
"""
import argparse
import json
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    valid: bool
    message: str
    details: Dict = field(default_factory=dict)


def check_python_version(min_version: str = "3.9") -> ValidationResult:
    """Check Python version meets minimum requirements."""
    current = f"{sys.version_info.major}.{sys.version_info.minor}"
    min_major, min_minor = map(int, min_version.split("."))

    valid = (
        sys.version_info.major > min_major or
        (sys.version_info.major == min_major and sys.version_info.minor >= min_minor)
    )

    return ValidationResult(
        name="python_version",
        valid=valid,
        message=f"Python {current} {'meets' if valid else 'does not meet'} minimum {min_version}",
        details={"current": current, "required": min_version}
    )


def check_packages(required: List[str]) -> ValidationResult:
    """Check required Python packages are installed."""
    import importlib.metadata

    missing = []
    installed = {}

    for package in required:
        try:
            version = importlib.metadata.version(package)
            installed[package] = version
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)

    valid = len(missing) == 0

    return ValidationResult(
        name="python_packages",
        valid=valid,
        message=f"{'All' if valid else 'Not all'} required packages installed",
        details={"installed": installed, "missing": missing}
    )


def check_docker() -> ValidationResult:
    """Check Docker daemon is available."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        valid = result.returncode == 0

        return ValidationResult(
            name="docker",
            valid=valid,
            message="Docker is available" if valid else "Docker not available",
            details={"output": result.stdout[:200] if valid else result.stderr[:200]}
        )
    except FileNotFoundError:
        return ValidationResult(
            name="docker",
            valid=False,
            message="Docker not installed",
            details={}
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            name="docker",
            valid=False,
            message="Docker timeout",
            details={}
        )


def check_port(port: int, host: str = "127.0.0.1") -> Tuple[bool, Optional[str]]:
    """Check if a port is available (not in use)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((host, port))
        sock.close()
        return False, "in use"  # Port is in use (something listening)
    except socket.timeout:
        return True, None  # Port timeout = available
    except ConnectionRefusedError:
        return True, None  # Connection refused = available
    except Exception as e:
        return True, str(e)


def check_ports(ports: List[int]) -> ValidationResult:
    """Check required ports are not in use or are used by our services."""
    port_status = {}
    conflicts = []

    for port in ports:
        available, error = check_port(port)
        port_status[port] = "available" if available else "in_use"
        # Note: in_use is not necessarily a conflict if it's our service

    return ValidationResult(
        name="ports",
        valid=True,  # We just report, don't fail on this
        message="Port scan complete",
        details={"ports": port_status}
    )


def check_ollama() -> ValidationResult:
    """Check Ollama is available."""
    try:
        import ollama
        models = ollama.list()
        model_names = [m.get("name", "") for m in models.get("models", [])]

        return ValidationResult(
            name="ollama",
            valid=True,
            message=f"Ollama available with {len(model_names)} models",
            details={"models": model_names}
        )
    except ImportError:
        return ValidationResult(
            name="ollama",
            valid=False,
            message="Ollama Python package not installed",
            details={}
        )
    except Exception as e:
        return ValidationResult(
            name="ollama",
            valid=False,
            message=f"Ollama not available: {e}",
            details={"error": str(e)}
        )


def check_ollama_models(required_models: List[str]) -> ValidationResult:
    """Check required Ollama models are available."""
    try:
        import ollama
        models = ollama.list()
        available = [m.get("name", "").split(":")[0] for m in models.get("models", [])]

        missing = [m for m in required_models if m not in available]
        valid = len(missing) == 0

        return ValidationResult(
            name="ollama_models",
            valid=valid,
            message="All required models available" if valid else f"Missing models: {missing}",
            details={"available": available, "required": required_models, "missing": missing}
        )
    except Exception as e:
        return ValidationResult(
            name="ollama_models",
            valid=False,
            message=f"Cannot check models: {e}",
            details={"error": str(e)}
        )


def run_all_validations() -> List[ValidationResult]:
    """Run all validation checks."""
    results = []

    # Python version
    results.append(check_python_version("3.9"))

    # Required packages
    required_packages = ["neo4j", "ollama", "pydantic", "pydantic_settings", "structlog"]
    results.append(check_packages(required_packages))

    # Docker
    results.append(check_docker())

    # Ports
    required_ports = [7474, 7687, 5173, 11434]
    results.append(check_ports(required_ports))

    # Ollama
    results.append(check_ollama())

    # Ollama models
    required_models = ["nomic-embed-text", "llama3.2"]
    results.append(check_ollama_models(required_models))

    return results


def print_results(results: List[ValidationResult], json_output: bool = False):
    """Print validation results."""
    if json_output:
        output = {
            "validations": [
                {
                    "name": r.name,
                    "valid": r.valid,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ],
            "overall_valid": all(r.valid for r in results)
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 50)
        print("Veracity Engine Dependency Validation")
        print("=" * 50)
        print()

        for result in results:
            status = "\033[92mPASS\033[0m" if result.valid else "\033[91mFAIL\033[0m"
            print(f"[{status}] {result.name}: {result.message}")

            if result.details:
                for key, value in result.details.items():
                    if isinstance(value, list) and len(value) > 5:
                        print(f"       {key}: [{len(value)} items]")
                    elif isinstance(value, dict) and len(value) > 5:
                        print(f"       {key}: {{{len(value)} items}}")
                    else:
                        print(f"       {key}: {value}")

        print()
        print("=" * 50)
        overall = all(r.valid for r in results)
        if overall:
            print("\033[92mAll validations passed!\033[0m")
        else:
            print("\033[91mSome validations failed.\033[0m")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Validate Veracity Engine dependencies")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--strict", action="store_true", help="Exit with error if any check fails")
    args = parser.parse_args()

    results = run_all_validations()
    print_results(results, json_output=args.json)

    if args.strict and not all(r.valid for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
