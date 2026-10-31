import json
import uuid
from pathlib import Path

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.router import router
from app.core.errors import AppError, BadRequestError, ConflictError, NotFoundError
from app.domain.question_validator import QuestionValidator
from app.models.entities import (
    Concept,
    Misconception,
    Question,
    QuestionKindEnum,
    QuestionReviewStatusEnum,
    QuestionSourceEnum,
)
from app.schemas.authoring import (
    GeneratedQuestionBatchResponse,
    QuestionAuthoringOut,
    QuestionCreateRequest,
    QuestionGenerateRequest,
    QuestionReviewActionRequest,
    QuestionUpdateRequest,
)

logger = structlog.get_logger(__name__)
PROMPTS_DIR = Path(__file__).parent.parent / "ai" / "prompts"


class LLMOptionItem(BaseModel):
    key: str
    text: str
    misconception_id: str | None = None


class LLMGeneratedItem(BaseModel):
    stem: str
    kind: str = "mcq"
    options: list[LLMOptionItem] = Field(default_factory=list)
    correct_key: str
    explanation: str
    difficulty_bucket: int = Field(default=2, ge=1, le=3)
    cognitive_skill: str | None = None
    learning_objective: str | None = None
    curriculum_ref: str | None = None
    distractor_explanations: dict[str, str] | None = None


class LLMGeneratedBatch(BaseModel):
    questions: list[LLMGeneratedItem]


def _to_authoring_out(q: Question) -> QuestionAuthoringOut:
    return QuestionAuthoringOut(
        id=q.id,
        concept_id=q.concept_id,
        kind=str(q.kind.value if hasattr(q.kind, "value") else q.kind),
        stem=q.stem,
        options=q.options if isinstance(q.options, list) else [],
        correct_key=q.correct_key,
        explanation=q.explanation,
        difficulty_bucket=q.difficulty_bucket,
        difficulty_rating=q.difficulty_rating,
        n_attempts=q.n_attempts,
        verified=q.verified,
        source=str(q.source.value if hasattr(q.source, "value") else q.source),
        review_status=str(q.review_status.value if hasattr(q.review_status, "value") else q.review_status),
        version=q.version,
        parent_id=q.parent_id,
        author_id=q.author_id,
        learning_objective=q.learning_objective,
        cognitive_skill=q.cognitive_skill,
        curriculum_ref=q.curriculum_ref,
        generation_model=q.generation_model,
        distractor_explanations=q.distractor_explanations,
        rejection_reason=q.rejection_reason,
    )


