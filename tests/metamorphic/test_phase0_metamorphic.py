from __future__ import annotations

from mavs10d.metrics.stats import exact_action_metrics


def test_metric_recomputation_is_permutation_invariant() -> None:
    actions = ["accept", "reject", "escalate", "accept", "reject"]
    labels = [False, True, True, True, False]
    expected = exact_action_metrics(actions, labels)
    permutation = [3, 0, 4, 2, 1]
    observed = exact_action_metrics([actions[i] for i in permutation], [labels[i] for i in permutation])
    assert observed == expected


def test_escalation_is_disjoint_from_false_rejection_and_unsafe_acceptance() -> None:
    metrics = exact_action_metrics(["escalate", "escalate"], [False, True])
    assert metrics["unsafe_accepted"] == 0
    assert metrics["false_rejected"] == 0
    assert metrics["accepted"] + metrics["rejected"] + metrics["escalated"] == 2
