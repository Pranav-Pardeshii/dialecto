from app.domain.bkt import adjust_slip, bkt_update, soft_evidence_update


def test_adjust_slip() -> None:
    # Base slip = 0.10
    # d = 1 -> 0.10 + 0.05 * (-1) = 0.05
    assert adjust_slip(0.10, 1) == 0.05
    # d = 2 -> 0.10
    assert adjust_slip(0.10, 2) == 0.10
    # d = 3 -> 0.10 + 0.05 * 1 = 0.15
    assert adjust_slip(0.10, 3) == 0.15


def test_bkt_update_correct() -> None:
    # Prior = 0.30, Correct, S=0.10, T=0.15, G=0.25 (num_options=4), d=2
    # P(L|c) = 0.30*(1-0.10) / [0.30*0.90 + 0.70*0.25] = 0.27 / [0.27 + 0.175] = 0.27 / 0.445 = 0.6067
    # P(L') = 0.6067 + (1 - 0.6067)*0.15 = 0.6067 + 0.0590 = 0.6657
    p_obs, p_next = bkt_update(
        0.30, is_correct=True, base_slip=0.10, learn_rate=0.15, num_options=4, difficulty_bucket=2
    )
    assert abs(p_obs - 0.6067) < 0.001
    assert abs(p_next - 0.6657) < 0.001


def test_bkt_update_wrong() -> None:
    # Prior = 0.50, Wrong, S=0.10, T=0.15, G=0.25, d=2
    # P(L|w) = 0.50*0.10 / [0.50*0.10 + 0.50*0.75] = 0.05 / [0.05 + 0.375] = 0.05 / 0.425 = 0.1176
    # P(L') = 0.1176 + (1 - 0.1176)*0.15 = 0.1176 + 0.1324 = 0.2500
    p_obs, p_next = bkt_update(
        0.50, is_correct=False, base_slip=0.10, learn_rate=0.15, num_options=4, difficulty_bucket=2
    )
    assert abs(p_obs - 0.1176) < 0.001
    assert abs(p_next - 0.2500) < 0.001


def test_soft_evidence_update() -> None:
    p_prior = 0.40
    # Soft evidence with high confidence 0.85 (capped at 0.70)
    p_new = soft_evidence_update(p_prior=p_prior, is_positive=True, confidence=0.85)
    assert p_new > p_prior
    assert p_new <= 1.0
