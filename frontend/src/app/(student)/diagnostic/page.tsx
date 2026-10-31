"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, DiagnosticStartResponse, DiagnosticResultResponse } from "@/lib/api/client";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

const FALLBACK_QUESTIONS: DiagnosticStartResponse["question"][] = [
  {
    id: "q-lp-nutrition-01",
    concept_id: "lp-nutrition",
    stem: "Which of the following organisms exhibits saprophytic nutrition?",
    options: [
      { key: "A", text: "Mushroom breaking down dead organic matter" },
      { key: "B", text: "Amoeba engulfing solid food particles with pseudopodia" },
      { key: "C", text: "Cuscuta deriving nutrition from a host plant" },
      { key: "D", text: "Green algae synthesizing glucose in water" },
    ],
    difficulty_bucket: 1,
  },
  {
    id: "q-lp-photo-01",
    concept_id: "lp-photosynthesis",
    stem: "During the light reaction of photosynthesis, what is the direct chemical source of released molecular oxygen?",
    options: [
      { key: "A", text: "Water molecules split by absorbed light energy (photolysis)" },
      { key: "B", text: "Carbon dioxide reduction during the Calvin cycle" },
      { key: "C", text: "Degradation of synthesized glucose polymers" },
      { key: "D", text: "Chlorophyll pigment breakdown" },
    ],
    difficulty_bucket: 2,
  },
  {
    id: "q-cc-neuron-01",
    concept_id: "cc-neuron",
    stem: "What is the correct unidirectional pathway of an electrical nerve impulse through a single neuron?",
    options: [
      { key: "A", text: "Dendrite → Cyton (cell body) → Axon → Axon terminal" },
      { key: "B", text: "Axon terminal → Axon → Cyton → Dendrite" },
      { key: "C", text: "Cyton → Dendrite → Axon → Synapse" },
      { key: "D", text: "Dendrite → Axon → Cyton → Axon terminal" },
    ],
    difficulty_bucket: 1,
  },
  {
    id: "q-lp-respiration-01",
    concept_id: "lp-respiration",
    stem: "Where does glycolysis take place within an active cell, and does it require oxygen?",
    options: [
      { key: "A", text: "Cytoplasm; does not require oxygen" },
      { key: "B", text: "Mitochondrial matrix; requires oxygen" },
      { key: "C", text: "Inner mitochondrial membrane; requires oxygen" },
      { key: "D", text: "Chloroplast stroma; does not require oxygen" },
    ],
    difficulty_bucket: 2,
  },
  {
    id: "q-he-variation-01",
    concept_id: "he-variation",
    stem: "What is the primary biological advantage of genetic variation occurring during sexual reproduction in a population?",
    options: [
      { key: "A", text: "Enhances species survival potential across changing environmental niches" },
      { key: "B", text: "Guarantees identical copies of parental DNA molecules" },
      { key: "C", text: "Shortens gestation and reproductive life cycles" },
      { key: "D", text: "Completely eliminates harmful recessive traits in a single generation" },
    ],
    difficulty_bucket: 2,
  },
];

export default function DiagnosticPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [session, setSession] = useState<DiagnosticStartResponse | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<DiagnosticStartResponse["question"] | null>(null);
  const [progress, setProgress] = useState({ answered: 0, total: 15 });
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [result, setResult] = useState<DiagnosticResultResponse | null>(null);
  const [startTime, setStartTime] = useState<number>(Date.now());

  useEffect(() => {
    async function start() {
      setLoading(true);
      try {
        const res = await api.startDiagnostic();
        setSession(res);
        setCurrentQuestion(res.question);
        setProgress(res.progress);
        setStartTime(Date.now());
      } catch {
        // Fallback demo state
        const firstQ = FALLBACK_QUESTIONS[0];
        setSession({
          session_id: 1,
          question: firstQ,
          progress: { answered: 0, total: 15 },
        });
        setCurrentQuestion(firstQ);
        setStartTime(Date.now());
      } finally {
        setLoading(false);
      }
    }
    start();
  }, []);

  const handleAnswerSubmit = async () => {
    if (!selectedKey || !session || !currentQuestion || submitting) return;

    setSubmitting(true);
    const responseMs = Date.now() - startTime;
    const clientAttemptId = crypto.randomUUID();

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
        setStartTime(Date.now());
      }
    } catch {
      // Advance locally if offline
      const newAnswered = Math.min(15, progress.answered + 1);
      setProgress({ answered: newAnswered, total: 15 });
      setSelectedKey(null);

      if (newAnswered >= 15) {
        setResult({
          mastery: [
            { concept_id: "lp-nutrition", concept_name: "Modes of Nutrition", p_mastery: 0.70, status: "learning" },
            { concept_id: "lp-photosynthesis", concept_name: "Photosynthesis", p_mastery: 0.35, status: "learning" },
            { concept_id: "lp-digestion", concept_name: "Human Alimentary Canal & Digestion", p_mastery: 0.75, status: "learning" },
            { concept_id: "cc-neuron", concept_name: "Neuron Structure & Nerve Impulse", p_mastery: 0.65, status: "learning" },
            { concept_id: "he-variation", concept_name: "Variation & Biological Evolution", p_mastery: 0.80, status: "mastered" },
            { concept_id: "cc-plant-hormones", concept_name: "Plant Hormones & Tropisms", p_mastery: 0.85, status: "mastered" },
          ],
          weakest: ["lp-photosynthesis", "lp-stomata", "cc-reflex"],
          recommended_next: "lp-photosynthesis",
        });
      } else {
        const nextQ = FALLBACK_QUESTIONS[newAnswered % FALLBACK_QUESTIONS.length];
        setCurrentQuestion(nextQ);
        setStartTime(Date.now());
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

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Exit to Study Map</span>
        </Link>

        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-ink-primary">
            {result
              ? `Completed (${progress.total} of ${progress.total})`
              : `Question ${Math.min(progress.answered + 1, progress.total)} of ${progress.total}`}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-subtle h-2 rounded-full overflow-hidden">
        <div
          className="h-full bg-mastery-emerald transition-all duration-300"
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

          {/* Submit Action */}
          <div className="flex items-center justify-end pt-2">
            <button
              disabled={!selectedKey || submitting}
              onClick={handleAnswerSubmit}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 disabled:opacity-40 transition shadow-subtle"
            >
              <span>{submitting ? "Processing..." : "Next Question"}</span>
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
              Your baseline mastery profile has been established across the CBSE Class 10 Biology syllabus.
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

          {/* Detailed Baseline Mastery Breakdown */}
          {result.mastery.length > 0 && (
            <div className="space-y-3 pt-2">
              <span className="font-mono text-[11px] uppercase tracking-wider text-ink-muted block">
                Calibrated Syllabus Baseline
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {result.mastery.slice(0, 8).map((item) => (
                  <div
                    key={item.concept_id}
                    className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-canvas/60"
                  >
                    <span className="text-xs text-ink-primary font-medium truncate max-w-[190px]">
                      {item.concept_name}
                    </span>
                    <span
                      className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded ${
                        item.p_mastery >= 0.75
                          ? "bg-mastery-emeraldLight text-mastery-emeraldText"
                          : item.p_mastery >= 0.5
                          ? "bg-mastery-amberLight text-mastery-amberText"
                          : "bg-mastery-crimsonLight text-mastery-crimsonText"
                      }`}
                    >
                      {Math.round(item.p_mastery * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4">
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
