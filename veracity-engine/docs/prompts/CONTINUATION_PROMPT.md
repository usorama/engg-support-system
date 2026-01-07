# Veracity Engine - Implementation Session Handover

## 🎯 Current Objective
You are continuing the implementation of the **Veracity Engine**, a deterministic Context Engineering platform. The project has been fully reorganized into a sequential 14-story roadmap located in `docs/plans/`.

## 🛠 Project Context
- **Framework**: Python 3.9 (Core), React + Vite (UI).
- **Infrastructure**: Neo4j 5.15, NeoDash, Docker Compose.
- **AI Stack**: Ollama (local) with `llama3.2` and `nomic-embed-text`.
- **Status**: Alpha. All stories are currently `NOT_STARTED`.

## 📍 Where to Start
1.  **Read `docs/plans/MASTER_TASKS.md`** to see the current progress and story sequence.
2.  **Follow `docs/plans/IMPLEMENTATION_WORKFLOW.md`** strictly for every task.
3.  **Target the first pending story**: Usually `docs/plans/STORY-001-project-discovery-config.md`.

## 📜 Operating Rules
- **AGENTS.md**: Follow the repository-specific coding guidelines.
- **Evidence-First**: Never assume. If logic is missing or hardcoded, find it in the code and document it in the story research section.
- **Determinism**: Every change must support reproducible KG builds and auditable evidence packets.
- **Workflow**: 
    - `Research` -> Update Story Research section.
    - `Plan` -> Update Story Checklist/DoR.
    - `Implement` -> One step at a time.
    - `Verify` -> Update DoD and `MASTER_TASKS.md`.

## 🔗 Key References
- **Architecture**: `docs/ARCHITECTURE.md`
- **Product Vision**: `docs/PRD_GRAPHRAG.md`
- **Master Plan**: `docs/plans/MASTER_TASKS.md`
- **Workflow**: `docs/plans/IMPLEMENTATION_WORKFLOW.md`

---
*Ready for Story-001 implementation.*
