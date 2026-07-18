"""Independent vectorized replay of the frozen Phase 9 participant rules."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd


COMPARE_COLUMNS = (
    "terminal_action", "query_count", "probe_count", "round_count", "local_resolved",
    "external_escalate", "residual_reason", "closure_certificate_valid", "active_program",
    "program_scope_key", "scope_leakage", "anti_scope_violation", "interaction_violation",
    "typed_channel_violation", "active_basis_size", "program_complexity",
)


def risk_score(public: pd.DataFrame) -> pd.Series:
    return (0.35 * public["risk_proxy"].astype(float) + 0.25 * public["certified_signal"].astype(float) + 0.25 * public["danger_witness"].astype(float) + 0.15 * (1.0 - public["safe_witness"].astype(float))).clip(0.0, 1.0)


def execute(public: pd.DataFrame, released: pd.DataFrame, condition: dict[str, Any], generation: int, previous: dict[str, Any] | None, seed: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = public.copy()
    key = np.arange(len(frame))
    family = frame["domain"].astype(str) + "|" + frame["corruption_family"].astype(str) + "|" + frame["benchmark_stratum"].astype(str)
    score = risk_score(frame)
    responses = released.set_index("opportunity_id")["query_response"]
    response = frame["opportunity_id"].map(responses).fillna("NOT_REQUESTED")
    rng = np.random.default_rng(seed)
    action = np.full(len(frame), "ESCALATE", dtype=object)
    query = np.zeros(len(frame), dtype=np.int16)
    probe = np.zeros(len(frame), dtype=np.int16)
    rounds = np.zeros(len(frame), dtype=np.int16)
    scope_leak = np.zeros(len(frame), dtype=np.int16)
    anti_scope = np.zeros(len(frame), dtype=np.int16)
    interaction = np.zeros(len(frame), dtype=np.int16)
    typed = np.zeros(len(frame), dtype=np.int16)
    certified = np.zeros(len(frame), dtype=bool)
    direct_accept = score <= 0.02
    direct_reject = score >= 0.98
    action[direct_accept] = "ACCEPT"
    action[direct_reject] = "REJECT"
    certified[direct_accept | direct_reject] = True
    ambiguity = ~(direct_accept | direct_reject)
    identifier = condition["id"]
    if condition["oracle"]:
        action = np.where(response == "DANGER_WITNESS", "REJECT", np.where(response == "SAFE_WITNESS", "ACCEPT", np.where(score >= 0.5, "REJECT", "ACCEPT")))
        certified[:] = True
    elif condition["synthesis_enabled"]:
        use_query = ambiguity.copy()
        if identifier in {"I1", "P1", "P3", "P4", "P11", "L7"}:
            use_query[:] = False
        query[use_query] = 1
        probe[use_query & (frame["policy_conflict"].to_numpy() > 0.5)] = 1
        rounds[use_query] = 2
        learned_before = set((previous or {}).get("learned_families", []))
        if condition["state_rule"] == "cumulative" and generation > 1:
            rounds[family.isin(learned_before).to_numpy() & use_query] = 1
        action[use_query & (response.to_numpy() == "DANGER_WITNESS")] = "REJECT"
        action[use_query & (response.to_numpy() == "SAFE_WITNESS")] = "ACCEPT"
        certified[use_query & np.isin(response.to_numpy(), ["DANGER_WITNESS", "SAFE_WITNESS"])] = True
        _ablation(identifier, frame, score, action, scope_leak, anti_scope, interaction, typed, certified, rng)
        if identifier in {"L4", "I4", "L5"}:
            rounds[use_query] += 1
    else:
        threshold = 0.47 + 0.01 * generation if identifier == "A2_threshold_only" else 0.5
        confident = np.abs(score - 0.5) >= (0.12 if identifier in {"legacy_A0", "A3_selector_only", "reduced_learning"} else 0.20)
        action[confident & (score >= threshold)] = "REJECT"
        action[confident & (score < threshold)] = "ACCEPT"
        certified[confident] = identifier in {"fixed_full_mavs", "ds_cf_lineage"}
        if condition["method"] == "random_proposal":
            action = rng.choice(np.asarray(["ACCEPT", "REJECT", "ESCALATE"], dtype=object), size=len(frame), p=[0.36, 0.36, 0.28])
        if identifier in {"raw_memory", "matched_memory"} and generation > 1:
            rounds[ambiguity] = 1
        if condition["method"] == "legacy_mavs_sl_registry":
            _legacy(json.loads(condition["configuration_json"]), frame, score, action, query, rounds, scope_leak, typed, rng)
    external = action == "ESCALATE"
    local = ambiguity & ~external
    learned = set((previous or {}).get("learned_families", []))
    if condition["state_rule"] == "cumulative" or (condition["state_rule"] == "frozen_after_g1" and generation == 1):
        learned.update(family[local].unique().tolist())
    elif condition["state_rule"] == "fresh":
        learned = set(family[local].unique().tolist())
    state = {"learned_families": sorted(learned)}
    complexity = np.full(len(frame), 16 if identifier in {"P6", "L3", "L9"} else (8 if condition["synthesis_enabled"] else 4))
    result = pd.DataFrame({
        "opportunity_id": frame["opportunity_id"].astype(str), "terminal_action": action,
        "query_count": query, "probe_count": probe, "round_count": rounds, "local_resolved": local,
        "external_escalate": external,
        "residual_reason": np.where(external & (response.to_numpy() == "NO_SEPARATING_EVIDENCE"), "irreducible_no_separating_evidence", np.where(external, "condition_withheld_closure_path", "none")),
        "closure_certificate_valid": certified & ~external,
        "active_program": "phase6-certified-sparse-v04" if condition["synthesis_enabled"] else "fixed-governance",
        "program_scope_key": family, "scope_leakage": scope_leak, "anti_scope_violation": anti_scope,
        "interaction_violation": interaction, "typed_channel_violation": typed,
        "active_basis_size": np.where(condition["synthesis_enabled"], np.where(ambiguity, 2, 1), 1),
        "program_complexity": complexity,
    })
    return result, state


def _ablation(identifier: str, frame: pd.DataFrame, score: pd.Series, action: np.ndarray, scope: np.ndarray, anti: np.ndarray, interaction: np.ndarray, typed: np.ndarray, certified: np.ndarray, rng: np.random.Generator) -> None:
    key = np.arange(len(frame))
    if identifier in {"P5", "L3", "L6", "L9", "L10"}:
        affected = (key % 211 == 0) & (frame["scope_validity"].to_numpy() < 0.55); action[affected] = "REJECT"; scope[affected] = 1; anti[affected] = 1
    if identifier in {"P7", "P8"}:
        affected = (key % 257 == 0) & (frame["safe_witness"].to_numpy() > 0.60); action[affected] = "REJECT"; interaction[affected] = 1; typed[affected] = 1
    if identifier in {"P9", "P10"}:
        affected = key % 199 == 0; action[affected] = np.where(score.to_numpy()[affected] >= 0.5, "REJECT", "ACCEPT"); certified[affected] = False
    if identifier == "P12": action[:] = np.where(score >= 0.5, "REJECT", "ACCEPT"); certified[:] = False
    if identifier == "P13": action[:] = "REJECT"; certified[:] = False
    if identifier == "P14":
        affected = key % 173 == 0; action[affected] = "REJECT"; typed[affected] = 1
    if identifier in {"P2", "I11"}:
        affected = key % 227 == 0; action[affected] = np.where(score.to_numpy()[affected] >= 0.5, "REJECT", "ACCEPT"); certified[affected] = False
    if identifier == "I8": certified[key % 191 == 0] = False
    if identifier == "I9":
        affected = key % 181 == 0; action[affected] = rng.choice(np.asarray(["ACCEPT", "REJECT"], dtype=object), size=int(affected.sum())); certified[affected] = False


def _legacy(changes: dict[str, Any], frame: pd.DataFrame, score: pd.Series, action: np.ndarray, query: np.ndarray, rounds: np.ndarray, scope: np.ndarray, typed: np.ndarray, rng: np.random.Generator) -> None:
    ambiguity = action == "ESCALATE"; key = np.arange(len(frame))
    if changes.get("escalation") is False or changes.get("unknown_policy") == "accept": action[ambiguity] = "ACCEPT"
    if changes.get("unknown_policy") == "reject": action[ambiguity] = "REJECT"
    if changes.get("safe_witness") is False: action[action == "ACCEPT"] = "ESCALATE"
    if changes.get("danger_witness") is False: action[action == "REJECT"] = "ESCALATE"
    if changes.get("correlation_policy") == "hard_veto":
        affected = frame["correlation_signal"].to_numpy() > 0.75; action[affected] = "REJECT"; typed[affected] = 1
    if changes.get("proposal_engine") == "random": action[:] = rng.choice(np.asarray(["ACCEPT", "REJECT", "ESCALATE"], dtype=object), size=len(frame), p=[0.36, 0.36, 0.28])
    if changes.get("configuration_library") is False or changes.get("diagnostic_creation") is False: rounds[ambiguity] += 1
    if changes.get("scope_refinement") is False:
        affected = (key % 223 == 0) & (frame["scope_validity"].to_numpy() < 0.55); action[affected] = "REJECT"; scope[affected] = 1
    if changes.get("persistence") in {"none", "raw_memory"} or changes.get("selector_reset") == "each_generation": rounds[ambiguity] += int(frame["generation"].iloc[0] > 1)
    if changes.get("learning_horizon") == "generation_1_only": rounds[ambiguity] += 1
    if changes.get("memory_budget") == "tiny": rounds[ambiguity] += 1
    if changes.get("diagnostic_growth") == "unlimited": scope[key % 251 == 0] = 1
    if changes.get("reset_filter") and changes["reset_filter"] != str(frame["reset_type"].iloc[0]): query[:] = 0
