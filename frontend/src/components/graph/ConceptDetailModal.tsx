"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, ConceptNode } from "@/lib/api/client";
import {
  X,
  BookOpen,
  MessageSquare,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Compass,
  AlertTriangle,
  History,
  CheckCircle2,
  Lock,
} from "lucide-react";

interface ConceptDetailModalProps {
  conceptId: string | null;
  selectedNode?: ConceptNode | null;
  onClose: () => void;
  onSelectConcept?: (conceptId: string) => void;
}

export function ConceptDetailModal({
  conceptId,
  selectedNode,
  onClose,
  onSelectConcept,
}: ConceptDetailModalProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"lesson" | "mastery">("mastery");

  const { data: concept, isLoading: isConceptLoading } = useQuery({
    queryKey: ["concept-detail", conceptId],
    queryFn: () => (conceptId ? api.getConceptDetail(conceptId) : null),
    enabled: !!conceptId,
  });

  const { data: explainable, isLoading: isExplainableLoading } = useQuery({
    queryKey: ["explainable-mastery", conceptId],
    queryFn: () => (conceptId ? api.getConceptExplainableMastery(conceptId) : null),
    enabled: !!conceptId,
  });

  // Listen for Escape key to close modal
  useEffect(() => {
    if (!conceptId) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [conceptId, onClose]);

  if (!conceptId) return null;

  const isLabSupported =
    conceptId === "lp-circulation" || conceptId === "lp-excretion" || conceptId === "lp-respiration";

  const isLocked =
    explainable?.status === "locked" || selectedNode?.mastery?.status === "locked";

  const unmetPrereqs =
    selectedNode?.mastery?.unmet_prerequisites || explainable?.unmet_prerequisites || [];

  const lockReason =
    selectedNode?.mastery?.lock_reason ||
    (unmetPrereqs.length > 0
      ? `Locked: Requires 60% prerequisite mastery. Unmet: ${unmetPrereqs.join(", ")}.`
      : null);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={concept?.name || "Concept Information"}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/20 backdrop-blur-sm animate-in fade-in duration-150"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[88vh] flex flex-col rounded-2xl border border-border-subtle bg-surface shadow-flyout overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-subtle px-6 py-4 bg-canvas/40">
          <div>
            <span className="font-mono text-[11px] text-ink-muted uppercase tracking-wider">
              {concept?.chapter.replace("-", " ")}
            </span>
            <h2 className="font-serif text-xl font-semibold text-ink-primary">
              {concept?.name || "Loading..."}
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1.5 text-ink-muted hover:text-ink-primary hover:bg-subtle transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b border-border-subtle bg-surface text-xs">
          <button
            onClick={() => setActiveTab("mastery")}
            className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-1.5 ${
              activeTab === "mastery"
                ? "border-emerald-700 text-emerald-800 font-semibold"
                : "border-transparent text-ink-secondary hover:text-ink-primary"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Mastery & Evidence</span>
          </button>
          <button
            onClick={() => setActiveTab("lesson")}
            className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-1.5 ${
              activeTab === "lesson"
                ? "border-emerald-700 text-emerald-800 font-semibold"
                : "border-transparent text-ink-secondary hover:text-ink-primary"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Lesson Curriculum</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Authentic Locked State Banner */}
          {isLocked && (
            <div className="p-4 rounded-xl border border-stone-300 bg-stone-100/80 text-xs text-stone-900 flex items-start gap-3 shadow-xs">
              <div className="p-2 rounded-lg bg-stone-200/90 text-stone-700 shrink-0 mt-0.5">
                <Lock className="w-4 h-4" />
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] font-semibold text-stone-700 uppercase tracking-wider">
                    Prerequisite Locked
                  </span>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-stone-200 text-stone-800">
                    Action Required
                  </span>
                </div>
                <p className="text-xs text-stone-800 leading-relaxed font-medium">
                  {lockReason ||
                    "This concept requires prerequisite mastery before practice or teach-back can begin."}
                </p>
                {concept?.prerequisites && concept.prerequisites.length > 0 && onSelectConcept && (
                  <div className="pt-2 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] text-stone-600 font-medium">Unlocks after:</span>
                    {concept.prerequisites.map((pId) => (
                      <button
                        key={pId}
                        onClick={() => onSelectConcept(pId)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-surface border border-stone-300 hover:border-emerald-600 text-ink-primary hover:text-emerald-800 transition"
                      >
                        <span>Inspect prerequisite</span>
                        <ArrowRight className="w-3 h-3 text-emerald-700" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "mastery" && (
            <>
              {isExplainableLoading ? (
                <div className="py-12 text-center text-xs text-ink-muted font-mono animate-pulse">
                  Aggregating learner evidence and timeline...
                </div>
              ) : explainable ? (
                <div className="space-y-4">
                  {/* Mastery & Evidence Confidence Banner */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                    <div className="p-3 rounded-lg border border-border-subtle bg-subtle/50">
                      <span className="text-[10px] uppercase font-mono text-ink-muted block mb-0.5">
                        Mastery Level
                      </span>
                      <span className="text-lg font-bold text-ink-primary font-mono">
                        {Math.round(explainable.p_effective * 100)}%
                      </span>
                      <span className="text-[10px] text-ink-secondary capitalize block mt-0.5">
                        {explainable.status}
                      </span>
                    </div>

                    <div className="p-3 rounded-lg border border-border-subtle bg-subtle/50">
                      <span className="text-[10px] uppercase font-mono text-ink-muted block mb-0.5">
                        Evidence Strength
                      </span>
                      <span className="text-sm font-semibold capitalize font-mono text-emerald-700">
                        {explainable.evidence_strength}
                      </span>
                      <span className="text-[10px] text-ink-secondary block mt-0.5">
                        Score: {Math.round(explainable.evidence_score * 100)}%
                      </span>
                    </div>

                    <div className="p-3 rounded-lg border border-border-subtle bg-subtle/50">
                      <span className="text-[10px] uppercase font-mono text-ink-muted block mb-0.5">
                        Assessments
                      </span>
                      <span className="text-sm font-semibold font-mono text-ink-primary">
                        {explainable.total_attempts} attempts
                      </span>
                      <span className="text-[10px] text-ink-secondary block mt-0.5">
                        {Math.round(explainable.accuracy_rate * 100)}% accuracy
                      </span>
                    </div>

                    <div className="p-3 rounded-lg border border-border-subtle bg-subtle/50">
                      <span className="text-[10px] uppercase font-mono text-ink-muted block mb-0.5">
                        Recent Trend
                      </span>
                      <span className="text-sm font-semibold capitalize font-mono text-ink-primary flex items-center gap-1">
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                        {explainable.recent_trend}
                      </span>
                      <span className="text-[10px] text-ink-secondary block mt-0.5">
                        {explainable.is_overdue ? `${explainable.days_overdue}d overdue` : "Up to date"}
                      </span>
                    </div>
                  </div>

                  {/* State-Derived Explanatory Narrative */}
                  <div className="p-3.5 rounded-lg border border-emerald-100 bg-emerald-50/60 text-xs text-emerald-950 leading-relaxed">
                    <p className="font-medium text-emerald-900 mb-1 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                      <span>Understanding Summary</span>
                    </p>
                    <p>{explainable.narrative}</p>
                  </div>

                  {/* Active Misconceptions Alert */}
                  {(explainable.active_misconceptions?.length ?? 0) > 0 && (
                    <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-xs text-red-950 space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-red-900">
                        <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                        <span>Active Misconception Detected</span>
                      </div>
                      {(explainable.active_misconceptions ?? []).map((m) => (
                        <div key={m.id} className="pt-1">
                          <p className="text-[11px] font-medium">{m.statement}</p>
                          <p className="text-[11px] text-red-800 mt-0.5">
                            <strong>Correction:</strong> {m.correction}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Evidence Timeline */}
                  <div>
                    <h4 className="text-xs font-semibold text-ink-primary mb-2 flex items-center gap-1.5">
                      <History className="w-3.5 h-3.5 text-ink-muted" />
                      <span>Evidence Timeline ({(explainable.timeline?.length ?? 0)} events)</span>
                    </h4>

                    {(explainable.timeline?.length ?? 0) === 0 ? (
                      <div className="text-xs text-ink-muted p-4 text-center rounded-lg border border-dashed border-border-subtle">
                        No assessment attempts recorded for this concept yet.
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                        {(explainable.timeline ?? []).map((ev, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-md border border-border-subtle bg-surface flex items-center justify-between text-xs"
                          >
                            <div className="flex items-center gap-2">
                              {ev.is_correct ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                              ) : (
                                <X className="w-3.5 h-3.5 text-red-600 shrink-0" />
                              )}
                              <div>
                                <span className="font-medium text-ink-primary block leading-tight">
                                  {ev.description}
                                </span>
                                <span className="text-[10px] text-ink-muted capitalize">
                                  {ev.event_type} • {new Date(ev.timestamp).toLocaleDateString()}
                                </span>
                              </div>
                            </div>

                            <div className="text-right font-mono text-[11px]">
                              <span>
                                {Math.round(ev.mastery_before * 100)}% →{" "}
                                <strong className="text-ink-primary font-bold">
                                  {Math.round(ev.mastery_after * 100)}%
                                </strong>
                              </span>
                              <span
                                className={`block text-[10px] font-medium ${
                                  ev.mastery_delta >= 0 ? "text-emerald-700" : "text-red-600"
                                }`}
                              >
                                {ev.mastery_delta >= 0 ? `+${Math.round(ev.mastery_delta * 100)}%` : `${Math.round(ev.mastery_delta * 100)}%`}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </>
          )}

          {activeTab === "lesson" && (
            <>
              {isConceptLoading ? (
                <div className="py-12 text-center text-xs text-ink-muted font-mono animate-pulse">
                  Loading concept curriculum...
                </div>
              ) : concept ? (
                <div className="space-y-4">
                  <div>
                    <h3 className="font-mono text-xs text-ink-muted uppercase tracking-wider mb-1">
                      Summary
                    </h3>
                    <p className="text-sm text-ink-secondary leading-relaxed">
                      {concept.description}
                    </p>
                  </div>

                  <div className="rounded-xl border border-border-subtle bg-canvas/50 p-4 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-primary">
                      <BookOpen className="h-3.5 w-3.5 text-emerald-700" />
                      <span>Curriculum Lesson Notes</span>
                    </div>
                    <p className="text-xs text-ink-secondary leading-relaxed whitespace-pre-line">
                      {concept.lesson_md}
                    </p>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>

        {/* Action Footer */}
        {concept && (
          <div className="border-t border-border-subtle p-4 bg-canvas/30 flex flex-wrap items-center justify-between gap-2">
            <div>
              {isLabSupported && (
                <button
                  onClick={() => {
                    onClose();
                    router.push("/lab");
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs font-semibold hover:bg-emerald-100 transition shadow-xs"
                >
                  <Compass className="h-3.5 w-3.5 text-emerald-700" />
                  <span>Interactive Biology Lab</span>
                </button>
              )}
            </div>

            {isLocked ? (
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-ink-muted">
                  Prerequisites need 60% mastery
                </span>
                <button
                  disabled
                  title={lockReason || "Complete prerequisite first"}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-border-subtle bg-subtle text-xs font-semibold text-ink-muted cursor-not-allowed"
                >
                  <Lock className="h-3.5 w-3.5" />
                  <span>Locked</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    onClose();
                    router.push(`/practice?concept=${concept.id}`);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-primary hover:bg-subtle transition"
                >
                  <BookOpen className="h-3.5 w-3.5 text-ink-secondary" />
                  <span>Practice</span>
                </button>
                <button
                  onClick={() => {
                    onClose();
                    router.push(`/teach-back/${concept.id}`);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition shadow-sm"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>Teach to Pip</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
