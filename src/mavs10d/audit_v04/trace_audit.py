"""Complete trace, lineage, authority, escalation, and learning-transition audit."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, result_root, verify_frozen_input_index, write_json


def audit_traces() -> dict[str, Any]:
    verify_frozen_input_index()
    cfg = config()
    p7 = REPO_ROOT / cfg["inputs"]["phase7"]
    p9 = REPO_ROOT / cfg["inputs"]["phase9"]
    opportunities = 0
    duplicate_terminal = 0
    missing_hypotheses = 0
    missing_round_lineage = 0
    missing_activation_proof = 0
    missing_authority = 0
    missing_residual = 0
    query_probe_missing_contract = 0
    learning_transition_gaps = 0
    per_track: dict[str, Any] = {}
    for track in ("paired_original_bank", "blind_bank"):
        track_rows = 0
        track_files = 0
        for path in sorted((p9 / track / "decision_traces").glob("*/generation_*.parquet")):
            frame = pd.read_parquet(path)
            track_files += 1
            track_rows += len(frame)
            opportunities += len(frame)
            duplicate_terminal += int(frame["opportunity_id"].duplicated().sum())
            unresolved = frame["hypothesis_count"] > 1
            missing_hypotheses += int((unresolved & (frame["ambiguity_class"].astype(str).str.len() == 0)).sum())
            missing_round_lineage += int(((frame["round_count"] > 0) & (frame["active_program"].astype(str).str.len() == 0)).sum())
            active = frame["active_basis_size"] > 0
            missing_activation_proof += int((active & (frame["program_scope_key"].astype(str).str.len() == 0)).sum())
            terminal = frame["terminal_action"].astype(str).str.upper()
            missing_authority += int((~terminal.isin(["ACCEPT", "REJECT", "ESCALATE"])).sum())
            escalation = frame["external_escalate"].astype(bool)
            missing_residual += int((escalation & frame["residual_reason"].astype(str).isin(["", "none", "nan"])).sum())
        checkpoint_files = sorted((p9 / track / "checkpoints").rglob("*.json"))
        for path in checkpoint_files:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            if "provenance" not in text and "rollback" not in text and "checkpoint" not in path.name.lower():
                learning_transition_gaps += 1
        per_track[track] = {"condition_generation_files": track_files, "terminal_rows": track_rows, "checkpoint_files": len(checkpoint_files)}
    p7_terminals = pd.read_parquet(p7 / "traces" / "terminal_decisions.parquet")
    p7_rounds = pd.read_parquet(p7 / "traces" / "perception_rounds.parquet")
    p7_queries = pd.read_parquet(p7 / "traces" / "queries_and_probes.parquet")
    p7_escalations = pd.read_parquet(p7 / "traces" / "escalations.parquet")
    duplicate_terminal += int(p7_terminals["case_id"].duplicated().sum())
    required_query_fields = {"case_id", "action_type", "target", "result", "cost"}
    missing_fields = sorted(required_query_fields - set(p7_queries.columns))
    query_probe_missing_contract += len(missing_fields)
    if "round_id" in p7_rounds:
        missing_round_lineage += int(p7_rounds["round_id"].isna().sum())
    if "residual_reason" in p7_escalations:
        missing_residual += int(p7_escalations["residual_reason"].astype(str).isin(["", "none", "nan"]).sum())
    completeness = {
        "schema_version": "1.0.0", "canonical_terminal_records_checked": opportunities + len(p7_terminals),
        "duplicate_or_missing_terminal_count": duplicate_terminal, "missing_hypothesis_count": missing_hypotheses,
        "missing_round_lineage_count": missing_round_lineage, "query_probe_contract_gap_count": query_probe_missing_contract,
        "completeness_rate": 1.0 if not (duplicate_terminal + missing_hypotheses + missing_round_lineage + query_probe_missing_contract) else 0.0,
        "per_track": per_track,
    }
    lineage = {"schema_version": "1.0.0", "learning_checkpoint_files_checked": sum(item["checkpoint_files"] for item in per_track.values()), "learning_transition_gap_count": learning_transition_gaps, "runtime_activation_proof_gap_count": missing_activation_proof, "status": "PASS" if learning_transition_gaps == 0 and missing_activation_proof == 0 else "FAIL"}
    authority = {"schema_version": "1.0.0", "terminal_records_checked": opportunities + len(p7_terminals), "missing_or_invalid_authority_count": missing_authority, "status": "PASS" if missing_authority == 0 else "FAIL"}
    residual = {"schema_version": "1.0.0", "phase7_escalations": len(p7_escalations), "missing_residual_decomposition_count": missing_residual, "status": "PASS" if missing_residual == 0 else "FAIL"}
    root = result_root() / "trace"
    write_json(root / "completeness.json", {**completeness, "status": "PASS" if completeness["completeness_rate"] == 1.0 else "FAIL"})
    write_json(root / "lineage.json", lineage)
    write_json(root / "terminal_authority.json", authority)
    write_json(root / "residual_escalation.json", residual)
    statuses = [lineage["status"], authority["status"], residual["status"], "PASS" if completeness["completeness_rate"] == 1.0 else "FAIL"]
    return {"terminal_records_checked": completeness["canonical_terminal_records_checked"], "statuses": statuses, "status": "PASS" if set(statuses) == {"PASS"} else "FAIL"}

