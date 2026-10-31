"use client";

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { Lock, CheckCircle2 } from "lucide-react";

export interface ConceptNodeData {
  id: string;
  name: string;
  chapter: string;
  position: number;
  mastery?: {
    p_effective: number;
    status: string; // locked, ready, learning, mastered
    lock_reason?: string | null;
    unmet_prerequisites?: string[];
  } | null;
  isSelected?: boolean;
  onSelect: (id: string) => void;
  [key: string]: unknown;
}

const CHAPTER_LABELS: Record<string, string> = {
  "life-processes": "Life Processes",
  "control-coordination": "Control & Coord",
  "heredity": "Heredity",
};

export const ConceptNodeComponent = memo(function ConceptNodeComponent({
  data,
}: {
  data: ConceptNodeData;
}) {
  const status = data.mastery?.status || "ready";
  const isLocked = status === "locked";
  const isMastered = status === "mastered";
  const isLearning = status === "learning";
  const isReady = status === "ready" || status === "unlocked";

  const pEff = data.mastery ? Math.round(data.mastery.p_effective * 100) : 0;
  const chapterName = CHAPTER_LABELS[data.chapter] || data.chapter;
  const lockReason = data.mastery?.lock_reason;

  return (
    <div
      role="button"
      tabIndex={0}
      title={isLocked && lockReason ? lockReason : undefined}
      aria-label={`Concept: ${data.name}. Chapter: ${chapterName}. Status: ${status}.${
        isLocked && lockReason ? ` ${lockReason}` : isLearning || isMastered ? ` Mastery: ${pEff} percent.` : ""
      }`}
      onClick={() => data.onSelect(data.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          data.onSelect(data.id);
        }
      }}
      className={`relative w-64 rounded-xl border p-4 transition-all duration-200 cursor-pointer shadow-subtle focus:outline-none focus:ring-2 focus:ring-mastery-emerald ${
        data.isSelected
          ? "border-mastery-emerald ring-2 ring-mastery-emerald shadow-flyout bg-surface"
          : isLocked
          ? "border-border-subtle bg-subtle/70 opacity-80 hover:opacity-100 hover:border-ink-muted"
          : isMastered
          ? "border-mastery-emerald bg-surface hover:shadow-flyout hover:border-mastery-emeraldText"
          : isLearning
          ? "border-mastery-amber bg-surface hover:shadow-flyout hover:border-mastery-amberText"
          : "border-border-subtle bg-surface hover:border-ink-primary hover:shadow-flyout"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-border-subtle !border-2 !border-surface transition-colors"
      />

      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider">
          {chapterName}
        </span>

        {/* Status Indicator */}
        {isLocked ? (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] text-ink-muted bg-subtle px-2 py-0.5 rounded border border-border-subtle">
            <Lock className="h-2.5 w-2.5 text-ink-muted" />
            <span>Locked</span>
          </span>
        ) : isMastered ? (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold text-mastery-emeraldText bg-mastery-emeraldLight px-2 py-0.5 rounded border border-mastery-emerald/30">
            <CheckCircle2 className="h-2.5 w-2.5 text-mastery-emerald" />
            <span>{pEff}% Mastered</span>
          </span>
        ) : isLearning ? (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold text-mastery-amberText bg-mastery-amberLight px-2 py-0.5 rounded border border-mastery-amber/30">
            <span>{pEff}% Learning</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] text-ink-secondary bg-subtle px-2 py-0.5 rounded border border-border-subtle">
            <span>Ready</span>
          </span>
        )}
      </div>

      <h3 className="font-serif text-sm font-semibold text-ink-primary leading-snug line-clamp-2">
        {data.name}
      </h3>

      {/* Progress Bar (rendered only for concepts with learning evidence) */}
      {!isLocked && (isLearning || isMastered) && (
        <div className="mt-3 w-full bg-subtle h-1.5 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              isMastered
                ? "bg-mastery-emerald"
                : "bg-mastery-amber"
            }`}
            style={{ width: `${Math.max(5, pEff)}%` }}
          />
        </div>
      )}

      {/* Ready hint for fresh concepts */}
      {isReady && (
        <div className="mt-3 text-[11px] text-ink-muted font-mono flex items-center gap-1">
          <span>Prerequisites met • Ready to learn</span>
        </div>
      )}

      {/* Locked explanation hint */}
      {isLocked && lockReason && (
        <div className="mt-2 text-[10px] text-ink-muted line-clamp-1 italic font-sans">
          Click to view lock reason
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-border-subtle !border-2 !border-surface transition-colors"
      />
    </div>
  );
});
