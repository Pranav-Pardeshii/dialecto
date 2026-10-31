"use client";

import React from "react";

interface StructureDef {
  id: string;
  name: string;
  color?: string;
  description?: string;
  function?: string;
}

interface Biological2DAtlasProps {
  diagramId: string;
  structures?: StructureDef[];
  selectedStructureId: string | null;
  isolatedStructureId?: string | null;
  hiddenStructureIds?: string[];
  onSelectStructure: (structureId: string) => void;
  className?: string;
}

export function Biological2DAtlas({
  diagramId,
  selectedStructureId,
  isolatedStructureId = null,
  hiddenStructureIds = [],
  onSelectStructure,
  className = "",
}: Biological2DAtlasProps) {
  const isSelected = (id: string) => selectedStructureId === id;
  const isDimmed = (id: string) => isolatedStructureId !== null && isolatedStructureId !== id;
  const isHidden = (id: string) => hiddenStructureIds.includes(id);

  const getStyle = (id: string, defaultColor: string) => {
    if (isHidden(id)) return { display: "none" };
    const selected = isSelected(id);
    return {
      fill: selected ? "#10B981" : defaultColor,
      opacity: isDimmed(id) ? 0.2 : 1,
      cursor: "pointer",
      transition: "all 0.2s ease",
      stroke: selected ? "#065F46" : "#292524",
      strokeWidth: selected ? 3 : 1.5,
    };
  };

  return (
    <div className={`relative w-full h-full min-h-[380px] flex items-center justify-center bg-canvas rounded-lg p-4 select-none ${className}`}>
      {/* 1. Animal Cell */}
      {diagramId === "animal" && (
        <svg
          viewBox="0 0 600 460"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of Animal Cell"
        >
          {/* Cytoplasm & Membrane */}
          <ellipse cx="300" cy="230" rx="250" ry="180" fill="#fdfbf7" stroke="#9db6dc" strokeWidth="4" />
          <text x="75" y="80" className="text-[12px] font-sans fill-ink-secondary">Animal Cell Boundary</text>

          {/* Nucleus */}
          <g
            style={getStyle("nucleus", "#7a49b0")}
            onClick={() => onSelectStructure("nucleus")}
            tabIndex={0}
            role="button"
            aria-label="Nucleus"
          >
            <circle cx="310" cy="230" r="65" />
            <circle cx="325" cy="225" r="22" fill="#582986" />
            <text x="310" y="235" textAnchor="middle" fill="#FFFFFF" className="text-[11px] font-medium font-sans">
              Nucleus
            </text>
          </g>

          {/* Mitochondrion 1 & 2 */}
          <g
            style={getStyle("mitochondrion", "#cf6f42")}
            onClick={() => onSelectStructure("mitochondrion")}
            tabIndex={0}
            role="button"
            aria-label="Mitochondrion"
          >
            <rect x="130" y="270" width="85" height="42" rx="21" transform="rotate(-20 172 291)" />
            <path d="M 140 290 Q 155 278 172 291 T 205 290" stroke="#fce7db" strokeWidth="2.5" fill="none" />
            <text x="170" y="325" textAnchor="middle" fill="#cf6f42" className="text-[11px] font-semibold font-sans">
              Mitochondrion
            </text>

            <rect x="420" y="140" width="75" height="38" rx="19" transform="rotate(25 457 159)" />
            <path d="M 430 159 Q 445 148 457 159 T 485 159" stroke="#fce7db" strokeWidth="2.5" fill="none" />
          </g>

          {/* Golgi Apparatus */}
          <g
            style={getStyle("golgi", "#d49057")}
            onClick={() => onSelectStructure("golgi")}
            tabIndex={0}
            role="button"
            aria-label="Golgi Apparatus"
          >
            <path d="M 390 280 C 420 270, 440 300, 470 290" strokeWidth="7" strokeLinecap="round" fill="none" />
            <path d="M 395 295 C 425 285, 445 315, 475 305" strokeWidth="7" strokeLinecap="round" fill="none" />
            <path d="M 400 310 C 430 300, 450 330, 480 320" strokeWidth="7" strokeLinecap="round" fill="none" />
            <text x="440" y="348" textAnchor="middle" fill="#d49057" className="text-[11px] font-semibold font-sans">
              Golgi Apparatus
            </text>
          </g>
        </svg>
      )}

      {/* 2. Plant Cell */}
      {diagramId === "plant" && (
        <svg
          viewBox="0 0 600 460"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of Plant Cell"
        >
          {/* Cell Wall */}
          <g
            style={getStyle("cellWall", "#81b64b")}
            onClick={() => onSelectStructure("cellWall")}
            tabIndex={0}
            role="button"
            aria-label="Cell Wall"
          >
            <rect x="45" y="35" width="510" height="390" rx="40" fill="#f0f7e8" stroke="#4f8a3f" strokeWidth="12" />
            <rect x="58" y="48" width="484" height="364" rx="30" fill="none" stroke="#7aa647" strokeWidth="5" />
            <text x="75" y="75" fill="#4f8a3f" className="text-[12px] font-bold font-sans">Cellulose Cell Wall</text>
          </g>

          {/* Central Vacuole */}
          <g
            style={getStyle("vacuole", "#62bdd2")}
            onClick={() => onSelectStructure("vacuole")}
            tabIndex={0}
            role="button"
            aria-label="Central Vacuole"
          >
            <ellipse cx="260" cy="245" rx="145" ry="110" />
            <text x="260" y="250" textAnchor="middle" fill="#0c4a6e" className="text-[12px] font-semibold font-sans">
              Central Vacuole (Cell Sap)
            </text>
          </g>

          {/* Nucleus */}
          <g
            style={getStyle("nucleus", "#7047a8")}
            onClick={() => onSelectStructure("nucleus")}
            tabIndex={0}
            role="button"
            aria-label="Nucleus"
          >
            <circle cx="440" cy="170" r="50" />
            <circle cx="452" cy="162" r="16" fill="#4c1d95" />
            <text x="440" y="175" textAnchor="middle" fill="#FFFFFF" className="text-[11px] font-medium font-sans">
              Nucleus
            </text>
          </g>

          {/* Chloroplasts */}
          <g
            style={getStyle("chloroplast", "#5fa842")}
            onClick={() => onSelectStructure("chloroplast")}
            tabIndex={0}
            role="button"
            aria-label="Chloroplast"
          >
            <ellipse cx="140" cy="130" rx="38" ry="24" transform="rotate(-15 140 130)" />
            <ellipse cx="440" cy="320" rx="38" ry="24" transform="rotate(20 440 320)" />
            <ellipse cx="150" cy="340" rx="38" ry="24" transform="rotate(-30 150 340)" />
            <text x="140" y="100" textAnchor="middle" fill="#2d6a1d" className="text-[11px] font-semibold font-sans">
              Chloroplast (Grana & Stroma)
            </text>
          </g>
        </svg>
      )}

      {/* 3. Neuron */}
      {diagramId === "neuron" && (
        <svg
          viewBox="0 0 650 380"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of Neuron"
        >
          {/* Dendrites */}
          <g
            style={getStyle("dendrites", "#7d9bcf")}
            onClick={() => onSelectStructure("dendrites")}
            tabIndex={0}
            role="button"
            aria-label="Dendrites"
          >
            <path d="M 120 180 Q 80 140, 40 120 M 120 190 Q 70 200, 30 220 M 130 170 Q 110 110, 80 60 M 140 210 Q 110 260, 70 300" strokeWidth="4.5" strokeLinecap="round" fill="none" />
            <text x="60" y="45" fill="#475569" className="text-[12px] font-semibold font-sans">
              Dendrites (Receptor Tips)
            </text>
          </g>

          {/* Soma */}
          <g
            style={getStyle("soma", "#7c52b7")}
            onClick={() => onSelectStructure("soma")}
            tabIndex={0}
            role="button"
            aria-label="Soma"
          >
            <polygon points="120,180 160,130 210,150 220,200 180,240 130,220" />
            <circle cx="170" cy="185" r="24" fill="#582986" />
            <text x="170" y="190" textAnchor="middle" fill="#FFFFFF" className="text-[11px] font-medium font-sans">
              Soma
            </text>
          </g>

          {/* Axon */}
          <g
            style={getStyle("axon", "#6b7dc6")}
            onClick={() => onSelectStructure("axon")}
            tabIndex={0}
            role="button"
            aria-label="Axon"
          >
            <line x1="220" y1="190" x2="560" y2="190" stroke="#6b7dc6" strokeWidth="8" />
            {/* Myelin Sheaths */}
            {[250, 320, 390, 460].map((x, i) => (
              <rect key={i} x={x} y="172" width="55" height="36" rx="8" fill="#e2e8f0" stroke="#64748b" strokeWidth="2" />
            ))}
            {/* Terminals */}
            <path d="M 560 190 Q 590 160, 620 150 M 560 190 Q 600 190, 630 190 M 560 190 Q 590 220, 620 230" strokeWidth="4" strokeLinecap="round" fill="none" />
            <text x="400" y="150" textAnchor="middle" fill="#334155" className="text-[12px] font-semibold font-sans">
              Axon (Impulse Transmission)
            </text>
          </g>
        </svg>
      )}

      {/* 4. Bacterial Cell Wall */}
      {diagramId === "bacteria" && (
        <svg
          viewBox="0 0 600 420"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of Bacteria Cell"
        >
          {/* Flagellum */}
          <g
            style={getStyle("flagellum", "#b87438")}
            onClick={() => onSelectStructure("flagellum")}
            tabIndex={0}
            role="button"
            aria-label="Flagellum"
          >
            <path d="M 440 210 Q 480 160, 520 230 T 580 180" strokeWidth="6" strokeLinecap="round" fill="none" />
            <text x="520" y="130" fill="#b87438" className="text-[11px] font-semibold font-sans">
              Flagellum Motor
            </text>
          </g>

          {/* Peptidoglycan Cell Wall */}
          <g
            style={getStyle("cellWall", "#55aa89")}
            onClick={() => onSelectStructure("cellWall")}
            tabIndex={0}
            role="button"
            aria-label="Cell Wall"
          >
            <rect x="90" y="120" width="360" height="180" rx="90" fill="#dbf1e7" stroke="#48a77d" strokeWidth="10" />
            <text x="270" y="100" textAnchor="middle" fill="#2d7a5b" className="text-[12px] font-bold font-sans">
              Peptidoglycan Cell Wall
            </text>
          </g>

          {/* Nucleoid */}
          <g
            style={getStyle("nucleoid", "#7a43ad")}
            onClick={() => onSelectStructure("nucleoid")}
            tabIndex={0}
            role="button"
            aria-label="Nucleoid"
          >
            <path
              d="M 190 200 Q 230 170, 260 210 T 310 190 T 340 220"
              stroke="#7a43ad"
              strokeWidth="9"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M 210 220 Q 250 240, 280 200 T 330 210"
              stroke="#7a43ad"
              strokeWidth="7"
              fill="none"
              strokeLinecap="round"
            />
            <text x="270" y="260" textAnchor="middle" fill="#582986" className="text-[11px] font-semibold font-sans">
              Nucleoid (Naked Chromosome)
            </text>
          </g>
        </svg>
      )}

      {/* 5. White Blood Cell */}
      {diagramId === "whiteBlood" && (
        <svg
          viewBox="0 0 600 440"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of White Blood Cell"
        >
          {/* Cell Membrane */}
          <circle cx="300" cy="220" r="175" fill="#f4f5fa" stroke="#b9bfd7" strokeWidth="6" />
          <text x="90" y="75" className="text-[12px] font-sans fill-ink-secondary">White Blood Cell (Leucocyte)</text>

          {/* Lobed Nucleus */}
          <g
            style={getStyle("nucleus", "#6f35a1")}
            onClick={() => onSelectStructure("nucleus")}
            tabIndex={0}
            role="button"
            aria-label="Lobed Nucleus"
          >
            <circle cx="250" cy="180" r="42" />
            <circle cx="350" cy="190" r="38" />
            <circle cx="300" cy="270" r="45" />
            {/* Chromatin Bridges */}
            <path d="M 250 180 Q 300 170, 350 190 Q 340 240, 300 270 Q 260 240, 250 180" stroke="#4a1572" strokeWidth="14" fill="none" />
            <text x="300" y="225" textAnchor="middle" fill="#FFFFFF" className="text-[11px] font-semibold font-sans">
              Lobed Nucleus
            </text>
          </g>

          {/* Lysosomes */}
          <g
            style={getStyle("lysosome", "#8b54b7")}
            onClick={() => onSelectStructure("lysosome")}
            tabIndex={0}
            role="button"
            aria-label="Lysosome"
          >
            <circle cx="190" cy="260" r="16" />
            <circle cx="210" cy="130" r="14" />
            <circle cx="390" cy="130" r="15" />
            <text x="175" y="295" fill="#6b21a8" className="text-[11px] font-semibold font-sans">
              Digestive Lysosomes
            </text>
          </g>

          {/* Granules */}
          <g
            style={getStyle("granules", "#c06696")}
            onClick={() => onSelectStructure("granules")}
            tabIndex={0}
            role="button"
            aria-label="Granules"
          >
            {[
              [160, 200], [210, 310], [380, 270], [420, 210], [310, 120]
            ].map(([x, y], idx) => (
              <circle key={idx} cx={x} cy={y} r="8" />
            ))}
            <text x="410" y="305" fill="#9d174d" className="text-[11px] font-semibold font-sans">
              Antimicrobial Granules
            </text>
          </g>
        </svg>
      )}

      {/* 6. Epithelial Cell */}
      {diagramId === "epithelial" && (
        <svg
          viewBox="0 0 600 460"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of Columnar Epithelial Cell"
        >
          {/* Main Columnar Body */}
          <rect x="180" y="90" width="240" height="310" rx="12" fill="#fdf2f4" stroke="#d79baa" strokeWidth="4" />

          {/* Microvilli Brush Border */}
          <g
            style={getStyle("microvilli", "#c86f80")}
            onClick={() => onSelectStructure("microvilli")}
            tabIndex={0}
            role="button"
            aria-label="Microvilli"
          >
            {Array.from({ length: 14 }).map((_, i) => (
              <rect key={i} x={185 + i * 16} y="45" width="10" height="48" rx="5" />
            ))}
            <text x="300" y="32" textAnchor="middle" fill="#991b1b" className="text-[12px] font-bold font-sans">
              Microvilli (Apical Brush Border)
            </text>
          </g>

          {/* Tight Junctions */}
          <g
            style={getStyle("junctions", "#9f6cbd")}
            onClick={() => onSelectStructure("junctions")}
            tabIndex={0}
            role="button"
            aria-label="Tight Junctions"
          >
            <rect x="172" y="105" width="16" height="50" rx="4" />
            <rect x="412" y="105" width="16" height="50" rx="4" />
            <text x="140" y="135" textAnchor="end" fill="#6b21a8" className="text-[11px] font-semibold font-sans">
              Tight Junctions
            </text>
          </g>

          {/* Basal Nucleus */}
          <g
            style={getStyle("nucleus", "#7a4aa2")}
            onClick={() => onSelectStructure("nucleus")}
            tabIndex={0}
            role="button"
            aria-label="Nucleus"
          >
            <ellipse cx="300" cy="300" rx="60" ry="45" />
            <circle cx="310" cy="295" r="16" fill="#4c1d95" />
            <text x="300" y="305" textAnchor="middle" fill="#FFFFFF" className="text-[11px] font-semibold font-sans">
              Basal Nucleus
            </text>
          </g>
        </svg>
      )}

      {/* 7. Muscle Cell */}
      {diagramId === "muscle" && (
        <svg
          viewBox="0 0 620 400"
          className="w-full h-full max-h-[440px]"
          role="img"
          aria-label="2D Schematic of Skeletal Muscle Fiber"
        >
          {/* Sarcolemma */}
          <g
            style={getStyle("sarcolemma", "#d7b284")}
            onClick={() => onSelectStructure("sarcolemma")}
            tabIndex={0}
            role="button"
            aria-label="Sarcolemma"
          >
            <rect x="40" y="90" width="540" height="220" rx="30" fill="#fbf5ee" stroke="#b45309" strokeWidth="6" />
            <text x="65" y="75" fill="#92400e" className="text-[12px] font-bold font-sans">
              Sarcolemma (Excitable Outer Membrane)
            </text>
          </g>

          {/* Myofibril Bundles */}
          <g
            style={getStyle("myofibril", "#bd3d51")}
            onClick={() => onSelectStructure("myofibril")}
            tabIndex={0}
            role="button"
            aria-label="Myofibril"
          >
            {[135, 185, 235].map((y, rowIdx) => (
              <g key={rowIdx}>
                <rect x="70" y={y} width="480" height="34" rx="4" fill="#fecdd3" stroke="#e11d48" strokeWidth="1.5" />
                {/* Sarcomere Bands (A band, I band, Z lines) */}
                {Array.from({ length: 9 }).map((_, bandIdx) => (
                  <rect key={bandIdx} x={80 + bandIdx * 52} y={y + 2} width="26" height="30" fill="#be123c" />
                ))}
              </g>
            ))}
            <text x="310" y="125" textAnchor="middle" fill="#881337" className="text-[11px] font-semibold font-sans">
              Contractile Myofibril (Striated Sarcomeres)
            </text>
          </g>

          {/* Mitochondria */}
          <g
            style={getStyle("mitochondria", "#cf7042")}
            onClick={() => onSelectStructure("mitochondria")}
            tabIndex={0}
            role="button"
            aria-label="Mitochondria"
          >
            <rect x="180" y="275" width="45" height="22" rx="10" />
            <rect x="360" y="275" width="45" height="22" rx="10" />
            <text x="270" y="292" textAnchor="middle" fill="#ea580c" className="text-[11px] font-semibold font-sans">
              Interfibrillar Mitochondria (ATP supply)
            </text>
          </g>
        </svg>
      )}
    </div>
  );
}
