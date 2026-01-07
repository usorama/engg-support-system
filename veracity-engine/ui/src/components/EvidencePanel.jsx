/**
 * Evidence Panel Component (STORY-015)
 *
 * Displays evidence packets with citations and file paths.
 * Supports evidence-only mode (no LLM synthesis).
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Code, AlertTriangle, CheckCircle, Copy, ExternalLink, Hash } from 'lucide-react';

/**
 * Format a Unix timestamp to readable date
 */
const formatTimestamp = (ts) => {
  if (!ts) return 'Unknown';
  try {
    const date = new Date(ts * 1000);
    return date.toLocaleString();
  } catch {
    return String(ts);
  }
};

/**
 * Truncate text with ellipsis
 */
const truncate = (text, maxLen = 100) => {
  if (!text) return '';
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
};

/**
 * Copy text to clipboard
 */
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};

/**
 * Evidence Item Component
 * Renders a single evidence entry with citation details
 */
const EvidenceItem = ({ evidence, type = 'code' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = evidence.excerpt || evidence.docstring || evidence.path;
    if (await copyToClipboard(text)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isCode = type === 'code';
  const Icon = isCode ? Code : FileText;
  const typeLabels = evidence.type || [];

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-3 mb-2 hover:border-blue-800 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} className={isCode ? "text-blue-400" : "text-green-400"} />
          <span className="text-sm font-medium text-gray-200">
            {evidence.name || 'Unknown'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {evidence.score !== undefined && (
            <span className="text-xs bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded">
              {(evidence.score * 100).toFixed(0)}%
            </span>
          )}
          <button
            onClick={handleCopy}
            className="p-1 text-gray-500 hover:text-blue-400 transition-colors"
            title="Copy to clipboard"
          >
            {copied ? <CheckCircle size={12} className="text-green-400" /> : <Copy size={12} />}
          </button>
        </div>
      </div>

      {/* File path */}
      <div className="text-xs text-gray-500 font-mono mb-2 flex items-center gap-1">
        <span>{evidence.path || 'unknown'}</span>
        {evidence.start_line && (
          <span className="text-gray-600">
            :{evidence.start_line}
            {evidence.end_line && evidence.end_line !== evidence.start_line ? `-${evidence.end_line}` : ''}
          </span>
        )}
      </div>

      {/* Type labels */}
      {typeLabels.length > 0 && (
        <div className="flex gap-1 mb-2">
          {typeLabels.map((label, i) => (
            <span key={i} className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
              {label}
            </span>
          ))}
        </div>
      )}

      {/* Excerpt/content preview */}
      {(evidence.excerpt || evidence.docstring) && (
        <div className="text-xs text-gray-400 font-mono bg-gray-950/50 p-2 rounded border border-gray-800">
          {truncate(evidence.excerpt || evidence.docstring, 200)}
        </div>
      )}

      {/* Evidence hash */}
      {evidence.evidence_hash && (
        <div className="mt-2 text-[10px] text-gray-600 flex items-center gap-1 font-mono">
          <Hash size={10} />
          {evidence.evidence_hash.slice(0, 16)}...
        </div>
      )}
    </div>
  );
};

/**
 * Provenance Display Component
 * Shows provenance metadata for evidence items
 */
export const ProvenanceDisplay = ({ provenance }) => {
  if (!provenance) return null;

  const fields = [
    { key: 'prov_file_hash', label: 'File Hash', icon: Hash },
    { key: 'prov_text_hash', label: 'Content Hash', icon: Hash },
    { key: 'prov_last_modified', label: 'Last Modified', format: formatTimestamp },
    { key: 'prov_extractor', label: 'Extractor' },
    { key: 'prov_extractor_version', label: 'Version' },
  ];

  const hasProvenance = fields.some(f => provenance[f.key]);
  if (!hasProvenance) return null;

  return (
    <div className="bg-indigo-900/20 border border-indigo-800/50 rounded-lg p-3 mt-2">
      <div className="text-xs font-bold text-indigo-400 mb-2 uppercase tracking-wider">
        Provenance
      </div>
      <div className="space-y-1">
        {fields.map(({ key, label, icon: Icon, format }) => {
          const value = provenance[key];
          if (!value) return null;

          const displayValue = format ? format(value) : value;
          const isHash = key.includes('hash');

          return (
            <div key={key} className="flex items-center gap-2 text-xs">
              {Icon && <Icon size={10} className="text-indigo-500" />}
              <span className="text-gray-500">{label}:</span>
              <span className={`text-gray-300 ${isHash ? 'font-mono text-[10px]' : ''}`}>
                {isHash ? truncate(displayValue, 20) : displayValue}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * Veracity Summary Component
 * Displays confidence score and fault summary
 */
export const VeracitySummary = ({ veracity }) => {
  if (!veracity) return null;

  const { confidence_score, is_stale, faults = [] } = veracity;
  const isHealthy = confidence_score >= 80;
  const hasWarnings = faults.length > 0;

  return (
    <div className={`rounded-lg p-3 border ${isHealthy ? 'bg-green-900/20 border-green-800/50' : 'bg-yellow-900/20 border-yellow-800/50'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isHealthy ? (
            <CheckCircle size={16} className="text-green-400" />
          ) : (
            <AlertTriangle size={16} className="text-yellow-400" />
          )}
          <span className="text-sm font-medium text-gray-200">Veracity Score</span>
        </div>
        <span className={`text-lg font-bold ${isHealthy ? 'text-green-400' : 'text-yellow-400'}`}>
          {confidence_score?.toFixed(1)}%
        </span>
      </div>

      {is_stale && (
        <div className="text-xs text-yellow-500 mb-2">
          Contains stale data
        </div>
      )}

      {hasWarnings && (
        <div className="mt-2">
          <div className="text-xs text-gray-500 mb-1">Faults ({faults.length}):</div>
          <ul className="text-xs text-gray-400 space-y-1">
            {faults.slice(0, 3).map((fault, i) => (
              <li key={i} className="flex items-start gap-1">
                <AlertTriangle size={10} className="text-yellow-500 mt-0.5 flex-shrink-0" />
                <span>{typeof fault === 'string' ? fault : fault.message || JSON.stringify(fault)}</span>
              </li>
            ))}
            {faults.length > 3 && (
              <li className="text-gray-600">...and {faults.length - 3} more</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

/**
 * Main Evidence Panel Component
 * Renders the complete evidence panel with tabs
 */
const EvidencePanel = ({ packet, onClose }) => {
  const [activeTab, setActiveTab] = useState('code');

  if (!packet) return null;

  const {
    meta = {},
    code_truth = [],
    doc_claims = [],
    veracity = {},
    graph_relationships = [],
    suggested_actions = [],
  } = packet;

  const tabs = [
    { id: 'code', label: 'Code Evidence', count: code_truth.length, icon: Code },
    { id: 'docs', label: 'Documents', count: doc_claims.length, icon: FileText },
  ];

  return (
    <motion.div
      initial={{ y: 300, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 300, opacity: 0 }}
      className="glass-panel absolute bottom-4 left-4 right-4 max-h-[50vh] overflow-hidden z-30 flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wider">Evidence Packet</div>
          <div className="text-sm text-gray-300 font-mono">
            {meta.query_id?.slice(0, 8) || 'N/A'}
          </div>
        </div>
        <div className="flex items-center gap-4">
          {meta.schema_version && (
            <span className="text-xs text-gray-600">Schema v{meta.schema_version}</span>
          )}
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-xl leading-none"
          >
            &times;
          </button>
        </div>
      </div>

      {/* Veracity Summary */}
      <div className="p-4 border-b border-gray-800">
        <VeracitySummary veracity={veracity} />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        {tabs.map(({ id, label, count, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
              activeTab === id
                ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-900/10'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon size={14} />
            {label}
            <span className="text-xs bg-gray-800 px-1.5 py-0.5 rounded">{count}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'code' && (
          <div>
            {code_truth.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-8">
                No code evidence found
              </div>
            ) : (
              code_truth.map((evidence, i) => (
                <div key={i}>
                  <EvidenceItem evidence={evidence} type="code" />
                  <ProvenanceDisplay provenance={evidence} />
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'docs' && (
          <div>
            {doc_claims.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-8">
                No document evidence found
              </div>
            ) : (
              doc_claims.map((evidence, i) => (
                <div key={i}>
                  <EvidenceItem evidence={evidence} type="doc" />
                  <ProvenanceDisplay provenance={evidence} />
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Suggested Actions */}
      {suggested_actions.length > 0 && (
        <div className="p-4 border-t border-gray-800 bg-gray-900/30">
          <div className="text-xs text-gray-500 mb-2">Suggested Actions</div>
          <ul className="text-xs text-gray-400 space-y-1">
            {suggested_actions.slice(0, 3).map((action, i) => (
              <li key={i} className="flex items-center gap-2">
                <ExternalLink size={10} className="text-blue-500" />
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
};

export default EvidencePanel;
