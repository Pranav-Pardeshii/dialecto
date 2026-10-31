"use client";

import Link from "next/link";
import { ArrowLeft, Clock } from "lucide-react";

export default function ReviewPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink-primary transition"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        <span>Back to Study Map</span>
      </Link>

      <div className="rounded-xl border border-border-subtle bg-surface p-8 shadow-subtle text-center">
        <div className="h-10 w-10 mx-auto rounded-full bg-subtle flex items-center justify-center text-ink-secondary mb-3">
          <Clock className="h-5 w-5 text-mastery-emerald" />
        </div>
        <h1 className="font-serif text-2xl font-normal text-ink-primary mb-2">
          Spaced Repetition Review
        </h1>
        <p className="text-xs text-ink-secondary max-w-sm mx-auto leading-relaxed mb-6">
          Concepts scheduled for periodic retrieval practice to ensure durable memory retention ahead of board exams.
        </p>
        <div className="inline-block font-mono text-[11px] text-ink-muted px-3 py-1.5 rounded-md bg-subtle">
          Scheduled for activation in Milestone M5
        </div>
      </div>
    </div>
  );
}

