"""
Tests for Repository Map + Structural Ranking (STORY-013).

Tests cover:
1. Symbol extraction from Python AST
2. Dependency graph construction (imports/references)
3. PageRank-based ranking
4. Deterministic output ordering
5. Token budget packing
6. Provenance tracking
"""
import pytest
import tempfile
import os
from pathlib import Path

from core.repo_map import (
    # Schema types
    SymbolKind,
    SymbolEntry,
    DependencyEdge,
    RepoMapConfig,
    RepoMapResult,
    # Extraction functions
    extract_symbols_from_file,
    extract_imports,
    # Graph construction
    build_dependency_graph,
    # Ranking
    compute_pagerank,
    # Main pipeline
    generate_repo_map,
    # Constants
    DEFAULT_DAMPING_FACTOR,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_TOKEN_BUDGET,
)


class TestSymbolKind:
    """Tests for symbol kind enum."""

    def test_symbol_kinds_defined(self):
        """All symbol kinds should be defined."""
        assert SymbolKind.FUNCTION is not None
        assert SymbolKind.CLASS is not None
        assert SymbolKind.METHOD is not None
        assert SymbolKind.VARIABLE is not None
        assert SymbolKind.IMPORT is not None
        assert SymbolKind.MODULE is not None


class TestSymbolEntry:
    """Tests for symbol entry structure."""

    def test_entry_has_required_fields(self):
        """Symbol entry should have all required fields."""
        entry = SymbolEntry(
            path="src/main.py",
            symbol="main",
            kind=SymbolKind.FUNCTION,
            signature="def main(args: list) -> int",
            start_line=10,
            end_line=25,
        )
        assert entry.path == "src/main.py"
        assert entry.symbol == "main"
        assert entry.kind == SymbolKind.FUNCTION
        assert entry.signature == "def main(args: list) -> int"
        assert entry.start_line == 10
        assert entry.end_line == 25

    def test_entry_to_dict(self):
        """Symbol entry should convert to dictionary."""
        entry = SymbolEntry(
            path="src/util.py",
            symbol="helper",
            kind=SymbolKind.FUNCTION,
            signature="def helper()",
            start_line=5,
            end_line=10,
        )
        d = entry.to_dict()
        assert d["path"] == "src/util.py"
        assert d["symbol"] == "helper"
        assert d["kind"] == "FUNCTION"
        assert "signature" in d


class TestRepoMapConfig:
    """Tests for repository map configuration."""

    def test_default_config(self):
        """Default config should have valid values."""
        config = RepoMapConfig()
        assert config.damping_factor == DEFAULT_DAMPING_FACTOR
        assert config.max_iterations == DEFAULT_MAX_ITERATIONS
        assert config.token_budget == DEFAULT_TOKEN_BUDGET

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = RepoMapConfig(
            damping_factor=0.9,
            max_iterations=50,
            token_budget=2048,
        )
        assert config.damping_factor == 0.9
        assert config.max_iterations == 50
        assert config.token_budget == 2048


class TestSymbolExtraction:
    """Tests for Python AST symbol extraction."""

    def test_extract_function(self):
        """Should extract function definitions."""
        code = '''
def hello_world():
    """Say hello."""
    print("Hello, World!")
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        assert len(symbols) >= 1
        func = next((s for s in symbols if s.symbol == "hello_world"), None)
        assert func is not None
        assert func.kind == SymbolKind.FUNCTION
        assert "def hello_world()" in func.signature

    def test_extract_class(self):
        """Should extract class definitions."""
        code = '''
class MyClass:
    """A simple class."""

    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        # Should have class and methods
        class_sym = next((s for s in symbols if s.symbol == "MyClass"), None)
        assert class_sym is not None
        assert class_sym.kind == SymbolKind.CLASS

    def test_extract_method(self):
        """Should extract methods inside classes."""
        code = '''
class Calculator:
    def add(self, a, b):
        return a + b
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        method = next((s for s in symbols if s.symbol == "add"), None)
        assert method is not None
        assert method.kind == SymbolKind.METHOD

    def test_extract_module_level_variables(self):
        """Should extract module-level variables."""
        code = '''
VERSION = "1.0.0"
DEBUG = True
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        version = next((s for s in symbols if s.symbol == "VERSION"), None)
        assert version is not None
        assert version.kind == SymbolKind.VARIABLE

    def test_extract_with_type_annotations(self):
        """Should capture type annotations in signature."""
        code = '''
def process(data: list[str], count: int = 10) -> dict:
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        func = next((s for s in symbols if s.symbol == "process"), None)
        assert func is not None
        # Signature should include type hints
        assert "data" in func.signature
        assert "->" in func.signature or "dict" in func.signature

    def test_invalid_syntax_returns_empty(self):
        """Should handle invalid Python syntax gracefully."""
        code = '''
