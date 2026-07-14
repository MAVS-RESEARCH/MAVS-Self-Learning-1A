"""Typed diagnostic influence permissions without additive severity stacking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


TERMINAL_CHANNEL_PERMISSION = {"danger": "REJECT", "safe": "ACCEPT"}
META_CHANNELS = frozenset({"availability", "scope", "novelty", "conflict"})
ALL_CHANNELS = frozenset(TERMINAL_CHANNEL_PERMISSION) | META_CHANNELS


@dataclass(frozen=True)
class Influence:
    source_id: str
    channel: str
    authority: str
    requested_action: str | None
    causal_family: str
    influential: bool

    def validate(self) -> None:
        if self.channel not in ALL_CHANNELS:
            raise ValueError(f"Unknown typed channel: {self.channel}")
        if self.authority not in {"L0", "L1", "L2", "L3"}:
            raise ValueError(f"Unknown authority: {self.authority}")
        if self.channel in META_CHANNELS and self.requested_action in {"ACCEPT", "REJECT"}:
            raise PermissionError(f"Meta-channel {self.channel} cannot directly hard-veto or authorize a terminal action.")
        if self.requested_action in {"ACCEPT", "REJECT"}:
            if TERMINAL_CHANNEL_PERMISSION.get(self.channel) != self.requested_action:
                raise PermissionError("Typed channel cannot support the requested terminal action.")
            if self.authority not in {"L2", "L3"}:
                raise PermissionError("L0/L1 influence cannot authorize a terminal action.")


def arbitrate(influences: Iterable[Influence]) -> dict[str, object]:
    active = [item for item in influences if item.influential]
    for item in active:
        item.validate()
    terminal = [item for item in active if item.requested_action in {"ACCEPT", "REJECT"}]
    actions = {item.requested_action for item in terminal}
    if len(actions) > 1:
        return {
            "terminal_action": None,
            "primary_causal_family": "conflict",
            "requires_adjudication": True,
            "explanation_edges": [vars(item) for item in active],
            "additive_severity_used": False,
        }
    primary = min(terminal, key=lambda item: (item.causal_family, item.source_id)) if terminal else None
    return {
        "terminal_action": primary.requested_action if primary else None,
        "primary_causal_family": primary.causal_family if primary else (active[0].causal_family if active else "none"),
        "requires_adjudication": False,
        "explanation_edges": [vars(item) for item in active],
        "additive_severity_used": False,
    }


def typed_hard_veto_violations(influences: Iterable[Influence]) -> list[str]:
    violations: list[str] = []
    for item in influences:
        try:
            item.validate()
        except PermissionError as error:
            violations.append(f"{item.source_id}:{error}")
    return violations
