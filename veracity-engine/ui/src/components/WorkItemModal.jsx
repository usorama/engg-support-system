import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Save,
  Trash2,
  GitCommit,
  ExternalLink,
  Clock,
  User,
  Tag,
  AlertTriangle
} from 'lucide-react';

/**
 * Status options for work items
 */
const STATUS_OPTIONS = [
  { value: 'open', label: 'Open', color: 'bg-blue-500' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-yellow-500' },
  { value: 'blocked', label: 'Blocked', color: 'bg-red-500' },
  { value: 'closed', label: 'Closed', color: 'bg-green-500' }
];

/**
 * Priority options
 */
const PRIORITY_OPTIONS = [
  { value: 'critical', label: 'Critical', color: 'text-red-400' },
  { value: 'high', label: 'High', color: 'text-orange-400' },
  { value: 'medium', label: 'Medium', color: 'text-yellow-400' },
  { value: 'low', label: 'Low', color: 'text-gray-400' }
];

/**
 * Work type options
 */
const WORK_TYPE_OPTIONS = [
  { value: 'bug', label: 'Bug' },
  { value: 'feature', label: 'Feature' },
  { value: 'task', label: 'Task' },
  { value: 'enhancement', label: 'Enhancement' },
  { value: 'docs', label: 'Documentation' },
  { value: 'refactor', label: 'Refactor' },
  { value: 'chore', label: 'Chore' }
];

/**
 * WorkItemModal - Modal for viewing, creating, and editing work items
 */
export function WorkItemModal({
  workItem,
  isOpen,
  onClose,
  onSave,
  onDelete,
  linkedCommits = [],
  isNew = false
}) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'open',
    priority: 'medium',
    work_type: 'task',
    assignee: ''
  });

  const [isSaving, setIsSaving] = useState(false);

  // Populate form when workItem changes
  useEffect(() => {
    if (workItem) {
      setFormData({
        title: workItem.title || '',
        description: workItem.description || '',
        status: workItem.status || 'open',
        priority: workItem.priority || 'medium',
        work_type: workItem.work_type || 'task',
        assignee: workItem.assignee || ''
      });
    } else {
      // Reset for new work item
      setFormData({
        title: '',
        description: '',
        status: 'open',
        priority: 'medium',
        work_type: 'task',
        assignee: ''
      });
    }
  }, [workItem]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    if (!formData.title.trim()) {
      return; // Require title
    }

    setIsSaving(true);
    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      console.error('Failed to save work item:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this work item?')) {
      try {
        await onDelete(workItem.uid);
        onClose();
      } catch (error) {
        console.error('Failed to delete work item:', error);
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[600px] md:max-h-[80vh] glass-panel rounded-xl overflow-hidden z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h2 className="text-lg font-bold text-white">
                {isNew ? 'Create Work Item' : 'Edit Work Item'}
              </h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Title */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-1 block">
                  Title *
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  placeholder="Enter work item title..."
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              {/* Description */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-1 block">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Describe the work item..."
                  rows={4}
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>

              {/* Status + Priority Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider mb-1 block">
                    Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => handleChange('status', e.target.value)}
                    className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                  >
                    {STATUS_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider mb-1 block">
                    Priority
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) => handleChange('priority', e.target.value)}
                    className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                  >
                    {PRIORITY_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Work Type + Assignee Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider mb-1 block">
                    Type
                  </label>
                  <select
                    value={formData.work_type}
                    onChange={(e) => handleChange('work_type', e.target.value)}
                    className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                  >
                    {WORK_TYPE_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider mb-1 block">
                    Assignee
                  </label>
                  <input
                    type="text"
                    value={formData.assignee}
                    onChange={(e) => handleChange('assignee', e.target.value)}
                    placeholder="Unassigned"
                    className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Read-only metadata for existing items */}
              {!isNew && workItem && (
                <div className="border-t border-gray-800 pt-4 space-y-3">
                  <h3 className="text-xs text-gray-500 uppercase tracking-wider">Metadata</h3>

                  {/* UID */}
                  <div className="flex items-center gap-2 text-xs">
                    <Tag size={12} className="text-gray-500" />
                    <span className="text-gray-500">UID:</span>
                    <code className="text-gray-400 bg-gray-900/50 px-2 py-0.5 rounded font-mono text-[10px]">
                      {workItem.uid}
                    </code>
                  </div>

                  {/* Created At */}
                  {workItem.created_at && (
                    <div className="flex items-center gap-2 text-xs">
                      <Clock size={12} className="text-gray-500" />
                      <span className="text-gray-500">Created:</span>
                      <span className="text-gray-400">
                        {new Date(workItem.created_at).toLocaleString()}
                      </span>
                    </div>
                  )}

                  {/* External Link */}
                  {workItem.external_id && (
                    <div className="flex items-center gap-2 text-xs">
                      <ExternalLink size={12} className="text-purple-400" />
                      <span className="text-gray-500">External:</span>
                      <span className="text-purple-400">{workItem.external_id}</span>
                    </div>
                  )}

                  {/* Linked Commits */}
                  {linkedCommits.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                        <GitCommit size={12} />
                        <span>Linked Commits ({linkedCommits.length})</span>
                      </div>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {linkedCommits.map((commit, idx) => (
                          <div
                            key={idx}
                            className="text-[10px] bg-gray-900/50 rounded px-2 py-1 font-mono text-gray-400"
                          >
                            <span className="text-green-400">{commit.hash?.slice(0, 8)}</span>
                            {' - '}
                            <span>{commit.message?.slice(0, 50)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-gray-800">
              <div>
                {!isNew && workItem && (
                  <button
                    onClick={handleDelete}
                    className="flex items-center gap-2 px-3 py-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-lg transition-colors text-sm"
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving || !formData.title.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm"
                >
                  <Save size={14} />
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default WorkItemModal;