class QuestionAuthoringService:
    def __init__(self) -> None:
        self.prompt_template = (PROMPTS_DIR / "question_generator.md").read_text(encoding="utf-8")

    async def generate_questions(
        self, session: AsyncSession, req: QuestionGenerateRequest, teacher_id: int
    ) -> GeneratedQuestionBatchResponse:
        """Runs the LLM generation pipeline and stores validated drafts in PostgreSQL."""
        # 1. Fetch concept and known misconceptions
        concept_stmt = select(Concept).where(Concept.id == req.concept_id)
        concept_res = await session.execute(concept_stmt)
        concept = concept_res.scalars().first()
        if not concept:
            raise NotFoundError(f"Concept '{req.concept_id}' not found.")

        misc_stmt = select(Misconception).where(Misconception.concept_id == req.concept_id)
        misc_res = await session.execute(misc_stmt)
        misconceptions = list(misc_res.scalars().all())
        valid_misc_ids = {m.id for m in misconceptions}

        misc_context = [
            {"id": m.id, "statement": m.statement, "correction": m.correction}
            for m in misconceptions
        ]

        # 2. Render prompt
        prompt = self.prompt_template
        prompt = prompt.replace("{{ concept_name }}", concept.name)
        prompt = prompt.replace("{{ concept_id }}", concept.id)
        prompt = prompt.replace("{{ chapter }}", concept.chapter)
        prompt = prompt.replace("{{ description }}", concept.description)
        prompt = prompt.replace("{{ key_points }}", json.dumps(concept.key_points))
        prompt = prompt.replace("{{ known_misconceptions }}", json.dumps(misc_context))
        prompt = prompt.replace("{{ question_kind }}", req.kind)
        prompt = prompt.replace("{{ difficulty_bucket }}", str(req.difficulty_bucket))
        prompt = prompt.replace("{{ cognitive_skill }}", req.cognitive_skill or "understanding")
        prompt = prompt.replace("{{ learning_objective }}", req.learning_objective or f"Assess mastery of {concept.name}")
        prompt = prompt.replace("{{ target_misconception }}", req.target_misconception_id or "Any known misconception for this concept")
        prompt = prompt.replace("{{ count }}", str(req.count))

        messages = [
            {"role": "system", "content": "You are a CBSE Class 10 Biology item writer. Output strictly valid JSON."},
            {"role": "user", "content": prompt},
        ]

        # 3. Call LLM Router
        try:
            res, meta = await router.complete(
                purpose="question_generation",
                messages=messages,
                schema=LLMGeneratedBatch,
                max_tokens=3000,
                temperature=0.3,
            )
        except Exception as exc:
            logger.error("question_generation_llm_failed", error=str(exc), concept_id=req.concept_id)
            raise AppError(
                message=f"Question generation failed: {exc}",
                code="ai_unavailable",
                status_code=503,
            ) from exc

        if not isinstance(res, LLMGeneratedBatch):
            raise AppError(
                message="LLM returned an invalid response structure.",
                code="ai_unavailable",
                status_code=502,
            )

        # 4. Fetch existing question stems for duplicate check
        existing_stems_stmt = select(Question.stem).where(Question.concept_id == req.concept_id)
        existing_stems_res = await session.execute(existing_stems_stmt)
        existing_stems = {s.strip().lower() for s in existing_stems_res.scalars().all()}

        saved_questions: list[QuestionAuthoringOut] = []
        validation_errors: list[str] = []
        passed_count = 0
        failed_count = 0

        # 5. Validate and save each generated question as a draft
        for idx, item in enumerate(res.questions):
            raw_options = [opt.model_dump() for opt in item.options]
            item_errors = QuestionValidator.validate_question(
                stem=item.stem,
                kind=item.kind,
                options=raw_options,
                correct_key=item.correct_key,
                explanation=item.explanation,
                difficulty_bucket=item.difficulty_bucket,
                concept_id=req.concept_id,
                valid_concept_misconception_ids=valid_misc_ids,
                existing_stems=existing_stems,
            )

            if item_errors:
                failed_count += 1
                validation_errors.append(f"Question #{idx + 1}: {'; '.join(item_errors)}")
                continue

            passed_count += 1
            existing_stems.add(item.stem.strip().lower())

            # Assign slug-like ID
            qid = f"gen-{req.concept_id[:16]}-{uuid.uuid4().hex[:8]}"

            # Map difficulty bucket to rating
            diff_rating = -1.0 if item.difficulty_bucket == 1 else (1.0 if item.difficulty_bucket == 3 else 0.0)

            # Map kind enum safely
            kind_enum = QuestionKindEnum.MCQ
            try:
                kind_enum = QuestionKindEnum(item.kind)
            except ValueError:
                kind_enum = QuestionKindEnum.MCQ

            db_q = Question(
                id=qid,
                concept_id=req.concept_id,
                kind=kind_enum,
                stem=item.stem,
                options=raw_options,
                correct_key=item.correct_key.upper(),
                explanation=item.explanation,
                difficulty_bucket=item.difficulty_bucket,
                difficulty_rating=diff_rating,
                n_attempts=0,
                verified=False,
                source=QuestionSourceEnum.LLM,
                review_status=QuestionReviewStatusEnum.DRAFT,
                version=1,
                author_id=teacher_id,
                learning_objective=item.learning_objective,
                cognitive_skill=item.cognitive_skill,
                curriculum_ref=item.curriculum_ref or "NCERT Class 10 Biology",
                generation_model=meta.model if hasattr(meta, "model") else "groq",
                distractor_explanations=item.distractor_explanations,
            )
            session.add(db_q)
            await session.flush()
            saved_questions.append(_to_authoring_out(db_q))

        await session.commit()

        return GeneratedQuestionBatchResponse(
            generated=saved_questions,
            validation_passed=passed_count,
            validation_failed=failed_count,
            errors=validation_errors,
        )

    async def list_questions(
        self,
        session: AsyncSession,
        concept_id: str | None = None,
        review_status: str | None = None,
        kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[QuestionAuthoringOut], int]:
        stmt = select(Question)
        count_stmt = select(func.count(Question.id))

        if concept_id:
            stmt = stmt.where(Question.concept_id == concept_id)
            count_stmt = count_stmt.where(Question.concept_id == concept_id)
        if review_status:
            stmt = stmt.where(Question.review_status == review_status)
            count_stmt = count_stmt.where(Question.review_status == review_status)
        if kind:
            stmt = stmt.where(Question.kind == kind)
            count_stmt = count_stmt.where(Question.kind == kind)

        stmt = stmt.order_by(desc(Question.version), Question.id).limit(limit).offset(offset)

        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one()

        res = await session.execute(stmt)
        items = list(res.scalars().all())
        return [_to_authoring_out(q) for q in items], total

    async def get_question(self, session: AsyncSession, question_id: str) -> QuestionAuthoringOut:
        stmt = select(Question).where(Question.id == question_id)
        res = await session.execute(stmt)
        q = res.scalars().first()
        if not q:
            raise NotFoundError(f"Question '{question_id}' not found.")
        return _to_authoring_out(q)

    async def create_question_draft(
        self, session: AsyncSession, req: QuestionCreateRequest, teacher_id: int
    ) -> QuestionAuthoringOut:
        # Check concept
        c_stmt = select(Concept).where(Concept.id == req.concept_id)
        c_res = await session.execute(c_stmt)
        if not c_res.scalars().first():
            raise NotFoundError(f"Concept '{req.concept_id}' not found.")

        # Misconceptions for concept
        misc_stmt = select(Misconception).where(Misconception.concept_id == req.concept_id)
        misc_res = await session.execute(misc_stmt)
        valid_misc_ids = {m.id for m in misc_res.scalars().all()}

        raw_options = [opt.model_dump() for opt in req.options]
        errors = QuestionValidator.validate_question(
            stem=req.stem,
            kind=req.kind,
            options=raw_options,
            correct_key=req.correct_key,
            explanation=req.explanation,
            difficulty_bucket=req.difficulty_bucket,
            concept_id=req.concept_id,
            valid_concept_misconception_ids=valid_misc_ids,
        )
        if errors:
            raise BadRequestError(f"Question validation failed: {'; '.join(errors)}")

        qid = f"author-{req.concept_id[:16]}-{uuid.uuid4().hex[:8]}"
        diff_rating = -1.0 if req.difficulty_bucket == 1 else (1.0 if req.difficulty_bucket == 3 else 0.0)

        kind_enum = QuestionKindEnum.MCQ
        try:
            kind_enum = QuestionKindEnum(req.kind)
        except ValueError:
            kind_enum = QuestionKindEnum.MCQ

        db_q = Question(
            id=qid,
            concept_id=req.concept_id,
            kind=kind_enum,
            stem=req.stem,
            options=raw_options,
            correct_key=req.correct_key.upper(),
            explanation=req.explanation,
            difficulty_bucket=req.difficulty_bucket,
            difficulty_rating=diff_rating,
            n_attempts=0,
            verified=False,
            source=QuestionSourceEnum.TEACHER,
            review_status=QuestionReviewStatusEnum.DRAFT,
            version=1,
            author_id=teacher_id,
            learning_objective=req.learning_objective,
            cognitive_skill=req.cognitive_skill,
            curriculum_ref=req.curriculum_ref or "Teacher Authored",
            distractor_explanations=req.distractor_explanations,
        )
        session.add(db_q)
        await session.commit()
        await session.refresh(db_q)
        return _to_authoring_out(db_q)

    async def update_question(
        self, session: AsyncSession, question_id: str, req: QuestionUpdateRequest, teacher_id: int
    ) -> QuestionAuthoringOut:
        """Updates a question with strict versioning.

        If the question has historical attempts, it creates a new question version!
        """
        stmt = select(Question).where(Question.id == question_id)
        res = await session.execute(stmt)
        existing = res.scalars().first()
        if not existing:
            raise NotFoundError(f"Question '{question_id}' not found.")

        # Determine target values
        new_stem = req.stem if req.stem is not None else existing.stem
        new_kind = req.kind if req.kind is not None else (existing.kind.value if hasattr(existing.kind, "value") else str(existing.kind))
        new_options = [opt.model_dump() for opt in req.options] if req.options is not None else existing.options
        new_correct_key = req.correct_key if req.correct_key is not None else existing.correct_key
        new_explanation = req.explanation if req.explanation is not None else existing.explanation
        new_diff_bucket = req.difficulty_bucket if req.difficulty_bucket is not None else existing.difficulty_bucket
        new_obj = req.learning_objective if req.learning_objective is not None else existing.learning_objective
        new_cog = req.cognitive_skill if req.cognitive_skill is not None else existing.cognitive_skill
        new_curriculum = req.curriculum_ref if req.curriculum_ref is not None else existing.curriculum_ref
        new_distractors = req.distractor_explanations if req.distractor_explanations is not None else existing.distractor_explanations

        # Validate
        misc_stmt = select(Misconception).where(Misconception.concept_id == existing.concept_id)
        misc_res = await session.execute(misc_stmt)
        valid_misc_ids = {m.id for m in misc_res.scalars().all()}

        errors = QuestionValidator.validate_question(
            stem=new_stem,
            kind=new_kind,
            options=new_options,
            correct_key=new_correct_key,
            explanation=new_explanation,
            difficulty_bucket=new_diff_bucket,
            concept_id=existing.concept_id,
            valid_concept_misconception_ids=valid_misc_ids,
        )
        if errors:
            raise BadRequestError(f"Validation failed: {'; '.join(errors)}")

        # If question has attempts, create a NEW VERSION to preserve historical attempts!
        if existing.n_attempts > 0:
            new_qid = f"{existing.id}-v{existing.version + 1}"
            kind_enum = QuestionKindEnum.MCQ
            try:
                kind_enum = QuestionKindEnum(new_kind)
            except ValueError:
                kind_enum = QuestionKindEnum.MCQ

            new_q = Question(
                id=new_qid,
                concept_id=existing.concept_id,
                kind=kind_enum,
                stem=new_stem,
                options=new_options,
                correct_key=new_correct_key.upper(),
                explanation=new_explanation,
                difficulty_bucket=new_diff_bucket,
                difficulty_rating=existing.difficulty_rating,
                n_attempts=0,
                verified=False,
                source=QuestionSourceEnum.TEACHER,
                review_status=QuestionReviewStatusEnum.DRAFT,
                version=existing.version + 1,
                parent_id=existing.id,
                author_id=teacher_id,
                learning_objective=new_obj,
                cognitive_skill=new_cog,
                curriculum_ref=new_curriculum,
                distractor_explanations=new_distractors,
            )
            session.add(new_q)
            await session.commit()
            await session.refresh(new_q)
            return _to_authoring_out(new_q)
        else:
            # Update draft in place
            existing.stem = new_stem
            try:
                existing.kind = QuestionKindEnum(new_kind)
            except ValueError:
                pass
            existing.options = new_options
            existing.correct_key = new_correct_key.upper()
            existing.explanation = new_explanation
            existing.difficulty_bucket = new_diff_bucket
            existing.learning_objective = new_obj
            existing.cognitive_skill = new_cog
            existing.curriculum_ref = new_curriculum
            existing.distractor_explanations = new_distractors
            await session.commit()
            await session.refresh(existing)
            return _to_authoring_out(existing)

    async def review_question(
        self, session: AsyncSession, question_id: str, req: QuestionReviewActionRequest, teacher_id: int
    ) -> QuestionAuthoringOut:
        stmt = select(Question).where(Question.id == question_id)
        res = await session.execute(stmt)
        q = res.scalars().first()
        if not q:
            raise NotFoundError(f"Question '{question_id}' not found.")

        action = req.action.lower().strip()
        if action == "approve":
            # Re-validate before approval
            misc_stmt = select(Misconception).where(Misconception.concept_id == q.concept_id)
            misc_res = await session.execute(misc_stmt)
            valid_misc_ids = {m.id for m in misc_res.scalars().all()}

            kind_str = q.kind.value if hasattr(q.kind, "value") else str(q.kind)
            errors = QuestionValidator.validate_question(
                stem=q.stem,
                kind=kind_str,
                options=q.options,
                correct_key=q.correct_key,
                explanation=q.explanation,
                difficulty_bucket=q.difficulty_bucket,
                concept_id=q.concept_id,
                valid_concept_misconception_ids=valid_misc_ids,
            )
            if errors:
                raise BadRequestError(f"Cannot approve invalid question: {'; '.join(errors)}")

            q.review_status = QuestionReviewStatusEnum.APPROVED
            q.verified = True
            q.rejection_reason = None
        elif action == "reject":
            if not req.rejection_reason or len(req.rejection_reason.strip()) < 5:
                raise BadRequestError("A rejection reason must be provided (at least 5 characters).")
            q.review_status = QuestionReviewStatusEnum.REJECTED
            q.verified = False
            q.rejection_reason = req.rejection_reason.strip()
        else:
            raise BadRequestError(f"Invalid review action '{req.action}'. Must be 'approve' or 'reject'.")

        await session.commit()
        await session.refresh(q)
        return _to_authoring_out(q)

    async def delete_question(self, session: AsyncSession, question_id: str) -> None:
        stmt = select(Question).where(Question.id == question_id)
        res = await session.execute(stmt)
        q = res.scalars().first()
        if not q:
            raise NotFoundError(f"Question '{question_id}' not found.")
        if q.n_attempts > 0:
            raise ConflictError("has_attempts", "Cannot delete a question that has recorded student attempts.")
        await session.delete(q)
        await session.commit()


question_authoring_service = QuestionAuthoringService()
