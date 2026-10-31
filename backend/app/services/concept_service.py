import datetime
from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.domain.graph import (
    PrerequisiteInfo,
    determine_concept_status,
)
from app.domain.sm2 import compute_effective_mastery
from app.repositories.concept_repo import concept_repo
from app.schemas.concept import (
    ConceptDetailResponse,
    ConceptEdge,
    ConceptGraphResponse,
    ConceptMasterySummary,
    ConceptNode,
)
from app.schemas.user import UserOut, UserRole


class ConceptService:
    def compute_effective_mastery(
        self, p_mastery: float, next_due_at: datetime.datetime | None
    ) -> float:
        """Delegates directly to canonical domain implementation."""
        return compute_effective_mastery(p_mastery, next_due_at)

    async def get_concept_graph(
        self, session: AsyncSession, current_user: UserOut | None = None
    ) -> ConceptGraphResponse:
        concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)
        concept_lookup = {c.id: c for c in concepts}

        # Map: concept_id -> list of prerequisite_ids
        prereq_map: dict[str, list[str]] = defaultdict(list)
        edges: list[ConceptEdge] = []
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)
            edges.append(ConceptEdge.model_validate({"from": prereq_id, "to": dependent_id}))

        user_mastery_map: dict[str, dict[str, Any]] = {}
        if current_user and current_user.role == UserRole.STUDENT:
            user_mastery_map = await concept_repo.get_user_masteries(session, current_user.id)

        now = datetime.datetime.now(datetime.UTC)
        nodes: list[ConceptNode] = []

        for c in concepts:
            mastery_summary: ConceptMasterySummary | None = None
            if current_user and current_user.role == UserRole.STUDENT:
                m_data = user_mastery_map.get(c.id)
                attempts = m_data["attempts"] if m_data else 0

                if m_data and attempts > 0:
                    eff = compute_effective_mastery(
                        m_data["p_mastery"], m_data["next_due_at"], now=now
                    )
                else:
                    # Untested concepts do not carry arbitrary low-mastery percentages
                    eff = 0.0

                # Build prerequisite infos using base masteries to prevent decay relock
                prereq_infos: list[PrerequisiteInfo] = []
                for p_id in prereq_map[c.id]:
                    p_concept = concept_lookup.get(p_id)
                    p_name = p_concept.name if p_concept else p_id
                    p_m = user_mastery_map.get(p_id)
                    # If prerequisite has attempts, use its base mastery; if not attempted, 0.0
                    p_base = (
                        float(p_m["p_mastery"])
                        if (p_m and p_m.get("attempts", 0) > 0)
                        else 0.0
                    )
                    prereq_infos.append(
                        PrerequisiteInfo(
                            prerequisite_id=p_id,
                            prerequisite_name=p_name,
                            base_mastery=p_base,
                        )
                    )

                status_details = determine_concept_status(
                    effective_mastery=eff,
                    attempts=attempts,
                    prerequisites=prereq_infos,
                )

                mastery_summary = ConceptMasterySummary(
                    p_effective=eff,
                    status=status_details.status,
                    lock_reason=status_details.lock_reason,
                    unmet_prerequisites=[
                        u["name"] for u in status_details.unmet_prerequisites
                    ],
                )

            nodes.append(
                ConceptNode(
                    id=c.id,
                    name=c.name,
                    chapter=c.chapter,
                    position=c.position,
                    mastery=mastery_summary,
                )
            )

        return ConceptGraphResponse(nodes=nodes, edges=edges)

    async def get_concept_detail(
        self, session: AsyncSession, concept_id: str
    ) -> ConceptDetailResponse:
        concept = await concept_repo.get_by_id(session, concept_id)
        if not concept:
            raise NotFoundError(f"Concept '{concept_id}' not found")

        prereqs = await concept_repo.get_prerequisites_for_concept(session, concept_id)
        counts = await concept_repo.get_misconception_counts(session)
        misconception_count = counts.get(concept_id, 0)

        return ConceptDetailResponse(
            id=concept.id,
            name=concept.name,
            chapter=concept.chapter,
            description=concept.description,
            lesson_md=concept.lesson_md,
            prerequisites=prereqs,
            misconception_count=misconception_count,
            lock_reason=None,
        )


concept_service = ConceptService()
