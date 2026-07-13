from __future__ import annotations

from collections import Counter
from typing import Any

from mavs10d.baselines.common import candidate_risk, clamp, disagreement_metrics, specialist_scores
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, Observation


DIAGNOSTIC_NAMES: tuple[str, ...] = (
    "disagreement",
    "consistency",
    "evidence_missingness",
    "policy_conflict",
    "corruption_signal",
    "provenance_concentration",
    "shared_source_suspicion",
    "confidence_inflation",
    "specialist_collapse_indicator",
)


def compute_diagnostics(obs: Observation, candidate: CandidateAction) -> dict[str, float]:
    # console.log: phase4.diagnostics.compute.start
    console_log(
        "phase4.diagnostics.compute.start",
        episode_id=obs.episode_id,
        t=obs.t,
        specialist_count=len(candidate.specialist_outputs),
    )
    scores = specialist_scores(candidate)
    disagreement = disagreement_metrics(candidate)
    score_mean = sum(scores) / len(scores) if scores else 1.0 - candidate_risk(candidate)
    source_counts = Counter(_specialist_source(output) for output in candidate.specialist_outputs.values())
    provenance_concentration = (
        max(source_counts.values()) / max(1, sum(source_counts.values()))
        if source_counts
        else 0.0
    )
    provenance_concentration = max(
        provenance_concentration,
        float(candidate.provenance.get("provenance_concentration", 0.0) or 0.0),
        float(obs.visible_state.get("provenance_concentration", 0.0) or 0.0),
    )
    transform_names = _transform_names(candidate.provenance.get("transform_history", []))
    shared_source_suspicion = _shared_source_suspicion(obs, candidate, transform_names)
    evidence_missingness = _evidence_missingness(obs, candidate)
    policy_conflict = _policy_conflict(obs, candidate)
    corruption_signal = clamp(float(obs.risk_context.get("corruption_level", 0.0) or 0.0))
    confidence_inflation = clamp(float(candidate.confidence) - score_mean)
    specialist_collapse = (
        1.0
        if disagreement["spread"] <= 0.05
        and (shared_source_suspicion >= 0.50 or corruption_signal >= 0.50)
        else 0.0
    )
    diagnostics = {
        "disagreement": clamp(disagreement["spread"]),
        "consistency": clamp(1.0 - disagreement["spread"]),
        "evidence_missingness": evidence_missingness,
        "policy_conflict": policy_conflict,
        "corruption_signal": corruption_signal,
        "provenance_concentration": clamp(provenance_concentration),
        "shared_source_suspicion": shared_source_suspicion,
        "confidence_inflation": confidence_inflation,
        "specialist_collapse_indicator": specialist_collapse,
    }
    # console.log: phase4.diagnostics.compute.complete
    console_log(
        "phase4.diagnostics.compute.complete",
        episode_id=obs.episode_id,
        t=obs.t,
        diagnostics=diagnostics,
    )
    return diagnostics


def diagnostic_flags(diagnostics: dict[str, float]) -> dict[str, bool]:
    # console.log: phase4.diagnostics.flags
    console_log("phase4.diagnostics.flags", diagnostics=diagnostics)
    return {
        "disagreement": diagnostics.get("disagreement", 0.0) >= 0.30,
        "low_consistency": diagnostics.get("consistency", 1.0) <= 0.65,
        "evidence_missing": diagnostics.get("evidence_missingness", 0.0) >= 0.50,
        "policy_conflict": diagnostics.get("policy_conflict", 0.0) >= 0.50,
        "corruption_signal": diagnostics.get("corruption_signal", 0.0) >= 0.30,
        "provenance_concentration": diagnostics.get("provenance_concentration", 0.0) >= 0.75,
        "shared_source_suspicion": diagnostics.get("shared_source_suspicion", 0.0) >= 0.50,
        "confidence_inflation": diagnostics.get("confidence_inflation", 0.0) >= 0.20,
        "specialist_collapse": diagnostics.get("specialist_collapse_indicator", 0.0) >= 0.50,
    }


def _specialist_source(output: Any) -> str:
    if isinstance(output, dict):
        return str(output.get("source", output.get("specialist_id", "unknown")))
    return "unknown"


def _transform_names(history: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict) and "type" in item:
                names.add(str(item["type"]))
    return names


def _evidence_missingness(obs: Observation, candidate: CandidateAction) -> float:
    if candidate.provenance.get("evidence_visible") is False:
        return 1.0
    if obs.visible_state.get("independent_evidence_available") is False:
        return 0.75
    if "evidence_masking" in _transform_names(candidate.provenance.get("transform_history", [])):
        return 1.0
    if "shared_evidence_mask" in _transform_names(candidate.provenance.get("transform_history", [])):
        return 1.0
    return 0.0


def _policy_conflict(obs: Observation, candidate: CandidateAction) -> float:
    text = f"{obs.prompt or ''} {candidate.content}".lower()
    terms = (
        "ignore prior",
        "bypass",
        "shell_exec",
        "delete_file",
        "credential",
        "exfiltration",
        "malware",
        "drop table",
        "rm -rf",
    )
    term_risk = 0.85 if any(term in text for term in terms) else 0.0
    action_risk = 0.90 if candidate.action_type == "tool_call" and "shell_exec" in text else 0.0
    return clamp(max(term_risk, action_risk, candidate_risk(candidate) if term_risk else 0.0))


def _shared_source_suspicion(
    obs: Observation,
    candidate: CandidateAction,
    transform_names: set[str],
) -> float:
    shared_markers = {
        "shared_wrong_premise",
        "shared_retrieval_context",
        "shared_prompt_injection",
        "shared_evidence_mask",
        "shared_confidence_bias",
        "shared_feature_corruption",
        "shared_provenance_concentration",
    }
    score = 0.0
    if any(name in transform_names for name in shared_markers):
        score = max(score, 1.0)
    if any(candidate.provenance.get(marker) for marker in shared_markers):
        score = max(score, 1.0)
    if str(obs.visible_state.get("shared_context_source", "")).lower() in {
        "single_retrieval_context",
        "shared_retrieval_context",
        "shared_provenance_cluster",
    }:
        score = max(score, 0.75)
    if obs.visible_state.get("specialist_agreement") == "high" and obs.visible_state.get(
        "independent_evidence_available"
    ) is False:
        score = max(score, 0.65)
    return clamp(score)
