"use client";

import React, { useRef, useEffect } from "react";
import { Mic } from "lucide-react";

interface VoiceFriendlyTextareaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  minRows?: number;
  maxLength?: number;
  autoFocus?: boolean;
  helperText?: string;
}

export function VoiceFriendlyTextarea({
  value,
  onChange,
  onSubmit,
  placeholder = "Speak out loud or type your explanation here...",
  disabled = false,
  minRows = 8,
  maxLength,
  autoFocus = false,
  helperText = "Press your dictation key to speak naturally, or type directly.",
}: VoiceFriendlyTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Enter or Cmd+Enter submits
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (onSubmit && !disabled && value.trim().length > 0) {
        onSubmit();
      }
    }
    // Normal Enter inserts a newline naturally - DO NOT INTERCEPT
  };

  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const charCount = value.length;

  return (
    <div className="relative w-full flex flex-col rounded-xl border border-border-subtle bg-surface shadow-subtle focus-within:border-ink-primary focus-within:ring-1 focus-within:ring-ink-primary/20 transition-all">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={minRows}
        maxLength={maxLength}
        className="w-full resize-y rounded-t-xl bg-transparent px-4 py-3.5 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none disabled:opacity-50 leading-relaxed font-sans"
      />

      {/* Tray with helper and word counter */}
      <div className="flex items-center justify-between border-t border-border-subtle/70 bg-canvas/40 px-3.5 py-2 text-[11px] text-ink-muted rounded-b-xl select-none">
        <div className="flex items-center gap-2">
          <Mic className="h-3.5 w-3.5 text-mastery-emerald animate-pulse" />
          <span>{helperText}</span>
        </div>

        <div className="flex items-center gap-3 font-mono">
          <span>{wordCount} {wordCount === 1 ? "word" : "words"}</span>
          <span className="text-border-subtle">•</span>
          <span>{charCount} chars</span>
          <span className="hidden sm:inline-block text-border-subtle">•</span>
          <span className="hidden sm:inline-block text-[10px] text-ink-muted">
            <kbd className="rounded border border-border-subtle bg-surface px-1 py-0.5 text-[10px]">Ctrl</kbd> + <kbd className="rounded border border-border-subtle bg-surface px-1 py-0.5 text-[10px]">Enter</kbd> to submit
          </span>
        </div>
      </div>
    </div>
  );
}
