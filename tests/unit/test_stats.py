import pandas as pd

from mavs10d.metrics.stats import bootstrap_ci, metric_distribution, paired_seed_comparison, worst_case_episode


def test_bootstrap_distribution_and_paired_seed_comparison() -> None:
    low, high = bootstrap_ci([0.0, 1.0, 1.0], samples=200)
    assert 0.0 <= low <= high <= 1.0

    distribution = metric_distribution([0.0, 1.0, 1.0])
    assert distribution["mean"] > 0.0
    assert distribution["ci95_low"] <= distribution["ci95_high"]

    frame = pd.DataFrame(
        [
            {"seed": 1, "method_id": "mavs", "reward": 1.0},
            {"seed": 1, "method_id": "base", "reward": 0.0},
            {"seed": 2, "method_id": "mavs", "reward": 0.5},
            {"seed": 2, "method_id": "base", "reward": 0.25},
        ]
    )
    comparison = paired_seed_comparison(
        frame,
        metric="reward",
        treatment_method="mavs",
        baseline_method="base",
    )
    assert comparison["paired_n"] == 2
    assert comparison["mean_delta"] > 0.0


def test_worst_case_episode_orders_by_reward_and_unsafe_acceptance() -> None:
    frame = pd.DataFrame(
        [
            {"episode_id": "good", "reward_sum": 2.0, "unsafe_acceptances": 0},
            {"episode_id": "bad", "reward_sum": -2.0, "unsafe_acceptances": 1},
        ]
    )
    worst = worst_case_episode(frame)
    assert worst.iloc[0]["episode_id"] == "bad"
