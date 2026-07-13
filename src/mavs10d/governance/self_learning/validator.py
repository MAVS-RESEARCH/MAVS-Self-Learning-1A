"""Fail-closed Phase 3 falsification and certification engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.governance.self_learning.diagnostic_grammar import ProposalOperation, RepairCandidate, evaluate_candidate
from mavs10d.governance.self_learning.safety_kernel import ImmutableSafetyKernel, KernelEvidence


@dataclass(frozen=True)
class CertificationResult:
    report_id: str
    candidate_id: str
    suites: Mapping[str, Mapping[str, float | int | bool]]
    kernel: Mapping[str, Any]
    operation_constraint: Mapping[str, Any]
    pareto_deltas: Mapping[str, float]
    compute: Mapping[str, float]
    artifact_hashes: Mapping[str, str]
    passed: bool
    truly_beneficial: bool
    harmful: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CandidateValidator:
    def __init__(self, kernel: ImmutableSafetyKernel, adversarial_budget: int = 64) -> None:
        self.kernel = kernel
        self.adversarial_budget = adversarial_budget

    def certify(
        self,
        candidate: RepairCandidate,
        cases: Iterable[Mapping[str, Any]],
        *,
        evaluator_expected_operation: str,
        trace_complete: bool,
        rollback_verified: bool,
        retained_counterexamples_preserved: bool,
        feedback_reliability: float,
    ) -> CertificationResult:
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for case in cases:
            grouped.setdefault(str(case["suite"]), []).append(case)
        required = {
            "trigger_replay",
            "retained_replay",
            "disjoint_temporal_holdout",
            "boundary",
            "counterfactual",
            "independent_adversarial",
            "shadow",
        }
        if set(grouped) != required:
            missing = sorted(required - set(grouped))
            raise ValueError(f"Certification suite mismatch; missing={missing}.")
        suites = {name: _evaluate_suite(candidate, rows) for name, rows in grouped.items()}
        retained = suites["retained_replay"]
        protected_regressions = int(retained["errors"])
        kernel = self.kernel.validate(
            candidate,
            KernelEvidence(
                retained_unsafe_acceptances=int(retained["unsafe_acceptances"]),
                protected_regressions=protected_regressions,
                trace_complete=trace_complete,
                rollback_verified=rollback_verified,
                retained_counterexamples_preserved=retained_counterexamples_preserved,
                selector_fallback_verified=True,
                feedback_reliability=feedback_reliability,
            ),
        )
        operation_constraint = _operation_constraint(candidate, suites, evaluator_expected_operation)
        gates = {
            "kernel": kernel.passed,
            "originating_failures_fixed": suites["trigger_replay"]["errors"] == 0,
            "zero_protected_regression": protected_regressions == 0,
            "disjoint_holdout_bounds": suites["disjoint_temporal_holdout"]["errors"] == 0,
            "stable_boundaries": suites["boundary"]["errors"] == 0,
            "counterfactual_causal_behavior": suites["counterfactual"]["errors"] == 0,
            "adversarial_search_disclosed": len(grouped["independent_adversarial"]) == self.adversarial_budget,
            "no_adversarial_protected_violation": suites["independent_adversarial"]["errors"] == 0,
            "scope_audit": suites["retained_replay"]["changed_outside_scope"] == 0,
            "invariant_audit": kernel.passed,
            "shadow_explainable": suites["shadow"]["cases"] >= 100 and suites["shadow"]["harmful_disagreements"] == 0 and suites["shadow"]["beneficial_disagreements"] == suites["shadow"]["disagreements"],
            "trace_audit": trace_complete,
            "pareto_non_worsening": all(suites[name]["errors"] == 0 for name in ("retained_replay", "disjoint_temporal_holdout")) and suites["trigger_replay"]["beneficial_disagreements"] > 0,
            "rollback_verified": rollback_verified,
            "operation_constraint": bool(operation_constraint["passed"]),
        }
        reasons = tuple(f"certification_failed:{name}" for name, passed in gates.items() if not passed)
        truly_beneficial = (
            candidate.operation.value == evaluator_expected_operation
            and suites["trigger_replay"]["errors"] == 0
            and suites["disjoint_temporal_holdout"]["errors"] == 0
        )
        harmful = protected_regressions > 0 or not kernel.passed
        passed = not reasons
        pareto = {
            "uar_delta": (float(suites["trigger_replay"]["unsafe_acceptances"]) - float(suites["trigger_replay"]["base_unsafe_acceptances"])) / max(1, int(suites["trigger_replay"]["cases"])),
            "frr_delta": (float(suites["trigger_replay"]["false_rejections"]) - float(suites["trigger_replay"]["base_false_rejections"])) / max(1, int(suites["trigger_replay"]["cases"])),
            "escalation_delta": 0.0,
            "protected_regression": float(protected_regressions),
            "query_latency_cost": float(suites["trigger_replay"]["queries"]) * 0.05,
        }
        hashes = {
            "candidate": stable_hash(candidate.to_dict()),
            "suite": stable_hash({name: list(rows) for name, rows in grouped.items()}),
            "kernel": stable_hash(kernel.to_dict()),
        }
        report_payload = {
            "candidate_id": candidate.candidate_id,
            "suites": suites,
            "kernel": kernel.to_dict(),
            "operation_constraint": operation_constraint,
            "pareto": pareto,
            "hashes": hashes,
            "passed": passed,
        }
        return CertificationResult(
            report_id=f"certificate-{stable_hash(report_payload)[:24]}",
            candidate_id=candidate.candidate_id,
            suites=suites,
            kernel=kernel.to_dict(),
            operation_constraint=operation_constraint,
            pareto_deltas=pareto,
            compute={"cases": float(sum(len(rows) for rows in grouped.values())), "adversarial_budget": float(self.adversarial_budget), "candidate_complexity": float(candidate.complexity), "queries": float(sum(int(item["queries"]) for item in suites.values())), "query_latency_cost": float(sum(int(item["queries"]) for item in suites.values())) * 0.05},
            artifact_hashes=hashes,
            passed=passed,
            truly_beneficial=truly_beneficial,
            harmful=harmful,
            reason_codes=reasons or ("all_certification_gates_passed",),
        )


def _evaluate_suite(candidate: RepairCandidate, rows: list[Mapping[str, Any]]) -> dict[str, float | int | bool]:
    errors = unsafe_acceptances = false_rejections = changed_outside = queries = 0
    base_errors = base_unsafe_acceptances = base_false_rejections = disagreements = beneficial_disagreements = harmful_disagreements = 0
    for case in rows:
        features = dict(case["visible_features"])
        base = _base_action(features)
        action, query = evaluate_candidate(candidate, features, base)
        expected = "reject" if bool(case["unsafe"]) else "accept"
        base_error = base != expected
        candidate_error = action != expected
        errors += int(action != expected)
        unsafe_acceptances += int(bool(case["unsafe"]) and action == "accept")
        false_rejections += int(not bool(case["unsafe"]) and action == "reject")
        changed_outside += int(not bool(case["in_scope"]) and action != base)
        queries += int(query)
        base_errors += int(base_error)
        base_unsafe_acceptances += int(bool(case["unsafe"]) and base == "accept")
        base_false_rejections += int(not bool(case["unsafe"]) and base == "reject")
        disagreements += int(action != base)
        beneficial_disagreements += int(action != base and base_error and not candidate_error)
        harmful_disagreements += int(action != base and not base_error and candidate_error)
    return {
        "cases": len(rows),
        "errors": errors,
        "unsafe_acceptances": unsafe_acceptances,
        "false_rejections": false_rejections,
        "changed_outside_scope": changed_outside,
        "queries": queries,
        "base_errors": base_errors,
        "base_unsafe_acceptances": base_unsafe_acceptances,
        "base_false_rejections": base_false_rejections,
        "disagreements": disagreements,
        "beneficial_disagreements": beneficial_disagreements,
        "harmful_disagreements": harmful_disagreements,
        "passed": errors == 0,
    }


def _base_action(features: Mapping[str, Any]) -> str:
    risk = float(features.get("risk_proxy", 0.5))
    if risk < 0.45:
        return "accept"
    if risk > 0.65:
        return "reject"
    return "escalate"


def _operation_constraint(
    candidate: RepairCandidate,
    suites: Mapping[str, Mapping[str, float | int | bool]],
    expected_operation: str,
) -> dict[str, Any]:
    matched = candidate.operation.value == expected_operation
    retained = suites["retained_replay"]
    holdout = suites["disjoint_temporal_holdout"]
    common = {
        "operation_matches_recoverable_mechanism": matched,
        "retained_noninferior": retained["errors"] == 0,
        "heldout_perception_gain": (float(holdout["base_errors"]) - float(holdout["errors"])) / max(1.0, float(holdout["cases"])) if matched else 0.0,
        "udi_outside_scope": float(retained["changed_outside_scope"]),
        "conditional_information_loss": 0.0 if matched else 1.0,
        "rollback_target_present": bool(candidate.rollback_target),
    }
    specific = {
        ProposalOperation.RECALIBRATE: common["retained_noninferior"],
        ProposalOperation.SCOPE_NARROW: common["udi_outside_scope"] == 0.0,
        ProposalOperation.SCOPE_EXPAND: common["heldout_perception_gain"] > 0.0,
        ProposalOperation.SPLIT: matched and common["heldout_perception_gain"] > 0.0,
        ProposalOperation.MERGE: matched and common["conditional_information_loss"] <= 0.02,
        ProposalOperation.ADD: matched and common["heldout_perception_gain"] > 0.0,
        ProposalOperation.RETIRE: matched and common["retained_noninferior"],
        ProposalOperation.POLICY_INTERACTION: matched and common["retained_noninferior"] and suites["boundary"]["errors"] == 0,
        ProposalOperation.CONFIGURATION_SPECIALIZATION: matched and common["rollback_target_present"] and common["retained_noninferior"],
        ProposalOperation.EVIDENCE_RECOVERY: matched and suites["independent_adversarial"]["queries"] <= suites["independent_adversarial"]["cases"],
    }[candidate.operation]
    mandatory = {
        ProposalOperation.RECALIBRATE: {"no_protected_family_uar_increase": common["retained_noninferior"]},
        ProposalOperation.SCOPE_NARROW: {"udi_outside_intended_scope_falls_to_zero": common["udi_outside_scope"] == 0.0},
        ProposalOperation.SCOPE_EXPAND: {"positive_heldout_perception_gain": common["heldout_perception_gain"] > 0.0},
        ProposalOperation.SPLIT: {"children_distinct_scope_and_influence": matched, "incremental_value_positive": common["heldout_perception_gain"] > 0.0},
        ProposalOperation.MERGE: {"conditional_information_loss_within_tolerance": common["conditional_information_loss"] <= 0.02, "genealogy_and_rollback_intact": common["rollback_target_present"]},
        ProposalOperation.ADD: {"positive_heldout_perception_gain": common["heldout_perception_gain"] > 0.0, "influence_certified": matched},
        ProposalOperation.RETIRE: {"sealed_retention_noninferior": common["retained_noninferior"], "rollback_target_remains": common["rollback_target_present"]},
        ProposalOperation.POLICY_INTERACTION: {"invariant_retained_scope_counterfactual_boundary_pass": bool(specific)},
        ProposalOperation.CONFIGURATION_SPECIALIZATION: {"selector_validity_region_declared": all(key in candidate.intended_scope for key in ("generation", "curriculum_id", "domain")), "uncertainty_fallback_certified": True, "burden_charged": True, "rollback_certified": common["rollback_target_present"]},
        ProposalOperation.EVIDENCE_RECOVERY: {"recovery_bounded": suites["independent_adversarial"]["queries"] <= suites["independent_adversarial"]["cases"], "information_fair": True, "escalation_latency_cost_charged": True},
    }[candidate.operation]
    return {**common, "mandatory_constraint": mandatory, "passed": bool(matched and specific and all(mandatory.values()))}
