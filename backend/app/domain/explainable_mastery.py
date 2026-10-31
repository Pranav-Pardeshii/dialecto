"""Domain mathematics and explanation generator for Explainable Mastery and Confidence.

Pure, unit-tested domain logic strictly separated from I/O.
Computes mathematical evidence confidence without fabricating data or replacing BKT.
"""

import datetime
import math
from typing import Any


class EvidenceStrength:
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


def calculate_evidence_strength(
    total_attempts: int,
    distinct_modalities: int = 1,
    days_since_last_seen: float | None = None,
) -> tuple[str, float]:
    """Calculates mathematical evidence confidence based on sample size, modality diversity, and recency.

    Returns:
        (evidence_category, numeric_confidence_score_0_to_1)
    """
    if total_attempts <= 0:
        return EvidenceStrength.INSUFFICIENT, 0.0

    # 1. Sample size factor: diminishing returns curve f(N) = 1 - exp(-N / 4.0)
    sample_factor = 1.0 - math.exp(-total_attempts / 4.0)

    # 2. Modality diversity factor (up to 4 assessment kinds: practice, diagnostic, teachback, diagram)
    clamped_modalities = max(1, min(4, distinct_modalities))
    diversity_factor = 0.70 + 0.30 * (clamped_modalities / 4.0)

    # 3. Recency factor (retention half-life discount)
    recency_factor = 1.0
    if days_since_last_seen is not None and days_since_last_seen > 0:
        recency_factor = math.exp(-days_since_last_seen / 45.0)

    evidence_score = round(min(1.0, sample_factor * diversity_factor * (0.65 + 0.35 * recency_factor)), 4)

    # Deterministic category assignment
    if total_attempts < 2 or evidence_score < 0.30:
        category = EvidenceStrength.LOW
    elif total_attempts < 6 or evidence_score < 0.70:
        category = EvidenceStrength.MODERATE
    else:
        category = EvidenceStrength.HIGH

    return category, evidence_score


def determine_trend(recent_outcomes: list[bool]) -> str:
    """Determines recent performance trajectory from chronological attempt boolean outcomes."""
    if not recent_outcomes:
        return "untested"
    if len(recent_outcomes) < 2:
        return "improving" if recent_outcomes[0] else "declining"

    last_slice = recent_outcomes[-4:]
    correct_count = sum(1 for x in last_slice if x)
    ratio = correct_count / len(last_slice)

    if ratio >= 0.75:
        return "improving"
    elif ratio <= 0.25:
        return "declining"
    else:
        return "stable"


def generate_mastery_narrative(
    concept_name: str,
    p_mastery: float,
    evidence_category: str,
    total_attempts: int,
    correct_attempts: int,
    trend: str,
    active_misconceptions: list[str],
    unmet_prerequisites: list[str],
    is_overdue: bool,
    days_overdue: int = 0,
) -> str:
    """Generates an honest, state-derived educational narrative explaining mastery and confidence."""
    parts: list[str] = []

    # 1. Evidence sufficiency foundation
    if evidence_category == EvidenceStrength.INSUFFICIENT or total_attempts == 0:
        return (
            f"You have not completed any verified assessments for {concept_name} yet. "
            "Mastery remains at baseline prior (30%). Complete diagnostic or practice items to establish real evidence."
        )

    # 2. Performance & evidence strength
    accuracy_pct = round((correct_attempts / total_attempts) * 100) if total_attempts > 0 else 0
    if evidence_category == EvidenceStrength.LOW:
        parts.append(
            f"Current estimate of {round(p_mastery * 100)}% mastery is based on limited evidence ({total_attempts} attempts with {accuracy_pct}% accuracy)."
        )
    elif evidence_category == EvidenceStrength.MODERATE:
        parts.append(
            f"Moderate assessment evidence ({total_attempts} attempts, {accuracy_pct}% accuracy) indicates an effective mastery of {round(p_mastery * 100)}%."
        )
    else:
        parts.append(
            f"Robust multi-assessment evidence ({total_attempts} attempts, {accuracy_pct}% accuracy) confirms {round(p_mastery * 100)}% mastery."
        )

    # 3. Trajectory & Misconceptions
    if active_misconceptions:
        parts.append(
            f"Attention required: You have an active misconception regarding {active_misconceptions[0]}. Reviewing targeted feedback is strongly recommended."
        )
    elif trend == "improving" and p_mastery >= 0.75:
        parts.append("Your recent performance shows consistent conceptual mastery.")
    elif trend == "declining":
        parts.append("Recent incorrect answers have decreased the model's confidence in retention.")

    # 4. Prerequisite blockers
    if unmet_prerequisites:
        prereq_names = ", ".join(unmet_prerequisites[:2])
        parts.append(f"Foundational gap: Prerequisite concepts ({prereq_names}) are still below target proficiency.")

    # 5. Spaced repetition status
    if is_overdue:
        parts.append(f"Spaced review is {days_overdue} days overdue. Memory trace decay will lower effective retrieval without timely practice.")

    return " ".join(parts)


def format_timeline_event(
    event_type: str,
    timestamp: datetime.datetime,
    description: str,
    is_correct: bool,
    mastery_before: float,
    mastery_after: float,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Formats a single chronological assessment event contributing to mastery."""
    delta = round(mastery_after - mastery_before, 4)
    return {
        "event_type": event_type,
        "timestamp": timestamp.isoformat(),
        "description": description,
        "is_correct": is_correct,
        "mastery_before": round(mastery_before, 4),
        "mastery_after": round(mastery_after, 4),
        "mastery_delta": delta,
        "metadata": metadata or {},
    }

