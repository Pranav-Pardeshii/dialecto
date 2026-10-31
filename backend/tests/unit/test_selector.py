from app.domain.selector import select_next_practice_question


def test_select_next_practice_question_prefers_weak_concept() -> None:
    unlocked_concepts = [
        {
            "id": "lp-digestion",
            "name": "Digestion",
            "p_effective": 0.85,
            "is_overdue": False,
            "has_active_misconception": False,
        },
        {
            "id": "lp-photosynthesis",
            "name": "Photosynthesis",
            "p_effective": 0.35,
            "is_overdue": False,
            "has_active_misconception": False,
        },
    ]

    questions_by_concept = {
        "lp-digestion": [{"id": "q-dig-1", "difficulty_rating": 0.0}],
        "lp-photosynthesis": [{"id": "q-photo-1", "difficulty_rating": 0.0}],
    }

    result = select_next_practice_question(
        unlocked_concepts, questions_by_concept, seen_question_ids=set()
    )
    assert result is not None
    concept_id, question, reason = result
    assert concept_id == "lp-photosynthesis"
    assert question["id"] == "q-photo-1"
    assert "reinforcing" in reason.lower() or "photosynthesis" in reason.lower()


def test_select_next_practice_question_prefers_misconception() -> None:
    unlocked_concepts = [
        {
            "id": "c-1",
            "name": "Concept 1",
            "p_effective": 0.40,
            "is_overdue": False,
            "has_active_misconception": False,
        },
        {
            "id": "c-2",
            "name": "Concept 2",
            "p_effective": 0.50,
            "is_overdue": False,
            "has_active_misconception": True,
        },
    ]

    questions_by_concept = {
        "c-1": [{"id": "q-1", "difficulty_rating": 0.0}],
        "c-2": [{"id": "q-2", "difficulty_rating": 0.0}],
    }

    result = select_next_practice_question(
        unlocked_concepts, questions_by_concept, seen_question_ids=set()
    )
    assert result is not None
    concept_id, _, reason = result
    # c-2 has score (1 - 0.50) * (1 + 0.5) = 0.5 * 1.5 = 0.75
    # c-1 has score (1 - 0.40) * 1.0 = 0.60
    assert concept_id == "c-2"
    assert "misconception" in reason.lower()
