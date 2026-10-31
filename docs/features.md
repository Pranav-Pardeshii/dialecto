# Feature Matrix: Dialecto

Priorities:
- **P0 (Must):** Required to satisfy the hackathon brief and the core demo path.
- **P1 (Should):** High-impact enhancements that strengthen judging criteria.
- **P2 (Stretch):** Polish or secondary views included only if time permits.

---

## 1. Feature Specifications

| ID | Feature | Priority | Area | Acceptance Criteria |
|---|---|---|---|---|
| **F-01** | **Diagnostic Test** (Brief #1) | **P0** | Fullstack | 15-question adaptive assessment; selects unasked concepts with uncertainty closest to 0.5; skips dependents of concepts <0.3; updates mastery and prerequisites; displays clean onboarding and final mastery profile. |
| **F-02** | **Concept Graph** (Brief #2) | **P0** | Fullstack | 20 CBSE Class 10 Biology concepts across 3 chapters; directed acyclic graph (prerequisites → dependents); nodes render mastery percentage and status (`locked`, `unlocked`, `learning`, `mastered`); smooth transition animations. |
| **F-03** | **Learner Model** (Brief #3) | **P0** | Backend | Pure Python BKT implementation with slip, guess, and transition parameters; updates in a single SQL transaction using `SELECT ... FOR UPDATE`; stores before/after mastery history in `attempts`. |
| **F-04** | **Targeted Practice & Difficulty Calibration** (Brief #4) | **P0** | Fullstack | Question selector prioritizes unlocked concepts with low effective mastery near 70% expected success; Elo-calibrated difficulty rating `b` updated after 5 attempts; displays human-readable "Why this question?" rationale. |
| **F-05** | **Misconception Detection** (Brief #5) | **P0** | Fullstack | Tagged distractors identify misconceptions deterministically; LLM classifier detects misconceptions from student free-text reasoning; feedback reveal animates mastery drop and names the scientific correction. |
| **F-06** | **Spaced-Repetition Scheduling** (Brief #6) | **P0** | Backend | SM-2 algorithm calculates repetition interval and ease factor `EF` based on answer correctness and response latency; effective mastery decays exponentially when overdue: $p_{\text{eff}} = p \cdot e^{-\text{overdue}/14}$. |
| **F-07** | **Teacher Heatmap & Gaps** (Brief #7) | **P0** | Fullstack | High-density 30 × 20 matrix (students vs. concepts); displays class-wide weakest concepts and most prevalent misconceptions; calculated directly via aggregate SQL queries. |
| **F-08** | **Teach-Back Mode with Pip** (Differentiator) | **P0** | Fullstack | Learner explains concepts to Pip; cumulative judge scores explanation against NCERT rubric; Pip's comprehension level (0–3) updates deterministically; soft-evidence Bayesian mastery update applied; up to 4 interactive turns. |
| **F-09** | **Dictation-Friendly Input** (Wispr Flow) | **P0** | Frontend | Free-text fields use unmasked, auto-focused, native `<textarea>` (≥8 rows); word counter; `Ctrl+Enter` submit shortcut; no cursor-stealing re-renders; visible Wispr Flow guidance. |
| **F-10** | **AI Reliability & Telemetry Panel** | **P0** | Fullstack | `LLMRouter` with Groq primary model (`openai/gpt-oss-120b`), fallback chain, token bucket budget, and circuit breaker; every call logged to `llm_calls` table; `/ops` dashboard displays p50/p95 latency and fallback rate. |
| **F-11** | **Spaced Review Queue UI** | **P1** | Frontend | Dedicated review view listing overdue concepts sorted by priority score; one-click launch into practice mode with `mode="review"`. |
| **F-12** | **Speech-to-Text Fallback** (Groq Whisper) | **P1** | Fullstack | In-app microphone button sending audio to `POST /speech/transcriptions` via Groq Whisper for learners without desktop dictation. |
| **F-13** | **Simulated Classroom Seeding** | **P0** | Backend | Deterministic seed (`random.Random(42)`) creating 30 simulated students with back-dated attempts and realistic class-wide weak spots across 21 days; idempotent execution. |
| **F-14** | **Teacher At-Risk & Student Drill-Down** | **P2** | Fullstack | At-risk student list (mastery <0.4 or 3+ overdue reviews); individual student detail modal showing concept mastery breakdown and attempt history. |
| **F-15** | **Offline Question Bank Generator** | **P1** | Backend | Background script generating 6 MCQs per concept with tagged distractors and dual-model solve verification check. |

---

## 2. Milestone Alignment

- **M0:** Monorepo skeleton, design system approval, app shell, demo role switcher.
- **M1:** F-02 (Concept graph), F-13 (DB models & seed), F-15 (Question generator script).
- **M2:** F-01 (Diagnostic), F-03 (BKT Learner core), F-04 (Targeted Practice), F-06 (SM-2 math).
- **M3:** F-05 (Misconception detection), F-10 (LLM Router & `/ops` telemetry).
- **M4:** F-08 (Teach-Back with Pip), F-09 (Wispr Flow dictation UX).
- **M5:** F-07 (Teacher dashboard heatmap & gaps), F-11 (Review queue).
- **M6 & M7:** F-12 (Whisper mic fallback), F-14 (At-risk drill-down), hardening, end-to-end polish.
