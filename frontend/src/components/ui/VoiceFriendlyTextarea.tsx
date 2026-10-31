"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import { Mic, Square, Loader2, AlertCircle } from "lucide-react";
import { getActiveDemoUserId } from "@/lib/api/client";

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
  helperText = "Press your dictation key or click the mic to speak naturally.",
}: VoiceFriendlyTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const latestValueRef = useRef<string>(value);
  const autoStopTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Keep latest value reference current to prevent stale closure overwrites
  useEffect(() => {
    latestValueRef.current = value;
  }, [value]);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Clean up recording tracks and timers on unmount
  useEffect(() => {
    return () => {
      if (autoStopTimeoutRef.current) {
        clearTimeout(autoStopTimeoutRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

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

  const stopActiveRecording = useCallback(() => {
    if (autoStopTimeoutRef.current) {
      clearTimeout(autoStopTimeoutRef.current);
      autoStopTimeoutRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const toggleRecording = async () => {
    setErrorMessage(null);

    if (isRecording) {
      stopActiveRecording();
    } else {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setErrorMessage("Voice recording is not supported in this browser.");
          return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;

        // Detect supported MIME type
        let selectedMimeType = "audio/webm";
        let extension = "webm";

        if (typeof MediaRecorder.isTypeSupported === "function") {
          if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            selectedMimeType = "audio/webm;codecs=opus";
            extension = "webm";
          } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
            selectedMimeType = "audio/mp4";
            extension = "mp4";
          } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
            selectedMimeType = "audio/ogg";
            extension = "ogg";
          }
        }

        const recorder = new MediaRecorder(stream, { mimeType: selectedMimeType });
        mediaRecorderRef.current = recorder;
        audioChunksRef.current = [];

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        recorder.onstop = async () => {
          // Release microphone tracks immediately
          stream.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;

          if (audioChunksRef.current.length === 0) return;

          const audioBlob = new Blob(audioChunksRef.current, { type: selectedMimeType });
          if (audioBlob.size > 5 * 1024 * 1024) {
            setErrorMessage("Audio recording exceeded 5 MB limit. Please record a shorter explanation.");
            return;
          }

          setIsTranscribing(true);

          try {
            const formData = new FormData();
            formData.append("audio", audioBlob, `recording.${extension}`);

            const userId = getActiveDemoUserId();
            const res = await fetch("/api/v1/speech/transcriptions", {
              method: "POST",
              headers: {
                "X-Demo-User-Id": userId.toString(),
              },
              body: formData,
            });

            if (res.ok) {
              const data = await res.json();
              if (data.text) {
                const currentText = latestValueRef.current;
                const updated = currentText
                  ? `${currentText.trim()} ${data.text.trim()}`
                  : data.text.trim();
                onChange(updated);
              }
            } else {
              const errorData = await res.json().catch(() => ({}));
              setErrorMessage(
                errorData?.error?.message || "Speech transcription failed. You can continue typing directly."
              );
            }
          } catch {
            setErrorMessage("Could not reach speech transcription service. Please type your explanation.");
          } finally {
            setIsTranscribing(false);
          }
        };

        recorder.start();
        setIsRecording(true);

        // Auto-stop after 60 seconds to protect network and memory
        autoStopTimeoutRef.current = setTimeout(() => {
          if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            stopActiveRecording();
          }
        }, 60000);
      } catch (err: unknown) {
        setIsRecording(false);
        const error = err as Error;
        if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
          setErrorMessage("Microphone access was denied. Please allow microphone permissions or type your answer.");
        } else {
          setErrorMessage("Failed to start voice input. Please type your response.");
        }
      }
    }
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
        disabled={disabled || isTranscribing}
        rows={minRows}
        maxLength={maxLength}
        className="w-full resize-y rounded-t-xl bg-transparent px-4 py-3.5 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none disabled:opacity-50 leading-relaxed font-sans"
      />

      {errorMessage && (
        <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-mastery-crimsonLight text-mastery-crimsonText text-xs border-t border-mastery-crimson/20">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Tray with helper, mic toggle, and word counter */}
      <div className="flex items-center justify-between border-t border-border-subtle/70 bg-canvas/40 px-3.5 py-2 text-[11px] text-ink-muted rounded-b-xl select-none">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleRecording}
            disabled={disabled || isTranscribing}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-md transition ${
              isRecording
                ? "bg-red-50 text-red-600 font-semibold animate-pulse border border-red-200"
                : isTranscribing
                ? "bg-canvas-warm text-ink-muted"
                : "text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm/80"
            }`}
          >
            {isTranscribing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : isRecording ? (
              <Square className="h-3 w-3 fill-current" />
            ) : (
              <Mic className="h-3.5 w-3.5 text-mastery-emerald" />
            )}
            <span>
              {isTranscribing
                ? "Transcribing voice..."
                : isRecording
                ? "Recording... click to finish"
                : "Record Voice"}
            </span>
          </button>
          <span className="hidden md:inline-block text-ink-muted text-[10px]">•</span>
          <span className="hidden md:inline-block text-[10px] text-ink-muted">{helperText}</span>
        </div>

        <div className="flex items-center gap-3 font-mono">
          <span>
            {wordCount} {wordCount === 1 ? "word" : "words"}
          </span>
          <span className="text-border-subtle">•</span>
          <span className={maxLength && charCount >= maxLength ? "text-mastery-crimson font-bold" : ""}>
            {charCount}
            {maxLength ? `/${maxLength}` : ""} chars
          </span>
          <span className="hidden sm:inline-block text-border-subtle">•</span>
          <span className="hidden sm:inline-block text-[10px] text-ink-muted">
            <kbd className="rounded border border-border-subtle bg-surface px-1 py-0.5 text-[10px]">Ctrl</kbd> +{" "}
            <kbd className="rounded border border-border-subtle bg-surface px-1 py-0.5 text-[10px]">Enter</kbd> to submit
          </span>
        </div>
      </div>
    </div>
  );
}
