import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.review import ReviewDueItem


@pytest.mark.asyncio
async def test_get_due_reviews(client: AsyncClient) -> None:
    now = datetime.datetime.now(datetime.UTC)
    fake_due = [
        ReviewDueItem(
            concept_id="lp-photosynthesis",
            name="Photosynthesis",
            chapter="life-processes",
            p_effective=0.55,
            days_overdue=3,
            next_due_at=now - datetime.timedelta(days=3),
        ),
        ReviewDueItem(
            concept_id="cr-reflex",
            name="Reflex Actions",
            chapter="control-coordination",
            p_effective=0.48,
            days_overdue=1,
            next_due_at=now - datetime.timedelta(days=1),
        ),
    ]

    with patch(
        "app.services.review_service.review_service.get_due_reviews", new_callable=AsyncMock
    ) as mock_due:
        mock_due.return_value = fake_due
        res = await client.get("/api/v1/reviews/due", headers={"X-Demo-User-Id": "1"})
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["concept_id"] == "lp-photosynthesis"
        assert data[0]["days_overdue"] == 3
