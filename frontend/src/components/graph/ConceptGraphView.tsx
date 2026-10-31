"use client";

import { useMemo, useState } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  Edge,
  Node,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ConceptEdge, ConceptNode } from "@/lib/api/client";
import { ConceptNodeComponent, ConceptNodeData } from "./ConceptNodeComponent";
import { CurvedTreeEdge } from "./CurvedTreeEdge";
import { ConceptDetailModal } from "./ConceptDetailModal";

// Geometrically balanced node positions maintaining strict hierarchical parent-child relationships
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  // Chapter 1: Life Processes
  // Symmetrically centered root node 'lp-nutrition' branching to photosynthesis (50), digestion (220), and respiration (390)
  "lp-nutrition": { x: 50, y: 220 },
  "lp-photosynthesis": { x: 360, y: 50 },
  "lp-digestion": { x: 360, y: 220 },
  "lp-respiration": { x: 360, y: 390 },
  "lp-stomata": { x: 670, y: 50 },
  "lp-gas-exchange": { x: 670, y: 390 },
  "lp-plant-transport": { x: 980, y: 50 },
  "lp-circulation": { x: 980, y: 390 },
  "lp-vessels-blood": { x: 1290, y: 320 },
  "lp-excretion": { x: 1290, y: 460 },

  // Chapter 2: Control & Coordination
  // Symmetrically centered root node 'cc-neuron' branching to reflex (590) and brain (730)
  "cc-neuron": { x: 50, y: 660 },
  "cc-reflex": { x: 360, y: 590 },
  "cc-brain": { x: 360, y: 730 },
  "cc-plant-hormones": { x: 50, y: 880 },
  "cc-animal-hormones": { x: 360, y: 880 },

  // Chapter 3: Heredity
  // Symmetrically centered root node 'he-variation' leading to 'he-genes-traits'
  "he-variation": { x: 50, y: 1090 },
  "he-genes-traits": { x: 360, y: 1090 },
  "he-monohybrid": { x: 670, y: 1020 },
  "he-sex-determination": { x: 670, y: 1160 },
  "he-dihybrid": { x: 980, y: 1020 },
};

interface ConceptGraphViewProps {
  nodes: ConceptNode[];
  edges: ConceptEdge[];
}

export function ConceptGraphView({ nodes, edges }: ConceptGraphViewProps) {
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);

  const nodeTypes = useMemo(() => ({ conceptNode: ConceptNodeComponent }), []);
  const edgeTypes = useMemo(() => ({ curvedTreeEdge: CurvedTreeEdge }), []);

  const nodesMap = useMemo(() => {
    return new Map<string, ConceptNode>(nodes.map((n) => [n.id, n]));
  }, [nodes]);

  const flowNodes: Node[] = useMemo(() => {
    return nodes.map((node) => {
      const pos = NODE_POSITIONS[node.id] || { x: 50, y: 50 };
      const isSelected = selectedConceptId === node.id;
      const nodeData: ConceptNodeData = {
        id: node.id,
        name: node.name,
        chapter: node.chapter,
        position: node.position,
        mastery: node.mastery,
        isSelected,
        onSelect: (id: string) => setSelectedConceptId(id),
      };

      return {
        id: node.id,
        type: "conceptNode",
        position: pos,
        data: nodeData,
      };
    });
  }, [nodes, selectedConceptId]);

  const flowEdges: Edge[] = useMemo(() => {
    return edges.map((edge, idx) => {
      const isHighlighted =
        selectedConceptId === edge.from || selectedConceptId === edge.to;

      const sourceNode = nodesMap.get(edge.from);
      const targetNode = nodesMap.get(edge.to);

      // Path active if source prerequisite is mastered (>=60% or status mastered/learning)
      const sourceMastery = sourceNode?.mastery?.p_effective ?? 0;
      const sourceStatus = sourceNode?.mastery?.status ?? "ready";
      const isActive =
        sourceStatus === "mastered" ||
        sourceStatus === "learning" ||
        sourceMastery >= 0.6;

      const isLocked = targetNode?.mastery?.status === "locked";

      const arrowColor = isHighlighted
        ? "#2E7D32"
        : isActive
        ? "#94A3B8"
        : "#CBD5E1";

      return {
        id: `e-${edge.from}-${edge.to}-${idx}`,
        source: edge.from,
        target: edge.to,
        type: "curvedTreeEdge",
        animated: false,
        data: {
          isHighlighted,
          isActive,
          isLocked,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: arrowColor,
          width: 12,
          height: 12,
        },
      };
    });
  }, [edges, selectedConceptId, nodesMap]);

  const selectedNode = selectedConceptId ? nodesMap.get(selectedConceptId) : null;

  return (
    <div className="relative w-full h-[680px] rounded-2xl border border-border-subtle bg-surface/50 overflow-hidden shadow-subtle">
      {/* Chapter Legends */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-surface/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-border-subtle shadow-subtle text-xs">
        <span className="font-mono text-[10px] text-ink-muted uppercase mr-1">Chapters:</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-mastery-emerald" />
          <span className="text-[11px] font-medium text-ink-secondary">Life Processes</span>
        </span>
        <span className="inline-flex items-center gap-1.5 ml-2">
          <span className="h-2 w-2 rounded-full bg-mastery-amber" />
          <span className="text-[11px] font-medium text-ink-secondary">Control & Coord</span>
        </span>
        <span className="inline-flex items-center gap-1.5 ml-2">
          <span className="h-2 w-2 rounded-full bg-mastery-slate" />
          <span className="text-[11px] font-medium text-ink-secondary">Heredity</span>
        </span>
      </div>

      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        className="bg-canvas"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#E5E3D8"
        />
        <Controls className="!bg-surface !border-border-subtle !shadow-subtle !rounded-lg overflow-hidden" />
      </ReactFlow>

      {/* Detail Modal */}
      <ConceptDetailModal
        conceptId={selectedConceptId}
        selectedNode={selectedNode}
        onClose={() => setSelectedConceptId(null)}
        onSelectConcept={(id) => setSelectedConceptId(id)}
      />
    </div>
  );
}
