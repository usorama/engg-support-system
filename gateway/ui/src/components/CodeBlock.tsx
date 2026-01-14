/**
 * CodeBlock - Syntax highlighted code display
 *
 * Renders code blocks with syntax highlighting, copy functionality,
 * and line number display.
 */

import { useState, useCallback } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check, FileCode } from "lucide-react";

export interface CodeBlockProps {
  /** Code content to display */
  code: string;
  /** Programming language for syntax highlighting */
  language?: string;
  /** Source file path */
  source?: string;
  /** Starting line number */
  lineStart?: number;
  /** Ending line number */
  lineEnd?: number;
  /** Show line numbers */
  showLineNumbers?: boolean;
  /** Max height before scroll */
  maxHeight?: string;
}

/**
 * Map common language aliases to their highlighting key
 */
function normalizeLanguage(lang?: string): string {
  if (!lang) return "plaintext";

  const languageMap: Record<string, string> = {
    ts: "typescript",
    tsx: "tsx",
    js: "javascript",
    jsx: "jsx",
    py: "python",
    rb: "ruby",
    md: "markdown",
    yml: "yaml",
    sh: "bash",
    shell: "bash",
    json: "json",
    sql: "sql",
    css: "css",
    html: "html",
    go: "go",
    rust: "rust",
    java: "java",
    c: "c",
    cpp: "cpp",
    cs: "csharp",
  };

  const normalized = lang.toLowerCase();
  return languageMap[normalized] || normalized;
}

export function CodeBlock({
  code,
  language,
  source,
  lineStart,
  lineEnd,
  showLineNumbers = true,
  maxHeight = "400px",
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [code]);

  const normalizedLang = normalizeLanguage(language);

  // Format line range display
  const lineRange =
    lineStart !== undefined
      ? lineEnd !== undefined && lineEnd !== lineStart
        ? `L${lineStart}-${lineEnd}`
        : `L${lineStart}`
      : null;

  return (
    <div className="code-block rounded-lg overflow-hidden border border-slate-700 my-3">
      {/* Header with source info and copy button */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2 text-sm text-slate-400 overflow-hidden">
          <FileCode size={14} className="flex-shrink-0" />
          {source && (
            <span className="truncate max-w-xs" title={source}>
              {source}
            </span>
          )}
          {lineRange && (
            <span className="text-slate-500 flex-shrink-0">{lineRange}</span>
          )}
          {!source && normalizedLang !== "plaintext" && (
            <span className="text-slate-500">{normalizedLang}</span>
          )}
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
          aria-label={copied ? "Copied!" : "Copy code"}
        >
          {copied ? (
            <>
              <Check size={14} className="text-green-400" />
              <span className="text-green-400">Copied</span>
            </>
          ) : (
            <>
              <Copy size={14} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code content with syntax highlighting */}
      <div
        className="overflow-auto"
        style={{ maxHeight }}
      >
        <SyntaxHighlighter
          language={normalizedLang}
          style={vscDarkPlus}
          showLineNumbers={showLineNumbers}
          startingLineNumber={lineStart || 1}
          customStyle={{
            margin: 0,
            padding: "1rem",
            background: "transparent",
            fontSize: "0.875rem",
            lineHeight: 1.5,
          }}
          lineNumberStyle={{
            minWidth: "2.5em",
            paddingRight: "1em",
            color: "#4a5568",
            userSelect: "none",
          }}
          codeTagProps={{
            style: {
              fontFamily:
                'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
            },
          }}
        >
          {code.trim()}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

export default CodeBlock;
