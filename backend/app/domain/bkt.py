def clamp(val: float, low: float = 0.001, high: float = 0.999) -> float:
    return max(low, min(high, val))


def adjust_slip(base_slip: float, difficulty_bucket: int) -> float:
    """Difficulty-adjusted slip: S_q = S + 0.05 * (d - 2), clamped to [0.02, 0.30]."""
    adjusted = base_slip + 0.05 * (difficulty_bucket - 2)
    return round(max(0.02, min(0.30, adjusted)), 4)


def bkt_update(
    p_prior: float,
    is_correct: bool,
    base_slip: float = 0.10,
    learn_rate: float = 0.15,
    num_options: int = 4,
    difficulty_bucket: int = 2,
) -> tuple[float, float]:
    """Computes Bayesian Knowledge Tracing update.

    Returns:
        (p_observed, p_posterior_after_transition)
    """
    p_prior = clamp(p_prior)
    s = adjust_slip(base_slip, difficulty_bucket)
    g = 1.0 / max(2, num_options)

    if is_correct:
        # P(L|c) = P(L)(1-S) / [P(L)(1-S) + (1-P(L))G]
        numerator = p_prior * (1.0 - s)
        denominator = numerator + (1.0 - p_prior) * g
        p_obs = numerator / max(1e-9, denominator)
    else:
        # P(L|w) = P(L)S / [P(L)S + (1-P(L))(1-G)]
        numerator = p_prior * s
        denominator = numerator + (1.0 - p_prior) * (1.0 - g)
        p_obs = numerator / max(1e-9, denominator)

    p_obs = clamp(p_obs)
    # Transition: P(L') = P(L|obs) + (1 - P(L|obs)) * T
    p_next = p_obs + (1.0 - p_obs) * learn_rate
    return round(clamp(p_obs), 4), round(clamp(p_next), 4)


def soft_evidence_update(
    p_prior: float,
    is_positive: bool,
    confidence: float,
    base_slip: float = 0.10,
    learn_rate: float = 0.15,
) -> float:
    """Soft evidence update used in Teach-Back mode.

    P_new = P_prior + w * (P_bkt - P_prior), where w = min(0.7, confidence).
    """
    _, p_bkt = bkt_update(
        p_prior=p_prior,
        is_correct=is_positive,
        base_slip=base_slip,
        learn_rate=learn_rate,
        num_options=4,
        difficulty_bucket=2,
    )
    weight = min(0.70, max(0.10, confidence))
    p_new = p_prior + weight * (p_bkt - p_prior)
    return round(clamp(p_new), 4)
