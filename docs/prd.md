# Product Requirements Document (PRD): Dialecto

**Project:** Dialecto  
**Mission:** An adaptive CBSE Class 10 Biology exam-prep tutor with a real Bayesian learner model, misconception detection from reasoning, spaced repetition, teacher analytics, and a differentiator Teach-Back mode with "Pip".  
**Competition / Context:** Agentic AI Hackathon (Product Space × Wispr Flow).

---

## 1. Problem Statement

Most AI tutoring applications behave as generic chat interfaces: they answer student questions on the fly but keep no structured, persistent representation of what the learner actually understands. When a student answers incorrectly, conventional tools score it binary (right vs. wrong) without diagnosing the underlying conceptual flaw.

Moreover, the most powerful way to master a subject is the **Feynman Technique**—explaining concepts in one's own words. Students studying for high-stakes exams (like CBSE Class 10 Board Exams) rarely have an attentive study partner to practice explaining concepts to, and typing lengthy scientific explanations on standard keyboards creates friction.

Dialecto solves this by pairing:
1. A **verifiable mathematical learner model** (Bayesian Knowledge Tracing, Elo-calibrated difficulty, SM-2 spaced repetition).
2. **Teach-Back mode with Pip**, a naive AI student whose comprehension is driven by a deterministic backend state machine.
3. A **dictation-first user experience** tailored for seamless voice explanation via Wispr Flow.
4. An actionable **Teacher Dashboard** revealing class-wide conceptual gaps and top misconceptions.

---

## 2. Target Personas

### Persona 1: Aarav (Student)
- **Profile:** 15-year-old student preparing for CBSE Class 10 Science Board Exams.
- **Pain Points:** Finds Biology overwhelming due to technical terminology (photosynthesis, reflex arcs, monohybrid crosses); easily confuses related mechanisms (e.g., believing oxygen released in photosynthesis comes from carbon dioxide instead of water); struggles with long typing sessions when explaining his reasoning.
- **Goals:** Wants to know exactly which concepts he is weak in, receive practice calibrated to his ability, practice explaining answers naturally out loud, and avoid last-minute cramming through spaced repetition.

### Persona 2: Ms. Rao (Teacher)
- **Profile:** Class 10 Biology teacher managing 30 students.
- **Pain Points:** Grading 30 pen-and-paper tests provides delayed, coarse-grained feedback; cannot see subtle misconceptions shared across the class; lacks time to build personalized revision plans for each student.
- **Goals:** Wants an instant visual heatmap of class mastery across the 20 NCERT syllabus concepts, a clear list of top misconceptions, and immediate visibility into at-risk students who need targeted intervention.

---

## 3. User Stories

### Student Journey
- **US-1 (Diagnostic):** As a student, I want to take a short, adaptive diagnostic test so that Dialecto can immediately establish my baseline mastery across the syllabus.
- **US-2 (Concept Graph):** As a student, I want to view an interactive concept graph showing my mastery percentage per concept and prerequisites so I understand my learning path.
- **US-3 (Targeted Practice):** As a student, I want questions targeted at my weakest unlocked concepts calibrated to roughly 70% expected success.
- **US-4 (Misconception Detection):** As a student, when I submit an answer with my reasoning, I want the system to identify any misconception I hold and explain the correct biological mechanism.
- **US-5 (Teach-Back Mode):** As a student, I want to explain a concept out loud to Pip (a naive peer AI) using Wispr Flow dictation, watch Pip's understanding increase, and earn mastery evidence.
- **US-6 (Spaced Repetition):** As a student, I want overdue concepts scheduled for review so I don't forget them before the board exams.

### Teacher Journey
- **US-7 (Class Heatmap):** As a teacher, I want to see a 30 × 20 matrix of student mastery across all syllabus concepts to identify class-wide strengths and weaknesses.
- **US-8 (Gap Analysis):** As a teacher, I want a sorted list of the weakest concepts and most common misconceptions in my class to plan my next revision lesson.

