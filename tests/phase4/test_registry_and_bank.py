from __future__ import annotations

from mavs10d.baselines.phase4_registry import load_operating_points
from mavs10d.envs.phase4_tournament import Phase4TournamentCompiler


def test_complete_frozen_registry_has_unique_budgeted_points() -> None:
    points = load_operating_points()
    assert len(points) == 139
    assert len({point.point_id for point in points}) == 139
    assert {point.family for point in points} >= {
        "trivial", "oracle", "mavs_lineage", "selective", "neyman_pearson", "conformal",
        "uncertainty", "guardrails", "critique_verifier", "drift", "online_experts",
        "test_time_adaptation", "pareto", "safe_control", "mavs_sl",
    }
    assert all(set(point.budget) == {"calls", "tokens", "latency_ms", "memory_bytes", "update_compute"} for point in points)


def test_untouched_bank_exact_allocation_mixtures_and_hidden_separation() -> None:
    compiler = Phase4TournamentCompiler()
    expected = {
        1: {"surface": 200, "structural": 175, "adversarial": 125},
        2: {"surface": 150, "structural": 200, "adversarial": 150},
        3: {"surface": 100, "structural": 200, "adversarial": 200},
    }
    identity_sets = []
    for generation in (1, 2, 3):
        compiled = compiler.compile_generation(generation)
        assert len(compiled.visible_rows) == len(compiled.hidden_rows) == 25000
        assert compiled.manifest["world_count"] == 500
        assert compiled.manifest["reset_counts"] == expected[generation]
        assert not ({"unsafe", "correct_action", "catastrophic_if_accepted", "hidden_regime"} & set(compiled.visible_rows[0]))
        identity_sets.append({row["opportunity_id"] for row in compiled.visible_rows})
    assert not identity_sets[0] & identity_sets[1]
    assert not identity_sets[0] & identity_sets[2]
    assert not identity_sets[1] & identity_sets[2]
