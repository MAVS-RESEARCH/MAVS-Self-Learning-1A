"""Finite explicit governance hypotheses and evidence-consistent updates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class EvidenceRequirement:
    field: str
    operator: str
    value: Any

    def evaluate(self, evidence: Mapping[str, Mapping[str, Any]]) -> bool | None:
        record = evidence.get(self.field)
        if not record or not record.get("available", False):
            return None
        observed = record.get("value")
        if self.operator == "eq":
            return observed == self.value
        if self.operator == "neq":
            return observed != self.value
        if self.operator == "gte":
            return float(observed) >= float(self.value)
        if self.operator == "lte":
            return float(observed) <= float(self.value)
        if self.operator == "in":
            return observed in self.value
        raise ValueError(f"Unsupported hypothesis operator: {self.operator}")


@dataclass(frozen=True)
class GovernanceHypothesis:
    hypothesis_id: str
    semantic_claim: str
    decision_class: str
    authority: str
    predicted_witnesses: tuple[str, ...]
    predicted_counterfactuals: tuple[str, ...]
    discriminating_actions: tuple[str, ...]
    positive_scope: tuple[str, ...]
    anti_scope: tuple[str, ...]
    terminal_consequence: str
    requirements: tuple[EvidenceRequirement, ...]

    def __post_init__(self) -> None:
        if self.decision_class not in {"safe", "unsafe"}:
            raise ValueError("Hypothesis decision class must be safe or unsafe.")
        if self.authority not in {"L0", "L1"}:
            raise ValueError("Uncertified hypotheses are restricted to L0/L1 authority.")
        expected = "ACCEPT" if self.decision_class == "safe" else "REJECT"
        if self.terminal_consequence != expected:
            raise ValueError("Terminal consequence is inconsistent with decision class.")
        if not self.predicted_witnesses or not self.discriminating_actions:
            raise ValueError("Hypotheses require predicted witnesses and discriminating actions.")

    def consistent(self, evidence: Mapping[str, Mapping[str, Any]]) -> bool:
        results = [requirement.evaluate(evidence) for requirement in self.requirements]
        return not any(result is False for result in results)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["predicted_witnesses"] = list(self.predicted_witnesses)
        payload["predicted_counterfactuals"] = list(self.predicted_counterfactuals)
        payload["discriminating_actions"] = list(self.discriminating_actions)
        payload["positive_scope"] = list(self.positive_scope)
        payload["anti_scope"] = list(self.anti_scope)
        payload["requirements"] = [asdict(item) for item in self.requirements]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GovernanceHypothesis":
        return cls(
            hypothesis_id=str(payload["hypothesis_id"]),
            semantic_claim=str(payload["semantic_claim"]),
            decision_class=str(payload["decision_class"]),
            authority=str(payload["authority"]),
            predicted_witnesses=tuple(map(str, payload["predicted_witnesses"])),
            predicted_counterfactuals=tuple(map(str, payload["predicted_counterfactuals"])),
            discriminating_actions=tuple(map(str, payload["discriminating_actions"])),
            positive_scope=tuple(map(str, payload.get("positive_scope", []))),
            anti_scope=tuple(map(str, payload.get("anti_scope", []))),
            terminal_consequence=str(payload["terminal_consequence"]),
            requirements=tuple(EvidenceRequirement(**item) for item in payload["requirements"]),
        )


def build_hypotheses(payloads: Iterable[Mapping[str, Any]]) -> tuple[GovernanceHypothesis, ...]:
    hypotheses = tuple(GovernanceHypothesis.from_dict(item) for item in payloads)
    if not hypotheses:
        raise ValueError("The resolver requires a nonempty finite hypothesis set.")
    classes = {item.decision_class for item in hypotheses}
    if classes != {"safe", "unsafe"}:
        raise ValueError("A genuinely unresolved decision requires safe- and unsafe-compatible hypotheses.")
    ids = [item.hypothesis_id for item in hypotheses]
    if len(ids) != len(set(ids)):
        raise ValueError("Hypothesis identifiers must be unique.")
    return hypotheses


def surviving_hypotheses(
    hypotheses: Iterable[GovernanceHypothesis], evidence: Mapping[str, Mapping[str, Any]]
) -> tuple[GovernanceHypothesis, ...]:
    survivors = tuple(item for item in hypotheses if item.consistent(evidence))
    if not survivors:
        raise RuntimeError("Evidence eliminated every registered governance hypothesis.")
    return survivors
