"use client";

import { useEffect, useState, useRef, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  TeachbackSessionStartResponse,
  TeachbackTurnResponse,
} from "@/lib/api/client";
import { VoiceFriendlyTextarea } from "@/components/ui/VoiceFriendlyTextarea";
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  Award,
  RotateCcw,
  AlertTriangle,
  Lightbulb,
} from "lucide-react";

interface TurnMessage {
  role: "pip" | "learner";
  content: string;
  level?: number;
  score?: number;
  covered?: string[];
  missing?: string[];
  misconceptions?: { id: string; statement: string }[];
}

export default function TeachbackPage({
  params,
}: {
  params: Promise<{ conceptId: string }>;
}) {
  const resolvedParams = use(params);
  const conceptId = resolvedParams.conceptId;
  const router = useRouter();

  const [session, setSession] = useState<TeachbackSessionStartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [turnError, setTurnError] = useState<string | null>(null);

  const [inputText, setInputText] = useState("");
  const [messages, setMessages] = useState<TurnMessage[]>([]);
  const [currentLevel, setCurrentLevel] = useState<number>(0);
  const [coveredPoints, setCoveredPoints] = useState<Set<string>>(new Set());
  const [finished, setFinished] = useState(false);
  const [finalResult, setFinalResult] = useState<TeachbackTurnResponse["result"] | null>(null);
  const [fallbackToast, setFallbackToast] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcript on new messages or thinking states
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, submitting]);

  const initSession = async () => {
    setLoading(true);
    setInitError(null);
    setTurnError(null);

    try {
      // Check if we can resume an existing session from storage
      const storageKey = `dialecto_teachback_${conceptId}`;
      const savedSessionId = typeof window !== "undefined" ? sessionStorage.getItem(storageKey) : null;

      if (savedSessionId) {
        try {
          const detail = await api.getTeachbackSession(Number(savedSessionId));
          if (detail && detail.concept_id === conceptId) {
            // Restore session
            setCurrentLevel(detail.current_level);
            setFinished(detail.finished);

            const restoredMessages: TurnMessage[] = detail.turns.map((t) => ({
              role: t.role === "learner" ? "learner" : "pip",
              content: t.content,
              level: t.level ?? undefined,
            }));

            setMessages(restoredMessages);

            // Fetch start session info to populate rubric
            const startData = await api.startTeachback(conceptId);
            setSession({
              ...startData,
              id: detail.id,
              turn_count: detail.turn_count,
              finished: detail.finished,
              pip: {
                content: restoredMessages[restoredMessages.length - 1]?.content || startData.pip.content,
                level: detail.current_level,
              },
            });
            setLoading(false);
            return;
          }
        } catch {
          // If restoring failed, continue to start a fresh session
          sessionStorage.removeItem(storageKey);
        }
      }

      // Start fresh session
      const startData = await api.startTeachback(conceptId);
      setSession(startData);
      setCurrentLevel(startData.pip.level);
      setFinished(startData.finished);
      setMessages([
        {
          role: "pip",
          content: startData.pip.content,
          level: startData.pip.level,
        },
      ]);
      if (typeof window !== "undefined") {
        sessionStorage.setItem(storageKey, String(startData.id));
      }
    } catch (err: unknown) {
      setSession(null);
      if (err instanceof ApiError) {
        setInitError(err.message || "Failed to initialize teach-back session.");
      } else {
        setInitError("Unable to connect to the learning server. Please check your connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conceptId]);

  const handleSubmit = async () => {
    if (!inputText.trim() || !session || submitting || finished) return;

    const userText = inputText.trim();
    setSubmitting(true);
    setTurnError(null);

    // Optimistically show user message
    const tempLearnerMsg: TurnMessage = { role: "learner", content: userText };
    setMessages((prev) => [...prev, tempLearnerMsg]);

    try {
      const turnResp = await api.submitTeachbackTurn(session.id, userText);
      setCurrentLevel(turnResp.pip.level);
      setInputText(""); // Clear input only after successful submission

      if (turnResp.ai?.fallback) {
        setFallbackToast(true);
        setTimeout(() => setFallbackToast(false), 5000);
      }

      // Track newly covered points
      if (turnResp.feedback.covered) {
        setCoveredPoints((prev) => {
          const updated = new Set(prev);
          turnResp.feedback.covered.forEach((pt) => updated.add(pt));
          return updated;
        });
      }

      // Add Pip's response
      setMessages((prev) => [
        ...prev,
        {
          role: "pip",
          content: turnResp.pip.content,
          level: turnResp.pip.level,
          score: turnResp.feedback.score,
          covered: turnResp.feedback.covered,
          missing: turnResp.feedback.missing,
          misconceptions: turnResp.feedback.misconceptions,
        },
      ]);

      if (turnResp.finished) {
        setFinished(true);
        setFinalResult(turnResp.result || null);
        if (typeof window !== "undefined") {
          sessionStorage.removeItem(`dialecto_teachback_${conceptId}`);
        }
      }
    } catch (err: unknown) {
      // Revert optimistic user message on failure so state stays consistent
      setMessages((prev) => prev.filter((m) => m !== tempLearnerMsg));
      if (err instanceof ApiError) {
        setTurnError(err.message || "Failed to evaluate explanation. You can retry.");
      } else {
        setTurnError("Network error while submitting explanation. Your input is preserved — click retry.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const levelBadges = [
    { label: "Level 0: Confused", color: "bg-earth-sand/30 text-ink-secondary", mood: "Needs foundation" },
    { label: "Level 1: Curious", color: "bg-earth-amber/15 text-earth-amberText", mood: "Asking questions" },
    { label: "Level 2: Connecting Dots", color: "bg-botanical-leaf/15 text-botanical-leaf", mood: "Grasping mechanism" },
    { label: "Level 3: Mastered!", color: "bg-mastery-emeraldLight text-mastery-emeraldText", mood: "Full comprehension!" },
  ];

  const hasLearnerTurn = messages.some((m) => m.role === "learner");

  if (loading && !session) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="h-6 w-32 bg-canvas-warm rounded animate-pulse mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-96 bg-canvas-card rounded-xl border border-earth-sand/30 animate-pulse" />
          <div className="md:col-span-2 h-96 bg-canvas-card rounded-xl border border-earth-sand/30 animate-pulse" />
        </div>
      </div>
    );
  }

  if (initError) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="rounded-2xl border border-mastery-crimson/30 bg-surface p-8 shadow-subtle text-center space-y-4">
          <div className="h-12 w-12 mx-auto rounded-full bg-mastery-crimsonLight flex items-center justify-center text-mastery-crimson">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-ink-primary">
            Unable to Start Teach-Back Session
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
              onClick={initSession}
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
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Fallback Notice Toast */}
      {fallbackToast && (
        <div className="mb-4 p-3 rounded-lg bg-earth-amber/15 border border-earth-amber/30 text-earth-amberText text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>Tutor is busy, using backup evaluation model.</span>
        </div>
      )}

      {/* Top Breadcrumb */}
      <div className="flex items-center justify-between mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Study Map</span>
        </Link>
        <span className="font-mono text-[11px] text-ink-muted uppercase tracking-wider">
          Teach-Back Arena • {session?.concept_name}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Pip Persona & Rubric (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Pip State Card */}
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-botanical-leaf/15 text-botanical-leaf text-xl font-serif font-bold">
                Pip
              </div>
              <div>
                <h2 className="font-serif text-base font-bold text-ink-primary">
                  Pip (Peer Learner)
                </h2>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                      levelBadges[currentLevel]?.color || levelBadges[0].color
                    }`}
                  >
                    {levelBadges[currentLevel]?.label}
                  </span>
                </div>
              </div>
            </div>

            <p className="text-xs text-ink-secondary mb-3 leading-relaxed">
              Pip is your peer student. Explain the biological concepts clearly in your own words
              so Pip can understand and level up from Level 0 to Level 3.
            </p>

            {/* Level Stepper Bar */}
            <div className="space-y-1.5 pt-2 border-t border-earth-sand/20">
              <div className="flex justify-between text-[10px] font-mono text-ink-muted">
                <span>Comprehension Level</span>
                <span>{currentLevel} / 3</span>
              </div>
              <div className="grid grid-cols-4 gap-1 h-1.5">
                {[0, 1, 2, 3].map((lvl) => (
                  <div
                    key={lvl}
                    className={`rounded-full transition-all duration-300 ${
                      currentLevel >= lvl
                        ? lvl === 3
                          ? "bg-mastery-emerald"
                          : "bg-botanical-leaf"
                        : "bg-canvas-warm"
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* NCERT Concept Checklist */}
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-1.5">
                <BookOpen className="h-4 w-4 text-mastery-emerald" />
                <h3 className="font-serif text-xs font-bold text-ink-primary">
                  Curriculum Rubric
                </h3>
              </div>
              <span className="font-mono text-[10px] text-ink-muted">
                {coveredPoints.size} / {session?.rubric.key_points.length || 0} Covered
              </span>
            </div>

            {!hasLearnerTurn ? (
              <div className="rounded-lg bg-canvas-warm/40 border border-earth-sand/30 p-3 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-ink-primary">
                  <Lightbulb className="h-4 w-4 text-mastery-amber" />
                  <span>Your Mission</span>
                </div>
                <p className="text-xs text-ink-secondary leading-relaxed">
                  Teach Pip about <strong>{session?.concept_name}</strong> in your own words. The key evaluation points will unlock and check off as you explain the core biological mechanisms.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {session?.rubric.key_points.map((pt, idx) => {
                  const isCovered = coveredPoints.has(pt);
                  return (
                    <div
                      key={idx}
                      className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-xs transition ${
                        isCovered
                          ? "bg-mastery-emeraldLight/40 border-mastery-emerald/30 text-ink-primary font-medium"
                          : "bg-canvas-warm/30 border-earth-sand/30 text-ink-muted"
                      }`}
                    >
                      {isCovered ? (
                        <CheckCircle2 className="h-4 w-4 text-mastery-emerald shrink-0 mt-0.5" />
                      ) : (
                        <div className="h-3.5 w-3.5 rounded-full border border-dashed border-earth-sand shrink-0 mt-0.5" />
                      )}
                      <span className="leading-snug">{pt}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Dialogue Thread & Dictation Input (7 cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-4">
          {/* Transcript Scroll Area */}
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card max-h-[460px] overflow-y-auto space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${
                  msg.role === "learner" ? "items-end" : "items-start"
                }`}
              >
                <div className="flex items-center gap-1.5 mb-1 px-1">
                  <span className="font-serif text-[11px] font-semibold text-ink-muted">
                    {msg.role === "learner" ? "You (Tutor)" : "Pip"}
                  </span>
                  {msg.level !== undefined && (
                    <span className="text-[10px] text-ink-muted font-mono">
                      · Level {msg.level}
                    </span>
                  )}
                </div>

                <div
                  className={`max-w-[88%] rounded-xl p-3.5 text-xs leading-relaxed ${
                    msg.role === "learner"
                      ? "bg-ink-primary text-canvas rounded-tr-none shadow-subtle"
                      : "bg-canvas-warm/70 border border-earth-sand/30 text-ink-primary rounded-tl-none"
                  }`}
                >
                  {msg.content}
                </div>

                {/* Turn Feedback note if present */}
                {msg.score !== undefined && (
                  <div className="mt-1 text-[11px] text-ink-muted flex items-center gap-2 px-1">
                    <span>Rubric Score: {Math.round(msg.score * 100)}%</span>
                    {msg.covered && msg.covered.length > 0 && (
                      <span className="text-mastery-emeraldText font-medium">
                        +{msg.covered.length} point(s) explained
                      </span>
                    )}
                  </div>
                )}

                {/* Detected Misconceptions on this turn */}
                {msg.misconceptions && msg.misconceptions.length > 0 && (
                  <div className="mt-2 max-w-[88%] rounded-lg border border-mastery-amber bg-mastery-amberLight p-3 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-mastery-amberText">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>Note for Clarity</span>
                    </div>
                    {msg.misconceptions.map((misc) => (
                      <p key={misc.id} className="text-ink-primary">
                        &ldquo;{misc.statement}&rdquo;
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {submitting && (
              <div className="flex items-start gap-2">
                <div className="bg-canvas-warm/70 border border-earth-sand/30 rounded-xl rounded-tl-none p-3 text-xs text-ink-muted animate-pulse">
                  Pip is thinking and reflecting on your explanation...
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Turn Submission Error Alert */}
          {turnError && (
            <div className="rounded-xl border border-mastery-crimson/30 bg-mastery-crimsonLight p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-mastery-crimson shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-semibold text-mastery-crimsonText">
                  Explanation Evaluation Failed
                </h4>
                <p className="text-xs text-ink-primary leading-relaxed">
                  {turnError}
                </p>
              </div>
            </div>
          )}

          {/* Completion Celebration Card */}
          {finished && finalResult && (
            <div className="bg-mastery-emeraldLight/50 border border-mastery-emerald/30 rounded-xl p-6 shadow-card space-y-4 animate-in fade-in duration-200">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-mastery-emerald text-canvas">
                  <Award className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-serif text-base font-bold text-ink-primary">
                    Teach-Back Session Complete!
                  </h3>
                  <p className="text-xs text-ink-secondary">
                    Pip reached Level {finalResult.final_level} with a rubric mastery of{" "}
                    {Math.round(finalResult.final_score * 100)}%!
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 bg-canvas-card rounded-lg border border-earth-sand/30 text-xs">
                <div>
                  <span className="text-[10px] text-ink-muted uppercase block">Mastery Delta</span>
                  <span className="font-semibold text-mastery-emeraldText">
                    {Math.round(finalResult.mastery.before * 100)}% →{" "}
                    {Math.round(finalResult.mastery.after * 100)}%
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-muted uppercase block">Curriculum Status</span>
                  <span className="font-semibold capitalize text-ink-primary">
                    {finalResult.mastery.status}
                  </span>
                </div>
              </div>

              {/* Strengths & Gaps Breakdown */}
              {finalResult.strengths && finalResult.strengths.length > 0 && (
                <div className="space-y-1 text-xs">
                  <span className="font-semibold text-mastery-emeraldText block">
                    Observed Explanatory Strengths:
                  </span>
                  <ul className="list-disc list-inside space-y-0.5 text-ink-secondary">
                    {finalResult.strengths.map((str, i) => (
                      <li key={i}>{str}</li>
                    ))}
                  </ul>
                </div>
              )}

              {finalResult.gaps && finalResult.gaps.length > 0 && (
                <div className="space-y-1 text-xs">
                  <span className="font-semibold text-mastery-amberText block">
                    Areas for Next Review:
                  </span>
                  <ul className="list-disc list-inside space-y-0.5 text-ink-secondary">
                    {finalResult.gaps.map((gap, i) => (
                      <li key={i}>{gap}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-mastery-emerald/20">
                <button
                  onClick={() => router.push("/dashboard")}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-mastery-emerald text-canvas text-xs font-semibold hover:bg-mastery-emeraldText transition shadow-subtle"
                >
                  <span>Return to Study Map</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Input Box for Active Session */}
          {!finished && (
            <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-4 shadow-card space-y-3">
              <div className="flex items-center justify-between text-xs text-ink-secondary">
                <div className="flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-botanical-leaf" />
                  <span className="font-medium">Teach Pip in Your Own Words</span>
                </div>
                <span className="text-[11px] text-ink-muted">
                  Ctrl+Enter or Send Explanation
                </span>
              </div>

              <VoiceFriendlyTextarea
                value={inputText}
                onChange={setInputText}
                onSubmit={handleSubmit}
                placeholder="Speak out loud or type your scientific explanation to Pip here..."
                minRows={6}
                maxLength={2000}
                disabled={submitting}
              />

              <div className="flex items-center justify-between pt-1">
                <div className="text-[11px] text-ink-muted">
                  Explain clearly to level Pip up to Level 3
                </div>
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim() || submitting}
                  className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 disabled:opacity-40 transition shadow-subtle"
                >
                  <span>{submitting ? "Evaluating..." : turnError ? "Retry Explanation" : "Send Explanation"}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
