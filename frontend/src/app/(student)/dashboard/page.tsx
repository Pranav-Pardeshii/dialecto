"use client";

import Link from "next/link";
import { ArrowRight, Layers } from "lucide-react";

export default function StudentDashboardPage() {
  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-border-subtle bg-surface p-6 shadow-subtle">
        <div>
          <span className="font-mono text-xs text-mastery-emerald font-semibold uppercase tracking-wider">
            Study Map
          </span>
          <h1 className="font-serif text-2xl font-normal text-ink-primary mt-1">
            Welcome, Aarav
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Your concept knowledge map is ready. Take the initial diagnostic to establish baseline mastery across Life Processes, Control & Coordination, and Heredity.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/diagnostic"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition"
          >
            <span>Start Diagnostic</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link
            href="/practice"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border-subtle bg-surface text-ink-primary text-xs font-semibold hover:bg-subtle transition"
          >
            <span>Practice</span>
          </Link>
        </div>
      </div>

      {/* Concept Graph Placeholder Arena (to be wired in M1) */}
      <div className="rounded-xl border border-border-subtle bg-surface p-8 shadow-subtle text-center min-h-[420px] flex flex-col items-center justify-center">
        <div className="h-12 w-12 rounded-full bg-subtle flex items-center justify-center text-ink-secondary mb-3">
          <Layers className="h-6 w-6 text-mastery-emerald" />
        </div>
        <h2 className="font-serif text-lg font-medium text-ink-primary mb-1">
          Concept Graph
        </h2>
        <p className="text-xs text-ink-secondary max-w-md leading-relaxed mb-4">
          Visualizing prerequisite relationships across 20 Class 10 Biology concepts. Mastery status will unlock nodes as you progress.
        </p>
        <span className="font-mono text-[11px] text-ink-muted px-2.5 py-1 rounded bg-subtle">
          Concept nodes loading in Milestone M1
        </span>
      </div>
    </div>
  );
}
