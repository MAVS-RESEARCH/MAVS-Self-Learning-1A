"""Frozen-bank behavior fingerprints and equivalence classes."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from mavs10d.core.hashing import stable_hash
from mavs10d.diagnostics.ast import evaluate_ast
from mavs10d.diagnostics.contracts import ExecutableDiagnostic


def fingerprint_frame(candidate: ExecutableDiagnostic, bank: pd.DataFrame) -> pd.DataFrame:
    candidate.validate()
    features: Mapping[str, Any] = {column: bank[column].to_numpy() for column in candidate.all_feature_references()}
    output = evaluate_ast(candidate.expression_ast, features, candidate.parameters).astype(float)
    positive_scope = evaluate_ast(candidate.positive_scope_ast, features, candidate.parameters).astype(bool)
    anti_scope = evaluate_ast(candidate.anti_scope_ast, features, candidate.parameters).astype(bool)
    active = positive_scope & ~anti_scope & bank["evidence_available"].to_numpy(dtype=bool)
    lower = float(candidate.influence_contract["minimum"])
    upper = float(candidate.influence_contract["maximum"])
    influence = np.where(active, np.clip(output, lower, upper), 0.0)
    result = pd.DataFrame({
        "candidate_id": candidate.candidate_id,
        "bank": bank["bank"].astype(str),
        "case_id": bank["case_id"].astype(str),
        "raw_output": output,
        "discrete_output": (output >= 0.5).astype(int),
        "positive_scope": positive_scope,
        "anti_scope": anti_scope,
        "active": active,
        "query_influence": np.where(candidate.influence_contract["channel"] == "query", influence, 0.0),
        "authority": candidate.influence_contract["channel"],
        "terminal_influence": np.where(candidate.influence_contract["terminal_authority"], influence, 0.0),
    })
    return result.sort_values(["bank", "case_id"], kind="stable").reset_index(drop=True)


def behavioral_hash(frame: pd.DataFrame) -> str:
    columns = ["bank", "case_id", "raw_output", "discrete_output", "positive_scope", "anti_scope", "active", "query_influence", "authority", "terminal_influence"]
    records = frame[columns].to_dict(orient="records")
    return stable_hash(records)


def behaviorally_equivalent(first: pd.DataFrame, second: pd.DataFrame, tolerance: float = 1e-12) -> bool:
    key_columns = ["bank", "case_id", "discrete_output", "positive_scope", "anti_scope", "active", "authority"]
    if not first[key_columns].equals(second[key_columns]):
        return False
    return bool(np.allclose(first["raw_output"], second["raw_output"], atol=tolerance, rtol=0.0)) and bool(
        np.allclose(first["terminal_influence"], second["terminal_influence"], atol=tolerance, rtol=0.0)
    )
