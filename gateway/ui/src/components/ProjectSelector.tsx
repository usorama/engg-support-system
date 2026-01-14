/**
 * ProjectSelector - Project dropdown selector
 *
 * Allows users to select a project context for their queries.
 * Supports search/filter for projects and persists selection.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import {
  ChevronDown,
  Folder,
  FolderOpen,
  Search,
  X,
  Loader2,
} from "lucide-react";

export interface ProjectSelectorProps {
  /** Available projects */
  projects: string[];
  /** Currently selected project */
  selectedProject: string | null;
  /** Callback when selection changes */
  onSelect: (project: string | null) => void;
  /** Loading state */
  isLoading?: boolean;
  /** Disabled state */
  disabled?: boolean;
}

export function ProjectSelector({
  projects,
  selectedProject,
  onSelect,
  isLoading = false,
  disabled = false,
}: ProjectSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Filter projects based on search
  const filteredProjects = projects.filter((project) =>
    project.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchQuery("");
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const handleToggle = useCallback(() => {
    if (!disabled && !isLoading) {
      setIsOpen((prev) => !prev);
      if (!isOpen) {
        setSearchQuery("");
      }
    }
  }, [disabled, isLoading, isOpen]);

  const handleSelect = useCallback(
    (project: string | null) => {
      onSelect(project);
      setIsOpen(false);
      setSearchQuery("");
    },
    [onSelect]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        setSearchQuery("");
      }
    },
    []
  );

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={handleToggle}
        disabled={disabled || isLoading}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all
          ${
            disabled || isLoading
              ? "bg-slate-800/30 text-slate-500 cursor-not-allowed"
              : "bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 hover:text-slate-200"
          }
          ${isOpen ? "ring-2 ring-cyan-500/50" : ""}
          border border-slate-600/50
        `}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        {isLoading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : selectedProject ? (
          <FolderOpen size={16} className="text-cyan-400" />
        ) : (
          <Folder size={16} />
        )}
        <span className="truncate max-w-[150px]">
          {selectedProject || "All projects"}
        </span>
        <ChevronDown
          size={14}
          className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-64 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 animate-slide-up"
          role="listbox"
          onKeyDown={handleKeyDown}
        >
          {/* Search input */}
          {projects.length > 5 && (
            <div className="p-2 border-b border-slate-700">
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search projects..."
                  className="w-full pl-8 pr-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Options list */}
          <div className="max-h-60 overflow-y-auto py-1">
            {/* "All projects" option */}
            <button
              onClick={() => handleSelect(null)}
              className={`
                w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors
                ${
                  selectedProject === null
                    ? "bg-cyan-500/20 text-cyan-300"
                    : "text-slate-300 hover:bg-slate-700/50"
                }
              `}
              role="option"
              aria-selected={selectedProject === null}
            >
              <Folder size={14} />
              <span>All projects</span>
            </button>

            {/* Divider */}
            {projects.length > 0 && (
              <div className="border-t border-slate-700 my-1" />
            )}

            {/* Project options */}
            {filteredProjects.length > 0 ? (
              filteredProjects.map((project) => (
                <button
                  key={project}
                  onClick={() => handleSelect(project)}
                  className={`
                    w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors
                    ${
                      selectedProject === project
                        ? "bg-cyan-500/20 text-cyan-300"
                        : "text-slate-300 hover:bg-slate-700/50"
                    }
                  `}
                  role="option"
                  aria-selected={selectedProject === project}
                >
                  <FolderOpen
                    size={14}
                    className={
                      selectedProject === project
                        ? "text-cyan-400"
                        : "text-slate-500"
                    }
                  />
                  <span className="truncate">{project}</span>
                </button>
              ))
            ) : projects.length > 0 ? (
              <div className="px-3 py-2 text-sm text-slate-500">
                No projects match "{searchQuery}"
              </div>
            ) : (
              <div className="px-3 py-2 text-sm text-slate-500">
                No projects indexed yet
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ProjectSelector;
