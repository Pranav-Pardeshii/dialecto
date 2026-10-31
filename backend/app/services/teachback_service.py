import asyncio
import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agents.judge import judge_explanation
from app.ai.agents.student_persona import generate_pip_reply
from app.core.errors import AppError, NotFoundError
from app.domain.bkt import soft_evidence_update
from app.models.entities import (
    DetectedMisconception,
    Mastery,
    Misconception,
    MisconceptionSourceEnum,
    Session,
    SessionKindEnum,
    SessionStatusEnum,
    TeachbackRoleEnum,
    TeachbackSession,
    TeachbackTurn,
)
from app.repositories.concept_repo import concept_repo
from app.schemas.practice import AIFallbackMeta, MasteryDelta
from app.schemas.teachback import (
    PipTurnOut,
    RubricOut,
    TeachbackDetailResponse,
    TeachbackMisconceptionFeedback,
    TeachbackResultOut,
    TeachbackSessionStartResponse,
    TeachbackTranscriptTurn,
    TeachbackTurnFeedback,
    TeachbackTurnRequest,
    TeachbackTurnResponse,
)

logger = structlog.get_logger(__name__)

INITIAL_PIP_PROMPTS: dict[str, str] = {
    "lp-photosynthesis": "Hi! Can you teach me how plants make food using sunlight? Where does the oxygen come from?",
    "lp-nutrition": "Hey! Could you explain the difference between autotrophic and heterotrophic nutrition to me?",
    "lp-stomata": "Hi there! I'm confused about how stomata open and close in leaves. Can you explain that to me?",
    "cc-reflex": "Hi! How does a reflex action work so quickly without waiting for the brain?",
    "he-dihybrid": "Hello! I find Mendel's dihybrid cross really complicated. Can you teach me how the 9:3:3:1 ratio happens?",
}

TRIVIAL_UTTERANCES = {
    "ok",
    "ok thanks",
    "okay",
    "thanks",
    "thank you",
    "bye",
    "goodbye",
    "cool",
    "got it",
    "yes",
    "no",
    "sure",
    "k",
    "alright",
}


