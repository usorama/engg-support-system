"""
Pytest configuration and shared fixtures for Veracity Engine tests.
"""
import pytest
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def project_name():
    """Default test project name."""
    return "test_project"


@pytest.fixture
def neo4j_test_config():
    """Neo4j configuration for testing.

    TODO: STORY-001 - Replace with ConfigLoader
    """
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
    }


@pytest.fixture
def sample_python_code():
    """Sample Python code for AST parsing tests."""
    return '''
class SampleClass:
    """A sample class for testing."""

    def sample_method(self, arg1: str) -> bool:
        """Sample method docstring."""
        return True

def standalone_function():
    """Standalone function for testing."""
    pass
'''


@pytest.fixture(scope="session")
def verify_env_setup():
    """Verify that test environment is properly configured."""
    pass


@pytest.fixture
def mock_config(monkeypatch):
    """Provide a mock configuration for tests."""
    def get_config():
        from unittest.mock import MagicMock
        config = MagicMock()
        config.neo4j.uri = "bolt://localhost:7687"
        config.neo4j.user = "neo4j"
        config.neo4j.password = "test_password"
        return config
    return get_config


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project directory for testing."""
    project = tmp_path / "test_project"
    project.mkdir()
    (project / "example.py").write_text("""
def test_func():
    pass
""")
    return str(project)
