from __future__ import annotations

from collections import Counter
from pathlib import Path

from mavs10d.corruption.phase2 import load_phase2_registry, sample_schedule
from mavs10d.envs.phase2_gauntlet import DEVELOPMENT_DOMAINS, EVALUATION_DOMAINS, SCENARIO_CLASS_COUNTS, Phase2WorldCompiler


ROOT = Path(__file__).resolve().parents[2]


def test_family_and_composition_floors_and_held_out_mechanisms() -> None:
    families, evaluation, development = load_phase2_registry(ROOT)
    assert len(families) == 13
    assert len(evaluation) == 48
    assert all(2 <= len(item.families) <= 4 for item in evaluation)
    development_families = {name for item in development for name in item}
    evaluation_families = {name for item in evaluation for name in item.families}
    assert {"feedback_poisoning", "evidence_source_compromise"}.isdisjoint(development_families)
    assert {"feedback_poisoning", "evidence_source_compromise"} <= evaluation_families


def test_exact_evaluation_allocation_mixture_and_composition_coverage() -> None:
    bank = Phase2WorldCompiler(ROOT).compile_evaluation(1)
    assert len(bank.visible) == len(bank.hidden) == 20000
    worlds = {(row.domain, row.world_id) for row in bank.visible}
    assert Counter(domain for domain, _ in worlds) == {domain: 40 for domain in EVALUATION_DOMAINS}
    classes = {visible.world_id: hidden.scenario_class for visible, hidden in zip(bank.visible, bank.hidden)}
    assert Counter(classes.values()) == SCENARIO_CLASS_COUNTS
    for domain in EVALUATION_DOMAINS:
        domain_classes = {visible.world_id: hidden.scenario_class for visible, hidden in zip(bank.visible, bank.hidden) if visible.domain == domain}
        assert Counter(domain_classes.values()) == {"safe_correlated_agreement": 12, "harmful_collapse": 12, "ambiguous_masking": 8, "mixed": 8}
    assert len({row.composition_id for row in bank.hidden}) == 48
    assert len({family for row in bank.hidden for family in row.corruption_families}) >= 10


def test_development_and_evaluation_are_structurally_disjoint() -> None:
    compiler = Phase2WorldCompiler(ROOT)
    development = compiler.compile_development()
    evaluation = compiler.compile_evaluation(1)
    assert set(DEVELOPMENT_DOMAINS).isdisjoint(EVALUATION_DOMAINS)
    assert {row.world_seed for row in development.visible}.isdisjoint(row.world_seed for row in evaluation.visible)
    assert {row.opportunity_id for row in development.visible}.isdisjoint(row.opportunity_id for row in evaluation.visible)
    assert set(development.manifest["corruption_families"]) != set(evaluation.manifest["corruption_families"])
    assert development.manifest["namespace"] != evaluation.manifest["namespace"]


def test_generation_resets_and_specialist_manifest_bounds() -> None:
    compiler = Phase2WorldCompiler(ROOT)
    banks = [compiler.compile_evaluation(generation) for generation in (1, 2, 3)]
    assert [(bank.manifest["seed_min"], bank.manifest["seed_max"]) for bank in banks] == [(120000, 120199), (320000, 320199), (520000, 520199)]
    assert len({bank.manifest["opportunity_ids_sha256"] for bank in banks}) == 3
    for bank in banks:
        assert all(3 <= len(items) <= 9 for items in bank.specialist_manifests.values())
        assert all(0.15 <= item.diversity <= 0.95 for items in bank.specialist_manifests.values() for item in items)


def test_counterfactuals_preserve_nuisance_and_only_change_evidence_availability() -> None:
    bank = Phase2WorldCompiler(ROOT).compile_evaluation(2)
    for row in bank.visible[::997]:
        assert row.counterfactual_evidence_status != row.evidence_status
        assert len(row.nuisance_hash) == 64
        assert row.world_id in bank.specialist_manifests


def test_schedules_are_bounded_transition_and_recover() -> None:
    families, _, _ = load_phase2_registry(ROOT)
    import numpy as np
    rng = np.random.default_rng(91)
    for family in families.values():
        schedule = sample_schedule(rng, family)
        states = [schedule.state_at(step) for step in range(100)]
        assert all(0.0 <= intensity <= 1.0 for intensity, _, _ in states)
        assert any(active for _, active, _ in states)
        assert any(recovery for _, _, recovery in states)
