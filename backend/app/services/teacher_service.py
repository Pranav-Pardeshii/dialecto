import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.domain.sm2 import compute_effective_mastery
from app.models.entities import (
    Attempt,
    Classroom,
    Concept,
    DetectedMisconception,
    Mastery,
    Misconception,
    User,
    UserRoleEnum,
)
from app.schemas.teacher import (
    AtRiskStudentItem,
    CurriculumGapItem,
    HeatmapCellOut,
    HeatmapConceptOut,
    HeatmapStudentOut,
    MisconceptionPrevalenceItem,
    StudentAttemptBrief,
    StudentDetailResponse,
    StudentMasteryDetail,
    StudentMisconceptionDetail,
    TeacherHeatmapResponse,
)


class TeacherService:
    async def get_heatmap(
        self,
        session: AsyncSession,
        classroom_id: int,
    ) -> TeacherHeatmapResponse:
        """Generates a 30x20 effective mastery matrix for the classroom."""
        classroom = await session.get(Classroom, classroom_id)
        if not classroom:
            raise NotFoundError(f"Classroom '{classroom_id}' not found")

        # Load students
        students_stmt = (
            select(User)
            .where(User.classroom_id == classroom_id, User.role == UserRoleEnum.STUDENT)
            .order_by(User.id)
        )
        students = (await session.execute(students_stmt)).scalars().all()

        # Load concepts
        concepts_stmt = select(Concept).order_by(Concept.position)
        concepts = (await session.execute(concepts_stmt)).scalars().all()

        now = datetime.datetime.now(datetime.UTC)

        # Load masteries for these students
        student_ids = [s.id for s in students]
        masteries_stmt = select(Mastery).where(Mastery.user_id.in_(student_ids))
        masteries = (await session.execute(masteries_stmt)).scalars().all()

        mastery_lookup: dict[tuple[int, str], Mastery] = {
            (m.user_id, m.concept_id): m for m in masteries
        }

        cells: list[HeatmapCellOut] = []
        for s in students:
            for c in concepts:
                m = mastery_lookup.get((s.id, c.id))
                if m:
                    p_eff = compute_effective_mastery(m.p_mastery, m.next_due_at, now=now)
                else:
                    p_eff = c.p_l0

                cells.append(
                    HeatmapCellOut(
                        student_id=s.id,
                        concept_id=c.id,
                        p_effective=round(p_eff, 4),
                    )
                )

        return TeacherHeatmapResponse(
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            concepts=[HeatmapConceptOut(id=c.id, name=c.name, chapter=c.chapter) for c in concepts],
            students=[HeatmapStudentOut(id=s.id, display_name=s.display_name) for s in students],
            cells=cells,
        )

    async def get_curriculum_gaps(
        self,
        session: AsyncSession,
        classroom_id: int,
    ) -> list[CurriculumGapItem]:
        """Identifies concepts with lowest classroom average mastery and highest failure rates."""
        heatmap = await self.get_heatmap(session, classroom_id)
        total_students = len(heatmap.students)
        if total_students == 0:
            return []

        concept_scores: dict[str, list[float]] = {c.id: [] for c in heatmap.concepts}
        concept_meta = {c.id: c for c in heatmap.concepts}

        for cell in heatmap.cells:
            concept_scores[cell.concept_id].append(cell.p_effective)

        gaps: list[CurriculumGapItem] = []
        for c_id, scores in concept_scores.items():
            if not scores:
                continue
            mean_m = sum(scores) / len(scores)
            below_50 = sum(1 for s in scores if s < 0.50)
            pct_below_50 = (below_50 / len(scores)) * 100.0
            meta = concept_meta[c_id]

            gaps.append(
                CurriculumGapItem(
                    concept_id=c_id,
                    name=meta.name,
                    chapter=meta.chapter,
                    mean_mastery=round(mean_m, 4),
                    pct_below_50=round(pct_below_50, 1),
                    n_students=total_students,
                )
            )

        # Weakest concepts first
        gaps.sort(key=lambda x: x.mean_mastery)
        return gaps

    async def get_misconception_prevalence(
        self,
        session: AsyncSession,
        classroom_id: int,
    ) -> list[MisconceptionPrevalenceItem]:
        """Calculates most prevalent active misconceptions in the classroom."""
        students_stmt = select(User.id).where(
            User.classroom_id == classroom_id, User.role == UserRoleEnum.STUDENT
        )
        student_ids = (await session.execute(students_stmt)).scalars().all()
        if not student_ids:
            return []

        query = (
            select(
                DetectedMisconception.misconception_id,
                func.count(func.distinct(DetectedMisconception.user_id)).label("student_count"),
            )
            .where(
                DetectedMisconception.user_id.in_(student_ids),
                DetectedMisconception.resolved_at.is_(None),
            )
            .group_by(DetectedMisconception.misconception_id)
            .order_by(func.count(func.distinct(DetectedMisconception.user_id)).desc())
        )
        results = (await session.execute(query)).all()

        misc_items: list[MisconceptionPrevalenceItem] = []
        for m_id, count in results:
            misc_obj = (
                (await session.execute(select(Misconception).where(Misconception.id == m_id)))
                .scalars()
                .first()
            )

            if misc_obj:
                concept_obj = (
                    (
                        await session.execute(
                            select(Concept).where(Concept.id == misc_obj.concept_id)
                        )
                    )
                    .scalars()
                    .first()
                )
                concept_name = concept_obj.name if concept_obj else misc_obj.concept_id

                misc_items.append(
                    MisconceptionPrevalenceItem(
                        misconception_id=m_id,
                        statement=misc_obj.statement,
                        concept_id=misc_obj.concept_id,
                        concept_name=concept_name,
                        n_students=count,
                    )
                )

        return misc_items

    async def get_at_risk_students(
        self,
        session: AsyncSession,
        classroom_id: int,
    ) -> list[AtRiskStudentItem]:
        """Flags learners needing teacher intervention based on low mastery and overdue backlogs."""
        heatmap = await self.get_heatmap(session, classroom_id)
        now = datetime.datetime.now(datetime.UTC)

        student_scores: dict[int, list[float]] = {s.id: [] for s in heatmap.students}
        student_meta = {s.id: s.display_name for s in heatmap.students}

        for cell in heatmap.cells:
            student_scores[cell.student_id].append(cell.p_effective)

        # Check overdue concepts per student
        student_ids = list(student_scores.keys())
        masteries_stmt = select(Mastery).where(Mastery.user_id.in_(student_ids))
        masteries = (await session.execute(masteries_stmt)).scalars().all()

        overdue_counts: dict[int, int] = {s_id: 0 for s_id in student_ids}
        for m in masteries:
            if m.next_due_at and now > m.next_due_at:
                overdue_counts[m.user_id] = overdue_counts.get(m.user_id, 0) + 1

        # Check active misconceptions per student
        misc_stmt = (
            select(
                DetectedMisconception.user_id,
                func.count(DetectedMisconception.id).label("m_count"),
            )
            .where(
                DetectedMisconception.user_id.in_(student_ids),
                DetectedMisconception.resolved_at.is_(None),
            )
            .group_by(DetectedMisconception.user_id)
        )
        misc_counts = dict((await session.execute(misc_stmt)).all())

        at_risk: list[AtRiskStudentItem] = []
        for s_id, scores in student_scores.items():
            if not scores:
                continue
            mean_m = sum(scores) / len(scores)
            overdue = overdue_counts.get(s_id, 0)
            m_count = misc_counts.get(s_id, 0)

            # Flag if average mastery below 45% or 3+ overdue concepts or 2+ misconceptions
            if mean_m < 0.45 or overdue >= 3 or m_count >= 2:
                at_risk.append(
                    AtRiskStudentItem(
                        student_id=s_id,
                        display_name=student_meta[s_id],
                        mean_mastery=round(mean_m, 4),
                        overdue_count=overdue,
                        active_misconceptions_count=m_count,
                    )
                )

        at_risk.sort(key=lambda x: x.mean_mastery)
        return at_risk

    async def get_student_detail(
        self,
        session: AsyncSession,
        classroom_id: int,
        student_id: int,
    ) -> StudentDetailResponse:
        """Detailed drill-down for an individual student."""
        student = await session.get(User, student_id)
        if not student or student.classroom_id != classroom_id:
            raise NotFoundError(f"Student '{student_id}' not found in classroom '{classroom_id}'")

        now = datetime.datetime.now(datetime.UTC)

        concepts_stmt = select(Concept).order_by(Concept.position)
        concepts = (await session.execute(concepts_stmt)).scalars().all()

        masteries_stmt = select(Mastery).where(Mastery.user_id == student_id)
        masteries = (await session.execute(masteries_stmt)).scalars().all()
        m_map = {m.concept_id: m for m in masteries}

        mastery_details: list[StudentMasteryDetail] = []
        eff_scores: list[float] = []

        for c in concepts:
            m = m_map.get(c.id)
            if m:
                p_eff = compute_effective_mastery(m.p_mastery, m.next_due_at, now=now)
                p_mast = m.p_mastery
                next_due = m.next_due_at
            else:
                p_eff = c.p_l0
                p_mast = c.p_l0
                next_due = None

            status = "mastered" if p_eff >= 0.80 else "learning" if m else "unlocked"
            eff_scores.append(p_eff)

            mastery_details.append(
                StudentMasteryDetail(
                    concept_id=c.id,
                    concept_name=c.name,
                    p_mastery=round(p_mast, 4),
                    p_effective=round(p_eff, 4),
                    status=status,
                    next_due_at=next_due,
                )
            )

        overall_mastery = sum(eff_scores) / len(eff_scores) if eff_scores else 0.0

        # Active misconceptions
        misc_stmt = (
            select(DetectedMisconception, Misconception.statement)
            .join(Misconception, DetectedMisconception.misconception_id == Misconception.id)
            .where(
                DetectedMisconception.user_id == student_id,
                DetectedMisconception.resolved_at.is_(None),
            )
            .order_by(DetectedMisconception.created_at.desc())
        )
        misc_rows = (await session.execute(misc_stmt)).all()
        active_miscs = [
            StudentMisconceptionDetail(
                misconception_id=dm.misconception_id,
                statement=stmt,
                source=dm.source.value,
                confidence=dm.confidence,
                detected_at=dm.created_at,
            )
            for dm, stmt in misc_rows
        ]

        # Recent attempts
        attempts_stmt = (
            select(Attempt)
            .where(Attempt.user_id == student_id)
            .order_by(Attempt.created_at.desc())
            .limit(10)
        )
        attempts = (await session.execute(attempts_stmt)).scalars().all()
        recent_attempts = [
            StudentAttemptBrief(
                id=a.id,
                question_id=a.question_id,
                concept_id=a.concept_id,
                is_correct=a.is_correct,
                created_at=a.created_at,
            )
            for a in attempts
        ]

        return StudentDetailResponse(
            student_id=student.id,
            display_name=student.display_name,
            overall_mastery=round(overall_mastery, 4),
            masteries=mastery_details,
            active_misconceptions=active_miscs,
            recent_attempts=recent_attempts,
        )


teacher_service = TeacherService()
