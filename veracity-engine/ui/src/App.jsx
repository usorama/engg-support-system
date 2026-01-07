import React, { useState, useEffect, useCallback, useRef, Suspense } from 'react';
const ForceGraph2D = React.lazy(() => import('react-force-graph-2d'));
import neo4j from 'neo4j-driver';
import { Search, Server, GitBranch, Code, FileText, Box, Layers, ShieldCheck, AlertTriangle, History } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- Configuration ---
const NEO4J_URI = import.meta.env.VITE_NEO4J_URI || "bolt://localhost:7687";
const NEO4J_USER = import.meta.env.VITE_NEO4J_USER || "neo4j";
const NEO4J_PASSWORD = import.meta.env.VITE_NEO4J_PASSWORD || "password";

const DRIVER = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD));

// --- Components ---
const AuditTrail = ({ reports, onSelect }) => {
  return (
    <motion.div
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="glass-panel absolute left-4 top-20 bottom-4 w-64 p-4 overflow-y-auto z-20 flex flex-col"
    >
      <div className="flex items-center gap-2 mb-4 text-gray-400">
        <History size={16} />
        <h3 className="text-sm font-bold uppercase tracking-wider">Audit Trail</h3>
      </div>
      <div className="space-y-3">
        {reports.length === 0 && <div className="text-xs text-gray-600">No reports logged yet.</div>}
        {reports.map((r, i) => (
          <button
            key={i}
            onClick={() => onSelect(r)}
            className="w-full text-left p-2 rounded bg-gray-900/50 border border-gray-800 hover:border-blue-500 transition-colors"
          >
            <div className="flex justify-between items-center mb-1">
              <span className={`text-[10px] px-1 rounded ${r.confidence_score > 80 ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'}`}>
                {r.confidence_score}%
              </span>
              <span className="text-[10px] text-gray-500">
                {r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : 'N/A'}
              </span>
            </div>
            <div className="text-xs text-gray-300 truncate">{r.question}</div>
          </button>
        ))}
      </div>
    </motion.div>
  );
};

// --- Visual Config ---
const NODE_REL_SIZE = 6;
const CARD_WIDTH = 120;
const CARD_HEIGHT = 60;
const FONT_SIZE = 12;

