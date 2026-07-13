from __future__ import annotations

from mavs10d.envs.phase5_transfer import Phase5TransferCompiler


def test_phase5_bank_exact_strata_resets_attack_budget_and_separation() -> None:
    compiler = Phase5TransferCompiler()
    expected_resets = {
        1: {"surface": 150, "structural": 100, "adversarial": 50},
        2: {"surface": 100, "structural": 100, "adversarial": 100},
        3: {"surface": 50, "structural": 100, "adversarial": 150},
    }
    identity_sets = []
    for generation in (1, 2, 3):
        compiled = compiler.compile_generation(generation)
        assert len(compiled.visible_rows) == len(compiled.hidden_rows) == 15000
        assert compiled.manifest["benchmark_strata"] == {
            "corruption_composition_leave_out": 50, "corruption_family_leave_out": 50,
            "domain_leave_out": 50, "generator_leave_out": 50,
            "long_horizon_recurrence": 50, "policy_semantic_transfer": 50,
        }
        assert compiled.manifest["reset_counts"] == expected_resets[generation]
        assert compiled.manifest["adversarial_probes"] == expected_resets[generation]["adversarial"] * 12
        assert not ({"unsafe", "correct_action", "answer_key_hash"} & set(compiled.visible_rows[0]))
        identity_sets.append({row["opportunity_id"] for row in compiled.visible_rows})
    assert not identity_sets[0] & identity_sets[1]
    assert not identity_sets[0] & identity_sets[2]
    assert not identity_sets[1] & identity_sets[2]
