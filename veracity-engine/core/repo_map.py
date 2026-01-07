"""
Repository Map + Structural Ranking Module (STORY-013).

Provides deterministic repository map generation with:
1. Python AST symbol extraction
2. Import/dependency graph construction
3. PageRank-based ranking
4. Token-budgeted packing
5. Provenance tracking

All outputs are evidence-based (no LLM synthesis) and deterministic.
"""
import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Default configuration values
DEFAULT_DAMPING_FACTOR = 0.85
DEFAULT_MAX_ITERATIONS = 100
DEFAULT_TOKEN_BUDGET = 1024
DEFAULT_CONVERGENCE_THRESHOLD = 1e-6

# Approximate tokens per character (for budget estimation)
TOKENS_PER_CHAR = 0.25


class SymbolKind(Enum):
    """Types of extracted symbols."""
    FUNCTION = "FUNCTION"
    CLASS = "CLASS"
    METHOD = "METHOD"
    VARIABLE = "VARIABLE"
    IMPORT = "IMPORT"
    MODULE = "MODULE"


@dataclass
class SymbolEntry:
    """
    A symbol extracted from source code.

    Attributes:
        path: Relative file path
        symbol: Symbol name
        kind: Type of symbol (function, class, etc.)
        signature: Full signature string
        start_line: Starting line number
        end_line: Ending line number
        rank: PageRank score (0-1)
        parent: Parent symbol (for methods)
    """
    path: str
    symbol: str
    kind: SymbolKind
    signature: str
    start_line: int
    end_line: int
    rank: Optional[float] = None
    parent: Optional[str] = None

    def to_dict(self) -> Dict:
        result = {
            "path": self.path,
            "symbol": self.symbol,
            "kind": self.kind.value,
            "signature": self.signature,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }
        if self.rank is not None:
            result["rank"] = self.rank
        if self.parent:
            result["parent"] = self.parent
        return result

    def token_estimate(self) -> int:
        """Estimate token count for this entry."""
        text = f"{self.path}:{self.symbol}:{self.signature}"
        return max(1, int(len(text) * TOKENS_PER_CHAR))


@dataclass
class DependencyEdge:
    """
    An edge in the dependency graph.

    Attributes:
        source: Source file path
        target: Target file/module path
        edge_type: Type of dependency (import, call, etc.)
    """
    source: str
    target: str
    edge_type: str = "import"

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
        }


@dataclass
class RepoMapConfig:
    """Configuration for repository map generation."""
    damping_factor: float = DEFAULT_DAMPING_FACTOR
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    token_budget: int = DEFAULT_TOKEN_BUDGET
    convergence_threshold: float = DEFAULT_CONVERGENCE_THRESHOLD
    include_variables: bool = False
    supported_extensions: List[str] = field(default_factory=lambda: [".py"])


@dataclass
class RepoMapResult:
    """
    Complete repository map result.

    Attributes:
        entries: List of symbol entries (ordered by rank)
        total_symbols: Total symbols extracted
        included_symbols: Symbols included within budget
        token_count: Estimated token count
        edges: Dependency edges
    """
    entries: List[SymbolEntry]
    total_symbols: int
    included_symbols: int
    token_count: int
    edges: List[DependencyEdge] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_symbols": self.total_symbols,
            "included_symbols": self.included_symbols,
            "token_count": self.token_count,
            "edges": [e.to_dict() for e in self.edges],
        }


def _build_signature(node: ast.AST) -> str:
    """Build a signature string from an AST node."""
    if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
        # Build function signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except Exception:
                    pass
            args.append(arg_str)

        # Add *args
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")

        # Add **kwargs
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        args_str = ", ".join(args)

        # Return type
        returns = ""
        if node.returns:
            try:
                returns = f" -> {ast.unparse(node.returns)}"
            except Exception:
                pass

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({args_str}){returns}"

    elif isinstance(node, ast.ClassDef):
        # Build class signature with bases
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                pass

        if bases:
            return f"class {node.name}({', '.join(bases)})"
        return f"class {node.name}"

    return ""


