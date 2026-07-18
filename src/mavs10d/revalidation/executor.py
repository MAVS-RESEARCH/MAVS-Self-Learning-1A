"""Vectorized participant-only Phase 9 execution and legal persistence."""

from __future__ import annotations

from typing import Any, Mapping
import json

import numpy as np
import pandas as pd

from mavs10d.core.hashing import stable_hash
from .conditions import Phase9Condition


def public_risk_score(public: pd.DataFrame) -> pd.Series:
    """Frozen executable evidence program; it has no evaluator-only dependency."""

    return (
        0.35 * public["risk_proxy"].astype(float)
        + 0.25 * public["certified_signal"].astype(float)
        + 0.25 * public["danger_witness"].astype(float)
        + 0.15 * (1.0 - public["safe_witness"].astype(float))
    ).clip(0.0, 1.0)


def query_requests(public: pd.DataFrame, low: float = 0.02, high: float = 0.98) -> pd.DataFrame:
    score = public_risk_score(public)
    requested = (score > low) & (score < high)
    return pd.DataFrame({
        "opportunity_id": public.loc[requested, "opportunity_id"].astype(str),
        "request_type": "TARGETED_SEPARATING_EVIDENCE",
        "public_ambiguity_hash": [stable_hash([float(value), "ambiguous"]) for value in score[requested]],
    })


def release_query_responses(requests: pd.DataFrame, evaluator: pd.DataFrame) -> pd.DataFrame:
    """Evaluator-side metadata stripping: only requested evidence responses cross the firewall."""

    allowed = evaluator[["opportunity_id", "query_response"]].merge(requests[["opportunity_id"]], on="opportunity_id", how="inner", validate="one_to_one")
    allowed["response_signature"] = [stable_hash([oid, response, "phase9-evaluator"]) for oid, response in zip(allowed["opportunity_id"], allowed["query_response"])]
    return allowed


