import datetime

from app.domain.sm2 import calculate_sm2_quality, calculate_sm2_update, compute_effective_mastery


def test_calculate_sm2_quality() -> None:
    assert calculate_sm2_quality(is_correct=False, response_ms=5000) == 1
    assert calculate_sm2_quality(is_correct=True, response_ms=10000) == 5  # fast
    assert calculate_sm2_quality(is_correct=True, response_ms=30000) == 4  # standard
    assert calculate_sm2_quality(is_correct=True, response_ms=75000) == 3  # slow


def test_calculate_sm2_progression() -> None:
    now = datetime.datetime(2026, 11, 1, 10, 0, tzinfo=datetime.UTC)

    # First attempt: correct and fast (q=5)
    # EF' = 2.5 + 0.1 - 0 = 2.6
    # Repetition 0 -> interval 1 day
    ef1, int1, rep1, due1 = calculate_sm2_update(
        2.5, 0, 0, is_correct=True, response_ms=15000, now=now
    )
    assert ef1 == 2.6
    assert int1 == 1
    assert rep1 == 1
    assert due1 == now + datetime.timedelta(days=1)

    # Second attempt: correct and fast (q=5)
    # Repetition 1 -> interval 6 days
    ef2, int2, rep2, due2 = calculate_sm2_update(
        ef1, int1, rep1, is_correct=True, response_ms=15000, now=now
    )
    assert int2 == 6
    assert rep2 == 2

    # Wrong answer resets repetitions and interval to 1
    ef3, int3, rep3, due3 = calculate_sm2_update(
        ef2, int2, rep2, is_correct=False, response_ms=10000, now=now
    )
    assert rep3 == 0
    assert int3 == 1
    assert ef3 < ef2


def test_effective_mastery_decay() -> None:
    now = datetime.datetime(2026, 11, 15, 12, 0, tzinfo=datetime.UTC)
    due_past = now - datetime.timedelta(days=14)  # 14 days overdue

    p_mastery = 0.80
    # After 14 days overdue: decay = exp(-14/14) = exp(-1) = ~0.3678
    # p_eff = 0.80 * 0.367879 = 0.2943
    p_eff = compute_effective_mastery(p_mastery, due_past, now=now)
    assert abs(p_eff - 0.2943) < 0.005
