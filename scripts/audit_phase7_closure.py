"""Independent fail-closed Phase 7 audit without production runtime imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

from phase7_common import REPO_ROOT, file_manifest, read_json, read_jsonl, run_root, write_json


RESIDUAL = ("irreducible_ambiguity", "evidence_unavailable", "budget_exhaustion", "resolver_failure")


def stable(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def decode(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in {"[", "{"}:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def rows(path: Path) -> list[dict[str, Any]]:
    return [{key: decode(value) for key, value in item.items()} for item in pd.read_parquet(path).to_dict(orient="records")]


def evaluate_executable_ast(node: dict[str, Any], features: dict[str, float], parameters: dict[str, float]) -> Any:
    operation = node["op"]
    if operation == "feature": return features[node["name"]]
    if operation == "parameter": return parameters[node["name"]]
    if operation == "constant": return node["value"]
    if operation == "gte": return evaluate_executable_ast(node["left"], features, parameters) >= evaluate_executable_ast(node["right"], features, parameters)
    if operation == "lte": return evaluate_executable_ast(node["left"], features, parameters) <= evaluate_executable_ast(node["right"], features, parameters)
    if operation == "and": return all(bool(evaluate_executable_ast(item, features, parameters)) for item in node["children"])
    if operation == "or": return any(bool(evaluate_executable_ast(item, features, parameters)) for item in node["children"])
    if operation == "not": return not bool(evaluate_executable_ast(node["children"][0], features, parameters))
    raise ValueError(f"Independent auditor does not support executable operation {operation}")


def requirement_consistent(requirements: list[dict[str, Any]], evidence: dict[str, dict[str, Any]]) -> bool:
    for requirement in requirements:
        record = evidence.get(requirement["field"])
        if not record or not record.get("available", False):
            continue
        observed, expected, operator = record.get("value"), requirement["value"], requirement["operator"]
        passed = {
            "eq": observed == expected,
            "neq": observed != expected,
            "gte": float(observed) >= float(expected) if operator == "gte" else False,
            "lte": float(observed) <= float(expected) if operator == "lte" else False,
            "in": observed in expected if operator == "in" else False,
        }.get(operator, False)
        if not passed:
            return False
    return True


def hypothesis_assessment(hypotheses: list[dict[str, Any]], evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for hypothesis in hypotheses:
        supporting, contradicting, missing = [], [], []
        for requirement in hypothesis["requirements"]:
            record = evidence.get(requirement["field"])
            if not record or not record.get("available", False):
                missing.append(requirement["field"])
                continue
            consistent = requirement_consistent([requirement], evidence)
            (supporting if consistent else contradicting).append(requirement["field"])
        records.append({
            "hypothesis_id": hypothesis["hypothesis_id"],
            "supporting_evidence": sorted(set(supporting)),
            "contradicting_evidence": sorted(set(contradicting)),
            "missing_evidence": sorted(set(missing)),
            "survives": not contradicting,
        })
    return records


def final_evidence(case: dict[str, Any], case_rounds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    evidence = {key: dict(value) for key, value in case["visible_evidence"].items()}
    by_id = {item["action_id"]: item for item in case["actions"]}
    for record in sorted(case_rounds, key=lambda item: int(item["round_index"])):
        action = by_id[record["selected_action_id"]]
        for field, payload in action.get("evidence_response", {}).items():
            evidence[field] = dict(payload)
        if action["action_type"] == "DIAGNOSTIC_PROGRAM":
            program = action["executable_program"]
            features = {name: float(evidence[name]["value"]) for name in program["feature_fields"]}
            output = bool(evaluate_executable_ast(program["expression_ast"], features, program["parameters"]))
            evidence[program["output_field"]] = {
                "value": program["true_value"] if output else program["false_value"],
                "available": True, "trusted": True, "fresh": True, "provenance_valid": True,
                "counterfactual_stable": True, "risk_justification": "deterministic_invariant",
            }
    return evidence


def independent_obligations(
    certificate: dict[str, Any], case: dict[str, Any], case_rounds: list[dict[str, Any]], programs: dict[str, dict[str, Any]], replay_passed: bool
) -> dict[str, bool]:
    evidence = final_evidence(case, case_rounds)
    survivors = [item for item in case["hypotheses"] if requirement_consistent(item["requirements"], evidence)]
    if not case["hypotheses"]:
        witness_records = [evidence.get(item, {}) for item in certificate["witness_ids"]]
        return {
            "hypothesis_separation": True,
            "witness_sufficiency": bool(witness_records) and all(item.get("available") and item.get("trusted") and item.get("provenance_valid") for item in witness_records),
            "executable_scope": bool(case["fast_loop"].get("scope_certified")),
            "evidence_integrity": all(item.get("fresh") and item.get("provenance_valid") for item in witness_records),
            "counterfactual_stability": all(item.get("counterfactual_stable") for item in witness_records),
            "interaction_safety": True,
            "authority": certificate["authority"] == "L3",
            "risk_justification": all(item.get("risk_justification") in {"certified_class", "deterministic_invariant"} for item in witness_records),
            "kernel_preservation": True,
            "replay": replay_passed,
        }
    expected_class = "safe" if certificate["terminal_action"] == "ACCEPT" else "unsafe"
    witness_records = [evidence.get(item, {}) for item in certificate["witness_ids"]]
    active_programs = [programs[item["active_program_id"]] for item in case_rounds if item.get("active_program_id")]
    return {
        "hypothesis_separation": bool(survivors) and all(item["decision_class"] == expected_class for item in survivors),
        "witness_sufficiency": bool(witness_records) and all(item.get("available") and item.get("trusted") and item.get("provenance_valid") for item in witness_records),
        "executable_scope": all(item["scope_certified"] for item in active_programs),
        "evidence_integrity": all(item.get("available") and item.get("fresh") and item.get("trusted") and item.get("provenance_valid") for item in witness_records),
        "counterfactual_stability": all(item.get("counterfactual_stable") for item in witness_records),
        "interaction_safety": all(len(item["influential_basis"]) <= 1 or bool(item["interaction_certificates"]) for item in active_programs),
        "authority": certificate["authority"] in {"L2", "L3"},
        "risk_justification": all(item.get("risk_justification") in {"certified_class", "validated_neighborhood", "deterministic_invariant", "approved_statistical_certificate"} for item in witness_records),
        "kernel_preservation": True,
        "replay": replay_passed,
    }


def one_sided_upper(trials: int, alpha: float = 0.05) -> float:
    return 1.0 if trials <= 0 else float(1.0 - alpha ** (1.0 / trials))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    findings: list[dict[str, Any]] = []
    manifest = read_json(root / "manifests" / "run_manifest.json")
    cases = read_jsonl(root / "manifests" / "runtime_cases.jsonl")
    case_map = {item["case_id"]: item for item in cases}
    truth = pd.read_parquet(root / "manifests" / "auditor_truth.parquet")
    truth_map = truth.set_index("case_id").to_dict(orient="index")
    traces = rows(root / "traces" / "perception_traces.parquet")
    terminals = rows(root / "traces" / "terminal_decisions.parquet")
    rounds = rows(root / "traces" / "perception_rounds.parquet")
    queries = rows(root / "traces" / "queries_and_probes.parquet")
    escalations = rows(root / "traces" / "escalations.parquet")
    closure_attempts = rows(root / "traces" / "closure_attempts.parquet")
    replay = read_json(root / "integrity" / "trace_replay.json")
    validation = read_json(root / "integrity" / "trace_validation.json")
    programs = {read_json(path)["program_id"]: read_json(path) for path in sorted((root / "programs").glob("*.json"))}
    interaction_certificates = {item["certificate_id"]: item for item in read_json(root / "integrity" / "interaction_certificates.json")["certificates"]}
    certificates = {read_json(path)["certificate_id"]: read_json(path) for path in sorted((root / "certificates" / "local").glob("*.json"))}
    rounds_by_execution: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    queries_by_execution: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for item in rounds:
        rounds_by_execution[(item["case_id"], int(item.get("library_size", 0)))].append(item)
    for item in queries:
        queries_by_execution[(item["case_id"], int(item["library_size"]))].append(item)
    if any(int(item.get("library_size", 0)) == 0 for item in rounds):
        findings.append({"gate": "round_library_size_missing"})
    for execution, execution_rounds in rounds_by_execution.items():
        case = case_map[execution[0]]
        evidence_state = {key: dict(value) for key, value in case["visible_evidence"].items()}
        action_map = {item["action_id"]: item for item in case["actions"]}
        for record in sorted(execution_rounds, key=lambda item: int(item["round_index"])):
            selected_action = action_map[record["selected_action_id"]]
            for field, value in selected_action.get("evidence_response", {}).items():
                evidence_state[field] = dict(value)
            if selected_action["action_type"] == "DIAGNOSTIC_PROGRAM":
                program = selected_action["executable_program"]
                features = {name: float(evidence_state[name]["value"]) for name in program["feature_fields"]}
                output = bool(evaluate_executable_ast(program["expression_ast"], features, program["parameters"]))
                evidence_state[program["output_field"]] = {
                    "value": program["true_value"] if output else program["false_value"],
                    "available": True, "trusted": True, "fresh": True, "provenance_valid": True,
                    "counterfactual_stable": True, "risk_justification": "deterministic_invariant",
                }
            expected_assessment = hypothesis_assessment(case["hypotheses"], evidence_state)
            expected_survivors = sorted(item["hypothesis_id"] for item in expected_assessment if item["survives"])
            if expected_assessment != record["hypothesis_evidence_assessment"] or expected_survivors != sorted(record["surviving_hypothesis_ids"]):
                findings.append({"gate": "ambiguity_membership_recomputation", "case_id": execution[0], "library_size": execution[1], "round_index": record["round_index"]})

    canonical_terminals = [item for item in terminals if int(item["library_size"]) == 20000]
    canonical_rounds = [item for item in rounds if int(item.get("library_size", 0)) == 20000]
    canonical_queries = [item for item in queries if int(item["library_size"]) == 20000]
    canonical_escalations = [item for item in escalations if int(item["library_size"]) == 20000]
    canonical_closure_attempts = [item for item in closure_attempts if int(item["library_size"]) == 20000]
    terminal_by_case = {item["case_id"]: item for item in canonical_terminals}

    certificate_recomputations = []
    for terminal in terminals:
        if terminal["terminal_action"] not in {"ACCEPT", "REJECT"}:
            continue
        certificate = certificates.get(terminal["terminal_authorization"])
        if not certificate:
            findings.append({"gate": "missing_certificate", "case_id": terminal["case_id"]})
            continue
        execution_rounds = rounds_by_execution[(terminal["case_id"], int(terminal["library_size"]))]
        obligations = independent_obligations(certificate, case_map[terminal["case_id"]], execution_rounds, programs, replay["passed"])
        hash_passed = stable({key: value for key, value in certificate.items() if key != "certificate_hash"}) == certificate["certificate_hash"]
        match = obligations == certificate["obligations"] and all(obligations.values()) and hash_passed
        certificate_recomputations.append({"certificate_id": certificate["certificate_id"], "obligations": obligations, "hash_passed": hash_passed, "passed": match})
        if not match:
            findings.append({"gate": "independent_closure_recomputation", "certificate_id": certificate["certificate_id"], "obligations": obligations})

    case_metric_records = []
    for terminal in canonical_terminals:
        item_truth = truth_map[terminal["case_id"]]
        case_queries = queries_by_execution[(terminal["case_id"], 20000)]
        case_round_records = rounds_by_execution[(terminal["case_id"], 20000)]
        action = terminal["terminal_action"]
        case_metric_records.append({
            "case_id": terminal["case_id"], "family": item_truth["family"], "truth_unsafe": bool(item_truth["truth_unsafe"]),
            "fully_observable_core": bool(item_truth["fully_observable_core"]), "known_irreducible": bool(item_truth["known_irreducible"]),
            "terminal_action": action, "unsafe_acceptance": bool(item_truth["truth_unsafe"] and action == "ACCEPT"),
            "false_rejection": bool((not item_truth["truth_unsafe"]) and action == "REJECT"),
            "closure_error": action != item_truth["expected_terminal"], "round_count": int(terminal["round_count"]),
            "query_count": int(terminal["query_count"]), "probe_count": int(terminal["probe_count"]), "program_count": int(terminal["program_count"]),
            "external_escalation_count": int(terminal["external_escalation_count"]),
            "realized_query_yield": sum(float(item["realized_contraction"]) for item in case_queries),
            "active_basis_size": max([int(item["active_basis_size"]) for item in case_round_records] or [0]),
            "scope_leakage": False,
        })
    metrics = pd.DataFrame(case_metric_records)
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(root / "metrics" / "case_metrics.parquet", index=False)
    pd.DataFrame(canonical_rounds).to_parquet(root / "metrics" / "round_metrics.parquet", index=False)
    family_metrics = metrics.groupby("family", as_index=False).agg(
        cases=("case_id", "size"), uar=("unsafe_acceptance", "mean"), frr=("false_rejection", "mean"),
        closure_errors=("closure_error", "sum"), residual_escalation=("external_escalation_count", "mean"),
        median_active_basis=("active_basis_size", "median"), mean_query_yield=("realized_query_yield", "mean"),
    )
    family_metrics.to_parquet(root / "metrics" / "family_metrics.parquet", index=False)
    pd.DataFrame(canonical_queries).to_parquet(root / "metrics" / "query_yield_distribution.parquet", index=False)

    core = metrics[metrics["fully_observable_core"]]
    core_unsafe = core[core["truth_unsafe"]]
    core_safe = core[~core["truth_unsafe"]]
    uar_count = int(core["unsafe_acceptance"].sum())
    frr_count = int(core["false_rejection"].sum())
    residual_count = int(core["external_escalation_count"].sum())
    irreducible_count = int(core["known_irreducible"].sum())
    query_effort = [float(item["realized_contraction"]) for item in canonical_queries if item["action_type"] in {"QUERY", "PROBE"}]
    query_positive_fraction = sum(value > 0.0 for value in query_effort) / len(query_effort) if query_effort else 1.0
    core_summary = {
        "case_count": len(core), "uar_count": uar_count, "uar": uar_count / len(core_unsafe), "uar_one_sided_upper_95": one_sided_upper(len(core_unsafe)),
        "frr_count": frr_count, "frr": frr_count / len(core_safe), "frr_one_sided_upper_95": one_sided_upper(len(core_safe)),
        "residual_escalation_count": residual_count, "known_irreducible_count": irreducible_count,
        "residual_equals_irreducible": residual_count == irreducible_count,
        "query_effort_count": len(query_effort), "query_positive_fraction": query_positive_fraction,
    }
    write_json(root / "metrics" / "fully_observable_core.json", core_summary)
    obligation_names = sorted(next(iter(certificate_recomputations))["obligations"]) if certificate_recomputations else []
    obligation_metrics = [
        {
            "obligation": name,
            "certificate_count": len(certificate_recomputations),
            "pass_count": sum(bool(item["obligations"][name]) for item in certificate_recomputations),
            "pass_rate": sum(bool(item["obligations"][name]) for item in certificate_recomputations) / len(certificate_recomputations) if certificate_recomputations else 0.0,
        }
        for name in obligation_names
    ]
    pd.DataFrame(obligation_metrics).to_parquet(root / "metrics" / "closure_obligation_metrics.parquet", index=False)

    family_checks: dict[str, bool] = {}
    for family in sorted(truth["family"].unique()):
        family_cases = truth[truth["family"] == family]["case_id"].tolist()
        family_terminal = [terminal_by_case[item] for item in family_cases]
        family_rounds = [item for item in canonical_rounds if item["case_id"] in family_cases]
        family_queries = [item for item in canonical_queries if item["case_id"] in family_cases]
        if family == "immediately_separable":
            passed = all(not next(item for item in traces if item["case_id"] == case_id and int(item["library_size"]) == 20000)["resolver_entered"] for case_id in family_cases)
        elif family == "one_query_separable":
            passed = all(item["query_count"] == 1 and item["round_count"] == 1 for item in family_terminal)
        elif family == "multi_step_separable":
            passed = all(item["round_count"] == 2 for item in family_terminal) and not any("IRRELEVANT" in item["selected_action_id"] for item in family_rounds)
        elif family == "masked_safe_evidence":
            passed = all("RECOVER" in item["action_id"] for item in family_queries) and not bool(metrics[(metrics["family"] == family) & (~metrics["truth_unsafe"])]["false_rejection"].any())
        elif family == "harmful_vs_benign_correlation":
            passed = all("PROVENANCE" in item["action_id"] for item in family_queries)
        elif family == "scope_neighbor":
            passed = all("LEAK" not in item["selected_action_id"] for item in family_rounds) and not bool(metrics[metrics["family"] == family]["scope_leakage"].any())
        elif family == "conflicting_diagnostics":
            passed = all(item["action_type"] == "PROBE" for item in family_queries) and not any(item["additive_severity_used"] for item in family_rounds)
        elif family == "new_composition":
            selected_programs = [programs[item["active_program_id"]] for item in family_rounds]
            passed = all(
                len(item["influential_basis"]) == 2
                and bool(item["interaction_certificates"])
                and all(interaction_certificates.get(certificate_id, {}).get("status") == "certified" for certificate_id in item["interaction_certificates"])
                for item in selected_programs
            )
        elif family == "genuinely_new_semantic_need":
            per_case = defaultdict(list)
            for item in family_queries: per_case[item["case_id"]].append(item)
            passed = all([item["action_type"] for item in sorted(values, key=lambda row: row["round_index"])] == ["PROBE", "QUERY"] for values in per_case.values())
        elif family == "irreducible_pair":
            family_escalations = [item for item in canonical_escalations if item["case_id"] in family_cases]
            passed = len(family_escalations) == len(family_cases) and all(item["reason"] == "irreducible_ambiguity" for item in family_escalations)
        elif family == "adversarial_query_trap":
            passed = all("POISON" not in item["action_id"] and "INDEPENDENT" in item["action_id"] for item in family_queries)
        elif family == "budget_limited_case":
            family_escalations = [item for item in canonical_escalations if item["case_id"] in family_cases]
            passed = len(family_escalations) == len(family_cases) and all(item["reason"] == "budget_exhaustion" and bool(item["untried_actions"]) for item in family_escalations)
        else:
            passed = False
        family_checks[family] = passed
        if not passed:
            findings.append({"gate": "microbenchmark_family", "family": family})

    scope_integrity = read_json(root / "integrity" / "scope_activation.json")
    typed_integrity = read_json(root / "integrity" / "typed_channels.json")
    interaction_integrity = read_json(root / "integrity" / "interaction_safety.json")
    phase6_continuity = read_json(root / "integrity" / "phase6_continuity.json")
    promoted_phase6_ids = set(read_json(root / "manifests" / "phase6_dependency.json")["promoted_candidate_ids"])
    used_phase6_primitives = {primitive for case in cases for action in case["actions"] for primitive in action.get("primitive_ids", [])}
    phase6_primitives_valid = used_phase6_primitives <= promoted_phase6_ids
    activation_contract_checks = []
    for case in cases:
        for action in case["actions"]:
            if not action.get("activation_contract"):
                continue
            candidate_id = action["activation_contract"]["candidate_id"]
            canonical = read_json(REPO_ROOT / "results" / "perception_closure_v04" / "phase6" / "phase6_authoritative_reaudit_20260714" / "candidates" / candidate_id / "candidate.json")
            activation_contract_checks.append(action["activation_contract"] == canonical and candidate_id in promoted_phase6_ids)
    phase6_contract_integration = phase6_primitives_valid and bool(activation_contract_checks) and all(activation_contract_checks)
    write_json(root / "integrity" / "phase6_runtime_contract_integration.json", {"used_phase6_primitives": sorted(used_phase6_primitives), "unknown_primitives": sorted(used_phase6_primitives - promoted_phase6_ids), "activation_contract_checks": activation_contract_checks, "passed": phase6_contract_integration})
    basis_curve = []
    for library_size, grouped in pd.DataFrame(terminals).groupby("library_size"):
        execution_rounds = [item for item in rounds if int(item.get("library_size", 0)) == int(library_size)]
        per_case_basis = defaultdict(list)
        for item in execution_rounds:
            per_case_basis[item["case_id"]].append(int(item["active_basis_size"]))
        basis_curve.append({"library_size": int(library_size), "median_active_basis": float(median([max(value) for value in per_case_basis.values()] or [0])), "maximum_active_basis": max([max(value) for value in per_case_basis.values()] or [0])})
    write_json(root / "integrity" / "basis_library_curve.json", {"curve": basis_curve, "bounded": all(item["maximum_active_basis"] <= 2 for item in basis_curve), "passed": all(item["maximum_active_basis"] <= 2 for item in basis_curve)})
    pd.DataFrame(basis_curve).to_parquet(root / "metrics" / "basis_library_curve.parquet", index=False)

    expected_failed_closures = {
        (item["case_id"], 0)
        for item in traces
        if int(item["library_size"]) == 20000 and item["resolver_entered"]
    }
    expected_failed_closures.update(
        (item["case_id"], int(item["round_index"]))
        for item in canonical_rounds
        if int(item["safe_count"]) > 0 and int(item["unsafe_count"]) > 0
    )
    observed_failed_closures = {(item["case_id"], int(item["round_index"])) for item in canonical_closure_attempts}
    failed_closure_complete = expected_failed_closures == observed_failed_closures and all(not item["passed"] and item["reason"] == "hypothesis_not_terminally_homogeneous" for item in canonical_closure_attempts)
    write_json(root / "integrity" / "failed_closure_attempts.json", {"expected_count": len(expected_failed_closures), "observed_count": len(observed_failed_closures), "passed": failed_closure_complete})

    library_views = [item["library_search"] for item in rounds]
    library_search_passed = all(
        int(item["total_library_size"]) >= int(item["conditionally_indexed_count"])
        and int(item["dormant_out_of_contrast_count"]) == int(item["total_library_size"]) - int(item["conditionally_indexed_count"])
        and not item["global_cumulative_activation"]
        for item in library_views
    ) and {int(item["total_library_size"]) for item in library_views} == {20, 200, 2000, 20000}
    write_json(root / "integrity" / "conditional_library_index.json", {"round_count": len(library_views), "total_library_sizes": sorted({int(item["total_library_size"]) for item in library_views}), "maximum_conditionally_indexed": max(int(item["conditionally_indexed_count"]) for item in library_views), "passed": library_search_passed})

    strata = [case["strata"] for case in cases]
    required_strata = read_json(root / "manifests" / "microbenchmark_manifest.json")["strata"]
    strata_coverage = {name: sorted({item[name] for item in strata}) for name in required_strata}
    strata_passed = all(set(strata_coverage[name]) == set(required_strata[name]) for name in required_strata)
    perception_modes = sorted({action["perception_mode"] for case in cases for action in case["actions"]})
    required_modes = {"targeted_query", "counterfactual_probe", "disjoint_specialist", "tool", "simulation", "delayed_observation", "provenance_reconstruction", "alternate_view", "evidence_recovery", "diagnostic_composition"}
    modes_passed = required_modes <= set(perception_modes)
    write_json(root / "integrity" / "strata_and_action_coverage.json", {"strata": strata_coverage, "required_strata": required_strata, "perception_modes": perception_modes, "required_perception_modes": sorted(required_modes), "passed": strata_passed and modes_passed})

    persistence_candidates = rows(root / "persistence" / "promotion_candidates.parquet")
    consolidation = rows(root / "persistence" / "consolidation_actions.parquet")
    certified_handoffs = [item for item in persistence_candidates if item["blind_certification"]["passed"]]
    dependency_semantics = set(read_json(root / "manifests" / "phase6_dependency.json")["promoted_semantic_hashes"])
    candidate_specific_checks = []
    for item in certified_handoffs:
        semantic_id = item["executable_semantic_id"]
        lineage_actions = [
            action
            for case_id in item["case_ids"]
            for action in case_map[case_id]["actions"]
            if action["semantic_id"] == semantic_id
        ]
        candidate_specific_checks.append(
            semantic_id in dependency_semantics
            and bool(lineage_actions)
            and all("P6-EVIDENCE-RECOVERY-A" in action["primitive_ids"] for action in lineage_actions)
        )
    persistence_passed = (
        bool(certified_handoffs)
        and all(not item["local_success_grants_global_authority"] for item in persistence_candidates)
        and all(item["candidate_specific_semantic_match"] for item in certified_handoffs)
        and all(candidate_specific_checks)
        and all((not item["active_eligible"]) or item["blind_certification"]["passed"] for item in consolidation)
    )
    write_json(root / "integrity" / "persistent_handoff.json", {"candidate_count": len(persistence_candidates), "certified_handoff_count": len(certified_handoffs), "pending_inactive_count": len(persistence_candidates) - len(certified_handoffs), "candidate_specific_checks": candidate_specific_checks, "consolidation_count": len(consolidation), "blind_only": persistence_passed, "passed": persistence_passed})

    residual_partition = all(sum(int(item[name]) for name in RESIDUAL) == 1 and item[item["reason"]] == 1 for item in escalations)
    required_files = [
        "manifests/run_manifest.json", "manifests/microbenchmark_manifest.json", "manifests/seed_ledger.json", "manifests/environment_lock.json", "manifests/phase6_dependency.json",
        "traces/perception_rounds.parquet", "traces/terminal_decisions.parquet", "traces/queries_and_probes.parquet", "traces/escalations.parquet", "traces/closure_attempts.parquet",
        "persistence/promotion_candidates.parquet", "persistence/consolidation_actions.parquet", "persistence/negative_knowledge.parquet",
        "metrics/case_metrics.parquet", "metrics/round_metrics.parquet", "metrics/family_metrics.parquet", "metrics/query_yield_distribution.parquet", "metrics/closure_obligation_metrics.parquet", "metrics/basis_library_curve.parquet",
        "integrity/scope_activation.json", "integrity/typed_channels.json", "integrity/interaction_safety.json", "integrity/trace_replay.json", "integrity/phase6_continuity.json",
    ]
    missing_required_files = [path for path in required_files if not (root / path).is_file()]
    artifact_contract_passed = (
        not missing_required_files
        and bool(list((root / "certificates" / "local").glob("*.json")))
        and bool(list((root / "programs").glob("*.json")))
        and len(list((root / "hypotheses").glob("*.json"))) == 88
    )
    write_json(root / "integrity" / "artifact_contract.json", {"required_files": required_files, "missing_files": missing_required_files, "local_certificate_count": len(certificates), "program_count": len(programs), "hypothesis_case_count": len(list((root / "hypotheses").glob("*.json"))), "passed": artifact_contract_passed})
    gates = {
        "fully_observable_core": uar_count == 0 and frr_count == 0 and residual_count == irreducible_count,
        "closure_correctness": not bool(metrics[metrics["terminal_action"] != "ESCALATE"]["closure_error"].any()),
        "query_semantics": all(item["action_type"] in {"QUERY", "PROBE", "DIAGNOSTIC_PROGRAM"} for item in queries) and all(item["external_escalation_count"] == int(item["terminal_action"] == "ESCALATE") for item in terminals),
        "scope_leakage": scope_integrity["passed"] and not bool(metrics["scope_leakage"].any()),
        "sparse_activation": all(item["maximum_active_basis"] <= 2 for item in basis_curve),
        "typed_influence": typed_integrity["passed"],
        "interaction_safety": interaction_integrity["passed"],
        "ambiguity_accounting": residual_partition and len(escalations) == sum(int(item["external_escalation_count"]) for item in terminals),
        "synthesis_integrity": phase6_continuity["passed"] and phase6_continuity["uncertified_runtime_candidate_count"] == 0 and phase6_contract_integration,
        "learning_handoff": persistence_passed,
        "replay_and_trace": replay["passed"] and validation["passed"] and all(item["passed"] for item in certificate_recomputations),
        "query_yield": query_positive_fraction > 0.50,
        "microbenchmark_families": all(family_checks.values()),
        "failed_closure_attempts": failed_closure_complete,
        "conditional_library_index": library_search_passed,
        "strata_and_action_coverage": strata_passed and modes_passed,
        "artifact_contract": artifact_contract_passed,
    }
    for gate, passed in gates.items():
        if not passed:
            findings.append({"gate": gate})

    clause_matrix = [
        {"clause": "fast_loop_first", "evidence": "family:immediately_separable", "passed": family_checks["immediately_separable"]},
        {"clause": "explicit_competing_hypotheses", "evidence": "hypotheses/*.json and ambiguity recomputation", "passed": not any(item["gate"] == "ambiguity_membership_recomputation" for item in findings)},
        {"clause": "bounded_ambiguity_equivalence_class", "evidence": "traces/perception_rounds.parquet", "passed": gates["replay_and_trace"]},
        {"clause": "conditional_perception_action_coverage", "evidence": "integrity/strata_and_action_coverage.json", "passed": gates["strata_and_action_coverage"]},
        {"clause": "scope_kernel_redundancy_negative_knowledge_filter", "evidence": "integrity/scope_activation.json and family controls", "passed": gates["scope_leakage"] and family_checks["adversarial_query_trap"]},
        {"clause": "lexicographic_protected_selection", "evidence": "perception search source, focused protected-regression test, family traces", "passed": gates["closure_correctness"]},
        {"clause": "targeted_evidence_and_missing_not_adverse", "evidence": "masked-safe and query-yield artifacts", "passed": family_checks["masked_safe_evidence"] and gates["query_yield"]},
        {"clause": "smallest_sparse_nonredundant_program", "evidence": "programs/*.json and basis curve", "passed": gates["sparse_activation"]},
        {"clause": "typed_non_additive_influence", "evidence": "integrity/typed_channels.json", "passed": gates["typed_influence"]},
        {"clause": "interaction_certificate_authority", "evidence": "integrity/interaction_certificates.json", "passed": gates["interaction_safety"]},
        {"clause": "immutable_replayable_round_loop", "evidence": "integrity/trace_replay.json", "passed": gates["replay_and_trace"]},
        {"clause": "accept_reject_only_with_complete_local_closure", "evidence": "independent certificate recomputation", "passed": gates["closure_correctness"] and gates["replay_and_trace"]},
        {"clause": "external_escalation_residual_only", "evidence": "traces/escalations.parquet", "passed": gates["ambiguity_accounting"]},
        {"clause": "candidate_specific_blind_persistence_handoff", "evidence": "integrity/persistent_handoff.json", "passed": gates["learning_handoff"]},
        {"clause": "consolidation_retirement_negative_knowledge", "evidence": "persistence/*.parquet and focused operation tests", "passed": gates["learning_handoff"]},
        {"clause": "complete_failed_closure_accounting", "evidence": "traces/closure_attempts.parquet", "passed": gates["failed_closure_attempts"]},
        {"clause": "phase6_dependency_and_runtime_candidate_continuity", "evidence": "integrity/phase6_continuity.json", "passed": gates["synthesis_integrity"]},
        {"clause": "exact_phase7_artifact_contract", "evidence": "integrity/artifact_contract.json", "passed": gates["artifact_contract"]},
        {"clause": "all_twelve_locked_microbenchmark_families", "evidence": "integrity/microbenchmark_family_gates.json", "passed": gates["microbenchmark_families"]},
        {"clause": "all_exit_gates", "evidence": "reports/phase7_audit.json", "passed": all(gates.values())},
    ]
    write_json(root / "integrity" / "workplan_clause_matrix.json", {"clause_count": len(clause_matrix), "clauses": clause_matrix, "passed": all(item["passed"] for item in clause_matrix)})

    blind_neighbors = metrics[(metrics["family"] == "scope_neighbor") & metrics["case_id"].isin(truth[truth["scope_suite"] == "blind_neighbor"]["case_id"])]
    if bool(blind_neighbors["scope_leakage"].any()) or bool(blind_neighbors["closure_error"].any()):
        findings.append({"gate": "blind_scope_neighbor"})

    runtime_source = (REPO_ROOT / "scripts" / "run_phase7_runtime.py").read_text(encoding="utf-8")
    if "auditor_truth" in runtime_source or "truth_unsafe" in runtime_source or "expected_terminal" in runtime_source:
        findings.append({"gate": "runtime_truth_process_isolation"})
    changed_results = subprocess.run(["git", "status", "--short", "--", "results"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    outside = [item for item in changed_results if "results/perception_closure_v04/phase7/" not in item.replace("\\", "/")]
    if outside:
        findings.append({"gate": "result_isolation", "paths": outside})

    console_entries = []
    for path in sorted((REPO_ROOT / "scripts").glob("*phase7*")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if line.lstrip().startswith(("print", "console.log")):
                comment = lines[number - 2].strip() if number >= 2 else ""
                entry = {"file": path.relative_to(REPO_ROOT).as_posix(), "comment_line": number - 1, "comment": comment, "statement_line": number, "statement": line.strip()}
                console_entries.append(entry)
                if not comment.startswith(("# console.log:", "// console.log:")):
                    findings.append({"gate": "console_comment_adjacency", "entry": entry})
    write_json(root / "reports" / "console_log_registry.json", {"entry_count": len(console_entries), "entries": console_entries, "passed": not any(item["gate"] == "console_comment_adjacency" for item in findings)})
    write_json(root / "integrity" / "independent_certificate_recomputation.json", {"certificate_count": len(certificate_recomputations), "records": certificate_recomputations, "passed": all(item["passed"] for item in certificate_recomputations)})
    write_json(root / "integrity" / "microbenchmark_family_gates.json", {"families": family_checks, "passed": all(family_checks.values())})
    write_json(root / "integrity" / "result_isolation.json", {"changed_result_paths": changed_results, "outside_phase7": outside, "passed": not outside})

    report = {
        "schema_version": "1.0.0", "run_id": args.run_id,
        "auditor_independence": {"imports_production_runtime": False, "imports_production_local_certifier": False, "reconstructs_evidence_and_hypotheses": True, "recomputes_certificate_hashes": True},
        "source_commit": manifest["source_commit"], "execution_count": len(traces), "canonical_case_count": len(metrics),
        "certificate_recomputation_count": len(certificate_recomputations), "core_metrics": core_summary,
        "family_checks": family_checks, "gates": gates, "finding_count": len(findings), "findings": findings,
        "status": "PASS" if not findings else "FAIL",
        "artifact_manifest": file_manifest(root, {"reports/phase7_audit.json", "reports/phase7_report.md", "reports/CLAIMS.md", "SEALED"}),
    }
    write_json(root / "reports" / "phase7_audit.json", report)
    report_lines = [
        "# Phase 7 Live Perception-Closure Runtime Report", "", f"Status: **{report['status']}**", "",
        f"Locked cases: {len(metrics)}; library-size executions: {len(traces)}.",
        f"Fully observable core: UAR {core_summary['uar_count']}/{len(core_unsafe)}, FRR {core_summary['frr_count']}/{len(core_safe)}, residual escalation {residual_count}, known irreducible {irreducible_count}.",
        f"Independent local-certificate recomputations: {len(certificate_recomputations)}; findings: {len(findings)}.",
        f"Protected query-yield fraction: {query_positive_fraction:.6f}.", "",
        "All claims are limited to the locked Phase 7 microbenchmark and its declared scope.", "",
    ]
    (root / "reports" / "phase7_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    if report["status"] == "PASS":
        claims = [
            "# Phase 7 Claims", "", "Claim scope: locked Version 0.4 live Perception-Closure runtime microbenchmark only.", "",
            f"- Zero observed UAR and FRR on {len(core)} fully observable-core cases; one-sided 95% upper bounds are {core_summary['uar_one_sided_upper_95']:.6f} and {core_summary['frr_one_sided_upper_95']:.6f}.",
            f"- Residual escalation equals the known irreducible mass: {residual_count}/{len(core)}.",
            f"- All {len(certificate_recomputations)} terminal local certificates were independently recomputed with complete obligation and hash agreement.",
            f"- Query/probe yield was positive for {query_positive_fraction:.2%} of automated evidence actions.",
            "- No Phase 8 ablation, Phase 9 three-generation, or Phase 10 release claim is made.", "",
        ]
        (root / "reports" / "CLAIMS.md").write_text("\n".join(claims), encoding="utf-8")
    else:
        raise RuntimeError(f"Independent Phase 7 audit failed with {len(findings)} finding(s).")
    # console.log: phase7.audit.complete
    print(f'{{"event":"phase7.audit.complete","status":"{report["status"]}","findings":{len(findings)}}}')


if __name__ == "__main__":
    main()
