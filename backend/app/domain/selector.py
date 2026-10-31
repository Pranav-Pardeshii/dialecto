from typing import Any

from app.domain.elo import calculate_expected_success


def select_next_practice_question(
    unlocked_concepts: list[dict[str, Any]],
    questions_by_concept: dict[str, list[dict[str, Any]]],
    seen_question_ids: set[str],
) -> tuple[str, dict[str, Any], str] | None:
    """Selects the optimal practice question targeting weak concepts at ~70% predicted success.

    Prioritizes unseen questions across all eligible unlocked concepts before reusing seen items.
    Returns:
        (concept_id, question_dict, selection_reason) or None
    """
    if not unlocked_concepts:
        return None

    # Sort concepts by priority score descending
    # score = (1 - p_effective) * (1 + due_bonus) * (1 + 0.5 * has_active_misconception)
    def concept_priority(c: dict[str, Any]) -> float:
        p_eff = float(c.get("p_effective", 0.3))
        due_bonus = 0.5 if c.get("is_overdue", False) else 0.0
        misc_bonus = 0.5 if c.get("has_active_misconception", False) else 0.0
        return float((1.0 - p_eff) * (1.0 + due_bonus) * (1.0 + misc_bonus))

    sorted_concepts = sorted(unlocked_concepts, key=concept_priority, reverse=True)

    def format_reason(concept: dict[str, Any], p_eff: float) -> str:
        c_name = concept.get("name", concept["id"])
        if concept.get("has_active_misconception"):
            return f"Targeting active misconception in {c_name}."
        elif concept.get("is_overdue"):
            return f"Due for spaced-repetition review in {c_name}."
        elif p_eff < 0.5:
            return (
                f"Reinforcing foundational understanding in {c_name} (mastery {int(p_eff * 100)}%)."
            )
        else:
            return f"Advancing mastery in {c_name} near optimal challenge difficulty."

    # Pass 1: Prioritize eligible concepts that have unseen questions
    for concept in sorted_concepts:
        c_id = concept["id"]
        candidate_questions = questions_by_concept.get(c_id, [])
        unseen = [q for q in candidate_questions if q["id"] not in seen_question_ids]
        if unseen:
            p_eff = concept.get("p_effective", 0.3)
            best_question = min(
                unseen,
                key=lambda q: abs(
                    calculate_expected_success(p_eff, q.get("difficulty_rating", 0.0)) - 0.70
                ),
            )
            return c_id, best_question, format_reason(concept, p_eff)

    # Pass 2: All eligible concepts have exhausted unseen questions; select optimal item from pool
    for concept in sorted_concepts:
        c_id = concept["id"]
        candidate_questions = questions_by_concept.get(c_id, [])
        if candidate_questions:
            p_eff = concept.get("p_effective", 0.3)
            best_question = min(
                candidate_questions,
                key=lambda q: abs(
                    calculate_expected_success(p_eff, q.get("difficulty_rating", 0.0)) - 0.70
                ),
            )
            return c_id, best_question, format_reason(concept, p_eff)

    return None
