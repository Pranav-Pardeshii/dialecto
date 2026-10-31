"use client";

import React, { Suspense, useMemo, useRef, useState, Component, type ErrorInfo, type ReactNode } from "react";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import {
  Center,
  ContactShadows,
  Environment,
  Float,
  Html,
  OrbitControls,
  useGLTF,
  useProgress,
} from "@react-three/drei";
import {
  ACESFilmicToneMapping,
  CatmullRomCurve3,
  Group,
  Mesh,
  TubeGeometry,
  Vector3,
  type MeshStandardMaterialParameters,
} from "three";
import type { CellItem, CellModelAsset, OrganelleItem, ViewMode } from "@/data/cells";
import {
  applyAssetVertexColors,
  createAssetMaterial,
  createNativeAssetMaterial,
  createSolidAssetMaterial,
} from "@/lib/cellMaterials";
import { AlertTriangle, RefreshCw } from "lucide-react";

// Client-side DOM safety patch for React 19 + Drei <Html> unmount race condition
if (typeof window !== "undefined") {
  const originalRemoveChild = Node.prototype.removeChild;
  Node.prototype.removeChild = function <T extends Node>(child: T): T {
    if (child && child.parentNode !== this) {
      if (child.parentNode) {
        return child.parentNode.removeChild(child) as T;
      }
      return child;
    }
    return originalRemoveChild.call(this, child) as T;
  };
}

// Error Boundary to prevent 3D canvas crashes and show authentic unavailable state
interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackCellName: string;
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string;
}

