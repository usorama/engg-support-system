/**
 * ChatInput - Message input component
 *
 * Provides a text input with send button, keyboard shortcuts,
 * and auto-resize functionality.
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { Send, Loader2, StopCircle } from "lucide-react";

export interface ChatInputProps {
  /** Callback when message is submitted */
  onSubmit: (message: string) => void;
  /** Callback when input is cancelled (e.g., during conversation) */
  onCancel?: () => void;
  /** Placeholder text */
  placeholder?: string;
  /** Whether submission is in progress */
  isLoading?: boolean;
  /** Whether we're in a conversation that can be cancelled */
  canCancel?: boolean;
  /** Disabled state */
  disabled?: boolean;
}

export function ChatInput({
  onSubmit,
  onCancel,
  placeholder = "Ask about your codebase...",
  isLoading = false,
  canCancel = false,
  disabled = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [value]);

  // Focus input on mount
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isLoading || disabled) return;

    onSubmit(trimmed);
    setValue("");

    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isLoading, disabled, onSubmit]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      // Submit on Enter (without Shift)
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
      }

      // Cancel on Escape if in conversation
      if (event.key === "Escape" && canCancel && onCancel) {
        onCancel();
      }
    },
    [handleSubmit, canCancel, onCancel]
  );

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      setValue(event.target.value);
    },
    []
  );

  const canSubmit = value.trim().length > 0 && !isLoading && !disabled;

  return (
    <div className="relative">
      <div className="flex items-end gap-2 p-2 bg-slate-800/50 rounded-2xl border border-slate-600/50 focus-within:border-cyan-500/50 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all">
        {/* Text input */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 resize-none focus:outline-none py-2 px-3 text-sm leading-relaxed disabled:opacity-50"
          style={{ maxHeight: "200px" }}
        />

        {/* Action buttons */}
        <div className="flex items-center gap-1 pb-1">
          {/* Cancel button (when in conversation) */}
          {canCancel && onCancel && (
            <button
              onClick={onCancel}
              className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-colors"
              title="Cancel conversation (Esc)"
            >
              <StopCircle size={20} />
            </button>
          )}

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`
              p-2 rounded-xl transition-all
              ${
                canSubmit
                  ? "bg-cyan-500 hover:bg-cyan-400 text-white"
                  : "bg-slate-700 text-slate-500 cursor-not-allowed"
              }
            `}
            title={canSubmit ? "Send message (Enter)" : "Type a message to send"}
          >
            {isLoading ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>
      </div>

      {/* Keyboard hints */}
      <div className="flex justify-between mt-1 px-3 text-xs text-slate-600">
        <span>
          Press <kbd className="px-1 py-0.5 bg-slate-800 rounded">Enter</kbd> to
          send
        </span>
        <span>
          <kbd className="px-1 py-0.5 bg-slate-800 rounded">Shift+Enter</kbd>{" "}
          for new line
        </span>
      </div>
    </div>
  );
}

export default ChatInput;
