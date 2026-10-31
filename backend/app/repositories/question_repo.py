import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Attempt, Question


class QuestionRepository:
    async def get_by_id(self, session: AsyncSession, question_id: str) -> Question | None:
        stmt = select(Question).where(Question.id == question_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def list_by_concept(self, session: AsyncSession, concept_id: str) -> list[Question]:
        stmt = select(Question).where(
            Question.concept_id == concept_id,
            Question.verified.is_(True),
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_verified(self, session: AsyncSession) -> list[Question]:
        stmt = select(Question).where(Question.verified.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_seen_question_ids(self, session: AsyncSession, user_id: int) -> set[str]:
        stmt = select(Attempt.question_id).where(Attempt.user_id == user_id)
        result = await session.execute(stmt)
        return set(result.scalars().all())

    async def get_attempt_by_client_id(
        self, session: AsyncSession, client_attempt_id: uuid.UUID
    ) -> Attempt | None:
        stmt = select(Attempt).where(Attempt.client_attempt_id == client_attempt_id)
        result = await session.execute(stmt)
        return result.scalars().first()


question_repo = QuestionRepository()