---

## 4. Goals and Non-Goals

### Goals (In Scope for Hackathon)
- Pure, unit-tested domain models: BKT (`P(L)`), Elo difficulty calibration (`b`), SM-2 spaced repetition (`EF`, interval).
- 20 CBSE Class 10 Biology concepts across 3 chapters (Life Processes, Control and Coordination, Heredity).
- Resilient LLM Router with primary model (`openai/gpt-oss-120b`), ordered fallback chain, circuit breaker, token budget, and repair retries.
- High-taste, dictation-friendly UI built with the Taste Skill (`design-taste-frontend`).
- Live AI reliability telemetry (`/ops` and `llm_calls` table).

### Non-Goals (Out of Scope)
- Complex user authentication (demo identities selected via `X-Demo-User-Id` header).
- External message queues (Redis/Celery); background logging uses `asyncio.Queue`.
- Multi-subject or multi-grade expansion (strictly CBSE Class 10 Biology).
- Student-to-student live multiplayer features.

---

## 5. Success Metrics & Rubric Mapping

| Rubric Dimension | Weight | Target Metric / Deliverable |
|---|---|---|
| **Wispr Flow Usage** | 20% | All free-text inputs use plain, native `<textarea>` with hotkey cues; Teach-Back designed around voice explanation; visible usage in demo video. |
| **Prototype & UX** | 20% | Adherence to Taste Skill; clean typography; responsive layout; zero "AI slop"; loading, empty, and error states on every screen. |
| **AI Integration** | 20% | Production-grade LLM Router with Groq SDK; Pydantic validation; fallback chain; token budget; graceful degradation if LLM is offline. |
| **Problem Understanding**| 15% | Real mathematical learner model (BKT); accurate NCERT Biology curriculum; misconception catalog with tagged distractors. |
| **LinkedIn Post & Video** | 15% | High-impact 90-second demo video; thoughtful LinkedIn post documenting the 9-hour build and Wispr Flow workflow. |
| **Innovation** | 10% | Teach-Back mode where Pip's comprehension level is governed by a deterministic backend state machine feeding Bayesian soft evidence. |

---

## 6. 90-Second Demo Script

1. **(0:00 – 0:10) Hook:**  
   *"Most AI tutors answer questions. Dialecto tracks what you actually understand."*
2. **(0:10 – 0:25) Diagnostic:**  
   Aarav (fresh student) answers initial diagnostic items; the concept graph lights up with mastery percentages and unlocked nodes.
3. **(0:25 – 0:45) Misconception Detection:**  
   Aarav selects a distractor on photosynthesis and dictates his reasoning with Wispr Flow; Dialecto detects the misconception (*"oxygen comes from CO₂ instead of water"*), displays the scientific correction, and mastery animates downwards.
4. **(0:45 – 1:10) Teach-Back with Pip:**  
   Aarav opens Teach-Back mode; dictates an explanation to Pip using Wispr Flow; Pip moves from "Confused" to "Understands!"; mastery score jumps based on rubric evaluation.
5. **(1:10 – 1:25) Teacher View:**  
   Switch to Ms. Rao's view: 30-student class heatmap instantly reveals that 65% of the class shares the photosynthesis misconception.
6. **(1:25 – 1:30) AI Reliability:**  
   Quick flash of the `/ops` panel showing live Groq latency, primary vs. fallback model usage, and zero dropped calls.

---

## 7. Key Risks & Mitigations

- **Risk:** Groq free-tier rate limits during demo.  
  *Mitigation:* In-process token budget, automatic fallback chain, offline pre-generation of question bank.
- **Risk:** LLM returns malformed JSON.  
  *Mitigation:* Single repair retry with schema guidance, followed by fallback model.
- **Risk:** Design drift or generic look.  
  *Mitigation:* Taste Skill tokens codified in `docs/design.md` and approved by developer prior to building UI.

