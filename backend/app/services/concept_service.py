import datetime
import math
from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.domain.graph import calculate_concept_status
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
        """Effective mastery with SM-2 decay:

        p_effective = p_mastery * exp(-max(0, days_overdue) / 14)
        """
        if not next_due_at:
            return round(p_mastery, 4)

        now = datetime.datetime.now(datetime.UTC)
        if now <= next_due_at:
            return round(p_mastery, 4)

        days_overdue = (now - next_due_at).total_seconds() / 86400.0
        decay = math.exp(-days_overdue / 14.0)
        return round(p_mastery * decay, 4)

    async def get_concept_graph(
        self, session: AsyncSession, current_user: UserOut | None = None
    ) -> ConceptGraphResponse:
        concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)

        # Map: concept_id -> list of prerequisite_ids
        prereq_map: dict[str, list[str]] = defaultdict(list)
        edges: list[ConceptEdge] = []
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)
            edges.append(ConceptEdge.model_validate({"from": prereq_id, "to": dependent_id}))

        user_mastery_map: dict[str, dict[str, Any]] = {}
        if current_user and current_user.role == UserRole.STUDENT:
            user_mastery_map = await concept_repo.get_user_masteries(session, current_user.id)

        # Pre-compute effective masteries for status calculation
        effective_masteries: dict[str, float] = {}
        for c in concepts:
            m_data = user_mastery_map.get(c.id)
            if m_data:
                eff = self.compute_effective_mastery(m_data["p_mastery"], m_data["next_due_at"])
            else:
                eff = c.p_l0
            effective_masteries[c.id] = eff

        nodes: list[ConceptNode] = []
        for c in concepts:
            mastery_summary: ConceptMasterySummary | None = None
            if current_user and current_user.role == UserRole.STUDENT:
                m_data = user_mastery_map.get(c.id)
                attempts = m_data["attempts"] if m_data else 0
                eff = effective_masteries[c.id]

                # List of effective masteries of prerequisites
                prereq_effs = [effective_masteries.get(p_id, 0.3) for p_id in prereq_map[c.id]]
                status = calculate_concept_status(eff, attempts, prereq_effs)

                mastery_summary = ConceptMasterySummary(
                    p_effective=eff,
                    status=status,
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
        )


concept_service = ConceptService()
