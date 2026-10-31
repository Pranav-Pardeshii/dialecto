"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError, PracticeNextResponse, PracticeAnswerResponse } from "@/lib/api/client";
import { VoiceFriendlyTextarea } from "@/components/ui/VoiceFriendlyTextarea";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  RotateCcw,
  AlertCircle,
} from "lucide-react";

export default function PracticePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-3xl mx-auto px-4 py-8">
          <div className="h-6 w-32 bg-canvas-warm rounded animate-pulse mb-6" />
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-8 shadow-card">
            <div className="h-4 w-48 bg-canvas-warm rounded animate-pulse mb-4" />
            <div className="h-16 w-full bg-canvas-warm rounded animate-pulse mb-6" />
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-12 bg-canvas-warm rounded-lg animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      }
    >
      <PracticeContent />
    </Suspense>
  );
}

function PracticeContent() {
  const searchParams = useSearchParams();
  const conceptParam = searchParams.get("concept");
  const modeParam = searchParams.get("mode");

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [sessionData, setSessionData] = useState<PracticeNextResponse | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [reasoningText, setReasoningText] = useState("");
  const [feedback, setFeedback] = useState<PracticeAnswerResponse | null>(null);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [clientAttemptId, setClientAttemptId] = useState<string>(() => crypto.randomUUID());

  const fetchNextQuestion = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    setSubmitError(null);
    setFeedback(null);
    setSelectedKey(null);
    setReasoningText("");

    try {
      const mode = modeParam === "review" ? "review" : conceptParam ? "concept" : "adaptive";
      const res = await api.getPracticeNext(mode, conceptParam || undefined);
      setSessionData(res);
      setClientAttemptId(crypto.randomUUID());
      setStartTime(Date.now());
    } catch (err: unknown) {
      setSessionData(null);
      if (err instanceof ApiError) {
        setFetchError(err.message || "Failed to load question from learning server.");
      } else {
        setFetchError("Unable to connect to the learning server. Please check your network connection.");
      }
    } finally {
      setLoading(false);
    }
  }, [conceptParam, modeParam]);

  useEffect(() => {
    fetchNextQuestion();
  }, [fetchNextQuestion]);

  const handleSubmit = async () => {
    if (!selectedKey || !sessionData || submitting) return;

    setSubmitting(true);
    setSubmitError(null);
    const responseMs = Date.now() - startTime;

    try {
      const res = await api.submitPracticeAnswer({
        client_attempt_id: clientAttemptId,
        session_id: sessionData.session_id,
        question_id: sessionData.question.id,
        selected_key: selectedKey,
        reasoning: reasoningText.trim().slice(0, 600) || undefined,
        response_ms: responseMs,
      });
      setFeedback(res);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setSubmitError(err.message || "Failed to evaluate answer. You can retry submission.");
      } else {
        setSubmitError("Network error while submitting answer. Your input is preserved — click below to retry.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-mastery-emerald border-t-transparent" />
        <p className="text-xs font-mono text-ink-muted">Selecting calibrated question...</p>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="rounded-2xl border border-mastery-crimson/30 bg-surface p-8 shadow-subtle text-center space-y-4">
          <div className="h-12 w-12 mx-auto rounded-full bg-mastery-crimsonLight flex items-center justify-center text-mastery-crimson">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-ink-primary">
            Unable to Load Practice Question
          </h2>
          <p className="text-xs text-ink-secondary max-w-md mx-auto">
            {fetchError}
          </p>
          <div className="pt-2 flex items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="px-4 py-2 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-secondary hover:bg-subtle transition"
            >
              Back to Study Map
            </Link>
            <button
              onClick={fetchNextQuestion}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-subtle"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const question = sessionData?.question;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Study Map</span>
        </Link>

        {sessionData?.selection_reason && (
          <div className="inline-flex items-center gap-1 text-[11px] font-mono text-ink-muted bg-subtle px-2.5 py-1 rounded-md">
            <HelpCircle className="h-3 w-3 text-mastery-emerald" />
            <span>{sessionData.selection_reason}</span>
          </div>
        )}
      </div>

      {/* Main Question Card */}
      {question && (
        <div className="rounded-2xl border border-border-subtle bg-surface p-6 sm:p-8 shadow-subtle space-y-6">
          {/* Question Stem */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider">
                Question
              </span>
              <span className="text-border-subtle">•</span>
              <span className="font-mono text-[10px] text-mastery-emerald">
                Level {question.difficulty_bucket}
              </span>
              {modeParam === "review" && (
                <>
                  <span className="text-border-subtle">•</span>
                  <span className="font-mono text-[10px] text-earth-amberText bg-earth-amber/15 px-2 py-0.5 rounded font-semibold">
                    Spaced Review
                  </span>
                </>
              )}
            </div>
            <h1 className="font-serif text-lg sm:text-xl font-medium text-ink-primary leading-snug">
              {question.stem}
            </h1>
          </div>

          {/* Options Grid */}
          <div className="space-y-3">
            {question.options.map((option) => {
              const isSelected = selectedKey === option.key;
              const isCorrectAnswer = feedback && feedback.correct_key === option.key;
              const isWrongChoice = feedback && !feedback.is_correct && isSelected;

              return (
                <button
                  key={option.key}
                  disabled={feedback !== null}
                  onClick={() => setSelectedKey(option.key)}
                  className={`w-full text-left flex items-start gap-3.5 p-4 rounded-xl border transition-all ${
                    isCorrectAnswer
                      ? "border-mastery-emerald bg-mastery-emeraldLight/70 text-mastery-emeraldText shadow-subtle"
                      : isWrongChoice
                      ? "border-mastery-crimson bg-mastery-crimsonLight text-mastery-crimsonText"
                      : isSelected
                      ? "border-ink-primary bg-subtle/70 text-ink-primary"
                      : "border-border-subtle bg-surface hover:border-ink-muted text-ink-primary"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md font-mono text-xs font-semibold ${
                      isCorrectAnswer
                        ? "bg-mastery-emerald text-canvas"
                        : isWrongChoice
                        ? "bg-mastery-crimson text-canvas"
                        : isSelected
                        ? "bg-ink-primary text-canvas"
                        : "bg-subtle text-ink-secondary"
                    }`}
                  >
                    {option.key}
                  </span>
                  <span className="text-xs sm:text-sm leading-relaxed mt-0.5">
                    {option.text}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Reasoning / Thinking Box */}
          {!feedback && (
            <div className="space-y-2 pt-2 border-t border-border-subtle">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-ink-primary">
                  Explain your reasoning (dictate or type)
                </span>
                <span className="text-[11px] text-ink-muted">
                  Max 600 characters • Helps identify misconceptions
                </span>
              </div>
              <VoiceFriendlyTextarea
                value={reasoningText}
                onChange={setReasoningText}
                onSubmit={handleSubmit}
                minRows={4}
                maxLength={600}
                placeholder="Speak out loud or type why you chose this answer..."
              />
            </div>
          )}

          {/* Inline Submission Error Alert */}
          {submitError && (
            <div className="rounded-xl border border-mastery-crimson/30 bg-mastery-crimsonLight p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-mastery-crimson shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-semibold text-mastery-crimsonText">
                  Submission Error
                </h4>
                <p className="text-xs text-ink-primary leading-relaxed">
                  {submitError}
                </p>
              </div>
            </div>
          )}

          {/* Post-Answer Feedback Reveal */}
          {feedback && (
            <div className="space-y-4 pt-4 border-t border-border-subtle animate-in fade-in duration-200">
              {/* Correctness & Explanation Banner */}
              <div
                className={`rounded-xl p-4 border ${
                  feedback.is_correct
                    ? "border-mastery-emerald bg-mastery-emeraldLight text-mastery-emeraldText"
                    : "border-mastery-crimson bg-mastery-crimsonLight text-mastery-crimsonText"
                }`}
              >
                <div className="flex items-center gap-2 font-semibold text-sm mb-1">
                  {feedback.is_correct ? (
                    <>
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Correct Answer!</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4" />
                      <span>Incorrect Choice</span>
                    </>
                  )}
                </div>
                <p className="text-xs leading-relaxed text-ink-primary">
                  {feedback.explanation}
                </p>
              </div>

              {/* Misconception Alert Card */}
              {feedback.misconception && (
                <div className="rounded-xl border border-mastery-amber bg-mastery-amberLight p-4 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-mastery-amberText">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Identified Biological Misconception</span>
                  </div>
                  <p className="text-xs font-medium text-ink-primary">
                    &ldquo;{feedback.misconception.statement}&rdquo;
                  </p>
                  <p className="text-xs text-ink-secondary bg-surface/80 p-2.5 rounded-lg border border-border-subtle leading-relaxed">
                    <strong>Correction:</strong> {feedback.misconception.correction}
                  </p>
                </div>
              )}

              {/* Animated Mastery Delta Banner */}
              <div className="flex items-center justify-between rounded-xl border border-border-subtle bg-canvas/60 p-4">
                <div className="flex flex-col">
                  <span className="font-mono text-[10px] text-ink-muted uppercase">
                    Bayesian Mastery Update
                  </span>
                  <div className="flex items-center gap-2 mt-0.5 font-mono">
                    <span className="text-sm font-semibold text-ink-secondary line-through">
                      {Math.round(feedback.mastery.before * 100)}%
                    </span>
                    <ArrowRight className="h-3.5 w-3.5 text-ink-muted" />
                    <span
                      className={`text-base font-bold ${
                        feedback.mastery.after >= feedback.mastery.before
                          ? "text-mastery-emerald"
                          : "text-mastery-crimson"
                      }`}
                    >
                      {Math.round(feedback.mastery.after * 100)}%
                    </span>
                    <span className="text-xs text-ink-muted">
                      ({feedback.mastery.status})
                    </span>
                  </div>
                </div>

                {feedback.newly_unlocked.length > 0 && (
                  <div className="text-right">
                    <span className="font-mono text-[10px] text-mastery-emerald font-semibold uppercase block">
                      Unlocked Next
                    </span>
                    <span className="text-xs font-medium text-ink-primary">
                      {feedback.newly_unlocked.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Submit / Continue Button */}
          <div className="flex items-center justify-end pt-2">
            {!feedback ? (
              <button
                disabled={!selectedKey || submitting}
                onClick={handleSubmit}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 disabled:opacity-40 transition shadow-subtle"
              >
                <span>{submitting ? "Evaluating..." : submitError ? "Retry Submission" : "Submit Answer"}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                onClick={fetchNextQuestion}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-mastery-emerald text-canvas text-xs font-semibold hover:bg-mastery-emeraldText transition shadow-subtle"
              >
                <span>Continue Practice</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
