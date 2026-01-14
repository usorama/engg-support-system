/**
 * ESS Chat Application - Main App Component
 *
 * Engineering Support System Chat Interface
 * A production-ready PWA for querying codebase intelligence.
 */

import { useCallback } from "react";
import { MessageSquare, Github } from "lucide-react";
import { ChatPanel } from "./components/ChatPanel";
import { ProjectSelector } from "./components/ProjectSelector";
import { HealthIndicator } from "./components/HealthIndicator";
import { useConversation } from "./hooks/useConversation";
import { useProjects } from "./hooks/useProjects";
import { useHealth } from "./hooks/useHealth";

/**
 * Main Application Component
 */
function App() {
  // Health monitoring
  const { health, isLoading: isHealthLoading, refresh: refreshHealth } = useHealth({
    pollInterval: 60000, // Check every minute
    autoStart: true,
  });

  // Project management
  const {
    projects,
    selectedProject,
    selectProject,
    isLoading: isProjectsLoading,
  } = useProjects();

  // Conversation management
  const {
    messages,
    conversationState,
    isLoading: isConversationLoading,
    error,
    sendQuery,
    answerClarifications,
    cancelConversation,
    submitFeedback,
    clearChat,
    retry,
  } = useConversation({
    defaultProject: selectedProject,
    synthesisMode: "synthesized",
  });

  // Handle query with project context
  const handleSendQuery = useCallback(
    (query: string) => {
      sendQuery(query, selectedProject);
    },
    [sendQuery, selectedProject]
  );

  // Determine if system is operational
  const isOperational = health?.status !== "unhealthy";

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50 glass-panel">
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <MessageSquare size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-100 leading-tight">
                ESS Chat
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block">
                Engineering Support System
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Project selector */}
          <ProjectSelector
            projects={projects}
            selectedProject={selectedProject}
            onSelect={selectProject}
            isLoading={isProjectsLoading}
            disabled={!isOperational}
          />

          {/* Health indicator */}
          <HealthIndicator
            health={health}
            isLoading={isHealthLoading}
            onRefresh={refreshHealth}
          />

          {/* GitHub link */}
          <a
            href="https://github.com/your-org/engg-support-system"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-colors hidden sm:flex"
            title="View on GitHub"
          >
            <Github size={20} />
          </a>
        </div>
      </header>

      {/* Offline/Unhealthy warning banner */}
      {!isOperational && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/30 flex items-center justify-center gap-2">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-sm text-red-300">
            System unavailable. Some services may be down.
          </span>
        </div>
      )}

      {/* Main chat area */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full max-w-4xl mx-auto">
          <ChatPanel
            messages={messages}
            isLoading={isConversationLoading}
            error={error}
            isConversationActive={conversationState.isActive}
            hasClarifications={conversationState.pendingClarifications !== null}
            onSendQuery={handleSendQuery}
            onAnswerClarifications={answerClarifications}
            onCancelConversation={cancelConversation}
            onFeedback={submitFeedback}
            onClearChat={clearChat}
            onRetry={retry}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="px-4 py-2 border-t border-slate-700/50 text-center">
        <p className="text-xs text-slate-600">
          Powered by Qdrant + Neo4j + zAI &bull; Evidence-based answers only
        </p>
      </footer>
    </div>
  );
}

export default App;
