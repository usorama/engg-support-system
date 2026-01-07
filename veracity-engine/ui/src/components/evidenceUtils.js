/**
 * Evidence Utilities (STORY-015)
 *
 * Utility functions for formatting and processing evidence data.
 * These functions are pure and can be easily tested.
 */

/**
 * Format a Unix timestamp to ISO string
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} ISO formatted date string
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp || isNaN(timestamp)) return 'Unknown';
  try {
    return new Date(timestamp * 1000).toISOString();
  } catch {
    return String(timestamp);
  }
};

/**
 * Format a Unix timestamp to locale string
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} Locale formatted date string
 */
export const formatTimestampLocale = (timestamp) => {
  if (!timestamp || isNaN(timestamp)) return 'Unknown';
  try {
    return new Date(timestamp * 1000).toLocaleString();
  } catch {
    return String(timestamp);
  }
};

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLen - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLen = 100) => {
  if (!text || typeof text !== 'string') return '';
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
};

/**
 * Truncate hash for display
 * @param {string} hash - Full hash string
 * @param {number} chars - Characters to show (split evenly)
 * @returns {string} Truncated hash with ellipsis
 */
export const truncateHash = (hash, chars = 16) => {
  if (!hash || typeof hash !== 'string') return '';
  if (hash.length <= chars) return hash;
  const half = Math.floor(chars / 2);
  return `${hash.slice(0, half)}...${hash.slice(-half)}`;
};

/**
 * Calculate confidence color based on score
 * @param {number} score - Confidence score (0-100)
 * @returns {string} Tailwind CSS color class
 */
export const getConfidenceColor = (score) => {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
};

/**
 * Calculate confidence background color based on score
 * @param {number} score - Confidence score (0-100)
 * @returns {string} Tailwind CSS background class
 */
export const getConfidenceBackground = (score) => {
  if (score >= 80) return 'bg-green-900/20';
  if (score >= 60) return 'bg-yellow-900/20';
  if (score >= 40) return 'bg-orange-900/20';
  return 'bg-red-900/20';
};

/**
 * Format file path for display
 * @param {string} path - File path
 * @param {number} maxLen - Maximum display length
 * @returns {string} Formatted path
 */
export const formatFilePath = (path, maxLen = 50) => {
  if (!path) return 'unknown';
  if (path.length <= maxLen) return path;

  const parts = path.split('/');
  if (parts.length <= 2) return truncateText(path, maxLen);

  // Keep first and last parts, truncate middle
  const first = parts[0];
  const last = parts.slice(-2).join('/');
  return `${first}/.../${last}`;
};

/**
 * Format line range for display
 * @param {number} start - Start line
 * @param {number} end - End line (optional)
 * @returns {string} Formatted line range
 */
export const formatLineRange = (start, end) => {
  if (!start) return '';
  if (!end || end === start) return `:${start}`;
  return `:${start}-${end}`;
};

/**
 * Calculate document freshness status
 * @param {number} lastModified - Unix timestamp
 * @returns {{ status: string, color: string, label: string }}
 */
export const getDocumentFreshness = (lastModified) => {
  if (!lastModified) {
    return { status: 'unknown', color: 'text-gray-500', label: 'Unknown' };
  }

  const now = Date.now() / 1000;
  const ageDays = (now - lastModified) / 86400;

  if (ageDays < 7) {
    return { status: 'fresh', color: 'text-green-400', label: 'Fresh' };
  }
  if (ageDays < 30) {
    return { status: 'recent', color: 'text-yellow-400', label: 'Recent' };
  }
  if (ageDays < 90) {
    return { status: 'aging', color: 'text-orange-400', label: 'Aging' };
  }
  return { status: 'stale', color: 'text-red-400', label: 'Stale' };
};

/**
 * Extract fault type from fault message
 * @param {string|object} fault - Fault message or object
 * @returns {string} Fault type
 */
export const extractFaultType = (fault) => {
  if (typeof fault === 'string') {
    const match = fault.match(/^([A-Z_]+):/);
    return match ? match[1] : 'UNKNOWN';
  }
  if (typeof fault === 'object' && fault.type) {
    return fault.type;
  }
  return 'UNKNOWN';
};

/**
 * Group faults by type
 * @param {Array} faults - Array of faults
 * @returns {Object} Faults grouped by type
 */
export const groupFaultsByType = (faults) => {
  if (!Array.isArray(faults)) return {};

  return faults.reduce((acc, fault) => {
    const type = extractFaultType(fault);
    if (!acc[type]) acc[type] = [];
    acc[type].push(fault);
    return acc;
  }, {});
};

/**
 * Validate evidence packet schema
 * @param {Object} packet - Evidence packet
 * @returns {{ valid: boolean, errors: string[] }}
 */
export const validateEvidencePacket = (packet) => {
  const errors = [];

  if (!packet) {
    return { valid: false, errors: ['Packet is null or undefined'] };
  }

  // Check meta
  if (!packet.meta) {
    errors.push('Missing meta section');
  } else {
    if (!packet.meta.schema_version) errors.push('Missing meta.schema_version');
    if (!packet.meta.query_id) errors.push('Missing meta.query_id');
    if (!packet.meta.project) errors.push('Missing meta.project');
  }

  // Check veracity
  if (!packet.veracity) {
    errors.push('Missing veracity section');
  } else {
    if (packet.veracity.confidence_score === undefined) {
      errors.push('Missing veracity.confidence_score');
    }
  }

  // Check evidence arrays
  if (!Array.isArray(packet.code_truth)) {
    errors.push('Missing or invalid code_truth array');
  }
  if (!Array.isArray(packet.doc_claims)) {
    errors.push('Missing or invalid doc_claims array');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
};

/**
 * Sort evidence by score (descending), then path (ascending)
 * @param {Array} evidence - Array of evidence items
 * @returns {Array} Sorted evidence
 */
export const sortEvidence = (evidence) => {
  if (!Array.isArray(evidence)) return [];

  return [...evidence].sort((a, b) => {
    // Score descending
    const scoreA = a.score || 0;
    const scoreB = b.score || 0;
    if (scoreA !== scoreB) return scoreB - scoreA;

    // Path ascending
    const pathA = a.path || '';
    const pathB = b.path || '';
    return pathA.localeCompare(pathB);
  });
};

/**
 * Check if evidence has provenance data
 * @param {Object} evidence - Evidence item
 * @returns {boolean}
 */
export const hasProvenance = (evidence) => {
  if (!evidence) return false;
  return !!(
    evidence.prov_file_hash ||
    evidence.prov_text_hash ||
    evidence.prov_last_modified ||
    evidence.prov_extractor
  );
};

/**
 * Extract provenance fields from evidence
 * @param {Object} evidence - Evidence item
 * @returns {Object} Provenance fields only
 */
export const extractProvenance = (evidence) => {
  if (!evidence) return {};

  return {
    prov_file_hash: evidence.prov_file_hash,
    prov_text_hash: evidence.prov_text_hash,
    prov_last_modified: evidence.prov_last_modified,
    prov_extractor: evidence.prov_extractor,
    prov_extractor_version: evidence.prov_extractor_version,
    prov_path: evidence.prov_path,
  };
};

export default {
  formatTimestamp,
  formatTimestampLocale,
  truncateText,
  truncateHash,
  getConfidenceColor,
  getConfidenceBackground,
  formatFilePath,
  formatLineRange,
  getDocumentFreshness,
  extractFaultType,
  groupFaultsByType,
  validateEvidencePacket,
  sortEvidence,
  hasProvenance,
  extractProvenance,
};
