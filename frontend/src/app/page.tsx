"use client";

import { useRouter } from "next/navigation";
import { setActiveDemoUserId } from "@/lib/api/client";
import { GraduationCap, Users, ArrowRight } from "lucide-react";

export default function HomePage() {
  const router = useRouter();

  const handleSelectRole = (userId: number, route: string) => {
    setActiveDemoUserId(userId);
    router.push(route);
  };

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-between">
      {/* Top minimalistic header */}
      <header className="border-b border-border-subtle/80 bg-canvas/60 px-6 py-4">
        <div className="mx-auto max-w-5xl flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-ink-primary text-canvas font-serif text-sm font-semibold">
              D
            </div>
            <span className="font-serif text-lg font-semibold tracking-tight text-ink-primary">
              Dialecto
            </span>
          </div>
          <span className="font-mono text-xs text-ink-muted">CBSE Class 10 Biology</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-4xl px-4 py-16 sm:px-6 w-full my-auto">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h1 className="font-serif text-3xl sm:text-4xl font-normal tracking-tight text-ink-primary mb-3">
            An adaptive study space that tracks what you truly understand.
          </h1>
          <p className="text-sm sm:text-base text-ink-secondary leading-relaxed">
            Move beyond binary right-or-wrong scores. Dialecto models student mastery per concept, detects conceptual misconceptions through reasoning, and reinforces long-term retention.
          </p>
        </div>

        {/* Perspective Selection Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Student Perspective */}
          <div
            onClick={() => handleSelectRole(1, "/dashboard")}
            className="group relative cursor-pointer rounded-xl border border-border-subtle bg-surface p-6 sm:p-8 transition-all duration-200 hover:border-mastery-emerald hover:shadow-subtle flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-mastery-emeraldLight text-mastery-emeraldText">
                  <GraduationCap className="h-5 w-5" />
                </div>
                <span className="font-mono text-[11px] text-ink-muted uppercase tracking-wider">
                  Student Space
                </span>
              </div>

              <h2 className="font-serif text-xl font-medium text-ink-primary mb-2 group-hover:text-mastery-emerald transition">
                Aarav
              </h2>
              <p className="text-xs text-ink-secondary leading-relaxed mb-6">
                Fresh study profile. Navigate the syllabus concept graph, identify hidden misconceptions in practice questions, and articulate understanding in conversational Teach-Back sessions.
              </p>

              <div className="space-y-2 border-t border-border-subtle pt-4 text-[12px] text-ink-secondary">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-mastery-emerald" />
                  <span>20 Biology concepts across 3 NCERT chapters</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-mastery-emerald" />
                  <span>Adaptive diagnostic & prerequisite graph</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-mastery-emerald" />
                  <span>Teach-Back inquiry with Pip</span>
                </div>
              </div>
            </div>

            <div className="mt-8 flex items-center gap-2 text-xs font-semibold text-mastery-emerald">
              <span>Open Student Study Map</span>
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </div>
          </div>

          {/* Teacher Perspective */}
          <div
            onClick={() => handleSelectRole(2, "/class")}
            className="group relative cursor-pointer rounded-xl border border-border-subtle bg-surface p-6 sm:p-8 transition-all duration-200 hover:border-ink-primary hover:shadow-subtle flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-subtle text-ink-primary">
                  <Users className="h-5 w-5" />
                </div>
                <span className="font-mono text-[11px] text-ink-muted uppercase tracking-wider">
                  Instructor Space
                </span>
              </div>

              <h2 className="font-serif text-xl font-medium text-ink-primary mb-2 group-hover:text-ink-primary transition">
                Ms. Rao
              </h2>
              <p className="text-xs text-ink-secondary leading-relaxed mb-6">
                Classroom analytics. Inspect a 30-student mastery heatmap across the curriculum, uncover prevalent misconceptions, and plan targeted classroom interventions.
              </p>

              <div className="space-y-2 border-t border-border-subtle pt-4 text-[12px] text-ink-secondary">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-ink-primary" />
                  <span>Class-wide 30 × 20 knowledge matrix</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-ink-primary" />
                  <span>Top shared misconception telemetry</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-ink-primary" />
                  <span>Systemic curriculum gap identification</span>
                </div>
              </div>
            </div>

            <div className="mt-8 flex items-center gap-2 text-xs font-semibold text-ink-primary">
              <span>Open Classroom Dashboard</span>
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border-subtle px-6 py-4 text-center">
        <p className="text-[12px] text-ink-muted">
          Dialecto • Designed for focused, deliberate biology study
        </p>
      </footer>
    </div>
  );
}