const DetailPanel = ({ node, onClose }) => {
  if (!node) return null;
  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      className="glass-panel absolute right-4 top-4 bottom-4 w-96 p-6 overflow-y-auto z-20 flex flex-col"
      style={{ maxHeight: 'calc(100vh - 32px)' }}
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-gray-500 mb-1">{node.type}</div>
          <h2 className="text-xl font-bold text-blue-400 break-all">{node.name}</h2>
        </div>
        <div className="flex gap-2">
          {node.type === 'Document' && node.freshnessColor === '#ef4444' && (
            <AlertTriangle size={18} className="text-red-500" title="Stale Document" />
          )}
          <button onClick={onClose} className="text-gray-400 hover:text-white pb-1">×</button>
        </div>
      </div>

      {node.confidence_score !== undefined && (
        <div className="mb-4 flex items-center gap-2 bg-blue-900/20 p-3 rounded-lg border border-blue-800/50">
          <ShieldCheck size={20} className={node.confidence_score > 80 ? "text-green-400" : "text-yellow-400"} />
          <div>
            <div className="text-xs text-gray-400">Context Veracity</div>
            <div className="text-lg font-bold">{node.confidence_score}%</div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <span className="text-xs text-gray-500">Qualified Name</span>
          <div className="text-sm font-mono bg-gray-900/50 p-2 rounded mt-1 break-all">
            {node.qualified_name || node.path}
          </div>
        </div>

        {node.docstring && (
          <div>
            <span className="text-xs text-gray-500">Docstring</span>
            <div className="text-sm text-gray-300 mt-1 whitespace-pre-wrap font-mono p-2 bg-gray-900/30 rounded border border-gray-800">
              {node.docstring.slice(0, 300)}{node.docstring.length > 300 ? '...' : ''}
            </div>
          </div>
        )}

        {/* Component/Asset info if available */}
        {node.category && (
          <div className="mt-2 text-xs font-mono text-pink-400 border border-pink-900/50 p-1 rounded inline-block">
            {node.category}
          </div>
        )}

        {node.faults && node.faults.length > 0 && (
          <div className="bg-red-900/20 p-3 rounded-lg border border-red-800/50 mb-4">
            <div className="text-xs text-red-400 font-bold mb-1 flex items-center gap-1">
              <AlertTriangle size={12} /> FAULTS DETECTED
            </div>
            <ul className="text-xs text-red-300 list-disc list-inside space-y-1">
              {node.faults.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}

        {node.question && (
          <div className="mb-4">
            <span className="text-xs text-gray-500">Query Context</span>
            <div className="text-sm italic text-gray-400 mt-1">"{node.question}"</div>
          </div>
        )}

        {node.neighbors && node.neighbors.length > 0 && (
          <div>
            <span className="text-xs text-gray-500">Connections ({node.neighbors.length})</span>
            <ul className="mt-2 space-y-2">
              {node.neighbors.slice(0, 10).map((n, i) => (
                <li key={i} className="text-xs flex items-center gap-2 text-gray-400">
                  {n.linkType === 'DEFINES' ? <Box size={10} color="orange" /> :
                    n.linkType === 'CALLS' ? <GitBranch size={10} color="cyan" /> :
                      <Layers size={10} color="gray" />}
                  <span className={n.direction === 'out' ? "text-blue-200" : "text-purple-200"}>
                    {n.direction === 'out' ? '→' : '←'} {n.name}
                  </span>
                </li>
              ))}
              {node.neighbors.length > 10 && <li className="text-xs text-gray-600">...and {node.neighbors.length - 10} more</li>}
            </ul>
          </div>
        )}
      </div>
    </motion.div>
  );
};

// --- Main Application ---
function App() {
  const [projectId, setProjectId] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [projects, setProjects] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [reports, setReports] = useState([]);
  const [showAudit, setShowAudit] = useState(false);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState("ALL");
  const fgRef = useRef();

  // 1. Fetch Projects
  useEffect(() => {
    const fetchProjects = async () => {
      const session = DRIVER.session();
      try {
        const result = await session.run("MATCH (n:Node) RETURN distinct n.project as project");
        const projs = result.records.map(r => r.get('project')).filter(Boolean);
        if (projs.length > 0) setProjects(projs);

        // Auto-select first project if none selected
        if (!projectId && projs.length > 0) {
          setProjectId(projs[0]);
        }
      } catch (e) {
        console.error("Failed to fetch initial data", e);
      } finally {
        session.close();
      }
    };
    fetchProjects();
  }, []);

  // 2. Fetch Graph Data
  const fetchGraph = useCallback(async () => {
    setLoading(true);
    const session = DRIVER.session();
    try {
      let nodeQuery = "MATCH (n:Node) WHERE n.project = $project RETURN n";
      let linkQuery = "MATCH (n:Node)-[r]->(m:Node) WHERE n.project = $project AND m.project = $project RETURN n.uid, r, m.uid";

      if (viewMode === 'DISCOVERY') {
        // Only Capabilities and Documents initially
        nodeQuery = "MATCH (n:Node) WHERE n.project = $project AND (n:Capability OR n:Document) RETURN n";
        linkQuery = "MATCH (n:Node)-[r]->(m:Node) WHERE n.project = $project AND m.project = $project AND (n:Capability OR n:Document) AND (m:Capability OR m:Document) RETURN n.uid, r, m.uid";
      }

      // Fetch Veracity Reports for this project
      const reportResult = await session.run(
        "MATCH (r:VeracityReport) WHERE r.project = $project RETURN r ORDER BY r.timestamp DESC LIMIT 20",
        { project: projectId }
      );
      const reportsData = reportResult.records.map(rec => ({
        ...rec.get('r').properties,
        type: 'VeracityReport',
        id: rec.get('r').properties.query_id,
        name: `Report: ${rec.get('r').properties.query_id.slice(0, 8)}`
      }));
      setReports(reportsData);

      const nodeResult = await session.run(nodeQuery, { project: projectId });
      const nodes = nodeResult.records.map(r => {
        const props = r.get('n').properties;
        const labels = r.get('n').labels;
        const type = labels.includes('Capability') ? 'Capability' :
          labels.includes('Feature') ? 'Feature' :
            labels.includes('Document') ? 'Document' :
              labels.includes('File') ? 'File' :
                labels.includes('Class') ? 'Class' :
                  labels.includes('Function') ? 'Function' : 'Code';

        // Freshness Calculation for Docs
        let freshnessColor = null;
        if (type === 'Document' && props.last_modified) {
          const ageDays = (Date.now() / 1000 - props.last_modified) / 86400;
          if (ageDays < 7) freshnessColor = '#4ade80'; // Green (Fresh)
          else if (ageDays < 30) freshnessColor = '#fbbf24'; // Yellow
          else freshnessColor = '#ef4444'; // Red (Stale)
        }

        // Check if this node is flagged in any of the top reports
        const faults = reportsData.some(rep => rep.faults && rep.faults.some(f => f.includes(props.name)));

        return {
          id: props.uid,
          type,
          val: type === 'Capability' ? 40 : type === 'Feature' ? 30 : type === 'File' ? 20 : 10,
          freshnessColor,
          isFaulty: faults,
          ...props
        };
      });

      const linkResult = await session.run(linkQuery, { project: projectId });
      const links = linkResult.records.map(r => ({
        source: r.get('n.uid'),
        target: r.get('m.uid'),
        type: r.get('r') ? r.get('r').type : 'CONNECTED_TO'
      }));

      const allNodes = [...nodes, ...reportsData.map(r => ({ ...r, val: 15 }))];
      setGraphData({ nodes: allNodes, links });
      // Reset zoom only on fresh load, not incremental
      // setTimeout(() => { if (fgRef.current) fgRef.current.zoomToFit(400); }, 500); 

    } catch (e) {
      console.error("Graph fetch error", e);
    } finally {
      session.close();
      setLoading(false);
    }
  }, [projectId, viewMode]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const toggleChildren = async (parentNode) => {
    // 1. Check if children are already loaded (Collapse logic)
    const existingChildLinks = graphData.links.filter(l => l.source.id === parentNode.id && l.type === 'HAS_CHILD');

    if (existingChildLinks.length > 0) {
      // Collapse: Remove these children and links
      const childIdsToRemove = new Set(existingChildLinks.map(l => l.target.id));

      // Recursive removal could be complex, for now strictly one level toggle for simplicity
      // But if we want to be correct, we should remove sub-trees. 
      // Let's do a simple filter for now which removes immediate children.

      setGraphData(prev => ({
        nodes: prev.nodes.filter(n => !childIdsToRemove.has(n.id)),
        links: prev.links.filter(l => !childIdsToRemove.has(l.target.id) && l.source.id !== parentNode.id)
      }));
      return;
    }

    // 2. Expand logic
    const session = DRIVER.session();
    try {
      // Find children connected by HAS_FEATURE, HAS_FILE, HAS_DOCUMENT, or DEFINES
      const result = await session.run(
        `MATCH (p:Node {uid: $uid})-[:HAS_FEATURE|HAS_FILE|HAS_DOCUMENT|DEFINES]->(c:Node) 
               RETURN c, labels(c) as labels`,
        { uid: parentNode.id }
      );

      const newNodes = [];
      const newLinks = [];

      result.records.forEach(r => {
        const props = r.get('c').properties;
        const labels = r.get('labels');
        const type = labels.includes('Feature') ? 'Feature' :
          labels.includes('File') ? 'File' :
            labels.includes('Document') ? 'Document' :
              labels.includes('Class') ? 'Class' : 'Function';

        if (!graphData.nodes.find(n => n.id === props.uid)) {
          let freshnessColor = null;
          if (type === 'Document' && props.last_modified) {
            const ageDays = (Date.now() / 1000 - props.last_modified) / 86400;
            if (ageDays < 7) freshnessColor = '#4ade80';
            else if (ageDays < 30) freshnessColor = '#fbbf24';
            else freshnessColor = '#ef4444';
          }

          newNodes.push({
            id: props.uid,
            type,
            val: type === 'Feature' ? 30 : type === 'File' ? 20 : 10,
            freshnessColor,
            ...props
          });
          newLinks.push({ source: parentNode.id, target: props.uid, type: 'HAS_CHILD' });
        }
      });

      if (newNodes.length > 0) {
        setGraphData(prev => ({
          nodes: [...prev.nodes, ...newNodes],
          links: [...prev.links, ...newLinks]
        }));
      }
    } finally {
      session.close();
    }
  };

  const handleNodeClick = useCallback(node => {
    if (viewMode === 'DISCOVERY' && ['Capability', 'Feature', 'File'].includes(node.type)) {
      toggleChildren(node);
    }
    setSelectedNode(node);
    fgRef.current.centerAt(node.x, node.y, 1000);
    fgRef.current.zoom(4, 2000);
  }, [graphData, viewMode]);

  // 3. Configure Physics Engine
  // 3. Configure Physics Engine (Explosion Logic)
  useEffect(() => {
    if (fgRef.current) {
      // Re-heat simulation to apply new forces
      const charge = fgRef.current.d3Force('charge');
      if (charge) {
        charge.strength(node => {
          if (selectedNode && node.id === selectedNode.id) return -800;
          return -300;
        }).distanceMax(600);
      }

      const collide = fgRef.current.d3Force('collide');
      if (collide) {
        collide.radius(node => {
          if (['Capability', 'Feature', 'Component'].includes(node.type)) return 60;
          return 10;
        });
      }

      const link = fgRef.current.d3Force('link');
      if (link) {
        link.distance(l => l.type === 'HAS_CHILD' ? 100 : 50);
      }

      fgRef.current.d3ReheatSimulation();
    }
  }, [graphData, selectedNode]);

  return (
    <div className="relative w-full h-full bg-[#0d1117]">
      {/* Header / Nav */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-4">
        <div className="glass-panel px-4 py-2 flex items-center gap-2">
          <Server size={18} className="text-blue-400" />
          <select
            value={projectId}
            onChange={e => setProjectId(e.target.value)}
            className="bg-transparent border-none text-white font-bold outline-none cursor-pointer"
          >
            {projects.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        <div className="glass-panel px-4 py-2 flex items-center gap-2">
          <button
            onClick={() => setViewMode(m => m === 'ALL' ? 'DISCOVERY' : 'ALL')}
            className={`text-xs px-2 py-1 rounded ${viewMode === 'DISCOVERY' ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-400'}`}
          >
            {viewMode === 'ALL' ? 'Full Graph' : 'Discovery Integration'}
          </button>
          <button
            onClick={() => setShowAudit(!showAudit)}
            className={`text-xs px-2 py-1 rounded flex items-center gap-1 ${showAudit ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'}`}
          >
            <History size={12} /> Audit Trail
          </button>
        </div>

        <div className="glass-panel px-4 py-2 text-sm text-gray-400">
          {viewMode === 'DISCOVERY' ? 'Click nodes to drill down' : `${graphData.nodes.length} Nodes`}
        </div>
      </div>

      {/* Detail Panel */}
      <AnimatePresence>
        {selectedNode && (
          <DetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
        {showAudit && (
          <AuditTrail reports={reports} onSelect={(r) => setSelectedNode(r)} />
        )}
      </AnimatePresence>

      {/* Graph Area */}
      {loading ? (
        <div className="flex items-center justify-center w-full h-full text-blue-400 animate-pulse">
          Loading Graph...
        </div>
      ) : (
        <Suspense fallback={<div className="flex items-center justify-center w-full h-full text-blue-400">Loading Visualization...</div>}>
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            backgroundColor="#0d1117"
            // Semantic Zoom Rendering
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.name;
              const isActive = selectedNode && selectedNode.id === node.id;

              if (viewMode === 'DISCOVERY' && ['Capability', 'Feature', 'Component'].includes(node.type)) {
                // Render as Card
                const width = CARD_WIDTH;
                const height = CARD_HEIGHT;
                const x = node.x - width / 2;
                const y = node.y - height / 2;
                const radius = 6;

                // Card Background
                ctx.beginPath();
                ctx.fillStyle = isActive ? 'rgba(50, 60, 80, 0.9)' : 'rgba(20, 25, 35, 0.8)';
                ctx.strokeStyle = isActive ? '#60a5fa' : '#30363d';
                ctx.lineWidth = isActive ? 2 : 1;
                ctx.roundRect(x, y, width, height, radius);
                ctx.fill();
                ctx.stroke();

                // Header
                ctx.fillStyle = isActive ? '#93c5fd' : '#e2e8f0';
                ctx.font = `bold ${FONT_SIZE}px Sans-Serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(label, node.x, node.y - 5);

                // Type Label
                ctx.fillStyle = '#94a3b8';
                ctx.font = `${FONT_SIZE - 2}px Sans-Serif`;
                ctx.fillText(node.type, node.x, node.y + 10);

              } else {
                // Render as Circle (Standard)
                const r = isActive ? 8 : 5;
                ctx.beginPath();
                ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);

                // Color Logic
                let color = '#9ca3af';
                if (node.isFaulty) color = '#f87171'; // Faulty highlight
                else if (node.type === 'VeracityReport') color = '#3b82f6';
                else if (node.freshnessColor) color = node.freshnessColor;
                else if (node.type === 'Document') color = '#22c55e';
                else if (node.type === 'File') color = '#ec4899';
                else if (node.type === 'Class') color = '#f59e0b';
                else if (node.type === 'Function') color = '#3b82f6';
                else if (node.category === 'Infrastructure') color = '#64748b';
                else if (node.category === 'Config') color = '#d946ef';

                ctx.fillStyle = color;
                ctx.fill();

                // Glow/Halo for Faulty
                if (node.isFaulty) {
                  ctx.shadowBlur = 15;
                  ctx.shadowColor = '#ef4444';
                }

                // Ring for active
                if (isActive) {
                  ctx.strokeStyle = '#fff';
                  ctx.lineWidth = 1.5;
                  ctx.stroke();
                }
                ctx.shadowBlur = 0; // Reset

                // Label (only if high zoom or active)
                if (globalScale > 2 || isActive) {
                  ctx.fillStyle = '#fff';
                  ctx.font = `${FONT_SIZE / globalScale * 3}px Sans-Serif`; // Scaled text
                  ctx.fillText(label, node.x, node.y + r + 4);
                }
              }
            }}
            nodeLabel={null} // Disable default label

            linkColor={() => '#30363d'}
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={0.005}
            linkDirectionalParticleWidth={2}
            onNodeClick={handleNodeClick}

            // Physics Tuning
            d3VelocityDecay={0.1}
            d3AlphaDecay={0.01}
            cooldownTicks={100}
            onEngineStop={() => fgRef.current.zoomToFit(400)}
          />
        </Suspense>
      )}

      {/* Legend / Footer */}
      <div className="absolute bottom-4 left-4 glass-panel p-3 text-xs flex gap-4 text-gray-400 z-10 flex-wrap max-w-2xl">
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-white"></div> Capability</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-purple-500"></div> Feature</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-green-500"></div> Doc (Fresh)</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-red-500"></div> Doc (Stale)</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-pink-500"></div> File</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-orange-500"></div> Class</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div> Function</div>
      </div>
    </div>
  );
}

export default App;
