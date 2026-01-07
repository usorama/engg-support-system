# GraphRAG Visualization UI

A modern, interactive graph explorer for the GraphRAG service. Built with React, Vite, and react-force-graph.

## Features

### Core Features
- **Project Selector**: Switch between indexed projects (tenants).
- **Interactive Graph**: Zoom, pan, and drag nodes.
- **Detail Panel**: View docstrings, neighbors, and relationships on click.
- **Visual Coding**: Color-coded nodes (pink=File, orange=Class, blue=Function).

### Audit Trail Panel

The Audit Trail panel provides a historical view of veracity reports and queries executed against the knowledge graph. Access it by clicking the "Audit Trail" button in the top navigation.

**What it displays:**
- Chronological list of the 20 most recent veracity reports for the selected project
- Confidence scores with color-coded badges:
  - **Green badge (>80%)**: High confidence/veracity
  - **Yellow badge (<=80%)**: Lower confidence, review recommended
- Timestamp for each report
- Query/question text that generated the report

**Usage:**
1. Click the "Audit Trail" button in the header to toggle the panel
2. Click on any report entry to view its full details in the Detail Panel
3. The panel slides in from the left side with smooth animation

### View Modes

Two view modes are available for exploring the graph:

#### ALL Mode (Default)
- Displays all graph nodes in the selected project
- Shows complete relationships between all node types (Files, Classes, Functions, Documents, Capabilities, Features)
- Best for understanding full codebase structure and dependencies
- Node count displayed in header: "{N} Nodes"

#### DISCOVERY Mode
- Filtered view showing only Capabilities and Documents initially
- Enables hierarchical drill-down exploration
- Click on Capability, Feature, or File nodes to expand their children
- Children are connected via HAS_FEATURE, HAS_FILE, HAS_DOCUMENT, or DEFINES relationships
- Click again on an expanded node to collapse its children
- Header displays "Click nodes to drill down" as guidance
- Ideal for top-down architectural exploration

**Toggle between modes:** Click the view mode button in the header (displays "Full Graph" or "Discovery Integration")

### Veracity Integration

Nodes display confidence scores and fault indicators from the Ground Truth Context System:

**Confidence Scores:**
- Displayed in the Detail Panel when a node has veracity data
- Shows percentage with shield icon
- Color-coded indicator:
  - **Green (>80%)**: High veracity/confidence
  - **Yellow (<=80%)**: Lower confidence, verification recommended

**Context Veracity Badge:**
- Located in the Detail Panel header area
- Shows "Context Veracity" label with percentage value
- Helps users assess trustworthiness of node information

### Dynamic Project Loading

Projects are loaded dynamically from Neo4j at application startup:

1. On load, the UI queries Neo4j for all distinct `project` labels on nodes
2. Projects populate the dropdown selector in the header
3. First available project is auto-selected if none was previously chosen
4. Selecting a different project:
   - Refreshes the graph with nodes from that project
   - Loads veracity reports specific to that project
   - Resets the view to show the new project's graph

**Project Selector Location:** Top-left corner with server icon

### Semantic Zoom

The graph visualization supports semantic zoom with different rendering modes based on zoom level and node type:

**Card-Style Nodes (Discovery Mode):**
- Capability, Feature, and Component nodes render as rectangular cards
- Cards display:
  - Node name (bold, centered)
  - Node type label below the name
  - Rounded corners with subtle border
- Active/selected cards have:
  - Highlighted background
  - Blue border
  - Brighter text

**Circle Nodes (Standard/Zoomed Out):**
- All other node types render as circles
- Size varies by importance (Capability: largest, Function: smallest)
- Color indicates node type and state (see Legend)
- Labels appear when:
  - Zoom level > 2x (globalScale > 2)
  - Node is actively selected

**Zoom Behavior:**
- Labels scale inversely with zoom for readability
- Clicking a node centers and zooms to 4x magnification
- Graph auto-fits to viewport when simulation stabilizes

### Fault Detection

Nodes with issues display visual indicators and alerts:

**Fault Triggers:**
- **STALE_DOC**: Documents older than 90 days (based on `last_modified` timestamp)
- **ORPHANED_NODE**: Nodes with fewer than 2 connections (detected via veracity reports)
- Nodes referenced in any fault report's `faults` array

**Visual Indicators:**

1. **Red Glow/Halo:** Faulty nodes display a red glow effect (shadowBlur) around their circle
2. **Red Node Color:** Faulty nodes are colored red (#f87171) regardless of their type
3. **Alert Icon:** Stale documents show an AlertTriangle icon in the Detail Panel header
4. **Faults Panel:** When a node has faults, the Detail Panel displays a dedicated red-bordered section:
   - "FAULTS DETECTED" header with warning icon
   - Bulleted list of all detected fault descriptions

**Document Freshness Colors:**
- **Green (#4ade80)**: Fresh (modified within 7 days)
- **Yellow (#fbbf24)**: Aging (modified 7-30 days ago)
- **Red (#ef4444)**: Stale (modified >30 days ago)

### Node Color Legend

The bottom-left legend displays the color coding:

| Node Type | Color |
|-----------|-------|
| Capability | White |
| Feature | Purple |
| Document (Fresh) | Green |
| Document (Stale) | Red |
| File | Pink |
| Class | Orange |
| Function | Blue |
| VeracityReport | Blue |
| Infrastructure | Slate gray |
| Config | Fuchsia |

## Configuration

### Environment Variables

Configure Neo4j connection via environment variables or `.env` file:

```bash
VITE_NEO4J_URI=bolt://localhost:7687    # Neo4j Bolt protocol URI
VITE_NEO4J_USER=neo4j                   # Neo4j username
VITE_NEO4J_PASSWORD=password            # Neo4j password
```

Defaults are used if not specified.

## Local Development
```bash
cd ui
npm install
npm run dev
```

## Docker
The UI is included in the main `docker-compose.yml`.
```bash
docker compose up -d
```
Access at `http://localhost:5173`.

## Architecture

### Components

- **App.jsx**: Main application with graph visualization, state management, and Neo4j integration
- **AuditTrail**: Left-side panel component for veracity report history
- **DetailPanel**: Right-side panel for selected node details and fault information
- **ForceGraph2D**: Lazy-loaded force-directed graph visualization (react-force-graph-2d)

### Dependencies

- **react-force-graph-2d**: Force-directed graph visualization
- **neo4j-driver**: Direct Neo4j database connectivity (v6.x)
- **framer-motion**: Smooth animations for panel transitions
- **lucide-react**: Icon library for UI elements

### Driver Version Compatibility Note

The UI uses `neo4j-driver` 6.x (JavaScript) while the backend uses Python `neo4j>=5.15.0`. This is intentional and fully supported:

- **JavaScript driver 6.x**: Compatible with Neo4j server 4.4, 5.x, and 2025.x
- **Python driver 5.x**: Compatible with Neo4j server 4.4 and 5.x
- Both drivers connect to the same Neo4j 5.15.0 server instance via Bolt protocol

The driver major versions do not need to match each other - they only need to be compatible with the target Neo4j server version. Neo4j officially supports this mixed-version deployment pattern.

References:
- [Neo4j JavaScript Driver Upgrade Guide](https://neo4j.com/docs/javascript-manual/current/upgrade/)
- [Neo4j Supported Versions](https://neo4j.com/developer/kb/neo4j-supported-versions/)
