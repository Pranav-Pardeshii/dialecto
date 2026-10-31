"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  X,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  BookOpen,
} from "lucide-react";
import { api, type TeachbackSessionStartResponse, type TeachbackTurnResponse } from "@/lib/api/client";
import { VoiceFriendlyTextarea } from "@/components/ui/VoiceFriendlyTextarea";
import type { CellItem, OrganelleItem } from "@/data/cells";

export interface PipTeachSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
  cell: CellItem;
  organelle: OrganelleItem;
  conceptId?: string;
}

interface MessageTurn {
  role: "pip" | "learner";
  content: string;
  level?: number;
  score?: number;
  covered?: string[];
  missing?: string[];
}

export function PipTeachSlideOver({
  isOpen,
  onClose,
  cell,
  organelle,
  conceptId = "lp-photosynthesis",
}: PipTeachSlideOverProps) {
  const [session, setSession] = useState<TeachbackSessionStartResponse | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [messages, setMessages] = useState<MessageTurn[]>([]);
  const [currentLevel, setCurrentLevel] = useState<number>(0);
  const [coveredPoints, setCoveredPoints] = useState<Set<string>>(new Set());
  const [isFinished, setIsFinished] = useState(false);
  const [fallbackToast, setFallbackToast] = useState(false);

  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Initialize or resume Teachback session when slide-over opens
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setIsLoadingSession(true);
    setSessionError(null);
    setInputText("");
    setIsFinished(false);

    api
      .startTeachback(conceptId)
      .then((startData) => {
        if (!isMounted) return;
        setSession(startData);
        setCurrentLevel(startData.pip.level);
        setIsFinished(startData.finished);

        // Customize Pip's opening prompt specifically for this selected organelle
        const customizedPrompt = `I can see the ${organelle.name} highlighted in this ${cell.name}! ${organelle.note} Could you teach me how it actually works and why the cell depends on it?`;

        setMessages([
          {
            role: "pip",
            content: customizedPrompt,
            level: startData.pip.level,
          },
        ]);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.warn("Teachback session initialization failed:", err);
        setSessionError(err instanceof Error ? err.message : "Unable to connect with Pip.");
      })
      .finally(() => {
        if (isMounted) setIsLoadingSession(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, conceptId, cell.name, organelle.name, organelle.note]);

  // Scroll transcript to bottom on new turns
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  const handleSubmitExplanation = async () => {
    if (!inputText.trim() || isSubmitting || !session) return;

    const learnerContent = inputText.trim();
    setInputText("");
    setIsSubmitting(true);
    setSessionError(null);

    // Optimistically add learner turn to transcript
    setMessages((prev) => [...prev, { role: "learner", content: learnerContent }]);

    try {
      const res: TeachbackTurnResponse = await api.submitTeachbackTurn(session.id, learnerContent);

      if (res.ai?.fallback) {
        setFallbackToast(true);
      }

      setCurrentLevel(res.pip.level);
      if (res.finished) {
        setIsFinished(true);
      }

      // Track newly covered rubric points
      if (res.feedback?.covered) {
        setCoveredPoints((prev) => {
          const next = new Set(prev);
          res.feedback.covered.forEach((pt: string) => next.add(pt));
          return next;
        });
      }

      // Append Pip's evaluation turn
      setMessages((prev) => [
        ...prev,
        {
          role: "pip",
          content: res.pip.content,
          level: res.pip.level,
          score: res.feedback?.score,
          covered: res.feedback?.covered,
          missing: res.feedback?.missing,
        },
      ]);
    } catch (err) {
      console.error("Turn submission error:", err);
      setSessionError("Failed to evaluate explanation. Your draft is preserved below.");
      setInputText(learnerContent);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const levelBadges = [
    { label: "Level 0: Confused", mood: "Needs basic mechanism", color: "bg-amber-100 text-amber-900 border-amber-300" },
    { label: "Level 1: Curious", mood: "Asking key questions", color: "bg-blue-100 text-blue-900 border-blue-300" },
    { label: "Level 2: Connecting Dots", mood: "Grasping process", color: "bg-emerald-100 text-emerald-900 border-emerald-300" },
    { label: "Level 3: Mastered!", mood: "Full biological clarity", color: "bg-emerald-600 text-white border-emerald-700 font-semibold" },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Dimmed backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-Over Drawer */}
      <div className="relative w-full max-w-xl bg-surface border-l border-border-subtle shadow-2xl flex flex-col h-full z-10 animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="px-5 py-4 border-b border-border-subtle bg-canvas/60 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-100 border border-emerald-200 text-emerald-800 font-serif font-bold text-base flex items-center justify-center shrink-0">
              Pip
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-ink-primary font-display leading-tight">
                  Teach Pip: {organelle.name}
                </h2>
                <span
                  className="w-2.5 h-2.5 rounded-full inline-block shrink-0 ring-1 ring-border-subtle"
                  style={{ backgroundColor: organelle.color }}
                  title={`${organelle.name} color indicator`}
                />
              </div>
              <p className="text-xs text-ink-secondary">
                {cell.name} • {organelle.subtitle || "Cellular Structure"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-ink-muted hover:text-ink-primary hover:bg-subtle transition-colors"
            title="Close dialog (Escape)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Fallback Toast */}
        {fallbackToast && (
          <div className="px-4 py-2 bg-amber-50 border-b border-amber-200 text-amber-900 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
            <span>Tutor is busy, using backup evaluation model.</span>
          </div>
        )}

        {/* Pip Comprehension Level Banner */}
        <div className="px-5 py-3 border-b border-border-subtle bg-subtle/40 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-ink-secondary flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Pip&apos;s Understanding:</span>
            </span>
            <span className={`px-2 py-0.5 rounded text-[11px] border ${levelBadges[currentLevel]?.color || ""}`}>
              {levelBadges[currentLevel]?.label || `Level ${currentLevel}`}
            </span>
          </div>

          {/* Progress Segment Bar */}
          <div className="w-full bg-border-subtle/60 h-2 rounded-full overflow-hidden flex gap-1 p-0.5">
            {[0, 1, 2, 3].map((lvl) => (
              <div
                key={lvl}
                className={`flex-1 h-full rounded-full transition-all duration-500 ${
                  lvl <= currentLevel
                    ? lvl === 3
                      ? "bg-emerald-600"
                      : "bg-emerald-500"
                    : "bg-transparent"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Transcript Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {isLoadingSession && (
            <div className="flex flex-col items-center justify-center h-48 gap-3 text-ink-secondary">
              <div className="w-6 h-6 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin" />
              <p className="text-xs">Preparing Pip&apos;s study context...</p>
            </div>
          )}

          {sessionError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold mb-0.5">Connection Notice</p>
                <p>{sessionError}</p>
              </div>
            </div>
          )}

          {/* Conversation Turns */}
          {messages.map((turn, index) => (
            <div
              key={index}
              className={`flex flex-col gap-1.5 ${
                turn.role === "learner" ? "items-end" : "items-start"
              }`}
            >
              <div className="flex items-center gap-1.5 text-[11px] text-ink-muted">
                {turn.role === "pip" ? (
                  <>
                    <span className="font-semibold text-emerald-800">Pip</span>
                    <span>• {turn.level !== undefined ? levelBadges[turn.level]?.mood : "Peer"}</span>
                  </>
                ) : (
                  <span className="font-semibold text-ink-primary">You (Teacher)</span>
                )}
              </div>

              <div
                className={`max-w-[88%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-xs ${
                  turn.role === "learner"
                    ? "bg-emerald-700 text-white rounded-br-xs"
                    : "bg-canvas border border-border-subtle text-ink-primary rounded-bl-xs"
                }`}
              >
                <p className="whitespace-pre-wrap">{turn.content}</p>

                {/* Rubric feedback badges if present */}
                {turn.role === "pip" && turn.covered && turn.covered.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-border-subtle/40 flex flex-wrap gap-1">
                    {turn.covered.map((pt, pIdx) => (
                      <span
                        key={pIdx}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 text-[10px] font-medium border border-emerald-200"
                      >
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        {pt}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isSubmitting && (
            <div className="flex items-start gap-2">
              <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-serif text-xs font-bold shrink-0">
                Pip
              </div>
              <div className="bg-canvas border border-border-subtle rounded-2xl rounded-bl-xs p-3 text-xs text-ink-secondary flex items-center gap-2">
                <div className="w-4 h-4 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin" />
                <span>Pip is reflecting on your explanation...</span>
              </div>
            </div>
          )}

          <div ref={transcriptEndRef} />
        </div>

        {/* Rubric Targets Checklist (Collapsible / Compact) */}
        {session?.rubric?.key_points && (
          <div className="px-5 py-2.5 bg-subtle/30 border-t border-border-subtle text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-ink-primary text-[11px] flex items-center gap-1">
                <BookOpen className="w-3 h-3 text-emerald-700" />
                Key Concepts to Teach:
              </span>
              <span className="text-[10px] text-ink-muted">
                {coveredPoints.size} of {session.rubric.key_points.length} grasped
              </span>
            </div>
            <ul className="space-y-1 text-[11px] text-ink-secondary">
              {session.rubric.key_points.slice(0, 3).map((point, idx) => {
                const isCovered = coveredPoints.has(point);
                return (
                  <li key={idx} className="flex items-start gap-1.5">
                    {isCovered ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-border-subtle shrink-0 mt-0.5" />
                    )}
                    <span className={isCovered ? "line-through text-ink-muted" : ""}>{point}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Teaching Input Footer */}
        <div className="p-4 border-t border-border-subtle bg-surface flex flex-col gap-2">
          {isFinished ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-center flex flex-col items-center gap-2">
              <Sparkles className="w-6 h-6 text-emerald-600" />
              <h4 className="text-sm font-semibold text-emerald-950 font-display">
                Pip Fully Understands!
              </h4>
              <p className="text-xs text-emerald-800 max-w-sm">
                You&apos;ve demonstrated mastery of {organelle.name} in the {cell.name}. Your learner model mastery has been updated.
              </p>
              <button
                onClick={onClose}
                className="mt-1 px-4 py-2 bg-emerald-700 text-white rounded-lg text-xs font-semibold hover:bg-emerald-800 transition-colors shadow-xs"
              >
                Return to 3D Biology Lab
              </button>
            </div>
          ) : (
            <>
              <VoiceFriendlyTextarea
                value={inputText}
                onChange={setInputText}
                onSubmit={handleSubmitExplanation}
                placeholder={`Explain ${organelle.name} in plain words. What does it do for this cell?`}
                disabled={isSubmitting || isLoadingSession}
                minRows={4}
                autoFocus
                helperText="Type your scientific explanation or use dictation. Press Ctrl+Enter to teach Pip."
              />

              <div className="flex items-center justify-between gap-2 pt-1">
                <span className="text-[11px] text-ink-muted">
                  Ctrl+Enter sends explanation
                </span>

                <button
                  onClick={handleSubmitExplanation}
                  disabled={!inputText.trim() || isSubmitting || isLoadingSession}
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-xs"
                >
                  <span>Teach Pip</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
