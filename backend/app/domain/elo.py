import math


def logit(p: float) -> float:
    """Computes log-odds of mastery as student ability proxy theta."""
    p_clamped = max(0.01, min(0.99, p))
    return math.log(p_clamped / (1.0 - p_clamped))


def sigmoid(x: float) -> float:
    """Computes logistic sigmoid function."""
    if x > 15.0:
        return 1.0
    if x < -15.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def calculate_expected_success(student_mastery: float, question_difficulty: float) -> float:
    """Computes expected probability of answering correctly: sigma(theta - b)."""
    theta = logit(student_mastery)
    return round(sigmoid(theta - question_difficulty), 4)


def calibrate_item_difficulty(
    current_difficulty: float,
    student_mastery: float,
    is_correct: bool,
    n_attempts: int,
    k_factor: float = 0.10,
    attempt_threshold: int = 5,
) -> float:
    """Updates item difficulty b <- b + K * (expected - y) if attempts >= 5."""
    if n_attempts < attempt_threshold:
        return current_difficulty

    expected = calculate_expected_success(student_mastery, current_difficulty)
    y = 1.0 if is_correct else 0.0
    delta = k_factor * (expected - y)
    new_b = current_difficulty + delta
    # Clamp difficulty to reasonable range [-3.0, 3.0]
    return round(max(-3.0, min(3.0, new_b)), 4)

