import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.graph import calculate_concept_status
from app.domain.sm2 import compute_effective_mastery
from app.models.entities import DetectedMisconception, Misconception
from app.repositories.concept_repo import concept_repo
from app.schemas.learner import (
    ActiveMisconceptionItem,
    LearnerMasteryItem,
    LearnerSummaryResponse,
)


class LearnerService:
    async def get_mastery_list(
        self, session: AsyncSession, user_id: int
    ) -> list[LearnerMasteryItem]:
        concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)

        prereq_map: dict[str, list[str]] = {}
        for c in concepts:
            prereq_map[c.id] = []
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)

        now = datetime.datetime.now(datetime.UTC)
        effective_map: dict[str, float] = {}
        for c in concepts:
            m = user_masteries.get(c.id)
            p_mast = m["p_mastery"] if m else c.p_l0
            next_due = m["next_due_at"] if m else None
            effective_map[c.id] = compute_effective_mastery(p_mast, next_due, now=now)

        items: list[LearnerMasteryItem] = []
        for c in concepts:
            m = user_masteries.get(c.id)
            p_mast = m["p_mastery"] if m else c.p_l0
            p_eff = effective_map[c.id]
            attempts = m["attempts"] if m else 0
            last_seen = m["last_seen_at"] if m else None
            next_due = m["next_due_at"] if m else None

            prereq_effs = [effective_map.get(p, 0.3) for p in prereq_map[c.id]]
            status = calculate_concept_status(p_eff, attempts, prereq_effs)

            items.append(
                LearnerMasteryItem(
                    concept_id=c.id,
                    concept_name=c.name,
                    chapter=c.chapter,
                    p_mastery=round(p_mast, 4),
                    p_effective=round(p_eff, 4),
                    attempts=attempts,
                    last_seen_at=last_seen,
                    next_due_at=next_due,
                    status=status,
                )
            )

        return items

    async def get_summary(self, session: AsyncSession, user_id: int) -> LearnerSummaryResponse:
        mastery_items = await self.get_mastery_list(session, user_id)
        if not mastery_items:
            return LearnerSummaryResponse(
                overall_mastery=0.30,
                weakest=[],
                due_count=0,
                active_misconceptions=[],
            )

        now = datetime.datetime.now(datetime.UTC)
        overall = sum(item.p_effective for item in mastery_items) / len(mastery_items)

        # Weakest 3 concepts
        sorted_by_mastery = sorted(mastery_items, key=lambda x: x.p_effective)
        weakest = [item.concept_id for item in sorted_by_mastery[:3]]

        # Due count
        due_count = sum(1 for item in mastery_items if item.next_due_at and now > item.next_due_at)

        # Active misconceptions
        misc_stmt = (
            select(
                DetectedMisconception.misconception_id,
                Misconception.statement,
                Misconception.concept_id,
            )
            .join(Misconception, DetectedMisconception.misconception_id == Misconception.id)
            .where(
                DetectedMisconception.user_id == user_id,
                DetectedMisconception.resolved_at.is_(None),
            )
        )
        misc_rows = (await session.execute(misc_stmt)).all()
        active_miscs = [
            ActiveMisconceptionItem(id=row[0], statement=row[1], concept_id=row[2])
            for row in misc_rows
        ]

        return LearnerSummaryResponse(
            overall_mastery=round(overall, 4),
            weakest=weakest,
            due_count=due_count,
            active_misconceptions=active_miscs,
        )


learner_service = LearnerService()
