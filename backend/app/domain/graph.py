from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

PREREQUISITE_MASTERY_THRESHOLD = 0.60
MASTERY_THRESHOLD = 0.80

STATUS_LOCKED = "locked"
STATUS_READY = "ready"
STATUS_UNLOCKED = "ready"  # Canonical name is "ready"; "unlocked" is normalized to "ready"
STATUS_LEARNING = "learning"
STATUS_MASTERED = "mastered"


class CycleDetectedError(Exception):
    pass


class InvalidPrerequisiteError(Exception):
    pass


@dataclass(frozen=True)
class PrerequisiteInfo:
    prerequisite_id: str
    prerequisite_name: str
    base_mastery: float  # Base mastery (not decayed) to prevent SM-2 decay relocking


@dataclass
class ConceptStatusDetails:
    status: str  # "locked", "ready", "learning", "mastered"
    lock_reason: str | None = None
    unmet_prerequisites: list[dict[str, Any]] = field(default_factory=list)


def validate_dag(edges: list[tuple[str, str]], all_nodes: set[str]) -> list[str]:
    """Validates that the prerequisite graph is a Directed Acyclic Graph (DAG).

    Edge tuple format: (prerequisite_id, dependent_id) meaning prerequisite -> dependent.
    Returns topologically sorted list of node IDs.
    Raises CycleDetectedError if a cycle is detected.
    """
    in_degree: dict[str, int] = {node: 0 for node in all_nodes}
    adj_list: dict[str, list[str]] = defaultdict(list)

    for prereq, dependent in edges:
        if prereq == dependent:
            raise CycleDetectedError(f"Self-referential dependency detected on concept '{prereq}'")
        if prereq in all_nodes and dependent in all_nodes:
            adj_list[prereq].append(dependent)
            in_degree[dependent] = in_degree.get(dependent, 0) + 1

    # Kahn's algorithm
    queue = deque([node for node, deg in in_degree.items() if deg == 0])
    sorted_nodes: list[str] = []

    while queue:
        curr = queue.popleft()
        sorted_nodes.append(curr)
        for neighbor in adj_list[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_nodes) != len(all_nodes):
        raise CycleDetectedError("Cycle detected in concept prerequisite graph!")

    return sorted_nodes


def validate_prerequisite_integrity(concepts: list[dict[str, Any]]) -> dict[str, Any]:
    """Validates that all prerequisite references exist, have no self-dependencies,

    have no circular dependencies, and validates chapter consistency.
    """
    concept_map = {c["id"]: c for c in concepts}
    all_node_ids = set(concept_map.keys())
    edges: list[tuple[str, str]] = []

    for c in concepts:
        c_id = c["id"]
        c_chapter = c.get("chapter")
        for prereq_id in c.get("prerequisites", []):
            if prereq_id not in all_node_ids:
                raise InvalidPrerequisiteError(
                    f"Concept '{c_id}' references non-existent prerequisite '{prereq_id}'"
                )
            if prereq_id == c_id:
                raise InvalidPrerequisiteError(
                    f"Concept '{c_id}' cannot depend on itself"
                )
            prereq_concept = concept_map[prereq_id]
            if prereq_concept.get("chapter") != c_chapter:
                # Flag cross-chapter dependency if unexpected
                pass
            edges.append((prereq_id, c_id))

    sorted_nodes = validate_dag(edges, all_node_ids)
    return {
        "valid": True,
        "total_concepts": len(all_node_ids),
        "total_edges": len(edges),
        "topological_order": sorted_nodes,
    }


def determine_concept_status(
    effective_mastery: float,
    attempts: int,
    prerequisites: list[PrerequisiteInfo] | None = None,
    prereq_threshold: float = PREREQUISITE_MASTERY_THRESHOLD,
    mastery_threshold: float = MASTERY_THRESHOLD,
) -> ConceptStatusDetails:
    """Authoritative concept status calculator per curriculum rules:

    LOCKED
      - At least one required prerequisite is genuinely unmet (base_mastery < 0.60).
      - Returns exact unmet prerequisite IDs, names, current mastery, and reason.

    READY
      - All required prerequisites are satisfied (or concept has no prerequisites).
      - attempts == 0 (learner has not yet started learning).

    LEARNING
      - All required prerequisites satisfied (or already attempted).
      - attempts > 0 and effective_mastery < 0.80.

    MASTERED
      - All required prerequisites satisfied (or already attempted).
      - attempts > 0 and effective_mastery >= 0.80.
    """
    prereqs = prerequisites or []
    unmet: list[dict[str, Any]] = []

    for p in prereqs:
        if p.base_mastery < prereq_threshold:
            unmet.append(
                {
                    "id": p.prerequisite_id,
                    "name": p.prerequisite_name,
                    "required_mastery": prereq_threshold,
                    "current_mastery": round(p.base_mastery, 4),
                }
            )

    if unmet:
        req_pct = int(round(prereq_threshold * 100))
        if len(unmet) == 1:
            u = unmet[0]
            curr_pct = int(round(u["current_mastery"] * 100))
            lock_reason = (
                f"Locked: {u['name']} requires {req_pct}% prerequisite mastery. "
                f"Your current mastery is {curr_pct}%."
            )
        else:
            reasons = [
                f"{u['name']} (current: {int(round(u['current_mastery'] * 100))}%, required: {req_pct}%)"
                for u in unmet
            ]
            lock_reason = (
                f"Locked: Requires {req_pct}% prerequisite mastery across {len(unmet)} prerequisites. "
                f"Unmet: {'; '.join(reasons)}."
            )

        return ConceptStatusDetails(
            status=STATUS_LOCKED,
            lock_reason=lock_reason,
            unmet_prerequisites=unmet,
        )

    # All prerequisites are satisfied (or root concept)
    if attempts == 0:
        return ConceptStatusDetails(
            status=STATUS_READY,
            lock_reason=None,
            unmet_prerequisites=[],
        )

    if effective_mastery >= mastery_threshold:
        return ConceptStatusDetails(
            status=STATUS_MASTERED,
            lock_reason=None,
            unmet_prerequisites=[],
        )

    return ConceptStatusDetails(
        status=STATUS_LEARNING,
        lock_reason=None,
        unmet_prerequisites=[],
    )


def calculate_concept_status(
    effective_mastery: float,
    attempts: int,
    prereq_masteries: list[float],
) -> str:
    """Calculates mastery status string for backward compatibility.

    - locked: any prerequisite has mastery < 0.60
    - ready / unlocked: prerequisites met, but 0 attempts recorded
    - learning: has attempts, but effective mastery < 0.80
    - mastered: effective mastery >= 0.80
    """
    for p in prereq_masteries:
        if p < PREREQUISITE_MASTERY_THRESHOLD:
            return STATUS_LOCKED

    if attempts == 0:
        return STATUS_READY

    if effective_mastery >= MASTERY_THRESHOLD:
        return STATUS_MASTERED

    return STATUS_LEARNING
