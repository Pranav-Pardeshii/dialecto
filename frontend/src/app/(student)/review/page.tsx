"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, ReviewDueItem } from "@/lib/api/client";
import {
  Clock,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  BookOpen,
  AlertCircle,
  RotateCcw,
} from "lucide-react";

export default function ReviewPage() {
  const router = useRouter();
  const [reviews, setReviews] = useState<ReviewDueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDueReviews();
      setReviews(data);
    } catch (err: unknown) {
      setReviews([]);
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load due reviews.");
      } else {
        setError("Unable to connect to the learning server. Please check your connection.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8 pb-4 border-b border-earth-sand/30 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-mastery-emerald" />
            <h1 className="font-serif text-2xl font-bold tracking-tight text-ink-primary">
              Spaced Repetition Review
            </h1>
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Maintain your long-term memory before concepts decay. Reviewed concepts reinforce retention.
          </p>
        </div>

        {reviews.length > 0 && (
          <button
            onClick={() => router.push(`/practice?concept=${reviews[0].concept_id}&mode=review`)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-subtle"
          >
            <Sparkles className="h-3.5 w-3.5 text-botanical-leaf" />
            <span>Start Review Session</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-canvas-card rounded-xl border border-earth-sand/30 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-mastery-crimson/30 bg-surface p-8 shadow-subtle text-center space-y-4">
          <div className="h-12 w-12 mx-auto rounded-full bg-mastery-crimsonLight flex items-center justify-center text-mastery-crimson">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="font-serif text-base font-semibold text-ink-primary">
            Unable to Load Due Reviews
          </h3>
          <p className="text-xs text-ink-secondary max-w-sm mx-auto">
            {error}
          </p>
          <div className="pt-2 flex items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="px-4 py-2 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-secondary hover:bg-subtle transition"
            >
              Back to Study Map
            </Link>
            <button
              onClick={fetchReviews}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-subtle"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      ) : reviews.length === 0 ? (
        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-12 text-center shadow-card">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-mastery-emeraldLight text-mastery-emerald mb-3">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h3 className="font-serif text-base font-bold text-ink-primary">
            All Caught Up!
          </h3>
          <p className="text-xs text-ink-muted max-w-sm mx-auto mt-1 mb-6">
            You have no concepts overdue for spaced repetition today. Continue practicing or explore the study map.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-mastery-emerald text-canvas text-xs font-semibold hover:bg-mastery-emeraldText transition shadow-subtle"
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span>Explore Study Map</span>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((item) => {
            const pct = Math.round(item.p_effective * 100);
            return (
              <div
                key={item.concept_id}
                className="bg-canvas-card rounded-xl border border-earth-sand/30 p-4 shadow-card flex items-center justify-between hover:border-earth-sand/60 transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-serif text-sm font-bold text-ink-primary">
                      {item.name}
                    </span>
                    {item.days_overdue > 0 ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-earth-amber/15 text-earth-amberText">
                        {item.days_overdue} day{item.days_overdue > 1 ? "s" : ""} overdue
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-canvas-warm text-ink-muted">
                        Due today
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-ink-muted">
                    <span className="capitalize">{item.chapter.replace("-", " ")}</span>
                    <span>•</span>
                    <span>Effective Retention: {pct}%</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => router.push(`/practice?concept=${item.concept_id}&mode=review`)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border-subtle bg-surface text-xs font-semibold text-ink-primary hover:bg-subtle transition shadow-subtle"
                  >
                    <span>Practice Now</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
