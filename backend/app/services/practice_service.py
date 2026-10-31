import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.misconception_classifier import classify_misconception
from app.core.errors import NotFoundError
from app.domain.bkt import bkt_update
from app.domain.elo import calibrate_item_difficulty
from app.domain.selector import select_next_practice_question
from app.domain.sm2 import calculate_sm2_update, compute_effective_mastery
from app.models.entities import (
    Attempt,
    DetectedMisconception,
    Mastery,
    Misconception,
    MisconceptionSourceEnum,
    Question,
    Session,
    SessionKindEnum,
    SessionStatusEnum,
)
from app.repositories.concept_repo import concept_repo
from app.repositories.question_repo import question_repo
from app.schemas.practice import (
    AIFallbackMeta,
    MasteryDelta,
    MisconceptionFeedback,
    PracticeAnswerRequest,
    PracticeAnswerResponse,
    PracticeNextRequest,
    PracticeNextResponse,
    QuestionOptionOut,
    QuestionOut,
)

logger = structlog.get_logger(__name__)


def to_question_out(q: Question) -> QuestionOut:
    cleaned_options = [QuestionOptionOut(key=opt["key"], text=opt["text"]) for opt in q.options]
    return QuestionOut(
        id=q.id,
        concept_id=q.concept_id,
        stem=q.stem,
        options=cleaned_options,
        difficulty_bucket=q.difficulty_bucket,
    )


