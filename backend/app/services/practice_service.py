import datetime
from collections import defaultdict
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.misconception_classifier import classify_misconception
from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.domain.bkt import bkt_update
from app.domain.elo import calibrate_item_difficulty
from app.domain.selector import select_next_practice_question
from app.domain.sm2 import calculate_sm2_update, compute_effective_mastery
from app.models.entities import (
    Attempt,
    Concept,
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
        concepts_by_id = {c.id: c for c in concepts}
        prereqs = await concept_repo.list_all_prerequisites(session)
        user_masteries = await concept_repo.get_user_masteries(session, user_id)
        seen_questions = await question_repo.get_seen_question_ids(session, user_id)

        # Build prereq map
        prereq_map: dict[str, list[str]] = defaultdict(list)
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)

        now = datetime.datetime.now(datetime.UTC)

        # Active misconceptions for student
        active_misc_stmt = select(DetectedMisconception.misconception_id).where(
            DetectedMisconception.user_id == user_id,
            DetectedMisconception.resolved_at.is_(None),
        )
        active_miscs = set((await session.execute(active_misc_stmt)).scalars().all())

        # Map misconceptions to their concept_id
        all_miscs_stmt = select(Misconception)
        all_miscs = (await session.execute(all_miscs_stmt)).scalars().all()
        misc_by_concept: dict[str, list[str]] = defaultdict(list)
        for m in all_miscs:
            misc_by_concept[m.concept_id].append(m.id)

        # Load all verified questions grouped by concept
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

        # Helper to check if concept is locked
        def check_lock(concept_id: str) -> str | None:
            # If student has already practiced this concept, it is unlocked
            if concept_id in user_masteries and user_masteries[concept_id].get("attempts", 0) > 0:
                return None
            unmet = []
            for p_id in prereq_map.get(concept_id, []):
                p_m = user_masteries.get(p_id, {})
                p_attempts = p_m.get("attempts", 0)
                p_base = float(p_m.get("p_mastery", 0.0)) if p_attempts > 0 else 0.0
                if p_base < 0.60:
                    p_name = concepts_by_id[p_id].name if p_id in concepts_by_id else p_id
                    unmet.append((p_name, int(round(p_base * 100))))
            if unmet:
                p_name, curr_pct = unmet[0]
                c_name = concepts_by_id[concept_id].name if concept_id in concepts_by_id else concept_id
                return f"Concept '{c_name}' is locked. {p_name} requires 60% prerequisite mastery (current: {curr_pct}%)."
            return None

        # Specific concept mode validation
        if req.mode == "concept":
            if not req.concept_id or req.concept_id not in concepts_by_id:
                raise NotFoundError(f"Concept '{req.concept_id}' not found.")
            lock_err = check_lock(req.concept_id)
            if lock_err:
                raise ForbiddenError(lock_err)

            c_questions = questions_by_concept.get(req.concept_id, [])
            if not c_questions:
                raise NotFoundError(f"No questions available for concept '{req.concept_id}'.")

            unseen = [q for q in c_questions if q["id"] not in seen_questions]
            pool = unseen if unseen else c_questions
            m_data = user_masteries.get(req.concept_id)
            c_obj = concepts_by_id[req.concept_id]
            p_eff = compute_effective_mastery(
                m_data["p_mastery"] if m_data else c_obj.p_l0,
                m_data["next_due_at"] if m_data else None,
                now=now,
            )
            best_q = min(
                pool,
                key=lambda q: abs(q.get("difficulty_rating", 0.0) - (p_eff * 2.0 - 1.0)),
            )
            return PracticeNextResponse(
                session_id=practice_session.id,
                question=to_question_out(best_q["obj"]),
                selection_reason=f"Practicing {c_obj.name}.",
            )

        # Unlocked concepts pool for adaptive and review modes
        unlocked_pool: list[dict[str, Any]] = []
        for c in concepts:
            if check_lock(c.id):
                continue

            m_data = user_masteries.get(c.id)
            p_mast = m_data["p_mastery"] if m_data else c.p_l0
            next_due = m_data["next_due_at"] if m_data else None
            p_eff = compute_effective_mastery(p_mast, next_due, now=now)

            is_overdue = next_due is not None and now > next_due
            # Active misconception check strictly scoped to this concept
            has_active_misc = any(m_id in active_miscs for m_id in misc_by_concept.get(c.id, []))

            unlocked_pool.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "p_effective": p_eff,
                    "is_overdue": is_overdue,
                    "has_active_misconception": has_active_misc,
                }
            )

        if not unlocked_pool:
            raise NotFoundError("No unlocked concepts available for practice.")

        # Review mode: filter to overdue or decaying concepts
        if req.mode == "review":
            review_pool = [c for c in unlocked_pool if c["is_overdue"] or c["p_effective"] < 0.75]
            target_pool = review_pool if review_pool else unlocked_pool
            chosen = select_next_practice_question(target_pool, questions_by_concept, seen_questions)
        else:
            chosen = select_next_practice_question(unlocked_pool, questions_by_concept, seen_questions)

        if not chosen:
            # Fallback to any unlocked question
            for c_info in unlocked_pool:
                cand = questions_by_concept.get(c_info["id"], [])
                if cand:
                    return PracticeNextResponse(
                        session_id=practice_session.id,
                        question=to_question_out(cand[0]["obj"]),
                        selection_reason=f"Reinforcing {c_info['name']}.",
                    )
            raise NotFoundError("No verified practice questions available.")

        chosen_concept_id, q_dict, reason = chosen
        return PracticeNextResponse(
            session_id=practice_session.id,
            question=to_question_out(q_dict["obj"]),
            selection_reason=reason,
        )

    def _get_unlocked_concept_ids(
        self,
        concepts: list[Concept],
        prereq_map: dict[str, list[str]],
        mastery_map: dict[str, dict[str, Any]],
    ) -> set[str]:
        unlocked = set()
        for c in concepts:
            if c.id in mastery_map and mastery_map[c.id].get("attempts", 0) > 0:
                unlocked.add(c.id)
                continue
            prereqs = prereq_map.get(c.id, [])
            if not prereqs:
                unlocked.add(c.id)
            elif all(
                (
                    mastery_map.get(p, {}).get("attempts", 0) > 0
                    and mastery_map.get(p, {}).get("p_mastery", 0.0) >= 0.60
                )
                for p in prereqs
            ):
                unlocked.add(c.id)
        return unlocked

    async def submit_answer(
        self, session: AsyncSession, user_id: int, req: PracticeAnswerRequest
    ) -> PracticeAnswerResponse:
        # Validate response timing
        if req.response_ms < 0 or req.response_ms > 600000:
            raise AppError(
                code="invalid_response_time",
                message="Response time must be between 0 and 600,000 ms.",
                status_code=422,
            )

        # Validate session ownership and type
        prac_session = await session.get(Session, req.session_id)
        if not prac_session:
            raise NotFoundError(f"Practice session '{req.session_id}' not found.")
        if prac_session.user_id != user_id:
            raise ForbiddenError("Session does not belong to authenticated user.")
        if prac_session.kind != SessionKindEnum.PRACTICE:
            raise AppError(
                code="invalid_session_kind",
                message="Session is not an active practice session.",
                status_code=400,
            )

        # Idempotency check before checking session active state
        existing_attempt = await question_repo.get_attempt_by_client_id(
            session, req.client_attempt_id
        )
        if existing_attempt:
            if existing_attempt.user_id != user_id:
                raise ForbiddenError("Attempt belongs to another user.")
            if existing_attempt.session_id != req.session_id:
                raise AppError(
                    code="session_mismatch",
                    message="Client attempt ID belongs to another session.",
                    status_code=409,
                )

            # Return complete stored result including any detected misconception
            q = await question_repo.get_by_id(session, existing_attempt.question_id)
            if not q:
                raise NotFoundError("Question not found for stored attempt.")

            m_stmt = select(Mastery).where(
                Mastery.user_id == user_id, Mastery.concept_id == existing_attempt.concept_id
            )
            mastery_row = (await session.execute(m_stmt)).scalars().first()

            dm_stmt = select(DetectedMisconception).where(
                DetectedMisconception.attempt_id == existing_attempt.id
            )
            stored_dm = (await session.execute(dm_stmt)).scalars().first()
            stored_misc_feedback: MisconceptionFeedback | None = None
            if stored_dm:
                misc_obj = await session.get(Misconception, stored_dm.misconception_id)
                if misc_obj:
                    stored_misc_feedback = MisconceptionFeedback(
                        id=misc_obj.id,
                        statement=misc_obj.statement,
                        correction=misc_obj.correction,
                        source="reasoning"
                        if stored_dm.source == MisconceptionSourceEnum.LLM_REASONING
                        else "distractor",
                        confidence=stored_dm.confidence,
                    )

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
                misconception=stored_misc_feedback,
                ai=AIFallbackMeta(used=False),
                newly_unlocked=[],
            )

        if prac_session.status != SessionStatusEnum.ACTIVE:
            raise ConflictError("session_closed", "Practice session is already completed.")

        # Load question and concept
        question = await question_repo.get_by_id(session, req.question_id)
        if not question:
            raise NotFoundError(f"Question '{req.question_id}' not found.")

        concept = await concept_repo.get_by_id(session, question.concept_id)
        if not concept:
            raise NotFoundError(f"Concept '{question.concept_id}' not found.")

        # Validate selected key
        valid_keys = [
            opt.get("key") for opt in question.options if isinstance(opt, dict) and "key" in opt
        ]
        if req.selected_key not in valid_keys:
            raise AppError(
                code="invalid_selected_key",
                message=f"Selected key '{req.selected_key}' is not among valid options: {valid_keys}",
                status_code=422,
            )

        # Evaluate correctness
        is_correct = req.selected_key.strip().upper() == question.correct_key.strip().upper()

        # Check for distractor-based misconception
        chosen_opt = next(
            (opt for opt in question.options if opt.get("key") == req.selected_key), None
        )
        distractor_misc_id = chosen_opt.get("misconception_id") if chosen_opt else None

        # Load known misconceptions for this concept
        misc_stmt = select(Misconception).where(Misconception.concept_id == concept.id)
        concept_miscs = (await session.execute(misc_stmt)).scalars().all()
        concept_misc_ids = {m.id for m in concept_miscs}

        # Misconception diagnosis via LLM Router if student provided reasoning and was wrong
        classification_result = None
        ai_meta = AIFallbackMeta(used=False, model=None, fallback=False)

        if not is_correct and req.reasoning and len(req.reasoning.strip()) >= 5:
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

        # Capture unlocked concepts before update for delta calculation
        all_concepts = await concept_repo.list_all(session)
        prereqs = await concept_repo.list_all_prerequisites(session)
        prereq_map: dict[str, list[str]] = defaultdict(list)
        for dependent_id, prereq_id in prereqs:
            prereq_map[dependent_id].append(prereq_id)
        user_masteries_before = await concept_repo.get_user_masteries(session, user_id)
        unlocked_before = self._get_unlocked_concept_ids(
            all_concepts, prereq_map, user_masteries_before
        )

        # Lock mastery row with FOR UPDATE and persist learner updates
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

        # Update or create Mastery with concurrency handling
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

        try:
            await session.flush()
        except IntegrityError:
            # Handle concurrent first attempt write race condition
            await session.rollback()
            # Reload session and locked mastery
            prac_session = await session.get(Session, req.session_id)
            mastery = (await session.execute(mastery_stmt)).scalars().first()
            if mastery:
                mastery.p_mastery = p_next
                mastery.attempts += 1
                mastery.correct += 1 if is_correct else 0
                mastery.last_seen_at = now
                mastery.version += 1
            session.add(attempt)
            await session.flush()

        # Misconception resolution and recording
        misconception_feedback: MisconceptionFeedback | None = None
        if not is_correct:
            active_misc_id = None
            misc_source = MisconceptionSourceEnum.DISTRACTOR
            confidence = 1.0

            if classification_result and classification_result.misconception_detected:
                candidate_id = classification_result.misconception_id or distractor_misc_id
                if candidate_id in concept_misc_ids:
                    active_misc_id = candidate_id
                    misc_source = MisconceptionSourceEnum.LLM_REASONING
                    confidence = classification_result.confidence
            elif distractor_misc_id and distractor_misc_id in concept_misc_ids:
                active_misc_id = distractor_misc_id
                misc_source = MisconceptionSourceEnum.DISTRACTOR
                confidence = 1.0

            if active_misc_id:
                misc_obj = await session.get(Misconception, active_misc_id)
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
        else:
            # Misconception resolution: if learner answers correctly, resolve active misconceptions for this concept
            res_stmt = select(DetectedMisconception).where(
                DetectedMisconception.user_id == user_id,
                DetectedMisconception.resolved_at.is_(None),
                DetectedMisconception.misconception_id.in_(concept_misc_ids),
            )
            to_resolve = (await session.execute(res_stmt)).scalars().all()
            for dm in to_resolve:
                dm.resolved_at = now

        # Compute newly unlocked concepts
        user_masteries_after = dict(user_masteries_before)
        user_masteries_after[concept.id] = {
            "p_mastery": p_next,
            "attempts": attempts_count + 1,
            "next_due_at": next_due,
        }
        unlocked_after = self._get_unlocked_concept_ids(
            all_concepts, prereq_map, user_masteries_after
        )
        newly_unlocked = [c_id for c_id in unlocked_after if c_id not in unlocked_before]

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
            newly_unlocked=newly_unlocked,
        )


practice_service = PracticeService()
