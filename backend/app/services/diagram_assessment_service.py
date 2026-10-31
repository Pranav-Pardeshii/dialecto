import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.domain.bkt import bkt_update, soft_evidence_update
from app.domain.sm2 import calculate_sm2_update
from app.models.entities import (
    DetectedMisconception,
    DiagramAssessment,
    DiagramAssessmentTypeEnum,
    Mastery,
    MisconceptionSourceEnum,
    Session,
    SessionKindEnum,
    SessionStatusEnum,
)
from app.schemas.diagram import DiagramAssessmentResponse, DiagramAssessmentSubmitRequest
from app.services.diagram_command_service import diagram_command_service


class DiagramAssessmentService:
    async def evaluate_and_persist(
        self, session: AsyncSession, user_id: int, req: DiagramAssessmentSubmitRequest
    ) -> DiagramAssessmentResponse:
        # 1. Idempotency Check
        dup_stmt = select(DiagramAssessment).where(
            DiagramAssessment.client_attempt_id == req.client_attempt_id
        )
        dup_res = await session.execute(dup_stmt)
        existing = dup_res.scalars().first()
        if existing:
            return DiagramAssessmentResponse(
                is_correct=existing.is_correct,
                score=existing.score,
                feedback=existing.feedback,
                target_structure_id=existing.target_structure_id,
                target_sequence=None,
                mastery={
                    "concept_id": existing.concept_id,
                    "before": existing.mastery_before,
                    "after": existing.mastery_after,
                },
                detected_misconception={"id": existing.detected_misconception_id} if existing.detected_misconception_id else None,
                is_idempotent_replay=True,
            )

        # 2. Get Diagram Manifest and Question
        manifest = diagram_command_service.get_manifest(req.diagram_id)
        if not manifest:
            raise NotFoundError(f"Diagram '{req.diagram_id}' not found in manifest.")

        concept_id = manifest["concept_id"]
        questions = manifest.get("assessments", [])
        q_item = next((q for q in questions if q["id"] == req.question_id), None)
        if not q_item:
            raise NotFoundError(f"Assessment question '{req.question_id}' not found in diagram '{req.diagram_id}'.")

        # 3. Evaluate response based on assessment type
        is_correct = False
        score = 0.0
        feedback = ""
        target_struct = q_item.get("target_structure_id")
        target_seq = q_item.get("target_sequence")
        detected_misc_id: str | None = None
        user_response_str = ""

        if req.assessment_type == "identification":
            user_response_str = req.selected_structure_id or ""
            # Check structure match or alias
            if target_struct and req.selected_structure_id:
                if req.selected_structure_id.lower().strip() == target_struct.lower().strip():
                    is_correct = True
                    score = 1.0
                    feedback = f"Correct! You identified {target_struct.replace('_', ' ').title()}."
                else:
                    is_correct = False
                    score = 0.0
                    feedback = f"Incorrect. That was not the target structure. Review the hint: {q_item.get('hint', '')}"
                    # Check if selected structure is related to a misconception
                    for s in manifest.get("structures", []):
                        if s["id"] == req.selected_structure_id and s.get("related_misconception_id"):
                            detected_misc_id = s["related_misconception_id"]

        elif req.assessment_type == "sequence":
            user_response_str = " -> ".join(req.selected_sequence or [])
            if target_seq and req.selected_sequence:
                if req.selected_sequence == target_seq:
                    is_correct = True
                    score = 1.0
                    feedback = "Perfect sequence! Blood/filtrate flow follows the exact physiological order."
                else:
                    # Partial credit: count matching pairs in sequence
                    matches = sum(
                        1
                        for i in range(min(len(req.selected_sequence), len(target_seq)))
                        if req.selected_sequence[i] == target_seq[i]
                    )
                    score = round(matches / max(1, len(target_seq)), 2)
                    is_correct = score >= 0.75
                    feedback = f"Partial sequence match ({round(score * 100)}%). Review the physiological pathway."

        elif req.assessment_type == "explanation":
            user_response_str = req.explanation_text or ""
            # Score against rubric points
            rubric_points = q_item.get("rubric_points", [])
            lower_text = user_response_str.lower()
            matched_points = 0
            for pt in rubric_points:
                keywords = [w.lower() for w in pt.split() if len(w) > 4]
                if any(kw in lower_text for kw in keywords):
                    matched_points += 1
            if rubric_points:
                score = round(matched_points / len(rubric_points), 2)
                is_correct = score >= 0.50
                feedback = (
                    f"Good scientific reasoning ({matched_points}/{len(rubric_points)} key points covered)."
                    if is_correct
                    else "Explanation missing critical physiological concepts."
                )
            else:
                is_correct = len(user_response_str) > 30
                score = 0.8 if is_correct else 0.2
                feedback = "Explanation received and logged."

        # 4. Get or Create Session
        active_session_id = req.session_id
        if not active_session_id:
            # Create a diagram lab session
            new_session = Session(
                user_id=user_id,
                kind=SessionKindEnum.DIAGRAM_LAB,
                status=SessionStatusEnum.ACTIVE,
            )
            session.add(new_session)
            await session.flush()
            active_session_id = new_session.id

        # 5. Lock Mastery Row (Atomic Learner Model Update)
        mastery_stmt = (
            select(Mastery)
            .where(Mastery.user_id == user_id, Mastery.concept_id == concept_id)
            .with_for_update()
        )
        mastery_res = await session.execute(mastery_stmt)
        mastery = mastery_res.scalars().first()

        now = datetime.datetime.now(datetime.UTC)
        if not mastery:
            mastery = Mastery(
                user_id=user_id,
                concept_id=concept_id,
                p_mastery=0.30,
                attempts=0,
                correct=0,
                last_seen_at=now,
                ease=2.5,
                interval_days=0,
                repetitions=0,
                next_due_at=None,
            )
            session.add(mastery)
            await session.flush()

        mastery_before = mastery.p_mastery

        # 6. Apply Bayesian Knowledge Tracing Update
        if req.assessment_type == "explanation":
            # Soft-evidence update
            p_after = soft_evidence_update(
                p_prior=mastery_before,
                is_positive=is_correct,
                confidence=score,
            )
        else:
            _, p_after = bkt_update(
                p_prior=mastery_before,
                is_correct=is_correct,
                base_slip=0.10,
                learn_rate=0.15,
                difficulty_bucket=2,
            )

        mastery.p_mastery = p_after
        mastery.attempts += 1
        if is_correct:
            mastery.correct += 1
        mastery.last_seen_at = now

        # Update SM-2 schedule
        new_ease, new_interval, new_reps, next_due = calculate_sm2_update(
            current_ease=mastery.ease,
            current_interval_days=mastery.interval_days,
            current_repetitions=mastery.repetitions,
            is_correct=is_correct,
            response_ms=10000,
            now=now,
        )
        mastery.ease = new_ease
        mastery.interval_days = new_interval
        mastery.repetitions = new_reps
        mastery.next_due_at = next_due

        # 7. Record Misconception if triggered
        if detected_misc_id and not is_correct:
            dm = DetectedMisconception(
                user_id=user_id,
                misconception_id=detected_misc_id,
                source=MisconceptionSourceEnum.DIAGRAM_LAB,
                confidence=0.85,
            )
            session.add(dm)

        # 8. Insert Diagram Assessment Record
        as_type_enum = DiagramAssessmentTypeEnum.IDENTIFICATION
        try:
            as_type_enum = DiagramAssessmentTypeEnum(req.assessment_type)
        except ValueError:
            pass

        assessment_record = DiagramAssessment(
            client_attempt_id=req.client_attempt_id,
            session_id=active_session_id,
            user_id=user_id,
            concept_id=concept_id,
            diagram_id=req.diagram_id,
            assessment_type=as_type_enum,
            target_structure_id=req.selected_structure_id or target_struct,
            user_response=user_response_str,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            detected_misconception_id=detected_misc_id,
            mastery_before=mastery_before,
            mastery_after=p_after,
        )
        session.add(assessment_record)

        await session.commit()

        return DiagramAssessmentResponse(
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            target_structure_id=target_struct,
            target_sequence=target_seq,
            mastery={
                "concept_id": concept_id,
                "before": round(mastery_before, 4),
                "after": round(p_after, 4),
            },
            detected_misconception={"id": detected_misc_id} if detected_misc_id else None,
            is_idempotent_replay=False,
        )


diagram_assessment_service = DiagramAssessmentService()
