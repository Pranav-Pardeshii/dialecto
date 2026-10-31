import pytest

from app.domain.graph import CycleDetectedError, calculate_concept_status, validate_dag


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


def test_calculate_concept_status() -> None:
    # Locked if any prereq is below 0.60
    assert calculate_concept_status(0.5, 0, [0.55]) == "locked"
    assert calculate_concept_status(0.9, 5, [0.40, 0.80]) == "locked"

    # Unlocked if prereqs met (or no prereqs) and 0 attempts
    assert calculate_concept_status(0.3, 0, [0.70]) == "unlocked"
    assert calculate_concept_status(0.3, 0, []) == "unlocked"

    # Learning if has attempts and mastery < 0.80
    assert calculate_concept_status(0.65, 3, [0.80]) == "learning"

    # Mastered if mastery >= 0.80
    assert calculate_concept_status(0.85, 4, [0.80]) == "mastered"
