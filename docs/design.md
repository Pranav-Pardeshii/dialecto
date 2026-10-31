# Design System: Dialecto

Status: DRAFT pending developer approval before any frontend screen is built.
Built using: **Taste Skill** (`design-taste-frontend` v2, based on the anti-slop app-screen study).

---

## 1. Design Direction & Core Subject Identity

**Concept:** A calm, focused biology laboratory study space that feels like sitting with an attentive private tutor. Warm paper textures, botanical precision, crisp scientific typography, and zero "AI slop" (no neon purple glows, no zebra-striped tables, no generic icon tiles in tinted circles).

### Taste Skill Dials
- **Variance:** `4` — Predictable, structured, reliable layouts that keep the student in a deep state of study.
- **Motion:** `5` — Purposeful motion only. Motion exists strictly to explain state transitions (mastery count-up, concept node unlocking, Pip's comprehension level shift); zero decorative bouncing.
- **Density:** 
  - `4` for Student screens (airy, focused, single-task clarity, ample white space for contemplation).
  - `7` for Teacher dashboard (high information density, compact matrix, immediate pattern recognition across 30 students × 20 concepts).

---

## 2. Color System (Data-Driven Palette)

In accordance with the Taste Skill app-screen principles: *Color goes on data, not chrome.* Less than 4% of pixels carry saturated chromatic color.

### Foundation Tokens (Light Theme First)
- **Canvas / Ground (`bg-canvas`):** `#FAF9F5` (Warm botanical paper / light alabaster stone)
- **Surface / Card (`bg-surface`):** `#FFFFFF` (Pure white card for maximum contrast against ground)
- **Subtle Surface (`bg-subtle`):** `#F3F2EC` (Warm recessed wells, inputs, and hover states)
- **Hairline Borders (`border-subtle`):** `#E5E3D8` (1px clean geometric divider)
- **Ink Primary (`text-ink-primary`):** `#191A15` (Deep mineral slate; softer than harsh #000)
- **Ink Secondary (`text-ink-secondary`):** `#5E6056` (Muted caption, labels, and metadata)
- **Ink Muted (`text-ink-muted`):** `#8C8E84` (Placeholders, inactive indicators)

### Data Hue & Mastery Semantics
Color is **never the sole indicator** of state; percentage values and textual badges accompany every mastery element.

| State | Background Tint | Border / Accent | Text Ink | Numerical / Label Rule |
|---|---|---|---|---|
| **Mastered (≥80%)** | `#EDF7EE` | `#2E7D32` (Forest Emerald) | `#1B5E20` | Always display `80%–100%` + "Mastered" |
| **Learning (<80%)** | `#FEF8E7` | `#D97706` (Warm Ochre) | `#92400E` | Always display `p%` + "Learning" |
| **Unlocked (Fresh)** | `#F3F4F6` | `#64748B` (Cool Slate) | `#334155` | Always display "Ready to start" |
| **Locked** | `#ECEBE4` | `#A8A29E` (Stone) | `#78716C` | Always display Lock icon + "Prereqs needed" |
| **Misconception Alert**| `#FDF2F2` | `#DC2626` (Crimson) | `#991B1B` | Naming the specific misconception |

---

## 3. Typography & Type Scale (via `next/font`)

### Font Families
1. **Editorial Display / Headings:** `Fraunces` or `Newsreader` (Google Fonts via `next/font/google`). Gives Dialecto its signature authoritative, academic, biological textbook heritage.
2. **UI & Primary Body:** `Plus Jakarta Sans` (Google Fonts via `next/font/google`). Crisp geometric sans with wide apertures and high legibility at 12–14px.
3. **Data, Stats & Monospace:** `JetBrains Mono`. Used for token counts, latencies, mastery percentages, and model identifiers (`tabular-nums` enabled).

### Scale & Hierarchy
- `font-display` (24px, Fraunces, weight 600, tracking -0.02em): Top-level screen title (no giant hero text; app screens keep titles modest).
- `font-h2` (18px, Plus Jakarta Sans, weight 600, tracking -0.01em): Section card headers.
- `font-body` (15px, Plus Jakarta Sans, weight 400, leading 1.5): Reading lessons, question stems.
- `font-caption` (13px, Plus Jakarta Sans, weight 500): Metadata, options, badges.
- `font-mono` (12px, JetBrains Mono, weight 500, `tabular-nums`): Mastery percentages, latency, timer, question counter.

---

## 4. Spacing, Borders & Elevation

- **Grid Base:** 4px baseline scale (`p-1` = 4px, `p-2` = 8px, `p-3` = 12px, `p-4` = 16px, `p-6` = 24px, `p-8` = 32px).
- **Corner Radii:**
  - Controls, inputs, buttons, pills: `rounded-md` (6px)
  - Cards, panels, modal dialogs: `rounded-lg` (8px)
  - Avatar badges: `rounded-full`
- **Elevation:** Surfaces are predominantly flat. Separation is handled by `1px solid var(--border-subtle)`.
  - Level 0 (Canvas): flat ground `#FAF9F5`.
  - Level 1 (Card): `#FFFFFF` with 1px border. No drop shadows by default.
  - Level 2 (Flyout/Tooltip/Modal): 1px border plus subtle soft shadow `0 4px 12px rgba(25, 26, 21, 0.06)`.

---

## 5. Motion Tokens & Physics

Powered by CSS transitions and Motion (Framer Motion). Honor `prefers-reduced-motion: reduce`.
- **Duration Micro:** 120ms (Hover states, button press).
- **Duration Standard:** 200ms (Disclosure transitions, badge updates).
- **Duration Hero / Mastery:** 400ms (Mastery gauge count-up, concept node status morph).
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (snappy ease-out, zero bouncy spring overshoot).

---

## 6. Dictation-First Input Component (`WisprFlowTextarea`)

Per standing rules in `AGENTS.md`:
- Plain native `<textarea>` element — **no** rich text editors, contenteditable, or input masking.
- `autoFocus` enabled where appropriate.
- Minimum 8 rows (`min-h-[160px]`).
- Clean live word counter in the bottom tray (`JetBrains Mono`).
- Keyboard ergonomics:
  - `Ctrl + Enter` (or `Cmd + Enter`) submits the response.
  - Standard `Enter` creates a normal newline.
  - Zero key interception that could hijack cursor position during Wispr Flow system-wide dictation.
- Subtle helper label: *"Press your Wispr Flow hotkey to speak your explanation naturally."*
- Groq Whisper mic button positioned cleanly as a secondary fallback.

---

## 7. Signature Moments & Component Inventory

1. **Concept Graph (React Flow):**
   - Clean DAG layout (prerequisites on the left/top flowing down/right).
   - Custom node cards showing concept title, chapter indicator, mastery progress ring, and status label.
   - Nodes transition smoothly between `locked` → `unlocked` → `learning` → `mastered`.
2. **Practice Card with Reasoning Box:**
   - Bold, unambiguous question stem.
   - Radio options with generous hit targets (minimum 44px height).
   - Dedicated "Reasoning / Working" expansion area built with `WisprFlowTextarea`.
   - Post-submit reveal: Instant mastery delta banner (`0.41 → 0.27`), clear explanation, and tagged misconception card.
3. **Teach-Back Arena (Pip the Student):**
   - Two-column or structured conversation flow.
   - **Pip Persona Indicator:** Expressive state badge reflecting backend state machine:
     - `Level 0`: "Confused" (Pale Amber tint, furrowed brow icon)
     - `Level 1`: "Curious" (Soft Ochre, questioning icon)
     - `Level 2`: "Connecting Dots" (Light Emerald tint)
     - `Level 3`: "Understands!" (Deep Forest Emerald badge)
   - Transcript bubbles clearly distinguishing Learner vs. Pip.
   - Judge Feedback card displaying rubric criteria covered vs. missing.
4. **Teacher Heatmap (Density 7):**
   - 30 Students (rows) × 20 Concepts (columns).
   - Fixed student column with avatar initials and student name.
   - Shaded cells indicating effective mastery, hovering reveals exact % and overdue decay.
   - Top banner summarizing "Class-Wide Gaps" and "Top Misconceptions".
5. **AI Reliability Panel (`/ops`):**
   - Live metrics: Primary model status (`openai/gpt-oss-120b`), active fallback models, p50 / p95 latency gauges, breaker circuit states.

---

## 8. Screen Inventory & Layout Intent

| Screen | Route | Layout Intent |
|---|---|---|
| **Identity Switcher** | `/` | Clean modal/card: select student (Aarav, fresh) or teacher (Ms. Rao) to enter. |
| **Student Dashboard** | `/dashboard` | Hero concept graph with zoom/pan, top mastery progress overview, quick action "Continue Practice". |
| **Diagnostic Test** | `/diagnostic` | Focused distraction-free view; 15-question progress bar; instantaneous adaptive next-question flow. |
| **Targeted Practice** | `/practice` | Centered practice card (max-w-2xl), option selection, reasoning box, instant animated feedback. |
| **Teach-Back Mode** | `/teach-back/[id]` | Side-by-side arena: Left panel concept rubric & Pip status; Right panel conversation & dictation area. |
| **Spaced Review** | `/review` | Ordered list of concepts with overdue decay indicators and quick "Review Now" trigger. |
| **Teacher Dashboard** | `/class` | Dense high-utility layout: Heatmap grid, weakest concept cards, at-risk student flags. |
| **Ops & AI Stats** | `/ops` | Telemetry dashboard: model chain, latency metrics, fallback circuit status. |

---

## 9. Microcopy & Voice Tone

- **Voice:** Calm, intellectually respectful, precise, and encouraging. Never snarky, never juvenile.
- **Pip's Voice:** Deliberately inquisitive, polite, asks genuine follow-up questions based on the judge's missing concepts without sounding like a generic corporate bot.
- **Scientific Precision:** Terms match NCERT Class 10 Biology conventions verbatim (*alveoli*, *salivary amylase*, *emulsification*, *synapse*, *tropism*, *monohybrid*).
