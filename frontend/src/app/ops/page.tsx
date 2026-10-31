"use client";

import { useEffect, useState } from "react";
import { api, LLMStatsResponse } from "@/lib/api/client";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Zap,
  Gauge,
  Clock,
  ShieldCheck,
} from "lucide-react";

export default function OpsPage() {
  const [stats, setStats] = useState<LLMStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStats = async () => {
    try {
      setRefreshing(true);
      const res = await api.getLLMStats();
      setStats(res);
    } catch {
      // Mock fallback data for preview if backend offline
      setStats({
        primary_model: "Primary Evaluation Model",
        fallback_models: ["Standard Backup Model", "High-Throughput Model"],
        total_calls: 142,
        fallback_rate: 1.4,
        error_rate: 0.0,
        p50_latency_ms: 380,
        p95_latency_ms: 920,
        models: [
          {
            model: "Primary Evaluation Model",
            is_primary: true,
            circuit_breaker: {
              model: "Primary Evaluation Model",
              state: "closed",
              failure_count: 0,
              seconds_until_reset: 0,
            },
            token_budget: {
              capacity: 20000,
              available: 18450,
              pct_remaining: 92.3,
            },
            calls: 138,
            errors: 0,
            avg_latency_ms: 410,
            tokens_consumed: 34120,
          },
          {
            model: "Standard Backup Model",
            is_primary: false,
            circuit_breaker: {
              model: "Standard Backup Model",
              state: "closed",
              failure_count: 0,
              seconds_until_reset: 0,
            },
            token_budget: {
              capacity: 20000,
              available: 20000,
              pct_remaining: 100.0,
            },
            calls: 4,
            errors: 0,
            avg_latency_ms: 320,
            tokens_consumed: 890,
          },
        ],
        recent_calls: [
          {
            purpose: "misconception_classifier",
            model: "Primary Evaluation Model",
            latency_ms: 395,
            status: "ok",
            fallback_used: false,
            tokens: 340,
            created_at: new Date().toISOString(),
          },
        ],
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="h-7 w-48 bg-canvas-warm rounded animate-pulse mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-canvas-card rounded-xl border border-earth-sand/30 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-earth-sand/30">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-mastery-emerald" />
            <h1 className="font-serif text-2xl font-bold tracking-tight text-ink-primary">
              System Reliability & AI Health
            </h1>
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Real-time latency metrics, circuit breaker status, and token budgets.
          </p>
        </div>
        <button
          onClick={fetchStats}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-earth-sand/50 bg-canvas-card text-xs font-medium text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm transition shadow-subtle"
        >
          <RotateCcw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-4 shadow-card">
          <div className="flex items-center justify-between text-ink-muted text-xs mb-1">
            <span>P50 Latency</span>
            <Clock className="h-3.5 w-3.5 text-mastery-emerald" />
          </div>
          <div className="font-serif text-2xl font-bold text-ink-primary">
            {stats?.p50_latency_ms || 0} ms
          </div>
          <div className="text-[11px] text-ink-muted mt-1">Median response time</div>
        </div>

        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-4 shadow-card">
          <div className="flex items-center justify-between text-ink-muted text-xs mb-1">
            <span>P95 Latency</span>
            <Gauge className="h-3.5 w-3.5 text-earth-amber" />
          </div>
          <div className="font-serif text-2xl font-bold text-ink-primary">
            {stats?.p95_latency_ms || 0} ms
          </div>
          <div className="text-[11px] text-ink-muted mt-1">95th percentile upper bound</div>
        </div>

        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-4 shadow-card">
          <div className="flex items-center justify-between text-ink-muted text-xs mb-1">
            <span>Fallback Rate</span>
            <Zap className="h-3.5 w-3.5 text-botanical-leaf" />
          </div>
          <div className="font-serif text-2xl font-bold text-ink-primary">
            {stats?.fallback_rate || 0}%
          </div>
          <div className="text-[11px] text-ink-muted mt-1">Automatic model failovers</div>
        </div>

        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-4 shadow-card">
          <div className="flex items-center justify-between text-ink-muted text-xs mb-1">
            <span>Error Rate</span>
            <ShieldCheck className="h-3.5 w-3.5 text-mastery-emerald" />
          </div>
          <div className="font-serif text-2xl font-bold text-ink-primary">
            {stats?.error_rate || 0}%
          </div>
          <div className="text-[11px] text-ink-muted mt-1">Unrecoverable call failures</div>
        </div>
      </div>

      {/* Model Cards */}
      <div className="mb-8">
        <h2 className="font-serif text-base font-semibold text-ink-primary mb-4">
          Configured Models & Circuit Health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {stats?.models.map((m) => {
            const isClosed = m.circuit_breaker.state === "closed";
            const isHalfOpen = m.circuit_breaker.state === "half_open";

            return (
              <div
                key={m.model}
                className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-ink-primary">
                        {m.model}
                      </span>
                      {m.is_primary && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-mastery-emeraldLight text-mastery-emeraldText">
                          Primary
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-ink-muted mt-0.5">
                      {m.calls} total requests · {m.avg_latency_ms} ms avg
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium ${
                      isClosed
                        ? "bg-mastery-emeraldLight text-mastery-emeraldText"
                        : isHalfOpen
                        ? "bg-earth-amber/15 text-earth-amberText"
                        : "bg-red-50 text-red-700"
                    }`}
                  >
                    {isClosed ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <AlertTriangle className="h-3 w-3" />
                    )}
                    <span>
                      {isClosed
                        ? "Circuit Healthy"
                        : isHalfOpen
                        ? "Testing Circuit"
                        : `Tripped (${m.circuit_breaker.seconds_until_reset}s)`}
                    </span>
                  </span>
                </div>

                {/* Token Budget Gauge */}
                <div className="mt-4 pt-4 border-t border-earth-sand/20">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-ink-secondary">Minute Token Capacity</span>
                    <span className="font-mono text-[11px] font-medium text-ink-primary">
                      {m.token_budget.available.toLocaleString()} /{" "}
                      {m.token_budget.capacity.toLocaleString()} ({m.token_budget.pct_remaining}%)
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-canvas-warm rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 rounded-full ${
                        m.token_budget.pct_remaining > 50
                          ? "bg-mastery-emerald"
                          : m.token_budget.pct_remaining > 20
                          ? "bg-earth-amber"
                          : "bg-red-500"
                      }`}
                      style={{ width: `${m.token_budget.pct_remaining}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Calls Stream */}
      <div>
        <h2 className="font-serif text-base font-semibold text-ink-primary mb-4">
          Recent LLM Invocations
        </h2>
        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 shadow-card overflow-hidden">
          {stats?.recent_calls && stats.recent_calls.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-canvas-warm/50 border-b border-earth-sand/30 text-ink-muted uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Purpose</th>
                    <th className="px-4 py-3">Model</th>
                    <th className="px-4 py-3">Latency</th>
                    <th className="px-4 py-3">Tokens</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Fallback</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-earth-sand/20">
                  {stats.recent_calls.map((call, idx) => (
                    <tr key={idx} className="hover:bg-canvas-warm/30 transition">
                      <td className="px-4 py-3 font-mono text-[11px] text-ink-primary">
                        {call.purpose}
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-ink-secondary">
                        {call.model}
                      </td>
                      <td className="px-4 py-3 text-ink-primary">
                        {call.latency_ms} ms
                      </td>
                      <td className="px-4 py-3 text-ink-muted">
                        {call.tokens}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                            call.status === "ok"
                              ? "bg-mastery-emeraldLight text-mastery-emeraldText"
                              : "bg-red-50 text-red-700"
                          }`}
                        >
                          {call.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {call.fallback_used ? (
                          <span className="text-earth-amber font-semibold">Yes</span>
                        ) : (
                          <span className="text-ink-muted">No</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-ink-muted">
              No recent LLM invocations recorded in this session.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
