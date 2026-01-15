import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import neo4j from 'neo4j-driver';
import {
  Plus,
  RefreshCw,
  Filter,
  Search,
  LayoutGrid,
  List,
  ArrowRight,
  ChevronDown
} from 'lucide-react';
import { WorkItemCard } from './WorkItemCard';
import { WorkItemModal } from './WorkItemModal';

// Neo4j configuration
const NEO4J_URI = import.meta.env.VITE_NEO4J_URI || "bolt://localhost:7687";
const NEO4J_USER = import.meta.env.VITE_NEO4J_USER || "neo4j";
const NEO4J_PASSWORD = import.meta.env.VITE_NEO4J_PASSWORD || "password";
const DRIVER = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD));

/**
 * Kanban column configuration
 */
const COLUMNS = [
  { id: 'open', label: 'Open', color: 'border-blue-500', bgColor: 'bg-blue-900/20' },
  { id: 'in_progress', label: 'In Progress', color: 'border-yellow-500', bgColor: 'bg-yellow-900/20' },
  { id: 'blocked', label: 'Blocked', color: 'border-red-500', bgColor: 'bg-red-900/20' },
  { id: 'closed', label: 'Closed', color: 'border-green-500', bgColor: 'bg-green-900/20' }
];

/**
 * Filter options
 */
const PRIORITY_FILTERS = ['all', 'critical', 'high', 'medium', 'low'];
const TYPE_FILTERS = ['all', 'bug', 'feature', 'task', 'enhancement', 'docs', 'refactor', 'chore'];

/**
 * KanbanColumn - A single column in the Kanban board
 */
