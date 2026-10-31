import datetime
import math


def calculate_sm2_quality(is_correct: bool, response_ms: int) -> int:
    """Calculates SM-2 quality response grade q in {1, 3, 4, 5}."""
    if not is_correct:
        return 1
    if response_ms < 20000:
        return 5
    if response_ms <= 60000:
        return 4
    return 3


def calculate_sm2_update(
    current_ease: float,
    current_interval_days: int,
    current_repetitions: int,
    is_correct: bool,
    response_ms: int,
    now: datetime.datetime | None = None,
) -> tuple[float, int, int, datetime.datetime]:
    """Computes SM-2 ease factor, interval, repetition count, and next due timestamp.

    Returns:
        (new_ease, new_interval_days, new_repetitions, next_due_at)
    """
    if now is None:
        now = datetime.datetime.now(datetime.UTC)

    q = calculate_sm2_quality(is_correct, response_ms)

    # Ease factor update
    delta_ef = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    new_ease = max(1.3, round(current_ease + delta_ef, 4))

    if q < 3:
        new_repetitions = 0
        new_interval_days = 1
    else:
        if current_repetitions == 0:
            new_interval_days = 1
        elif current_repetitions == 1:
            new_interval_days = 6
        else:
            new_interval_days = min(365, max(1, round(current_interval_days * new_ease)))
        new_repetitions = current_repetitions + 1

    next_due_at = now + datetime.timedelta(days=new_interval_days)
    return new_ease, new_interval_days, new_repetitions, next_due_at


def compute_effective_mastery(
    p_mastery: float,
    next_due_at: datetime.datetime | None,
    now: datetime.datetime | None = None,
) -> float:
    """Computes mastery decay when review is overdue:

    p_effective = p_mastery * exp(-max(0, days_overdue) / 14)
    """
    if not next_due_at:
        return round(p_mastery, 4)

    if now is None:
        now = datetime.datetime.now(datetime.UTC)

    if now <= next_due_at:
        return round(p_mastery, 4)

    days_overdue = (now - next_due_at).total_seconds() / 86400.0
    decay = math.exp(-days_overdue / 14.0)
    return round(max(0.01, p_mastery * decay), 4)
