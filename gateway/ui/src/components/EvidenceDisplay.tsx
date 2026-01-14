/**
 * EvidenceDisplay - Shows citations and evidence sources
 *
 * Displays evidence citations with confidence indicators,
 * source links, and expandable code snippets.
 */

import { useState } from "react";
import {
  FileCode,
  FileText,
  GitBranch,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  CheckCircle,
} from "lucide-react";
import type {
  SynthesisCitation,
  SemanticMatch,
  StructuralRelationship,
  QueryResults,
} from "../types/api";
import { CodeBlock } from "./CodeBlock";

export interface EvidenceDisplayProps {
  /** Citations from synthesized answer */
  citations?: SynthesisCitation[];
  /** Full query results for expanded view */
  results?: QueryResults;
  /** Overall confidence score */
  confidence?: number;
}

/**
 * Get icon for citation type
 */
function getCitationIcon(type: "code" | "doc" | "graph") {
  switch (type) {
    case "code":
      return FileCode;
    case "doc":
      return FileText;
    case "graph":
      return GitBranch;
    default:
      return FileCode;
  }
}

/**
 * Get confidence color class
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-green-400";
  if (confidence >= 0.5) return "text-yellow-400";
  return "text-red-400";
}

/**
 * Format relevance as percentage
 */
function formatRelevance(relevance: number): string {
  return `${Math.round(relevance * 100)}%`;
}

/**
 * Citation item component
 */
function CitationItem({
  citation,
  index,
}: {
  citation: SynthesisCitation;
  index: number;
}) {
  const Icon = getCitationIcon(citation.type);
  const lineInfo =
    citation.lineStart !== undefined
      ? citation.lineEnd !== undefined && citation.lineEnd !== citation.lineStart
        ? `L${citation.lineStart}-${citation.lineEnd}`
        : `L${citation.lineStart}`
      : null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors">
      <span className="flex items-center justify-center w-5 h-5 text-xs font-medium bg-slate-700 rounded">
        {index + 1}
      </span>
      <Icon size={14} className="text-slate-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-300 truncate" title={citation.source}>
            {citation.source}
          </span>
          {lineInfo && (
            <span className="text-xs text-slate-500">{lineInfo}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 text-xs">
        <span className={getConfidenceColor(citation.relevance)}>
          {formatRelevance(citation.relevance)}
        </span>
      </div>
    </div>
  );
}

/**
 * Semantic match item with expandable code
 */
function SemanticMatchItem({
  match,
  index,
}: {
  match: SemanticMatch;
  index: number;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-slate-800/30 hover:bg-slate-800/50 transition-colors text-left"
      >
        {isExpanded ? (
          <ChevronDown size={14} className="text-slate-400" />
        ) : (
          <ChevronRight size={14} className="text-slate-400" />
        )}
        <span className="flex items-center justify-center w-5 h-5 text-xs font-medium bg-slate-700 rounded">
          {index + 1}
        </span>
        <FileCode size={14} className="text-slate-400" />
        <span className="text-sm text-slate-300 truncate flex-1">
          {match.source}
        </span>
        <span className={`text-xs ${getConfidenceColor(match.score)}`}>
          {formatRelevance(match.score)}
        </span>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-700">
          <CodeBlock
            code={match.content}
            language={match.language}
            source={match.source}
            lineStart={match.lineStart}
            lineEnd={match.lineEnd}
            maxHeight="200px"
          />
        </div>
      )}
    </div>
  );
}

/**
 * Structural relationship item
 */
function RelationshipItem({
  relationship,
}: {
  relationship: StructuralRelationship;
}) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/30 rounded-lg text-sm">
      <GitBranch size={14} className="text-cyan-400 flex-shrink-0" />
      <span className="text-slate-400 truncate">{relationship.source}</span>
      <span className="text-cyan-400 font-mono text-xs px-1.5 py-0.5 bg-cyan-400/10 rounded">
        {relationship.type}
      </span>
      <span className="text-slate-400 truncate">{relationship.target}</span>
    </div>
  );
}

export function EvidenceDisplay({
  citations,
  results,
  confidence,
}: EvidenceDisplayProps) {
  const [showExpanded, setShowExpanded] = useState(false);

  const hasCitations = citations && citations.length > 0;
  const hasSemanticResults =
    results?.semantic?.matches && results.semantic.matches.length > 0;
  const hasStructuralResults =
    results?.structural?.relationships &&
    results.structural.relationships.length > 0;

  if (!hasCitations && !hasSemanticResults && !hasStructuralResults) {
    return null;
  }

  return (
    <div className="mt-4 pt-4 border-t border-slate-700/50">
      {/* Header with confidence */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CheckCircle
            size={16}
            className={confidence ? getConfidenceColor(confidence) : "text-slate-400"}
          />
          <span className="text-sm font-medium text-slate-300">
            Evidence Sources
          </span>
          {confidence !== undefined && (
            <span className={`text-sm ${getConfidenceColor(confidence)}`}>
              ({Math.round(confidence * 100)}% confidence)
            </span>
          )}
        </div>

        {(hasSemanticResults || hasStructuralResults) && (
          <button
            onClick={() => setShowExpanded(!showExpanded)}
            className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
          >
            {showExpanded ? "Show less" : "Show details"}
            <ExternalLink size={12} />
          </button>
        )}
      </div>

      {/* Citations list */}
      {hasCitations && (
        <div className="space-y-2 mb-4">
          {citations.map((citation, index) => (
            <CitationItem key={index} citation={citation} index={index} />
          ))}
        </div>
      )}

      {/* Expanded view with full results */}
      {showExpanded && (
        <div className="space-y-4 mt-4 animate-slide-up">
          {/* Semantic matches */}
          {hasSemanticResults && (
            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                <FileCode size={14} />
                Semantic Matches ({results.semantic.matches.length})
              </h4>
              <div className="space-y-2">
                {results.semantic.matches.slice(0, 5).map((match, index) => (
                  <SemanticMatchItem key={index} match={match} index={index} />
                ))}
              </div>
            </div>
          )}

          {/* Structural relationships */}
          {hasStructuralResults && (
            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                <GitBranch size={14} />
                Graph Relationships ({results.structural.relationships.length})
              </h4>
              <div className="space-y-2">
                {results.structural.relationships
                  .slice(0, 5)
                  .map((rel, index) => (
                    <RelationshipItem key={index} relationship={rel} />
                  ))}
              </div>
            </div>
          )}

          {/* Insights */}
          {results?.insights && (
            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-2">
                Key Findings
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                {results.insights.keyFindings.map((finding, index) => (
                  <li key={index}>{finding}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default EvidenceDisplay;