def extract_symbols_from_file(file_path: str) -> List[SymbolEntry]:
    """
    Extract symbols from a Python file using AST.

    Args:
        file_path: Path to Python file

    Returns:
        List of SymbolEntry for each extracted symbol
    """
    # Only process Python files
    if not file_path.endswith('.py'):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    symbols = []
    rel_path = file_path  # Will be made relative by caller

    for node in ast.walk(tree):
        # Top-level functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if it's a method (inside a class)
            is_method = any(
                isinstance(child, ast.ClassDef) and node in ast.walk(child)
                for child in ast.iter_child_nodes(tree)
                if isinstance(child, ast.ClassDef)
            )

            # Skip if it's a method (we'll handle those when processing classes)
            if not _is_nested_function(tree, node):
                symbols.append(SymbolEntry(
                    path=rel_path,
                    symbol=node.name,
                    kind=SymbolKind.FUNCTION,
                    signature=_build_signature(node),
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                ))

        # Classes
        elif isinstance(node, ast.ClassDef):
            symbols.append(SymbolEntry(
                path=rel_path,
                symbol=node.name,
                kind=SymbolKind.CLASS,
                signature=_build_signature(node),
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
            ))

            # Methods inside the class
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(SymbolEntry(
                        path=rel_path,
                        symbol=item.name,
                        kind=SymbolKind.METHOD,
                        signature=_build_signature(item),
                        start_line=item.lineno,
                        end_line=item.end_lineno or item.lineno,
                        parent=node.name,
                    ))

        # Module-level variables (assignments)
        elif isinstance(node, ast.Assign):
            # Only top-level assignments
            if _is_top_level(tree, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.append(SymbolEntry(
                            path=rel_path,
                            symbol=target.id,
                            kind=SymbolKind.VARIABLE,
                            signature=f"{target.id} = ...",
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                        ))

    return symbols


def _is_nested_function(tree: ast.Module, func_node: ast.AST) -> bool:
    """Check if a function is nested inside a class."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if item is func_node:
                    return True
    return False


def _is_top_level(tree: ast.Module, node: ast.AST) -> bool:
    """Check if a node is at module level."""
    return node in tree.body


def extract_imports(file_path: str) -> List[str]:
    """
    Extract import statements from a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        List of imported module names
    """
    if not file_path.endswith('.py'):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except (IOError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
            elif node.level > 0:
                # Relative import
                imports.append("." * node.level)

    return imports


def build_dependency_graph(root_dir: str) -> List[DependencyEdge]:
    """
    Build dependency graph from import relationships.

    Args:
        root_dir: Root directory to scan

    Returns:
        List of DependencyEdge representing imports
    """
    edges = []
    root_path = Path(root_dir)

    # Map module names to file paths
    module_to_file: Dict[str, str] = {}

    # First pass: build module map
    for py_file in root_path.rglob("*.py"):
        rel_path = str(py_file.relative_to(root_path))
        # Convert path to module name (e.g., src/utils/helper.py -> src.utils.helper)
        module_name = rel_path[:-3].replace(os.sep, ".")
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        module_to_file[module_name] = rel_path
        # Also map the file stem for simple imports
        module_to_file[py_file.stem] = rel_path

    # Second pass: extract imports and create edges
    for py_file in root_path.rglob("*.py"):
        rel_path = str(py_file.relative_to(root_path))
        imports = extract_imports(str(py_file))

        for imp in imports:
            # Check if this import refers to a local file
            target = module_to_file.get(imp)
            if target and target != rel_path:
                edges.append(DependencyEdge(
                    source=rel_path,
                    target=target,
                    edge_type="import",
                ))

    return edges


def compute_pagerank(
    nodes: List[str],
    edges: List[DependencyEdge],
    damping: float = DEFAULT_DAMPING_FACTOR,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    convergence: float = DEFAULT_CONVERGENCE_THRESHOLD,
) -> Dict[str, float]:
    """
    Compute PageRank scores for nodes.

    Args:
        nodes: List of node identifiers
        edges: List of dependency edges
        damping: Damping factor (default 0.85)
        max_iterations: Maximum iterations
        convergence: Convergence threshold

    Returns:
        Dictionary mapping node to PageRank score
    """
    if not nodes:
        return {}

    n = len(nodes)
    if n == 1:
        return {nodes[0]: 1.0}

    # Initialize ranks
    ranks = {node: 1.0 / n for node in nodes}

    # Build adjacency: who links TO each node (incoming edges)
    incoming: Dict[str, List[str]] = {node: [] for node in nodes}
    outgoing_count: Dict[str, int] = {node: 0 for node in nodes}

    for edge in edges:
        if edge.source in nodes and edge.target in nodes:
            incoming[edge.target].append(edge.source)
            outgoing_count[edge.source] += 1

    # Iterative PageRank
    for _ in range(max_iterations):
        new_ranks = {}
        diff = 0.0

        for node in nodes:
            # Sum of contributions from incoming nodes
            rank_sum = 0.0
            for source in incoming[node]:
                if outgoing_count[source] > 0:
                    rank_sum += ranks[source] / outgoing_count[source]

            # Apply damping factor
            new_rank = (1 - damping) / n + damping * rank_sum
            new_ranks[node] = new_rank
            diff += abs(new_rank - ranks[node])

        ranks = new_ranks

        # Check convergence
        if diff < convergence:
            break

    # Normalize to [0, 1]
    max_rank = max(ranks.values()) if ranks else 1.0
    if max_rank > 0:
        ranks = {k: v / max_rank for k, v in ranks.items()}

    return ranks


def generate_repo_map(
    root_dir: str,
    config: Optional[RepoMapConfig] = None,
) -> RepoMapResult:
    """
    Generate a complete repository map.

    Args:
        root_dir: Root directory to analyze
        config: Optional configuration

    Returns:
        RepoMapResult with ranked symbol entries
    """
    if config is None:
        config = RepoMapConfig()

    root_path = Path(root_dir)
    all_symbols: List[SymbolEntry] = []

    # Collect all symbols
    for ext in config.supported_extensions:
        pattern = f"*{ext}"
        for file_path in root_path.rglob(pattern):
            rel_path = str(file_path.relative_to(root_path))
            symbols = extract_symbols_from_file(str(file_path))

            # Update paths to be relative
            for sym in symbols:
                sym.path = rel_path

                # Filter variables if not included
                if sym.kind == SymbolKind.VARIABLE and not config.include_variables:
                    continue

                all_symbols.append(sym)

    # Build dependency graph
    edges = build_dependency_graph(root_dir)

    # Get unique file paths
    file_paths = sorted(set(sym.path for sym in all_symbols))

    # Compute PageRank for files
    file_ranks = compute_pagerank(
        file_paths,
        edges,
        damping=config.damping_factor,
        max_iterations=config.max_iterations,
        convergence=config.convergence_threshold,
    )

    # Assign ranks to symbols based on their file's rank
    for sym in all_symbols:
        sym.rank = file_ranks.get(sym.path, 1.0 / len(file_paths) if file_paths else 0.0)

    # Sort by rank (descending), then by path (ascending), then by symbol (ascending)
    all_symbols.sort(key=lambda s: (-s.rank, s.path, s.symbol))

    # Apply token budget
    included_symbols = []
    total_tokens = 0

    for sym in all_symbols:
        token_cost = sym.token_estimate()
        if total_tokens + token_cost <= config.token_budget:
            included_symbols.append(sym)
            total_tokens += token_cost
        else:
            # Budget exceeded
            break

    return RepoMapResult(
        entries=included_symbols,
        total_symbols=len(all_symbols),
        included_symbols=len(included_symbols),
        token_count=total_tokens,
        edges=edges,
    )
