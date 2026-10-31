"use client";

import React, { useEffect, useRef, useState } from "react";
import { Mic, Send, AlertCircle, Loader2, Volume2 } from "lucide-react";

interface WisprCommandInputProps {
  onSubmit: (text: string) => Promise<void> | void;
  placeholder?: string;
  multiline?: boolean;
  minRows?: number;
  autoFocus?: boolean;
  disabled?: boolean;
  label?: string;
  helperText?: string;
  className?: string;
  buttonLabel?: string;
}

export function WisprCommandInput({
  onSubmit,
  placeholder = "Speak naturally or type your command here...",
  multiline = false,
  minRows = 3,
  autoFocus = false,
  disabled = false,
  label,
  helperText,
  className = "",
  buttonLabel = "Submit",
}: WisprCommandInputProps) {
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);

  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || isSubmitting || disabled) return;

    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(trimmed);
      setValue("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed. Your text has been preserved.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (multiline) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      }
    } else {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    }
  };

  // Optional in-browser microphone fallback
  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mr.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (audioBlob.size === 0) return;

        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.webm");
          const res = await fetch("/api/v1/speech/transcriptions", {
            method: "POST",
            body: formData,
            headers: {
              "X-Demo-User-Id": "1",
            },
          });
          if (res.ok) {
            const data = await res.json();
            if (data.text) {
              setValue((prev) => (prev ? `${prev} ${data.text}` : data.text));
            }
          }
        } catch {
          setError("Voice transcription was unable to process audio. You can continue typing.");
        } finally {
          setIsTranscribing(false);
        }
      };

      mr.start();
      setIsRecording(true);
    } catch {
      setError("Microphone access was not permitted. Please type your message.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <label className="text-xs font-medium text-ink-secondary flex items-center justify-between">
          <span>{label}</span>
          <span className="inline-flex items-center gap-1 text-[11px] text-ink-muted">
            <Mic className="w-3 h-3 text-emerald-600" />
            Dictation ready
          </span>
        </label>
      )}

      <div className="relative rounded-lg border border-border-subtle bg-surface focus-within:border-emerald-600 focus-within:ring-1 focus-within:ring-emerald-600 transition-all shadow-sm">
        {multiline ? (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={minRows}
            disabled={disabled || isSubmitting}
            placeholder={placeholder}
            aria-label={label || "Voice and text input"}
            className="w-full px-3 py-2.5 text-sm bg-transparent resize-y rounded-t-lg outline-none placeholder:text-ink-muted text-ink-primary font-normal leading-relaxed"
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isSubmitting}
            placeholder={placeholder}
            aria-label={label || "Voice and text input"}
            className="w-full px-3 py-2.5 text-sm bg-transparent outline-none placeholder:text-ink-muted text-ink-primary font-normal"
          />
        )}

        {/* Action tray */}
        <div className="flex items-center justify-between px-3 py-1.5 border-t border-border-subtle/60 bg-subtle/50 rounded-b-lg">
          <div className="flex items-center gap-2 text-xs text-ink-secondary">
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              disabled={disabled || isSubmitting || isTranscribing}
              title={isRecording ? "Stop voice recording" : "Use microphone"}
              className={`p-1.5 rounded-md transition-colors flex items-center gap-1.5 text-xs ${
                isRecording
                  ? "bg-red-50 text-red-600 border border-red-200 animate-pulse"
                  : "hover:bg-surface text-ink-secondary hover:text-ink-primary"
              }`}
            >
              {isTranscribing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
              ) : isRecording ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
                  <span>Listening...</span>
                </>
              ) : (
                <>
                  <Mic className="w-3.5 h-3.5" />
                  <span>Mic</span>
                </>
              )}
            </button>
            <span className="text-[11px] text-ink-muted hidden sm:inline">
              {multiline ? "Press Ctrl+Enter to send" : "Press Enter to submit"}
            </span>
          </div>

          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={!value.trim() || isSubmitting || disabled}
            className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-white bg-emerald-700 hover:bg-emerald-800 disabled:opacity-40 disabled:hover:bg-emerald-700 rounded-md transition-all shadow-sm"
          >
            {isSubmitting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            <span>{buttonLabel}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-1.5 text-xs text-red-600 mt-0.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {helperText && !error && (
        <p className="text-[11px] text-ink-muted flex items-center gap-1">
          <Volume2 className="w-3 h-3" />
          {helperText}
        </p>
      )}
    </div>
  );
}