class PracticeService:
    async def get_or_create_practice_session(self, session: AsyncSession, user_id: int) -> Session:
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.kind == SessionKindEnum.PRACTICE,
            Session.status == SessionStatusEnum.ACTIVE,
        )
        res = await session.execute(stmt)
        s = res.scalars().first()
        if not s:
            s = Session(
                user_id=user_id,
                kind=SessionKindEnum.PRACTICE,
                status=SessionStatusEnum.ACTIVE,
            )
            session.add(s)
            await session.commit()
        return s

    async def get_next_question(
        self, session: AsyncSession, user_id: int, req: PracticeNextRequest
    ) -> PracticeNextResponse:
        practice_session = await self.get_or_create_practice_session(session, user_id)
        concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)
        seen_questions = await question_repo.get_seen_question_ids(session, user_id)

        # Build prereq map
        prereq_map: dict[str, list[str]] = {}
        for c in concepts:
            prereq_map[c.id] = []
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)

        now = datetime.datetime.now(datetime.UTC)

        # Active misconceptions for student
        active_misc_stmt = select(DetectedMisconception.misconception_id).where(
            DetectedMisconception.user_id == user_id,
            DetectedMisconception.resolved_at.is_(None),
        )
        active_miscs = set((await session.execute(active_misc_stmt)).scalars().all())

        # Unlocked concepts pool
        unlocked_pool: list[dict[str, Any]] = []
        for c in concepts:
            if req.mode == "concept" and req.concept_id and c.id != req.concept_id:
                continue

            m = user_masteries.get(c.id)
            p_mast = m["p_mastery"] if m else c.p_l0
            next_due = m["next_due_at"] if m else None
            p_eff = compute_effective_mastery(p_mast, next_due, now=now)

            # Check prerequisites
            prereq_effs = [
                compute_effective_mastery(
                    user_masteries[p]["p_mastery"] if p in user_masteries else 0.3,
                    user_masteries[p]["next_due_at"] if p in user_masteries else None,
                    now=now,
                )
                for p in prereq_map[c.id]
            ]
            is_locked = any(pe < 0.60 for pe in prereq_effs)
            if is_locked and req.mode != "concept":
                continue

            is_overdue = next_due is not None and now > next_due
            has_active_misc = any(
                m_id.startswith(f"m-{c.id}") or m_id in active_miscs for m_id in active_miscs
            )

            unlocked_pool.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "p_effective": p_eff,
                    "is_overdue": is_overdue,
                    "has_active_misconception": has_active_misc,
                }
            )

        # Load questions for unlocked concepts
        all_questions = await question_repo.list_all_verified(session)
        questions_by_concept: dict[str, list[dict[str, Any]]] = {}
        for q in all_questions:
            questions_by_concept.setdefault(q.concept_id, []).append(
                {
                    "id": q.id,
                    "concept_id": q.concept_id,
                    "stem": q.stem,
                    "options": q.options,
                    "difficulty_bucket": q.difficulty_bucket,
                    "difficulty_rating": q.difficulty_rating,
                    "obj": q,
                }
            )

        chosen = select_next_practice_question(unlocked_pool, questions_by_concept, seen_questions)
        if not chosen:
            # Fallback to any verified question
            if all_questions:
                fallback_q = all_questions[0]
                return PracticeNextResponse(
                    session_id=practice_session.id,
                    question=to_question_out(fallback_q),
                    selection_reason="Exploring foundational concept questions.",
                )
            raise NotFoundError("No verified practice questions available.")

        chosen_concept_id, q_dict, reason = chosen
        return PracticeNextResponse(
            session_id=practice_session.id,
            question=to_question_out(q_dict["obj"]),
            selection_reason=reason,
        )

    async def submit_answer(
        self, session: AsyncSession, user_id: int, req: PracticeAnswerRequest
    ) -> PracticeAnswerResponse:
        # 1. Idempotency check
        existing_attempt = await question_repo.get_attempt_by_client_id(
            session, req.client_attempt_id
        )
        if existing_attempt:
            # Return stored result
            q = await question_repo.get_by_id(session, existing_attempt.question_id)
            if not q:
                raise NotFoundError("Question not found for stored attempt")

            m_stmt = select(Mastery).where(
                Mastery.user_id == user_id, Mastery.concept_id == existing_attempt.concept_id
            )
            mastery_row = (await session.execute(m_stmt)).scalars().first()

            return PracticeAnswerResponse(
                is_correct=existing_attempt.is_correct,
                correct_key=q.correct_key,
                explanation=q.explanation,
                mastery=MasteryDelta(
                    concept_id=existing_attempt.concept_id,
                    before=existing_attempt.mastery_before,
                    after=existing_attempt.mastery_after,
                    status="learning" if existing_attempt.mastery_after < 0.8 else "mastered",
                ),
                next_due_at=mastery_row.next_due_at if mastery_row else None,
                misconception=None,
                ai=AIFallbackMeta(used=False),
                newly_unlocked=[],
            )

        # 2. Load question and concept
        question = await question_repo.get_by_id(session, req.question_id)
        if not question:
            raise NotFoundError(f"Question '{req.question_id}' not found")

        concept = await concept_repo.get_by_id(session, question.concept_id)
        if not concept:
            raise NotFoundError(f"Concept '{question.concept_id}' not found")

        # Evaluate correctness
        is_correct = req.selected_key.strip().upper() == question.correct_key.strip().upper()

        # Check for distractor-based misconception
        chosen_opt = next(
            (opt for opt in question.options if opt.get("key") == req.selected_key), None
        )
        distractor_misc_id = chosen_opt.get("misconception_id") if chosen_opt else None

        # Misconception diagnosis via LLM Router if student provided reasoning and was wrong
        # Rule: Call LLM before opening row lock transaction
        classification_result = None
        ai_meta = AIFallbackMeta(used=False, model=None, fallback=False)

        if not is_correct and req.reasoning and len(req.reasoning.strip()) >= 5:
            # Load known misconceptions for this concept
            misc_stmt = select(Misconception).where(Misconception.concept_id == concept.id)
            concept_miscs = (await session.execute(misc_stmt)).scalars().all()
            misc_dicts = [
                {"id": m.id, "statement": m.statement, "correction": m.correction}
                for m in concept_miscs
            ]

            try:
                classification_result, ai_meta = await classify_misconception(
                    stem=question.stem,
                    options=question.options,
                    selected_key=req.selected_key,
                    correct_key=question.correct_key,
                    student_reasoning=req.reasoning,
                    possible_misconceptions=misc_dicts,
                    deterministic_misconception_id=distractor_misc_id,
                )
            except Exception as exc:
                logger.warning("misconception_classification_error", error=str(exc))

        # 3. Lock mastery row with FOR UPDATE and persist learner updates
        mastery_stmt = (
            select(Mastery)
            .where(Mastery.user_id == user_id, Mastery.concept_id == question.concept_id)
            .with_for_update()
        )
        mastery = (await session.execute(mastery_stmt)).scalars().first()

        now = datetime.datetime.now(datetime.UTC)
        p_prior = mastery.p_mastery if mastery else concept.p_l0
        ease = mastery.ease if mastery else 2.5
        interval = mastery.interval_days if mastery else 0
        reps = mastery.repetitions if mastery else 0
        attempts_count = mastery.attempts if mastery else 0
        correct_count = mastery.correct if mastery else 0

        # BKT Update
        _, p_next = bkt_update(
            p_prior=p_prior,
            is_correct=is_correct,
            base_slip=concept.p_s,
            learn_rate=concept.p_t,
            num_options=len(question.options),
            difficulty_bucket=question.difficulty_bucket,
        )

        # Elo difficulty calibration on question
        question.difficulty_rating = calibrate_item_difficulty(
            current_difficulty=question.difficulty_rating,
            student_mastery=p_prior,
            is_correct=is_correct,
            n_attempts=question.n_attempts,
        )
        question.n_attempts += 1

        # SM-2 Spaced Repetition update
        new_ease, new_interval, new_reps, next_due = calculate_sm2_update(
            current_ease=ease,
            current_interval_days=interval,
            current_repetitions=reps,
            is_correct=is_correct,
            response_ms=req.response_ms,
            now=now,
        )

        # Update or create Mastery
        if not mastery:
            mastery = Mastery(
                user_id=user_id,
                concept_id=question.concept_id,
                p_mastery=p_next,
                attempts=1,
                correct=1 if is_correct else 0,
                last_seen_at=now,
                ease=new_ease,
                interval_days=new_interval,
                repetitions=new_reps,
                next_due_at=next_due,
                version=1,
            )
            session.add(mastery)
        else:
            mastery.p_mastery = p_next
            mastery.attempts = attempts_count + 1
            mastery.correct = correct_count + (1 if is_correct else 0)
            mastery.last_seen_at = now
            mastery.ease = new_ease
            mastery.interval_days = new_interval
            mastery.repetitions = new_reps
            mastery.next_due_at = next_due
            mastery.version += 1

        # Record attempt
        attempt = Attempt(
            client_attempt_id=req.client_attempt_id,
            session_id=req.session_id,
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
        await session.flush()

        # Misconception resolution / recording
        misconception_feedback: MisconceptionFeedback | None = None
        if not is_correct:
            active_misc_id = None
            misc_source = MisconceptionSourceEnum.DISTRACTOR
            confidence = 1.0

            if classification_result and classification_result.misconception_detected:
                active_misc_id = classification_result.misconception_id or distractor_misc_id
                misc_source = MisconceptionSourceEnum.LLM_REASONING
                confidence = classification_result.confidence
            elif distractor_misc_id:
                active_misc_id = distractor_misc_id
                misc_source = MisconceptionSourceEnum.DISTRACTOR
                confidence = 1.0

            if active_misc_id:
                misc_stmt = select(Misconception).where(Misconception.id == active_misc_id)
                misc_obj = (await session.execute(misc_stmt)).scalars().first()
                if misc_obj:
                    detected = DetectedMisconception(
                        user_id=user_id,
                        misconception_id=active_misc_id,
                        attempt_id=attempt.id,
                        source=misc_source,
                        confidence=confidence,
                        created_at=now,
                    )
                    session.add(detected)
                    misconception_feedback = MisconceptionFeedback(
                        id=misc_obj.id,
                        statement=misc_obj.statement,
                        correction=(
                            classification_result.remedial_nudge
                            if classification_result and classification_result.remedial_nudge
                            else misc_obj.correction
                        ),
                        source="reasoning"
                        if misc_source == MisconceptionSourceEnum.LLM_REASONING
                        else "distractor",
                        confidence=confidence,
                    )
            elif classification_result and classification_result.student_gap_summary:
                # Custom detected misconception from reasoning
                misconception_feedback = MisconceptionFeedback(
                    id="reasoning-gap",
                    statement=classification_result.student_gap_summary,
                    correction=classification_result.remedial_nudge,
                    source="reasoning",
                    confidence=classification_result.confidence,
                )

        # Status & unlocks
        status = "mastered" if p_next >= 0.80 else "learning"

        await session.commit()

        return PracticeAnswerResponse(
            is_correct=is_correct,
            correct_key=question.correct_key,
            explanation=question.explanation,
            mastery=MasteryDelta(
                concept_id=question.concept_id,
                before=p_prior,
                after=p_next,
                status=status,
            ),
            next_due_at=next_due,
            misconception=misconception_feedback,
            ai=ai_meta,
            newly_unlocked=[],
        )


practice_service = PracticeService()
