import asyncio
import datetime
import json
import random
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select

from app.db.session import async_session_factory
from app.domain.bkt import bkt_update
from app.domain.elo import calibrate_item_difficulty
from app.domain.graph import validate_dag
from app.domain.sm2 import calculate_sm2_update
from app.models.entities import (
    Attempt,
    Classroom,
    Concept,
    ConceptPrerequisite,
    DetectedMisconception,
    Mastery,
    Misconception,
    MisconceptionSourceEnum,
    Question,
    QuestionKindEnum,
    QuestionSourceEnum,
    User,
    UserRoleEnum,
)

logger = structlog.get_logger(__name__)

CONTENT_DIR = Path(__file__).parent.parent / "content"


async def load_content_data() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    with open(CONTENT_DIR / "concepts.json", encoding="utf-8") as f:
        concepts = json.load(f)
    with open(CONTENT_DIR / "misconceptions.json", encoding="utf-8") as f:
        misconceptions = json.load(f)
    with open(CONTENT_DIR / "questions.json", encoding="utf-8") as f:
        questions = json.load(f)
    return concepts, misconceptions, questions


async def seed_database(reset_demo: bool = False) -> None:
    logger.info("starting_database_seed")
    concepts_data, misconceptions_data, questions_data = await load_content_data()

    # 1. Validate Prerequisite DAG
    all_node_ids = {c["id"] for c in concepts_data}
    edges: list[tuple[str, str]] = []
    for c in concepts_data:
        for prereq in c.get("prerequisites", []):
            edges.append((prereq, c["id"]))

    logger.info("validating_prerequisite_dag", total_concepts=len(all_node_ids), edges=len(edges))
    sorted_order = validate_dag(edges, all_node_ids)
    logger.info("dag_validated_successfully", topological_order=sorted_order)

    async with async_session_factory() as session:
        async with session.begin():
            # 2. Seed / Upsert Concepts
            for c_data in concepts_data:
                concept = await session.get(Concept, c_data["id"])
                if not concept:
                    concept = Concept(
                        id=c_data["id"],
                        chapter=c_data["chapter"],
                        name=c_data["name"],
                        description=c_data["description"],
                        lesson_md=c_data["lesson_md"],
                        key_points=c_data["key_points"],
                        p_l0=c_data.get("p_l0", 0.30),
                        p_t=c_data.get("p_t", 0.15),
                        p_s=c_data.get("p_s", 0.10),
                        position=c_data.get("position", 0),
                    )
                    session.add(concept)
                else:
                    concept.name = c_data["name"]
                    concept.description = c_data["description"]
                    concept.lesson_md = c_data["lesson_md"]
                    concept.key_points = c_data["key_points"]
                    concept.position = c_data.get("position", 0)

            # 3. Seed / Upsert Prerequisites
            for c_data in concepts_data:
                concept_id = c_data["id"]
                for prereq_id in c_data.get("prerequisites", []):
                    stmt = select(ConceptPrerequisite).where(
                        ConceptPrerequisite.concept_id == concept_id,
                        ConceptPrerequisite.prerequisite_id == prereq_id,
                    )
                    existing = (await session.execute(stmt)).scalars().first()
                    if not existing:
                        session.add(
                            ConceptPrerequisite(
                                concept_id=concept_id,
                                prerequisite_id=prereq_id,
                            )
                        )

            # 4. Seed / Upsert Misconceptions
            for m_data in misconceptions_data:
                misc = await session.get(Misconception, m_data["id"])
                if not misc:
                    session.add(
                        Misconception(
                            id=m_data["id"],
                            concept_id=m_data["concept_id"],
                            statement=m_data["statement"],
                            correction=m_data["correction"],
                        )
                    )
                else:
                    misc.statement = m_data["statement"]
                    misc.correction = m_data["correction"]

            # 5. Seed / Upsert Questions
            for q_data in questions_data:
                q = await session.get(Question, q_data["id"])
                if not q:
                    session.add(
                        Question(
                            id=q_data["id"],
                            concept_id=q_data["concept_id"],
                            kind=QuestionKindEnum.MCQ,
                            stem=q_data["stem"],
                            options=q_data["options"],
                            correct_key=q_data["correct_key"],
                            explanation=q_data["explanation"],
                            difficulty_bucket=q_data.get("difficulty_bucket", 2),
                            difficulty_rating=q_data.get("difficulty_rating", 0.0),
                            n_attempts=0,
                            verified=q_data.get("verified", True),
                            source=QuestionSourceEnum.SEED,
                        )
                    )

            # 6. Seed Demo Classroom & Core Users
            classroom = await session.get(Classroom, 1)
            if not classroom:
                classroom = Classroom(id=1, name="Class 10-A Biology")
                session.add(classroom)

            # Featured fresh student Aarav (id=1)
            aarav = await session.get(User, 1)
            if not aarav:
                aarav = User(
                    id=1,
                    display_name="Aarav",
                    role=UserRoleEnum.STUDENT,
                    classroom_id=1,
                    is_simulated=False,
                )
                session.add(aarav)

            # Featured teacher Ms. Rao (id=2)
            ms_rao = await session.get(User, 2)
            if not ms_rao:
                ms_rao = User(
                    id=2,
                    display_name="Ms. Rao",
                    role=UserRoleEnum.TEACHER,
                    classroom_id=1,
                    is_simulated=False,
                )
                session.add(ms_rao)

            # 7. Seed 30 Simulated Students with Real Domain Math
            student_names = [
                "Ananya Iyer",
                "Dev Patel",
                "Diya Sen",
                "Ishaan Verma",
                "Kavya Nair",
                "Rohan Gupta",
                "Meera Joshi",
                "Aditya Kulkarni",
                "Pooja Reddy",
                "Vikram Malhotra",
                "Sneha Das",
                "Arjun Bhatia",
                "Neha Choudhury",
                "Siddharth Rao",
                "Tanvi Mehta",
                "Aryan Saxena",
                "Priyanka Roy",
                "Rishi Menon",
                "Tara Pillai",
                "Varun Chopra",
                "Simran Gill",
                "Nikhil Sethi",
                "Anika Jain",
                "Kabir Bose",
                "Rhea Kapoor",
                "Manish Pandey",
                "Shruti Agarwal",
                "Gaurav Trivedi",
                "Isha Mukherjee",
                "Dhruv Ghosh",
            ]

            all_concepts_list = (
                (await session.execute(select(Concept).order_by(Concept.position))).scalars().all()
            )
            all_questions_list = (await session.execute(select(Question))).scalars().all()
            q_by_concept: dict[str, list[Question]] = {}
            for q in all_questions_list:
                q_by_concept.setdefault(q.concept_id, []).append(q)

            now = datetime.datetime.now(datetime.UTC)

            # Known misconception IDs for targeted classroom hotspots
            hotspot_misconceptions = [
                "m-o2-from-co2",  # Oxygen comes from CO2
                "m-reflex-brain",  # Reflex arc goes to brain
                "m-recessive-lost",  # Blending inheritance / lost traits
            ]

            for idx, name in enumerate(student_names, start=3):
                existing_student = await session.get(User, idx)
                if not existing_student:
                    student = User(
                        id=idx,
                        display_name=name,
                        role=UserRoleEnum.STUDENT,
                        classroom_id=1,
                        is_simulated=True,
                    )
                    session.add(student)
                    await session.flush()
                else:
                    student = existing_student

                # Determine ability profile: 5 high (85%), 18 average (65%), 7 struggling (40%)
                if idx in (3, 4, 5, 6, 7):
                    target_accuracy = 0.88
                elif idx in (26, 27, 28, 29, 30, 31, 32):
                    target_accuracy = 0.38
                else:
                    target_accuracy = 0.65

                # Seed attempts & mastery across concepts using real domain math
                for concept in all_concepts_list:
                    existing_mastery = (
                        (
                            await session.execute(
                                select(Mastery).where(
                                    Mastery.user_id == student.id, Mastery.concept_id == concept.id
                                )
                            )
                        )
                        .scalars()
                        .first()
                    )
                    if existing_mastery:
                        continue

                    # Simulate 1 to 4 attempts on this concept over the past 14 days
                    num_attempts = random.randint(1, 4)
                    p_prior = concept.p_l0
                    ease = 2.5
                    interval = 0
                    reps = 0
                    correct_count = 0

                    c_questions = q_by_concept.get(concept.id, [])
                    if not c_questions:
                        continue

                    for att_i in range(num_attempts):
                        q = random.choice(c_questions)
                        days_ago = random.randint(1, 14)
                        attempt_time = now - datetime.timedelta(
                            days=days_ago, hours=random.randint(1, 12)
                        )

                        # Accuracy check with stochastic noise
                        is_correct = random.random() < target_accuracy
                        if is_correct:
                            correct_count += 1

                        # BKT update
                        _, p_next = bkt_update(
                            p_prior=p_prior,
                            is_correct=is_correct,
                            base_slip=concept.p_s,
                            learn_rate=concept.p_t,
                            num_options=len(q.options),
                            difficulty_bucket=q.difficulty_bucket,
                        )

                        # Elo update
                        q.difficulty_rating = calibrate_item_difficulty(
                            current_difficulty=q.difficulty_rating,
                            student_mastery=p_prior,
                            is_correct=is_correct,
                            n_attempts=q.n_attempts,
                        )
                        q.n_attempts += 1

                        # SM-2 update
                        ease, interval, reps, next_due = calculate_sm2_update(
                            current_ease=ease,
                            current_interval_days=interval,
                            current_repetitions=reps,
                            is_correct=is_correct,
                            response_ms=random.randint(8000, 45000),
                            now=attempt_time,
                        )

                        # Record attempt
                        attempt = Attempt(
                            client_attempt_id=uuid.uuid4(),
                            session_id=1,
                            user_id=student.id,
                            question_id=q.id,
                            concept_id=concept.id,
                            selected_key=q.correct_key if is_correct else "A",
                            is_correct=is_correct,
                            response_ms=random.randint(8000, 45000),
                            mastery_before=p_prior,
                            mastery_after=p_next,
                            created_at=attempt_time,
                        )
                        session.add(attempt)
                        p_prior = p_next

                    # Persist final Mastery row
                    mastery_row = Mastery(
                        user_id=student.id,
                        concept_id=concept.id,
                        p_mastery=p_prior,
                        attempts=num_attempts,
                        correct=correct_count,
                        last_seen_at=now - datetime.timedelta(days=random.randint(1, 7)),
                        ease=ease,
                        interval_days=interval,
                        repetitions=reps,
                        next_due_at=next_due,
                        version=1,
                    )
                    session.add(mastery_row)

                # Add active misconceptions for struggling/average students
                if target_accuracy < 0.70 and random.random() < 0.60:
                    chosen_misc_id = random.choice(hotspot_misconceptions)
                    existing_dm = (
                        (
                            await session.execute(
                                select(DetectedMisconception).where(
                                    DetectedMisconception.user_id == student.id,
                                    DetectedMisconception.misconception_id == chosen_misc_id,
                                )
                            )
                        )
                        .scalars()
                        .first()
                    )
                    if not existing_dm:
                        detected_misc = DetectedMisconception(
                            user_id=student.id,
                            misconception_id=chosen_misc_id,
                            attempt_id=None,
                            source=MisconceptionSourceEnum.DISTRACTOR,
                            confidence=0.85,
                            created_at=now - datetime.timedelta(days=random.randint(1, 5)),
                        )
                        session.add(detected_misc)

        logger.info("database_seed_completed_successfully")


if __name__ == "__main__":
    asyncio.run(seed_database())
