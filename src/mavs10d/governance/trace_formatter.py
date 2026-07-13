from __future__ import annotations

from typing import Any

from mavs10d.baselines.common import clamp
from mavs10d.core.hashing import stable_hash
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, Observation, mavs_trace_template
from mavs10d.governance.diagnostics import diagnostic_flags
from mavs10d.governance.escalation import HardVetoResult, MitigationResult
from mavs10d.governance.severity import SeverityResult
from mavs10d.governance.thresholds import ThresholdResult


def format_mavs_trace(
    *,
    obs: Observation,
    candidate: CandidateAction,
    representation: dict[str, Any],
    support_scores: dict[str, float],
    weights: dict[str, float],
    diagnostics: dict[str, float],
    severity: SeverityResult,
    mitigation: MitigationResult,
    threshold: ThresholdResult,
    consensus: float,
    hard_veto: HardVetoResult,
    final_decision: str,
    risk_score: float,
) -> dict[str, Any]:
    # console.log: phase4.trace_formatter.format.start
    console_log(
        "phase4.trace_formatter.format.start",
        episode_id=obs.episode_id,
        t=obs.t,
        final_decision=final_decision,
    )
    flags = diagnostic_flags(diagnostics)
    trace = mavs_trace_template()
    trace.update(
        {
            "specialist_id": list(candidate.specialist_outputs),
            "representation_hash": representation["hash"],
            "support_score": clamp((consensus + 1.0) / 2.0),
            "confidence": candidate.confidence,
            "source": "mavs_gc",
            "corruption_exposure": obs.corruption_hint,
            "diagnostic_values": diagnostics,
            "disagreement": diagnostics["disagreement"],
            "consistency": diagnostics["consistency"],
            "missing_evidence": diagnostics["evidence_missingness"],
            "policy_conflict": diagnostics["policy_conflict"],
            "corruption_signal": diagnostics["corruption_signal"],
            "raw_severity": severity.raw_severity,
            "normalized_severity": severity.normalized_severity,
            "severity_contribution_breakdown": severity.contribution_breakdown,
            "base_threshold": threshold.base_threshold,
            "threshold_delta": threshold.threshold_delta,
            "final_threshold": threshold.final_threshold,
            "escalation_reason": None,
            "fallback_action": None,
        }
    )
    formal_calculus = {
        "X": {
            "episode_id": obs.episode_id,
            "t": obs.t,
            "visible_state_hash": stable_hash(obs.visible_state),
        },
        "Phi": representation,
        "F": list(candidate.specialist_outputs),
        "G": diagnostics,
        "A": {
            "raw_severity": severity.raw_severity,
            "normalized_severity": severity.normalized_severity,
            "breakdown": severity.contribution_breakdown,
        },
        "W": weights,
        "P": {
            "mitigation_strength": mitigation.strength,
            "organs": mitigation.organs,
            "rationale": mitigation.rationale,
        },
        "Theta": threshold.__dict__,
        "Pi": {
            "final_decision": final_decision,
            "risk_score": risk_score,
        },
        "r_i": support_scores,
        "w_i": weights,
        "z": flags,
        "a": severity.normalized_severity,
        "m": mitigation.__dict__,
        "theta": threshold.final_threshold,
        "R": consensus,
        "hard_veto": hard_veto.__dict__,
        "final_decision": final_decision,
    }
    trace["formal_calculus"] = formal_calculus
    trace["supports_r_i"] = support_scores
    trace["weights_w_i"] = weights
    trace["flags_z"] = flags
    trace["severity_a"] = severity.normalized_severity
    trace["mitigation_m"] = mitigation.__dict__
    trace["threshold_theta"] = threshold.final_threshold
    trace["consensus_R"] = consensus
    trace["hard_veto"] = hard_veto.__dict__
    trace["final_decision"] = final_decision
    # console.log: phase4.trace_formatter.format.complete
    console_log(
        "phase4.trace_formatter.format.complete",
        representation_hash=representation["hash"],
        final_decision=final_decision,
    )
    return trace

