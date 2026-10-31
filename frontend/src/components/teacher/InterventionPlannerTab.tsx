"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type InterventionRecommendation,
} from "@/lib/api/client";
import {
  Sparkles,
  Compass,
  BookOpen,
  MessageSquare,
  CheckCircle,
  Clock,
  BarChart2,
  Plus,
  X,
  Loader2,
} from "lucide-react";
import { WisprCommandInput } from "@/components/ui/WisprCommandInput";

interface InterventionPlannerTabProps {
  classroomId?: number;
}

export function InterventionPlannerTab({ classroomId = 1 }: InterventionPlannerTabProps) {
  const queryClient = useQueryClient();
  const [selectedOutcomesId, setSelectedOutcomesId] = useState<number | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  // Fetch recommendations
  const { data: recommendations, isLoading: isRecsLoading } = useQuery({
    queryKey: ["intervention-recommendations", classroomId],
    queryFn: () => api.getInterventionRecommendations(classroomId),
  });

  // Fetch persisted interventions
  const { data: interventions, isLoading: isInterventionsLoading } = useQuery({
    queryKey: ["interventions-list", classroomId],
    queryFn: () => api.getInterventions(classroomId),
  });

  // Fetch outcomes for selected intervention
  const { data: outcomesData, isLoading: isOutcomesLoading } = useQuery({
    queryKey: ["intervention-outcomes", selectedOutcomesId],
    queryFn: () => (selectedOutcomesId ? api.getInterventionOutcomes(selectedOutcomesId, classroomId) : null),
    enabled: selectedOutcomesId !== null,
  });

  // Approve & Assign recommendation mutation
  const assignRecMutation = useMutation({
    mutationFn: async (rec: InterventionRecommendation) => {
      // 1. Create intervention
      const created = await api.createIntervention(
        {
          concept_id: rec.concept_id,
          title: rec.title,
          learning_gap: rec.learning_gap,
          target_misconception_id: rec.target_misconception_id,
          activity_type: rec.activity_type,
          recommended_remediation: rec.recommended_remediation,
          status: "approved",
        },
        classroomId
      );
      // 2. Assign affected students
      const studentIds = (rec.affected_students ?? []).map((s) => s.id);
      return api.assignIntervention(created.id, studentIds, classroomId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["interventions-list"] });
      queryClient.invalidateQueries({ queryKey: ["intervention-recommendations"] });
    },
    onError: (err: Error) => {
      alert(`Assignment failed: ${err.message}`);
    },
  });

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "diagram_lab":
        return <Compass className="w-3.5 h-3.5 text-emerald-700" />;
      case "teachback":
        return <MessageSquare className="w-3.5 h-3.5 text-purple-700" />;
      default:
        return <BookOpen className="w-3.5 h-3.5 text-blue-700" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-surface border border-border-subtle rounded-xl shadow-xs">
        <div>
          <h2 className="text-sm font-semibold text-ink-primary flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-700" />
            <span>Targeted Classroom Interventions</span>
          </h2>
          <p className="text-xs text-ink-secondary mt-0.5">
            Identify learning gaps across classroom diagnostic data, assign remediation, and measure post-intervention outcomes.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition shadow-xs self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Intervention</span>
        </button>
      </div>

      {/* Auto-Recommended Interventions */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted font-mono">
            Data-Driven Recommendations ({recommendations?.length || 0})
          </h3>
          <span className="text-[11px] text-ink-secondary">Generated from actual class gaps</span>
        </div>

        {isRecsLoading ? (
          <div className="py-8 text-center text-xs text-ink-muted font-mono animate-pulse">
            Scanning classroom matrix for learning gap clusters...
          </div>
        ) : !recommendations || recommendations.length === 0 ? (
          <div className="p-6 text-center text-xs text-ink-muted bg-surface rounded-xl border border-dashed border-border-subtle">
            No critical learning gaps or misconception hotspots detected across tested students.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recommendations.map((rec) => (
              <div
                key={rec.title}
                className="p-4 bg-surface rounded-xl border border-border-subtle shadow-xs flex flex-col justify-between gap-3 hover:border-emerald-600/40 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-subtle text-ink-secondary">
                      {getActivityIcon(rec.activity_type)}
                      <span>{rec.activity_type.replace("_", " ")}</span>
                    </span>
                    <span className="text-[11px] font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded font-medium">
                      {rec.affected_student_count} students affected
                    </span>
                  </div>

                  <h4 className="text-sm font-semibold text-ink-primary mt-2">{rec.title}</h4>
                  <p className="text-xs text-ink-secondary mt-1 leading-relaxed">{rec.learning_gap}</p>

                  <div className="mt-2.5 p-2 rounded bg-subtle/60 border border-border-subtle/60 text-[11px] text-ink-secondary leading-snug">
                    <strong className="text-ink-primary">Remediation:</strong> {rec.recommended_remediation}
                  </div>
                </div>

                <div className="pt-2 border-t border-border-subtle flex items-center justify-between gap-2">
                  <span className="text-[11px] text-ink-muted flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>~{rec.suggested_duration_mins} mins</span>
                  </span>

                  <button
                    onClick={() => assignRecMutation.mutate(rec)}
                    disabled={assignRecMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-700 text-white rounded-md text-xs font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs"
                  >
                    {assignRecMutation.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5" />
                    )}
                    <span>Approve & Assign</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Persisted Classroom Interventions */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted font-mono">
          Classroom Intervention Tracking ({interventions?.length || 0})
        </h3>

        {isInterventionsLoading ? (
          <div className="py-8 text-center text-xs text-ink-muted font-mono animate-pulse">
            Loading active interventions...
          </div>
        ) : !interventions || interventions.length === 0 ? (
          <div className="p-6 text-center text-xs text-ink-muted bg-surface rounded-xl border border-dashed border-border-subtle">
            No interventions assigned yet. Approve a recommendation above or create a custom plan.
          </div>
        ) : (
          <div className="space-y-2.5">
            {interventions.map((it) => (
              <div
                key={it.id}
                className="p-4 bg-surface rounded-xl border border-border-subtle shadow-xs flex flex-wrap items-center justify-between gap-3 hover:border-border-subtle/80 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                        it.status === "completed"
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : it.status === "in_progress"
                          ? "bg-blue-50 text-blue-800 border border-blue-200"
                          : "bg-amber-50 text-amber-800 border border-amber-200"
                      }`}
                    >
                      {it.status}
                    </span>
                    <h4 className="text-sm font-semibold text-ink-primary">{it.title}</h4>
                  </div>
                  <p className="text-xs text-ink-secondary">
                    {it.concept_name} • {it.completed_count} of {it.total_assigned} completed
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedOutcomesId(it.id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-subtle bg-subtle text-xs font-medium text-ink-primary hover:bg-border-subtle transition"
                  >
                    <BarChart2 className="w-3.5 h-3.5 text-emerald-700" />
                    <span>Measure Outcomes</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Outcomes Modal */}
      {selectedOutcomesId && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/20 backdrop-blur-sm"
        >
          <div className="w-full max-w-xl bg-surface border border-border-subtle rounded-xl p-6 shadow-flyout space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted">
                  Intervention Outcome Analytics
                </span>
                <h3 className="text-base font-serif font-semibold text-ink-primary">
                  {outcomesData?.title || "Measuring Outcomes..."}
                </h3>
              </div>
              <button
                onClick={() => setSelectedOutcomesId(null)}
                className="p-1 hover:bg-subtle rounded text-ink-muted"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {isOutcomesLoading ? (
              <div className="py-8 text-center text-xs text-ink-muted font-mono animate-pulse">
                Computing pre vs. post intervention mastery deltas...
              </div>
            ) : outcomesData ? (
              <div className="space-y-4 text-xs">
                {/* Metric Cards */}
                <div className="grid grid-cols-3 gap-2.5">
                  <div className="p-3 bg-subtle/50 rounded-lg border border-border-subtle text-center">
                    <span className="text-[10px] text-ink-muted uppercase block">Completion</span>
                    <span className="text-base font-bold text-ink-primary font-mono">
                      {Math.round(outcomesData.completion_rate * 100)}%
                    </span>
                    <span className="text-[10px] text-ink-secondary block">
                      {outcomesData.completed_count}/{outcomesData.total_assigned} done
                    </span>
                  </div>

                  <div className="p-3 bg-subtle/50 rounded-lg border border-border-subtle text-center">
                    <span className="text-[10px] text-ink-muted uppercase block">Baseline Mastery</span>
                    <span className="text-base font-bold text-ink-primary font-mono">
                      {Math.round(outcomesData.mean_baseline_mastery * 100)}%
                    </span>
                    <span className="text-[10px] text-ink-secondary block">At assignment</span>
                  </div>

                  <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-200 text-center">
                    <span className="text-[10px] text-emerald-800 uppercase block font-medium">Post Mastery</span>
                    <span className="text-base font-bold text-emerald-800 font-mono">
                      {outcomesData.mean_post_mastery != null
                        ? `${Math.round(outcomesData.mean_post_mastery * 100)}%`
                        : "Pending"}
                    </span>
                    {outcomesData.mean_mastery_gain != null && (
                      <span className="text-[10px] text-emerald-700 font-medium block">
                        +{Math.round(outcomesData.mean_mastery_gain * 100)}% gain
                      </span>
                    )}
                  </div>
                </div>

                {/* Outcome Narrative Summary */}
                <div className="p-3 bg-subtle rounded-lg border border-border-subtle leading-relaxed">
                  <p className="font-medium text-ink-primary mb-0.5">Statistical Analysis:</p>
                  <p className="text-ink-secondary">{outcomesData.outcome_summary}</p>
                </div>

                {/* Student Assignment List */}
                <div>
                  <h4 className="font-semibold text-ink-primary mb-2">Student Cohort Status</h4>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {(outcomesData.assignments ?? []).map((a) => (
                      <div
                        key={a.id}
                        className="p-2 rounded bg-surface border border-border-subtle flex items-center justify-between text-xs"
                      >
                        <span className="font-medium text-ink-primary">{a.student_name}</span>
                        <div className="flex items-center gap-3 font-mono text-[11px]">
                          <span>
                            {Math.round(a.baseline_mastery * 100)}% →{" "}
                            {a.post_mastery != null ? `${Math.round(a.post_mastery * 100)}%` : "..."}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] capitalize ${
                              a.status === "completed"
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-amber-50 text-amber-700"
                            }`}
                          >
                            {a.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Manual Intervention Creation Modal */}
      {isCreateModalOpen && (
        <CreateInterventionModal
          classroomId={classroomId}
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={() => {
            setIsCreateModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ["interventions-list"] });
          }}
        />
      )}
    </div>
  );
}

function CreateInterventionModal({
  classroomId,
  onClose,
  onSuccess,
}: {
  classroomId: number;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [conceptId, setConceptId] = useState<string>("lp-photosynthesis");
  const [title, setTitle] = useState<string>("");
  const [learningGap, setLearningGap] = useState<string>("");
  const [activityType, setActivityType] = useState<string>("practice");
  const [remediation, setRemediation] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !learningGap.trim() || !remediation.trim()) {
      setError("Please complete all required intervention fields.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await api.createIntervention(
        {
          concept_id: conceptId,
          title: title.trim(),
          learning_gap: learningGap.trim(),
          activity_type: activityType,
          recommended_remediation: remediation.trim(),
          status: "draft",
        },
        classroomId
      );
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Intervention creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/20 backdrop-blur-sm"
    >
      <div className="w-full max-w-lg bg-surface border border-border-subtle rounded-xl p-6 shadow-flyout space-y-4">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <h3 className="text-base font-serif font-semibold text-ink-primary">
            Create Intervention Plan
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-subtle rounded text-ink-muted">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Target Concept</label>
            <select
              value={conceptId}
              onChange={(e) => setConceptId(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-xs"
            >
              <option value="lp-photosynthesis">Photosynthesis (lp-photosynthesis)</option>
              <option value="lp-circulation">Circulation & Heart (lp-circulation)</option>
              <option value="lp-excretion">Excretion & Nephron (lp-excretion)</option>
              <option value="lp-respiration">Respiration & Cell (lp-respiration)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Intervention Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs"
              placeholder="e.g. Double Circulation Pathway Review"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Identified Learning Gap</label>
            <WisprCommandInput
              multiline
              minRows={2}
              onSubmit={(text) => setLearningGap((prev) => (prev ? `${prev} ${text}` : text))}
              placeholder="Dictate or type the diagnosed learning gap..."
              buttonLabel="Add to gap"
            />
            {learningGap && (
              <textarea
                value={learningGap}
                onChange={(e) => setLearningGap(e.target.value)}
                rows={2}
                className="w-full mt-1 p-2 bg-subtle border border-border-subtle rounded text-xs text-ink-primary"
              />
            )}
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Recommended Activity</label>
            <select
              value={activityType}
              onChange={(e) => setActivityType(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-xs"
            >
              <option value="practice">Targeted Adaptive Practice</option>
              <option value="diagram_lab">Interactive Biology Lab</option>
              <option value="teachback">Teach-Back Conversation with Pip</option>
              <option value="review">Spaced Repetition Review</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Remediation Instructions</label>
            <textarea
              value={remediation}
              onChange={(e) => setRemediation(e.target.value)}
              rows={2}
              className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs text-ink-primary"
              placeholder="Actionable instructions for students..."
            />
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2 border-t border-border-subtle">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg border border-border-subtle text-xs hover:bg-subtle"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 disabled:opacity-50"
            >
              {isSubmitting ? "Creating..." : "Save Plan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