function KanbanColumn({
  column,
  workItems,
  onItemClick,
  onStatusChange,
  onDragStart,
  onDragOver,
  onDrop,
  isDropTarget
}) {
  return (
    <div
      className={`flex-1 min-w-[280px] max-w-[350px] flex flex-col rounded-lg border-t-4 ${column.color} ${column.bgColor}`}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, column.id)}
    >
      {/* Column Header */}
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider">
            {column.label}
          </h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">
            {workItems.length}
          </span>
        </div>
      </div>

      {/* Column Body - Scrollable */}
      <div
        className={`flex-1 p-2 overflow-y-auto space-y-2 transition-colors ${
          isDropTarget ? 'bg-blue-900/30' : ''
        }`}
      >
        <AnimatePresence mode="popLayout">
          {workItems.map((item) => (
            <div
              key={item.uid}
              draggable
              onDragStart={(e) => onDragStart(e, item)}
            >
              <WorkItemCard
                workItem={item}
                onClick={onItemClick}
              />
            </div>
          ))}
        </AnimatePresence>

        {workItems.length === 0 && (
          <div className="text-center py-8 text-gray-600 text-xs">
            No items
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * KanbanBoard - Main Kanban board component for work item management
 */
export function KanbanBoard({ projectId }) {
  const [workItems, setWorkItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal state
  const [selectedItem, setSelectedItem] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isNewItem, setIsNewItem] = useState(false);
  const [linkedCommits, setLinkedCommits] = useState([]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  // Drag state
  const [dragItem, setDragItem] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);

  /**
   * Fetch work items from Neo4j
   */
  const fetchWorkItems = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    const session = DRIVER.session();
    try {
      const result = await session.run(
        `MATCH (w:WorkItem)
         WHERE w.project = $project
         OPTIONAL MATCH (c:CodeChange)-[:LINKS_TO]->(w)
         RETURN w, count(c) as linkedCommits
         ORDER BY
           CASE w.priority
             WHEN 'critical' THEN 0
             WHEN 'high' THEN 1
             WHEN 'medium' THEN 2
             WHEN 'low' THEN 3
           END,
           w.created_at DESC`,
        { project: projectId }
      );

      const items = result.records.map(record => {
        const props = record.get('w').properties;
        const commits = record.get('linkedCommits').toNumber?.() || record.get('linkedCommits');
        return {
          ...props,
          linked_commits: commits
        };
      });

      setWorkItems(items);
    } catch (e) {
      console.error('Failed to fetch work items:', e);
      setError('Failed to load work items');
    } finally {
      session.close();
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchWorkItems();
  }, [fetchWorkItems]);

  /**
   * Fetch linked commits for a work item
   */
  const fetchLinkedCommits = async (workItemUid) => {
    const session = DRIVER.session();
    try {
      const result = await session.run(
        `MATCH (c:CodeChange)-[:LINKS_TO]->(w:WorkItem {uid: $uid})
         RETURN c
         ORDER BY c.timestamp DESC
         LIMIT 20`,
        { uid: workItemUid }
      );

      return result.records.map(r => r.get('c').properties);
    } catch (e) {
      console.error('Failed to fetch linked commits:', e);
      return [];
    } finally {
      session.close();
    }
  };

  /**
   * Create a new work item
   */
  const createWorkItem = async (data) => {
    const session = DRIVER.session();
    try {
      const uid = `${projectId}::workitem::${crypto.randomUUID().split('-')[0]}`;
      const now = new Date().toISOString();

      await session.run(
        `CREATE (w:WorkItem {
           uid: $uid,
           project: $project,
           title: $title,
           description: $description,
           status: $status,
           priority: $priority,
           work_type: $work_type,
           assignee: $assignee,
           created_at: $created_at,
           updated_at: $updated_at,
           source: 'manual'
         })
         RETURN w`,
        {
          uid,
          project: projectId,
          title: data.title,
          description: data.description || '',
          status: data.status || 'open',
          priority: data.priority || 'medium',
          work_type: data.work_type || 'task',
          assignee: data.assignee || '',
          created_at: now,
          updated_at: now
        }
      );

      await fetchWorkItems();
    } finally {
      session.close();
    }
  };

  /**
   * Update an existing work item
   */
  const updateWorkItem = async (data) => {
    if (!selectedItem) return;

    const session = DRIVER.session();
    try {
      await session.run(
        `MATCH (w:WorkItem {uid: $uid})
         SET w.title = $title,
             w.description = $description,
             w.status = $status,
             w.priority = $priority,
             w.work_type = $work_type,
             w.assignee = $assignee,
             w.updated_at = $updated_at
         RETURN w`,
        {
          uid: selectedItem.uid,
          title: data.title,
          description: data.description || '',
          status: data.status,
          priority: data.priority,
          work_type: data.work_type,
          assignee: data.assignee || '',
          updated_at: new Date().toISOString()
        }
      );

      await fetchWorkItems();
    } finally {
      session.close();
    }
  };

  /**
   * Delete a work item
   */
  const deleteWorkItem = async (uid) => {
    const session = DRIVER.session();
    try {
      await session.run(
        `MATCH (w:WorkItem {uid: $uid})
         DETACH DELETE w`,
        { uid }
      );

      await fetchWorkItems();
    } finally {
      session.close();
    }
  };

  /**
   * Update work item status (for drag-drop)
   */
  const updateWorkItemStatus = async (uid, newStatus) => {
    const session = DRIVER.session();
    try {
      await session.run(
        `MATCH (w:WorkItem {uid: $uid})
         SET w.status = $status,
             w.updated_at = $updated_at
         RETURN w`,
        {
          uid,
          status: newStatus,
          updated_at: new Date().toISOString()
        }
      );

      await fetchWorkItems();
    } finally {
      session.close();
    }
  };

  /**
   * Handle item click - open modal
   */
  const handleItemClick = async (item) => {
    setSelectedItem(item);
    setIsNewItem(false);
    setIsModalOpen(true);

    // Fetch linked commits
    const commits = await fetchLinkedCommits(item.uid);
    setLinkedCommits(commits);
  };

  /**
   * Handle create new item
   */
  const handleCreateNew = () => {
    setSelectedItem(null);
    setIsNewItem(true);
    setLinkedCommits([]);
    setIsModalOpen(true);
  };

  /**
   * Handle save from modal
   */
  const handleSave = async (data) => {
    if (isNewItem) {
      await createWorkItem(data);
    } else {
      await updateWorkItem(data);
    }
  };

  /**
   * Drag handlers
   */
  const handleDragStart = (e, item) => {
    setDragItem(item);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e, columnId) => {
    e.preventDefault();
    setDropTarget(null);

    if (dragItem && dragItem.status !== columnId) {
      await updateWorkItemStatus(dragItem.uid, columnId);
    }
    setDragItem(null);
  };

  /**
   * Filter work items
   */
  const filteredItems = workItems.filter(item => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        item.title?.toLowerCase().includes(query) ||
        item.description?.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }

    // Priority filter
    if (priorityFilter !== 'all' && item.priority !== priorityFilter) {
      return false;
    }

    // Type filter
    if (typeFilter !== 'all' && item.work_type !== typeFilter) {
      return false;
    }

    return true;
  });

  /**
   * Group items by status
   */
  const itemsByStatus = COLUMNS.reduce((acc, col) => {
    acc[col.id] = filteredItems.filter(item => item.status === col.id);
    return acc;
  }, {});

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <LayoutGrid size={20} className="text-blue-400" />
            Work Items
          </h2>
          <span className="text-xs text-gray-500">
            {filteredItems.length} items
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-gray-900/50 border border-gray-800 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none w-48"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm transition-colors ${
              showFilters ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <Filter size={14} />
            Filters
            <ChevronDown size={14} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>

          {/* Refresh */}
          <button
            onClick={fetchWorkItems}
            disabled={loading}
            className="p-2 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>

          {/* Create New */}
          <button
            onClick={handleCreateNew}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors text-sm"
          >
            <Plus size={14} />
            New Item
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-b border-gray-800 overflow-hidden"
          >
            <div className="p-4 flex items-center gap-6">
              {/* Priority Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Priority:</span>
                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="bg-gray-900/50 border border-gray-800 rounded px-2 py-1 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  {PRIORITY_FILTERS.map(p => (
                    <option key={p} value={p}>{p === 'all' ? 'All Priorities' : p}</option>
                  ))}
                </select>
              </div>

              {/* Type Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Type:</span>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="bg-gray-900/50 border border-gray-800 rounded px-2 py-1 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  {TYPE_FILTERS.map(t => (
                    <option key={t} value={t}>{t === 'all' ? 'All Types' : t}</option>
                  ))}
                </select>
              </div>

              {/* Clear Filters */}
              {(priorityFilter !== 'all' || typeFilter !== 'all' || searchQuery) && (
                <button
                  onClick={() => {
                    setPriorityFilter('all');
                    setTypeFilter('all');
                    setSearchQuery('');
                  }}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  Clear filters
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-900/20 border-b border-red-800 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto p-4">
        {loading && workItems.length === 0 ? (
          <div className="flex items-center justify-center h-full text-blue-400 animate-pulse">
            Loading work items...
          </div>
        ) : (
          <div className="flex gap-4 h-full min-h-[400px]">
            {COLUMNS.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                workItems={itemsByStatus[column.id] || []}
                onItemClick={handleItemClick}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                isDropTarget={dropTarget === column.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Work Item Modal */}
      <WorkItemModal
        workItem={selectedItem}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedItem(null);
          setLinkedCommits([]);
        }}
        onSave={handleSave}
        onDelete={deleteWorkItem}
        linkedCommits={linkedCommits}
        isNew={isNewItem}
      />
    </div>
  );
}

export default KanbanBoard;
