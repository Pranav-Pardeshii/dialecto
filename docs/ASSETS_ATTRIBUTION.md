# Biological 3D Asset Provenance and Attribution

This document records the provenance, attribution, licensing, and source references for all 3D specimens and visual assets used in Dialecto's Interactive Biology Lab, integrated from [Cell Architecture Studio](https://github.com/cclank/cell-architecture-studio).

---

## 1. Whitelisted Biological Specimens

Dialecto strictly permits only the seven biological specimen types defined and supported by Cell Architecture Studio:

| Specimen ID | Specimen Name | Asset Type | Source Implementation / Asset | Licence |
|---|---|---|---|---|
| `plant` | Plant Cell | Production GLB | `/models/plant-cell-first001.glb` | CC-BY-4.0 / Educational Use |
| `whiteBlood` | White Blood Cell | Production GLB | `/models/white-blood-cell-user.glb` | CC-BY-4.0 / Educational Use |
| `animal` | Animal Cell | Production GLB | `/models/animal-cell-nih.glb` | Public Domain / CC0 (NIH 3D Entry 3DPX-015797) |
| `neuron` | Neuron | Production GLB | `/models/neuron-nih.glb` | Public Domain / CC0 (NIH 3D Entry 3DPX-015796) |
| `bacteria` | Bacterial Cell Wall | Production GLB | `/models/bacteria-wall-nih.glb` | Public Domain / CC0 (NIH 3D Entry 3DPX-010752) |
| `epithelial` | Epithelial Cell | Procedural 3D | Source repository procedural geometry (`EpithelialModel`) | MIT (Application Code) |
| `muscle` | Muscle Cell | Procedural 3D | Source repository procedural geometry (`MuscleModel`) | MIT (Application Code) |

---

## 2. Model Detail & Provenance Records

### 1. Plant Cell (`plant`)
- **Model Path:** `/models/plant-cell-first001.glb`
- **Preview Path:** `/cell-renders-transparent/plant.png`
- **Source:** Cell Architecture Studio
- **Origin Reference:** High-fidelity botanical plant cell GLB asset with cellulose cell wall, large central vacuole, thylakoid chloroplasts, and peripheral nucleus.
- **Licence:** CC-BY-4.0 / Educational Use.
- **Attribution:** Specimen geometry and texture maps integrated from Cell Architecture Studio open educational biology repository.

### 2. White Blood Cell (`whiteBlood`)
- **Model Path:** `/models/white-blood-cell-user.glb`
- **Preview Path:** `/cell-renders-transparent/white-blood.png`
- **Source:** Cell Architecture Studio
- **Origin Reference:** Leucocyte immune cell GLB asset featuring multi-lobed nucleus, phagocytic lysosomes, and cytoplasmic granules.
- **Licence:** CC-BY-4.0 / Educational Use.
- **Attribution:** Specimen geometry and texture maps integrated from Cell Architecture Studio open educational biology repository.

### 3. Animal Cell (`animal`)
- **Model Path:** `/models/animal-cell-nih.glb`
- **Preview Path:** `/nih-previews/animal-cell-nih.png`
- **Source URL:** https://3d.nih.gov/entries/3DPX-015797/2
- **Creator:** National Institutes of Health (NIH 3D Print Exchange)
- **Licence:** Public Domain (US Government Work) / CC0.
- **Attribution:** 3D specimen from verified NIH 3D model 3DPX-015797 via Cell Architecture Studio.

### 4. Neuron (`neuron`)
- **Model Path:** `/models/neuron-nih.glb`
- **Preview Path:** `/nih-previews/neuron-nih.png`
- **Source URL:** https://3d.nih.gov/entries/3DPX-015796/2
- **Creator:** National Institutes of Health (NIH 3D Print Exchange)
- **Licence:** Public Domain (US Government Work) / CC0.
- **Attribution:** Neuron 3D specimen from verified NIH 3D model 3DPX-015796 via Cell Architecture Studio.

### 5. Bacterial Cell Wall (`bacteria`)
- **Model Path:** `/models/bacteria-wall-nih.glb`
- **Preview Path:** `/nih-previews/bacteria-wall-nih.png`
- **Source URL:** https://3d.nih.gov/entries/3DPX-010752/2
- **Creator:** National Institutes of Health (NIH 3D Print Exchange)
- **Licence:** Public Domain (US Government Work) / CC0.
- **Attribution:** Gram-positive bacterial cell wall specimen from verified NIH 3D model 3DPX-010752 via Cell Architecture Studio.

### 6. Epithelial Cell (`epithelial`)
- **Model Type:** Procedural Three.js geometry from Cell Architecture Studio (`EpithelialModel`).
- **Preview Path:** `/cell-renders-transparent/epithelial.png`
- **Source:** Cell Architecture Studio
- **Licence:** MIT.
- **Attribution:** Procedural columnar epithelial architecture with microvilli brush border and tight junction seams from Cell Architecture Studio.

### 7. Muscle Cell (`muscle`)
- **Model Type:** Procedural Three.js geometry from Cell Architecture Studio (`MuscleModel`).
- **Preview Path:** `/cell-renders-transparent/muscle.png`
- **Source:** Cell Architecture Studio
- **Licence:** MIT.
- **Attribution:** Procedural skeletal muscle fiber architecture with repeating sarcomere myofibril bundles from Cell Architecture Studio.

---

## 3. Reference Renders & Transparent Previews

The single-subject generated reference images for thumbnails and preview metadata located in `public/cell-renders/` and `public/cell-renders-transparent/` are provided by Cell Architecture Studio under the MIT / CC-BY-4.0 educational asset licence.

---

## 4. Policy Regarding Prohibited / Unsupported Diagrams

In accordance with Dialecto's biological accuracy policy:
- No independently generated, unverified, or placeholder biological diagrams (such as Heart, Nephron, Kidney, Lungs, DNA, or external 3D models) are permitted.
- If a biological diagram is not part of the seven whitelisted specimens from Cell Architecture Studio, it is strictly excluded from the Biology Lab.
- Any missing model asset triggers an authentic "Specimen Unavailable" state rather than substituting generic geometric shapes.