class TeachbackService:
    def __init__(self) -> None:
        self._session_locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, session_id: int) -> asyncio.Lock:
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    def _cleanup_lock(self, session_id: int) -> None:
        if session_id in self._session_locks and not self._session_locks[session_id].locked():
            self._session_locks.pop(session_id, None)

    async def start_session(
        self,
        session: AsyncSession,
        user_id: int,
        concept_id: str,
    ) -> TeachbackSessionStartResponse:
        """Initializes a new Teach-Back dialogue session with Pip."""
        concept = await concept_repo.get_by_id(session, concept_id)
        if not concept:
            raise NotFoundError(f"Concept '{concept_id}' not found")

        now = datetime.datetime.now(datetime.UTC)

        # 1. Create main session entity
        parent_session = Session(
            user_id=user_id,
            kind=SessionKindEnum.TEACHBACK,
            status=SessionStatusEnum.ACTIVE,
            started_at=now,
        )
        session.add(parent_session)
        await session.flush()

        # 2. Create TeachbackSession entity
        tb_session = TeachbackSession(
            session_id=parent_session.id,
            user_id=user_id,
            concept_id=concept_id,
            status=SessionStatusEnum.ACTIVE,
            turn_count=0,
            final_score=None,
            final_level=0,
        )
        session.add(tb_session)
        await session.flush()

        # 3. Pip's opening question (Turn 0)
        opening_line = INITIAL_PIP_PROMPTS.get(
            concept_id,
            f"Hi! Can you teach me about {concept.name}? How does it work?",
        )

        initial_pip_turn = TeachbackTurn(
            teachback_session_id=tb_session.id,
            idx=0,
            role=TeachbackRoleEnum.PIP,
            content=opening_line,
            judge=None,
            level=0,
            created_at=now,
        )
        session.add(initial_pip_turn)
        await session.commit()

        return TeachbackSessionStartResponse(
            id=tb_session.id,
            concept_id=concept.id,
            concept_name=concept.name,
            turn_count=0,
            pip=PipTurnOut(content=opening_line, level=0),
            rubric=RubricOut(key_points=concept.key_points or []),
            finished=False,
        )

    async def submit_turn(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: int,
        req: TeachbackTurnRequest,
    ) -> TeachbackTurnResponse:
        """Processes a student explanation turn: evaluates transcript, updates Pip persona, and tracks soft evidence."""
        lock = self._get_lock(session_id)
        if lock.locked():
            raise AppError(
                code="turn_in_progress",
                message="A turn is currently in progress for this session",
                status_code=409,
            )

        async with lock:
            try:
                # Step 1: Read session & concept state
                stmt = (
                    select(TeachbackSession)
                    .options(selectinload(TeachbackSession.turns))
                    .where(TeachbackSession.id == session_id, TeachbackSession.user_id == user_id)
                )
                tb_session = (await session.execute(stmt)).scalars().first()
                if not tb_session:
                    raise NotFoundError(f"Teachback session '{session_id}' not found")

                # If session is already completed, return idempotent completion response
                if tb_session.status == SessionStatusEnum.COMPLETED:
                    sorted_turns = sorted(tb_session.turns, key=lambda t: t.idx)
                    last_pip_turn = next(
                        (t for t in reversed(sorted_turns) if t.role == TeachbackRoleEnum.PIP), None
                    )
                    pip_content = last_pip_turn.content if last_pip_turn else "Thank you for teaching me!"
                    return TeachbackTurnResponse(
                        turn_index=tb_session.turn_count,
                        pip=PipTurnOut(content=pip_content, level=tb_session.final_level or 3),
                        feedback=TeachbackTurnFeedback(
                            score=tb_session.final_score or 1.0,
                            covered=[],
                            missing=[],
                            misconceptions=[],
                        ),
                        finished=True,
                        result=None,
                        ai=AIFallbackMeta(used=False),
                    )

                concept = await concept_repo.get_by_id(session, tb_session.concept_id)
                if not concept:
                    raise NotFoundError(f"Concept '{tb_session.concept_id}' not found")

                # Load known misconceptions
                misc_stmt = select(Misconception).where(Misconception.concept_id == concept.id)
                concept_miscs = (await session.execute(misc_stmt)).scalars().all()
                misc_dicts = [
                    {"id": m.id, "statement": m.statement, "correction": m.correction}
                    for m in concept_miscs
                ]

                # Build dialog history from existing turns
                sorted_turns = sorted(tb_session.turns, key=lambda t: t.idx)
                dialog_history = [{"role": t.role.value, "content": t.content} for t in sorted_turns]

                current_pip_level = 0
                prior_best_score = 0.0
                for t in reversed(sorted_turns):
                    if t.role == TeachbackRoleEnum.PIP and t.level is not None:
                        current_pip_level = max(current_pip_level, t.level)
                    if t.role == TeachbackRoleEnum.LEARNER and t.judge:
                        prior_best_score = max(
                            prior_best_score, float(t.judge.get("accuracy_score", 0.0))
                        )

                # Check if this turn is a conversational filler/acknowledgement
                cleaned_content = req.content.strip().lower()
                is_trivial = cleaned_content in TRIVIAL_UTTERANCES or len(cleaned_content) < 4

                # Build cumulative learner explanation context
                learner_explanations = [
                    t.content for t in sorted_turns if t.role == TeachbackRoleEnum.LEARNER
                ]
                learner_explanations.append(req.content)
                cumulative_explanation = "\n---\n".join(learner_explanations)

                # Step 2: AI Judge & Pip Persona evaluation
                judge_res, judge_ai_meta = await judge_explanation(
                    concept_name=concept.name,
                    chapter=concept.chapter,
                    rubric_points=concept.key_points or [],
                    known_misconceptions=misc_dicts,
                    student_explanation=cumulative_explanation if not is_trivial else (
                        learner_explanations[0] if len(learner_explanations) > 1 else req.content
                    ),
                )

                # If current turn was trivial acknowledgment, do not degrade prior best score or level
                if is_trivial and prior_best_score > 0.0:
                    judge_res.accuracy_score = max(judge_res.accuracy_score, prior_best_score)

                # Pip's level progresses monotonically
                new_pip_level = max(current_pip_level, judge_res.comprehension_level)
                new_turn_count = tb_session.turn_count + 1
                finished = (new_pip_level >= 3) or (new_turn_count >= 4)

                pip_res, pip_ai_meta = await generate_pip_reply(
                    concept_name=concept.name,
                    current_level=new_pip_level,
                    dialog_history=dialog_history,
                    tutor_message=req.content,
                )

                ai_meta = AIFallbackMeta(
                    used=judge_ai_meta.used or pip_ai_meta.used,
                    model=judge_ai_meta.model or pip_ai_meta.model,
                    fallback=judge_ai_meta.fallback or pip_ai_meta.fallback,
                )

                # Step 3: Fresh write transaction & locking (avoiding stale mastery overwrite)
                now = datetime.datetime.now(datetime.UTC)
                result_out: TeachbackResultOut | None = None

                # Re-query fresh mastery with FOR UPDATE inside write transaction
                lock_mastery_stmt = (
                    select(Mastery)
                    .where(Mastery.user_id == user_id, Mastery.concept_id == concept.id)
                    .with_for_update()
                )
                locked_mastery = (await session.execute(lock_mastery_stmt)).scalars().first()
                fresh_p_prior = locked_mastery.p_mastery if locked_mastery else concept.p_l0
                p_after = fresh_p_prior

                if finished:
                    # Mark sessions completed
                    tb_session.status = SessionStatusEnum.COMPLETED
                    parent_session = await session.get(Session, tb_session.session_id)
                    if parent_session:
                        parent_session.status = SessionStatusEnum.COMPLETED
                        parent_session.ended_at = now

                    # Only perform Bayesian update on authoritative AI judgment (not keyword fallback)
                    if not judge_ai_meta.fallback:
                        is_positive = judge_res.accuracy_score >= 0.65
                        p_after = soft_evidence_update(
                            p_prior=fresh_p_prior,
                            is_positive=is_positive,
                            confidence=judge_res.confidence,
                            base_slip=concept.p_s,
                            learn_rate=concept.p_t,
                        )

                        if not locked_mastery:
                            locked_mastery = Mastery(
                                user_id=user_id,
                                concept_id=concept.id,
                                p_mastery=p_after,
                                attempts=1,
                                correct=1 if is_positive else 0,
                                last_seen_at=now,
                                ease=2.5,
                                interval_days=1,
                                repetitions=1,
                                next_due_at=now + datetime.timedelta(days=1),
                                version=1,
                            )
                            session.add(locked_mastery)
                        else:
                            locked_mastery.p_mastery = p_after
                            locked_mastery.attempts += 1
                            if is_positive:
                                locked_mastery.correct += 1
                            locked_mastery.last_seen_at = now
                            locked_mastery.version += 1

                    status_str = "mastered" if p_after >= 0.80 else "learning"
                    result_out = TeachbackResultOut(
                        final_score=judge_res.accuracy_score,
                        final_level=new_pip_level,
                        mastery=MasteryDelta(
                            concept_id=concept.id,
                            before=fresh_p_prior,
                            after=p_after,
                            status=status_str,
                        ),
                        strengths=judge_res.covered_points,
                        gaps=judge_res.missing_points,
                    )

                # Append learner turn
                next_turn_idx = len(sorted_turns)
                learner_turn = TeachbackTurn(
                    teachback_session_id=tb_session.id,
                    idx=next_turn_idx,
                    role=TeachbackRoleEnum.LEARNER,
                    content=req.content,
                    judge=judge_res.model_dump(),
                    level=None,
                    created_at=now,
                )
                session.add(learner_turn)
                await session.flush()

                # Persist detected misconceptions with source=TEACHBACK
                for m in judge_res.misconceptions_found:
                    detected_misc = DetectedMisconception(
                        user_id=user_id,
                        misconception_id=m.id,
                        attempt_id=None,
                        teachback_turn_id=learner_turn.id,
                        source=MisconceptionSourceEnum.TEACHBACK,
                        confidence=judge_res.confidence,
                        created_at=now,
                    )
                    session.add(detected_misc)

                # Append pip turn
                pip_turn = TeachbackTurn(
                    teachback_session_id=tb_session.id,
                    idx=next_turn_idx + 1,
                    role=TeachbackRoleEnum.PIP,
                    content=pip_res.pip_reply,
                    judge=None,
                    level=new_pip_level,
                    created_at=now,
                )
                session.add(pip_turn)

                # Update TeachbackSession summary
                tb_session.turn_count = new_turn_count
                if finished:
                    tb_session.final_score = judge_res.accuracy_score
                    tb_session.final_level = new_pip_level

                await session.commit()

                feedback_misc = [
                    TeachbackMisconceptionFeedback(id=m.id, statement=m.statement)
                    for m in judge_res.misconceptions_found
                ]

                return TeachbackTurnResponse(
                    turn_index=new_turn_count,
                    pip=PipTurnOut(content=pip_res.pip_reply, level=new_pip_level),
                    feedback=TeachbackTurnFeedback(
                        score=judge_res.accuracy_score,
                        covered=judge_res.covered_points,
                        missing=judge_res.missing_points,
                        misconceptions=feedback_misc,
                    ),
                    finished=finished,
                    result=result_out,
                    ai=ai_meta,
                )
            finally:
                if finished:
                    self._cleanup_lock(session_id)

    async def get_session_detail(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: int,
    ) -> TeachbackDetailResponse:
        """Retrieves complete transcript and current state for a Teachback session."""
        stmt = (
            select(TeachbackSession)
            .options(selectinload(TeachbackSession.turns))
            .where(TeachbackSession.id == session_id, TeachbackSession.user_id == user_id)
        )
        tb_session = (await session.execute(stmt)).scalars().first()
        if not tb_session:
            raise NotFoundError(f"Teachback session '{session_id}' not found")

        concept = await concept_repo.get_by_id(session, tb_session.concept_id)
        concept_name = concept.name if concept else tb_session.concept_id

        sorted_turns = sorted(tb_session.turns, key=lambda t: t.idx)
        current_level = 0
        for t in reversed(sorted_turns):
            if t.role == TeachbackRoleEnum.PIP and t.level is not None:
                current_level = t.level
                break

        transcript_turns = [
            TeachbackTranscriptTurn(
                idx=t.idx,
                role=t.role.value,
                content=t.content,
                level=t.level,
                created_at=t.created_at,
            )
            for t in sorted_turns
        ]

        is_finished = (
            tb_session.status == SessionStatusEnum.COMPLETED
            or (tb_session.final_level is not None and tb_session.final_level >= 3)
            or (tb_session.turn_count >= 4)
        )

        return TeachbackDetailResponse(
            id=tb_session.id,
            concept_id=tb_session.concept_id,
            concept_name=concept_name,
            turn_count=tb_session.turn_count,
            current_level=current_level,
            finished=is_finished,
            final_score=tb_session.final_score,
            turns=transcript_turns,
        )


teachback_service = TeachbackService()
