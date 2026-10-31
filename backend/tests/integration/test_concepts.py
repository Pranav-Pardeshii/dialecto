from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.entities import Mastery, User, UserRoleEnum
from app.schemas.concept import (
    ConceptDetailResponse,
    ConceptEdge,
    ConceptGraphResponse,
    ConceptNode,
)
from app.schemas.user import UserOut, UserRole
from app.services.concept_service import concept_service


@pytest.mark.asyncio
async def test_get_concepts_graph(client: AsyncClient) -> None:
    fake_response = ConceptGraphResponse(
        nodes=[
            ConceptNode(
                id="lp-nutrition", name="Modes of Nutrition", chapter="life-processes", position=1
            ),
            ConceptNode(
                id="lp-photosynthesis", name="Photosynthesis", chapter="life-processes", position=2
            ),
        ],
        edges=[
            ConceptEdge.model_validate({"from": "lp-nutrition", "to": "lp-photosynthesis"}),
        ],
    )

    with patch(
        "app.services.concept_service.concept_service.get_concept_graph", new_callable=AsyncMock
    ) as mock_get:
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

    with patch(
        "app.services.concept_service.concept_service.get_concept_detail", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = fake_detail
        response = await client.get("/api/v1/concepts/lp-photosynthesis")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "lp-photosynthesis"
        assert "lesson_md" in data
        assert "key_points" not in data  # key_points must NEVER be returned to students


@pytest.mark.asyncio
async def test_concept_graph_fresh_student_status_logic() -> None:
    """Verifies that for a fresh student (0 attempts):

    - Root concepts are accessible with status 'ready'.
    - Dependent concepts are 'locked' with an authentic lock reason explaining the unmet prerequisite.
    """
    student = UserOut(
        id=999, display_name="Test Student", role=UserRole.STUDENT, is_simulated=False, classroom_id=1
    )

    async with async_session_factory() as session:
        graph = await concept_service.get_concept_graph(session, current_user=student)
        nodes_by_id = {node.id: node for node in graph.nodes}

        # Root concepts without prerequisites must be 'ready', never 'locked'
        root_ids = ["lp-nutrition", "cc-neuron", "cc-plant-hormones", "cc-animal-hormones", "he-variation"]
        for rid in root_ids:
            node = nodes_by_id[rid]
            assert node.mastery is not None
            assert node.mastery.status == "ready", f"Root concept {rid} should be 'ready', got {node.mastery.status}"
            assert node.mastery.lock_reason is None
            assert node.mastery.p_effective == 0.0

        # Dependent concept 'lp-photosynthesis' requires 'lp-nutrition'
        photo_node = nodes_by_id["lp-photosynthesis"]
        assert photo_node.mastery is not None
        assert photo_node.mastery.status == "locked"
        assert photo_node.mastery.lock_reason is not None
        assert "Modes of Nutrition requires 60% prerequisite mastery" in photo_node.mastery.lock_reason
        assert "Modes of Nutrition" in photo_node.mastery.unmet_prerequisites


@pytest.mark.asyncio
async def test_concept_graph_satisfied_prerequisite_unlocks() -> None:
    """Verifies that satisfying a prerequisite unlocks dependent concepts."""
    student_id = 998
    student = UserOut(
        id=student_id, display_name="Advanced Student", role=UserRole.STUDENT, is_simulated=False, classroom_id=1
    )

    async with async_session_factory() as session:
        async with session.begin():
            existing_user = await session.get(User, student_id)
            if not existing_user:
                session.add(
                    User(
                        id=student_id,
                        display_name="Advanced Student",
                        role=UserRoleEnum.STUDENT,
                        classroom_id=1,
                        is_simulated=False,
                    )
                )
                await session.flush()

            # Give student 75% mastery on lp-nutrition with 3 attempts
            m_row = await session.get(Mastery, (student_id, "lp-nutrition"))
            if not m_row:
                m_row = Mastery(
                    user_id=student_id,
                    concept_id="lp-nutrition",
                    p_mastery=0.75,
                    attempts=3,
                    correct=3,
                    version=1,
                )
                session.add(m_row)
            else:
                m_row.p_mastery = 0.75
                m_row.attempts = 3
                m_row.correct = 3

        graph = await concept_service.get_concept_graph(session, current_user=student)
        nodes_by_id = {node.id: node for node in graph.nodes}

        # lp-nutrition should be 'learning' (0.75 < 0.80)
        nut_node = nodes_by_id["lp-nutrition"]
        assert nut_node.mastery is not None
        assert nut_node.mastery.status == "learning"

        # lp-photosynthesis and lp-digestion should now be unlocked ('ready')
        photo_node = nodes_by_id["lp-photosynthesis"]
        assert photo_node.mastery is not None
        assert photo_node.mastery.status == "ready"
        assert photo_node.mastery.lock_reason is None
        assert len(photo_node.mastery.unmet_prerequisites) == 0

        digestion_node = nodes_by_id["lp-digestion"]
        assert digestion_node.mastery is not None
        assert digestion_node.mastery.status == "ready"
