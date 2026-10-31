"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  Layers,
  RotateCcw,
  Sparkles,
  Compass,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
  Box,
  CircleDot,
  Info,
  ChevronRight,
  X,
} from "lucide-react";
import { api, type DiagramManifest, type DiagramAssessmentResponse } from "@/lib/api/client";
import { Biological3DViewer } from "@/components/lab/Biological3DViewer";
import { Biological2DAtlas } from "@/components/lab/Biological2DAtlas";
import { PipTeachSlideOver } from "@/components/lab/PipTeachSlideOver";
import { cells, getCellById, type ViewMode } from "@/data/cells";

export default function InteractiveBiologyLabPage() {
  const [selectedDiagramId, setSelectedDiagramId] = useState<string>("plant");
  const [manifest, setManifest] = useState<DiagramManifest | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // View & Mode controls
  const [renderMode, setRenderMode] = useState<"3d" | "2d">("3d");
  const [stageViewMode, setStageViewMode] = useState<ViewMode>("mesh");
  const [crossSection, setCrossSection] = useState<boolean>(false);
  const [autoRotate, setAutoRotate] = useState<boolean>(false);
  const [resetKey, setResetKey] = useState<number>(0);
  const [isAssessmentMode, setIsAssessmentMode] = useState<boolean>(false);

  // Structure interaction states: string or null when empty space is clicked
  const [activeOrganelleId, setActiveOrganelleId] = useState<string | null>("nucleus");

  // Pip Teach-Back slide-over state
  const [isTeachingPip, setIsTeachingPip] = useState<boolean>(false);

  // Assessment state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [assessmentResult, setAssessmentResult] = useState<DiagramAssessmentResponse | null>(null);
  const [isSubmittingAssessment, setIsSubmittingAssessment] = useState<boolean>(false);
  const [showHint, setShowHint] = useState<boolean>(false);

  const activeCell = getCellById(selectedDiagramId);

  // Fetch diagram manifest on specimen selection
  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    setAssessmentResult(null);
    setShowHint(false);

    api
      .getDiagramManifest(selectedDiagramId)
      .then((data) => {
        if (isMounted) {
          setManifest(data);
          const firstOrganelle = activeCell.organelles[0]?.id || data.structures?.[0]?.id || "nucleus";
          setActiveOrganelleId(firstOrganelle);
          setCurrentQuestionIndex(0);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn("Backend manifest fetch failed, falling back to local specimen data:", err);
          // Resilient client-side fallback
          setManifest({
            id: activeCell.id,
            concept_id: activeCell.id === "plant" ? "lp-photosynthesis" : "lp-respiration",
            chapter: "life-processes",
            display_name: activeCell.name,
            subtitle: activeCell.type,
            model_type: "cellular_organelles",
            structures: activeCell.organelles.map((o) => ({
              id: o.id,
              name: o.name,
              aliases: [o.name.toLowerCase()],
              description: o.note,
              function: o.subtitle,
              color: o.color,
            })),
            assessments: [],
          });
          const firstOrganelle = activeCell.organelles[0]?.id || "nucleus";
          setActiveOrganelleId(firstOrganelle);
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedDiagramId, activeCell.id, activeCell.name, activeCell.type, activeCell.organelles]);

  const activeQuestion = manifest?.assessments?.[currentQuestionIndex] || null;
  const currentOrganelle = activeOrganelleId
    ? activeCell.organelles.find((o) => o.id === activeOrganelleId) || null
    : null;

  // Submit assessment answer
  const handleAnswerSubmit = async (structureId?: string, explanationText?: string) => {
    if (!activeQuestion || isSubmittingAssessment) return;
    setIsSubmittingAssessment(true);
    try {
      const attemptId = crypto.randomUUID();
      const res = await api.submitDiagramAssessment(selectedDiagramId, {
        client_attempt_id: attemptId,
        diagram_id: selectedDiagramId,
        question_id: activeQuestion.id,
        assessment_type: activeQuestion.type,
        selected_structure_id: structureId || activeOrganelleId || null,
        selected_sequence: activeQuestion.type === "sequence" && activeOrganelleId ? [activeOrganelleId] : null,
        explanation_text: explanationText || null,
      });
      setAssessmentResult(res);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Assessment submission failed.");
    } finally {
      setIsSubmittingAssessment(false);
    }
  };

  const handleResetViewport = () => {
    setStageViewMode("mesh");
    setCrossSection(false);
    setAutoRotate(false);
    setResetKey((prev) => prev + 1);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin" />
          <p className="text-sm font-medium text-ink-secondary">Loading biological specimen...</p>
        </div>
      </div>
    );
  }

  if (error || !manifest) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-surface border border-red-200 rounded-lg p-6 text-center shadow-xs">
          <ShieldAlert className="w-10 h-10 text-red-600 mx-auto mb-3" />
          <h2 className="text-base font-semibold text-ink-primary mb-1">Specimen Load Error</h2>
          <p className="text-sm text-ink-secondary mb-4">{error || "Unable to load diagram."}</p>
          <button
            onClick={() => setSelectedDiagramId("plant")}
            className="px-4 py-2 bg-emerald-700 text-white rounded-md text-sm font-medium hover:bg-emerald-800 transition-colors shadow-xs"
          >
            Load Plant Cell Specimen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas text-ink-primary flex flex-col">
      {/* Top Laboratory Navigation Bar */}
      <header className="border-b border-border-subtle bg-surface px-4 py-3 sm:px-6 flex flex-wrap items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-700 shrink-0">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink-primary leading-tight font-display">
              {activeCell.name}
            </h1>
            <p className="text-xs text-ink-secondary hidden sm:block">
              {manifest.subtitle || activeCell.type}
            </p>
          </div>
        </div>

        {/* Specimen Switcher & Mode Toggles */}
        <div className="flex items-center gap-2">
          {/* Specimen Selector */}
          <select
            value={selectedDiagramId}
            onChange={(e) => {
              setSelectedDiagramId(e.target.value);
              setStageViewMode("mesh");
              setCrossSection(false);
            }}
            className="px-2.5 py-1.5 text-xs font-medium bg-subtle border border-border-subtle rounded-md text-ink-primary focus:outline-none focus:ring-1 focus:ring-emerald-600 cursor-pointer"
          >
            {cells.map((cell) => (
              <option key={cell.id} value={cell.id}>
                {cell.name} ({cell.type})
              </option>
            ))}
          </select>

          {/* 3D vs 2D Toggle */}
          <div className="flex items-center bg-subtle p-0.5 rounded-md border border-border-subtle text-xs">
            <button
              onClick={() => setRenderMode("3d")}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                renderMode === "3d" ? "bg-surface text-emerald-800 shadow-xs" : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              3D Studio
            </button>
            <button
              onClick={() => setRenderMode("2d")}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                renderMode === "2d" ? "bg-surface text-emerald-800 shadow-xs" : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              2D Atlas
            </button>
          </div>

          {/* Assessment Mode Toggle */}
          <button
            onClick={() => {
              setIsAssessmentMode(!isAssessmentMode);
              setAssessmentResult(null);
            }}
            className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs ${
              isAssessmentMode
                ? "bg-amber-600 text-white hover:bg-amber-700"
                : "bg-emerald-700 text-white hover:bg-emerald-800"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>{isAssessmentMode ? "Exit Assessment" : "Start Assessment"}</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Stage */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 p-4 sm:p-6 max-w-7xl mx-auto w-full">
        {/* Left / Center: Interactive 3D Biological Viewport (7 or 8 columns) */}
        <section className="lg:col-span-8 flex flex-col gap-3 min-h-[520px]">
          <div className="relative flex-1 bg-surface border border-border-subtle rounded-xl shadow-xs overflow-hidden flex flex-col">
            {/* Viewport Control Bar */}
            <div className="px-3.5 py-2.5 border-b border-border-subtle bg-subtle/50 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-medium text-ink-secondary flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-emerald-600" />
                  <span>{renderMode === "3d" ? "Cell Architecture Studio 3D" : "2D Schematic Atlas"}</span>
                </span>
                {stageViewMode === "focus" && (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-semibold flex items-center gap-1">
                    <CircleDot className="w-3 h-3" /> Focus Mode Active
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {renderMode === "3d" && (
                  <>
                    {/* View mode toggle (Mesh vs Focus) */}
                    <div className="flex items-center bg-surface p-0.5 rounded border border-border-subtle text-[11px]">
                      <button
                        onClick={() => setStageViewMode("mesh")}
                        className={`px-2 py-0.5 rounded font-medium flex items-center gap-1 transition-colors ${
                          stageViewMode === "mesh"
                            ? "bg-subtle text-ink-primary font-semibold"
                            : "text-ink-secondary hover:text-ink-primary"
                        }`}
                        title="Render complete specimen mesh"
                      >
                        <Box className="w-3 h-3" />
                        Mesh
                      </button>
                      <button
                        onClick={() => setStageViewMode("focus")}
                        className={`px-2 py-0.5 rounded font-medium flex items-center gap-1 transition-colors ${
                          stageViewMode === "focus"
                            ? "bg-emerald-50 text-emerald-800 font-semibold"
                            : "text-ink-secondary hover:text-ink-primary"
                        }`}
                        title="Focus and isolate active organelle"
                      >
                        <CircleDot className="w-3 h-3" />
                        Focus
                      </button>
                    </div>

                    {/* Cutaway cross-section toggle */}
                    <button
                      onClick={() => setCrossSection(!crossSection)}
                      className={`px-2.5 py-1 rounded text-[11px] font-medium border border-border-subtle transition-colors ${
                        crossSection
                          ? "bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold"
                          : "bg-surface text-ink-secondary hover:text-ink-primary"
                      }`}
                      title="Toggle cutaway interior cross section"
                    >
                      {crossSection ? "Cross Section On" : "Cross Section"}
                    </button>

                    {/* Auto-rotate toggle */}
                    <button
                      onClick={() => setAutoRotate(!autoRotate)}
                      className={`px-2.5 py-1 rounded text-[11px] font-medium border border-border-subtle transition-colors ${
                        autoRotate
                          ? "bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold"
                          : "bg-surface text-ink-secondary hover:text-ink-primary"
                      }`}
                      title="Toggle continuous rotation"
                    >
                      {autoRotate ? "Rotating" : "Rotate"}
                    </button>
                  </>
                )}

                {/* Reset Viewport */}
                <button
                  onClick={handleResetViewport}
                  title="Reset viewport camera and state"
                  className="p-1 hover:bg-surface rounded text-ink-secondary hover:text-ink-primary transition-colors flex items-center gap-1 ml-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span className="text-[11px] hidden sm:inline">Reset</span>
                </button>
              </div>
            </div>

            {/* Viewport Canvas (Spacious, Unconstrained Biological Canvas) */}
            <div className="flex-1 w-full relative min-h-[460px] bg-[#fbf7ee]">
              {renderMode === "3d" ? (
                <Biological3DViewer
                  cell={activeCell}
                  activeOrganelle={activeOrganelleId}
                  onSelectOrganelle={(id) => setActiveOrganelleId(id)}
                  onClearSelection={() => setActiveOrganelleId(null)}
                  viewMode={stageViewMode}
                  crossSection={crossSection}
                  autoRotate={autoRotate}
                  resetKey={resetKey}
                  onReset={handleResetViewport}
                />
              ) : (
                <Biological2DAtlas
                  diagramId={selectedDiagramId}
                  selectedStructureId={activeOrganelleId || ""}
                  onSelectStructure={(id) => setActiveOrganelleId(id)}
                />
              )}

              {/* Discreet Viewport Interaction Hint */}
              <div className="absolute bottom-3 left-3 bg-surface/90 backdrop-blur-xs border border-border-subtle rounded-md px-2.5 py-1 text-[11px] text-ink-muted pointer-events-none shadow-xs select-none flex items-center gap-2">
                <span>Click structures to inspect</span>
                <span>•</span>
                <span>Drag to rotate</span>
                <span>•</span>
                <span>Scroll to zoom</span>
              </div>
            </div>
          </div>
        </section>

        {/* Right: Structure Directory & Inspector or Assessment Panel (4 or 5 columns) */}
        <aside className="lg:col-span-4 flex flex-col gap-4">
          {/* Structure Quick-Select Rail */}
          <div className="bg-surface border border-border-subtle rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2 mb-3">
              <span className="text-xs font-semibold text-ink-primary font-display flex items-center gap-1.5">
                <Box className="w-3.5 h-3.5 text-emerald-700" />
                Cell Structures ({activeCell.organelles.length})
              </span>
              {activeOrganelleId && (
                <button
                  onClick={() => setActiveOrganelleId(null)}
                  className="text-[11px] text-ink-muted hover:text-ink-primary flex items-center gap-0.5"
                  title="Deselect active structure"
                >
                  <X className="w-3 h-3" />
                  <span>Clear</span>
                </button>
              )}
            </div>

            <div className="space-y-1">
              {activeCell.organelles.map((organelle) => {
                const isSelected = activeOrganelleId === organelle.id;
                return (
                  <button
                    key={organelle.id}
                    onClick={() => setActiveOrganelleId(organelle.id)}
                    className={`w-full px-2.5 py-2 rounded-lg text-left text-xs flex items-center justify-between transition-colors ${
                      isSelected
                        ? "bg-emerald-50 border border-emerald-300/80 text-emerald-950 font-medium shadow-xs"
                        : "hover:bg-subtle text-ink-primary border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0 ring-1 ring-border-subtle"
                        style={{ backgroundColor: organelle.color }}
                      />
                      <div className="truncate">
                        <span className="font-semibold block truncate leading-tight">{organelle.name}</span>
                        {organelle.subtitle && (
                          <span className="text-[10px] text-ink-muted block truncate font-normal">
                            {organelle.subtitle}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight
                      className={`w-3.5 h-3.5 shrink-0 transition-transform ${
                        isSelected ? "text-emerald-700 translate-x-0.5" : "text-ink-muted"
                      }`}
                    />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Conditional: Assessment Mode vs Structure Context Inspector */}
          {isAssessmentMode && activeQuestion ? (
            /* Active Assessment Card */
            <div className="bg-surface border border-border-subtle rounded-xl p-4 shadow-xs flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-border-subtle pb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
                  Question {currentQuestionIndex + 1} of {manifest.assessments?.length || 1}
                </span>
                <span className="text-xs font-mono text-ink-muted capitalize">
                  {activeQuestion.type}
                </span>
              </div>

              <div>
                <p className="text-xs font-medium text-ink-secondary mb-1">Task Prompt:</p>
                <h3 className="text-sm font-semibold text-ink-primary font-display leading-snug">
                  {activeQuestion.prompt}
                </h3>
              </div>

              {/* Assessment Type Specific Actions */}
              {activeQuestion.type === "identification" && (
                <div className="p-3 bg-subtle rounded-lg border border-border-subtle flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-ink-secondary">Selected structure:</span>
                    <span className="font-semibold text-emerald-800 capitalize">
                      {currentOrganelle ? currentOrganelle.name : "None selected"}
                    </span>
                  </div>
                  <button
                    disabled={isSubmittingAssessment || !currentOrganelle}
                    onClick={() => handleAnswerSubmit()}
                    className="w-full py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white rounded-lg font-semibold text-xs shadow-xs transition-colors"
                  >
                    {isSubmittingAssessment ? "Evaluating..." : "Confirm Identification"}
                  </button>
                </div>
              )}

              {/* Hint Accordion */}
              {activeQuestion.hint && (
                <div>
                  <button
                    onClick={() => setShowHint(!showHint)}
                    className="text-xs text-emerald-700 hover:underline flex items-center gap-1 font-medium"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                    <span>{showHint ? "Hide Scientific Hint" : "Need a Hint?"}</span>
                  </button>
                  {showHint && (
                    <p className="mt-1.5 p-2 bg-emerald-50/70 border border-emerald-200 rounded text-xs text-emerald-900 italic">
                      {activeQuestion.hint}
                    </p>
                  )}
                </div>
              )}

              {/* Assessment Evaluation Reveal */}
              {assessmentResult && (
                <div
                  className={`p-3.5 rounded-lg border flex flex-col gap-2 ${
                    assessmentResult.is_correct
                      ? "bg-emerald-50 border-emerald-200 text-emerald-950"
                      : "bg-red-50 border-red-200 text-red-950"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {assessmentResult.is_correct ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600 shrink-0" />
                    )}
                    <span className="text-sm font-semibold">
                      {assessmentResult.is_correct ? "Mastery Demonstrated!" : "Incomplete Explanation"}
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed">{assessmentResult.feedback}</p>

                  {/* Next Question Navigation */}
                  <div className="mt-2 flex items-center justify-end">
                    {currentQuestionIndex + 1 < (manifest.assessments?.length || 0) ? (
                      <button
                        onClick={() => {
                          setCurrentQuestionIndex((prev) => prev + 1);
                          setAssessmentResult(null);
                          setShowHint(false);
                        }}
                        className="px-3 py-1.5 bg-emerald-700 text-white rounded text-xs font-semibold hover:bg-emerald-800 flex items-center gap-1 shadow-xs"
                      >
                        <span>Next Question</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          setIsAssessmentMode(false);
                          setAssessmentResult(null);
                        }}
                        className="px-3 py-1.5 bg-surface border border-border-subtle text-ink-primary rounded text-xs font-medium hover:bg-subtle"
                      >
                        Return to Exploration
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : currentOrganelle ? (
            /* Selected Organelle Context Inspector Card */
            <div className="bg-surface border border-border-subtle rounded-xl p-4 shadow-xs flex flex-col gap-3.5">
              {/* Card Header */}
              <div className="flex items-center justify-between border-b border-border-subtle pb-2.5">
                <div className="flex items-center gap-2.5">
                  <span
                    className="w-3.5 h-3.5 rounded-full shrink-0 ring-1 ring-border-subtle"
                    style={{ backgroundColor: currentOrganelle.color }}
                  />
                  <div>
                    <h3 className="text-sm font-semibold text-ink-primary font-display leading-tight">
                      {currentOrganelle.name}
                    </h3>
                    {currentOrganelle.subtitle && (
                      <span className="text-[11px] font-medium text-ink-muted">
                        {currentOrganelle.subtitle}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Contextual Action: Teach this to Pip */}
              <div className="p-3 bg-emerald-50/70 border border-emerald-200/80 rounded-xl flex flex-col gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-serif text-xs font-bold shrink-0">
                    Pip
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-emerald-950">
                      Teach this to Pip
                    </h4>
                    <p className="text-[11px] text-emerald-800 leading-tight">
                      Explain {currentOrganelle.name}&apos;s role to Pip and test your mastery.
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setIsTeachingPip(true)}
                  className="w-full mt-1 py-2 px-3 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-xs"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Start Teaching Dialogue</span>
                </button>
              </div>

              {/* Attributes Grid */}
              {currentOrganelle.attributes && currentOrganelle.attributes.length > 0 && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {currentOrganelle.attributes.map((attr, idx) => (
                    <div key={idx} className="p-2 bg-subtle rounded-md border border-border-subtle/50">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-ink-muted block">
                        {attr.label}
                      </span>
                      <span className="font-medium text-ink-primary mt-0.5 block">
                        {attr.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Scientific Note */}
              {currentOrganelle.note && (
                <div className="text-xs bg-canvas p-2.5 rounded-lg border border-border-subtle">
                  <span className="font-semibold text-ink-primary block mb-1">Biological Context:</span>
                  <p className="text-ink-secondary leading-relaxed">{currentOrganelle.note}</p>
                </div>
              )}

              {/* Scientific Fact */}
              {currentOrganelle.fact && (
                <div className="text-xs p-2.5 bg-subtle rounded-lg border border-border-subtle">
                  <span className="font-semibold text-ink-primary flex items-center gap-1 mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-amber-600" /> Key Observation:
                  </span>
                  <p className="text-ink-secondary leading-relaxed">{currentOrganelle.fact}</p>
                </div>
              )}

              {/* Viewport Control Shortcuts */}
              <div className="pt-2 border-t border-border-subtle flex items-center gap-2">
                <button
                  onClick={() => {
                    setStageViewMode(stageViewMode === "focus" ? "mesh" : "focus");
                  }}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium border flex items-center justify-center gap-1.5 transition-colors ${
                    stageViewMode === "focus"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold"
                      : "bg-surface text-ink-primary border-border-subtle hover:bg-subtle"
                  }`}
                >
                  <CircleDot className="w-3.5 h-3.5" />
                  <span>{stageViewMode === "focus" ? "Show Whole Specimen" : "Focus Structure"}</span>
                </button>
              </div>
            </div>
          ) : (
            /* Calm Empty State when no organelle is selected */
            <div className="bg-surface border border-border-subtle rounded-xl p-5 shadow-xs flex flex-col gap-3">
              <div className="flex items-center gap-2 text-ink-primary">
                <Info className="w-4 h-4 text-emerald-700 shrink-0" />
                <h3 className="text-sm font-semibold font-display">Select a Structure to Explore</h3>
              </div>

              <p className="text-xs text-ink-secondary leading-relaxed">
                Click any 3D marker on the specimen or select a cellular structure from the list above to inspect its biological mechanism and teach it to Pip.
              </p>

              <div className="mt-1 p-3 bg-subtle rounded-lg border border-border-subtle space-y-2 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-ink-muted block">
                    Occurrence ({activeCell.occurrence.title}):
                  </span>
                  <p className="text-ink-secondary mt-0.5 leading-relaxed">{activeCell.occurrence.body}</p>
                </div>

                {activeCell.clinicalContext && (
                  <div className="pt-2 border-t border-border-subtle/50">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-ink-muted block">
                      Clinical Context:
                    </span>
                    <p className="text-ink-secondary mt-0.5 leading-relaxed">{activeCell.clinicalContext}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </aside>
      </main>

      {/* Pip Teach-Back Interactive Slide-Over */}
      {currentOrganelle && (
        <PipTeachSlideOver
          isOpen={isTeachingPip}
          onClose={() => setIsTeachingPip(false)}
          cell={activeCell}
          organelle={currentOrganelle}
          conceptId={manifest?.concept_id || "lp-photosynthesis"}
        />
      )}
    </div>
  );
}
