import pytest

from app.domain.graph import (
    CycleDetectedError,
    InvalidPrerequisiteError,
    PrerequisiteInfo,
    calculate_concept_status,
    determine_concept_status,
    validate_dag,
    validate_prerequisite_integrity,
)


def test_validate_dag_valid() -> None:
    nodes = {"A", "B", "C", "D"}
    edges = [("A", "B"), ("B", "C"), ("A", "D")]
    order = validate_dag(edges, nodes)
    assert len(order) == 4
    assert order.index("A") < order.index("B")
    assert order.index("B") < order.index("C")
    assert order.index("A") < order.index("D")


def test_validate_dag_cycle_raises() -> None:
    nodes = {"A", "B", "C"}
    edges = [("A", "B"), ("B", "C"), ("C", "A")]
    with pytest.raises(CycleDetectedError):
        validate_dag(edges, nodes)


def test_validate_dag_self_reference_raises() -> None:
    nodes = {"A"}
    edges = [("A", "A")]
    with pytest.raises(CycleDetectedError):
        validate_dag(edges, nodes)


def test_validate_prerequisite_integrity_invalid_prereq_raises() -> None:
    concepts = [
        {"id": "c1", "chapter": "ch1", "prerequisites": ["non-existent"]},
    ]
    with pytest.raises(InvalidPrerequisiteError):
        validate_prerequisite_integrity(concepts)


def test_validate_prerequisite_integrity_self_prereq_raises() -> None:
    concepts = [
        {"id": "c1", "chapter": "ch1", "prerequisites": ["c1"]},
    ]
    with pytest.raises(InvalidPrerequisiteError):
        validate_prerequisite_integrity(concepts)


def test_validate_prerequisite_integrity_valid() -> None:
    concepts = [
        {"id": "c1", "chapter": "ch1", "prerequisites": []},
        {"id": "c2", "chapter": "ch1", "prerequisites": ["c1"]},
    ]
    res = validate_prerequisite_integrity(concepts)
    assert res["valid"] is True
    assert res["topological_order"] == ["c1", "c2"]


def test_root_concept_always_accessible() -> None:
    # Root concepts (no prerequisites) should never be locked
    res_ready = determine_concept_status(effective_mastery=0.0, attempts=0, prerequisites=[])
    assert res_ready.status == "ready"
    assert res_ready.lock_reason is None

    res_learning = determine_concept_status(effective_mastery=0.55, attempts=2, prerequisites=[])
    assert res_learning.status == "learning"

    res_mastered = determine_concept_status(effective_mastery=0.85, attempts=4, prerequisites=[])
    assert res_mastered.status == "mastered"


def test_unsatisfied_prerequisite_locks_concept_with_clear_reason() -> None:
    prereqs = [
        PrerequisiteInfo(prerequisite_id="lp-nutrition", prerequisite_name="Modes of Nutrition", base_mastery=0.42),
    ]
    res = determine_concept_status(effective_mastery=0.0, attempts=0, prerequisites=prereqs)
    assert res.status == "locked"
    assert "Modes of Nutrition requires 60% prerequisite mastery" in res.lock_reason
    assert "Your current mastery is 42%" in res.lock_reason
    assert len(res.unmet_prerequisites) == 1
    assert res.unmet_prerequisites[0]["id"] == "lp-nutrition"


def test_satisfied_prerequisites_unlock_dependent_concept() -> None:
    prereqs = [
        PrerequisiteInfo(prerequisite_id="lp-nutrition", prerequisite_name="Modes of Nutrition", base_mastery=0.75),
    ]
    # Untested student with satisfied prerequisites gets "ready"
    res_ready = determine_concept_status(effective_mastery=0.0, attempts=0, prerequisites=prereqs)
    assert res_ready.status == "ready"
    assert res_ready.lock_reason is None

    # Student actively learning gets "learning"
    res_learning = determine_concept_status(effective_mastery=0.68, attempts=3, prerequisites=prereqs)
    assert res_learning.status == "learning"

    # Student at or above 80% gets "mastered"
    res_mastered = determine_concept_status(effective_mastery=0.82, attempts=5, prerequisites=prereqs)
    assert res_mastered.status == "mastered"


def test_calculate_concept_status_backward_compatibility() -> None:
    # Locked if any prereq is below 0.60
    assert calculate_concept_status(0.5, 0, [0.55]) == "locked"
    assert calculate_concept_status(0.9, 5, [0.40, 0.80]) == "locked"

    # Ready if prereqs met (or no prereqs) and 0 attempts
    assert calculate_concept_status(0.3, 0, [0.70]) in ("ready", "unlocked")
    assert calculate_concept_status(0.3, 0, []) in ("ready", "unlocked")

    # Learning if has attempts and mastery < 0.80
    assert calculate_concept_status(0.65, 3, [0.80]) == "learning"

    # Mastered if mastery >= 0.80
    assert calculate_concept_status(0.85, 4, [0.80]) == "mastered"
