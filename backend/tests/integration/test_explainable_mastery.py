import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_student_concept_explainable_mastery(client: AsyncClient) -> None:
    # Student Aarav
    res = await client.get(
        "/api/v1/learner/concepts/lp-photosynthesis/explainable",
        headers={"X-Demo-User-Id": "1"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["concept_id"] == "lp-photosynthesis"
    assert "p_mastery" in data
    assert "evidence_strength" in data
    assert data["evidence_strength"] in ("insufficient", "low", "moderate", "high")
    assert "assessment_breakdown" in data
    assert "narrative" in data
    assert "timeline" in data
    assert isinstance(data["timeline"], list)


@pytest.mark.asyncio
async def test_teacher_can_inspect_student_explainable_mastery(client: AsyncClient) -> None:
    # Teacher Ms. Rao (user_id=2) inspecting student Aarav (user_id=1) in classroom 1
    res = await client.get(
        "/api/v1/teacher/classrooms/1/students/1/concepts/lp-photosynthesis/explainable",
        headers={"X-Demo-User-Id": "2"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["concept_id"] == "lp-photosynthesis"
    assert "timeline" in data
    assert len(data["narrative"]) > 10


@pytest.mark.asyncio
async def test_untested_concept_returns_insufficient_or_low_evidence(client: AsyncClient) -> None:
    # Concept he-sex-determination for student Aarav
    res = await client.get(
        "/api/v1/learner/concepts/he-sex-determination/explainable",
        headers={"X-Demo-User-Id": "1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["concept_id"] == "he-sex-determination"
    assert data["evidence_strength"] in ("insufficient", "low")