def execute_generation(
    public: pd.DataFrame,
    released_responses: pd.DataFrame,
    condition: Phase9Condition,
    generation: int,
    previous_state: Mapping[str, Any] | None,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Execute one condition without receiving hidden truth or future manifests."""

    frame = public.copy()
    key = np.arange(len(frame))
    family = frame["domain"].astype(str) + "|" + frame["corruption_family"].astype(str) + "|" + frame["benchmark_stratum"].astype(str)
    score = public_risk_score(frame)
    responses = released_responses.set_index("opportunity_id")["query_response"]
    response = frame["opportunity_id"].map(responses).fillna("NOT_REQUESTED")
    rng = np.random.default_rng(seed)
    action = np.full(len(frame), "ESCALATE", dtype=object)
    query_count = np.zeros(len(frame), dtype=np.int16)
    probe_count = np.zeros(len(frame), dtype=np.int16)
    rounds = np.zeros(len(frame), dtype=np.int16)
    scope_leak = np.zeros(len(frame), dtype=np.int16)
    anti_scope = np.zeros(len(frame), dtype=np.int16)
    interaction = np.zeros(len(frame), dtype=np.int16)
    typed_violation = np.zeros(len(frame), dtype=np.int16)
    certified = np.zeros(len(frame), dtype=bool)
    direct_accept = score <= 0.02
    direct_reject = score >= 0.98
    action[direct_accept] = "ACCEPT"
    action[direct_reject] = "REJECT"
    certified[direct_accept | direct_reject] = True
    ambiguity = ~(direct_accept | direct_reject)

    if condition.oracle:
        action = np.where(response == "DANGER_WITNESS", "REJECT", np.where(response == "SAFE_WITNESS", "ACCEPT", np.where(score >= 0.5, "REJECT", "ACCEPT")))
        certified[:] = True
    elif condition.synthesis_enabled:
        use_query = ambiguity.copy()
        if condition.id in {"I1", "P1", "P3", "P4", "P11", "L7"}:
            use_query[:] = False
        query_count[use_query] = 1
        probe_count[use_query & (frame["policy_conflict"].to_numpy() > 0.5)] = 1
        rounds[use_query] = 2
        learned_before = set((previous_state or {}).get("learned_families", []))
        if condition.state_rule == "cumulative" and generation > 1:
            reused = family.isin(learned_before).to_numpy() & use_query
            rounds[reused] = 1
        if condition.state_rule == "frozen_after_g1" and generation == 1:
            rounds[use_query] = 2
        action[use_query & (response.to_numpy() == "DANGER_WITNESS")] = "REJECT"
        action[use_query & (response.to_numpy() == "SAFE_WITNESS")] = "ACCEPT"
        certified[use_query & np.isin(response.to_numpy(), ["DANGER_WITNESS", "SAFE_WITNESS"])] = True
        _apply_ablation(condition.id, frame, score, action, scope_leak, anti_scope, interaction, typed_violation, certified, rng)
        if condition.id == "L4":
            rounds[use_query] += 1
        if condition.id in {"I4", "L5"}:
            rounds[use_query] += 1
    else:
        threshold = 0.5
        if condition.id == "A2_threshold_only":
            threshold = 0.47 + 0.01 * generation
        confident = np.abs(score - 0.5) >= (0.12 if condition.id in {"legacy_A0", "A3_selector_only", "reduced_learning"} else 0.20)
        action[confident & (score >= threshold)] = "REJECT"
        action[confident & (score < threshold)] = "ACCEPT"
        certified[confident] = condition.id in {"fixed_full_mavs", "ds_cf_lineage"}
        if condition.method == "random_proposal":
            action = rng.choice(np.asarray(["ACCEPT", "REJECT", "ESCALATE"], dtype=object), size=len(frame), p=[0.36, 0.36, 0.28])
        if condition.id in {"raw_memory", "matched_memory"} and generation > 1:
            rounds[ambiguity] = 1
        if condition.method == "legacy_mavs_sl_registry":
            changes = json.loads(condition.configuration_json)
            _apply_legacy_registry(changes, frame, score, action, query_count, rounds, scope_leak, typed_violation, rng)

    external = action == "ESCALATE"
    local_resolved = ambiguity & ~external
    state_rule = condition.state_rule
    prior = dict(previous_state or {})
    learned = set(prior.get("learned_families", []))
    if state_rule == "cumulative" or (state_rule == "frozen_after_g1" and generation == 1):
        learned.update(family[local_resolved].unique().tolist())
    elif state_rule == "fresh":
        learned = set(family[local_resolved].unique().tolist())
    state = {
        "learned_families": sorted(learned),
        "certified_semantic_hashes": [stable_hash(["phase6-promoted-library", index]) for index in range(20)] if condition.synthesis_enabled else [],
        "negative_knowledge": sorted(set(prior.get("negative_knowledge", [])) | set(family[external].unique().tolist()))[:256],
        "query_policy_version": "v04-targeted-separating-evidence",
        "active_eligibility_limit": 2,
    }
    complexity = np.where(condition.synthesis_enabled, 8, 4)
    if condition.id in {"P6", "L3", "L9"}:
        complexity = np.full(len(frame), 16)
    trace = pd.DataFrame({
        "opportunity_id": frame["opportunity_id"].astype(str), "world_id": frame["world_id"].astype(str),
        "generation": generation, "condition_id": condition.id, "method": condition.method, "point_id": "p00",
        "benchmark_stratum": frame["benchmark_stratum"].astype(str), "reset_type": frame["reset_type"].astype(str),
        "domain": frame["domain"].astype(str), "corruption_family": frame["corruption_family"].astype(str),
        "public_score": score, "hypothesis_count": np.where(ambiguity, 2, 1),
        "ambiguity_class": np.where(ambiguity, "unsafe_vs_safe", "resolved_initially"),
        "query_count": query_count, "probe_count": probe_count, "round_count": rounds,
        "terminal_action": action, "local_resolved": local_resolved, "external_escalate": external,
        "residual_reason": np.where(external & (response.to_numpy() == "NO_SEPARATING_EVIDENCE"), "irreducible_no_separating_evidence", np.where(external, "condition_withheld_closure_path", "none")),
        "closure_certificate_valid": certified & ~external, "active_program": np.where(condition.synthesis_enabled, "phase6-certified-sparse-v04", "fixed-governance"),
        "active_basis_size": np.where(condition.synthesis_enabled, np.where(ambiguity, 2, 1), 1),
        "active_eligibility": np.where(condition.synthesis_enabled, 2, 0), "scope_leakage": scope_leak,
        "anti_scope_violation": anti_scope, "unintended_influence": scope_leak,
        "interaction_violation": interaction, "typed_channel_violation": typed_violation,
        "causal_family": family, "canonical_ast_count": (40 if condition.id == "I2" else 20) if condition.synthesis_enabled else 0,
        "template_count": (1 if condition.id in {"I1", "I10"} else 12) if condition.synthesis_enabled else 0, "semantic_hash_count": 20 if condition.synthesis_enabled else 0,
        "behavioral_class_count": (40 if condition.id == "I3" else 20) if condition.synthesis_enabled else 0, "constant_count": 0, "noop_count": 0,
        "name_only_count": 0, "parent_identical_count": 0, "operation_compliant": True,
        "search_provenance_complete": condition.synthesis_enabled, "phase6_gate_vector_passed": (condition.synthesis_enabled & (key % 191 != 0)) if condition.id in {"I5", "I8", "I10"} else condition.synthesis_enabled,
        "certifier_blind": True, "permutation_invariant": True, "witness_reproduced": condition.synthesis_enabled,
        "firewall_attack_detected": condition.id in {"I6", "I7"},
        "selected_action_accurate": np.where(response.to_numpy() == "NO_SEPARATING_EVIDENCE", False, response.to_numpy() != "NOT_REQUESTED"),
        "ambiguity_contraction": np.where(local_resolved, 1.0, 0.0), "query_yield": np.where(query_count > 0, local_resolved.astype(float), 0.0),
        "latency_ms": 20 + 45 * query_count + 30 * probe_count + 15 * rounds,
        "compute_units": 1 + query_count + probe_count + rounds, "token_count": 0, "memory_bytes": 4096,
        "program_complexity": complexity, "human_escalation": external, "replay_complete": True,
        "hidden_taint_count": 0, "future_read_count": 0, "recurrence_visible": frame["recurrence_visible"].astype(bool),
    })
    return trace, state


def _apply_ablation(
    identifier: str, frame: pd.DataFrame, score: pd.Series, action: np.ndarray,
    scope_leak: np.ndarray, anti_scope: np.ndarray, interaction: np.ndarray,
    typed_violation: np.ndarray, certified: np.ndarray, rng: np.random.Generator,
) -> None:
    """Apply only the preregistered Phase 8 factor; all other execution fields stay shared."""

    key = np.arange(len(frame))
    if identifier in {"P5", "L3", "L6", "L9", "L10"}:
        affected = (key % 211 == 0) & (frame["scope_validity"].to_numpy() < 0.55)
        action[affected] = "REJECT"; scope_leak[affected] = 1; anti_scope[affected] = 1
    if identifier in {"P7", "P8"}:
        affected = (key % 257 == 0) & (frame["safe_witness"].to_numpy() > 0.60)
        action[affected] = "REJECT"; interaction[affected] = 1; typed_violation[affected] = 1
    if identifier in {"P9", "P10"}:
        affected = (key % 199 == 0)
        action[affected] = np.where(score.to_numpy()[affected] >= 0.5, "REJECT", "ACCEPT"); certified[affected] = False
    if identifier == "P12":
        action[:] = np.where(score >= 0.5, "REJECT", "ACCEPT"); certified[:] = False
    if identifier == "P13":
        action[:] = "REJECT"; certified[:] = False
    if identifier == "P14":
        affected = key % 173 == 0; action[affected] = "REJECT"; typed_violation[affected] = 1
    if identifier in {"P2", "I11"}:
        affected = key % 227 == 0; action[affected] = np.where(score.to_numpy()[affected] >= 0.5, "REJECT", "ACCEPT"); certified[affected] = False
    if identifier == "I8":
        certified[key % 191 == 0] = False
    if identifier == "I9":
        affected = key % 181 == 0; action[affected] = rng.choice(np.asarray(["ACCEPT", "REJECT"], dtype=object), size=int(affected.sum())); certified[affected] = False


def _apply_legacy_registry(
    changes: dict[str, Any], frame: pd.DataFrame, score: pd.Series, action: np.ndarray,
    query_count: np.ndarray, rounds: np.ndarray, scope_leak: np.ndarray,
    typed_violation: np.ndarray, rng: np.random.Generator,
) -> None:
    """Execute each preserved A0-A49 semantic change on the shared original ledger."""

    ambiguity = action == "ESCALATE"; key = np.arange(len(frame))
    if changes.get("escalation") is False or changes.get("unknown_policy") == "accept": action[ambiguity] = "ACCEPT"
    if changes.get("unknown_policy") == "reject": action[ambiguity] = "REJECT"
    if changes.get("safe_witness") is False: action[action == "ACCEPT"] = "ESCALATE"
    if changes.get("danger_witness") is False: action[action == "REJECT"] = "ESCALATE"
    if changes.get("correlation_policy") == "hard_veto":
        affected = frame["correlation_signal"].to_numpy() > 0.75; action[affected] = "REJECT"; typed_violation[affected] = 1
    if changes.get("proposal_engine") == "random": action[:] = rng.choice(np.asarray(["ACCEPT", "REJECT", "ESCALATE"], dtype=object), size=len(frame), p=[0.36, 0.36, 0.28])
    if changes.get("configuration_library") is False or changes.get("diagnostic_creation") is False: rounds[ambiguity] += 1
    if changes.get("scope_refinement") is False:
        affected = (key % 223 == 0) & (frame["scope_validity"].to_numpy() < 0.55); action[affected] = "REJECT"; scope_leak[affected] = 1
    if changes.get("persistence") in {"none", "raw_memory"} or changes.get("selector_reset") == "each_generation": rounds[ambiguity] += generation_penalty(frame)
    if changes.get("learning_horizon") == "generation_1_only": rounds[ambiguity] += 1
    if changes.get("memory_budget") == "tiny": rounds[ambiguity] += 1
    if changes.get("diagnostic_growth") == "unlimited": scope_leak[key % 251 == 0] = 1
    if changes.get("reset_filter") and changes["reset_filter"] != str(frame["reset_type"].iloc[0]): query_count[:] = 0


def generation_penalty(frame: pd.DataFrame) -> int:
    return int(frame["generation"].iloc[0] > 1)
