/**
 * MarkdownContent - Renders markdown with custom components
 *
 * Provides consistent markdown rendering with syntax-highlighted
 * code blocks, styled lists, and proper link handling.
 */

import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { CodeBlock } from "./CodeBlock";

export interface MarkdownContentProps {
  /** Markdown content to render */
  content: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Custom components for ReactMarkdown
 */
const markdownComponents: Components = {
  // Code blocks with syntax highlighting
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    const isInline = !match && !className;

    if (isInline) {
      return (
        <code
          className="bg-slate-700/50 px-1.5 py-0.5 rounded text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      );
    }

    return (
      <CodeBlock
        code={String(children).replace(/\n$/, "")}
        language={match ? match[1] : undefined}
        showLineNumbers={false}
      />
    );
  },

  // Pre wrapper (handled by code component)
  pre({ children }) {
    return <>{children}</>;
  },

  // Headings
  h1({ children }) {
    return (
      <h1 className="text-xl font-bold mt-4 mb-2 text-slate-100">{children}</h1>
    );
  },
  h2({ children }) {
    return (
      <h2 className="text-lg font-semibold mt-3 mb-2 text-slate-100">
        {children}
      </h2>
    );
  },
  h3({ children }) {
    return (
      <h3 className="text-base font-semibold mt-3 mb-1 text-slate-200">
        {children}
      </h3>
    );
  },

  // Paragraphs
  p({ children }) {
    return <p className="mb-3 leading-relaxed">{children}</p>;
  },

  // Lists
  ul({ children }) {
    return <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>;
  },
  ol({ children }) {
    return (
      <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>
    );
  },
  li({ children }) {
    return <li className="text-slate-300">{children}</li>;
  },

  // Links
  a({ href, children }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
      >
        {children}
      </a>
    );
  },

  // Blockquotes
  blockquote({ children }) {
    return (
      <blockquote className="border-l-4 border-cyan-500 pl-4 my-3 text-slate-400 italic">
        {children}
      </blockquote>
    );
  },

  // Horizontal rule
  hr() {
    return <hr className="border-slate-600 my-4" />;
  },

  // Strong/Bold
  strong({ children }) {
    return <strong className="font-semibold text-slate-100">{children}</strong>;
  },

  // Emphasis/Italic
  em({ children }) {
    return <em className="italic text-slate-300">{children}</em>;
  },

  // Tables
  table({ children }) {
    return (
      <div className="overflow-x-auto my-3">
        <table className="min-w-full border border-slate-600 rounded">
          {children}
        </table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="bg-slate-700">{children}</thead>;
  },
  tbody({ children }) {
    return <tbody className="divide-y divide-slate-600">{children}</tbody>;
  },
  tr({ children }) {
    return <tr>{children}</tr>;
  },
  th({ children }) {
    return (
      <th className="px-4 py-2 text-left text-sm font-semibold text-slate-200">
        {children}
      </th>
    );
  },
  td({ children }) {
    return <td className="px-4 py-2 text-sm text-slate-300">{children}</td>;
  },
};

export function MarkdownContent({ content, className = "" }: MarkdownContentProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
    </div>
  );
}

export default MarkdownContent;
