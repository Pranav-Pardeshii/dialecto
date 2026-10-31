from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.teacher import (
    AtRiskStudentItem,
    CurriculumGapItem,
    HeatmapCellOut,
    HeatmapConceptOut,
    HeatmapStudentOut,
    MisconceptionPrevalenceItem,
    StudentDetailResponse,
    StudentMasteryDetail,
    TeacherHeatmapResponse,
)


@pytest.mark.asyncio
async def test_teacher_role_enforcement(client: AsyncClient) -> None:
    # User 1 is student Aarav -> Should return 403 Forbidden
    res = await client.get("/api/v1/teacher/classrooms/1/heatmap", headers={"X-Demo-User-Id": "1"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_teacher_heatmap(client: AsyncClient) -> None:
    fake_heatmap = TeacherHeatmapResponse(
        classroom_id=1,
        classroom_name="Class 10-A Biology",
        concepts=[
            HeatmapConceptOut(
                id="lp-photosynthesis", name="Photosynthesis", chapter="life-processes"
            )
        ],
        students=[HeatmapStudentOut(id=1, display_name="Aarav")],
        cells=[HeatmapCellOut(student_id=1, concept_id="lp-photosynthesis", p_effective=0.72)],
    )

    with patch(
        "app.services.teacher_service.teacher_service.get_heatmap", new_callable=AsyncMock
    ) as mock_hm:
        mock_hm.return_value = fake_heatmap
        # User 2 is teacher Ms. Rao
        res = await client.get(
            "/api/v1/teacher/classrooms/1/heatmap", headers={"X-Demo-User-Id": "2"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["classroom_id"] == 1
        assert len(data["concepts"]) == 1
        assert len(data["students"]) == 1
        assert len(data["cells"]) == 1


@pytest.mark.asyncio
async def test_teacher_gaps(client: AsyncClient) -> None:
    fake_gaps = [
        CurriculumGapItem(
            concept_id="lp-photosynthesis",
            name="Photosynthesis",
            chapter="life-processes",
            mean_mastery=0.45,
            pct_below_50=65.0,
            n_students=30,
        )
    ]

    with patch(
        "app.services.teacher_service.teacher_service.get_curriculum_gaps", new_callable=AsyncMock
    ) as mock_gaps:
        mock_gaps.return_value = fake_gaps
        res = await client.get("/api/v1/teacher/classrooms/1/gaps", headers={"X-Demo-User-Id": "2"})
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["mean_mastery"] == 0.45


@pytest.mark.asyncio
async def test_teacher_misconceptions(client: AsyncClient) -> None:
    fake_miscs = [
        MisconceptionPrevalenceItem(
            misconception_id="mis-lp-photo-01",
            statement="Oxygen released during photosynthesis comes from carbon dioxide",
            concept_id="lp-photosynthesis",
            concept_name="Photosynthesis",
            n_students=12,
        )
    ]

    with patch(
        "app.services.teacher_service.teacher_service.get_misconception_prevalence",
        new_callable=AsyncMock,
    ) as mock_m:
        mock_m.return_value = fake_miscs
        res = await client.get(
            "/api/v1/teacher/classrooms/1/misconceptions", headers={"X-Demo-User-Id": "2"}
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["n_students"] == 12


@pytest.mark.asyncio
async def test_teacher_at_risk(client: AsyncClient) -> None:
    fake_risk = [
        AtRiskStudentItem(
            student_id=5,
            display_name="Rohan Gupta",
            mean_mastery=0.36,
            overdue_count=4,
            active_misconceptions_count=2,
        )
    ]

    with patch(
        "app.services.teacher_service.teacher_service.get_at_risk_students", new_callable=AsyncMock
    ) as mock_risk:
        mock_risk.return_value = fake_risk
        res = await client.get(
            "/api/v1/teacher/classrooms/1/at-risk", headers={"X-Demo-User-Id": "2"}
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["overdue_count"] == 4


@pytest.mark.asyncio
async def test_teacher_student_drilldown(client: AsyncClient) -> None:
    fake_detail = StudentDetailResponse(
        student_id=5,
        display_name="Rohan Gupta",
        overall_mastery=0.36,
        masteries=[
            StudentMasteryDetail(
                concept_id="lp-photosynthesis",
                concept_name="Photosynthesis",
                p_mastery=0.35,
                p_effective=0.30,
                status="learning",
                next_due_at=None,
            )
        ],
        active_misconceptions=[],
        recent_attempts=[],
    )

    with patch(
        "app.services.teacher_service.teacher_service.get_student_detail", new_callable=AsyncMock
    ) as mock_dtl:
        mock_dtl.return_value = fake_detail
        res = await client.get(
            "/api/v1/teacher/classrooms/1/students/5", headers={"X-Demo-User-Id": "2"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["student_id"] == 5
        assert data["display_name"] == "Rohan Gupta"
