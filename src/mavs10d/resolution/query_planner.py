"""Targeted evidence acquisition with exact cost, latency, call, and privacy ledgers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from mavs10d.diagnostics.ast import evaluate_ast


@dataclass
class BudgetLedger:
    max_cost: float
    max_latency_ms: float
    max_calls: int
    max_privacy_units: float
    spent_cost: float = 0.0
    spent_latency_ms: float = 0.0
    spent_calls: int = 0
    spent_privacy_units: float = 0.0

    def permits(self, action: Mapping[str, Any]) -> bool:
        return (
            self.spent_cost + float(action.get("cost", 0.0)) <= self.max_cost
            and self.spent_latency_ms + float(action.get("latency_ms", 0.0)) <= self.max_latency_ms
            and self.spent_calls + 1 <= self.max_calls
            and self.spent_privacy_units + float(action.get("privacy_units", 0.0)) <= self.max_privacy_units
        )

    def debit(self, action: Mapping[str, Any]) -> None:
        if not self.permits(action):
            raise RuntimeError("Perception action exceeds the remaining bounded budget.")
        self.spent_cost += float(action.get("cost", 0.0))
        self.spent_latency_ms += float(action.get("latency_ms", 0.0))
        self.spent_calls += 1
        self.spent_privacy_units += float(action.get("privacy_units", 0.0))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_action(
    action: Mapping[str, Any],
    evidence: dict[str, dict[str, Any]],
    budget: BudgetLedger,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if action.get("action_type") not in {"QUERY", "PROBE", "DIAGNOSTIC_PROGRAM"}:
        raise ValueError("Only registered internal perception actions may execute.")
    budget.debit(action)
    updates = dict(action.get("evidence_response", {}))
    if action.get("action_type") == "DIAGNOSTIC_PROGRAM":
        program = action.get("executable_program")
        if not program:
            raise RuntimeError("Diagnostic programs require an executable AST program.")
        feature_names = list(map(str, program["feature_fields"]))
        features = {
            name: [float(evidence[name]["value"])]
            for name in feature_names
            if name in evidence and evidence[name].get("available", False)
        }
        if set(features) != set(feature_names):
            raise RuntimeError("Executable diagnostic program evidence is unavailable.")
        output = bool(evaluate_ast(program["expression_ast"], features, program.get("parameters", {}))[0])
        updates[str(program["output_field"])] = {
            "value": program["true_value"] if output else program["false_value"],
            "available": True, "trusted": True, "fresh": True, "provenance_valid": True,
            "counterfactual_stable": True, "risk_justification": "deterministic_invariant",
        }
    updated = {key: dict(value) for key, value in evidence.items()}
    for field, record in updates.items():
        normalized = dict(record)
        normalized.setdefault("available", True)
        normalized.setdefault("trusted", True)
        normalized.setdefault("fresh", True)
        normalized.setdefault("provenance_valid", True)
        updated[str(field)] = normalized
    result = {
        "result_available": bool(updates) and all(item.get("available", True) for item in updates.values()),
        "result_trusted": bool(updates) and all(item.get("trusted", True) for item in updates.values()),
        "provenance_valid": bool(updates) and all(item.get("provenance_valid", True) for item in updates.values()),
        "updated_fields": sorted(map(str, updates)),
    }
    return updated, result
