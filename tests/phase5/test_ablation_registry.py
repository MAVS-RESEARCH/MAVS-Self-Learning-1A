from __future__ import annotations

from dataclasses import asdict

from mavs10d.ablations.registry import AUTHORITATIVE_CONDITIONS, AblationState, load_ablation_specs


def test_authoritative_a0_a49_registry_has_one_explicit_diff() -> None:
    specs = load_ablation_specs()
    assert len(specs) == 50
    assert [spec.ablation_id for spec in specs] == [f"A{index}" for index in range(50)]
    assert tuple(spec.exact_condition for spec in specs) == AUTHORITATIVE_CONDITIONS
    assert not specs[0].changes
    assert all(len(spec.changes) == 1 for spec in specs[1:])
    base = asdict(AblationState())
    for spec in specs[1:]:
        state = asdict(spec.state())
        assert {key: value for key, value in state.items() if value != base[key]} == dict(spec.changes)
