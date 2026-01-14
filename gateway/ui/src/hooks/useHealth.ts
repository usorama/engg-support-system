/**
 * useHealth Hook - Monitors ESS Gateway health status
 *
 * Provides real-time health monitoring with automatic polling
 * and status indicators for all backend services.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient, APIClientError } from "../utils/api-client";
import type { HealthResponse, ServiceHealth } from "../types/api";

export interface UseHealthOptions {
  /** Polling interval in ms (default: 30000 = 30 seconds) */
  pollInterval?: number;
  /** Auto-start polling (default: true) */
  autoStart?: boolean;
}

export interface UseHealthResult {
  /** Current health status */
  health: HealthResponse | null;
  /** Loading state */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Is the system healthy enough to use */
  isOperational: boolean;
  /** Manually refresh health */
  refresh: () => Promise<void>;
  /** Start polling */
  startPolling: () => void;
  /** Stop polling */
  stopPolling: () => void;
}

/**
 * Hook for monitoring ESS Gateway health
 */
export function useHealth(options: UseHealthOptions = {}): UseHealthResult {
  const { pollInterval = 30000, autoStart = true } = options;

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const checkHealth = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
      setIsLoading(true);
      setError(null);
      const response = await apiClient.getHealth();
      if (mountedRef.current) {
        setHealth(response);
      }
    } catch (err) {
      if (mountedRef.current) {
        if (err instanceof APIClientError) {
          setError(err.message);
        } else {
          setError("Failed to check health status");
        }
        // Set unhealthy state when we can't reach the API
        setHealth({
          status: "unhealthy",
          timestamp: new Date().toISOString(),
          services: {
            neo4j: { status: "unknown" },
            qdrant: { status: "unknown" },
            redis: { status: "unknown" },
            ollama: { status: "unknown" },
          },
        });
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  const startPolling = useCallback(() => {
    if (pollingRef.current) return;
    pollingRef.current = setInterval(checkHealth, pollInterval);
  }, [checkHealth, pollInterval]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // Initial check and auto-start polling
  useEffect(() => {
    mountedRef.current = true;
    checkHealth();

    if (autoStart) {
      startPolling();
    }

    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [checkHealth, autoStart, startPolling, stopPolling]);

  // Determine if system is operational
  const isOperational =
    health !== null &&
    (health.status === "healthy" || health.status === "degraded");

  return {
    health,
    isLoading,
    error,
    isOperational,
    refresh: checkHealth,
    startPolling,
    stopPolling,
  };
}

/**
 * Get service status indicator color
 */
export function getServiceStatusColor(status: ServiceHealth["status"]): string {
  switch (status) {
    case "ok":
      return "text-green-400";
    case "error":
      return "text-red-400";
    default:
      return "text-yellow-400";
  }
}

/**
 * Get overall status indicator color
 */
export function getOverallStatusColor(
  status: HealthResponse["status"]
): string {
  switch (status) {
    case "healthy":
      return "text-green-400";
    case "degraded":
      return "text-yellow-400";
    default:
      return "text-red-400";
  }
}

export default useHealth;
