# Changelog - GraphRAG Service

## [V3.1] - 2025-12-29
### ✨ Multitenancy & extraction
- **Project Isolation**: Refactored `build_graph.py` to support `--project-name` and `--root-dir`.
- **Schema Update**: Introduced `:Project` labels and project-property filtering for multi-repo support.
- **Service Standard**: Standardized Docker container names (`graphrag_neo4j`) and paths.
- **Extraction Scripts**: Added `setup_service.sh` for easy deployment.
- **Documentation**: Created full PRD, Architecture diagrams, and UI Specifications.

## [V3.0] - 2025-12-27
### Added
- **Intelligent Sync**: Implemented file hashing (SHA1) to detect changes. The system now skips unchanged files, drastically reducing build time from minutes to seconds.
- **Unique UIDs**: Introduced a global UID strategy for all nodes (e.g., `path::node_name`). 
- **O(1) Neo4j Commits**: Leveraged `UNIQUE CONSTRAINT` on UIDs to make relationship commits constant time, regardless of graph size.
- **Auto-Deletion**: Logical deletion added; files removed from the disk are now automatically cleaned from the Neo4j graph.
- **NeoDash Integration**: Added infrastructure for browser-based graph visualization.

### Improved
- **Synchronous Git Automation**: Moved KG updates from background to foreground in the `pre-commit` hook for better reliability and state tracking.
- **State Persistence**: `.graph_hashes.json` is now tracked by Git, enabling seamless indexing across different environments.
- **Hybrid Search**: `ask_codebase.py` now combines Neo4j vector search with AST-based relationship queries for higher precision.

## [v2.0.0] - 2025-12-22 (Legacy)
### Added
- Initial Neo4j migration from Vector-only index.
- Basic AST parsing for Python files.

## [v1.0.0] - 2025-12-10 (Legacy)
### Added
- Original LlamaIndex-based context system using local Ollama embeddings and directory readers.
