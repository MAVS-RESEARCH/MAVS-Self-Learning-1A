"""Live Perception-Closure runtime with residual-only external escalation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.diagnostics.typed_channels import Influence, arbitrate, typed_hard_veto_violations
from mavs10d.memory.negative_knowledge import NegativeKnowledge
from mavs10d.resolution.ambiguity import ambiguity_contraction, make_ambiguity_state
from mavs10d.resolution.closure import attempt_local_closure, decompose_residual_escalation
from mavs10d.resolution.hypotheses import build_hypotheses, surviving_hypotheses
from mavs10d.resolution.perception_search import indexed_library_view, rank_actions
from mavs10d.resolution.program_builder import build_program
from mavs10d.resolution.query_planner import BudgetLedger, execute_action


FORBIDDEN_RUNTIME_FIELDS = frozenset({"expected_outcome", "oracle_label", "unsafe", "hidden_world", "target_decision"})
KERNEL_STATE = {"hard_veto": True, "mitigation": True, "monotonicity": True, "traceability": True, "rollback": True}


def assert_runtime_blindness(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in FORBIDDEN_RUNTIME_FIELDS or str(key).lower().startswith("hidden_"):
                raise ValueError(f"Forbidden runtime field at {path}.{key}")
            assert_runtime_blindness(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            assert_runtime_blindness(nested, f"{path}[{index}]")


@dataclass
class RuntimeResult:
    case_id: str
    library_size: int
    trace: dict[str, Any]
    rounds: list[dict[str, Any]] = field(default_factory=list)
    queries_and_probes: list[dict[str, Any]] = field(default_factory=list)
    programs: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    initial_ambiguity_state: dict[str, Any] = field(default_factory=dict)
    certificate: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None
    terminal_record: dict[str, Any] = field(default_factory=dict)
    negative_knowledge: list[dict[str, Any]] = field(default_factory=list)


class PerceptionClosureRuntime:
    def __init__(self, runtime_config: Mapping[str, Any]) -> None:
        self.config = dict(runtime_config)
        self.max_basis = int(self.config["sparse_basis"]["max_influential_diagnostics"])

    def resolve(self, case: Mapping[str, Any], library_size: int) -> RuntimeResult:
        assert_runtime_blindness(case)
        case_id = str(case["case_id"])
        evidence = {str(key): dict(value) for key, value in case["visible_evidence"].items()}
        root_hash = stable_hash({"case": case, "library_size": library_size, "runtime_version": self.config["runtime_version"]})
        fast_loop = dict(case["fast_loop"])
        fast_outcome = str(fast_loop["outcome"])
        if fast_outcome in {"ACCEPT", "REJECT"} and bool(fast_loop.get("certificate_valid", False)):
            certificate = self._fast_loop_certificate(case_id, fast_loop, evidence, root_hash)
            trace = self._trace(
                case_id, library_size, fast_outcome, False, [], [], [], fast_outcome,
                certificate["certificate_id"], root_hash, certificate["certificate_hash"],
            )
            terminal = self._terminal_record(case_id, fast_outcome, certificate["certificate_id"], 0, 0, 0, 0, 0, trace["trace_hash"])
            return RuntimeResult(case_id, library_size, trace, certificate=certificate, terminal_record=terminal)
        if fast_outcome != "UNRESOLVED":
            raise RuntimeError("An uncertified fast-loop terminal outcome is forbidden.")

        hypotheses = build_hypotheses(case["hypotheses"])
        survivor_set = surviving_hypotheses(hypotheses, evidence)
        state = make_ambiguity_state(case_id, 0, str(case["ambiguity_type"]), evidence, survivor_set, root_hash)
        negative = NegativeKnowledge(
            anti_scopes=set(map(str, case.get("negative_knowledge", {}).get("anti_scopes", []))),
            low_yield_queries=set(map(str, case.get("negative_knowledge", {}).get("low_yield_queries", []))),
            prohibited_compositions={frozenset(map(str, item)) for item in case.get("negative_knowledge", {}).get("prohibited_compositions", [])},
        )
        budget_cfg = self.config["budgets"][str(case["budget_level"])]
        budget = BudgetLedger(**budget_cfg)
        actions = [dict(item) for item in case.get("actions", [])]
        executed: set[str] = set()
        round_records: list[dict[str, Any]] = []
        query_records: list[dict[str, Any]] = []
        programs: list[dict[str, Any]] = []
        influences: list[Influence] = []
        certificate: dict[str, Any] | None = None
        escalation: dict[str, Any] | None = None
        terminal_action: str | None = None

        for round_index in range(1, int(case.get("max_rounds", 8)) + 1):
            if state.decision_homogeneous:
                certificate = self._attempt_certificate(case_id, state, survivor_set, evidence, programs, influences)
                if certificate:
                    terminal_action = state.terminal_action
                    break
            remaining = [item for item in actions if str(item["action_id"]) not in executed]
            library_view = indexed_library_view(library_size, len(remaining), str(case["ambiguity_type"]))
            search = rank_actions(remaining, evidence, negative)
            selected = search.selected
            finding_records = [vars(item) for item in search.findings]
            if selected is None:
                reason = self._infer_residual_reason(case, finding_records, remaining, budget)
                escalation = decompose_residual_escalation(
                    case_id,
                    reason,
                    [],
                    finding_records,
                    budget.to_dict(),
                    state.state_hash,
                )
                terminal_action = "ESCALATE"
                break
            if not budget.permits(selected):
                escalation = decompose_residual_escalation(
                    case_id,
                    "budget_exhaustion",
                    [str(selected["action_id"])],
                    finding_records,
                    budget.to_dict(),
                    state.state_hash,
                )
                terminal_action = "ESCALATE"
                break

            before = state
            program = None
            if selected["action_type"] == "DIAGNOSTIC_PROGRAM":
                program = build_program(case_id, round_index, selected, remaining, self.max_basis)
                programs.append(program)
            evidence, action_result = execute_action(selected, evidence, budget)
            executed.add(str(selected["action_id"]))
            survivor_set = surviving_hypotheses(hypotheses, evidence)
            action_parent = state.state_hash
            state = make_ambiguity_state(case_id, round_index, str(case["ambiguity_type"]), evidence, survivor_set, action_parent)
            realized = ambiguity_contraction(before, state)
            negative.record_low_yield(str(selected["action_id"]), realized)
            query_record = self._query_record(case_id, round_index, selected, action_result, realized, action_parent)
            query_records.append(query_record)
            influence = self._influence_from_state(selected, survivor_set)
            if influence:
                influence.validate()
                influences.append(influence)
            arbitration = arbitrate(influences)
            round_payload = {
                "case_id": case_id,
                "round_index": round_index,
                "event_type": "RESOLVER_ROUND",
                "ambiguity_type": state.ambiguity_type,
                "before_state_hash": before.state_hash,
                "after_state_hash": state.state_hash,
                "before_survivor_count": before.safe_count + before.unsafe_count,
                "after_survivor_count": state.safe_count + state.unsafe_count,
                "safe_count": state.safe_count,
                "unsafe_count": state.unsafe_count,
                "generated_action_ids": [str(item["action_id"]) for item in remaining],
                "action_findings": finding_records,
                "surviving_hypothesis_ids": list(state.surviving_hypotheses),
                "hypothesis_evidence_assessment": self._hypothesis_assessment(hypotheses, evidence),
                "selected_action_id": str(selected["action_id"]),
                "selected_action_type": str(selected["action_type"]),
                "target_contrast": str(selected["target_contrast"]),
                "expected_contraction": float(selected["expected_contraction"]),
                "realized_contraction": realized,
                "active_program_id": program["program_id"] if program else None,
                "active_basis_size": len(program["influential_basis"]) if program else 0,
                "typed_channel": str(selected["channel"]),
                "typed_influence_graph": arbitration["explanation_edges"],
                "authority": str(selected["authority"]),
                "interaction_status": str(selected["interaction_status"]),
                "interaction_certificate_ids": list(selected.get("interaction_certificate_ids", [])),
                "positive_scope": bool(selected["positive_scope"]),
                "anti_scope": bool(selected["anti_scope"]),
                "result_available": bool(action_result["result_available"]),
                "result_trusted": bool(action_result["result_trusted"]),
                "result_provenance_valid": bool(action_result["provenance_valid"]),
                "library_search": library_view,
                "primary_causal_family": arbitration["primary_causal_family"],
                "additive_severity_used": arbitration["additive_severity_used"],
                "budget_ledger": budget.to_dict(),
                "query_record_hash": query_record["record_hash"],
                "parent_hash": before.state_hash,
            }
            round_payload["round_hash"] = stable_hash(round_payload)
            round_records.append(round_payload)
            if state.decision_homogeneous:
                certificate = self._attempt_certificate(case_id, state, survivor_set, evidence, programs, influences)
                if certificate:
                    terminal_action = state.terminal_action
                    break

        if terminal_action is None:
            escalation = decompose_residual_escalation(
                case_id, "resolver_failure", [], [], budget.to_dict(), state.state_hash
            )
            terminal_action = "ESCALATE"
        if terminal_action in {"ACCEPT", "REJECT"} and certificate is None:
            raise RuntimeError("Terminal ACCEPT/REJECT requires a passing local closure certificate.")
        if typed_hard_veto_violations(influences):
            raise RuntimeError("Typed-channel hard-veto violation reached the terminal path.")

        terminal_authorization = certificate["certificate_id"] if certificate else None
        terminal_hash = certificate["certificate_hash"] if certificate else escalation["record_hash"]
        trace = self._trace(
            case_id, library_size, fast_outcome, True, round_records, query_records, programs,
            terminal_action, terminal_authorization, root_hash, terminal_hash,
        )
        terminal = self._terminal_record(
            case_id,
            terminal_action,
            terminal_authorization,
            len(round_records),
            sum(item["action_type"] == "QUERY" for item in query_records),
            sum(item["action_type"] == "PROBE" for item in query_records),
            sum(item["action_type"] == "DIAGNOSTIC_PROGRAM" for item in query_records),
            int(terminal_action == "ESCALATE"),
            trace["trace_hash"],
        )
        return RuntimeResult(
            case_id=case_id,
            library_size=library_size,
            trace=trace,
            rounds=round_records,
            queries_and_probes=query_records,
            programs=programs,
            hypotheses=[item.to_dict() for item in hypotheses],
            initial_ambiguity_state=make_ambiguity_state(case_id, 0, str(case["ambiguity_type"]), {str(key): dict(value) for key, value in case["visible_evidence"].items()}, surviving_hypotheses(hypotheses, {str(key): dict(value) for key, value in case["visible_evidence"].items()}), root_hash).to_dict(),
            certificate=certificate,
            escalation=escalation,
            terminal_record=terminal,
            negative_knowledge=negative.to_records(),
        )

    def _attempt_certificate(self, case_id: str, state: Any, survivors: Any, evidence: Any, programs: Any, influences: Any) -> dict[str, Any] | None:
        terminal_action = state.terminal_action
        matching = [item for item in influences if item.requested_action == terminal_action]
        witness_ids = [item.source_id for item in matching]
        authority = max((item.authority for item in matching), default="L0")
        return attempt_local_closure(case_id, state, survivors, evidence, programs, witness_ids, authority, KERNEL_STATE)

    @staticmethod
    def _hypothesis_assessment(hypotheses: Any, evidence: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        assessments = []
        for hypothesis in hypotheses:
            supporting, contradicting, missing = [], [], []
            for requirement in hypothesis.requirements:
                result = requirement.evaluate(evidence)
                target = missing if result is None else supporting if result else contradicting
                target.append(requirement.field)
            assessments.append({
                "hypothesis_id": hypothesis.hypothesis_id,
                "supporting_evidence": sorted(set(supporting)),
                "contradicting_evidence": sorted(set(contradicting)),
                "missing_evidence": sorted(set(missing)),
                "survives": not contradicting,
            })
        return assessments

    @staticmethod
    def _influence_from_state(selected: Mapping[str, Any], survivors: Any) -> Influence | None:
        classes = {item.decision_class for item in survivors}
        if len(classes) != 1:
            return None
        decision_class = next(iter(classes))
        requested_action = "ACCEPT" if decision_class == "safe" else "REJECT"
        source_id = next(iter(next(iter(survivors)).predicted_witnesses))
        return Influence(
            source_id=source_id,
            channel="safe" if decision_class == "safe" else "danger",
            authority=str(selected["authority"]),
            requested_action=requested_action,
            causal_family=str(selected.get("causal_family", "registered_case_family")),
            influential=True,
        )

    @staticmethod
    def _query_record(case_id: str, round_index: int, selected: Mapping[str, Any], result: Mapping[str, Any], realized: float, parent_hash: str) -> dict[str, Any]:
        payload = {
            "case_id": case_id,
            "round_index": round_index,
            "action_id": str(selected["action_id"]),
            "action_type": str(selected["action_type"]),
            "target_contrast": str(selected["target_contrast"]),
            "expected_contraction": float(selected["expected_contraction"]),
            "realized_contraction": float(realized),
            "cost": float(selected.get("cost", 0.0)),
            "latency_ms": float(selected.get("latency_ms", 0.0)),
            "privacy_units": float(selected.get("privacy_units", 0.0)),
            "result_available": bool(result["result_available"]),
            "result_trusted": bool(result["result_trusted"]),
            "provenance_valid": bool(result["provenance_valid"]),
            "updated_fields": list(result["updated_fields"]),
            "parent_hash": parent_hash,
        }
        payload["record_hash"] = stable_hash(payload)
        return payload

    @staticmethod
    def _infer_residual_reason(case: Mapping[str, Any], findings: list[dict[str, Any]], remaining: list[dict[str, Any]], budget: BudgetLedger) -> str:
        if str(case["ambiguity_type"]) == "irreducible" and not remaining:
            return "irreducible_ambiguity"
        reasons = {str(item["reason"]) for item in findings}
        if reasons & {"invalid_provenance", "insufficient_trust", "prerequisite_not_observed"}:
            return "evidence_unavailable"
        if remaining and not any(budget.permits(item) for item in remaining):
            return "budget_exhaustion"
        return "resolver_failure"

    @staticmethod
    def _fast_loop_certificate(case_id: str, fast_loop: Mapping[str, Any], evidence: Mapping[str, Any], root_hash: str) -> dict[str, Any]:
        witness_id = str(fast_loop["witness_id"])
        witness = evidence.get(witness_id, {})
        obligations = {
            "hypothesis_separation": True,
            "witness_sufficiency": bool(witness.get("available") and witness.get("trusted") and witness.get("provenance_valid")),
            "executable_scope": bool(fast_loop.get("scope_certified")),
            "evidence_integrity": bool(witness.get("fresh") and witness.get("provenance_valid")),
            "counterfactual_stability": bool(witness.get("counterfactual_stable")),
            "interaction_safety": True,
            "authority": fast_loop.get("authority") == "L3",
            "risk_justification": witness.get("risk_justification") in {"certified_class", "deterministic_invariant"},
            "kernel_preservation": True,
            "replay": len(root_hash) == 64,
        }
        payload = {
            "certificate_id": f"FC-{stable_hash({'case': case_id, 'root': root_hash})[:20]}",
            "case_id": case_id,
            "terminal_action": str(fast_loop["outcome"]),
            "surviving_hypotheses": [f"approved-fast-loop-{case_id}"],
            "obligations": obligations,
            "all_passed": all(obligations.values()),
            "witness_ids": [witness_id],
            "authority": "L3",
            "parent_hash": root_hash,
        }
        payload["certificate_hash"] = stable_hash(payload)
        if not payload["all_passed"]:
            raise RuntimeError("Approved fast-loop certificate failed an obligation.")
        return payload

    @staticmethod
    def _trace(case_id: str, library_size: int, fast_outcome: str, resolver_entered: bool, rounds: list[dict[str, Any]], queries: list[dict[str, Any]], programs: list[dict[str, Any]], terminal_action: str, authorization: str | None, root_hash: str, terminal_hash: str) -> dict[str, Any]:
        payload = {
            "case_id": case_id,
            "library_size": library_size,
            "fast_loop_outcome": fast_outcome,
            "resolver_entered": resolver_entered,
            "round_count": len(rounds),
            "query_count": sum(item["action_type"] == "QUERY" for item in queries),
            "probe_count": sum(item["action_type"] == "PROBE" for item in queries),
            "program_count": sum(item["action_type"] == "DIAGNOSTIC_PROGRAM" for item in queries),
            "external_escalation_count": int(terminal_action == "ESCALATE"),
            "terminal_action": terminal_action,
            "terminal_authorization": authorization,
            "root_hash": root_hash,
            "terminal_hash": terminal_hash,
        }
        payload["trace_hash"] = stable_hash(payload)
        return payload

    @staticmethod
    def _terminal_record(case_id: str, action: str, authorization: str | None, rounds: int, queries: int, probes: int, programs: int, escalations: int, trace_hash: str) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "terminal_action": action,
            "terminal_authorization": authorization,
            "round_count": rounds,
            "query_count": queries,
            "probe_count": probes,
            "program_count": programs,
            "external_escalation_count": escalations,
            "trace_hash": trace_hash,
        }
