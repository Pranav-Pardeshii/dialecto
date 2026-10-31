# Architecture & Project Decisions: Dialecto

Record decisions in this file: Date, Decision, Reason.

---

### 2026-10-31: Phase 0 Startup & Document Inventory

- **Decision:** Note missing `docs/agents.md` from repository bundle and extract prompt and evidence specifications directly from `docs/architecture.md`, `docs/api.md`, and `docs/curriculum.md` until provided.
- **Reason:** `MASTER_PROMPT.md` lists `docs/agents.md` as authoritative doc #6, but the file was omitted in the initial files. The architecture and API documents provide comprehensive coverage of the agent schemas, state machines, and evidence rules.

- **Decision:** Use `design-taste-frontend` as the sole Taste Skill package.
- **Reason:** Upstream `https://github.com/Leonxlnx/taste-skill` only contains `design-taste-frontend` (`full-output-enforcement` is not an independent skill upstream, and its rules against incomplete output/stubs are incorporated directly into agent standing rules).

- **Decision:** Place root-level copies of `AGENTS.md` and `README.md` at project root in addition to `docs/`.
- **Reason:** Matches the repository layout prescribed in `docs/README.md` and `MASTER_PROMPT.md` section 5/6.

- **Decision:** Strictly ban mentions of backend frameworks, internal architecture, and third-party tools in any user-facing UI code or copy (e.g. no "FastAPI", "identity validation", "Wispr Flow", "Groq").
- **Reason:** Preserves a clean, minimal, beautiful, and distraction-free user experience focused purely on learning without leaking implementation details.

- **Decision:** Establish canonical concept status engine (`determine_concept_status`) in `domain/graph.py` and replace orthogonal tree edges with diagonal cubic Bézier curves (`CurvedTreeEdge`).
- **Reason:** Eliminates ad-hoc, contradictory status calculations across endpoints, ensures prerequisite decay does not cause relocking, provides transparent, authentic lock explanations with actual prerequisite names and mastery percentages, and renders an elegant hierarchical learning tree.

