import datetime
from collections import defaultdict

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
        """Generates dynamic student-concept effective mastery matrix for the classroom."""
        classroom = await session.get(Classroom, classroom_id)
        if not classroom:
            raise NotFoundError(f"Classroom '{classroom_id}' not found")

        # Load students belonging strictly to this classroom
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
        mastery_lookup: dict[tuple[int, str], Mastery] = {}
        if student_ids:
            masteries_stmt = select(Mastery).where(Mastery.user_id.in_(student_ids))
            masteries = (await session.execute(masteries_stmt)).scalars().all()
            mastery_lookup = {(m.user_id, m.concept_id): m for m in masteries}

        cells: list[HeatmapCellOut] = []
        for s in students:
            for c in concepts:
                m = mastery_lookup.get((s.id, c.id))
                if m and m.attempts > 0:
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
        """Calculates most prevalent active misconceptions in the classroom using single efficient join query."""
        students_stmt = select(User.id).where(
            User.classroom_id == classroom_id, User.role == UserRoleEnum.STUDENT
        )
        student_ids = (await session.execute(students_stmt)).scalars().all()
        if not student_ids:
            return []

        # Single aggregated query eliminating N+1 DB round trips
        query = (
            select(
                DetectedMisconception.misconception_id,
                Misconception.statement,
                Misconception.concept_id,
                Concept.name.label("concept_name"),
                func.count(func.distinct(DetectedMisconception.user_id)).label("student_count"),
            )
            .join(Misconception, DetectedMisconception.misconception_id == Misconception.id)
            .join(Concept, Misconception.concept_id == Concept.id)
            .where(
                DetectedMisconception.user_id.in_(student_ids),
                DetectedMisconception.resolved_at.is_(None),
            )
            .group_by(
                DetectedMisconception.misconception_id,
                Misconception.statement,
                Misconception.concept_id,
                Concept.name,
            )
            .order_by(func.count(func.distinct(DetectedMisconception.user_id)).desc())
        )
        results = (await session.execute(query)).all()

        misc_items: list[MisconceptionPrevalenceItem] = []
        for m_id, statement, c_id, c_name, count in results:
            misc_items.append(
                MisconceptionPrevalenceItem(
                    misconception_id=m_id,
                    statement=statement,
                    concept_id=c_id,
                    concept_name=c_name,
                    n_students=count,
                )
            )

        return misc_items

    async def get_at_risk_students(
        self,
        session: AsyncSession,
        classroom_id: int,
    ) -> list[AtRiskStudentItem]:
        """Flags learners needing teacher intervention based on low mastery, overdue backlogs, or active misconceptions."""
        now = datetime.datetime.now(datetime.UTC)

        # 1. Load classroom students
        students_stmt = (
            select(User)
            .where(User.classroom_id == classroom_id, User.role == UserRoleEnum.STUDENT)
            .order_by(User.id)
        )
        students = (await session.execute(students_stmt)).scalars().all()
        if not students:
            return []

        student_ids = [s.id for s in students]

        # 2. Load masteries for these students
        masteries_stmt = select(Mastery).where(Mastery.user_id.in_(student_ids))
        masteries = (await session.execute(masteries_stmt)).scalars().all()

        masteries_by_student: dict[int, list[Mastery]] = defaultdict(list)
        for m in masteries:
            masteries_by_student[m.user_id].append(m)

        # 3. Count distinct active misconceptions per student
        misc_stmt = (
            select(
                DetectedMisconception.user_id,
                func.count(func.distinct(DetectedMisconception.misconception_id)).label("m_count"),
            )
            .where(
                DetectedMisconception.user_id.in_(student_ids),
                DetectedMisconception.resolved_at.is_(None),
            )
            .group_by(DetectedMisconception.user_id)
        )
        misc_counts = dict((await session.execute(misc_stmt)).all())

        at_risk: list[AtRiskStudentItem] = []
        for s in students:
            s_masteries = masteries_by_student.get(s.id, [])
            # Only compute mean across concepts the student has actually attempted
            attempted_scores = [
                compute_effective_mastery(m.p_mastery, m.next_due_at, now=now)
                for m in s_masteries
                if m.attempts > 0
            ]

            mean_m = (
                round(sum(attempted_scores) / len(attempted_scores), 4)
                if attempted_scores
                else 0.30
            )

            overdue_count = sum(1 for m in s_masteries if m.next_due_at and now > m.next_due_at)
            distinct_misc_count = misc_counts.get(s.id, 0)

            # Flag if average measured mastery below 45% or 3+ overdue reviews or 2+ distinct active misconceptions
            if (attempted_scores and mean_m < 0.45) or overdue_count >= 3 or distinct_misc_count >= 2:
                at_risk.append(
                    AtRiskStudentItem(
                        student_id=s.id,
                        display_name=s.display_name,
                        mean_mastery=mean_m,
                        overdue_count=overdue_count,
                        active_misconceptions_count=distinct_misc_count,
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
        attempted_scores: list[float] = []

        for c in concepts:
            m = m_map.get(c.id)
            if m and m.attempts > 0:
                p_eff = compute_effective_mastery(m.p_mastery, m.next_due_at, now=now)
                p_mast = m.p_mastery
                next_due = m.next_due_at
                status = "mastered" if p_eff >= 0.80 else "learning"
                attempted_scores.append(p_eff)
            else:
                p_eff = c.p_l0
                p_mast = c.p_l0
                next_due = None
                status = "untested"

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

        overall_mastery = (
            sum(attempted_scores) / len(attempted_scores) if attempted_scores else 0.0
        )

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
