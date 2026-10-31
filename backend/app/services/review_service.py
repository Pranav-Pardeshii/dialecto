import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.sm2 import compute_effective_mastery
from app.models.entities import Concept, Mastery
from app.schemas.review import ReviewDueItem


class ReviewService:
    async def get_due_reviews(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> list[ReviewDueItem]:
        """Calculates concepts due for spaced repetition review based on canonical next_due_at timestamp."""
        now = datetime.datetime.now(datetime.UTC)

        concepts_stmt = select(Concept).order_by(Concept.position)
        concepts = (await session.execute(concepts_stmt)).scalars().all()
        concept_map = {c.id: c for c in concepts}

        mastery_stmt = select(Mastery).where(Mastery.user_id == user_id)
        masteries = (await session.execute(mastery_stmt)).scalars().all()

        due_items: list[ReviewDueItem] = []

        for m in masteries:
            c = concept_map.get(m.concept_id)
            if not c or m.attempts == 0:
                continue

            # Canonical condition: an item is due if current time is at or past next_due_at
            if m.next_due_at and now >= m.next_due_at:
                p_eff = compute_effective_mastery(m.p_mastery, m.next_due_at, now=now)
                seconds_overdue = (now - m.next_due_at).total_seconds()
                days_overdue = max(0, int(seconds_overdue // 86400))

                due_items.append(
                    ReviewDueItem(
                        concept_id=c.id,
                        name=c.name,
                        chapter=c.chapter,
                        p_effective=round(p_eff, 4),
                        days_overdue=days_overdue,
                        next_due_at=m.next_due_at,
                    )
                )

        # Order by most overdue days descending, then lowest effective mastery
        due_items.sort(key=lambda x: (x.days_overdue, -x.p_effective), reverse=True)
        return due_items


review_service = ReviewService()
