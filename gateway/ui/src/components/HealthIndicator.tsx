/**
 * HealthIndicator - Service health status display
 *
 * Shows the overall health status and individual service
 * statuses with visual indicators.
 */

import { useState } from "react";
import {
  Activity,
  Database,
  Search,
  Cpu,
  Server,
  ChevronDown,
  RefreshCw,
} from "lucide-react";
import type { HealthResponse, ServiceHealth } from "../types/api";

export interface HealthIndicatorProps {
  /** Current health status */
  health: HealthResponse | null;
  /** Is health check in progress */
  isLoading?: boolean;
  /** Callback to refresh health */
  onRefresh?: () => void;
}

/**
 * Get status indicator styles
 */
function getStatusStyles(status: HealthResponse["status"] | ServiceHealth["status"]) {
  switch (status) {
    case "healthy":
    case "ok":
      return {
        bg: "bg-green-500",
        text: "text-green-400",
        glow: "shadow-green-500/50",
      };
    case "degraded":
    case "unknown":
      return {
        bg: "bg-yellow-500",
        text: "text-yellow-400",
        glow: "shadow-yellow-500/50",
      };
    case "unhealthy":
    case "error":
      return {
        bg: "bg-red-500",
        text: "text-red-400",
        glow: "shadow-red-500/50",
      };
    default:
      return {
        bg: "bg-slate-500",
        text: "text-slate-400",
        glow: "",
      };
  }
}

/**
 * Service icon component
 */
function ServiceIcon({ service }: { service: string }) {
  switch (service) {
    case "neo4j":
      return <Database size={14} />;
    case "qdrant":
      return <Search size={14} />;
    case "ollama":
      return <Cpu size={14} />;
    case "redis":
      return <Server size={14} />;
    default:
      return <Activity size={14} />;
  }
}

/**
 * Individual service status row
 */
function ServiceRow({
  name,
  health,
}: {
  name: string;
  health: ServiceHealth;
}) {
  const styles = getStatusStyles(health.status);

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <ServiceIcon service={name} />
        <span className="text-sm text-slate-300 capitalize">{name}</span>
      </div>
      <div className="flex items-center gap-2">
        {health.latency !== undefined && (
          <span className="text-xs text-slate-500">{health.latency}ms</span>
        )}
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${styles.bg} ${styles.glow} shadow-sm`}
          />
          <span className={`text-xs ${styles.text}`}>
            {health.status === "ok" ? "Connected" : health.status}
          </span>
        </div>
      </div>
    </div>
  );
}

export function HealthIndicator({
  health,
  isLoading,
  onRefresh,
}: HealthIndicatorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const overallStatus = health?.status || "unknown";
  const styles = getStatusStyles(overallStatus);

  return (
    <div className="relative">
      {/* Compact indicator */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all
          bg-slate-800/50 border border-slate-600/50
          hover:bg-slate-700/50
          ${isExpanded ? "ring-2 ring-cyan-500/30" : ""}
        `}
      >
        <div className="relative">
          <div
            className={`w-2.5 h-2.5 rounded-full ${styles.bg} ${styles.glow} shadow-sm`}
          />
          {isLoading && (
            <div className="absolute inset-0 animate-ping">
              <div className={`w-2.5 h-2.5 rounded-full ${styles.bg} opacity-50`} />
            </div>
          )}
        </div>
        <span className={`text-xs font-medium ${styles.text} capitalize`}>
          {overallStatus}
        </span>
        <ChevronDown
          size={12}
          className={`text-slate-500 transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Expanded panel */}
      {isExpanded && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 animate-slide-up">
          <div className="p-3 border-b border-slate-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity size={16} className={styles.text} />
                <span className="text-sm font-medium text-slate-200">
                  System Health
                </span>
              </div>
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  disabled={isLoading}
                  className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-cyan-400/10 rounded-lg transition-colors disabled:opacity-50"
                  title="Refresh"
                >
                  <RefreshCw
                    size={14}
                    className={isLoading ? "animate-spin" : ""}
                  />
                </button>
              )}
            </div>
            {health?.timestamp && (
              <p className="text-xs text-slate-500 mt-1">
                Last checked: {new Date(health.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>

          <div className="p-3 divide-y divide-slate-700/50">
            {health?.services ? (
              Object.entries(health.services).map(([name, serviceHealth]) => (
                <ServiceRow key={name} name={name} health={serviceHealth} />
              ))
            ) : (
              <div className="py-2 text-sm text-slate-500 text-center">
                No health data available
              </div>
            )}
          </div>

          {/* Error messages */}
          {health?.services &&
            Object.entries(health.services).some(([_, s]) => s.error) && (
              <div className="p-3 border-t border-slate-700 bg-red-500/5">
                {Object.entries(health.services)
                  .filter(([_, s]) => s.error)
                  .map(([name, s]) => (
                    <p key={name} className="text-xs text-red-400">
                      {name}: {s.error}
                    </p>
                  ))}
              </div>
            )}
        </div>
      )}
    </div>
  );
}

export default HealthIndicator;
