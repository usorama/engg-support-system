# Repository Guidelines

## Project Purpose and Outcomes
- Purpose: Build a deterministic, evidence-based context engineering system (Veracity Engine) that indexes codebases into a knowledge graph for auditable retrieval.
- Objectives: index all files with provenance, create veracity checks (staleness/orphans/contradictions), and return evidence-only query outputs.
- Outcomes: reproducible KG builds, deterministic embeddings/chunking, and query results that cite exact sources.

## Project Structure & Module Organization
- `core/`: Python engines for building and querying the knowledge graph (e.g., `build_graph.py`, `ask_codebase.py`).
- `infra/`: Docker Compose stack for Neo4j persistence (`infra/docker-compose.yml`).
- `ui/`: React + Vite dashboard for graph visualization (`ui/src/`).
- `scripts/`: Automation and bootstrap tools such as `scripts/install.sh`.
- `templates/`: Agent configuration templates (e.g., `templates/context-kg.mdc`).
- `docs/`: Product, architecture, and UI documentation (`docs/ARCHITECTURE.md`).

## Build, Test, and Development Commands
- `bash scripts/install.sh`: Installs GTCS into a target project, boots Neo4j, creates `.veracity_venv`, and indexes the project.
- `python3 core/build_graph.py --project-name NAME --root-dir PATH`: Build or refresh the knowledge graph.
- `python3 core/ask_codebase.py --project-name NAME "question"`: Query the graph for architectural context.
- `cd ui && npm install`: Install UI dependencies.
- `cd ui && npm run dev`: Run the Vite dev server for the dashboard.
- `cd ui && npm run build`: Build the UI for production.
- `cd ui && npm run lint`: Lint the UI codebase with ESLint.

## Coding Style & Naming Conventions
- Python follows standard 4-space indentation; keep modules small and task-focused.
- React uses component files in `ui/src/` with JSX; prefer PascalCase for components.
- Keep script names verb-first and descriptive (e.g., `build_graph.py`).
- Linting: run `npm run lint` in `ui/` before UI changes.

## Testing Guidelines
- Python testing uses `pytest` (declared in `requirements.txt`).
- Add tests alongside Python modules when introducing new graph logic.
- If you add tests, run them with `pytest` from the repo root.

## Commit & Pull Request Guidelines
- No git history is available in this repository, so commit conventions are unspecified.
- Suggested commit format: `type: short summary` (e.g., `feat: add graph query cache`).
- PRs should include a clear description, linked issue (if any), and UI screenshots for dashboard changes.

## Security & Configuration Notes
- Docker and Ollama are required to run the full stack.
- The installer creates a `.veracity_venv` in the target project; avoid committing it.

## Agent Workflow
- Follow `docs/plans/IMPLEMENTATION_WORKFLOW.md` for story execution and progress updates.
