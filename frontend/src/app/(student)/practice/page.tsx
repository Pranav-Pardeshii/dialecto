"use client";

import Link from "next/link";
import { ArrowLeft, BookOpen } from "lucide-react";

export default function PracticePage() {
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
          <BookOpen className="h-5 w-5 text-mastery-emerald" />
        </div>
        <h1 className="font-serif text-2xl font-normal text-ink-primary mb-2">
          Targeted Practice
        </h1>
        <p className="text-xs text-ink-secondary max-w-sm mx-auto leading-relaxed mb-6">
          Calibrated questions targeting your weak concepts, paired with a dictation-friendly reasoning box to isolate misconceptions.
        </p>
        <div className="inline-block font-mono text-[11px] text-ink-muted px-3 py-1.5 rounded-md bg-subtle">
          Scheduled for activation in Milestone M2
        </div>
      </div>
    </div>
  );
}
