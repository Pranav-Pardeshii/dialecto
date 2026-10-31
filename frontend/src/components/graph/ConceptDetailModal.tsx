"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { X, BookOpen, MessageSquare, ArrowRight } from "lucide-react";

interface ConceptDetailModalProps {
  conceptId: string | null;
  onClose: () => void;
}

export function ConceptDetailModal({ conceptId, onClose }: ConceptDetailModalProps) {
  const router = useRouter();

  const { data: concept, isLoading, error } = useQuery({
    queryKey: ["concept-detail", conceptId],
    queryFn: () => (conceptId ? api.getConceptDetail(conceptId) : null),
    enabled: !!conceptId,
  });

  if (!conceptId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/20 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-xl max-h-[85vh] flex flex-col rounded-2xl border border-border-subtle bg-surface shadow-flyout overflow-hidden">
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
            className="rounded-lg p-1.5 text-ink-muted hover:text-ink-primary hover:bg-subtle transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading && (
            <div className="py-12 text-center text-xs text-ink-muted font-mono animate-pulse">
              Loading concept curriculum...
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-mastery-crimsonLight p-4 text-xs text-mastery-crimsonText">
              Failed to load concept information.
            </div>
          )}

          {concept && (
            <>
              {/* Description */}
              <div>
                <h3 className="font-mono text-xs text-ink-muted uppercase tracking-wider mb-1">
                  Summary
                </h3>
                <p className="text-sm text-ink-secondary leading-relaxed">
                  {concept.description}
                </p>
              </div>

              {/* Lesson Text */}
              <div className="rounded-xl border border-border-subtle bg-canvas/50 p-4 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-ink-primary">
                  <BookOpen className="h-3.5 w-3.5 text-mastery-emerald" />
                  <span>Curriculum Lesson Notes</span>
                </div>
                <p className="text-xs text-ink-secondary leading-relaxed whitespace-pre-line">
                  {concept.lesson_md}
                </p>
              </div>

              {/* Prerequisites and Misconceptions Stats */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-lg border border-border-subtle p-3 bg-surface">
                  <span className="font-mono text-[10px] text-ink-muted uppercase block mb-1">
                    Prerequisites
                  </span>
                  <span className="font-medium text-ink-primary">
                    {concept.prerequisites.length > 0
                      ? `${concept.prerequisites.length} prerequisite(s)`
                      : "Foundational (none)"}
                  </span>
                </div>
                <div className="rounded-lg border border-border-subtle p-3 bg-surface">
                  <span className="font-mono text-[10px] text-ink-muted uppercase block mb-1">
                    Misconception Catalog
                  </span>
                  <span className="font-medium text-ink-primary">
                    {concept.misconception_count} tracked misconception(s)
                  </span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Action Footer */}
        {concept && (
          <div className="border-t border-border-subtle p-4 bg-canvas/30 flex items-center justify-end gap-3">
            <button
              onClick={() => {
                onClose();
                router.push(`/practice?concept=${concept.id}`);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-primary hover:bg-subtle transition"
            >
              <BookOpen className="h-3.5 w-3.5 text-ink-secondary" />
              <span>Practice Questions</span>
            </button>
            <button
              onClick={() => {
                onClose();
                router.push(`/teach-back/${concept.id}`);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-mastery-emerald text-canvas text-xs font-semibold hover:bg-mastery-emeraldText transition shadow-subtle"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Teach to Pip</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
