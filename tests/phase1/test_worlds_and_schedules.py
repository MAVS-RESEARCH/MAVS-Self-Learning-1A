from __future__ import annotations

from collections import Counter

from mavs10d.corruption.nonstationary import SCHEDULE_FAMILIES, schedule_state
from mavs10d.envs.phase1_gauntlet import DEVELOPMENT_DOMAINS, EVALUATION_DOMAINS, Phase1WorldCompiler
from mavs10d.envs.domain_adapters import DOMAIN_ADAPTERS, get_domain_adapter


def test_all_required_schedule_families_are_bounded_and_recoverable() -> None:
    for family in SCHEDULE_FAMILIES:
        states = [schedule_state(family, "mixed", step, 0.40) for step in range(100)]
        assert all(0.0 <= state.corruption_level <= 0.55 for state in states)
        assert any(state.change_active for state in states)
    assert any(schedule_state("recovery_trap", "mixed", step, 0.40).recovery_active for step in range(100))


def test_evaluation_allocation_is_exact_and_balanced() -> None:
    bank = Phase1WorldCompiler().compile_evaluation(1)
    assert len(bank.visible) == len(bank.hidden) == 15000
    worlds = {(row.domain, row.world_id) for row in bank.visible}
    assert Counter(domain for domain, _ in worlds) == {domain: 30 for domain in EVALUATION_DOMAINS}
    assert Counter(next(row.shift_class for row in bank.visible if row.world_id == world) for _, world in worlds) == {"abrupt": 38, "gradual": 38, "recurring": 37, "mixed": 37}
    assert {row.schedule_family for row in bank.visible} == set(SCHEDULE_FAMILIES)
    assert all(len({row.cost_preference for row in bank.visible if row.world_id == world}) == 3 for _, world in worlds)


def test_all_required_domain_adapters_are_explicit_and_fail_closed() -> None:
    expected = set(EVALUATION_DOMAINS) | set(DEVELOPMENT_DOMAINS)
    assert set(DOMAIN_ADAPTERS) == expected
    assert all(get_domain_adapter(domain).evidence_semantics for domain in expected)
    try:
        get_domain_adapter("undeclared_domain")
    except ValueError:
        pass
    else:
        raise AssertionError("Undeclared domains must fail closed.")


def test_development_and_evaluation_are_domain_seed_and_identity_disjoint() -> None:
    compiler = Phase1WorldCompiler()
    development = compiler.compile_development("train", 1000, worlds_per_domain=2)
    evaluation = compiler.compile_evaluation(1)
    assert set(DEVELOPMENT_DOMAINS).isdisjoint(EVALUATION_DOMAINS)
    assert {row.world_seed for row in development.visible}.isdisjoint(row.world_seed for row in evaluation.visible)
    assert {row.opportunity_id for row in development.visible}.isdisjoint(row.opportunity_id for row in evaluation.visible)
    assert development.manifest["prior_version"] != evaluation.manifest["prior_version"]


def test_censored_and_delayed_feedback_are_never_encoded_as_negative() -> None:
    bank = Phase1WorldCompiler().compile_evaluation(2)
    pairs = list(zip(bank.visible, bank.hidden))
    censored = [(visible, hidden) for visible, hidden in pairs if visible.feedback_release_step is None]
    delayed = [(visible, hidden) for visible, hidden in pairs if visible.feedback_release_step is not None and visible.feedback_release_step > visible.step]
    assert censored and delayed
    assert all(hidden.observed_feedback_label is None for _, hidden in censored)
    assert all(visible.feedback_release_step >= visible.step for visible, _ in delayed)


def test_three_generations_are_independently_regenerated() -> None:
    compiler = Phase1WorldCompiler()
    manifests = [compiler.compile_evaluation(generation).manifest for generation in (1, 2, 3)]
    assert len({item["opportunity_ids_sha256"] for item in manifests}) == 3
    assert [(item["seed_min"], item["seed_max"]) for item in manifests] == [(100000, 100149), (300000, 300149), (500000, 500149)]
