import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_teacher_intervention_recommendations(client: AsyncClient) -> None:
    headers = {"X-Demo-User-Id": "2"}  # Teacher Ms. Rao
    res = await client.get("/api/v1/teacher/classrooms/1/interventions/recommendations", headers=headers)
    assert res.status_code == 200
    recommendations = res.json()
    assert isinstance(recommendations, list)
    if recommendations:
        rec = recommendations[0]
        assert "concept_id" in rec
        assert "affected_students" in rec
        assert "activity_type" in rec
        assert "recommended_remediation" in rec


@pytest.mark.asyncio
async def test_teacher_intervention_lifecycle(client: AsyncClient) -> None:
    teacher_headers = {"X-Demo-User-Id": "2"}
    student_headers = {"X-Demo-User-Id": "1"}

    # 1. Create a draft intervention
    create_payload = {
        "concept_id": "lp-circulation",
        "title": "Double Circulation Mastery Clinic",
        "learning_gap": "Targeting systemic vs. pulmonary path confusion",
        "activity_type": "diagram_lab",
        "recommended_remediation": "Interactive heart lab tracing blood flow through ventricles and arteries.",
        "status": "draft",
    }
    create_res = await client.post(
        "/api/v1/teacher/classrooms/1/interventions",
        json=create_payload,
        headers=teacher_headers,
    )
    assert create_res.status_code == 200
    it_data = create_res.json()
    it_id = it_data["id"]
    assert it_data["status"] == "draft"

    # 2. Assign intervention to student Aarav (user_id=1)
    assign_res = await client.post(
        f"/api/v1/teacher/classrooms/1/interventions/{it_id}/assign",
        json={"student_ids": [1]},
        headers=teacher_headers,
    )
    assert assign_res.status_code == 200
    assigned_data = assign_res.json()
    assert assigned_data["status"] == "assigned"
    assert len(assigned_data["assignments"]) >= 1

    assignment_id = assigned_data["assignments"][0]["id"]

    # 3. Student fetches their active interventions
    student_res = await client.get("/api/v1/learner/interventions", headers=student_headers)
    assert student_res.status_code == 200
    my_interventions = student_res.json()
    assert any(item["intervention_id"] == it_id for item in my_interventions)

    # 4. Student completes the intervention
    comp_res = await client.post(
        f"/api/v1/learner/interventions/{assignment_id}/complete",
        headers=student_headers,
    )
    assert comp_res.status_code == 204

    # 5. Teacher checks intervention outcomes
    outcome_res = await client.get(
        f"/api/v1/teacher/classrooms/1/interventions/{it_id}/outcomes",
        headers=teacher_headers,
    )
    assert outcome_res.status_code == 200
    outcomes = outcome_res.json()
    assert outcomes["completed_count"] >= 1
    assert "outcome_summary" in outcomes

