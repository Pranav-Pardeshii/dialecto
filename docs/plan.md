# Plan: 9 hours, solo

## Operating model

You are the product owner, reviewer, and tester. The Antigravity agent is the builder. **Your scarce resource is review attention, not typing speed**, so the plan is built around it:

- One **vertical slice** at a time: backend and UI together, ending in a click-through demo path you can verify in under 2 minutes.
- Approve or redirect each slice plan in under 2 minutes. Do not read every diff; read the summary, run the demo path, and spot-check the risky parts (learner math, prompts, migrations).
- Use the agent's run time for work only you can do: content review, the LinkedIn draft, Wispr Flow recordings, design approvals.
- If Antigravity lets you run agents in parallel, parallelize only **inside** a slice and on separate folders (`backend/` and `frontend/`). Otherwise run sequentially. Never run two agents on the same files.
- Hour 0 to 1:15 is deliberately heavy on setup and design, because rework on a solo build is far more expensive than on a team.

## Timeline

| Time | Slice | What happens | Gate |
|---|---|---|---|
| 0:00 to 0:40 | **M0** Setup | Create repo `dialecto`, copy docs, install Taste Skill (`npx skills add ... design-taste-frontend` and `full-output-enforcement`), paste `MASTER_PROMPT.md`, agent writes Phase 0 docs, scaffolds backend and frontend, Compose, Makefile, CI | `make check` green |
| 0:40 to 1:15 | **M0** Design foundation | Agent drafts `docs/design.md` with the Taste Skill; **you approve the look**; app shell and role switcher built in that design | Look approved before any screen is built |
| 1:15 to 2:30 | **M1** Data and graph | Models, migration, seed, `/concepts`, concept graph screen. Start the question generator; **review `curriculum.md` (30 min) while it runs**. Deploy the skeleton (Vercel, container host, Neon) and smoke test it | Real graph renders; curriculum verified; skeleton live |
| 2:30 to 4:00 | **M2** Learner core | Domain math with unit tests; diagnostic and practice endpoints and screens | Diagnostic and practice work end to end |
| 4:00 to 4:45 | **M3** AI layer | LLM router, classifier, reasoning box, misconception reveal | Wrong answer with reasoning names a misconception |
| 4:45 to 6:15 | **M4** Teach-Back | Judge, Pip, state machine, endpoints, chat UI (dictation-first) | **Go/no-go at 6:15** |
| 6:15 to 7:00 | **M5** Teacher | Heatmap, gaps, misconceptions, simulated class, minimal review entry | **Feature freeze at 7:00** |
| 7:00 to 7:45 | **M6** Hardening | Error paths, tests, `/ready`, degradation, production smoke test | Production demo path works |
| 7:45 to 8:45 | **M7** Polish and demo | Taste audit pass, AI panel, screenshots, **record demo (Wispr Flow visible)**, finalize LinkedIn post, submit | Submitted |
| 8:45 to 9:00 | Buffer | Nothing new | None |

Draft the LinkedIn post (dictated with Wispr Flow) during any agent run in M3 or M4. Do not leave it for the end.

## Gates and decisions

- **6:15 go/no-go.** If Teach-Back does not work end to end, **cut Pip** and keep the judge only: an "Explain it in your own words" box that scores the explanation and updates mastery. You keep the dictation story and the learner-model evidence.
- **Feature freeze at 7:00.** After that: bug fixes, polish, deploy, demo only.
- The brief requires a teacher dashboard. If time is short, reduce it to **heatmap plus weakest-concepts list**. Do not drop it.

## Cut list (cut from the bottom up)

1. Teacher drill-down page for a single student
2. At-risk list
3. AI reliability panel UI (keep the endpoint and logs)
4. Groq Whisper mic button
5. Review queue UI (keep SM-2 scheduling in the backend and the due endpoint)
6. LLM misconception classifier (keep the deterministic distractor tags)
7. Dark mode, extra micro-interactions

**Never cut:** learner model, concept graph, diagnostic, targeted practice, teacher heatmap, Teach-Back (at least the judge), seeded class data, demo video, LinkedIn post, the design polish on the six signature moments.

## Risk register

| Risk | Mitigation |
|---|---|
| Solo workload: you are the only reviewer | Vertical slices with 2-minute demo paths; agent summaries; spot-check only risky code; strict cut list |
| Agent drifts from the plan | `AGENTS.md`, `progress.md`, slice plans approved before work; stop-and-ask rules |
| Design drift or generic "AI slop" UI | Taste Skill as the single design direction; `design.md` approved first; audit pass at M7 |
| Groq free-tier token limits (about 8k tokens per minute on the main model) | Lean prompts, fallback chain with separate per-model limits, pre-generated content, token budget in the router, consider the paid Developer tier if a card is available |
| Wrong biology in content | Human review of `curriculum.md`; dual-model solve check; unverified items never served |
| Judge scores noisy or wrong | Rubric-based prompt, soft evidence weighting, eval golden set before the demo |
| Deployment surprises late in the build | Deploy the skeleton in M1 and smoke test every milestone after |
| Free-hosting cold start during judging | Ping `/health` before the demo; "waking the server" state; record the video from a warm instance |
| Types drift between backend and frontend | Regenerate API types after every slice; CI typecheck |

## Wispr Flow evidence (20% of the score)

Wispr Flow has no public API, so the score comes from **visible, genuine usage plus product design**.

- **Product:** every free-text field is a dictation-friendly textarea; Teach-Back is designed around speaking an explanation out loud; a short in-app hint shows the learner how to use their Wispr Flow hotkey.
- **Process:** dictate Antigravity prompts, commit messages, docs, and the LinkedIn drafts with Wispr Flow, and screen-record some of it with the Wispr Flow indicator visible.
- **Demo video:** show a learner dictating a Teach-Back explanation with Wispr Flow and Pip's level rising.
- **LinkedIn post:** include a clear "How I used Wispr Flow" paragraph with a short clip.
- **Verify:** check Product Space's support page for exactly how they verify Wispr Flow usage, and follow it.

## 90-second demo script

1. **(0:00 to 0:10) Hook.** "Most AI tutors answer questions. Dialecto tracks what you actually understand."
2. **(0:10 to 0:25) Diagnostic.** Fresh student takes a few questions; the concept graph lights up with mastery colors and locked concepts.
3. **(0:25 to 0:45) Misconception detection.** Answer wrong; dictate the reasoning with Wispr Flow; Dialecto names the misconception ("you think the oxygen comes from CO2") and mastery drops with an animation.
4. **(0:45 to 1:10) Teach-Back.** Open the concept; dictate an explanation to Pip; Pip's level rises from confused to "got it"; mastery jumps.
5. **(1:10 to 1:25) Teacher view.** Switch role; class heatmap and top misconceptions across 30 students.
6. **(1:25 to 1:30) Reliability.** Flash the AI panel: primary model, automatic fallback, latency.

## LinkedIn post outline (15% of the score)

Hook (the problem) → what Dialecto is (3 bullets) → the learner model in one line → Teach-Back → "How I used Wispr Flow" → short demo clip → what I learned building solo in 9 hours → links (repo, demo) → relevant tags (Product Space, Wispr Flow). Draft by hour 4:45 (dictated), finalize at hour 8.

## Checkpoints

- **2:30:** skeleton deployed and graph live. If not, stop and fix deployment before continuing.
- **4:00:** diagnostic and practice work. This is your safety net; everything after is upside.
- **6:15:** Teach-Back go/no-go.
- **7:00:** freeze; run the demo script once on the deployed URLs.
