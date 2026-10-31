import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.models.entities import Concept
from app.schemas.concept import ConceptDetailResponse, ConceptGraphResponse, ConceptNode, ConceptEdge


@pytest.mark.asyncio
async def test_get_concepts_graph(client: AsyncClient) -> None:
    fake_response = ConceptGraphResponse(
        nodes=[
            ConceptNode(id="lp-nutrition", name="Modes of Nutrition", chapter="life-processes", position=1),
            ConceptNode(id="lp-photosynthesis", name="Photosynthesis", chapter="life-processes", position=2),
        ],
        edges=[
            ConceptEdge.model_validate({"from": "lp-nutrition", "to": "lp-photosynthesis"}),
        ],
    )

    with patch("app.services.concept_service.concept_service.get_concept_graph", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        response = await client.get("/api/v1/concepts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["from"] == "lp-nutrition"


@pytest.mark.asyncio
async def test_get_concept_detail(client: AsyncClient) -> None:
    fake_detail = ConceptDetailResponse(
        id="lp-photosynthesis",
        name="Photosynthesis",
        chapter="life-processes",
        description="Mechanism of light absorption and carbon reduction",
        lesson_md="# Photosynthesis\nPhotosynthesis converts light into chemical energy...",
        prerequisites=["lp-nutrition"],
        misconception_count=1,
    )

    with patch("app.services.concept_service.concept_service.get_concept_detail", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_detail
        response = await client.get("/api/v1/concepts/lp-photosynthesis")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "lp-photosynthesis"
        assert "lesson_md" in data
        assert "key_points" not in data  # key_points must NEVER be returned to students
