# Prompt for Next Session: Knowledge Graph UI & Multitenancy

**Context:**
We have successfully implemented a high-performance, Neo4j-based Knowledge Graph for Veracity Engine (V3). It uses AST-based parsing and SHA1 hashing for incremental sync. The entire capability is consolidated in the repo root (`core/`, `infra/`, `docs/`, `ui/`).

**Objective:**
Evolve this system into a standalone, project-agnostic service with a visual relationship exploration UI.

**Action Items:**
1. **Research & Design a Visualization UI**:
   - Evaluate [NeoDash](https://neo4j.com/labs/neodash/) dashboards for relationship mapping.
   - Alternatively, design a lightweight React/D3.js or Plotly Cytoscape interface for interactive node discovery.
   - Goal: Allow the user to "walk" the code dependencies visually (e.g., clicking `self_healing_orchestrator` shows its `CALLS` and `DEFINES` links).

2. **Project Agnosticism & Multitenancy**:
   - Refactor `build_graph.py` to accept a `root_dir` and a `project_name` as arguments.
   - Update the Neo4j schema to include a `:Project` label or a `project` property on all nodes.
   - Ensure `ask_codebase.py` can filter queries by project.
   - Plan storage for multiple hash caches (e.g., `.graph_hashes_{project}.json`).

3. **Standalone Extraction**:
   - Prepare a separate `docker-compose.yml` that can be run in any project directory.
   - Define a clear API or CLI interface for external CI/CD integration.

**Retrieved Knowledge for Context:**
All relevant files are located in the repo root.
- Core Logic: `core/`
- Infrastructure: `infra/`
- Documentation: `docs/`

**Start by researching existing Neo4j visualization patterns and outlining the multi-project schema change.**
