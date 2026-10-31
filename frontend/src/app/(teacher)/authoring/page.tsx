"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  api,
} from "@/lib/api/client";
import {
  Sparkles,
  CheckCircle,
  XCircle,
  Trash2,
  Filter,
  Plus,
  BookOpen,
  Loader2,
} from "lucide-react";
import { WisprCommandInput } from "@/components/ui/WisprCommandInput";

export default function QuestionAuthoringPage() {
  const queryClient = useQueryClient();

  // Filters
  const [selectedConcept, setSelectedConcept] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationFeedback, setGenerationFeedback] = useState<string | null>(null);

  // Manual authoring modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  // Generation form state
  const [genConceptId, setGenConceptId] = useState<string>("lp-photosynthesis");
  const [genKind, setGenKind] = useState<string>("mcq");
  const [genBucket, setGenBucket] = useState<number>(2);
  const [genCount, setGenCount] = useState<number>(2);

  // Fetch concepts for dropdown
  const { data: conceptsData } = useQuery({
    queryKey: ["concepts-list"],
    queryFn: () => api.getConceptGraph(),
  });

  // Fetch authoring questions
  const { data: questionsData, isLoading } = useQuery({
    queryKey: ["authoring-questions", selectedConcept, selectedStatus],
    queryFn: () =>
      api.getAuthoringQuestions({
        concept_id: selectedConcept || undefined,
        review_status: selectedStatus || undefined,
      }),
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (questionId: string) => api.reviewQuestion(questionId, "approve"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authoring-questions"] });
    },
    onError: (err: Error) => {
      alert(`Approval failed: ${err.message}`);
    },
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.reviewQuestion(id, "reject", reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authoring-questions"] });
    },
    onError: (err: Error) => {
      alert(`Rejection failed: ${err.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (questionId: string) => api.deleteQuestionDraft(questionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["authoring-questions"] });
    },
    onError: (err: Error) => {
      alert(`Delete failed: ${err.message}`);
    },
  });

  // Generate questions handler
  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationFeedback(null);
    try {
      const res = await api.generateQuestions({
        concept_id: genConceptId,
        kind: genKind,
        difficulty_bucket: genBucket,
        count: genCount,
      });
      setGenerationFeedback(
        `Generated ${res.generated.length} question drafts (${res.validation_passed} passed validation).`
      );
      queryClient.invalidateQueries({ queryKey: ["authoring-questions"] });
    } catch (err) {
      setGenerationFeedback(err instanceof Error ? err.message : "Question generation failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  const questions = questionsData?.questions || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto p-4 sm:p-6 text-ink-primary">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 bg-surface border border-border-subtle rounded-xl shadow-xs">
        <div>
          <span className="font-mono text-xs uppercase tracking-wider text-emerald-700 font-semibold">
            Teacher Item Writer
          </span>
          <h1 className="text-2xl font-serif font-normal text-ink-primary mt-1">
            Question Authoring & Generation Pipeline
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-2xl">
            Generate, author, validate, and review curriculum questions. All generated items are held as drafts and strictly excluded from student sessions until approved.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 transition shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Manual Question</span>
        </button>
      </div>

      {/* AI Question Generation Panel */}
      <div className="p-5 bg-surface border border-emerald-200/80 rounded-xl shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-700" />
            <h2 className="text-sm font-semibold text-ink-primary">
              AI Question Generator (Deterministic Validation)
            </h2>
          </div>
          <span className="text-[11px] font-mono text-ink-muted">CBSE Class 10 Biology</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Target Concept</label>
            <select
              value={genConceptId}
              onChange={(e) => setGenConceptId(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-ink-primary text-xs focus:ring-1 focus:ring-emerald-600"
            >
              {conceptsData?.nodes?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              )) || <option value="lp-photosynthesis">Photosynthesis</option>}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Question Type</label>
            <select
              value={genKind}
              onChange={(e) => setGenKind(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-ink-primary text-xs focus:ring-1 focus:ring-emerald-600"
            >
              <option value="mcq">Multiple Choice (MCQ)</option>
              <option value="assertion_reason">Assertion-Reason</option>
              <option value="case_based">Case-Based</option>
              <option value="application">Application-Based</option>
              <option value="diagram_id">Diagram Identification</option>
              <option value="short_answer">Short Answer</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Difficulty Bucket</label>
            <select
              value={genBucket}
              onChange={(e) => setGenBucket(parseInt(e.target.value, 10))}
              className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-ink-primary text-xs focus:ring-1 focus:ring-emerald-600"
            >
              <option value={1}>Bucket 1 (Foundation)</option>
              <option value={2}>Bucket 2 (Standard CBSE)</option>
              <option value={3}>Bucket 3 (Advanced Application)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Count</label>
            <div className="flex items-center gap-2">
              <select
                value={genCount}
                onChange={(e) => setGenCount(parseInt(e.target.value, 10))}
                className="w-20 px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-ink-primary text-xs focus:ring-1 focus:ring-emerald-600"
              >
                <option value={1}>1 item</option>
                <option value={2}>2 items</option>
                <option value={3}>3 items</option>
                <option value={5}>5 items</option>
              </select>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex-1 py-1.5 px-3 bg-emerald-700 text-white rounded-md font-medium text-xs hover:bg-emerald-800 disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5 shadow-xs"
              >
                {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                <span>{isGenerating ? "Generating..." : "Generate Drafts"}</span>
              </button>
            </div>
          </div>
        </div>

        {generationFeedback && (
          <div className="p-2.5 rounded-md bg-emerald-50 text-emerald-900 border border-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{generationFeedback}</span>
          </div>
        )}
      </div>

      {/* Filter and Question Bank Table */}
      <div className="bg-surface border border-border-subtle rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border-subtle">
          <div className="flex items-center gap-2 text-xs font-semibold text-ink-primary">
            <BookOpen className="w-4 h-4 text-emerald-700" />
            <span>Curriculum Question Bank ({questionsData?.total || 0} items)</span>
          </div>

          {/* Status and Concept Filter */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="flex items-center gap-1 text-ink-secondary">
              <Filter className="w-3.5 h-3.5" />
              <span>Status:</span>
            </div>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-2.5 py-1 bg-subtle border border-border-subtle rounded-md text-xs text-ink-primary"
            >
              <option value="">All Statuses</option>
              <option value="draft">Drafts</option>
              <option value="approved">Approved (Live)</option>
              <option value="rejected">Rejected</option>
            </select>

            <div className="flex items-center gap-1 text-ink-secondary ml-1">
              <span>Concept:</span>
            </div>
            <select
              value={selectedConcept}
              onChange={(e) => setSelectedConcept(e.target.value)}
              className="px-2.5 py-1 bg-subtle border border-border-subtle rounded-md text-xs text-ink-primary max-w-[140px]"
            >
              <option value="">All Concepts</option>
              {conceptsData?.nodes?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-xs text-ink-muted font-mono animate-pulse">
            Loading question repository...
          </div>
        ) : questions.length === 0 ? (
          <div className="py-12 text-center text-xs text-ink-muted rounded-lg border border-dashed border-border-subtle">
            No questions found matching the selected filter.
          </div>
        ) : (
          <div className="space-y-3">
            {questions.map((q) => (
              <div
                key={q.id}
                className="p-4 rounded-lg border border-border-subtle bg-surface hover:border-emerald-600/40 transition-colors shadow-2xs space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold ${
                        q.review_status === "approved"
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : q.review_status === "rejected"
                          ? "bg-red-50 text-red-800 border border-red-200"
                          : "bg-amber-50 text-amber-800 border border-amber-200"
                      }`}
                    >
                      {q.review_status}
                    </span>
                    <span className="text-[11px] font-mono text-ink-muted">
                      v{q.version} • {q.kind.replace("_", " ")}
                    </span>
                    <span className="text-[11px] font-medium text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded">
                      {q.concept_id}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {q.review_status !== "approved" && (
                      <button
                        onClick={() => approveMutation.mutate(q.id)}
                        disabled={approveMutation.isPending}
                        className="px-2.5 py-1 bg-emerald-700 text-white rounded text-xs font-medium hover:bg-emerald-800 flex items-center gap-1"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Approve</span>
                      </button>
                    )}

                    {q.review_status !== "rejected" && (
                      <button
                        onClick={() => {
                          const reason = prompt("Enter rejection reason for this question:");
                          if (reason) rejectMutation.mutate({ id: q.id, reason });
                        }}
                        disabled={rejectMutation.isPending}
                        className="px-2.5 py-1 bg-subtle hover:bg-red-50 text-red-700 border border-border-subtle rounded text-xs font-medium flex items-center gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    )}

                    {q.n_attempts === 0 && (
                      <button
                        onClick={() => {
                          if (confirm("Delete this draft question?")) {
                            deleteMutation.mutate(q.id);
                          }
                        }}
                        className="p-1 hover:bg-red-50 rounded text-ink-muted hover:text-red-600 transition-colors"
                        title="Delete unattempted question"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Question Stem */}
                <div>
                  <h3 className="text-sm font-semibold text-ink-primary leading-relaxed">
                    {q.stem}
                  </h3>
                </div>

                {/* Options List */}
                {q.options && q.options.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {(q.options as Array<{ key: string; text: string; misconception_id?: string | null }>).map((opt) => {
                      const isCorrect = opt.key.toUpperCase() === q.correct_key.toUpperCase();
                      return (
                        <div
                          key={opt.key}
                          className={`p-2 rounded-md border text-xs flex items-start gap-2 ${
                            isCorrect
                              ? "bg-emerald-50/70 border-emerald-300 text-emerald-950 font-medium"
                              : "bg-subtle/50 border-border-subtle/70 text-ink-secondary"
                          }`}
                        >
                          <span className="font-mono font-bold shrink-0">{opt.key}.</span>
                          <div className="flex-1">
                            <span>{opt.text}</span>
                            {opt.misconception_id && (
                              <span className="block mt-0.5 text-[10px] text-red-600 font-mono">
                                Distractor tags: {opt.misconception_id}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Explanation */}
                <div className="p-2.5 bg-subtle/60 rounded-md border border-border-subtle/70 text-xs text-ink-secondary leading-relaxed">
                  <strong className="text-ink-primary">Scientific Explanation:</strong> {q.explanation}
                </div>

                {q.rejection_reason && (
                  <div className="text-xs text-red-700 bg-red-50 p-2 rounded border border-red-200">
                    <strong>Rejection reason:</strong> {q.rejection_reason}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual Question Authoring Dialog */}
      {isCreateModalOpen && (
        <ManualQuestionModal
          conceptIds={conceptsData?.nodes?.map((n) => n.id) || ["lp-photosynthesis"]}
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={() => {
            setIsCreateModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ["authoring-questions"] });
          }}
        />
      )}
    </div>
  );
}

// Modal for manual question creation with Wispr Flow dictation compatibility
function ManualQuestionModal({
  conceptIds,
  onClose,
  onSuccess,
}: {
  conceptIds: string[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [conceptId, setConceptId] = useState<string>(conceptIds[0] || "lp-photosynthesis");
  const [stem, setStem] = useState<string>("");
  const [optA, setOptA] = useState<string>("");
  const [optB, setOptB] = useState<string>("");
  const [optC, setOptC] = useState<string>("");
  const [optD, setOptD] = useState<string>("");
  const [correctKey, setCorrectKey] = useState<string>("A");
  const [explanation, setExplanation] = useState<string>("");
  const [bucket, setBucket] = useState<number>(2);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stem.trim() || !optA.trim() || !optB.trim() || !explanation.trim()) {
      setError("Please complete all required question fields.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await api.createQuestionDraft({
        concept_id: conceptId,
        kind: "mcq",
        stem: stem.trim(),
        options: [
          { key: "A", text: optA.trim() },
          { key: "B", text: optB.trim() },
          { key: "C", text: optC.trim() || "None of the above" },
          { key: "D", text: optD.trim() || "All of the above" },
        ],
        correct_key: correctKey,
        explanation: explanation.trim(),
        difficulty_bucket: bucket,
      });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creation failed.");
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
      <div className="w-full max-w-xl bg-surface border border-border-subtle rounded-xl p-6 shadow-flyout space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <h2 className="text-base font-serif font-semibold text-ink-primary">
            Author Verified Question Draft
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-subtle rounded text-ink-muted">
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Target Concept</label>
            <select
              value={conceptId}
              onChange={(e) => setConceptId(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-xs"
            >
              {conceptIds.map((cid) => (
                <option key={cid} value={cid}>
                  {cid}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Question Stem</label>
            <WisprCommandInput
              multiline
              minRows={2}
              onSubmit={(text) => setStem((prev) => (prev ? `${prev} ${text}` : text))}
              placeholder="Dictate or type the question stem..."
              buttonLabel="Add to stem"
            />
            {stem && (
              <textarea
                value={stem}
                onChange={(e) => setStem(e.target.value)}
                rows={2}
                className="w-full mt-1.5 p-2 bg-subtle border border-border-subtle rounded text-xs text-ink-primary"
              />
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] font-medium text-ink-secondary mb-1">Option A</label>
              <input
                type="text"
                value={optA}
                onChange={(e) => setOptA(e.target.value)}
                className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs"
                placeholder="Option text..."
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-ink-secondary mb-1">Option B</label>
              <input
                type="text"
                value={optB}
                onChange={(e) => setOptB(e.target.value)}
                className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs"
                placeholder="Option text..."
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-ink-secondary mb-1">Option C</label>
              <input
                type="text"
                value={optC}
                onChange={(e) => setOptC(e.target.value)}
                className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs"
                placeholder="Option text..."
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-ink-secondary mb-1">Option D</label>
              <input
                type="text"
                value={optD}
                onChange={(e) => setOptD(e.target.value)}
                className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs"
                placeholder="Option text..."
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-ink-secondary mb-1">Correct Answer</label>
              <select
                value={correctKey}
                onChange={(e) => setCorrectKey(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-xs font-bold"
              >
                <option value="A">Option A</option>
                <option value="B">Option B</option>
                <option value="C">Option C</option>
                <option value="D">Option D</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-ink-secondary mb-1">Difficulty</label>
              <select
                value={bucket}
                onChange={(e) => setBucket(parseInt(e.target.value, 10))}
                className="w-full px-2.5 py-1.5 bg-subtle border border-border-subtle rounded-md text-xs"
              >
                <option value={1}>1 - Foundation</option>
                <option value={2}>2 - Standard</option>
                <option value={3}>3 - Advanced</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-secondary mb-1">Explanation</label>
            <textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              rows={2}
              className="w-full p-2 bg-subtle border border-border-subtle rounded text-xs text-ink-primary"
              placeholder="Scientific justification from NCERT..."
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
              {isSubmitting ? "Saving..." : "Save Draft"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
