from app.domain.explainable_mastery import (
    EvidenceStrength,
    calculate_evidence_strength,
    determine_trend,
    generate_mastery_narrative,
)


def test_evidence_strength_zero_attempts() -> None:
    cat, score = calculate_evidence_strength(total_attempts=0)
    assert cat == EvidenceStrength.INSUFFICIENT
    assert score == 0.0


def test_evidence_strength_low_attempts() -> None:
    cat, score = calculate_evidence_strength(total_attempts=1)
    assert cat == EvidenceStrength.LOW
    assert 0.0 < score < 0.40


def test_evidence_strength_moderate_attempts() -> None:
    cat, score = calculate_evidence_strength(total_attempts=4, distinct_modalities=2)
    assert cat == EvidenceStrength.MODERATE
    assert 0.40 <= score < 0.85


def test_evidence_strength_high_attempts() -> None:
    cat, score = calculate_evidence_strength(total_attempts=10, distinct_modalities=3)
    assert cat == EvidenceStrength.HIGH
    assert score >= 0.70


def test_determine_trend() -> None:
    assert determine_trend([]) == "untested"
    assert determine_trend([True, True, True, True]) == "improving"
    assert determine_trend([False, False, False, False]) == "declining"
    assert determine_trend([True, False, True, False]) == "stable"


def test_narrative_generation_untested() -> None:
    narrative = generate_mastery_narrative(
        concept_name="Photosynthesis",
        p_mastery=0.30,
        evidence_category=EvidenceStrength.INSUFFICIENT,
        total_attempts=0,
        correct_attempts=0,
        trend="untested",
        active_misconceptions=[],
        unmet_prerequisites=[],
        is_overdue=False,
    )
    assert "not completed any verified assessments" in narrative

