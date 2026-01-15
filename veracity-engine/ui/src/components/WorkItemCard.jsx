import React from 'react';
import { motion } from 'framer-motion';
import {
  Bug,
  Lightbulb,
  FileText,
  Wrench,
  CheckCircle,
  Clock,
  AlertTriangle,
  GitCommit,
  ExternalLink,
  MoreHorizontal
} from 'lucide-react';

/**
 * Work item type icons
 */
const TYPE_ICONS = {
  bug: Bug,
  feature: Lightbulb,
  docs: FileText,
  refactor: Wrench,
  task: CheckCircle,
  enhancement: Lightbulb,
  chore: Wrench
};

/**
 * Priority badge colors
 */
const PRIORITY_COLORS = {
  critical: 'bg-red-900/50 text-red-400 border-red-800',
  high: 'bg-orange-900/50 text-orange-400 border-orange-800',
  medium: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
  low: 'bg-gray-800/50 text-gray-400 border-gray-700'
};

/**
 * WorkItemCard - A single work item displayed in the Kanban board
 */
export function WorkItemCard({
  workItem,
  onClick,
  onStatusChange,
  isDragging = false
}) {
  const TypeIcon = TYPE_ICONS[workItem.work_type] || CheckCircle;
  const priorityClass = PRIORITY_COLORS[workItem.priority] || PRIORITY_COLORS.medium;

  // Calculate age in days
  const createdAt = workItem.created_at ? new Date(workItem.created_at) : null;
  const ageDays = createdAt
    ? Math.floor((Date.now() - createdAt.getTime()) / (1000 * 60 * 60 * 24))
    : null;

  // Linked commits count
  const linkedCommits = workItem.linked_commits || 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      whileHover={{ scale: 1.02 }}
      onClick={() => onClick && onClick(workItem)}
      className={`
        glass-panel p-3 mb-2 cursor-pointer
        border border-gray-800 hover:border-blue-500
        transition-colors rounded-lg
        ${isDragging ? 'opacity-50 scale-105' : ''}
      `}
    >
      {/* Header Row: Type Icon + Priority */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <TypeIcon size={14} className="text-blue-400" />
          <span className="text-xs text-gray-500 uppercase tracking-wider">
            {workItem.work_type || 'task'}
          </span>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded border ${priorityClass}`}>
          {workItem.priority || 'medium'}
        </span>
      </div>

      {/* Title */}
      <h4 className="text-sm font-medium text-gray-200 mb-2 line-clamp-2">
        {workItem.title}
      </h4>

      {/* Description preview */}
      {workItem.description && (
        <p className="text-xs text-gray-500 mb-2 line-clamp-2">
          {workItem.description}
        </p>
      )}

      {/* Footer Row: Metadata */}
      <div className="flex items-center justify-between text-[10px] text-gray-500">
        <div className="flex items-center gap-3">
          {/* Age indicator */}
          {ageDays !== null && (
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {ageDays === 0 ? 'Today' : `${ageDays}d`}
            </span>
          )}

          {/* Linked commits */}
          {linkedCommits > 0 && (
            <span className="flex items-center gap-1 text-green-400">
              <GitCommit size={10} />
              {linkedCommits}
            </span>
          )}

          {/* External link indicator */}
          {workItem.external_id && (
            <span className="flex items-center gap-1 text-purple-400" title={workItem.external_id}>
              <ExternalLink size={10} />
            </span>
          )}
        </div>

        {/* Stale warning */}
        {ageDays > 30 && workItem.status !== 'closed' && (
          <span className="flex items-center gap-1 text-yellow-500" title="Stale work item">
            <AlertTriangle size={10} />
          </span>
        )}
      </div>
    </motion.div>
  );
}

export default WorkItemCard;
