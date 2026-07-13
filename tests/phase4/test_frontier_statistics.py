from __future__ import annotations

import math

from mavs10d.metrics.frontier import FrontierPoint, additive_epsilon, hypervolume, matched_rate_advantages, pareto_frontier
from mavs10d.metrics.phase4 import exact_binomial_interval, hierarchical_bootstrap_ratio, holm_adjust, paired_sign_test


def test_exact_four_dimensional_frontier_hypervolume_and_epsilon() -> None:
    points = (
        FrontierPoint("a", 0.2, 0.3, 0.4, 0.5),
        FrontierPoint("b", 0.3, 0.4, 0.5, 0.6),
        FrontierPoint("c", 0.1, 0.5, 0.3, 0.4),
    )
    assert {point.method_id for point in pareto_frontier(points)} == {"a", "c"}
    assert math.isclose(hypervolume((points[0],)), 0.8 * 0.7 * 0.6 * 0.5)
    assert additive_epsilon((points[0],), (points[0],)) == 0.0
    matched = matched_rate_advantages((points[0],), (FrontierPoint("d", 0.3, 0.3, 0.5, 0.5),), frr_tolerance=0.0, uar_tolerance=0.2)
    assert matched["lower_uar_at_matched_frr"] is True


def test_rare_event_hierarchical_and_multiplicity_statistics() -> None:
    low, high = exact_binomial_interval(0, 100, 0.95)
    assert low == 0.0 and 0.03 < high < 0.04
    assert exact_binomial_interval(100, 100)[1] == 1.0
    first = hierarchical_bootstrap_ratio([1, 2, 0], [10, 10, 10], repetitions=100, seed=7)
    second = hierarchical_bootstrap_ratio([1, 2, 0], [10, 10, 10], repetitions=100, seed=7)
    assert first == second
    assert holm_adjust([0.01, 0.04, 0.03]) == (0.03, 0.06, 0.06)
    assert paired_sign_test([1.0] * 10) < 0.01
    assert 0.0 <= paired_sign_test([1.0] * 1500) < 1e-100