export class ModelErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error.message || "Failed to load 3D model asset." };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Biological 3D Viewer error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full min-h-[380px] flex flex-col items-center justify-center p-6 bg-amber-50/60 border border-amber-200/80 rounded-xl text-center">
          <AlertTriangle className="w-10 h-10 text-amber-600 mb-3" />
          <h3 className="text-base font-semibold text-ink-primary font-display mb-1">
            Specimen 3D Asset Unavailable
          </h3>
          <p className="text-xs text-ink-secondary max-w-sm mb-4">
            The high-resolution 3D specimen for <strong>{this.props.fallbackCellName}</strong> could not be rendered in this browser session.
          </p>
          {this.props.onRetry && (
            <button
              onClick={() => {
                this.setState({ hasError: false, errorMessage: "" });
                this.props.onRetry?.();
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-surface border border-border-subtle rounded-md text-ink-primary hover:bg-subtle transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry Loading Specimen
            </button>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}

type MaterialProps = {
  id: string;
  activeOrganelle: string;
  viewMode: ViewMode;
  color: string;
  opacity?: number;
  roughness?: number;
  metalness?: number;
};

function CellMaterial({
  id,
  activeOrganelle,
  viewMode,
  color,
  opacity = 1,
  roughness = 0.66,
  metalness = 0.03,
}: MaterialProps) {
  const active = id === activeOrganelle;
  const dimmed = viewMode === "focus" && !active;
  const material: MeshStandardMaterialParameters = {
    color,
    roughness,
    metalness,
    transparent: opacity < 1 || dimmed,
    opacity: dimmed ? Math.min(opacity, 0.18) : opacity,
    emissive: active ? color : "#000000",
    emissiveIntensity: active ? 0.34 : 0,
  };

  return <meshStandardMaterial {...material} />;
}

interface OrganelleHotspotPinProps {
  organelle: OrganelleItem;
  isSelected: boolean;
  radius: number;
  onSelect: (id: string) => void;
}

function OrganelleHotspotPin({
  organelle,
  isSelected,
  radius,
  onSelect,
}: OrganelleHotspotPinProps) {
  const [hovered, setHovered] = useState(false);
  const position = organelle.position3D ?? [0, 0, 0];
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null);

  const currentRadius = isSelected ? radius * 1.3 : hovered ? radius * 1.15 : radius;

  return (
    <group position={position}>
      {/* Active Emerald Ring when selected */}
      {isSelected && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[radius * 1.6, radius * 2.1, 32]} />
          <meshBasicMaterial color="#16a34a" transparent opacity={0.85} side={2} />
        </mesh>
      )}

      {/* Anatomical Marker Pin */}
      <mesh
        onPointerDown={(e) => {
          e.stopPropagation();
          pointerDownPos.current = { x: e.clientX, y: e.clientY };
        }}
        onClick={(e) => {
          e.stopPropagation();
          if (pointerDownPos.current) {
            const dist = Math.hypot(
              e.clientX - pointerDownPos.current.x,
              e.clientY - pointerDownPos.current.y
            );
            if (dist > 6) return;
          }
          onSelect(organelle.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[currentRadius, 20, 20]} />
        <meshStandardMaterial
          color={organelle.color}
          emissive={isSelected ? "#22c55e" : hovered ? organelle.color : "#111111"}
          emissiveIntensity={isSelected ? 0.75 : hovered ? 0.4 : 0.12}
          roughness={0.3}
          metalness={0.2}
        />
      </mesh>

      {/* Label Tooltip - Persistently mounted to avoid React 19 Drei root unmount race conditions */}
      <Html
        position={[0, radius * 2.8, 0]}
        center
        distanceFactor={6}
        style={{
          pointerEvents: "none",
          transition: "opacity 150ms ease, transform 150ms ease",
          opacity: hovered || isSelected ? 1 : 0,
          visibility: hovered || isSelected ? "visible" : "hidden",
        }}
      >
        <div
          className={`px-2.5 py-1.5 rounded-lg text-xs font-sans transition-all duration-150 border shadow-sm select-none pointer-events-none whitespace-nowrap flex flex-col gap-0.5 ${
            isSelected
              ? "bg-stone-900/95 text-stone-100 border-emerald-500 shadow-md ring-2 ring-emerald-500/25"
              : "bg-surface/95 text-ink-primary border-border-subtle shadow-xs backdrop-blur-xs"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full inline-block shrink-0 ring-1 ring-white/50"
              style={{ backgroundColor: organelle.color }}
            />
            <span className="font-semibold text-xs tracking-tight">{organelle.name}</span>
            {isSelected && (
              <span className="px-1 py-0.2 rounded text-[9px] font-bold uppercase bg-emerald-600 text-white tracking-wider ml-1">
                Selected
              </span>
            )}
          </div>
          {organelle.subtitle && (
            <span className={`text-[10px] leading-tight ${isSelected ? "text-stone-300" : "text-ink-muted"}`}>
              {organelle.subtitle}
            </span>
          )}
        </div>
      </Html>
    </group>
  );
}

type TubeProps = {
  id: string;
  color: string;
  points: Array<[number, number, number]>;
  radius?: number;
  activeOrganelle: string;
  viewMode: ViewMode;
  onClick?: () => void;
};

function CurveTube({
  id,
  color,
  points,
  radius = 0.035,
  activeOrganelle,
  viewMode,
  onClick,
}: TubeProps) {
  const geometry = useMemo(() => {
    const curve = new CatmullRomCurve3(
      points.map((point) => new Vector3(point[0], point[1], point[2])),
    );
    return new TubeGeometry(curve, 80, radius, 12, false);
  }, [points, radius]);

  const pointerDownPos = useRef<{ x: number; y: number } | null>(null);

  return (
    <mesh
      geometry={geometry}
      castShadow
      receiveShadow
      onPointerDown={(e) => {
        if (onClick) {
          pointerDownPos.current = { x: e.clientX, y: e.clientY };
        }
      }}
      onClick={(e) => {
        if (onClick) {
          if (pointerDownPos.current) {
            const dist = Math.hypot(
              e.clientX - pointerDownPos.current.x,
              e.clientY - pointerDownPos.current.y
            );
            if (dist > 6) return;
          }
          e.stopPropagation();
          onClick();
        }
      }}
      onPointerOver={(e) => {
        if (onClick) {
          e.stopPropagation();
          document.body.style.cursor = "pointer";
        }
      }}
      onPointerOut={() => {
        document.body.style.cursor = "auto";
      }}
    >
      <CellMaterial
        id={id}
        activeOrganelle={activeOrganelle}
        viewMode={viewMode}
        color={color}
        roughness={0.58}
      />
    </mesh>
  );
}

type CommonModelProps = {
  activeOrganelle: string;
  viewMode: ViewMode;
  crossSection: boolean;
};

function AssetCellModel({
  cell,
  asset,
  activeOrganelle,
  onSelectOrganelle,
  viewMode,
  crossSection,
}: CommonModelProps & {
  cell: CellItem;
  asset: CellModelAsset;
  onSelectOrganelle?: (id: string) => void;
}) {
  const { scene } = useGLTF(asset.url, true, true);
  const clonedScene = useMemo(() => {
    const clone = scene.clone(true);
    let meshIndex = 0;

    clone.traverse((node) => {
      const mesh = node as Mesh;
      if (!mesh.isMesh) {
        return;
      }

      mesh.castShadow = true;
      mesh.receiveShadow = true;

      // Diagnostic logging in development
      if (process.env.NODE_ENV !== "production") {
        mesh.geometry?.computeBoundingBox();
        console.groupCollapsed(`[3D Specimen Mesh] ${cell.name}: ${mesh.name || "mesh"}`);
        console.log("Type:", mesh.type);
        console.log("Geometry Bounds:", mesh.geometry?.boundingBox);
        console.log(
          "Material:",
          Array.isArray(mesh.material)
            ? mesh.material.map((m) => m.name)
            : mesh.material?.name
        );
        console.log("UserData:", mesh.userData);
        console.groupEnd();
      }

      if (asset.materialMode === "native") {
        mesh.material = createNativeAssetMaterial({
          original: mesh.material,
          cell,
          asset,
          crossSection,
        });
      } else if (asset.materialMode === "solid") {
        mesh.geometry.computeVertexNormals();
        mesh.material = createSolidAssetMaterial({
          original: mesh.material,
          cell,
          viewMode,
          crossSection,
        });
      } else {
        mesh.geometry.computeVertexNormals();
        applyAssetVertexColors(mesh, cell);
        mesh.material = createAssetMaterial({
          original: mesh.material,
          cell,
          meshIndex,
          viewMode,
          crossSection,
        });
      }
      meshIndex += 1;
    });

    return clone;
  }, [cell, scene, viewMode, crossSection, asset]);

  // Pointer position tracker to distinguish clean clicks from OrbitControls drag/orbit
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null);

  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMeshClick = (e: ThreeEvent<MouseEvent>) => {
    if (pointerDownPos.current) {
      const dist = Math.hypot(
        e.clientX - pointerDownPos.current.x,
        e.clientY - pointerDownPos.current.y
      );
      if (dist > 6) {
        // Drag gesture to rotate/orbit model - ignore to prevent misclicks
        return;
      }
    }

    e.stopPropagation();

    // The clicked mesh
    const mesh = e.object as Mesh;
    // Transform raycast world hit point to mesh-local coordinates
    const localPoint = mesh.worldToLocal(e.point.clone());

    // Resolve closest biological organelle based on model-local coordinates
    let closestId: string | null = null;
    let minDistance = Infinity;

    for (const organelle of cell.organelles) {
      if (!organelle.position3D) continue;
      const [ox, oy, oz] = organelle.position3D;
      const dist = Math.hypot(localPoint.x - ox, localPoint.y - oy, localPoint.z - oz);
      if (dist < minDistance) {
        minDistance = dist;
        closestId = organelle.id;
      }
    }

    if (closestId) {
      onSelectOrganelle?.(closestId);
    }
  };

  // Pin radius scaled inversely to asset.scale so visual pin size is always ~0.04 world units
  const pinRadius = 0.04 / (asset.scale || 1.0);

  return (
    <group
      position={asset.position ?? [0, 0, 0]}
      rotation={asset.rotation ?? [0, 0, 0]}
      scale={[asset.scale, asset.scale, asset.scale]}
    >
      <Center>
        <primitive
          object={clonedScene}
          onPointerDown={handlePointerDown}
          onClick={handleMeshClick}
          onPointerOver={() => {
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            document.body.style.cursor = "auto";
          }}
        />

        {/* Hotspots anchored in the EXACT same transformed & centered model space */}
        {cell.organelles.map((organelle) => {
          if (!organelle.position3D) return null;
          return (
            <OrganelleHotspotPin
              key={organelle.id}
              organelle={organelle}
              isSelected={activeOrganelle === organelle.id}
              radius={pinRadius}
              onSelect={(id) => onSelectOrganelle?.(id)}
            />
          );
        })}
      </Center>
    </group>
  );
}

function Dots({
  id,
  color,
  activeOrganelle,
  viewMode,
  count,
  spread,
}: CommonModelProps & {
  id: string;
  color: string;
  count: number;
  spread: [number, number, number];
}) {
  const dots = useMemo(
    () =>
      Array.from({ length: count }, (_, index) => {
        const a = index * 1.71;
        const b = index * 2.37;
        return [
          Math.sin(a) * spread[0],
          Math.cos(b) * spread[1],
          Math.sin(a + b) * spread[2],
        ] as [number, number, number];
      }),
    [count, spread],
  );

  return (
    <>
      {dots.map((position, index) => (
        <mesh key={`${id}-${index}`} position={position} castShadow>
          <sphereGeometry args={[0.055 + (index % 3) * 0.018, 18, 18]} />
          <CellMaterial
            id={id}
            activeOrganelle={activeOrganelle}
            viewMode={viewMode}
            color={color}
            opacity={0.92}
          />
        </mesh>
      ))}
    </>
  );
}

function Nucleus({
  id = "nucleus",
  position,
  scale,
  activeOrganelle,
  viewMode,
  color = "#7047a8",
  onClick,
}: CommonModelProps & {
  id?: string;
  position: [number, number, number];
  scale: [number, number, number];
  color?: string;
  onClick?: () => void;
}) {
  return (
    <group
      position={position}
      scale={scale}
      onClick={(e) => {
        if (onClick) {
          e.stopPropagation();
          onClick();
        }
      }}
      onPointerOver={(e) => {
        if (onClick) {
          e.stopPropagation();
          document.body.style.cursor = "pointer";
        }
      }}
      onPointerOut={() => {
        document.body.style.cursor = "auto";
      }}
    >
      <mesh castShadow receiveShadow>
        <sphereGeometry args={[1, 48, 48]} />
        <CellMaterial
          id={id}
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          color={color}
          opacity={0.92}
          roughness={0.44}
        />
      </mesh>
      <mesh position={[0.2, 0.16, 0.38]} castShadow>
        <sphereGeometry args={[0.23, 28, 28]} />
        <CellMaterial
          id={id}
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          color="#b56ad8"
          opacity={0.9}
        />
      </mesh>
    </group>
  );
}

function EpithelialModel({
  cell,
  activeOrganelle,
  viewMode,
  crossSection,
  onSelectOrganelle,
}: CommonModelProps & { cell: CellItem; onSelectOrganelle?: (id: string) => void }) {
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null);

  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleClickPart = (id: string, e: ThreeEvent<MouseEvent>) => {
    if (pointerDownPos.current) {
      const dist = Math.hypot(
        e.clientX - pointerDownPos.current.x,
        e.clientY - pointerDownPos.current.y
      );
      if (dist > 6) return;
    }
    e.stopPropagation();
    onSelectOrganelle?.(id);
  };

  const microvilliRows = 6;
  const microvilliCols = 6;
  const microvilli: Array<{ position: [number, number, number]; height: number }> = [];
  for (let row = 0; row < microvilliRows; row += 1) {
    for (let col = 0; col < microvilliCols; col += 1) {
      const x = -0.55 + col * 0.22 + (row % 2 === 0 ? 0 : 0.11);
      const z = -0.55 + row * 0.22;
      const dist = Math.hypot(x, z);
      if (dist > 0.7) continue;
      const height = 0.38 + Math.sin(row * 1.3 + col * 0.7) * 0.06;
      microvilli.push({ position: [x, 1.34 + height / 2, z], height });
    }
  }

  return (
    <group rotation={[0.08, -0.22, 0]} scale={[1.08, 1.08, 1.08]}>
      <mesh
        position={[0, 0, 0]}
        castShadow
        receiveShadow
        onPointerDown={handlePointerDown}
        onClick={(e) => handleClickPart("microvilli", e)}
      >
        <cylinderGeometry args={[0.78, 0.88, 2.6, 32, 1, false]} />
        <CellMaterial
          id="membrane"
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          color="#d79baa"
          opacity={crossSection ? 0.3 : 0.52}
        />
      </mesh>
      {[-1.62, 1.62].map((x, index) => (
        <mesh key={`neighbor-${index}`} position={[x, -0.08, 0]} castShadow receiveShadow>
          <cylinderGeometry args={[0.74, 0.84, 2.2, 28, 1, false]} />
          <CellMaterial
            id="membrane"
            activeOrganelle={activeOrganelle}
            viewMode={viewMode}
            color="#c98ba0"
            opacity={crossSection ? 0.22 : 0.34}
          />
        </mesh>
      ))}
      {microvilli.map((villus, index) => (
        <mesh
          key={`villus-${index}`}
          position={villus.position}
          castShadow
          onPointerDown={handlePointerDown}
          onClick={(e) => handleClickPart("microvilli", e)}
          onPointerOver={(e) => {
            e.stopPropagation();
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            document.body.style.cursor = "auto";
          }}
        >
          <capsuleGeometry args={[0.038, villus.height, 6, 12]} />
          <CellMaterial
            id="microvilli"
            activeOrganelle={activeOrganelle}
            viewMode={viewMode}
            color="#c86f80"
          />
        </mesh>
      ))}
      <mesh
        position={[0, 1.34, 0]}
        castShadow
        receiveShadow
        onPointerDown={handlePointerDown}
        onClick={(e) => handleClickPart("microvilli", e)}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "auto";
        }}
      >
        <cylinderGeometry args={[0.78, 0.78, 0.06, 32]} />
        <CellMaterial
          id="microvilli"
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          color="#b85a6d"
          opacity={0.85}
        />
      </mesh>
      <Nucleus
        position={[0, -0.55, 0]}
        scale={[0.46, 0.36, 0.46]}
        activeOrganelle={activeOrganelle}
        viewMode={viewMode}
        crossSection={crossSection}
        onClick={() => onSelectOrganelle?.("nucleus")}
      />
      {[-0.82, 0.82].map((x, index) => (
        <mesh
          key={`junction-${index}`}
          position={[x, 0.95, 0]}
          castShadow
          onPointerDown={handlePointerDown}
          onClick={(e) => handleClickPart("junctions", e)}
          onPointerOver={(e) => {
            e.stopPropagation();
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            document.body.style.cursor = "auto";
          }}
        >
          <torusGeometry args={[0.22, 0.05, 10, 20, Math.PI]} />
          <CellMaterial
            id="junctions"
            activeOrganelle={activeOrganelle}
            viewMode={viewMode}
            color="#9f6cbd"
          />
        </mesh>
      ))}
      <CurveTube
        id="junctions"
        color="#9f6cbd"
        points={[
          [-0.82, 1.0, -0.4],
          [-0.4, 1.05, 0],
          [-0.82, 1.0, 0.4],
        ]}
        radius={0.04}
        activeOrganelle={activeOrganelle}
        viewMode={viewMode}
        onClick={() => onSelectOrganelle?.("junctions")}
      />
      <CurveTube
        id="junctions"
        color="#9f6cbd"
        points={[
          [0.82, 1.0, -0.4],
          [0.4, 1.05, 0],
          [0.82, 1.0, 0.4],
        ]}
        radius={0.04}
        activeOrganelle={activeOrganelle}
        viewMode={viewMode}
        onClick={() => onSelectOrganelle?.("junctions")}
      />
      <mesh position={[0, -1.36, 0]} receiveShadow>
        <cylinderGeometry args={[0.9, 0.9, 0.08, 36]} />
        <CellMaterial
          id="membrane"
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          color="#a56d7f"
          opacity={0.6}
        />
      </mesh>
      <Dots
        id="nucleus"
        color="#d082a2"
        count={14}
        spread={[0.5, 0.5, 0.36]}
        activeOrganelle={activeOrganelle}
        viewMode={viewMode}
        crossSection={crossSection}
      />

      {/* Anatomical Pins inside model local space */}
      {cell.organelles.map((organelle) => {
        if (!organelle.position3D) return null;
        return (
          <OrganelleHotspotPin
            key={organelle.id}
            organelle={organelle}
            isSelected={activeOrganelle === organelle.id}
            radius={0.04}
            onSelect={(id) => onSelectOrganelle?.(id)}
          />
        );
      })}
    </group>
  );
}

function MuscleModel({
  cell,
  activeOrganelle,
  viewMode,
  crossSection,
  onSelectOrganelle,
}: CommonModelProps & { cell: CellItem; onSelectOrganelle?: (id: string) => void }) {
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null);

  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleClickPart = (id: string, e: ThreeEvent<MouseEvent>) => {
    if (pointerDownPos.current) {
      const dist = Math.hypot(
        e.clientX - pointerDownPos.current.x,
        e.clientY - pointerDownPos.current.y
      );
      if (dist > 6) return;
    }
    e.stopPropagation();
    onSelectOrganelle?.(id);
  };

  const fiberLength = 4.4;
  const sarcomere = 0.36;
  const sarcomereCount = Math.floor(fiberLength / sarcomere);
  const myofibrilLayout: Array<{ y: number; z: number }> = [
    { y: 0.36, z: 0.0 },
    { y: 0.18, z: 0.34 },
    { y: 0.18, z: -0.34 },
    { y: -0.18, z: 0.34 },
    { y: -0.18, z: -0.34 },
    { y: -0.36, z: 0.0 },
    { y: 0.0, z: 0.0 },
  ];

  return (
    <group rotation={[0.12, -0.18, -0.03]} scale={[1.0, 1.0, 1.0]}>
      <mesh
        rotation={[0, 0, Math.PI / 2]}
        castShadow
        receiveShadow
        onPointerDown={handlePointerDown}
        onClick={(e) => handleClickPart("sarcolemma", e)}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "auto";
        }}
      >
        <capsuleGeometry args={[0.7, fiberLength, 14, 48]} />
        <CellMaterial
          id="sarcolemma"
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          color="#d7b284"
          opacity={crossSection ? 0.22 : 0.36}
        />
      </mesh>
      {myofibrilLayout.map((fibril, fibrilIndex) => (
        <group key={`myofibril-${fibrilIndex}`} position={[0, fibril.y, fibril.z]}>
          {Array.from({ length: sarcomereCount }, (_, sIndex) => {
            const x = -fiberLength / 2 + sIndex * sarcomere + sarcomere / 2;
            return (
              <group
                key={`s-${sIndex}`}
                position={[x, 0, 0]}
                onPointerDown={handlePointerDown}
                onClick={(e) => handleClickPart("myofibril", e)}
                onPointerOver={(e) => {
                  e.stopPropagation();
                  document.body.style.cursor = "pointer";
                }}
                onPointerOut={() => {
                  document.body.style.cursor = "auto";
                }}
              >
                <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
                  <cylinderGeometry args={[0.13, 0.13, sarcomere * 0.55, 18]} />
                  <CellMaterial
                    id="myofibril"
                    activeOrganelle={activeOrganelle}
                    viewMode={viewMode}
                    color="#a02f43"
                  />
                </mesh>
                <mesh position={[sarcomere * 0.32, 0, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
                  <cylinderGeometry args={[0.115, 0.115, sarcomere * 0.32, 18]} />
                  <CellMaterial
                    id="myofibril"
                    activeOrganelle={activeOrganelle}
                    viewMode={viewMode}
                    color="#e09aa5"
                  />
                </mesh>
                <mesh position={[sarcomere * 0.5, 0, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
                  <cylinderGeometry args={[0.145, 0.145, 0.04, 18]} />
                  <CellMaterial
                    id="myofibril"
                    activeOrganelle={activeOrganelle}
                    viewMode={viewMode}
                    color="#3d1418"
                  />
                </mesh>
              </group>
            );
          })}
        </group>
      ))}
      {[-1.45, -0.1, 1.25].map((x, index) => (
        <Nucleus
          key={`nucleus-${index}`}
          id="nucleus"
          position={[x, 0.62, 0.18]}
          scale={[0.36, 0.16, 0.22]}
          color="#7a4aa2"
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          crossSection={crossSection}
          onClick={() => onSelectOrganelle?.("nucleus")}
        />
      ))}
      {[
        [-1.8, -0.5, 0.2],
        [-0.6, -0.55, -0.22],
        [0.6, -0.5, 0.22],
        [1.8, -0.55, -0.2],
      ].map((position, index) => (
        <mesh
          key={`mito-${index}`}
          position={position as [number, number, number]}
          rotation={[0, 0, Math.PI / 2]}
          castShadow
          onPointerDown={handlePointerDown}
          onClick={(e) => handleClickPart("mitochondria", e)}
          onPointerOver={(e) => {
            e.stopPropagation();
            document.body.style.cursor = "pointer";
          }}
          onPointerOut={() => {
            document.body.style.cursor = "auto";
          }}
        >
          <capsuleGeometry args={[0.09, 0.32, 8, 14]} />
          <CellMaterial
            id="mitochondria"
            activeOrganelle={activeOrganelle}
            viewMode={viewMode}
            color="#cf7042"
          />
        </mesh>
      ))}
      {[0, 1, 2, 3].map((index) => (
        <CurveTube
          key={`sr-${index}`}
          id="sarcolemma"
          color="#ead2a7"
          points={[
            [-2.0 + index * 1.0, -0.78, 0.28],
            [-1.9 + index * 1.0, -0.2, 0.36],
            [-2.0 + index * 1.0, 0.62, 0.3],
          ]}
          radius={0.03}
          activeOrganelle={activeOrganelle}
          viewMode={viewMode}
          onClick={() => onSelectOrganelle?.("sarcolemma")}
        />
      ))}

      {/* Anatomical Pins inside model local space */}
      {cell.organelles.map((organelle) => {
        if (!organelle.position3D) return null;
        return (
          <OrganelleHotspotPin
            key={organelle.id}
            organelle={organelle}
            isSelected={activeOrganelle === organelle.id}
            radius={0.04}
            onSelect={(id) => onSelectOrganelle?.(id)}
          />
        );
      })}
    </group>
  );
}

function CellModelContainer({
  cell,
  activeOrganelle,
  viewMode,
  crossSection,
  autoRotate,
  onSelectOrganelle,
}: {
  cell: CellItem;
  activeOrganelle: string | null;
  viewMode: ViewMode;
  crossSection: boolean;
  autoRotate: boolean;
  onSelectOrganelle?: (id: string) => void;
}) {
  const group = useRef<Group>(null);

  useFrame((_, delta) => {
    if (group.current && autoRotate) {
      group.current.rotation.y += delta * 0.12;
    }
  });

  const common = { activeOrganelle: activeOrganelle ?? "", viewMode, crossSection };

  return (
    <group ref={group} position={[0, 0, 0]}>
      {cell.modelAsset ? (
        <AssetCellModel
          cell={cell}
          asset={cell.modelAsset}
          onSelectOrganelle={onSelectOrganelle}
          {...common}
        />
      ) : (
        <>
          {cell.modelKind === "epithelial" && (
            <EpithelialModel
              cell={cell}
              onSelectOrganelle={onSelectOrganelle}
              {...common}
            />
          )}
          {cell.modelKind === "muscle" && (
            <MuscleModel
              cell={cell}
              onSelectOrganelle={onSelectOrganelle}
              {...common}
            />
          )}
        </>
      )}
    </group>
  );
}

function ModelLoadingOverlay({ cell }: { cell: CellItem }) {
  const { progress, loaded, total } = useProgress();
  const displayProgress = Math.max(2, Math.min(100, Math.round(progress)));
  const mbLoaded = loaded ? (loaded / (1024 * 1024)).toFixed(1) : null;
  const mbTotal = total ? (total / (1024 * 1024)).toFixed(1) : null;

  return (
    <Html center>
      <div className="bg-surface/95 backdrop-blur-sm border border-border-subtle rounded-xl px-5 py-4 shadow-md flex flex-col items-center gap-2.5 min-w-[220px]">
        <div className="w-6 h-6 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin" />
        <span className="text-xs font-semibold text-ink-primary font-display">
          Loading {cell.name} 3D Specimen
        </span>
        <div className="w-full bg-border-subtle h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-emerald-600 h-full rounded-full transition-all duration-300"
            style={{ width: `${displayProgress}%` }}
          />
        </div>
        <span className="text-[11px] text-ink-muted">
          {displayProgress}%
          {mbLoaded && mbTotal && total > 0 && ` (${mbLoaded} / ${mbTotal} MB)`}
        </span>
      </div>
    </Html>
  );
}

export interface Biological3DViewerProps {
  cell: CellItem;
  activeOrganelle: string | null;
  onSelectOrganelle?: (organelleId: string) => void;
  onClearSelection?: () => void;
  viewMode?: ViewMode;
  crossSection?: boolean;
  autoRotate?: boolean;
  resetKey?: number;
  className?: string;
  onReset?: () => void;
}

export function Biological3DViewer({
  cell,
  activeOrganelle,
  onSelectOrganelle,
  onClearSelection,
  viewMode = "mesh",
  crossSection = false,
  autoRotate = false,
  resetKey = 0,
  className = "",
  onReset,
}: Biological3DViewerProps) {
  const nativeMaterial = cell.modelAsset?.materialMode === "native";

  return (
    <ModelErrorBoundary fallbackCellName={cell.name} onRetry={onReset}>
      <div className={`relative w-full h-full min-h-[420px] rounded-xl overflow-hidden ${className}`}>
        <Canvas
          key={`${cell.id}-${resetKey}`}
          className="w-full h-full"
          dpr={[1, 2]}
          shadows
          onPointerMissed={() => onClearSelection?.()}
          gl={{
            antialias: true,
            alpha: true,
            premultipliedAlpha: false,
            preserveDrawingBuffer: true,
            toneMapping: ACESFilmicToneMapping,
            toneMappingExposure: nativeMaterial ? 1.05 : 1.18,
          }}
          camera={{ position: [0, 0.2, 5.8], fov: 38 }}
        >
          {!nativeMaterial && <color attach="background" args={["#fbf7ee"]} />}
          <Suspense fallback={null}>
            <Environment
              preset="studio"
              background={false}
              environmentIntensity={nativeMaterial ? 0.75 : 0.5}
            />
          </Suspense>
          <ambientLight intensity={nativeMaterial ? 0.65 : 0.85} />
          <hemisphereLight
            args={[
              nativeMaterial ? "#fffaf0" : "#fff8ea",
              nativeMaterial ? "#efe3d2" : "#e3ded2",
              nativeMaterial ? 0.55 : 0.65,
            ]}
          />
          <directionalLight
            position={[4.2, 5.2, 5.8]}
            intensity={nativeMaterial ? 1.85 : 1.95}
            castShadow
            shadow-mapSize={[1024, 1024]}
            shadow-bias={-0.0001}
          />
          {nativeMaterial && (
            <directionalLight
              position={[-4.4, 2.2, 3.6]}
              intensity={0.55}
              color="#fff1df"
            />
          )}
          <spotLight
            position={[-3.6, 3.2, 4.6]}
            angle={0.42}
            penumbra={0.74}
            intensity={nativeMaterial ? 0.4 : 0.85}
            color={nativeMaterial ? "#fff8ec" : cell.accentSoft}
          />
          <pointLight
            position={[2.8, -1.2, 3.2]}
            intensity={nativeMaterial ? 0.28 : 0.4}
            color={nativeMaterial ? "#ffffff" : cell.accent}
          />
          <Suspense fallback={<ModelLoadingOverlay cell={cell} />}>
            <Float speed={1.25} rotationIntensity={0.08} floatIntensity={0.18}>
              <CellModelContainer
                cell={cell}
                activeOrganelle={activeOrganelle}
                onSelectOrganelle={onSelectOrganelle}
                viewMode={viewMode}
                crossSection={crossSection}
                autoRotate={autoRotate}
              />
            </Float>
            <ContactShadows
              position={[0, -1.8, 0]}
              opacity={nativeMaterial ? 0.28 : 0.34}
              scale={nativeMaterial ? 7.8 : 7.2}
              blur={nativeMaterial ? 2.6 : 2.0}
              far={4.2}
              resolution={512}
            />
          </Suspense>
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.08}
            enablePan
            minDistance={2.5}
            maxDistance={9.0}
          />
        </Canvas>
      </div>
    </ModelErrorBoundary>
  );
}
