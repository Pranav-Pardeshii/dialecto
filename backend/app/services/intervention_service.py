import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.domain.explainable_mastery import calculate_evidence_strength
from app.models.entities import (
    Concept,
    DetectedMisconception,
    Intervention,
    InterventionActivityTypeEnum,
    InterventionAssignment,
    InterventionAssignmentStatusEnum,
    InterventionStatusEnum,
    Mastery,
    Misconception,
    User,
    UserRoleEnum,
)
from app.schemas.intervention import (
    AffectedStudentOut,
    InterventionAssignmentOut,
    InterventionCreateRequest,
    InterventionDetailOut,
    InterventionOutcomesResponse,
    InterventionRecommendationOut,
    StudentInterventionItemOut,
)


class InterventionService:
    async def get_recommendations(
        self, session: AsyncSession, classroom_id: int
    ) -> list[InterventionRecommendationOut]:
        """Analyzes real classroom data to identify learning gaps and suggest targeted interventions."""
        # 1. Fetch students in this classroom
        students_stmt = select(User).where(
            User.classroom_id == classroom_id, User.role == UserRoleEnum.STUDENT
        )
        students_res = await session.execute(students_stmt)
        students = list(students_res.scalars().all())
        if not students:
            return []

        student_ids = [s.id for s in students]
        student_map = {s.id: s.display_name for s in students}
        recommendations: list[InterventionRecommendationOut] = []

        # 2. Find common active misconceptions across classroom
        misc_stmt = (
            select(
                Misconception.id,
                Misconception.statement,
                Misconception.concept_id,
                Concept.name.label("concept_name"),
                Concept.chapter,
                func.count(func.distinct(DetectedMisconception.user_id)).label("student_count"),
            )
            .join(Misconception, DetectedMisconception.misconception_id == Misconception.id)
            .join(Concept, Misconception.concept_id == Concept.id)
            .where(
                DetectedMisconception.user_id.in_(student_ids),
                DetectedMisconception.resolved_at.is_(None),
            )
            .group_by(
                Misconception.id,
                Misconception.statement,
                Misconception.concept_id,
                Concept.name,
                Concept.chapter,
            )
            .having(func.count(func.distinct(DetectedMisconception.user_id)) >= 2)
            .order_by(desc("student_count"))
            .limit(3)
        )
        misc_res = await session.execute(misc_stmt)
        common_miscs = misc_res.all()

        for m_id, m_stmt, c_id, c_name, chapter, s_count in common_miscs:
            # Get affected students
            aff_stmt = (
                select(DetectedMisconception.user_id)
                .where(
                    DetectedMisconception.misconception_id == m_id,
                    DetectedMisconception.user_id.in_(student_ids),
                    DetectedMisconception.resolved_at.is_(None),
                )
                .distinct()
            )
            aff_res = await session.execute(aff_stmt)
            aff_uids = list(aff_res.scalars().all())

            affected_list: list[AffectedStudentOut] = []
            for uid in aff_uids:
                mst_stmt = select(Mastery).where(Mastery.user_id == uid, Mastery.concept_id == c_id)
                mst_res = await session.execute(mst_stmt)
                m = mst_res.scalars().first()
                p_mst = m.p_mastery if m else 0.30
                attempts = m.attempts if m else 0
                strength, _ = calculate_evidence_strength(attempts)
                affected_list.append(
                    AffectedStudentOut(
                        id=uid,
                        display_name=student_map.get(uid, f"Student {uid}"),
                        baseline_mastery=p_mst,
                        evidence_strength=strength,
                    )
                )

            # Choose activity: anatomical concepts benefit from diagram lab
            act_type = "practice"
            if c_id in ("lp-circulation", "lp-excretion", "lp-respiration"):
                act_type = "diagram_lab"
            elif s_count >= 5:
                act_type = "teachback"

            recommendations.append(
                InterventionRecommendationOut(
                    concept_id=c_id,
                    concept_name=c_name,
                    chapter=chapter,
                    title=f"Misconception Clinic: {m_stmt[:48]}...",
                    learning_gap=f"{s_count} students exhibit active misconception: '{m_stmt}'",
                    target_misconception_id=m_id,
                    target_misconception_statement=m_stmt,
                    affected_student_count=len(affected_list),
                    affected_students=affected_list,
                    activity_type=act_type,
                    recommended_remediation=f"Targeted review contrasting the misconception with biological evidence from {c_name}.",
                    suggested_duration_mins=15,
                    reason=f"High prevalence ({round(s_count / len(students) * 100)}% of class) of misconception {m_id}.",
                )
            )

        # 3. Find concepts with low mastery (<0.50) and at least 3 struggling students
        gap_stmt = (
            select(
                Mastery.concept_id,
                Concept.name,
                Concept.chapter,
                func.count(Mastery.user_id).label("low_count"),
                func.avg(Mastery.p_mastery).label("avg_mastery"),
            )
            .join(Concept, Mastery.concept_id == Concept.id)
            .where(
                Mastery.user_id.in_(student_ids),
                Mastery.attempts > 0,
                Mastery.p_mastery < 0.50,
            )
            .group_by(Mastery.concept_id, Concept.name, Concept.chapter)
            .having(func.count(Mastery.user_id) >= 3)
            .order_by(desc("low_count"), "avg_mastery")
            .limit(3)
        )
        gap_res = await session.execute(gap_stmt)
        gap_rows = gap_res.all()

        for c_id, c_name, chapter, low_count, avg_m in gap_rows:
            # Skip if already in recommendations
            if any(r.concept_id == c_id for r in recommendations):
                continue

            gap_aff_stmt = select(Mastery).where(
                Mastery.user_id.in_(student_ids),
                Mastery.concept_id == c_id,
                Mastery.p_mastery < 0.50,
            )
            gap_aff_res = await session.execute(gap_aff_stmt)
            aff_masteries = list(gap_aff_res.scalars().all())

            affected_list = []
            for mst_item in aff_masteries:
                strength, _ = calculate_evidence_strength(mst_item.attempts)
                affected_list.append(
                    AffectedStudentOut(
                        id=mst_item.user_id,
                        display_name=student_map.get(mst_item.user_id, f"Student {mst_item.user_id}"),
                        baseline_mastery=mst_item.p_mastery,
                        evidence_strength=strength,
                    )
                )

            act_type = "diagram_lab" if c_id in ("lp-circulation", "lp-excretion") else "practice"

            recommendations.append(
                InterventionRecommendationOut(
                    concept_id=c_id,
                    concept_name=c_name,
                    chapter=chapter,
                    title=f"Core Concept Remediation: {c_name}",
                    learning_gap=f"{low_count} students have tested below proficiency (<50% mastery, average {round(float(avg_m or 0) * 100)}%).",
                    target_misconception_id=None,
                    target_misconception_statement=None,
                    affected_student_count=len(affected_list),
                    affected_students=affected_list,
                    activity_type=act_type,
                    recommended_remediation=f"Structured scaffolded practice targeting foundational NCERT principles for {c_name}.",
                    suggested_duration_mins=20,
                    reason=f"Curriculum bottleneck: Class average mastery is {round(float(avg_m or 0) * 100)}%.",
                )
            )

        return recommendations

    async def create_intervention(
        self, session: AsyncSession, classroom_id: int, teacher_id: int, req: InterventionCreateRequest
    ) -> InterventionDetailOut:
        concept_stmt = select(Concept).where(Concept.id == req.concept_id)
        concept_res = await session.execute(concept_stmt)
        concept = concept_res.scalars().first()
        if not concept:
            raise NotFoundError(f"Concept '{req.concept_id}' not found.")

        # Map activity enum
        act_enum = InterventionActivityTypeEnum.PRACTICE
        try:
            act_enum = InterventionActivityTypeEnum(req.activity_type)
        except ValueError:
            pass

        # Map status enum
        status_enum = InterventionStatusEnum.DRAFT
        try:
            status_enum = InterventionStatusEnum(req.status)
        except ValueError:
            pass

        intervention = Intervention(
            teacher_id=teacher_id,
            classroom_id=classroom_id,
            concept_id=req.concept_id,
            title=req.title,
            learning_gap=req.learning_gap,
            target_misconception_id=req.target_misconception_id,
            activity_type=act_enum,
            recommended_remediation=req.recommended_remediation,
            status=status_enum,
        )
        session.add(intervention)
        await session.commit()
        await session.refresh(intervention)
        return await self.get_intervention_detail(session, classroom_id, intervention.id)

    async def list_interventions(
        self, session: AsyncSession, classroom_id: int, status_filter: str | None = None
    ) -> list[InterventionDetailOut]:
        stmt = (
            select(Intervention)
            .where(Intervention.classroom_id == classroom_id)
            .order_by(desc(Intervention.created_at))
        )
        if status_filter:
            stmt = stmt.where(Intervention.status == status_filter)

        res = await session.execute(stmt)
        interventions = list(res.scalars().all())

        results: list[InterventionDetailOut] = []
        for it in interventions:
            detail = await self.get_intervention_detail(session, classroom_id, it.id)
            results.append(detail)
        return results

    async def get_intervention_detail(
        self, session: AsyncSession, classroom_id: int, intervention_id: int
    ) -> InterventionDetailOut:
        stmt = select(Intervention).where(
            Intervention.id == intervention_id, Intervention.classroom_id == classroom_id
        )
        res = await session.execute(stmt)
        it = res.scalars().first()
        if not it:
            raise NotFoundError(f"Intervention #{intervention_id} not found.")

        concept_stmt = select(Concept.name).where(Concept.id == it.concept_id)
        c_res = await session.execute(concept_stmt)
        c_name = c_res.scalar_one_or_none() or it.concept_id

        # Fetch assignments
        assign_stmt = (
            select(InterventionAssignment, User.display_name)
            .join(User, InterventionAssignment.user_id == User.id)
            .where(InterventionAssignment.intervention_id == intervention_id)
            .order_by(InterventionAssignment.assigned_at.desc())
        )
        assign_res = await session.execute(assign_stmt)
        assign_rows = assign_res.all()

        assignments_out: list[InterventionAssignmentOut] = []
        completed_count = 0
        for ia, uname in assign_rows:
            if ia.status == InterventionAssignmentStatusEnum.COMPLETED:
                completed_count += 1
            assignments_out.append(
                InterventionAssignmentOut(
                    id=ia.id,
                    intervention_id=ia.intervention_id,
                    user_id=ia.user_id,
                    student_name=uname,
                    baseline_mastery=ia.baseline_mastery,
                    post_mastery=ia.post_mastery,
                    baseline_evidence_strength=ia.baseline_evidence_strength,
                    post_evidence_strength=ia.post_evidence_strength,
                    status=str(ia.status.value if hasattr(ia.status, "value") else ia.status),
                    assigned_at=ia.assigned_at,
                    completed_at=ia.completed_at,
                )
            )

        return InterventionDetailOut(
            id=it.id,
            teacher_id=it.teacher_id,
            classroom_id=it.classroom_id,
            concept_id=it.concept_id,
            concept_name=c_name,
            title=it.title,
            learning_gap=it.learning_gap,
            target_misconception_id=it.target_misconception_id,
            activity_type=str(it.activity_type.value if hasattr(it.activity_type, "value") else it.activity_type),
            recommended_remediation=it.recommended_remediation,
            status=str(it.status.value if hasattr(it.status, "value") else it.status),
            created_at=it.created_at,
            updated_at=it.updated_at,
            total_assigned=len(assignments_out),
            completed_count=completed_count,
            assignments=assignments_out,
        )

    async def assign_intervention(
        self,
        session: AsyncSession,
        classroom_id: int,
        intervention_id: int,
        student_ids: list[int],
    ) -> InterventionDetailOut:
        """Assigns students to an intervention with their baseline mastery and evidence strength."""
        stmt = select(Intervention).where(
            Intervention.id == intervention_id, Intervention.classroom_id == classroom_id
        )
        res = await session.execute(stmt)
        it = res.scalars().first()
        if not it:
            raise NotFoundError(f"Intervention #{intervention_id} not found.")

        if not student_ids:
            raise BadRequestError("At least one student must be selected for assignment.")

        # Update intervention status
        it.status = InterventionStatusEnum.ASSIGNED
        it.updated_at = datetime.datetime.now(datetime.UTC)

        for uid in student_ids:
            # Check existing assignment
            chk_stmt = select(InterventionAssignment).where(
                InterventionAssignment.intervention_id == intervention_id,
                InterventionAssignment.user_id == uid,
            )
            chk_res = await session.execute(chk_stmt)
            existing = chk_res.scalars().first()
            if existing:
                continue

            # Look up baseline mastery
            mst_stmt = select(Mastery).where(
                Mastery.user_id == uid, Mastery.concept_id == it.concept_id
            )
            mst_res = await session.execute(mst_stmt)
            m = mst_res.scalars().first()
            b_mst = m.p_mastery if m else 0.30
            b_attempts = m.attempts if m else 0
            b_strength, _ = calculate_evidence_strength(b_attempts)

            assignment = InterventionAssignment(
                intervention_id=intervention_id,
                user_id=uid,
                baseline_mastery=b_mst,
                baseline_evidence_strength=b_strength,
                status=InterventionAssignmentStatusEnum.ASSIGNED,
            )
            session.add(assignment)

        await session.commit()
        return await self.get_intervention_detail(session, classroom_id, intervention_id)

    async def get_student_interventions(
        self, session: AsyncSession, user_id: int
    ) -> list[StudentInterventionItemOut]:
        """Fetches active assigned interventions for the current student."""
        stmt = (
            select(InterventionAssignment, Intervention, Concept.name)
            .join(Intervention, InterventionAssignment.intervention_id == Intervention.id)
            .join(Concept, Intervention.concept_id == Concept.id)
            .where(
                InterventionAssignment.user_id == user_id,
                InterventionAssignment.status.in_([
                    InterventionAssignmentStatusEnum.ASSIGNED,
                    InterventionAssignmentStatusEnum.IN_PROGRESS,
                ]),
            )
            .order_by(InterventionAssignment.assigned_at.desc())
        )
        res = await session.execute(stmt)
        rows = res.all()

        results: list[StudentInterventionItemOut] = []
        for ia, it, c_name in rows:
            results.append(
                StudentInterventionItemOut(
                    assignment_id=ia.id,
                    intervention_id=it.id,
                    concept_id=it.concept_id,
                    concept_name=c_name,
                    title=it.title,
                    learning_gap=it.learning_gap,
                    activity_type=str(it.activity_type.value if hasattr(it.activity_type, "value") else it.activity_type),
                    recommended_remediation=it.recommended_remediation,
                    status=str(ia.status.value if hasattr(ia.status, "value") else ia.status),
                    assigned_at=ia.assigned_at,
                )
            )
        return results

    async def complete_student_intervention(
        self, session: AsyncSession, user_id: int, assignment_id: int
    ) -> None:
        """Records student completion and measures post-intervention mastery."""
        stmt = select(InterventionAssignment).where(
            InterventionAssignment.id == assignment_id,
            InterventionAssignment.user_id == user_id,
        )
        res = await session.execute(stmt)
        ia = res.scalars().first()
        if not ia:
            raise NotFoundError(f"Assignment #{assignment_id} not found.")

        # Fetch parent intervention
        it_stmt = select(Intervention).where(Intervention.id == ia.intervention_id)
        it_res = await session.execute(it_stmt)
        it = it_res.scalars().first()
        if not it:
            raise NotFoundError("Intervention not found.")

        # Measure current post-intervention mastery
        mst_stmt = select(Mastery).where(
            Mastery.user_id == user_id, Mastery.concept_id == it.concept_id
        )
        mst_res = await session.execute(mst_stmt)
        m = mst_res.scalars().first()
        post_mst = m.p_mastery if m else ia.baseline_mastery
        post_attempts = m.attempts if m else 0
        post_strength, _ = calculate_evidence_strength(post_attempts)

        ia.status = InterventionAssignmentStatusEnum.COMPLETED
        ia.post_mastery = post_mst
        ia.post_evidence_strength = post_strength
        ia.completed_at = datetime.datetime.now(datetime.UTC)

        # Check if all assignments for this intervention are completed
        all_assign_stmt = select(InterventionAssignment).where(
            InterventionAssignment.intervention_id == it.id
        )
        all_res = await session.execute(all_assign_stmt)
        all_assignments = list(all_res.scalars().all())

        if all(a.status == InterventionAssignmentStatusEnum.COMPLETED for a in all_assignments):
            it.status = InterventionStatusEnum.COMPLETED
            it.updated_at = datetime.datetime.now(datetime.UTC)
        else:
            it.status = InterventionStatusEnum.IN_PROGRESS

        await session.commit()

    async def get_intervention_outcomes(
        self, session: AsyncSession, classroom_id: int, intervention_id: int
    ) -> InterventionOutcomesResponse:
        """Measures pre/post outcomes with honest reporting and sample size validation."""
        detail = await self.get_intervention_detail(session, classroom_id, intervention_id)

        completed_assignments = [
            a for a in detail.assignments if a.status == "completed" and a.post_mastery is not None
        ]

        total = len(detail.assignments)
        completed = len(completed_assignments)
        completion_rate = round(completed / total, 4) if total > 0 else 0.0

        mean_baseline = (
            round(sum(a.baseline_mastery for a in detail.assignments) / total, 4) if total > 0 else 0.0
        )

        mean_post: float | None = None
        mean_gain: float | None = None
        sample_sufficient = completed >= 5

        if completed_assignments:
            post_sum = sum(float(a.post_mastery) for a in completed_assignments if a.post_mastery is not None)
            mean_post = round(post_sum / completed, 4)
            mean_gain = round(mean_post - mean_baseline, 4)

        # Check resolved misconceptions
        resolved_count = 0
        if detail.target_misconception_id and detail.assignments:
            uids = [a.user_id for a in detail.assignments]
            dm_stmt = select(func.count(DetectedMisconception.id)).where(
                DetectedMisconception.user_id.in_(uids),
                DetectedMisconception.misconception_id == detail.target_misconception_id,
                DetectedMisconception.resolved_at.is_not(None),
            )
            dm_res = await session.execute(dm_stmt)
            resolved_count = dm_res.scalar_one()

        # Build narrative summary
        if completed == 0:
            summary = "Intervention has been assigned but no students have completed their remediation yet."
        elif not sample_sufficient:
            summary = (
                f"Preliminary results based on {completed} of {total} students. "
                f"Mean mastery changed from {round(mean_baseline * 100)}% to {round((mean_post or 0) * 100)}%. "
                "Sample size is insufficient for formal statistical significance."
            )
        else:
            gain_sign = "+" if (mean_gain or 0) >= 0 else ""
            summary = (
                f"Completed across {completed} learners. Average mastery progressed from {round(mean_baseline * 100)}% "
                f"to {round((mean_post or 0) * 100)}% ({gain_sign}{round((mean_gain or 0) * 100)}% delta). "
                f"{resolved_count} student misconception instances successfully resolved."
            )

        return InterventionOutcomesResponse(
            intervention_id=detail.id,
            title=detail.title,
            concept_id=detail.concept_id,
            concept_name=detail.concept_name,
            status=detail.status,
            total_assigned=total,
            completed_count=completed,
            completion_rate=completion_rate,
            mean_baseline_mastery=mean_baseline,
            mean_post_mastery=mean_post,
            mean_mastery_gain=mean_gain,
            misconceptions_resolved_count=resolved_count,
            sample_size_sufficient=sample_sufficient,
            outcome_summary=summary,
            assignments=detail.assignments,
        )


intervention_service = InterventionService()
