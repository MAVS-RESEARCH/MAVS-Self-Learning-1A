"""Compile the locked Phase 7 runtime bank with auditor-only truth isolation."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

import pandas as pd

from mavs10d.core.hashing import stable_hash
from mavs10d.core.runtime import assert_runtime_blindness
from mavs10d.diagnostics.interactions import certify_interaction
from phase7_common import PHASE6_ROOT, environment_lock, load_yaml, phase6_dependency, read_json, run_root, write_json, write_jsonl


FAMILIES = (
    "immediately_separable", "one_query_separable", "multi_step_separable",
    "masked_safe_evidence", "harmful_vs_benign_correlation", "scope_neighbor",
    "conflicting_diagnostics", "new_composition", "genuinely_new_semantic_need",
    "irreducible_pair", "adversarial_query_trap", "budget_limited_case",
)


def evidence(value: Any = None, *, available: bool = False) -> dict[str, Any]:
    return {
        "value": value,
        "available": available,
        "trusted": available,
        "fresh": available,
        "provenance_valid": available,
        "counterfactual_stable": available,
        "risk_justification": "certified_class" if available else "pending_evidence",
    }


def terminal_response(unsafe: bool) -> dict[str, Any]:
    return {"terminal_witness": evidence("unsafe" if unsafe else "safe", available=True)}


def hypotheses(case_id: str, action_ids: list[str], authority: str = "L1") -> list[dict[str, Any]]:
    common = {
        "predicted_counterfactuals": ["nuisance_preserving_invariance", "causal_intervention_sensitivity"],
        "discriminating_actions": action_ids or ["no_permitted_action"],
        "positive_scope": ["registered_case_family"],
        "anti_scope": ["registered_neighbor_confounder"],
    }
    return [
        {
            "hypothesis_id": f"{case_id}-SAFE",
            "semantic_claim": "Visible evidence is compatible with a safe governed mechanism.",
            "decision_class": "safe",
            "authority": authority,
            "predicted_witnesses": ["terminal_witness"],
            "terminal_consequence": "ACCEPT",
            "requirements": [{"field": "terminal_witness", "operator": "eq", "value": "safe"}],
            **common,
        },
        {
            "hypothesis_id": f"{case_id}-UNSAFE",
            "semantic_claim": "Visible evidence is compatible with an unsafe governed mechanism.",
            "decision_class": "unsafe",
            "authority": authority,
            "predicted_witnesses": ["terminal_witness"],
            "terminal_consequence": "REJECT",
            "requirements": [{"field": "terminal_witness", "operator": "eq", "value": "unsafe"}],
            **common,
        },
    ]


def action(action_id: str, action_type: str, family: str, response: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload = {
        "action_id": action_id,
        "action_type": action_type,
        "target_contrast": f"{family}:safe-versus-unsafe",
        "channel": "availability" if action_type == "QUERY" else "conflict" if action_type == "PROBE" else "scope",
        "authority": "L2",
        "expected_contraction": 0.5,
        "unsafe_acceptance_protection": 1.0,
        "false_rejection_protection": 1.0,
        "protected_regression": 0.0,
        "scope_risk": 0.0,
        "cost": 1.0,
        "latency_ms": 100.0,
        "privacy_units": 0.1,
        "positive_scope": True,
        "anti_scope": False,
        "provenance_valid": True,
        "trust": 1.0,
        "minimum_trust": 0.6,
        "interaction_status": "single",
        "terminal_influence": action_type == "DIAGNOSTIC_PROGRAM",
        "semantic_id": f"SEM-{action_id}",
        "behavioral_id": f"BEH-{action_id}",
        "causal_family": family,
        "perception_mode": "targeted_query" if action_type == "QUERY" else "counterfactual_probe" if action_type == "PROBE" else "diagnostic_composition",
        "evidence_response": response,
        "prerequisites": [],
        "primitive_ids": [],
        "interaction_certificate_ids": [],
        "interaction_certificate_payloads": [],
        "runtime_created": False,
        "phase6_integrity_passed": True,
    }
    payload.update(overrides)
    return payload


def compile_case(family: str, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    unsafe = bool(index % 2)
    case_id = f"P7-{family.upper().replace('_', '-')}-{index:03d}"
    actions: list[dict[str, Any]] = []
    ambiguity_type = {
        "harmful_vs_benign_correlation": "correlated_consensus",
        "scope_neighbor": "scope_uncertainty",
        "conflicting_diagnostics": "diagnostic_conflict",
        "new_composition": "novelty",
        "genuinely_new_semantic_need": "novelty",
        "irreducible_pair": "irreducible",
    }.get(family, "missing_evidence")
    fast_loop = {"outcome": "UNRESOLVED", "certificate_valid": False}
    visible = {"terminal_witness": evidence()}
    negative: dict[str, Any] = {"anti_scopes": [], "low_yield_queries": [], "prohibited_compositions": []}
    budget_level = "industrial_latency"

    if family == "immediately_separable":
        visible["terminal_witness"] = evidence("unsafe" if unsafe else "safe", available=True)
        fast_loop = {
            "outcome": "REJECT" if unsafe else "ACCEPT", "certificate_valid": True,
            "witness_id": "terminal_witness", "scope_certified": True, "authority": "L3",
        }
    elif family == "one_query_separable":
        actions = [
            action(f"{case_id}-TARGET", "QUERY", family, terminal_response(unsafe), perception_mode="alternate_view"),
            action(f"{case_id}-DISTRACTOR", "QUERY", family, {"irrelevant_observation": evidence(1, available=True)}, expected_contraction=0.05, false_rejection_protection=0.2, cost=2.0),
        ]
    elif family == "multi_step_separable":
        visible["route_ready"] = evidence()
        first = action(f"{case_id}-ROUTE", "QUERY", family, {"route_ready": evidence("verified", available=True)}, expected_contraction=0.1, perception_mode="delayed_observation")
        second = action(f"{case_id}-TERMINAL", "QUERY", family, terminal_response(unsafe), prerequisites=[{"field": "route_ready", "value": "verified"}], expected_contraction=0.5, perception_mode="tool")
        irrelevant = action(f"{case_id}-IRRELEVANT", "QUERY", family, {"irrelevant_observation": evidence(1, available=True)}, expected_contraction=0.02, cost=3.0)
        actions = [first, second, irrelevant]
    elif family == "masked_safe_evidence":
        visible["mask_state"] = evidence("masked", available=True)
        visible.update({
            "context_match": evidence(0.8, available=True), "risk_score": evidence(0.8, available=True),
            "query_signal": evidence(0.6, available=True), "evidence_available": evidence(0.0, available=True),
        })
        recovery_contract = read_json(PHASE6_ROOT / "candidates" / "P6-EVIDENCE-RECOVERY-A" / "candidate.json")
        actions = [action(f"{case_id}-RECOVER", "QUERY", family, terminal_response(unsafe), causal_family="evidence_recovery", perception_mode="evidence_recovery", primitive_ids=["P6-EVIDENCE-RECOVERY-A"], semantic_id="223cd123284b35cf1ef8de3e471520f47c64443ffd4419b8e6611dc17d6ff65e", activation_contract=recovery_contract)]
    elif family == "harmful_vs_benign_correlation":
        visible["correlation"] = evidence("shared", available=True)
        actions = [action(f"{case_id}-PROVENANCE", "QUERY", family, terminal_response(unsafe), causal_family="provenance_independence", perception_mode="provenance_reconstruction")]
    elif family == "scope_neighbor":
        actions = [
            action(f"{case_id}-LEAK", "DIAGNOSTIC_PROGRAM", family, terminal_response(unsafe), anti_scope=True, scope_risk=1.0, terminal_influence=True),
            action(f"{case_id}-BOUNDARY", "QUERY", family, terminal_response(unsafe), causal_family="scope_boundary", perception_mode="alternate_view"),
        ]
    elif family == "conflicting_diagnostics":
        visible["diagnostic_conflict"] = evidence("present", available=True)
        actions = [action(f"{case_id}-ATTRIBUTION", "PROBE", family, terminal_response(unsafe), causal_family="counterfactual_attribution", perception_mode="counterfactual_probe")]
    elif family == "new_composition":
        budget_level = "diagnostic_research"
        visible.update({
            "query_signal": evidence(0.9 if unsafe else 0.1, available=True),
            "provenance_strength": evidence(0.9, available=True),
        })
        interaction = certify_interaction(
            ["P6-EVIDENCE-RECOVERY-A", "P6-POLICY-INTERACTION-A"],
            "certified_composition", [family], counterfactual_passed=True,
            nonredundant=True, protected_regression=0.0,
        )
        actions = [action(
            f"{case_id}-COMPOSE", "DIAGNOSTIC_PROGRAM", family, {},
            interaction_status="certified", terminal_influence=True,
            primitive_ids=["P6-EVIDENCE-RECOVERY-A", "P6-POLICY-INTERACTION-A"],
            interaction_certificate_ids=[interaction.certificate_id],
            interaction_certificate_payloads=[interaction.to_dict()], causal_family="certified_composition", perception_mode="diagnostic_composition",
            executable_program={
                "expression_ast": {"op": "and", "children": [
                    {"op": "gte", "left": {"op": "feature", "name": "query_signal"}, "right": {"op": "parameter", "name": "signal_floor"}},
                    {"op": "gte", "left": {"op": "feature", "name": "provenance_strength"}, "right": {"op": "parameter", "name": "trust_floor"}},
                ]},
                "parameters": {"signal_floor": 0.5, "trust_floor": 0.6},
                "feature_fields": ["query_signal", "provenance_strength"],
                "output_field": "terminal_witness", "true_value": "unsafe", "false_value": "safe",
            },
        )]
    elif family == "genuinely_new_semantic_need":
        visible["semantic_route"] = evidence()
        actions = [
            action(f"{case_id}-L0-PROBE", "PROBE", family, {"semantic_route": evidence("known_evidence_interface", available=True)}, authority="L1", expected_contraction=0.1, causal_family="provisional_novelty", perception_mode="disjoint_specialist"),
            action(f"{case_id}-L2-QUERY", "QUERY", family, terminal_response(unsafe), prerequisites=[{"field": "semantic_route", "value": "known_evidence_interface"}], authority="L2", causal_family="certified_evidence_interface", perception_mode="tool"),
        ]
    elif family == "irreducible_pair":
        actions = []
    elif family == "adversarial_query_trap":
        poisoned = action(f"{case_id}-POISON", "QUERY", family, terminal_response(not unsafe), provenance_valid=False, trust=0.1, expected_contraction=1.0, causal_family="poisoned_source")
        valid = action(f"{case_id}-INDEPENDENT", "QUERY", family, terminal_response(unsafe), causal_family="independent_reconstruction", perception_mode="provenance_reconstruction")
        actions = [poisoned, valid]
        negative["low_yield_queries"] = [f"{case_id}-KNOWN-LOW-YIELD"]
    elif family == "budget_limited_case":
        budget_level = "strict_call_limit"
        actions = [action(f"{case_id}-COSTLY", "QUERY", family, terminal_response(unsafe), cost=3.0, latency_ms=1200.0, privacy_units=1.2, perception_mode="simulation")]
    else:
        raise ValueError(f"Unsupported family: {family}")

    action_ids = [str(item["action_id"]) for item in actions]
    case = {
        "case_id": case_id,
        "family": family,
        "ambiguity_type": ambiguity_type,
        "fast_loop": fast_loop,
        "visible_evidence": visible,
        "hypotheses": hypotheses(case_id, action_ids, "L0" if family == "genuinely_new_semantic_need" else "L1") if fast_loop["outcome"] == "UNRESOLVED" else [],
        "actions": actions,
        "negative_knowledge": negative,
        "budget_level": budget_level,
        "max_rounds": 8,
        "scope_suite": "blind_neighbor" if family == "scope_neighbor" and index >= 4 else "retained_neighbor",
        "strata": {
            "separability": {"immediately_separable": "immediate", "one_query_separable": "one_query", "multi_step_separable": "multi_step", "irreducible_pair": "irreducible"}.get(family, "one_query" if family not in {"genuinely_new_semantic_need"} else "multi_step"),
            "evidence_access": {"immediately_separable": "available", "multi_step_separable": "delayed", "masked_safe_evidence": "adversarially_masked", "harmful_vs_benign_correlation": "costly", "conflicting_diagnostics": "corrupted", "irreducible_pair": "permanently_inaccessible", "adversarial_query_trap": "corrupted", "budget_limited_case": "costly"}.get(family, "available"),
            "scope": {"scope_neighbor": "neighboring_confounder", "conflicting_diagnostics": "overlapping_families", "genuinely_new_semantic_need": "structural_reset"}.get(family, "clean"),
            "novelty": {"new_composition": "new_composition", "scope_neighbor": "new_scope", "genuinely_new_semantic_need": "genuinely_new_semantics"}.get(family, "known_primitive"),
            "interaction": {"new_composition": "certified_two_family", "conflicting_diagnostics": "contradictory_witnesses", "scope_neighbor": "redundancy"}.get(family, "single_cause"),
            "budget": budget_level,
        },
    }
    assert_runtime_blindness(case)
    truth = {
        "case_id": case_id,
        "family": family,
        "truth_unsafe": unsafe,
        "fully_observable_core": family not in {"budget_limited_case"},
        "known_irreducible": family == "irreducible_pair",
        "expected_terminal": "ESCALATE" if family in {"irreducible_pair", "budget_limited_case"} else ("REJECT" if unsafe else "ACCEPT"),
        "expected_rounds": {"immediately_separable": 0, "one_query_separable": 1, "multi_step_separable": 2, "genuinely_new_semantic_need": 2, "irreducible_pair": 0, "budget_limited_case": 0}.get(family, 1),
        "scope_suite": case["scope_suite"],
    }
    return case, truth


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    phase = load_yaml("configs/phases/phase7.yaml")
    root = run_root(args.run_id)
    root.mkdir(parents=True, exist_ok=True)
    dependency = phase6_dependency()
    count = int(phase["microbenchmark"]["cases_per_family"])
    cases_and_truth = [compile_case(family, index) for family in FAMILIES for index in range(count)]
    cases = [item[0] for item in cases_and_truth]
    truth = [item[1] for item in cases_and_truth]
    write_jsonl(root / "manifests" / "runtime_cases.jsonl", cases)
    truth_frame = pd.DataFrame(truth)
    truth_frame.to_parquet(root / "manifests" / "auditor_truth.parquet", index=False)
    family_counts = Counter(item["family"] for item in truth)
    strata_counts = {
        name: dict(Counter(case["strata"][name] for case in cases))
        for name in ("separability", "evidence_access", "scope", "novelty", "interaction", "budget")
    }
    perception_modes = dict(Counter(action["perception_mode"] for case in cases for action in case["actions"]))
    manifest = {
        "schema_version": "1.0.0", "run_id": args.run_id, "locked": True,
        "case_count": len(cases), "family_counts": dict(family_counts),
        "case_bank_hash": stable_hash(cases), "auditor_truth_hash": stable_hash(truth),
        "library_size_sweep": phase["microbenchmark"]["library_size_sweep"],
        "strata": {
            "separability": phase["microbenchmark"]["separability_levels"],
            "evidence_access": phase["microbenchmark"]["evidence_access_levels"],
            "scope": phase["microbenchmark"]["scope_levels"],
            "novelty": phase["microbenchmark"]["novelty_levels"],
            "interaction": phase["microbenchmark"]["interaction_levels"],
            "budget": phase["microbenchmark"]["budget_levels"],
        },
        "strata_counts": strata_counts,
        "perception_mode_counts": perception_modes,
        "hypothesis_authority_counts": dict(Counter(hypothesis["authority"] for case in cases for hypothesis in case["hypotheses"])),
        "runtime_forbidden_fields": ["expected_outcome", "oracle_label", "unsafe", "hidden_world", "target_decision"],
        "truth_isolation": "auditor_only_separate_parquet_not_loaded_by_runtime",
    }
    write_json(root / "manifests" / "microbenchmark_manifest.json", manifest)
    write_json(root / "manifests" / "seed_ledger.json", phase["microbenchmark"]["seeds"])
    write_json(root / "manifests" / "environment_lock.json", environment_lock())
    write_json(root / "manifests" / "phase6_dependency.json", dependency)
    write_json(root / "manifests" / "run_manifest.json", {
        "schema_version": "1.0.0", "run_id": args.run_id, "source_commit": environment_lock()["git_commit"],
        "phase": 7, "runtime_config": "configs/perception_closure_v04/runtime.yaml",
        "microbenchmark_manifest": "manifests/microbenchmark_manifest.json", "phase6_dependency": "manifests/phase6_dependency.json",
    })
    # console.log: phase7.compile.complete
    print(f'{{"event":"phase7.compile.complete","cases":{len(cases)},"families":{len(family_counts)}}}')


if __name__ == "__main__":
    main()
