from mavs10d.governance.thresholds import compute_threshold


def test_thresholds_become_stricter_when_severity_rises() -> None:
    low = compute_threshold(
        base_threshold=0.60,
        severity=0.10,
        mitigation_strength=0.0,
        hard_veto=False,
    )
    high = compute_threshold(
        base_threshold=0.60,
        severity=0.80,
        mitigation_strength=0.0,
        hard_veto=False,
    )

    assert high.final_threshold < low.final_threshold


def test_threshold_relaxation_is_bounded_and_blocked_by_hard_veto() -> None:
    relaxed = compute_threshold(
        base_threshold=0.60,
        severity=0.0,
        mitigation_strength=0.50,
        hard_veto=False,
        max_mitigation_relaxation=0.10,
    )
    vetoed = compute_threshold(
        base_threshold=0.60,
        severity=0.0,
        mitigation_strength=0.50,
        hard_veto=True,
        max_mitigation_relaxation=0.10,
    )

    assert relaxed.final_threshold == 0.70
    assert vetoed.final_threshold == 0.60
    assert vetoed.mitigation_relaxation == 0.0

