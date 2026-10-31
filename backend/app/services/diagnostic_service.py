import datetime
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
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

        # Select first question
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
        # 1. Validate response timing
        if req.response_ms < 0 or req.response_ms > 600000:
            raise AppError(
                code="invalid_response_time",
                message="Response time must be between 0 and 600,000 ms.",
                status_code=422,
            )

        # 2. Verify session existence, ownership, and kind
        diag_session = await session.get(Session, session_id)
        if not diag_session:
            raise NotFoundError("Diagnostic session not found.")
        if diag_session.user_id != user_id:
            raise ForbiddenError("Session does not belong to authenticated user.")
        if diag_session.kind != SessionKindEnum.DIAGNOSTIC:
            raise AppError(
                code="invalid_session_kind",
                message="Session is not a diagnostic session.",
                status_code=400,
            )

        # 3. Idempotency check BEFORE checking session active status
        existing_attempt = await question_repo.get_attempt_by_client_id(
            session, req.client_attempt_id
        )
        if existing_attempt:
            if existing_attempt.user_id != user_id:
                raise ForbiddenError("Attempt belongs to another user.")
            if existing_attempt.session_id != session_id:
                raise AppError(
                    code="session_mismatch",
                    message="Client attempt ID belongs to another session.",
                    status_code=409,
                )

            answered_count = await self._count_session_attempts(session, session_id)
            if answered_count >= TOTAL_DIAGNOSTIC_QUESTIONS or diag_session.status == SessionStatusEnum.COMPLETED:
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

        # Session must be active for new submissions
        if diag_session.status != SessionStatusEnum.ACTIVE:
            raise ConflictError("session_closed", "Diagnostic session is already completed.")

        # 4. Load question and concept
        question = await question_repo.get_by_id(session, req.question_id)
        if not question:
            raise NotFoundError(f"Question '{req.question_id}' not found.")
        concept = await concept_repo.get_by_id(session, question.concept_id)
        if not concept:
            raise NotFoundError(f"Concept '{question.concept_id}' not found.")

        # 5. Validate answer key
        valid_keys = [
            opt.get("key") for opt in question.options if isinstance(opt, dict) and "key" in opt
        ]
        if req.selected_key not in valid_keys:
            raise AppError(
                code="invalid_selected_key",
                message=f"Selected key '{req.selected_key}' is not among valid options: {valid_keys}",
                status_code=422,
            )

        # 6. Lock mastery row
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

        # Prerequisite inference: if dependent answered correctly, nudge prerequisites upward
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

        # Count answered in this session
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
        diag_session = await session.get(Session, session_id)
        if not diag_session:
            raise NotFoundError(f"Session '{session_id}' not found.")
        if diag_session.user_id != user_id:
            raise ForbiddenError("Session does not belong to authenticated user.")
        if diag_session.kind != SessionKindEnum.DIAGNOSTIC:
            raise AppError(
                code="invalid_session_kind",
                message="Session is not a diagnostic session.",
                status_code=400,
            )

        concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)

        prereq_map: dict[str, list[str]] = defaultdict(list)
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)

        # Check concepts tested during this session
        session_tested_stmt = select(Attempt.concept_id).where(Attempt.session_id == session_id)
        session_tested = set((await session.execute(session_tested_stmt)).scalars().all())

        results: list[DiagnosticConceptResult] = []
        for c in concepts:
            m = user_masteries.get(c.id)
            has_tested = c.id in session_tested or (m and m.get("attempts", 0) > 0)
            p_val = m["p_mastery"] if m else c.p_l0
            if not has_tested:
                status = "untested"
            elif p_val >= 0.80:
                status = "mastered"
            elif p_val >= 0.45:
                status = "learning"
            else:
                status = "needs_practice"

            results.append(
                DiagnosticConceptResult(
                    concept_id=c.id,
                    concept_name=c.name,
                    p_mastery=p_val,
                    status=status,
                )
            )

        # Identify weakest among TESTED concepts
        tested_results = [r for r in results if r.status != "untested"]
        if not tested_results:
            tested_results = results

        sorted_by_weakness = sorted(tested_results, key=lambda x: x.p_mastery)
        weakest_ids = [r.concept_id for r in sorted_by_weakness[:3]]

        # Ensure recommended_next is an unlocked concept
        def is_concept_unlocked(cid: str) -> bool:
            p_list = prereq_map.get(cid, [])
            if not p_list:
                return True
            return all(user_masteries.get(p, {}).get("p_mastery", 0.3) >= 0.60 for p in p_list)

        recommended = None
        for wid in weakest_ids:
            if is_concept_unlocked(wid):
                recommended = wid
                break

        if not recommended:
            for r in sorted_by_weakness:
                if is_concept_unlocked(r.concept_id):
                    recommended = r.concept_id
                    break

        if not recommended:
            recommended = "lp-nutrition"

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
        asked_concept_stmt = select(Attempt.concept_id).where(Attempt.session_id == session_id)
        asked_concepts = set((await session.execute(asked_concept_stmt)).scalars().all())

        asked_question_stmt = select(Attempt.question_id).where(Attempt.session_id == session_id)
        asked_questions = set((await session.execute(asked_question_stmt)).scalars().all())

        concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)

        prereq_map: dict[str, list[str]] = defaultdict(list)
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)

        # Prerequisite skip constraint: skip dependent concept if prerequisite mastery < 0.30
        candidate_concepts = []
        for c in concepts:
            if c.id in asked_concepts:
                continue
            prereqs_for_c = prereq_map.get(c.id, [])
            # If any prerequisite was tested and has mastery < 0.30, skip testing this dependent
            prereq_failed = any(
                user_masteries.get(p, {}).get("p_mastery", 0.30) < 0.30
                and user_masteries.get(p, {}).get("attempts", 0) > 0
                for p in prereqs_for_c
            )
            if prereq_failed:
                continue
            candidate_concepts.append(c)

        if not candidate_concepts:
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
