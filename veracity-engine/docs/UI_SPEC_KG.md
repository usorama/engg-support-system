# Knowledge Graph UI Specification

## Overview
A visual relationship explorer for the code Knowledge Graph. The UI should allow users to interactively "walk" the codebase, understanding dependencies, call hierarchies, and ownership without reading raw code.

## Core Features

### 1. Project Management
- **Project Selector**: A dropdown to switch between multiple indexed codebases (tenanted via the `:Project` label).
- **Indexing Status**: Visual indicator of whether the current project is in-sync or requires an update.

### 2. Graph Visualization (The Canvas)
- **Interactive Nodes**: Nodes represent `File`, `Class`, and `Function` entities.
- **Relationship Edges**:
    - `DEFINES`: Parent-child relationship (e.g., File -> Class).
    - `CALLS`: Function-to-function invocation.
    - `DEPENDS_ON`: Imports and module dependencies.
- **Node "Walking"**: Clicking a node selects it and highlights its immediate neighbors. Double-clicking "expands" the node to show its connections.
- **Drill-Down**: A side-panel that displays the **docstring**, **filepath**, and **line number** of the selected entity.

### 3. Search & Filter
- **Semantic Search Bar**: Search for code components using natural language (powered by the existing vector index).
- **Filter by Type**: Toggle visibility of Files vs. Functions vs. Classes.
- **Complexity Heatmaps**: (Optional) Color nodes based on how many incoming/outgoing edges they have (identifying "God Objects" or critical functions).

## Technical Implementation Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **NeoDash** | Instant deployment, native Neo4j integration, low-code. | Customization is limited, UI feels "utility-like". |
| **Custom React + Cytoscape.js** | Full control over UX, premium look, tailored drill-down panels. | Higher development effort. |
| **Plotly Dash / Cytoscape** | Python-based, easy to integrate with existing parser logic. | Harder to scale into a "premium" standalone app. |

## Next Steps
1. Finalize the Multitenancy schema (Track B) so the UI has a `project` property to filter by.
2. Prototype a basic NeoDash dashboard to validate the graph structure.
3. If NeoDash is insufficient, proceed with a custom React/Vite implementation.
