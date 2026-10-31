import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.domain.explainable_mastery import (
    calculate_evidence_strength,
    determine_trend,
    generate_mastery_narrative,
)
from app.domain.graph import PrerequisiteInfo, determine_concept_status
from app.domain.sm2 import compute_effective_mastery
from app.models.entities import (
    Attempt,
    Concept,
    ConceptPrerequisite,
    DetectedMisconception,
    DiagramAssessment,
    Mastery,
    Misconception,
    Session,
    SessionKindEnum,
    TeachbackSession,
)
from app.schemas.explainable_mastery import (
    AssessmentBreakdownOut,
    ExplainableConceptMasteryResponse,
    MisconceptionStateOut,
    TimelineEventOut,
)


class ExplainableMasteryService:
    async def get_concept_explainable_mastery(
        self, session: AsyncSession, user_id: int, concept_id: str
    ) -> ExplainableConceptMasteryResponse:
        # 1. Fetch concept
        concept_stmt = select(Concept).where(Concept.id == concept_id)
        concept_res = await session.execute(concept_stmt)
        concept = concept_res.scalars().first()
        if not concept:
            raise NotFoundError(f"Concept '{concept_id}' not found.")

        # 2. Fetch mastery row
        mastery_stmt = select(Mastery).where(
            Mastery.user_id == user_id, Mastery.concept_id == concept_id
        )
        mastery_res = await session.execute(mastery_stmt)
        mastery = mastery_res.scalars().first()

        attempts = mastery.attempts if mastery else 0
        p_mastery = mastery.p_mastery if (mastery and attempts > 0) else 0.0
        last_seen = mastery.last_seen_at if mastery else None
        next_due = mastery.next_due_at if mastery else None
        now = datetime.datetime.now(datetime.UTC)

        # Spaced repetition decay & overdue computation
        days_overdue = 0
        is_overdue = False
        p_eff = p_mastery
        if next_due and now > next_due:
            is_overdue = True
            delta = now - next_due
            days_overdue = max(0, delta.days)
            p_eff = round(compute_effective_mastery(p_mastery, next_due, now), 4)

        # Fetch prerequisite blockers
        prereq_stmt = (
            select(ConceptPrerequisite.prerequisite_id, Concept.name)
            .join(Concept, ConceptPrerequisite.prerequisite_id == Concept.id)
            .where(ConceptPrerequisite.concept_id == concept_id)
        )
        prereq_res = await session.execute(prereq_stmt)
        prereq_rows = prereq_res.all()

        prereq_infos: list[PrerequisiteInfo] = []
        for pid, pname in prereq_rows:
            p_mst_stmt = select(Mastery).where(
                Mastery.user_id == user_id, Mastery.concept_id == pid
            )
            p_mst_res = await session.execute(p_mst_stmt)
            p_m = p_mst_res.scalars().first()
            p_base = float(p_m.p_mastery) if (p_m and p_m.attempts > 0) else 0.0
            prereq_infos.append(
                PrerequisiteInfo(
                    prerequisite_id=pid,
                    prerequisite_name=pname,
                    base_mastery=p_base,
                )
            )

        status_details = determine_concept_status(
            effective_mastery=p_eff,
            attempts=attempts,
            prerequisites=prereq_infos,
        )
        status = status_details.status
        unmet_prereqs = [u["name"] for u in status_details.unmet_prerequisites]

        # 3. Fetch all attempts for this user and concept
        attempts_stmt = (
            select(Attempt, Session.kind)
            .join(Session, Attempt.session_id == Session.id)
            .where(Attempt.user_id == user_id, Attempt.concept_id == concept_id)
            .order_by(Attempt.created_at.asc())
        )
        attempts_res = await session.execute(attempts_stmt)
        attempt_rows = attempts_res.all()

        # 4. Fetch diagram assessments
        diagram_stmt = (
            select(DiagramAssessment)
            .where(DiagramAssessment.user_id == user_id, DiagramAssessment.concept_id == concept_id)
            .order_by(DiagramAssessment.created_at.asc())
        )
        diagram_res = await session.execute(diagram_stmt)
        diagram_assessments = list(diagram_res.scalars().all())

        # 5. Fetch teachback sessions
        tb_stmt = (
            select(TeachbackSession)
            .where(TeachbackSession.user_id == user_id, TeachbackSession.concept_id == concept_id)
            .order_by(TeachbackSession.id.asc())
        )
        tb_res = await session.execute(tb_stmt)
        tb_sessions = list(tb_res.scalars().all())

        # Breakdown assessment counts
        practice_count = 0
        diagnostic_count = 0
        review_count = 0
        outcomes_chronological: list[bool] = []

        timeline_events: list[TimelineEventOut] = []

        for att, s_kind in attempt_rows:
            outcomes_chronological.append(att.is_correct)
            desc_text = "Practice question"
            ev_type = "practice"
            if s_kind == SessionKindEnum.DIAGNOSTIC:
                diagnostic_count += 1
                ev_type = "diagnostic"
                desc_text = "Adaptive diagnostic assessment"
            elif s_kind == SessionKindEnum.REVIEW:
                review_count += 1
                ev_type = "review"
                desc_text = "Spaced repetition review"
            else:
                practice_count += 1

            timeline_events.append(
                TimelineEventOut(
                    event_type=ev_type,
                    timestamp=att.created_at,
                    description=desc_text,
                    is_correct=att.is_correct,
                    mastery_before=att.mastery_before,
                    mastery_after=att.mastery_after,
                    mastery_delta=round(att.mastery_after - att.mastery_before, 4),
                    metadata={"question_id": att.question_id, "response_ms": att.response_ms},
                )
            )

        # Add diagram assessments to timeline
        diagram_count = len(diagram_assessments)
        for da in diagram_assessments:
            outcomes_chronological.append(da.is_correct)
            timeline_events.append(
                TimelineEventOut(
                    event_type="diagram_lab",
                    timestamp=da.created_at,
                    description=f"Interactive Lab ({da.assessment_type.replace('_', ' ').title()})",
                    is_correct=da.is_correct,
                    mastery_before=da.mastery_before,
                    mastery_after=da.mastery_after,
                    mastery_delta=round(da.mastery_after - da.mastery_before, 4),
                    metadata={"diagram_id": da.diagram_id, "score": da.score},
                )
            )

        # Add teachback sessions to timeline
        teachback_count = len(tb_sessions)
        for tb in tb_sessions:
            if tb.final_score is not None:
                timeline_events.append(
                    TimelineEventOut(
                        event_type="teachback",
                        timestamp=now,
                        description=f"Teach-Back conversation with Pip (Final Level: {tb.final_level or 1})",
                        is_correct=(tb.final_score >= 0.60),
                        mastery_before=p_mastery,
                        mastery_after=p_mastery,
                        mastery_delta=0.0,
                        metadata={"final_score": tb.final_score, "turns": tb.turn_count},
                    )
                )

        # Sort timeline chronologically
        timeline_events.sort(key=lambda ev: ev.timestamp)

        # 6. Fetch misconceptions (active and resolved)
        misc_stmt = (
            select(DetectedMisconception, Misconception)
            .join(Misconception, DetectedMisconception.misconception_id == Misconception.id)
            .where(
                DetectedMisconception.user_id == user_id,
                Misconception.concept_id == concept_id,
            )
            .order_by(desc(DetectedMisconception.created_at))
        )
        misc_res = await session.execute(misc_stmt)
        misc_rows = misc_res.all()

        active_miscs: list[MisconceptionStateOut] = []
        resolved_miscs: list[MisconceptionStateOut] = []
        seen_misc_ids: set[str] = set()

        for dm, m in misc_rows:
            if dm.misconception_id in seen_misc_ids:
                continue
            seen_misc_ids.add(dm.misconception_id)
            item = MisconceptionStateOut(
                id=m.id,
                statement=m.statement,
                correction=m.correction,
                detected_at=dm.created_at,
                resolved_at=dm.resolved_at,
            )
            if dm.resolved_at is None:
                active_miscs.append(item)
            else:
                resolved_miscs.append(item)

        # 8. Compute Evidence Strength & Score
        total_valid_attempts = len(attempt_rows) + diagram_count + teachback_count
        correct_count = sum(1 for x in outcomes_chronological if x)
        accuracy_rate = round(correct_count / total_valid_attempts, 4) if total_valid_attempts > 0 else 0.0

        distinct_modalities = 0
        if practice_count > 0 or review_count > 0:
            distinct_modalities += 1
        if diagnostic_count > 0:
            distinct_modalities += 1
        if teachback_count > 0:
            distinct_modalities += 1
        if diagram_count > 0:
            distinct_modalities += 1

        days_since_seen = None
        if last_seen:
            days_since_seen = max(0.0, (now - last_seen).total_seconds() / 86400.0)

        ev_category, ev_score = calculate_evidence_strength(
            total_attempts=total_valid_attempts,
            distinct_modalities=max(1, distinct_modalities),
            days_since_last_seen=days_since_seen,
        )

        trend = determine_trend(outcomes_chronological)

        active_misc_statements = [m.statement for m in active_miscs]
        narrative = generate_mastery_narrative(
            concept_name=concept.name,
            p_mastery=p_eff,
            evidence_category=ev_category,
            total_attempts=total_valid_attempts,
            correct_attempts=correct_count,
            trend=trend,
            active_misconceptions=active_misc_statements,
            unmet_prerequisites=unmet_prereqs,
            is_overdue=is_overdue,
            days_overdue=days_overdue,
        )

        return ExplainableConceptMasteryResponse(
            concept_id=concept.id,
            concept_name=concept.name,
            chapter=concept.chapter,
            p_mastery=p_mastery,
            p_effective=p_eff,
            status=status,
            evidence_strength=ev_category,
            evidence_score=ev_score,
            total_attempts=total_valid_attempts,
            correct_attempts=correct_count,
            accuracy_rate=accuracy_rate,
            recent_trend=trend,
            last_seen_at=last_seen,
            next_due_at=next_due,
            is_overdue=is_overdue,
            days_overdue=days_overdue,
            assessment_breakdown=AssessmentBreakdownOut(
                practice_count=practice_count + review_count,
                diagnostic_count=diagnostic_count,
                teachback_count=teachback_count,
                diagram_count=diagram_count,
            ),
            active_misconceptions=active_miscs,
            resolved_misconceptions=resolved_miscs,
            unmet_prerequisites=unmet_prereqs,
            narrative=narrative,
            timeline=timeline_events,
        )


explainable_mastery_service = ExplainableMasteryService()
