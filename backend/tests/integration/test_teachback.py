import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.practice import AIFallbackMeta
from app.schemas.teachback import (
    PipTurnOut,
    RubricOut,
    TeachbackDetailResponse,
    TeachbackSessionStartResponse,
    TeachbackTranscriptTurn,
    TeachbackTurnFeedback,
    TeachbackTurnResponse,
)


@pytest.mark.asyncio
async def test_teachback_lifecycle(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "1"}
    now = datetime.datetime.now(datetime.UTC)

    fake_start_resp = TeachbackSessionStartResponse(
        id=1,
        concept_id="lp-photosynthesis",
        concept_name="Photosynthesis",
        turn_count=0,
        pip=PipTurnOut(
            content="Hi! Can you teach me how plants make food using sunlight? Where does the oxygen come from?",
            level=0,
        ),
        rubric=RubricOut(key_points=["Splitting of water (photolysis) releasing oxygen gas"]),
        finished=False,
    )

    fake_turn_resp = TeachbackTurnResponse(
        turn_index=1,
        pip=PipTurnOut(
            content="Oh, so the water gets split into oxygen? That's really clear! But where does CO2 enter?",
            level=2,
        ),
        feedback=TeachbackTurnFeedback(
            score=0.75,
            covered=["Splitting of water (photolysis) releasing oxygen gas"],
            missing=["Reduction of carbon dioxide to carbohydrates"],
            misconceptions=[],
        ),
        finished=False,
        result=None,
        ai=AIFallbackMeta(used=True, model="openai/gpt-oss-120b", fallback=False),
    )

    fake_detail_resp = TeachbackDetailResponse(
        id=1,
        concept_id="lp-photosynthesis",
        concept_name="Photosynthesis",
        turn_count=1,
        current_level=2,
        finished=False,
        final_score=None,
        turns=[
            TeachbackTranscriptTurn(
                idx=0,
                role="pip",
                content="Hi! Can you teach me?",
                level=0,
                created_at=now,
            ),
            TeachbackTranscriptTurn(
                idx=1,
                role="learner",
                content="Water splits into oxygen.",
                level=None,
                created_at=now,
            ),
        ],
    )

    with (
        patch(
            "app.services.teachback_service.teachback_service.start_session", new_callable=AsyncMock
        ) as mock_start,
        patch(
            "app.services.teachback_service.teachback_service.submit_turn", new_callable=AsyncMock
        ) as mock_turn,
        patch(
            "app.services.teachback_service.teachback_service.get_session_detail",
            new_callable=AsyncMock,
        ) as mock_detail,
    ):
        mock_start.return_value = fake_start_resp
        mock_turn.return_value = fake_turn_resp
        mock_detail.return_value = fake_detail_resp

        # 1. Start session
        start_res = await client.post(
            "/api/v1/teachback/sessions",
            json={"concept_id": "lp-photosynthesis"},
            headers=headers,
        )
        assert start_res.status_code == 200
        start_data = start_res.json()
        assert start_data["concept_id"] == "lp-photosynthesis"
        assert start_data["pip"]["level"] == 0
        assert len(start_data["rubric"]["key_points"]) > 0

        session_id = start_data["id"]

        # 2. Submit turn
        turn_res = await client.post(
            f"/api/v1/teachback/sessions/{session_id}/turns",
            json={
                "content": "Light energy splits water molecules into hydrogen and oxygen gas. This is photolysis."
            },
            headers=headers,
        )
        assert turn_res.status_code == 200
        turn_data = turn_res.json()
        assert turn_data["turn_index"] == 1
        assert turn_data["pip"]["level"] == 2
        assert "Oh, so the water gets split" in turn_data["pip"]["content"]
        assert turn_data["feedback"]["score"] == 0.75

        # 3. Get session transcript
        detail_res = await client.get(
            f"/api/v1/teachback/sessions/{session_id}",
            headers=headers,
        )
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["id"] == session_id
        assert detail_data["current_level"] == 2
        assert len(detail_data["turns"]) == 2
