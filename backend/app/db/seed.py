import asyncio
import json
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select

from app.db.session import async_session_factory
from app.domain.graph import validate_dag
from app.models.entities import (
    Classroom,
    Concept,
    ConceptPrerequisite,
    Misconception,
    Question,
    QuestionKindEnum,
    QuestionSourceEnum,
    User,
    UserRoleEnum,
)

logger = structlog.get_logger(__name__)

CONTENT_DIR = Path(__file__).parent.parent / "content"


async def load_content_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
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

        logger.info("database_seed_completed_successfully")


if __name__ == "__main__":
    asyncio.run(seed_database())
