from app.domain.elo import calculate_expected_success, calibrate_item_difficulty, logit, sigmoid


def test_logit_and_sigmoid() -> None:
    assert abs(logit(0.50)) < 0.001
    assert abs(sigmoid(0.0) - 0.50) < 0.001
    assert abs(sigmoid(logit(0.75)) - 0.75) < 0.001


def test_expected_success() -> None:
    # Student mastery 0.5 -> theta = 0. Question difficulty b = 0.
    # expected = sigmoid(0 - 0) = 0.50
    assert abs(calculate_expected_success(0.50, 0.0) - 0.50) < 0.001


def test_calibrate_difficulty_gate() -> None:
    # If attempts < 5, difficulty must NOT change
    current_b = 0.0
    updated_b = calibrate_item_difficulty(current_b, 0.50, is_correct=True, n_attempts=4)
    assert updated_b == current_b


def test_calibrate_difficulty_update() -> None:
    # attempts >= 5, student mastery 0.50, b = 0.0, expected = 0.50
    # Correct answer (y = 1): b <- 0.0 + 0.10 * (0.50 - 1.0) = -0.05
    new_b = calibrate_item_difficulty(0.0, 0.50, is_correct=True, n_attempts=5, k_factor=0.10)
    assert abs(new_b - (-0.05)) < 0.001

    # Wrong answer (y = 0): b <- 0.0 + 0.10 * (0.50 - 0.0) = +0.05
    harder_b = calibrate_item_difficulty(0.0, 0.50, is_correct=False, n_attempts=5, k_factor=0.10)
    assert abs(harder_b - 0.05) < 0.001
