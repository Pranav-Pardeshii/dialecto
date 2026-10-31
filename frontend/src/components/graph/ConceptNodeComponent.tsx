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
    status: string; // locked, unlocked, learning, mastered
  } | null;
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
  const status = data.mastery?.status || "unlocked";
  const pEff = data.mastery ? Math.round(data.mastery.p_effective * 100) : 30;
  const isLocked = status === "locked";
  const isMastered = status === "mastered";
  const isLearning = status === "learning";

  const chapterName = CHAPTER_LABELS[data.chapter] || data.chapter;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Concept: ${data.name}. Chapter: ${chapterName}. Status: ${status}. Retention: ${pEff} percent.`}
      onClick={() => data.onSelect(data.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          data.onSelect(data.id);
        }
      }}
      className={`relative w-64 rounded-xl border p-4 transition-all duration-200 cursor-pointer shadow-subtle focus:outline-none focus:ring-2 focus:ring-mastery-emerald ${
        isLocked
          ? "border-border-subtle bg-subtle/60 opacity-75 hover:opacity-100"
          : isMastered
          ? "border-mastery-emerald bg-surface hover:shadow-flyout hover:border-mastery-emeraldText"
          : isLearning
          ? "border-mastery-amber bg-surface hover:shadow-flyout"
          : "border-border-subtle bg-surface hover:border-ink-primary hover:shadow-flyout"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-border-subtle !border-surface"
      />

      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider">
          {chapterName}
        </span>

        {/* Status Indicator */}
        {isLocked ? (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] text-ink-muted bg-subtle px-2 py-0.5 rounded">
            <Lock className="h-2.5 w-2.5" />
            <span>Locked</span>
          </span>
        ) : isMastered ? (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold text-mastery-emeraldText bg-mastery-emeraldLight px-2 py-0.5 rounded">
            <CheckCircle2 className="h-2.5 w-2.5 text-mastery-emerald" />
            <span>{pEff}% Mastered</span>
          </span>
        ) : isLearning ? (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold text-mastery-amberText bg-mastery-amberLight px-2 py-0.5 rounded">
            <span>{pEff}% Learning</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] text-ink-secondary bg-subtle px-2 py-0.5 rounded">
            <span>Ready</span>
          </span>
        )}
      </div>

      <h3 className="font-serif text-sm font-semibold text-ink-primary leading-snug line-clamp-2">
        {data.name}
      </h3>

      {/* Progress Bar */}
      {!isLocked && (
        <div className="mt-3 w-full bg-subtle h-1.5 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              isMastered
                ? "bg-mastery-emerald"
                : isLearning
                ? "bg-mastery-amber"
                : "bg-ink-muted"
            }`}
            style={{ width: `${Math.max(5, pEff)}%` }}
          />
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-border-subtle !border-surface"
      />
    </div>
  );
});
