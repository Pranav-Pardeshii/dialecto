import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.diagnostic import (
    DiagnosticAnswerResponse,
    DiagnosticProgress,
    DiagnosticStartResponse,
)
from app.schemas.practice import QuestionOptionOut, QuestionOut


@pytest.mark.asyncio
async def test_diagnostic_flow(client: AsyncClient) -> None:
    fake_start = DiagnosticStartResponse(
        session_id=10,
        question=QuestionOut(
            id="q-lp-nutrition-01",
            concept_id="lp-nutrition",
            stem="Which organism exhibits saprophytic nutrition?",
            options=[
                QuestionOptionOut(key="A", text="Mushroom"),
                QuestionOptionOut(key="B", text="Amoeba"),
            ],
            difficulty_bucket=1,
        ),
        progress=DiagnosticProgress(answered=0, total=15),
    )

    fake_ans = DiagnosticAnswerResponse(
        is_correct=True,
        next_question=QuestionOut(
            id="q-lp-photosynthesis-01",
            concept_id="lp-photosynthesis",
            stem="Next question",
            options=[QuestionOptionOut(key="A", text="Option A")],
            difficulty_bucket=2,
        ),
        progress=DiagnosticProgress(answered=1, total=15),
        result=None,
    )

    with (
        patch(
            "app.services.diagnostic_service.diagnostic_service.start_session",
            new_callable=AsyncMock,
        ) as m_start,
        patch(
            "app.services.diagnostic_service.diagnostic_service.submit_answer",
            new_callable=AsyncMock,
        ) as m_ans,
    ):
        m_start.return_value = fake_start
        m_ans.return_value = fake_ans

        # Start
        start_res = await client.post(
            "/api/v1/diagnostic/sessions", headers={"X-Demo-User-Id": "1"}
        )
        assert start_res.status_code == 200
        assert start_res.json()["session_id"] == 10

        # Answer
        ans_res = await client.post(
            "/api/v1/diagnostic/sessions/10/answers",
            json={
                "client_attempt_id": str(uuid.uuid4()),
                "question_id": "q-lp-nutrition-01",
                "selected_key": "A",
                "response_ms": 9000,
            },
            headers={"X-Demo-User-Id": "1"},
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["progress"]["answered"] == 1
