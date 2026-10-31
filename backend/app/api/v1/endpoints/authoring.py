from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_teacher
from app.db.session import get_db_session
from app.schemas.authoring import (
    GeneratedQuestionBatchResponse,
    QuestionAuthoringListResponse,
    QuestionAuthoringOut,
    QuestionCreateRequest,
    QuestionGenerateRequest,
    QuestionReviewActionRequest,
    QuestionUpdateRequest,
)
from app.schemas.user import UserOut
from app.services.question_authoring_service import question_authoring_service

router = APIRouter(prefix="/authoring", tags=["Question Authoring"])


@router.post(
    "/questions/generate",
    response_model=GeneratedQuestionBatchResponse,
    summary="Generate CBSE Class 10 Biology questions with deterministic validation",
)
async def generate_questions(
    req: QuestionGenerateRequest,
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GeneratedQuestionBatchResponse:
    return await question_authoring_service.generate_questions(session, req, teacher.id)


@router.get(
    "/questions",
    response_model=QuestionAuthoringListResponse,
    summary="List questions in the authoring repository with status/concept filters",
)
async def list_questions(
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    concept_id: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> QuestionAuthoringListResponse:
    questions, total = await question_authoring_service.list_questions(
        session, concept_id, review_status, kind, limit, offset
    )
    return QuestionAuthoringListResponse(questions=questions, total=total)


@router.get(
    "/questions/{question_id}",
    response_model=QuestionAuthoringOut,
    summary="Get question detail with version and authoring metadata",
)
async def get_question(
    question_id: str,
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuestionAuthoringOut:
    return await question_authoring_service.get_question(session, question_id)


@router.post(
    "/questions",
    response_model=QuestionAuthoringOut,
    status_code=status.HTTP_201_CREATED,
    summary="Manually author a new question draft",
)
async def create_question_draft(
    req: QuestionCreateRequest,
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuestionAuthoringOut:
    return await question_authoring_service.create_question_draft(session, req, teacher.id)


@router.put(
    "/questions/{question_id}",
    response_model=QuestionAuthoringOut,
    summary="Update or branch a new question version",
)
async def update_question(
    question_id: str,
    req: QuestionUpdateRequest,
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuestionAuthoringOut:
    return await question_authoring_service.update_question(session, question_id, req, teacher.id)


@router.post(
    "/questions/{question_id}/review",
    response_model=QuestionAuthoringOut,
    summary="Approve or reject a question draft",
)
async def review_question(
    question_id: str,
    req: QuestionReviewActionRequest,
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuestionAuthoringOut:
    return await question_authoring_service.review_question(session, question_id, req, teacher.id)


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unattempted question draft",
)
async def delete_question(
    question_id: str,
    teacher: Annotated[UserOut, Depends(require_teacher)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await question_authoring_service.delete_question(session, question_id)
