"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  DiagnosticStartResponse,
  DiagnosticResultResponse,
} from "@/lib/api/client";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
} from "lucide-react";

export default function DiagnosticPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [session, setSession] = useState<DiagnosticStartResponse | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<DiagnosticStartResponse["question"] | null>(null);
  const [progress, setProgress] = useState({ answered: 0, total: 15 });
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [result, setResult] = useState<DiagnosticResultResponse | null>(null);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [clientAttemptId, setClientAttemptId] = useState<string>(() => crypto.randomUUID());

  const startDiagnosticSession = useCallback(async () => {
    setLoading(true);
    setInitError(null);
    setSubmitError(null);
    setResult(null);
    setSelectedKey(null);

    try {
      const res = await api.startDiagnostic();
      setSession(res);
      setCurrentQuestion(res.question);
      setProgress(res.progress);
      setClientAttemptId(crypto.randomUUID());
      setStartTime(Date.now());
    } catch (err: unknown) {
      setSession(null);
      setCurrentQuestion(null);
      if (err instanceof ApiError) {
        setInitError(err.message || "Failed to start diagnostic assessment.");
      } else {
        setInitError("Unable to connect to learning server. Please verify your connection.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    startDiagnosticSession();
  }, [startDiagnosticSession]);

  const handleAnswerSubmit = async () => {
    if (!selectedKey || !session || !currentQuestion || submitting) return;

    setSubmitting(true);
    setSubmitError(null);
    const responseMs = Date.now() - startTime;

    try {
      const res = await api.submitDiagnosticAnswer(session.session_id, {
        client_attempt_id: clientAttemptId,
        question_id: currentQuestion.id,
        selected_key: selectedKey,
        response_ms: responseMs,
      });

      setSelectedKey(null);
      setProgress(res.progress);

      if (res.result) {
        setResult(res.result);
      } else if (res.next_question) {
        setCurrentQuestion(res.next_question);
        setClientAttemptId(crypto.randomUUID());
        setStartTime(Date.now());
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setSubmitError(err.message || "Failed to submit answer. You can retry submission.");
      } else {
        setSubmitError("Network connection error. Your selected answer is saved — click retry.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-mastery-emerald border-t-transparent" />
        <p className="text-xs font-mono text-ink-muted">Initializing adaptive diagnostic test...</p>
      </div>
    );
  }

  if (initError) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4">
        <div className="rounded-2xl border border-mastery-crimson/30 bg-surface p-8 shadow-subtle text-center space-y-4">
          <div className="h-12 w-12 mx-auto rounded-full bg-mastery-crimsonLight flex items-center justify-center text-mastery-crimson">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-ink-primary">
            Unable to Start Diagnostic Test
          </h2>
          <p className="text-xs text-ink-secondary max-w-md mx-auto">
            {initError}
          </p>
          <div className="pt-2 flex items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="px-4 py-2 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-secondary hover:bg-subtle transition"
            >
              Back to Study Map
            </Link>
            <button
              onClick={startDiagnosticSession}
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

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Exit to Study Map</span>
        </Link>

        {!result && (
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-ink-primary">
              Question {progress.answered + 1}
            </span>
            <span className="font-mono text-xs text-ink-muted">
              / {progress.total}
            </span>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-subtle h-2 rounded-full overflow-hidden">
        <div
          className="bg-mastery-emerald h-full transition-all duration-300"
          style={{ width: `${Math.min(100, (progress.answered / progress.total) * 100)}%` }}
        />
      </div>

      {/* Diagnostic In Progress Card */}
      {!result && currentQuestion && (
        <div className="rounded-2xl border border-border-subtle bg-surface p-6 sm:p-8 shadow-subtle space-y-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider">
                Adaptive Assessment
              </span>
              <span className="text-border-subtle">•</span>
              <span className="font-mono text-[10px] text-mastery-emerald">
                Level {currentQuestion.difficulty_bucket}
              </span>
            </div>
            <h2 className="font-serif text-lg sm:text-xl font-medium text-ink-primary leading-snug">
              {currentQuestion.stem}
            </h2>
          </div>

          {/* Options */}
          <div className="space-y-3">
            {currentQuestion.options.map((option) => (
              <button
                key={option.key}
                disabled={submitting}
                onClick={() => setSelectedKey(option.key)}
                className={`w-full text-left flex items-start gap-3.5 p-4 rounded-xl border transition-all ${
                  selectedKey === option.key
                    ? "border-ink-primary bg-subtle/80 text-ink-primary shadow-subtle"
                    : "border-border-subtle bg-surface hover:border-ink-muted text-ink-primary"
                }`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md font-mono text-xs font-semibold ${
                    selectedKey === option.key
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
            ))}
          </div>

          {/* Submission Error Banner */}
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

          {/* Submit Action */}
          <div className="flex items-center justify-end pt-2">
            <button
              disabled={!selectedKey || submitting}
              onClick={handleAnswerSubmit}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 disabled:opacity-40 transition shadow-subtle"
            >
              <span>{submitting ? "Processing..." : submitError ? "Retry Answer" : "Next Question"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Completed Results Summary */}
      {result && (
        <div className="rounded-2xl border border-border-subtle bg-surface p-6 sm:p-8 shadow-subtle space-y-6 animate-in fade-in duration-200">
          <div className="text-center space-y-2 pb-4 border-b border-border-subtle">
            <div className="h-12 w-12 mx-auto rounded-full bg-mastery-emeraldLight flex items-center justify-center text-mastery-emerald">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h2 className="font-serif text-2xl font-semibold text-ink-primary">
              Diagnostic Assessment Complete!
            </h2>
            <p className="text-xs sm:text-sm text-ink-secondary max-w-md mx-auto">
              Your baseline mastery profile has been established across all 20 CBSE Class 10 Biology concepts.
            </p>
          </div>

          {/* Weakest Concepts Attention Box */}
          {result.weakest.length > 0 && (
            <div className="rounded-xl border border-mastery-amber bg-mastery-amberLight p-4 space-y-1.5">
              <span className="font-mono text-[10px] text-mastery-amberText uppercase font-semibold block">
                Primary Opportunity Areas
              </span>
              <p className="text-xs text-ink-primary leading-relaxed">
                Initial uncertainty sampling identified high potential for revision in:{" "}
                <strong>
                  {result.weakest
                    .map((id) => {
                      const match = result.mastery.find((m) => m.concept_id === id);
                      return match ? match.concept_name : id;
                    })
                    .join(", ")}
                </strong>.
              </p>
            </div>
          )}

          {/* Detailed Baseline Mastery Breakdown (All 20 concepts) */}
          {result.mastery.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] uppercase tracking-wider text-ink-muted block">
                  Calibrated Syllabus Baseline ({result.mastery.length} Concepts)
                </span>
                <span className="text-[10px] font-mono text-ink-muted">
                  BKT Probability
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[380px] overflow-y-auto p-1">
                {result.mastery.map((item) => (
                  <div
                    key={item.concept_id}
                    className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-canvas/60 hover:border-earth-sand transition"
                  >
                    <span className="text-xs text-ink-primary font-medium truncate max-w-[190px]" title={item.concept_name}>
                      {item.concept_name}
                    </span>
                    <span
                      className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded ${
                        item.status === "untested"
                          ? "bg-canvas-warm text-ink-muted"
                          : item.p_mastery >= 0.75
                          ? "bg-mastery-emeraldLight text-mastery-emeraldText"
                          : item.p_mastery >= 0.5
                          ? "bg-mastery-amberLight text-mastery-amberText"
                          : "bg-mastery-crimsonLight text-mastery-crimsonText"
                      }`}
                    >
                      {item.status === "untested" ? "Untested" : `${Math.round(item.p_mastery * 100)}%`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-border-subtle">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto text-center px-5 py-2.5 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-primary hover:bg-subtle transition"
            >
              View Updated Concept Graph
            </Link>
            <button
              onClick={() => router.push(`/practice?concept=${result.recommended_next}`)}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-mastery-emerald text-canvas text-xs font-semibold hover:bg-mastery-emeraldText transition shadow-subtle"
            >
              <span>Begin Targeted Practice</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
