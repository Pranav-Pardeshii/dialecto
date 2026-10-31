from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.authoring import GeneratedQuestionBatchResponse, QuestionAuthoringOut


@pytest.mark.asyncio
async def test_student_forbidden_from_authoring(client: AsyncClient) -> None:
    # Student identity Aarav (user_id=1, role=student)
    response = await client.get("/api/v1/authoring/questions", headers={"X-Demo-User-Id": "1"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_teacher_create_draft_and_approval_flow(client: AsyncClient) -> None:
    # Teacher identity Ms. Rao (user_id=2, role=teacher)
    headers = {"X-Demo-User-Id": "2"}

    # 1. Create a question draft
    create_payload = {
        "concept_id": "lp-photosynthesis",
        "kind": "mcq",
        "stem": "Which pigment absorbs light energy primarily during photosynthesis in green plants?",
        "options": [
            {"key": "A", "text": "Chlorophyll"},
            {"key": "B", "text": "Carotene"},
            {"key": "C", "text": "Anthocyanin"},
            {"key": "D", "text": "Xanthophyll"},
        ],
        "correct_key": "A",
        "explanation": "Chlorophyll in thylakoid membranes is the primary photosynthetic pigment.",
        "difficulty_bucket": 1,
        "learning_objective": "Identify primary photosynthetic pigment",
        "cognitive_skill": "recall",
    }
    create_res = await client.post("/api/v1/authoring/questions", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    q_data = create_res.json()
    qid = q_data["id"]
    assert q_data["review_status"] == "draft"
    assert q_data["verified"] is False
    assert q_data["version"] == 1

    # 2. Update the draft
    update_payload = {
        "stem": "Which pigment absorbs light energy primarily during photosynthesis in green leaves?",
        "explanation": "Chlorophyll a and b absorb light wavelengths to drive photolysis of water.",
    }
    up_res = await client.put(f"/api/v1/authoring/questions/{qid}", json=update_payload, headers=headers)
    assert up_res.status_code == 200
    updated_data = up_res.json()
    assert "green leaves" in updated_data["stem"]

    # 3. Reject action test
    rej_res = await client.post(
        f"/api/v1/authoring/questions/{qid}/review",
        json={"action": "reject", "rejection_reason": "Stem needs more clarity for CBSE exams."},
        headers=headers,
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["review_status"] == "rejected"
    assert rej_res.json()["verified"] is False

    # 4. Approve action test
    app_res = await client.post(
        f"/api/v1/authoring/questions/{qid}/review",
        json={"action": "approve"},
        headers=headers,
    )
    assert app_res.status_code == 200
    approved_data = app_res.json()
    assert approved_data["review_status"] == "approved"
    assert approved_data["verified"] is True

    # 5. Clean up
    del_res = await client.delete(f"/api/v1/authoring/questions/{qid}", headers=headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_question_validator_rejects_cross_concept_misconception(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "2"}
    # Try creating question for lp-photosynthesis with a misconception from lp-circulation ('m-arteries-oxygenated')
    invalid_payload = {
        "concept_id": "lp-photosynthesis",
        "kind": "mcq",
        "stem": "What is the primary function of stomatal guard cells during gas exchange?",
        "options": [
            {"key": "A", "text": "Regulate pore opening and closing", "misconception_id": None},
            {"key": "B", "text": "Absorb water directly from air", "misconception_id": "m-arteries-oxygenated"},
        ],
        "correct_key": "A",
        "explanation": "Guard cells swell when water flows in, opening the stomatal pore.",
        "difficulty_bucket": 2,
    }
    res = await client.post("/api/v1/authoring/questions", json=invalid_payload, headers=headers)
    assert res.status_code == 422
    assert "targets misconception" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_mocked_llm_question_generation(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "2"}
    fake_batch = GeneratedQuestionBatchResponse(
        generated=[
            QuestionAuthoringOut(
                id="gen-test-01",
                concept_id="lp-photosynthesis",
                kind="mcq",
                stem="During light-dependent reactions of photosynthesis, water molecules undergo which process?",
                options=[
                    {"key": "A", "text": "Photolysis"},
                    {"key": "B", "text": "Glycolysis"},
                    {"key": "C", "text": "Fermentation"},
                    {"key": "D", "text": "Translocation"},
                ],
                correct_key="A",
                explanation="Light energy splits water molecules into protons, electrons, and oxygen gas.",
                difficulty_bucket=2,
                difficulty_rating=0.0,
                n_attempts=0,
                verified=False,
                source="llm",
                review_status="draft",
                version=1,
            )
        ],
        validation_passed=1,
        validation_failed=0,
        errors=[],
    )

    with patch(
        "app.services.question_authoring_service.question_authoring_service.generate_questions",
        new_callable=AsyncMock,
    ) as mock_gen:
        mock_gen.return_value = fake_batch
        res = await client.post(
            "/api/v1/authoring/questions/generate",
            json={"concept_id": "lp-photosynthesis", "count": 1, "difficulty_bucket": 2},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["generated"]) == 1
        assert data["generated"][0]["review_status"] == "draft"
        assert data["validation_passed"] == 1

