"""Feedback provenance, censorship, release, and poison quarantine controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FeedbackDisposition:
    opportunity_id: str
    disposition: str
    release_step: int | None
    reliability: float
    poisoned: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FeedbackQuarantine:
    def __init__(self, reliability_floor: float = 0.75):
        self.reliability_floor = float(reliability_floor)

    def classify(self, event: dict[str, Any], current_step: int) -> FeedbackDisposition:
        release = event.get("release_step")
        reliability = float(event.get("reliability", 0.0))
        poisoned = bool(event.get("poisoned", False))
        if release is None:
            disposition, reason = "censored", "feedback permanently unavailable"
        elif int(release) > int(current_step):
            disposition, reason = "unreleased", "feedback release time not reached"
        elif poisoned:
            disposition, reason = "quarantined", "poison metadata"
        elif reliability < self.reliability_floor:
            disposition, reason = "quarantined", "reliability below floor"
        else:
            disposition, reason = "accepted", "released and sufficiently reliable"
        return FeedbackDisposition(str(event["opportunity_id"]), disposition, None if release is None else int(release), reliability, poisoned, reason)
