import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.graph import PrerequisiteInfo, determine_concept_status
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
        concept_lookup = {c.id: c for c in concepts}
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
            if m and m.get("attempts", 0) > 0:
                effective_map[c.id] = compute_effective_mastery(
                    m["p_mastery"], m["next_due_at"], now=now
                )
            else:
                effective_map[c.id] = 0.0

        items: list[LearnerMasteryItem] = []
        for c in concepts:
            m = user_masteries.get(c.id)
            attempts = m["attempts"] if m else 0
            p_mast = m["p_mastery"] if (m and attempts > 0) else 0.0
            p_eff = effective_map[c.id]
            last_seen = m["last_seen_at"] if m else None
            next_due = m["next_due_at"] if m else None

            # Base masteries of prerequisites to prevent decay relock
            prereq_infos: list[PrerequisiteInfo] = []
            for p_id in prereq_map[c.id]:
                p_concept = concept_lookup.get(p_id)
                p_name = p_concept.name if p_concept else p_id
                p_m = user_masteries.get(p_id)
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
                effective_mastery=p_eff,
                attempts=attempts,
                prerequisites=prereq_infos,
            )

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
                    status=status_details.status,
                )
            )

        return items

    async def get_summary(self, session: AsyncSession, user_id: int) -> LearnerSummaryResponse:
        mastery_items = await self.get_mastery_list(session, user_id)
        if not mastery_items:
            return LearnerSummaryResponse(
                overall_mastery=0.0,
                weakest=[],
                due_count=0,
                active_misconceptions=[],
            )

        now = datetime.datetime.now(datetime.UTC)
        # Only compute overall mastery across attempted concepts, or 0.0 if none
        attempted_items = [it for it in mastery_items if it.attempts > 0]
        if attempted_items:
            overall = sum(item.p_effective for item in attempted_items) / len(attempted_items)
        else:
            overall = 0.0

        # Weakest 3 concepts among attempted or unlocked concepts
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
            ActiveMisconceptionItem(
                id=row[0],
                statement=row[1],
                concept_id=row[2],
            )
            for row in misc_rows
        ]

        return LearnerSummaryResponse(
            overall_mastery=round(overall, 4),
            weakest=weakest,
            due_count=due_count,
            active_misconceptions=active_miscs,
        )


learner_service = LearnerService()