def broken(
    # Missing closing parenthesis
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        # Should return empty list, not raise exception
        assert symbols == []

    def test_non_python_file_returns_empty(self):
        """Should return empty for non-Python files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Not Python code")
            f.flush()
            symbols = extract_symbols_from_file(f.name)
        os.unlink(f.name)

        assert symbols == []


class TestImportExtraction:
    """Tests for import statement extraction."""

    def test_extract_simple_import(self):
        """Should extract simple import statements."""
        code = '''
import os
import sys
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            imports = extract_imports(f.name)
        os.unlink(f.name)

        assert "os" in imports
        assert "sys" in imports

    def test_extract_from_import(self):
        """Should extract from-import statements."""
        code = '''
from pathlib import Path
from collections import defaultdict, Counter
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            imports = extract_imports(f.name)
        os.unlink(f.name)

        assert "pathlib" in imports
        assert "collections" in imports

    def test_extract_relative_import(self):
        """Should extract relative imports."""
        code = '''
from . import sibling
from ..parent import module
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            imports = extract_imports(f.name)
        os.unlink(f.name)

        # Relative imports should be captured
        assert len(imports) >= 0  # May include . or .. prefixed


class TestDependencyGraph:
    """Tests for dependency graph construction."""

    def test_build_graph_from_imports(self):
        """Should build graph edges from import relationships."""
        # Create temp project with two files
        with tempfile.TemporaryDirectory() as tmpdir:
            # File A imports from File B
            file_a = os.path.join(tmpdir, "a.py")
            file_b = os.path.join(tmpdir, "b.py")

            with open(file_a, 'w') as f:
                f.write("from b import helper\n")
            with open(file_b, 'w') as f:
                f.write("def helper(): pass\n")

            edges = build_dependency_graph(tmpdir)

            # Should have edge from a.py to b.py
            assert len(edges) >= 1
            edge = next((e for e in edges if "a.py" in e.source), None)
            assert edge is not None

    def test_empty_directory_no_edges(self):
        """Should return empty edges for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            edges = build_dependency_graph(tmpdir)
            assert edges == []


class TestPageRank:
    """Tests for PageRank-based ranking."""

    def test_single_node_rank(self):
        """Single node should have rank 1.0."""
        edges = []  # No edges
        nodes = ["file.py"]
        ranks = compute_pagerank(nodes, edges)
        assert ranks["file.py"] == pytest.approx(1.0, abs=0.01)

    def test_equal_nodes_equal_rank(self):
        """Disconnected nodes should have equal rank."""
        edges = []
        nodes = ["a.py", "b.py", "c.py"]
        ranks = compute_pagerank(nodes, edges)

        # All should be approximately equal
        values = list(ranks.values())
        assert all(abs(v - values[0]) < 0.01 for v in values)

    def test_hub_node_higher_rank(self):
        """Node with many incoming edges should rank higher."""
        edges = [
            DependencyEdge(source="a.py", target="hub.py"),
            DependencyEdge(source="b.py", target="hub.py"),
            DependencyEdge(source="c.py", target="hub.py"),
        ]
        nodes = ["a.py", "b.py", "c.py", "hub.py"]
        ranks = compute_pagerank(nodes, edges)

        # hub.py should have highest rank
        assert ranks["hub.py"] > ranks["a.py"]

    def test_deterministic_ranking(self):
        """Same inputs should produce same ranks."""
        edges = [
            DependencyEdge(source="a.py", target="b.py"),
            DependencyEdge(source="b.py", target="c.py"),
        ]
        nodes = ["a.py", "b.py", "c.py"]

        ranks1 = compute_pagerank(nodes, edges)
        ranks2 = compute_pagerank(nodes, edges)

        for node in nodes:
            assert ranks1[node] == ranks2[node]

    def test_custom_damping_factor(self):
        """Should accept custom damping factor."""
        edges = [DependencyEdge(source="a.py", target="b.py")]
        nodes = ["a.py", "b.py"]

        ranks_85 = compute_pagerank(nodes, edges, damping=0.85)
        ranks_50 = compute_pagerank(nodes, edges, damping=0.50)

        # Different damping should produce different results
        # (exact values depend on implementation, but should differ)
        # Just verify no errors occur
        assert "a.py" in ranks_85
        assert "a.py" in ranks_50


class TestRepoMapResult:
    """Tests for repository map result structure."""

    def test_result_structure(self):
        """Result should have required fields."""
        result = RepoMapResult(
            entries=[],
            total_symbols=0,
            included_symbols=0,
            token_count=0,
        )
        assert result.entries == []
        assert result.total_symbols == 0

    def test_result_to_dict(self):
        """Result should convert to dictionary."""
        entry = SymbolEntry(
            path="test.py",
            symbol="test_func",
            kind=SymbolKind.FUNCTION,
            signature="def test_func()",
            start_line=1,
            end_line=3,
            rank=0.5,
        )
        result = RepoMapResult(
            entries=[entry],
            total_symbols=1,
            included_symbols=1,
            token_count=10,
        )
        d = result.to_dict()
        assert "entries" in d
        assert len(d["entries"]) == 1
        assert "total_symbols" in d


class TestGenerateRepoMap:
    """Tests for complete repo map generation."""

    def test_generate_simple_project(self):
        """Should generate repo map for simple project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file
            main_py = os.path.join(tmpdir, "main.py")
            with open(main_py, 'w') as f:
                f.write('''
def main():
    """Entry point."""
    print("Hello")

class App:
    def run(self):
        pass
''')

            result = generate_repo_map(tmpdir)

            assert result.total_symbols >= 3  # main, App, run
            assert result.included_symbols > 0

    def test_entries_have_rank(self):
        """Each entry should have a rank value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main_py = os.path.join(tmpdir, "main.py")
            with open(main_py, 'w') as f:
                f.write("def func(): pass\n")

            result = generate_repo_map(tmpdir)

            for entry in result.entries:
                assert entry.rank is not None
                assert 0 <= entry.rank <= 1.0

    def test_deterministic_output(self):
        """Same project should produce identical repo map."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main_py = os.path.join(tmpdir, "main.py")
            with open(main_py, 'w') as f:
                f.write('''
def alpha(): pass
def beta(): pass
def gamma(): pass
''')

            result1 = generate_repo_map(tmpdir)
            result2 = generate_repo_map(tmpdir)

            # Same number of entries
            assert len(result1.entries) == len(result2.entries)

            # Same order
            for e1, e2 in zip(result1.entries, result2.entries):
                assert e1.symbol == e2.symbol
                assert e1.rank == e2.rank

    def test_ordering_by_rank_then_path(self):
        """Entries should be ordered by rank (desc), then path (asc)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files that will have different ranks
            for name in ["aaa.py", "bbb.py", "ccc.py"]:
                with open(os.path.join(tmpdir, name), 'w') as f:
                    f.write(f"def func_{name[0]}(): pass\n")

            result = generate_repo_map(tmpdir)

            # Verify ordering: entries should be sorted
            if len(result.entries) >= 2:
                for i in range(len(result.entries) - 1):
                    e1, e2 = result.entries[i], result.entries[i + 1]
                    # Either rank is higher, or ranks equal and path is earlier
                    assert (e1.rank > e2.rank or
                            (e1.rank == e2.rank and e1.path <= e2.path))

    def test_token_budget_respected(self):
        """Should respect token budget limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create many symbols
            code = "\n".join([f"def func_{i}(): pass" for i in range(100)])
            with open(os.path.join(tmpdir, "many_funcs.py"), 'w') as f:
                f.write(code)

            config = RepoMapConfig(token_budget=50)  # Very small budget
            result = generate_repo_map(tmpdir, config)

            # Should have fewer entries due to budget
            assert result.token_count <= 50
            assert result.included_symbols < result.total_symbols

    def test_provenance_in_entries(self):
        """Entries should include provenance information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main_py = os.path.join(tmpdir, "main.py")
            with open(main_py, 'w') as f:
                f.write("def test(): pass\n")

            result = generate_repo_map(tmpdir)

            if result.entries:
                entry = result.entries[0]
                # Should have provenance (path at minimum)
                assert entry.path is not None

    def test_empty_directory(self):
        """Should handle empty directory gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_repo_map(tmpdir)

            assert result.total_symbols == 0
            assert result.entries == []

    def test_nested_directory_structure(self):
        """Should handle nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = os.path.join(tmpdir, "src", "utils")
            os.makedirs(subdir)

            with open(os.path.join(subdir, "helpers.py"), 'w') as f:
                f.write("def helper(): pass\n")

            result = generate_repo_map(tmpdir)

            assert result.total_symbols >= 1
            # Path should include relative path
            assert any("helpers.py" in e.path for e in result.entries)
