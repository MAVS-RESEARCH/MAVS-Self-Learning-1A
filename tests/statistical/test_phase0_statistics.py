from __future__ import annotations

import math

import pytest

from mavs10d.metrics.frontier import FrontierPoint, pareto_frontier
from mavs10d.metrics.stats import wilson_interval
from mavs10d.metrics.transfer import learning_acceleration, negative_transfer_rate


def test_wilson_interval_contains_observed_rate() -> None:
    low, high = wilson_interval(0, 100)
    assert low == 0.0
    assert 0.0 < high < 0.1


def test_pareto_frontier_removes_strictly_dominated_point() -> None:
    strong = FrontierPoint("strong", 0.0, 0.1, 0.2, 1.0)
    weak = FrontierPoint("weak", 0.1, 0.2, 0.3, 2.0)
    assert pareto_frontier([weak, strong]) == (strong,)


def test_transfer_zero_denominator_is_explicit() -> None:
    assert math.isinf(learning_acceleration(2.0, 0.0))
    assert math.isnan(negative_transfer_rate(0, 0))
    with pytest.raises(ValueError):
        negative_transfer_rate(2, 1)
