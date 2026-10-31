import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.domain.bkt import bkt_update
from app.domain.sm2 import calculate_sm2_update
from app.models.entities import (
    Attempt,
    Concept,
    Mastery,
    Question,
    Session,
    SessionKindEnum,
    SessionStatusEnum,
)
from app.repositories.concept_repo import concept_repo
from app.repositories.question_repo import question_repo
from app.schemas.diagnostic import (
    DiagnosticAnswerRequest,
    DiagnosticAnswerResponse,
    DiagnosticConceptResult,
    DiagnosticProgress,
    DiagnosticResultResponse,
    DiagnosticStartResponse,
)
from app.schemas.practice import QuestionOptionOut, QuestionOut

TOTAL_DIAGNOSTIC_QUESTIONS = 15


def to_question_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=q.id,
        concept_id=q.concept_id,
        stem=q.stem,
        options=[QuestionOptionOut(key=opt["key"], text=opt["text"]) for opt in q.options],
        difficulty_bucket=q.difficulty_bucket,
    )


class DiagnosticService:
    async def start_session(self, session: AsyncSession, user_id: int) -> DiagnosticStartResponse:
        # Create fresh diagnostic session
        diag_session = Session(
            user_id=user_id,
            kind=SessionKindEnum.DIAGNOSTIC,
            status=SessionStatusEnum.ACTIVE,
        )
        session.add(diag_session)
        await session.commit()

        # Select first question (foundation with uncertainty closest to 0.5)
        q = await self._select_next_diagnostic_question(session, user_id, diag_session.id)
        if not q:
            raise NotFoundError("No diagnostic questions available.")

        return DiagnosticStartResponse(
            session_id=diag_session.id,
            question=to_question_out(q),
            progress=DiagnosticProgress(answered=0, total=TOTAL_DIAGNOSTIC_QUESTIONS),
        )

    async def submit_answer(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: int,
        req: DiagnosticAnswerRequest,
    ) -> DiagnosticAnswerResponse:
        # 1. Verify session
        diag_session = await session.get(Session, session_id)
        if not diag_session or diag_session.user_id != user_id:
            raise NotFoundError("Diagnostic session not found.")
        if diag_session.status != SessionStatusEnum.ACTIVE:
            raise ConflictError("session_closed", "Diagnostic session is already completed.")

        # 2. Idempotency check
        existing_attempt = await question_repo.get_attempt_by_client_id(
            session, req.client_attempt_id
        )
        if existing_attempt:
            # Re-read progress
            answered_count = await self._count_session_attempts(session, session_id)
            if answered_count >= TOTAL_DIAGNOSTIC_QUESTIONS:
                result = await self.get_session_result(session, session_id, user_id)
                return DiagnosticAnswerResponse(
                    is_correct=existing_attempt.is_correct,
                    next_question=None,
                    progress=DiagnosticProgress(
                        answered=TOTAL_DIAGNOSTIC_QUESTIONS, total=TOTAL_DIAGNOSTIC_QUESTIONS
                    ),
                    result=result,
                )
            next_q = await self._select_next_diagnostic_question(session, user_id, session_id)
            return DiagnosticAnswerResponse(
                is_correct=existing_attempt.is_correct,
                next_question=to_question_out(next_q) if next_q else None,
                progress=DiagnosticProgress(
                    answered=answered_count, total=TOTAL_DIAGNOSTIC_QUESTIONS
                ),
                result=None,
            )

        # 3. Load question and concept
        question = await question_repo.get_by_id(session, req.question_id)
        if not question:
            raise NotFoundError(f"Question '{req.question_id}' not found")
        concept = await concept_repo.get_by_id(session, question.concept_id)
        if not concept:
            raise NotFoundError(f"Concept '{question.concept_id}' not found")

        # 4. Lock mastery row
        mastery_stmt = (
            select(Mastery)
            .where(Mastery.user_id == user_id, Mastery.concept_id == question.concept_id)
            .with_for_update()
        )
        mastery = (await session.execute(mastery_stmt)).scalars().first()

        now = datetime.datetime.now(datetime.UTC)
        p_prior = mastery.p_mastery if mastery else concept.p_l0
        is_correct = req.selected_key.strip().upper() == question.correct_key.strip().upper()

        # BKT Update
        _, p_next = bkt_update(
            p_prior=p_prior,
            is_correct=is_correct,
            base_slip=concept.p_s,
            learn_rate=concept.p_t,
            num_options=len(question.options),
            difficulty_bucket=question.difficulty_bucket,
        )

        # SM-2 update
        new_ef, new_int, new_reps, next_due = calculate_sm2_update(
            current_ease=mastery.ease if mastery else 2.5,
            current_interval_days=mastery.interval_days if mastery else 0,
            current_repetitions=mastery.repetitions if mastery else 0,
            is_correct=is_correct,
            response_ms=req.response_ms,
            now=now,
        )

        if not mastery:
            mastery = Mastery(
                user_id=user_id,
                concept_id=question.concept_id,
                p_mastery=p_next,
                attempts=1,
                correct=1 if is_correct else 0,
                last_seen_at=now,
                ease=new_ef,
                interval_days=new_int,
                repetitions=new_reps,
                next_due_at=next_due,
                version=1,
            )
            session.add(mastery)
        else:
            mastery.p_mastery = p_next
            mastery.attempts += 1
            if is_correct:
                mastery.correct += 1
            mastery.last_seen_at = now
            mastery.ease = new_ef
            mastery.interval_days = new_int
            mastery.repetitions = new_reps
            mastery.next_due_at = next_due
            mastery.version += 1

        # Prerequisite inference: if dependent answered correctly, nudge prerequisites upward (0.3 weight)
        if is_correct:
            prereqs = await concept_repo.get_prerequisites_for_concept(session, concept.id)
            for p_id in prereqs:
                p_mast = (
                    (
                        await session.execute(
                            select(Mastery).where(
                                Mastery.user_id == user_id, Mastery.concept_id == p_id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
                if p_mast and p_mast.p_mastery < 0.8:
                    p_mast.p_mastery = min(0.85, round(p_mast.p_mastery + 0.10, 4))

        # Record attempt
        attempt = Attempt(
            client_attempt_id=req.client_attempt_id,
            session_id=session_id,
            user_id=user_id,
            question_id=question.id,
            concept_id=question.concept_id,
            selected_key=req.selected_key,
            is_correct=is_correct,
            reasoning_text=req.reasoning,
            response_ms=req.response_ms,
            mastery_before=p_prior,
            mastery_after=p_next,
            created_at=now,
        )
        session.add(attempt)
        await session.commit()

        # Count answered
        answered_count = await self._count_session_attempts(session, session_id)

        if answered_count >= TOTAL_DIAGNOSTIC_QUESTIONS:
            diag_session.status = SessionStatusEnum.COMPLETED
            diag_session.ended_at = now
            await session.commit()
            result = await self.get_session_result(session, session_id, user_id)
            return DiagnosticAnswerResponse(
                is_correct=is_correct,
                next_question=None,
                progress=DiagnosticProgress(
                    answered=answered_count, total=TOTAL_DIAGNOSTIC_QUESTIONS
                ),
                result=result,
            )

        # Select next question
        next_q = await self._select_next_diagnostic_question(session, user_id, session_id)
        return DiagnosticAnswerResponse(
            is_correct=is_correct,
            next_question=to_question_out(next_q) if next_q else None,
            progress=DiagnosticProgress(answered=answered_count, total=TOTAL_DIAGNOSTIC_QUESTIONS),
            result=None,
        )

    async def get_session_result(
        self, session: AsyncSession, session_id: int, user_id: int
    ) -> DiagnosticResultResponse:
        concepts = await concept_repo.list_all(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)

        results: list[DiagnosticConceptResult] = []
        for c in concepts:
            m = user_masteries.get(c.id)
            p_val = m["p_mastery"] if m else c.p_l0
            status = "mastered" if p_val >= 0.8 else "learning" if p_val > 0.4 else "unlocked"
            results.append(
                DiagnosticConceptResult(
                    concept_id=c.id,
                    concept_name=c.name,
                    p_mastery=p_val,
                    status=status,
                )
            )

        # Identify weakest concepts
        sorted_by_weakness = sorted(results, key=lambda x: x.p_mastery)
        weakest_ids = [r.concept_id for r in sorted_by_weakness[:3]]
        recommended = weakest_ids[0] if weakest_ids else "lp-nutrition"

        return DiagnosticResultResponse(
            mastery=results,
            weakest=weakest_ids,
            recommended_next=recommended,
        )

    async def _count_session_attempts(self, session: AsyncSession, session_id: int) -> int:
        stmt = select(func.count(Attempt.id)).where(Attempt.session_id == session_id)
        return int((await session.execute(stmt)).scalar() or 0)

    async def _select_next_diagnostic_question(
        self, session: AsyncSession, user_id: int, session_id: int
    ) -> Question | None:
        # Uncertainty sampling: pick concept with mastery closest to 0.50
        # Skip concepts already asked in this session
        asked_concept_stmt = select(Attempt.concept_id).where(Attempt.session_id == session_id)
        asked_concepts = set((await session.execute(asked_concept_stmt)).scalars().all())

        asked_question_stmt = select(Attempt.question_id).where(Attempt.session_id == session_id)
        asked_questions = set((await session.execute(asked_question_stmt)).scalars().all())

        concepts = await concept_repo.list_all(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)

        candidate_concepts = [c for c in concepts if c.id not in asked_concepts]
        if not candidate_concepts:
            candidate_concepts = concepts

        # Pick candidate minimizing |p_mastery - 0.50|
        def uncertainty_score(c: Concept) -> float:
            m = user_masteries.get(c.id)
            p = float(m["p_mastery"]) if m else float(c.p_l0)
            return float(abs(p - 0.50))

        best_concept = min(candidate_concepts, key=uncertainty_score)

        # Pick unasked question from that concept
        concept_questions = await question_repo.list_by_concept(session, best_concept.id)
        unasked_concept_q = [q for q in concept_questions if q.id not in asked_questions]
        if unasked_concept_q:
            return unasked_concept_q[0]

        # Fallback to any unasked verified question
        all_q = await question_repo.list_all_verified(session)
        unasked_all = [q for q in all_q if q.id not in asked_questions]
        return unasked_all[0] if unasked_all else (all_q[0] if all_q else None)


diagnostic_service = DiagnosticService()
