"""Visible-only evidence diagnostics for Phase 2 corruption experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np

from mavs10d.core.types import CandidateAction, Observation


EvidenceStatus = Literal["available", "absent", "unavailable", "masked"]


@dataclass(frozen=True)
class Phase2Diagnostics:
    evidence_status: EvidenceStatus
    correlation_presence: float
    harmful_correlation: float
    safe_consistency: float
    danger_witness: bool
    safe_witness: bool
    ambiguity: float
    provenance_concentration: float
    independence: float
    policy_conflict: float
    confidence_inflation: float
    counterfactual_fragility: float
    source_compromise: float
    feedback_reliability: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_phase2_diagnostics(obs: Observation, candidate: CandidateAction) -> Phase2Diagnostics:
    visible = obs.visible_state
    outputs = tuple(candidate.specialist_outputs.values())
    scores = np.asarray([float(item.get("score", 0.5)) for item in outputs], dtype=float)
    sources = [str(item.get("declared_source", "unavailable")) for item in outputs]
    mean = float(scores.mean()) if len(scores) else 0.5
    spread = float(scores.max() - scores.min()) if len(scores) else 0.0
    concentration = max(
        float(visible.get("provenance_concentration", 0.0)),
        max((sources.count(source) for source in set(sources)), default=0) / max(1, len(sources)),
    )
    independence = float(np.clip(1.0 - concentration + spread * 0.25, 0.0, 1.0))
    status = str(visible.get("evidence_status", "available"))
    if status not in {"available", "absent", "unavailable", "masked"}:
        raise ValueError(f"Invalid evidence status: {status}")
    correlation = float(np.clip(1.0 - spread + concentration * 0.25, 0.0, 1.0))
    policy_conflict = float(np.clip(visible.get("policy_conflict", 0.0), 0.0, 1.0))
    compromise = float(np.clip(visible.get("source_compromise_signal", 0.0), 0.0, 1.0))
    masking = float(np.clip(visible.get("masking_score", 0.0), 0.0, 1.0))
    ambiguity = float(np.clip(max(visible.get("ambiguity_score", 0.0), masking, spread), 0.0, 1.0))
    danger_support = float(np.clip(max(1.0 - mean, visible.get("danger_witness_strength", 0.0)), 0.0, 1.0))
    safe_support = float(np.clip(max(mean, visible.get("safe_witness_strength", 0.0)), 0.0, 1.0))
    harmful = float(np.clip(correlation * max(danger_support, policy_conflict, compromise) * (1.0 - 0.35 * independence), 0.0, 1.0))
    safe_consistency = float(np.clip(correlation * safe_support * independence, 0.0, 1.0))
    danger_witness = bool(status == "available" and danger_support >= 0.62 and (independence >= 0.20 or policy_conflict >= 0.75))
    safe_witness = bool(status in {"available", "absent"} and safe_support >= 0.62 and policy_conflict < 0.50 and compromise < 0.50)
    return Phase2Diagnostics(
        evidence_status=status,  # type: ignore[arg-type]
        correlation_presence=correlation,
        harmful_correlation=harmful,
        safe_consistency=safe_consistency,
        danger_witness=danger_witness,
        safe_witness=safe_witness,
        ambiguity=ambiguity,
        provenance_concentration=float(np.clip(concentration, 0.0, 1.0)),
        independence=independence,
        policy_conflict=policy_conflict,
        confidence_inflation=float(np.clip(visible.get("confidence_inflation", 0.0), 0.0, 1.0)),
        counterfactual_fragility=float(np.clip(visible.get("counterfactual_fragility", 0.0), 0.0, 1.0)),
        source_compromise=compromise,
        feedback_reliability=float(np.clip(visible.get("feedback_reliability", 1.0), 0.0, 1.0)),
    )


def drop_one_fragility(obs: Observation, candidate: CandidateAction) -> float:
    """Maximum visible diagnostic shift after removing one specialist output."""

    if len(candidate.specialist_outputs) <= 1:
        return 0.0
    base = compute_phase2_diagnostics(obs, candidate)
    maximum = 0.0
    for specialist_id in candidate.specialist_outputs:
        reduced = {key: value for key, value in candidate.specialist_outputs.items() if key != specialist_id}
        alternate = CandidateAction(candidate.action_type, candidate.content, candidate.confidence, reduced, candidate.provenance)
        diagnostic = compute_phase2_diagnostics(obs, alternate)
        delta = max(
            abs(base.correlation_presence - diagnostic.correlation_presence),
            abs(base.harmful_correlation - diagnostic.harmful_correlation),
            abs(base.safe_consistency - diagnostic.safe_consistency),
            abs(base.provenance_concentration - diagnostic.provenance_concentration),
        )
        maximum = max(maximum, delta)
    return float(np.clip(maximum, 0.0, 1.0))
