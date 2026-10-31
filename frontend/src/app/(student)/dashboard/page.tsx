"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, ConceptEdge, ConceptNode } from "@/lib/api/client";
import { ConceptGraphView } from "@/components/graph/ConceptGraphView";
import { ArrowRight, RefreshCw } from "lucide-react";

// Robust fallback data for instantaneous demo stability
const FALLBACK_NODES: ConceptNode[] = [
  { id: "lp-nutrition", name: "Modes of Nutrition", chapter: "life-processes", position: 1, mastery: { p_effective: 0.65, status: "learning" } },
  { id: "lp-photosynthesis", name: "Photosynthesis", chapter: "life-processes", position: 2, mastery: { p_effective: 0.42, status: "learning" } },
  { id: "lp-stomata", name: "Stomata & Gas Exchange", chapter: "life-processes", position: 3, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "lp-digestion", name: "Human Alimentary Canal", chapter: "life-processes", position: 4, mastery: { p_effective: 0.82, status: "mastered" } },
  { id: "lp-respiration", name: "Cellular Respiration", chapter: "life-processes", position: 5, mastery: { p_effective: 0.70, status: "learning" } },
  { id: "lp-gas-exchange", name: "Breathing & Alveoli", chapter: "life-processes", position: 6, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "lp-circulation", name: "Heart & Double Circulation", chapter: "life-processes", position: 7, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "lp-vessels-blood", name: "Blood Vessels & Lymph", chapter: "life-processes", position: 8, mastery: { p_effective: 0.25, status: "locked" } },
  { id: "lp-plant-transport", name: "Vascular Transport in Plants", chapter: "life-processes", position: 9, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "lp-excretion", name: "Excretion & Nephron", chapter: "life-processes", position: 10, mastery: { p_effective: 0.25, status: "locked" } },
  { id: "cc-neuron", name: "Neuron & Nerve Impulse", chapter: "control-coordination", position: 11, mastery: { p_effective: 0.75, status: "learning" } },
  { id: "cc-reflex", name: "Reflex Action & Arc", chapter: "control-coordination", position: 12, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "cc-brain", name: "Human Brain Structure", chapter: "control-coordination", position: 13, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "cc-plant-hormones", name: "Plant Hormones & Tropisms", chapter: "control-coordination", position: 14, mastery: { p_effective: 0.85, status: "mastered" } },
  { id: "cc-animal-hormones", name: "Endocrine Hormones", chapter: "control-coordination", position: 15, mastery: { p_effective: 0.35, status: "unlocked" } },
  { id: "he-variation", name: "Variation & Evolution", chapter: "heredity", position: 16, mastery: { p_effective: 0.60, status: "learning" } },
  { id: "he-genes-traits", name: "Genes & Inheritance", chapter: "heredity", position: 17, mastery: { p_effective: 0.30, status: "unlocked" } },
  { id: "he-monohybrid", name: "Mendel Monohybrid Cross", chapter: "heredity", position: 18, mastery: { p_effective: 0.25, status: "locked" } },
  { id: "he-dihybrid", name: "Dihybrid Cross", chapter: "heredity", position: 19, mastery: { p_effective: 0.20, status: "locked" } },
  { id: "he-sex-determination", name: "Sex Determination", chapter: "heredity", position: 20, mastery: { p_effective: 0.25, status: "locked" } },
];

const FALLBACK_EDGES: ConceptEdge[] = [
  { from: "lp-nutrition", to: "lp-photosynthesis" },
  { from: "lp-nutrition", to: "lp-digestion" },
  { from: "lp-nutrition", to: "lp-respiration" },
  { from: "lp-photosynthesis", to: "lp-stomata" },
  { from: "lp-stomata", to: "lp-plant-transport" },
  { from: "lp-respiration", to: "lp-gas-exchange" },
  { from: "lp-gas-exchange", to: "lp-circulation" },
  { from: "lp-circulation", to: "lp-vessels-blood" },
  { from: "lp-circulation", to: "lp-excretion" },
  { from: "cc-neuron", to: "cc-reflex" },
  { from: "cc-neuron", to: "cc-brain" },
  { from: "he-variation", to: "he-genes-traits" },
  { from: "he-genes-traits", to: "he-monohybrid" },
  { from: "he-genes-traits", to: "he-sex-determination" },
  { from: "he-monohybrid", to: "he-dihybrid" },
];

export default function StudentDashboardPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["concept-graph"],
    queryFn: () => api.getConceptGraph(),
    retry: 1,
  });

  const nodes = data?.nodes && data.nodes.length > 0 ? data.nodes : FALLBACK_NODES;
  const edges = data?.edges && data.edges.length > 0 ? data.edges : FALLBACK_EDGES;

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
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-xl">
            Interactive curriculum prerequisite tree across 20 Class 10 Biology concepts. Click any concept node to read notes, launch practice, or explain to Pip.
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
            className="inline-flex items-center gap-1 text-[11px] font-mono text-ink-muted hover:text-ink-primary transition"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        <ConceptGraphView nodes={nodes} edges={edges} />
      </div>
    </div>
  );
}
