"""
Veracity Engine Core Package

This package contains the core components of the Veracity Engine:
- build_graph: Knowledge graph construction and indexing
- ask_codebase: Query engine with veracity checking
- generate_codebase_map: Markdown codebase map generation
- embeddings: Shared embedding utilities (consolidated from build_graph and ask_codebase)

Usage:
    from core.build_graph import CodeGraphBuilder
    from core.ask_codebase import GroundTruthContextSystem, query_graph
    from core.generate_codebase_map import generate_structure_markdown
    from core.embeddings import get_embedding, get_document_embedding, get_query_embedding
"""

# Version info
__version__ = "0.1.0"
__author__ = "Veracity Engine Team"

# Lazy imports to avoid circular dependencies
# Explicit imports should be done in calling code:
#   from core.build_graph import CodeGraphBuilder
#   from core.ask_codebase import query_graph
#   from core.embeddings import get_embedding

__all__ = [
    "build_graph",
    "ask_codebase",
    "generate_codebase_map",
    "embeddings",
]
