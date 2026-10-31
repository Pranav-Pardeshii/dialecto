import asyncio
import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agents.judge import judge_explanation
from app.ai.agents.student_persona import generate_pip_reply
from app.core.errors import AppError, NotFoundError
from app.domain.bkt import bkt_update
from app.models.entities import (
    Mastery,
    Misconception,
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
    "cr-reflex": "Hi! How does a reflex action work so quickly without waiting for the brain?",
    "hr-mendel-dihybrid": "Hello! I find Mendel's dihybrid cross really complicated. Can you teach me how the 9:3:3:1 ratio happens?",
}


class TeachbackService:
    def __init__(self) -> None:
        self._session_locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, session_id: int) -> asyncio.Lock:
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

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
        """Processes a student explanation turn: judges rubric coverage, updates Pip persona, and tracks soft evidence."""
        lock = self._get_lock(session_id)
        if lock.locked():
            raise AppError(
                code="turn_in_progress",
                message="A turn is currently in progress for this session",
                status_code=409,
            )

        async with lock:
            # Step 1: Read session & concept state
            stmt = (
                select(TeachbackSession)
                .options(selectinload(TeachbackSession.turns))
                .where(TeachbackSession.id == session_id, TeachbackSession.user_id == user_id)
            )
            tb_session = (await session.execute(stmt)).scalars().first()
            if not tb_session:
                raise NotFoundError(f"Teachback session '{session_id}' not found")

            if tb_session.final_level == 3 or tb_session.turn_count >= 4:
                raise AppError(
                    code="session_closed",
                    message="This Teach-Back session has concluded",
                    status_code=409,
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

            # Current mastery
            mastery_stmt = select(Mastery).where(
                Mastery.user_id == user_id, Mastery.concept_id == concept.id
            )
            mastery_obj = (await session.execute(mastery_stmt)).scalars().first()
            p_prior = mastery_obj.p_mastery if mastery_obj else concept.p_l0

            # Build dialog history from existing turns
            sorted_turns = sorted(tb_session.turns, key=lambda t: t.idx)
            dialog_history = [{"role": t.role.value, "content": t.content} for t in sorted_turns]

            current_pip_level = 0
            for t in reversed(sorted_turns):
                if t.role == TeachbackRoleEnum.PIP and t.level is not None:
                    current_pip_level = t.level
                    break

            # Step 2: AI Judge & Pip Persona evaluation (Outside open DB write transactions)
            judge_res, judge_ai_meta = await judge_explanation(
                concept_name=concept.name,
                chapter=concept.chapter,
                rubric_points=concept.key_points or [],
                known_misconceptions=misc_dicts,
                student_explanation=req.content,
            )

            # State machine update: Pip's level progresses monotonically
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

            # Step 3: Compute soft evidence Bayesian update if finished
            p_after = p_prior
            result_out: TeachbackResultOut | None = None
            now = datetime.datetime.now(datetime.UTC)

            if finished:
                is_correct = judge_res.accuracy_score >= 0.65
                _, p_bkt = bkt_update(
                    p_prior=p_prior,
                    is_correct=is_correct,
                    base_slip=concept.p_s,
                    learn_rate=concept.p_t,
                    num_options=4,
                )
                weight = min(0.70, judge_res.confidence)
                p_after = p_prior + weight * (p_bkt - p_prior)

                status_str = "mastered" if p_after >= 0.80 else "learning"
                result_out = TeachbackResultOut(
                    final_score=judge_res.accuracy_score,
                    final_level=new_pip_level,
                    mastery=MasteryDelta(
                        concept_id=concept.id,
                        before=p_prior,
                        after=p_after,
                        status=status_str,
                    ),
                    strengths=judge_res.covered_points,
                    gaps=judge_res.missing_points,
                )

            # Step 4: Atomic Write Transaction
            # Lock mastery row if updating
            if finished:
                lock_mastery_stmt = (
                    select(Mastery)
                    .where(Mastery.user_id == user_id, Mastery.concept_id == concept.id)
                    .with_for_update()
                )
                locked_mastery = (await session.execute(lock_mastery_stmt)).scalars().first()
                if not locked_mastery:
                    locked_mastery = Mastery(
                        user_id=user_id,
                        concept_id=concept.id,
                        p_mastery=p_after,
                        attempts=1,
                        correct=1 if judge_res.accuracy_score >= 0.65 else 0,
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
                    locked_mastery.correct += 1 if judge_res.accuracy_score >= 0.65 else 0
                    locked_mastery.last_seen_at = now
                    locked_mastery.version += 1

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

        is_finished = (tb_session.final_level == 3) or (tb_session.turn_count >= 4)

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
