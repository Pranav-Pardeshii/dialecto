from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.learner import ActiveMisconceptionItem, LearnerSummaryResponse


@pytest.mark.asyncio
async def test_get_learner_summary(client: AsyncClient) -> None:
    fake_summary = LearnerSummaryResponse(
        overall_mastery=0.55,
        weakest=["lp-photosynthesis", "lp-stomata"],
        due_count=2,
        active_misconceptions=[
            ActiveMisconceptionItem(
                id="m-o2-from-co2",
                statement="The oxygen released comes from carbon dioxide",
                concept_id="lp-photosynthesis",
            )
        ],
    )

    with patch(
        "app.services.learner_service.learner_service.get_summary", new_callable=AsyncMock
    ) as m_sum:
        m_sum.return_value = fake_summary
        res = await client.get("/api/v1/learner/summary", headers={"X-Demo-User-Id": "1"})
        assert res.status_code == 200
        data = res.json()
        assert data["overall_mastery"] == 0.55
        assert len(data["weakest"]) == 2
        assert len(data["active_misconceptions"]) == 1
