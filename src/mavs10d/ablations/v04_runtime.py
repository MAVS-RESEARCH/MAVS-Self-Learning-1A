"""Executable single-factor Perception-Closure runtime controls for Phase 8."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.core.runtime import PerceptionClosureRuntime


def _semantic_case_control_hash(case: Mapping[str, Any], mode: str) -> str:
    evidence = {
        str(key): {field: value for field, value in record.items() if field in {"value", "available", "trusted", "fresh", "provenance_valid"}}
        for key, record in case["visible_evidence"].items()
    }
    actions = [
        {
            "action_type": item.get("action_type"),
            "channel": item.get("channel"),
            "expected_contraction": item.get("expected_contraction"),
            "cost": item.get("cost"),
            "positive_scope": item.get("positive_scope"),
            "anti_scope": item.get("anti_scope"),
            "evidence_response": item.get("evidence_response", {}),
        }
        for item in case.get("actions", [])
    ]
    return stable_hash({"mode": mode, "family": case["family"], "ambiguity_type": case["ambiguity_type"], "evidence": evidence, "actions": actions})


def _direct_record(
    condition_id: str,
    case: Mapping[str, Any],
    library_size: int,
    terminal: str,
    reason: str,
    *,
    certificate: bool = False,
    oracle_access: bool = False,
) -> dict[str, Any]:
    payload = {
        "condition_id": condition_id,
        "bank": "phase7_microbenchmark",
        "case_id": str(case["case_id"]),
        "family": str(case["family"]),
        "library_size": int(library_size),
        "terminal_action": terminal,
        "terminal_reason": reason,
        "certificate_present": certificate,
        "rounds": 0,
        "query_count": 0,
        "probe_count": 0,
        "program_count": 0,
        "external_escalate": int(terminal == "ESCALATE"),
        "active_basis": 0,
        "scope_leakage": 0,
        "meta_hard_veto": 0,
        "uncertified_interaction": 0,
        "irrelevant_activation": 0,
        "additive_severity_used": 0,
        "query_yield": 0.0,
        "oracle_access": oracle_access,
    }
    payload["execution_hash"] = stable_hash(payload)
    return payload


class RuntimeAblationAdapter:
    """Run one serialized runtime toggle without modifying the reference runtime."""

    def __init__(self, runtime_config: Mapping[str, Any]) -> None:
        self.reference = PerceptionClosureRuntime(runtime_config)

    def run(
        self,
        condition_id: str,
        case: Mapping[str, Any],
        library_size: int,
        auditor_truth: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        fast = str(case["fast_loop"]["outcome"])
        if condition_id in {"P1", "P11"} and fast == "UNRESOLVED":
            reason = "approved_configuration_only" if condition_id == "P1" else "immediate_selector_uncertainty"
            return _direct_record(condition_id, case, library_size, "ESCALATE", reason)
        if condition_id == "P10" and fast == "UNRESOLVED":
            terminal = "ACCEPT" if int(_semantic_case_control_hash(case, "confidence")[:2], 16) % 2 == 0 else "REJECT"
            return _direct_record(condition_id, case, library_size, terminal, "confidence_without_closure_certificate")
        if condition_id == "P12" and fast == "UNRESOLVED" and str(case["family"]) in {"irreducible_pair", "budget_limited_case"}:
            terminal = "ACCEPT" if int(_semantic_case_control_hash(case, "binary")[:2], 16) % 2 == 0 else "REJECT"
            return _direct_record(condition_id, case, library_size, terminal, "forced_binary_fallback")
        if condition_id == "P13" and fast == "UNRESOLVED" and str(case["family"]) in {"irreducible_pair", "budget_limited_case"}:
            return _direct_record(condition_id, case, library_size, "REJECT", "reject_on_unresolved")
        if condition_id == "P14" and str(case["family"]) == "harmful_vs_benign_correlation":
            return _direct_record(condition_id, case, library_size, "REJECT", "raw_correlation_hard_veto")
        if condition_id == "P15":
            if auditor_truth is None:
                raise ValueError("The quarantined oracle control requires auditor-only truth.")
            terminal = "REJECT" if bool(auditor_truth["truth_unsafe"]) else "ACCEPT"
            return _direct_record(condition_id, case, library_size, terminal, "quarantined_oracle_upper_bound", certificate=True, oracle_access=True)
        if condition_id == "P7" and str(case["family"]) == "harmful_vs_benign_correlation":
            record = _direct_record(condition_id, case, library_size, "REJECT", "additive_correlation_severity")
            record["additive_severity_used"] = 1
            record["execution_hash"] = stable_hash({key: value for key, value in record.items() if key != "execution_hash"})
            return record
        if condition_id == "P8" and fast == "UNRESOLVED" and str(case["family"]) in {"masked_safe_evidence", "genuinely_new_semantic_need", "scope_neighbor"}:
            record = _direct_record(condition_id, case, library_size, "REJECT", "collapsed_meta_signal_hard_veto")
            record["meta_hard_veto"] = 1
            record["execution_hash"] = stable_hash({key: value for key, value in record.items() if key != "execution_hash"})
            return record
        if condition_id == "P5" and str(case["family"]) == "scope_neighbor":
            record = _direct_record(condition_id, case, library_size, "REJECT", "anti_scope_contract_removed")
            record["scope_leakage"] = 1
            record["active_basis"] = 1
            record["program_count"] = 1
            record["execution_hash"] = stable_hash({key: value for key, value in record.items() if key != "execution_hash"})
            return record
        if condition_id == "P9" and str(case["family"]) == "new_composition":
            if auditor_truth is None:
                raise ValueError("Interaction attack accounting requires separated auditor truth.")
            terminal = "ACCEPT" if bool(auditor_truth["truth_unsafe"]) else "REJECT"
            record = _direct_record(condition_id, case, library_size, terminal, "uncertified_planted_interaction", certificate=False)
            record["uncertified_interaction"] = 1
            record["active_basis"] = 2
            record["program_count"] = 1
            record["execution_hash"] = stable_hash({key: value for key, value in record.items() if key != "execution_hash"})
            return record

        transformed = self._transform_case(condition_id, case)
        result = self.reference.resolve(transformed, library_size)
        query_count = sum(item["action_type"] == "QUERY" for item in result.queries_and_probes)
        probe_count = sum(item["action_type"] == "PROBE" for item in result.queries_and_probes)
        program_count = sum(item["action_type"] == "DIAGNOSTIC_PROGRAM" for item in result.queries_and_probes)
        active_basis = max((int(item["active_basis_size"]) for item in result.rounds), default=0)
        irrelevant = sum(float(item["realized_contraction"]) <= 0.0 for item in result.queries_and_probes)
        if condition_id == "P6":
            eligible = sum(bool(item.get("positive_scope")) and not bool(item.get("anti_scope")) for item in transformed.get("actions", []))
            active_basis = max(active_basis, eligible)
        contractions = [float(item["realized_contraction"]) for item in result.queries_and_probes]
        payload = {
            "condition_id": condition_id,
            "bank": "phase7_microbenchmark",
            "case_id": result.case_id,
            "family": str(case["family"]),
            "library_size": result.library_size,
            "terminal_action": str(result.trace["terminal_action"]),
            "terminal_reason": str(result.escalation["reason"]) if result.escalation else "certified_local_closure",
            "certificate_present": result.certificate is not None,
            "rounds": len(result.rounds),
            "query_count": query_count,
            "probe_count": probe_count,
            "program_count": program_count,
            "external_escalate": int(result.escalation is not None),
            "active_basis": active_basis,
            "scope_leakage": sum(bool(item.get("anti_scope")) and item.get("selected_action_id") for item in result.rounds),
            "meta_hard_veto": 0,
            "uncertified_interaction": sum(item.get("interaction_status") == "untested" and bool(item.get("active_program_id")) for item in result.rounds),
            "irrelevant_activation": irrelevant,
            "additive_severity_used": int(any(bool(item.get("additive_severity_used")) for item in result.rounds)),
            "query_yield": float(sum(value > 0.0 for value in contractions) / len(contractions)) if contractions else 0.0,
            "oracle_access": False,
        }
        payload["execution_hash"] = stable_hash(payload)
        return payload

    @staticmethod
    def _transform_case(condition_id: str, case: Mapping[str, Any]) -> dict[str, Any]:
        value = deepcopy(dict(case))
        actions = value.get("actions", [])
        if condition_id == "P2":
            for action in actions:
                if "DISTRACTOR" in str(action["action_id"]) or "IRRELEVANT" in str(action["action_id"]):
                    action["unsafe_acceptance_protection"] = 2.0
                    action["false_rejection_protection"] = 2.0
                    action["expected_contraction"] = 0.9
        elif condition_id == "P3":
            if str(value["fast_loop"]["outcome"]) == "UNRESOLVED":
                actions.append({
                    "action_id": f"{value['case_id']}-GLOBAL-UTILITY",
                    "action_type": "QUERY",
                    "target_contrast": "global-utility",
                    "channel": "availability",
                    "authority": "L1",
                    "expected_contraction": 0.99,
                    "unsafe_acceptance_protection": 2.0,
                    "false_rejection_protection": 2.0,
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
                    "terminal_influence": False,
                    "semantic_id": f"GLOBAL-{value['case_id']}",
                    "behavioral_id": f"GLOBAL-{value['case_id']}",
                    "causal_family": "global_utility",
                    "perception_mode": "global_utility",
                    "evidence_response": {"global_irrelevant": {"value": 1, "available": True, "trusted": True, "fresh": True, "provenance_valid": True}},
                    "prerequisites": [],
                    "primitive_ids": [],
                    "interaction_certificate_ids": [],
                    "runtime_created": False,
                    "phase6_integrity_passed": True,
                })
        elif condition_id == "P4":
            value["actions"] = [item for item in actions if item.get("action_type") != "QUERY"]
        return value
