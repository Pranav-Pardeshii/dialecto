"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, getActiveDemoUserId } from "@/lib/api/client";
import { ConceptGraphView } from "@/components/graph/ConceptGraphView";
import { ArrowRight, RefreshCw, AlertCircle, RotateCcw } from "lucide-react";

export default function StudentDashboardPage() {
  const [userId, setUserId] = useState<number | null>(null);

  useEffect(() => {
    setUserId(getActiveDemoUserId());
    const handleStorage = () => setUserId(getActiveDemoUserId());
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const { data: me } = useQuery({
    queryKey: ["user-me", userId],
    queryFn: () => api.getMe(),
    enabled: userId !== null,
  });

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["concept-graph", userId],
    queryFn: () => api.getConceptGraph(),
    enabled: userId !== null,
    retry: 1,
  });

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-border-subtle bg-surface p-6 shadow-subtle">
        <div>
          <span className="font-mono text-xs text-mastery-emerald font-semibold uppercase tracking-wider">
            Study Map
          </span>
          <h1 className="font-serif text-2xl font-normal text-ink-primary mt-1">
            {me?.display_name ? `Welcome, ${me.display_name}` : "Curriculum Study Map"}
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-xl">
            Interactive prerequisite knowledge graph across 20 Class 10 Biology concepts. Click any concept node to read notes, launch practice, or explain to Pip.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/diagnostic"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-subtle"
          >
            <span>Start Diagnostic</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link
            href="/practice"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border-subtle bg-surface text-ink-primary text-xs font-semibold hover:bg-subtle transition"
          >
            <span>Targeted Practice</span>
          </Link>
        </div>
      </div>

      {/* Hero Interactive Concept Graph */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2 text-xs text-ink-muted font-mono">
            <span>20 Concepts • Directed Prerequisite Acyclic Graph</span>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="inline-flex items-center gap-1 text-[11px] font-mono text-ink-muted hover:text-ink-primary transition"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {isLoading ? (
          <div className="w-full h-[680px] rounded-2xl border border-border-subtle bg-surface/50 flex flex-col items-center justify-center space-y-3">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-mastery-emerald border-t-transparent" />
            <p className="text-xs font-mono text-ink-muted">Loading curriculum knowledge graph...</p>
          </div>
        ) : isError ? (
          <div className="w-full h-[400px] rounded-2xl border border-mastery-crimson/30 bg-surface flex flex-col items-center justify-center p-8 text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-mastery-crimsonLight flex items-center justify-center text-mastery-crimson">
              <AlertCircle className="h-6 w-6" />
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink-primary">
              Unable to Load Concept Graph
            </h3>
            <p className="text-xs text-ink-secondary max-w-md">
              {error instanceof Error ? error.message : "Failed to connect to the learning server. Please verify your connection."}
            </p>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-subtle"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          </div>
        ) : data && data.nodes && data.nodes.length > 0 ? (
          <ConceptGraphView nodes={data.nodes} edges={data.edges} />
        ) : (
          <div className="w-full h-[300px] rounded-2xl border border-border-subtle bg-surface flex items-center justify-center text-xs text-ink-muted">
            No concepts available.
          </div>
        )}
      </div>
    </div>
  );
}
