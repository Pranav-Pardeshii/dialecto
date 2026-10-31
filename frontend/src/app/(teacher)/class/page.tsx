"use client";

import { Users, Grid } from "lucide-react";

export default function ClassHeatmapPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-border-subtle bg-surface p-6 shadow-subtle">
        <div>
          <span className="font-mono text-xs text-ink-primary font-semibold uppercase tracking-wider">
            Instructor Analytics
          </span>
          <h1 className="font-serif text-2xl font-normal text-ink-primary mt-1">
            Class 10-A Biology Overview
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Instructor: Ms. Rao • 30 Students enrolled across Life Processes, Control & Coordination, and Heredity.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-subtle text-xs font-mono text-ink-primary border border-border-subtle">
            <Users className="h-3.5 w-3.5 text-mastery-emerald" />
            <span>30 Students Active</span>
          </span>
        </div>
      </div>

      {/* Heatmap Matrix Arena Placeholder */}
      <div className="rounded-xl border border-border-subtle bg-surface p-8 shadow-subtle text-center min-h-[420px] flex flex-col items-center justify-center">
        <div className="h-12 w-12 rounded-full bg-subtle flex items-center justify-center text-ink-secondary mb-3">
          <Grid className="h-6 w-6 text-ink-primary" />
        </div>
        <h2 className="font-serif text-lg font-medium text-ink-primary mb-1">
          Class-Wide Knowledge Heatmap
        </h2>
        <p className="text-xs text-ink-secondary max-w-md leading-relaxed mb-4">
          A high-density 30 × 20 matrix displaying student-by-concept mastery percentages, top shared misconceptions, and systemic learning gaps.
        </p>
        <span className="font-mono text-[11px] text-ink-muted px-2.5 py-1 rounded bg-subtle">
          Heatmap simulation data loading in Milestone M5
        </span>
      </div>
    </div>
  );
}
