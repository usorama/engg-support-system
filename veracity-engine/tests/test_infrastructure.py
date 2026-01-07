"""
Tests for Infrastructure Validation (STORY-005).

Tests cover:
1. Dependency validation functions
2. Health check script execution
3. Port checking utilities
"""
import sys
import subprocess
import importlib.util
from pathlib import Path

import pytest

# Load validate_deps module directly from file
_script_path = Path(__file__).parent.parent / "scripts" / "validate-deps.py"
_spec = importlib.util.spec_from_file_location("validate_deps", _script_path)
validate_deps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_deps)

# Import functions from the loaded module
check_python_version = validate_deps.check_python_version
check_packages = validate_deps.check_packages
check_docker = validate_deps.check_docker
check_port = validate_deps.check_port
check_ports = validate_deps.check_ports
ValidationResult = validate_deps.ValidationResult


class TestPythonVersionCheck:
    """Tests for Python version validation."""

    def test_current_version_passes(self):
        """Current Python version should pass minimum check."""
        result = check_python_version("3.9")
        assert isinstance(result, ValidationResult)
        assert result.name == "python_version"
        # Should pass since we're running on Python 3.9+
        assert result.valid is True

    def test_high_minimum_fails(self):
        """Higher minimum than current should fail."""
        result = check_python_version("99.0")
        assert result.valid is False

    def test_result_has_details(self):
        """Result should include version details."""
        result = check_python_version("3.9")
        assert "current" in result.details
        assert "required" in result.details


class TestPackageCheck:
    """Tests for package validation."""

    def test_installed_packages_pass(self):
        """Already installed packages should pass."""
        result = check_packages(["pytest"])
        assert result.valid is True
        assert "pytest" in result.details["installed"]

    def test_missing_packages_fail(self):
        """Non-existent packages should fail."""
        result = check_packages(["nonexistent_package_xyz"])
        assert result.valid is False
        assert "nonexistent_package_xyz" in result.details["missing"]

    def test_mixed_packages(self):
        """Mix of installed and missing should fail."""
        result = check_packages(["pytest", "nonexistent_xyz"])
        assert result.valid is False
        assert "pytest" in result.details["installed"]
        assert "nonexistent_xyz" in result.details["missing"]


class TestDockerCheck:
    """Tests for Docker availability."""

    def test_docker_check_returns_result(self):
        """Docker check should return a ValidationResult."""
        result = check_docker()
        assert isinstance(result, ValidationResult)
        assert result.name == "docker"
        # Result can be True or False depending on Docker availability
        assert isinstance(result.valid, bool)


class TestPortCheck:
    """Tests for port availability checking."""

    def test_check_port_returns_tuple(self):
        """check_port should return (available, error)."""
        available, error = check_port(12345)
        assert isinstance(available, bool)

    def test_check_ports_returns_result(self):
        """check_ports should return ValidationResult."""
        result = check_ports([7474, 7687])
        assert isinstance(result, ValidationResult)
        assert "ports" in result.details


class TestHealthCheckScript:
    """Tests for the health check bash script."""

    def test_script_exists(self):
        """Health check script should exist."""
        script_path = Path(__file__).parent.parent / "scripts" / "health-check.sh"
        assert script_path.exists()

    def test_script_is_executable(self):
        """Health check script should be executable."""
        script_path = Path(__file__).parent.parent / "scripts" / "health-check.sh"
        import os
        assert os.access(script_path, os.X_OK)

    def test_script_json_output(self):
        """Health check script should support --json flag."""
        script_path = Path(__file__).parent.parent / "scripts" / "health-check.sh"
        result = subprocess.run(
            ["bash", str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Script may fail if services not running, but output should be JSON
        import json
        try:
            data = json.loads(result.stdout)
            assert "timestamp" in data
            assert "overall_status" in data
            assert "neo4j" in data
        except json.JSONDecodeError:
            # If output isn't JSON, that's a failure
            pytest.fail("Health check --json output is not valid JSON")


class TestValidateDepsScript:
    """Tests for the validate-deps.py script."""

    def test_script_exists(self):
        """Validate deps script should exist."""
        script_path = Path(__file__).parent.parent / "scripts" / "validate-deps.py"
        assert script_path.exists()

    def test_script_runs(self):
        """Validate deps script should run without error."""
        script_path = Path(__file__).parent.parent / "scripts" / "validate-deps.py"
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Should complete without crashing
        assert result.returncode in [0, 1]  # 0=pass, 1=fail (both valid)

    def test_script_json_output(self):
        """Validate deps script should support --json flag."""
        script_path = Path(__file__).parent.parent / "scripts" / "validate-deps.py"
        result = subprocess.run(
            ["python3", str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        import json
        data = json.loads(result.stdout)
        assert "validations" in data
        assert "overall_valid" in data


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_result_creation(self):
        """Should create ValidationResult with required fields."""
        result = ValidationResult(
            name="test",
            valid=True,
            message="Test passed"
        )
        assert result.name == "test"
        assert result.valid is True
        assert result.message == "Test passed"
        assert result.details == {}

    def test_result_with_details(self):
        """Should create ValidationResult with details."""
        result = ValidationResult(
            name="test",
            valid=False,
            message="Test failed",
            details={"reason": "something"}
        )
        assert result.details["reason"] == "something"


class TestVPSDeploymentDocs:
    """Tests for VPS deployment documentation."""

    def test_docs_exist(self):
        """VPS deployment docs should exist."""
        docs_path = Path(__file__).parent.parent / "docs" / "OPERATIONS" / "VPS_DEPLOYMENT.md"
        assert docs_path.exists()

    def test_docs_content(self):
        """VPS deployment docs should have key sections."""
        docs_path = Path(__file__).parent.parent / "docs" / "OPERATIONS" / "VPS_DEPLOYMENT.md"
        content = docs_path.read_text()

        assert "System Requirements" in content
        assert "Deployment Steps" in content
        assert "Health Checks" in content
        assert "Troubleshooting" in content
