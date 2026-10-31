from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Concept, ConceptPrerequisite, Mastery, Misconception


class ConceptRepository:
    async def list_all(self, session: AsyncSession) -> list[Concept]:
        stmt = select(Concept).order_by(Concept.position)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, concept_id: str) -> Concept | None:
        stmt = select(Concept).where(Concept.id == concept_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def list_all_prerequisites(self, session: AsyncSession) -> list[tuple[str, str]]:
        stmt = select(ConceptPrerequisite.concept_id, ConceptPrerequisite.prerequisite_id)
        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_prerequisites_for_concept(self, session: AsyncSession, concept_id: str) -> list[str]:
        stmt = select(ConceptPrerequisite.prerequisite_id).where(
            ConceptPrerequisite.concept_id == concept_id
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_misconception_counts(self, session: AsyncSession) -> dict[str, int]:
        stmt = select(Misconception.concept_id, func.count(Misconception.id)).group_by(
            Misconception.concept_id
        )
        result = await session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_user_masteries(
        self, session: AsyncSession, user_id: int
    ) -> dict[str, dict[str, Any]]:
        stmt = select(Mastery).where(Mastery.user_id == user_id)
        result = await session.execute(stmt)
        masteries = result.scalars().all()
        return {
            m.concept_id: {
                "p_mastery": m.p_mastery,
                "attempts": m.attempts,
                "last_seen_at": m.last_seen_at,
                "next_due_at": m.next_due_at,
            }
            for m in masteries
        }


concept_repo = ConceptRepository()
