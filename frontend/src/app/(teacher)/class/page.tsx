"use client";

import { useEffect, useState, useCallback } from "react";
import {
  api,
  ApiError,
  AtRiskStudentItem,
  CurriculumGapItem,
  MisconceptionPrevalenceItem,
  StudentDetailResponse,
  TeacherHeatmapResponse,
} from "@/lib/api/client";
import {
  Users,
  Grid,
  AlertTriangle,
  TrendingDown,
  X,
  ArrowRight,
  ShieldAlert,
  AlertCircle,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { InterventionPlannerTab } from "@/components/teacher/InterventionPlannerTab";

function getConceptAbbr(id: string): string {
  const customMap: Record<string, string> = {
    "cc-plant-hormones": "plt-h",
    "cc-animal-hormones": "anm-h",
    "lp-photosynthesis": "photo",
    "lp-nutrition": "nutr",
    "lp-stomata": "stoma",
    "lp-digestion": "digst",
    "lp-respiration": "resp",
    "lp-gas-exchange": "gas-x",
    "lp-circulation": "circ",
    "lp-vessels-blood": "vessl",
    "lp-plant-transport": "plt-t",
    "lp-excretion": "excr",
    "cc-neuron": "nerve",
    "cc-reflex": "reflx",
    "cc-brain": "brain",
    "he-variation": "var",
    "he-genes-traits": "genes",
    "he-monohybrid": "mono",
    "he-dihybrid": "dihyb",
    "he-sex-determination": "sex-d",
  };
  return customMap[id] || id.replace(/^(lp|cc|he)-/, "").slice(0, 5);
}

export default function ClassHeatmapPage() {
  const [activeTab, setActiveTab] = useState<"matrix" | "gaps" | "misconceptions" | "atrisk" | "interventions">("matrix");
  const [heatmap, setHeatmap] = useState<TeacherHeatmapResponse | null>(null);
  const [gaps, setGaps] = useState<CurriculumGapItem[]>([]);
  const [misconceptions, setMisconceptions] = useState<MisconceptionPrevalenceItem[]>([]);
  const [atRisk, setAtRisk] = useState<AtRiskStudentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Student drill-down state
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [studentDetail, setStudentDetail] = useState<StudentDetailResponse | null>(null);
  const [loadingStudent, setLoadingStudent] = useState(false);
  const [studentError, setStudentError] = useState<string | null>(null);

  // Hovered cell tooltip
  const [hoveredCell, setHoveredCell] = useState<{
    studentName: string;
    conceptName: string;
    pct: number;
    x: number;
    y: number;
  } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [hmData, gapsData, miscsData, riskData] = await Promise.all([
        api.getTeacherHeatmap(1),
        api.getTeacherGaps(1),
        api.getTeacherMisconceptions(1),
        api.getTeacherAtRisk(1),
      ]);
      setHeatmap(hmData);
      setGaps(gapsData);
      setMisconceptions(miscsData);
      setAtRisk(riskData);
    } catch (err: unknown) {
      setHeatmap(null);
      setGaps([]);
      setMisconceptions([]);
      setAtRisk([]);
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load teacher analytics data.");
      } else {
        setError("Unable to connect to the teacher analytics service. Please verify server connectivity.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSelectStudent = async (studentId: number) => {
    setSelectedStudentId(studentId);
    setLoadingStudent(true);
    setStudentError(null);
    try {
      const detail = await api.getTeacherStudentDetail(studentId, 1);
      setStudentDetail(detail);
    } catch (err: unknown) {
      setStudentDetail(null);
      if (err instanceof ApiError) {
        setStudentError(err.message || "Failed to load student breakdown.");
      } else {
        setStudentError("Network error while loading student profile.");
      }
    } finally {
      setLoadingStudent(false);
    }
  };

  // Helper mapping (student_id, concept_id) -> p_effective
  const cellMap = new Map<string, number>();
  if (heatmap) {
    for (const cell of heatmap.cells) {
      cellMap.set(`${cell.student_id}:${cell.concept_id}`, cell.p_effective);
    }
  }

  const getHeatmapColor = (p: number) => {
    if (p >= 0.80) return "bg-[#216e39] hover:ring-2 hover:ring-[#40c463] text-white font-bold";
    if (p >= 0.50) return "bg-[#30a14e] hover:ring-2 hover:ring-[#40c463] text-white font-semibold";
    if (p >= 0.35) return "bg-[#40c463] hover:ring-2 hover:ring-[#216e39] text-[#0a3622] font-semibold";
    return "bg-[#9be9a8] hover:ring-2 hover:ring-[#30a14e] text-[#0d381e] font-medium";
  };

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4">
        <div className="rounded-2xl border border-mastery-crimson/30 bg-surface p-8 shadow-subtle text-center space-y-4">
          <div className="h-12 w-12 mx-auto rounded-full bg-mastery-crimsonLight flex items-center justify-center text-mastery-crimson">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-ink-primary">
            Unable to Load Teacher Analytics
          </h2>
          <p className="text-xs text-ink-secondary max-w-md mx-auto">
            {error}
          </p>
          <div className="pt-2">
            <button
              onClick={fetchData}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ink-primary text-canvas text-xs font-semibold hover:bg-ink-primary/90 transition shadow-subtle"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-2 sm:px-4 py-4">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-earth-sand/30 bg-canvas-card p-6 shadow-card">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-mastery-emeraldText font-semibold uppercase tracking-wider bg-mastery-emeraldLight px-2 py-0.5 rounded">
              Instructor Analytics
            </span>
            <span className="text-xs text-ink-muted">• Class 10-A Biology</span>
          </div>
          <h1 className="font-serif text-2xl font-bold text-ink-primary mt-1.5">
            Classroom Knowledge Diagnostics
          </h1>
          <p className="text-xs text-ink-secondary mt-1">
            Teacher: Ms. Rao • Live BKT mastery tracking, misconception diagnosis, and curriculum gap analytics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-canvas-warm text-xs font-mono text-ink-primary border border-earth-sand/30">
            <Users className="h-3.5 w-3.5 text-mastery-emerald" />
            <span>{heatmap?.students.length ?? 0} Students Tracked</span>
          </span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-earth-sand/30 pb-2">
        <button
          onClick={() => setActiveTab("matrix")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            activeTab === "matrix"
              ? "bg-ink-primary text-canvas font-semibold shadow-subtle"
              : "text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm"
          }`}
        >
          <Grid className="h-3.5 w-3.5" />
          <span>
            Class Matrix ({heatmap ? `${heatmap.students.length} × ${heatmap.concepts.length}` : "Matrix"})
          </span>
        </button>

        <button
          onClick={() => setActiveTab("gaps")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            activeTab === "gaps"
              ? "bg-ink-primary text-canvas font-semibold shadow-subtle"
              : "text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm"
          }`}
        >
          <TrendingDown className="h-3.5 w-3.5 text-earth-amber" />
          <span>Curriculum Gaps ({gaps.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("misconceptions")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            activeTab === "misconceptions"
              ? "bg-ink-primary text-canvas font-semibold shadow-subtle"
              : "text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm"
          }`}
        >
          <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
          <span>Misconception Hotspots ({misconceptions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("atrisk")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            activeTab === "atrisk"
              ? "bg-ink-primary text-canvas font-semibold shadow-subtle"
              : "text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm"
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5 text-earth-amber" />
          <span>At-Risk Students ({atRisk.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("interventions")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            activeTab === "interventions"
              ? "bg-ink-primary text-canvas font-semibold shadow-subtle"
              : "text-ink-secondary hover:text-ink-primary hover:bg-canvas-warm"
          }`}
        >
          <Sparkles className="h-3.5 w-3.5 text-mastery-emerald" />
          <span>Intervention Planner</span>
        </button>
      </div>

      {/* Tab 1: Heatmap Matrix */}
      {activeTab === "matrix" && (
        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-serif text-sm font-bold text-ink-primary">
                Learner Mastery Matrix
              </h2>
              <p className="text-[11px] text-ink-muted">
                Hover over any cell to inspect effective mastery percentage. Click a student row to inspect their learning trajectory.
              </p>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-3 text-[11px] text-ink-secondary">
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-[#9be9a8] border border-[#85e89d]" />
                <span>&lt; 35% (Untested / Needs Prep)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-[#40c463] border border-[#34b256]" />
                <span>35 - 49% (Emerging)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-[#30a14e] border border-[#278641]" />
                <span>50 - 79% (Learning)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-[#216e39] border border-[#1b582e]" />
                <span>80%+ (Mastered)</span>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="h-96 flex items-center justify-center text-xs text-ink-muted animate-pulse">
              Loading class matrix...
            </div>
          ) : heatmap ? (
            <div className="overflow-x-auto pb-4">
              <table className="border-collapse text-left">
                <thead>
                  <tr>
                    <th className="sticky left-0 bg-canvas-card z-20 pb-3 pr-4 text-xs font-serif font-bold text-ink-primary min-w-[130px]">
                      Student
                    </th>
                    {heatmap.concepts.map((c) => (
                      <th
                        key={c.id}
                        className="pb-3 px-1 text-center font-mono text-[9px] text-ink-muted tracking-tight w-8 max-w-[36px]"
                        title={c.name}
                      >
                        <div className="truncate w-8 text-center" title={`${c.name} (${c.id})`}>
                          {getConceptAbbr(c.id)}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-earth-sand/20 text-xs">
                  {heatmap.students.map((s) => (
                    <tr
                      key={s.id}
                      onClick={() => handleSelectStudent(s.id)}
                      className="hover:bg-canvas-warm/40 cursor-pointer transition group"
                    >
                      <td className="sticky left-0 bg-canvas-card group-hover:bg-canvas-warm/40 py-1.5 pr-4 font-medium text-ink-primary truncate z-10">
                        {s.display_name}
                      </td>
                      {heatmap.concepts.map((c) => {
                        const val = cellMap.get(`${s.id}:${c.id}`) ?? 0.30;
                        const pct = Math.round(val * 100);
                        return (
                          <td key={c.id} className="p-1 text-center">
                            <div
                              onMouseEnter={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect();
                                setHoveredCell({
                                  studentName: s.display_name,
                                  conceptName: c.name,
                                  pct,
                                  x: rect.x + rect.width / 2,
                                  y: rect.y - 8,
                                });
                              }}
                              onMouseLeave={() => setHoveredCell(null)}
                              className={`h-6 w-7 rounded transition cursor-pointer flex items-center justify-center text-[9px] font-mono ${getHeatmapColor(
                                val
                              )}`}
                            >
                              <span className="opacity-0 group-hover:opacity-100 hover:opacity-100 drop-shadow-sm font-bold">
                                {pct}
                              </span>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}

      {/* Tab 2: Curriculum Gaps */}
      {activeTab === "gaps" && (
        <div className="space-y-4">
          <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
            <h2 className="font-serif text-base font-bold text-ink-primary mb-1">
              Curriculum Failure Hotspots
            </h2>
            <p className="text-xs text-ink-muted mb-4">
              Ranked from lowest to highest classroom average mastery. Prioritize these concepts during revision lessons.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {gaps.map((gap, idx) => {
                const meanPct = Math.round(gap.mean_mastery * 100);
                return (
                  <div
                    key={gap.concept_id}
                    className="p-4 rounded-xl border border-earth-sand/30 bg-canvas-warm/30 shadow-subtle flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-mono text-[10px] text-ink-muted uppercase">
                          Priority #{idx + 1} · {gap.chapter.replace("-", " ")}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-earth-amber/15 text-earth-amberText">
                          {gap.pct_below_50}% below 50%
                        </span>
                      </div>
                      <h3 className="font-serif text-sm font-bold text-ink-primary">
                        {gap.name}
                      </h3>
                    </div>

                    <div className="mt-4 pt-3 border-t border-earth-sand/20">
                      <div className="flex items-center justify-between text-xs mb-1 font-mono text-ink-muted">
                        <span>Class Average</span>
                        <span className="font-semibold text-ink-primary">{meanPct}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-canvas-warm rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            meanPct < 50 ? "bg-earth-amber" : "bg-mastery-emerald"
                          }`}
                          style={{ width: `${meanPct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Misconception Hotspots */}
      {activeTab === "misconceptions" && (
        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
          <h2 className="font-serif text-base font-bold text-ink-primary mb-1">
            Most Prevalent Classroom Misconceptions
          </h2>
          <p className="text-xs text-ink-muted mb-6">
            Diagnosed from student answer choices and free-text explanations. Address these misconceptions on the blackboard.
          </p>

          <div className="space-y-4">
            {misconceptions.map((m) => (
              <div
                key={m.misconception_id}
                className="p-4 rounded-xl border border-earth-sand/30 bg-canvas-warm/20 shadow-subtle"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="space-y-0.5">
                    <span className="font-mono text-[10px] text-ink-muted uppercase">
                      Topic: {m.concept_name}
                    </span>
                    <h3 className="font-serif text-sm font-bold text-ink-primary">
                      &quot;{m.statement}&quot;
                    </h3>
                  </div>

                  <span className="shrink-0 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-100 flex items-center gap-1.5">
                    <AlertTriangle className="h-3 w-3" />
                    <span>{m.n_students} student{m.n_students > 1 ? "s" : ""}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: At-Risk Students */}
      {activeTab === "atrisk" && (
        <div className="bg-canvas-card rounded-xl border border-earth-sand/30 p-5 shadow-card">
          <h2 className="font-serif text-base font-bold text-ink-primary mb-1">
            Learners Requiring Intervention
          </h2>
          <p className="text-xs text-ink-muted mb-6">
            Students flagged with overall mastery below 45% or with 3+ overdue review concepts.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {atRisk.map((s) => (
              <div
                key={s.student_id}
                onClick={() => handleSelectStudent(s.student_id)}
                className="p-4 rounded-xl border border-earth-sand/30 bg-canvas-warm/30 hover:border-earth-sand/60 transition cursor-pointer shadow-subtle flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-serif text-sm font-bold text-ink-primary">
                      {s.display_name}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-50 text-red-700">
                      At Risk
                    </span>
                  </div>

                  <div className="space-y-1 text-xs text-ink-secondary">
                    <div className="flex justify-between">
                      <span className="text-ink-muted">Overall Mastery:</span>
                      <span className="font-mono font-semibold">{Math.round(s.mean_mastery * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-ink-muted">Overdue Concepts:</span>
                      <span className="font-mono text-earth-amberText font-semibold">{s.overdue_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-ink-muted">Active Misconceptions:</span>
                      <span className="font-mono text-red-700 font-semibold">{s.active_misconceptions_count}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-earth-sand/20 flex items-center justify-end text-[11px] text-mastery-emerald font-semibold">
                  <span>View Breakdown</span>
                  <ArrowRight className="h-3 w-3 ml-1" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: Intervention Planner */}
      {activeTab === "interventions" && (
        <InterventionPlannerTab classroomId={1} />
      )}

      {/* Student Drill-Down Side Drawer / Modal */}
      {selectedStudentId && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-ink-primary/20 backdrop-blur-sm p-4">
          <div className="w-full max-w-md h-full bg-canvas-card rounded-2xl border border-earth-sand/40 p-6 shadow-flyout flex flex-col overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-earth-sand/30 mb-4">
              <div>
                <span className="font-mono text-[10px] text-ink-muted uppercase">Student Diagnostic</span>
                <h2 className="font-serif text-xl font-bold text-ink-primary">
                  {studentDetail?.display_name || "Student Profile"}
                </h2>
              </div>
              <button
                onClick={() => setSelectedStudentId(null)}
                className="p-1.5 rounded-lg border border-earth-sand/30 hover:bg-canvas-warm text-ink-muted hover:text-ink-primary transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {loadingStudent ? (
              <div className="flex-1 flex items-center justify-center text-xs text-ink-muted animate-pulse">
                Fetching student profile...
              </div>
            ) : studentError ? (
              <div className="p-4 rounded-lg bg-mastery-crimsonLight text-mastery-crimsonText text-xs">
                {studentError}
              </div>
            ) : studentDetail ? (
              <div className="space-y-5">
                {/* Overall Score */}
                <div className="p-3 bg-canvas-warm/40 rounded-xl border border-earth-sand/30 flex items-center justify-between">
                  <span className="text-xs text-ink-secondary">Overall Effective Mastery</span>
                  <span className="font-serif text-lg font-bold text-ink-primary">
                    {Math.round(studentDetail.overall_mastery * 100)}%
                  </span>
                </div>

                {/* Active Misconceptions */}
                <div>
                  <h3 className="font-serif text-xs font-bold text-ink-primary uppercase tracking-wider mb-2">
                    Active Misconceptions ({studentDetail.active_misconceptions.length})
                  </h3>
                  {studentDetail.active_misconceptions.length === 0 ? (
                    <p className="text-xs text-ink-muted">No active misconceptions detected.</p>
                  ) : (
                    <div className="space-y-2">
                      {studentDetail.active_misconceptions.map((m) => (
                        <div
                          key={m.misconception_id}
                          className="p-2.5 rounded-lg border border-red-200 bg-red-50/50 text-xs text-red-900 leading-snug"
                        >
                          {m.statement}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Concept Masteries */}
                <div>
                  <h3 className="font-serif text-xs font-bold text-ink-primary uppercase tracking-wider mb-2">
                    Concept Mastery Breakdown
                  </h3>
                  <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                    {studentDetail.masteries.map((m) => {
                      const effPct = Math.round(m.p_effective * 100);
                      return (
                        <div
                          key={m.concept_id}
                          className="p-2.5 rounded-lg border border-earth-sand/30 bg-canvas-warm/20 text-xs"
                        >
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-medium text-ink-primary">{m.concept_name}</span>
                            <span className="font-mono text-[11px] text-ink-muted">{effPct}%</span>
                          </div>
                          <div className="h-1 w-full bg-canvas-warm rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                effPct >= 80
                                  ? "bg-mastery-emerald"
                                  : effPct >= 50
                                  ? "bg-botanical-leaf"
                                  : "bg-earth-sand"
                              }`}
                              style={{ width: `${effPct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Floating cell tooltip */}
      {hoveredCell && (
        <div
          className="fixed pointer-events-none z-50 -translate-x-1/2 -translate-y-full px-2.5 py-1.5 rounded-lg bg-ink-primary text-canvas text-[11px] shadow-flyout whitespace-nowrap"
          style={{ left: hoveredCell.x, top: hoveredCell.y }}
        >
          <div className="font-semibold">{hoveredCell.studentName}</div>
          <div className="text-canvas/80 text-[10px]">
            {hoveredCell.conceptName}: {hoveredCell.pct}%
          </div>
        </div>
      )}
    </div>
  );
}
