from collections import defaultdict, deque


class CycleDetectedError(Exception):
    pass


def validate_dag(edges: list[tuple[str, str]], all_nodes: set[str]) -> list[str]:
    """Validates that the prerequisite graph is a Directed Acyclic Graph (DAG).

    Edge tuple format: (prerequisite_id, dependent_id) meaning prerequisite -> dependent.
    Returns topologically sorted list of node IDs.
    Raises CycleDetectedError if a cycle is detected.
    """
    in_degree: dict[str, int] = {node: 0 for node in all_nodes}
    adj_list: dict[str, list[str]] = defaultdict(list)

    for prereq, dependent in edges:
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


def calculate_concept_status(
    effective_mastery: float,
    attempts: int,
    prereq_masteries: list[float],
) -> str:
    """Calculates mastery status per docs/architecture.md:

    - locked: any prerequisite has effective mastery < 0.60
    - unlocked: prerequisites met, but 0 attempts recorded
    - learning: has attempts, but effective mastery < 0.80
    - mastered: effective mastery >= 0.80
    """
    for p in prereq_masteries:
        if p < 0.60:
            return "locked"

    if attempts == 0:
        return "unlocked"

    if effective_mastery >= 0.80:
        return "mastered"

    return "learning"
