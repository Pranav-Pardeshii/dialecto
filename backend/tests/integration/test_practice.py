import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.practice import (
    AIFallbackMeta,
    MasteryDelta,
    PracticeAnswerResponse,
    PracticeNextResponse,
    QuestionOptionOut,
    QuestionOut,
)


@pytest.mark.asyncio
async def test_get_next_practice_question(client: AsyncClient) -> None:
    fake_resp = PracticeNextResponse(
        session_id=1,
        question=QuestionOut(
            id="q-lp-photosynthesis-01",
            concept_id="lp-photosynthesis",
            stem="During photosynthesis, which molecule yields oxygen?",
            options=[
                QuestionOptionOut(key="A", text="Carbon dioxide"),
                QuestionOptionOut(key="B", text="Water"),
            ],
            difficulty_bucket=2,
        ),
        selection_reason="Targeting weak concept at optimal difficulty.",
    )

    with patch(
        "app.services.practice_service.practice_service.get_next_question", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = fake_resp
        response = await client.post(
            "/api/v1/practice/next",
            json={"mode": "adaptive"},
            headers={"X-Demo-User-Id": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"]["id"] == "q-lp-photosynthesis-01"
        assert "selection_reason" in data


@pytest.mark.asyncio
async def test_submit_practice_answer(client: AsyncClient) -> None:
    client_attempt_id = str(uuid.uuid4())
    fake_answer_resp = PracticeAnswerResponse(
        is_correct=True,
        correct_key="B",
        explanation="Oxygen is released from the photolysis of water.",
        mastery=MasteryDelta(
            concept_id="lp-photosynthesis",
            before=0.30,
            after=0.66,
            status="learning",
        ),
        misconception=None,
        ai=AIFallbackMeta(used=False),
        newly_unlocked=["lp-stomata"],
    )

    with patch(
        "app.services.practice_service.practice_service.submit_answer", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = fake_answer_resp
        response = await client.post(
            "/api/v1/practice/answers",
            json={
                "client_attempt_id": client_attempt_id,
                "session_id": 1,
                "question_id": "q-lp-photosynthesis-01",
                "selected_key": "B",
                "reasoning": "Photolysis of water splits H2O into oxygen.",
                "response_ms": 12000,
            },
            headers={"X-Demo-User-Id": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is True
        assert data["mastery"]["after"] == 0.66
