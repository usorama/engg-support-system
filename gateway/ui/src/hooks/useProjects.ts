/**
 * useProjects Hook - Manages project selection
 *
 * Fetches available projects from Neo4j and manages
 * the current project selection state.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient, APIClientError } from "../utils/api-client";

export interface UseProjectsResult {
  /** Available projects */
  projects: string[];
  /** Currently selected project */
  selectedProject: string | null;
  /** Select a project */
  selectProject: (project: string | null) => void;
  /** Loading state */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Refresh project list */
  refresh: () => Promise<void>;
}

// Local storage key for persisting selection
const SELECTED_PROJECT_KEY = "ess-selected-project";

/**
 * Hook for managing project selection
 */
export function useProjects(): UseProjectsResult {
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(() => {
    // Restore from local storage
    try {
      return localStorage.getItem(SELECTED_PROJECT_KEY);
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const fetchProjects = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
      setIsLoading(true);
      setError(null);
      const response = await apiClient.getProjects();
      if (mountedRef.current) {
        setProjects(response.projects);

        // If selected project no longer exists, reset selection
        if (
          selectedProject &&
          response.projects.length > 0 &&
          !response.projects.includes(selectedProject)
        ) {
          setSelectedProject(null);
          localStorage.removeItem(SELECTED_PROJECT_KEY);
        }
      }
    } catch (err) {
      if (mountedRef.current) {
        if (err instanceof APIClientError) {
          setError(err.message);
        } else {
          setError("Failed to load projects");
        }
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [selectedProject]);

  const selectProject = useCallback((project: string | null) => {
    setSelectedProject(project);
    try {
      if (project) {
        localStorage.setItem(SELECTED_PROJECT_KEY, project);
      } else {
        localStorage.removeItem(SELECTED_PROJECT_KEY);
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    fetchProjects();

    return () => {
      mountedRef.current = false;
    };
  }, [fetchProjects]);

  return {
    projects,
    selectedProject,
    selectProject,
    isLoading,
    error,
    refresh: fetchProjects,
  };
}

export default useProjects;
