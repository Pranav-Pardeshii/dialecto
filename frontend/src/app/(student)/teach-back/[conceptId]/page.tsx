"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
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
  const [inputText, setInputText] = useState("");
  const [messages, setMessages] = useState<TurnMessage[]>([]);
  const [currentLevel, setCurrentLevel] = useState<number>(0);
  const [coveredPoints, setCoveredPoints] = useState<Set<string>>(new Set());
  const [finished, setFinished] = useState(false);
  const [finalResult, setFinalResult] = useState<TeachbackTurnResponse["result"] | null>(null);
  const [fallbackToast, setFallbackToast] = useState(false);

  useEffect(() => {
    let mounted = true;
    const initSession = async () => {
      try {
        setLoading(true);
        const startData = await api.startTeachback(conceptId);
        if (!mounted) return;
        setSession(startData);
        setCurrentLevel(startData.pip.level);
        setMessages([
          {
            role: "pip",
            content: startData.pip.content,
            level: startData.pip.level,
          },
        ]);
      } catch {
        // Fallback demo session if backend endpoint offline
        if (!mounted) return;
        setSession({
          id: 1,
          concept_id: conceptId,
          concept_name: "Photosynthesis Mechanism",
          turn_count: 0,
          pip: {
            content:
              "Hi! Can you teach me how plants make food using sunlight? Where does the oxygen come from?",
            level: 0,
          },
          rubric: {
            key_points: [
              "Absorption of light energy by chlorophyll",
              "Splitting of water (photolysis) releasing oxygen gas",
              "Reduction of carbon dioxide to carbohydrates",
            ],
          },
          finished: false,
        });
        setMessages([
          {
            role: "pip",
            content:
              "Hi! Can you teach me how plants make food using sunlight? Where does the oxygen come from?",
            level: 0,
          },
        ]);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    initSession();
    return () => {
      mounted = false;
    };
  }, [conceptId]);

  const handleSubmit = async () => {
    if (!inputText.trim() || !session || submitting || finished) return;

    const userText = inputText.trim();
    setInputText("");
    setSubmitting(true);

    // Optimistically add learner turn to thread
    setMessages((prev) => [...prev, { role: "learner", content: userText }]);

    try {
      const turnResp = await api.submitTeachbackTurn(session.id, userText);
      setCurrentLevel(turnResp.pip.level);

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
      }
    } catch {
      // Graceful fallback dialogue if offline
      setCurrentLevel((prev) => Math.min(3, prev + 1));
      setMessages((prev) => [
        ...prev,
        {
          role: "pip",
          content:
            "Oh, that's helpful! So water splits and sunlight powers the chloroplast, right?",
          level: 1,
        },
      ]);
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
          Teach-Back Arena
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Pip Persona & Rubric Checklist (4 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Pip State Card */}
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-botanical-leaf/15 text-botanical-leaf text-xl font-serif font-bold">
                Pip
              </div>
              <div>
                <h2 className="font-serif text-base font-bold text-ink-primary">
                  Pip (Student AI)
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
                <span>Comprehension</span>
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

          {/* NCERT Rubric Checklist */}
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-1.5">
                <BookOpen className="h-4 w-4 text-mastery-emerald" />
                <h3 className="font-serif text-xs font-bold text-ink-primary">
                  NCERT Concept Rubric
                </h3>
              </div>
              <span className="font-mono text-[10px] text-ink-muted">
                {coveredPoints.size} / {session?.rubric.key_points.length || 0}
              </span>
            </div>

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
              </div>
            ))}

            {submitting && (
              <div className="flex items-start gap-2">
                <div className="bg-canvas-warm/70 border border-earth-sand/30 rounded-xl rounded-tl-none p-3 text-xs text-ink-muted animate-pulse">
                  Pip is thinking and reflecting on your explanation...
                </div>
              </div>
            )}
          </div>

          {/* Completion Celebration Card */}
          {finished && finalResult && (
            <div className="bg-mastery-emeraldLight/50 border border-mastery-emerald/30 rounded-xl p-6 shadow-card">
              <div className="flex items-center gap-3 mb-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-mastery-emerald text-canvas">
                  <Award className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-serif text-base font-bold text-ink-primary">
                    Teach-Back Session Complete!
                  </h3>
                  <p className="text-xs text-ink-secondary">
                    Pip reached Level {finalResult.final_level} with a score of{" "}
                    {Math.round(finalResult.final_score * 100)}%!
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 my-4 p-3 bg-canvas-card rounded-lg border border-earth-sand/30 text-xs">
                <div>
                  <span className="text-[10px] text-ink-muted uppercase block">Mastery Delta</span>
                  <span className="font-semibold text-mastery-emeraldText">
                    {Math.round(finalResult.mastery.before * 100)}% →{" "}
                    {Math.round(finalResult.mastery.after * 100)}%
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-muted uppercase block">Status</span>
                  <span className="font-semibold capitalize text-ink-primary">
                    {finalResult.mastery.status}
                  </span>
                </div>
              </div>

              <div className="flex justify-end gap-2">
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
                  Ctrl+Enter or Submit
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
                  Explain clearly to unlock Level 3
                </div>
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim() || submitting}
                  className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 disabled:opacity-40 transition shadow-subtle"
                >
                  <span>{submitting ? "Evaluating..." : "Send Explanation"}</span>
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
