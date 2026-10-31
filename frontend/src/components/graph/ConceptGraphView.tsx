"use client";

import { useMemo, useState } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  Edge,
  Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ConceptEdge, ConceptNode } from "@/lib/api/client";
import { ConceptNodeComponent, ConceptNodeData } from "./ConceptNodeComponent";
import { ConceptDetailModal } from "./ConceptDetailModal";

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  // Chapter 1: Life Processes
  "lp-nutrition": { x: 50, y: 100 },
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
  "cc-neuron": { x: 50, y: 640 },
  "cc-reflex": { x: 360, y: 590 },
  "cc-brain": { x: 360, y: 730 },
  "cc-plant-hormones": { x: 50, y: 880 },
  "cc-animal-hormones": { x: 360, y: 880 },

  // Chapter 3: Heredity
  "he-variation": { x: 50, y: 1080 },
  "he-genes-traits": { x: 360, y: 1080 },
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

  const flowNodes: Node[] = useMemo(() => {
    return nodes.map((node) => {
      const pos = NODE_POSITIONS[node.id] || { x: 50, y: 50 };
      const nodeData: ConceptNodeData = {
        id: node.id,
        name: node.name,
        chapter: node.chapter,
        position: node.position,
        mastery: node.mastery,
        onSelect: (id: string) => setSelectedConceptId(id),
      };

      return {
        id: node.id,
        type: "conceptNode",
        position: pos,
        data: nodeData,
      };
    });
  }, [nodes]);

  const flowEdges: Edge[] = useMemo(() => {
    return edges.map((edge, idx) => ({
      id: `e-${edge.from}-${edge.to}-${idx}`,
      source: edge.from,
      target: edge.to,
      animated: true,
      style: { stroke: "#A8A29E", strokeWidth: 1.5 },
      type: "smoothstep",
    }));
  }, [edges]);

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
        onClose={() => setSelectedConceptId(null)}
      />
    </div>
  );
}
