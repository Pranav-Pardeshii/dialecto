"use client";

import { memo } from "react";
import {
  BaseEdge,
  EdgeProps,
  getBezierPath,
  Position,
} from "@xyflow/react";

export interface CurvedTreeEdgeData {
  isHighlighted?: boolean;
  isActive?: boolean;
  isLocked?: boolean;
  [key: string]: unknown;
}

export const CurvedTreeEdge = memo(function CurvedTreeEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition = Position.Right,
  targetPosition = Position.Left,
  style = {},
  markerEnd,
  data,
  selected,
}: EdgeProps) {
  // Consistent cubic Bézier path following the horizontal tree progression
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.45,
  });

  const edgeData = data as CurvedTreeEdgeData | undefined;
  const isHighlighted = selected || Boolean(edgeData?.isHighlighted);
  const isActive = Boolean(edgeData?.isActive);
  const isLocked = Boolean(edgeData?.isLocked);

  // Taste Skill palette tokens:
  // - Highlighted: #2E7D32 (Forest Emerald, 2.5px)
  // - Active (prereq satisfied): #94A3B8 (Cool Slate, 1.75px)
  // - Locked / Inactive: #D1D5DB (Muted Divider, 1.5px, subtle dash)
  let strokeColor = "#CBD5E1";
  let strokeWidth = 1.5;
  let strokeDasharray: string | undefined = undefined;

  if (isHighlighted) {
    strokeColor = "#2E7D32";
    strokeWidth = 2.5;
    strokeDasharray = undefined;
  } else if (isActive) {
    strokeColor = "#94A3B8";
    strokeWidth = 1.75;
    strokeDasharray = undefined;
  } else if (isLocked) {
    strokeColor = "#D1D5DB";
    strokeWidth = 1.5;
    strokeDasharray = "4 3";
  }

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: strokeColor,
        strokeWidth,
        strokeDasharray,
        transition: "stroke 0.2s ease, stroke-width 0.2s ease",
      }}
      markerEnd={markerEnd}
    />
  );
});
