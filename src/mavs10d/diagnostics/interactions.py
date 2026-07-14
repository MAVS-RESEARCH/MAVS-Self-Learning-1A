"""Non-additive interaction certification and prohibition controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from mavs10d.core.hashing import stable_hash


@dataclass(frozen=True)
class InteractionCertificate:
    certificate_id: str
    primitive_ids: tuple[str, ...]
    causal_family: str
    scope_ids: tuple[str, ...]
    counterfactual_passed: bool
    nonredundant: bool
    protected_regression: float
    status: str

    def permits_terminal_influence(self) -> bool:
        return (
            self.status == "certified"
            and self.counterfactual_passed
            and self.nonredundant
            and self.protected_regression == 0.0
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "certificate_id": self.certificate_id,
            "primitive_ids": list(self.primitive_ids),
            "causal_family": self.causal_family,
            "scope_ids": list(self.scope_ids),
            "counterfactual_passed": self.counterfactual_passed,
            "nonredundant": self.nonredundant,
            "protected_regression": self.protected_regression,
            "status": self.status,
        }


def certify_interaction(
    primitive_ids: Iterable[str],
    causal_family: str,
    scope_ids: Iterable[str],
    *,
    counterfactual_passed: bool,
    nonredundant: bool,
    protected_regression: float,
    prohibited_patterns: set[frozenset[str]] | None = None,
) -> InteractionCertificate:
    primitives = tuple(sorted(set(primitive_ids)))
    if len(primitives) < 2:
        raise ValueError("Interaction certificates require at least two distinct primitives.")
    prohibited = prohibited_patterns or set()
    if frozenset(primitives) in prohibited:
        status = "prohibited"
    elif counterfactual_passed and nonredundant and protected_regression == 0.0:
        status = "certified"
    else:
        status = "untested"
    identity = stable_hash({
        "primitive_ids": primitives,
        "causal_family": causal_family,
        "scope_ids": sorted(set(scope_ids)),
        "status": status,
    })
    return InteractionCertificate(
        certificate_id=f"IC-{identity[:20]}",
        primitive_ids=primitives,
        causal_family=causal_family,
        scope_ids=tuple(sorted(set(scope_ids))),
        counterfactual_passed=counterfactual_passed,
        nonredundant=nonredundant,
        protected_regression=float(protected_regression),
        status=status,
    )


def enforce_interaction_status(status: str, terminal_influence_requested: bool) -> str:
    if status == "prohibited":
        raise PermissionError("Prohibited diagnostic compositions cannot execute.")
    if status == "untested" and terminal_influence_requested:
        return "observation_only"
    if status not in {"single", "certified", "untested"}:
        raise ValueError(f"Unknown interaction status: {status}")
    return "terminal" if terminal_influence_requested else "observation_only"
