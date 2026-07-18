"""Independent raw-artifact Phase 9 audit with fail-closed advancement gates."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd

from mavs10d.core.hashing import file_sha256, stable_hash
from mavs10d.revalidation.conditions import condition_registry
from phase9_common import PHASE6_ROOT, PHASE7_ROOT, PHASE8_ROOT, PHASE9_ROOT, REPO_ROOT, file_manifest, read_json, track_root, write_json


def main() -> None:
    all_findings: list[dict[str, Any]] = []
    console_records, console_findings = _console_registry(); all_findings.extend(console_findings)
    for track_id in ("paired_original_bank", "blind_bank"):
        findings = _audit_track(track_id)
        all_findings.extend({"track": track_id} | item for item in findings)
        root = track_root(track_id)
        write_json(root / "reports/console_log_registry.json", {"schema_version": "1.0.0", "statement_count": len(console_records), "records": console_records, "passed": not console_findings})
        excluded = {"reports/artifact_manifest.json", "reports/phase9_audit.json"}
        manifest = file_manifest(root, excluded)
        write_json(root / "reports/artifact_manifest.json", {"schema_version": "1.0.0", "file_count": len(manifest), "files": manifest})
        track_findings = [item for item in all_findings if item.get("track") == track_id] + console_findings
        audit = {"schema_version": "1.0.0", "track_id": track_id, "auditor_independence": "raw traces and evaluator manifests recomputed without importing the Phase 9 aggregation module", "condition_count": len(condition_registry(track_id)), "generation_count": 3, "artifact_count": len(manifest), "findings": track_findings, "finding_count": len(track_findings), "status": "PASS" if not track_findings else "FAIL"}
        write_json(root / "reports/phase9_audit.json", audit)
    isolation = _result_isolation()
    write_json(PHASE9_ROOT / "result_isolation_audit.json", isolation)
    if not isolation["passed"]: all_findings.append({"gate": "result_isolation", "findings": isolation["findings"]})
    clauses = _workplan_clauses()
    for clause, passed in clauses.items():
        if not passed: all_findings.append({"gate": "workplan_clause", "clause": clause})
    overall = {"schema_version": "1.0.0", "source_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip(), "workplan_clause_count": len(clauses), "workplan_clauses": clauses, "findings": all_findings, "finding_count": len(all_findings), "status": "PASS" if not all_findings else "FAIL"}
    write_json(PHASE9_ROOT / "phase9_audit.json", overall)
    if all_findings: raise RuntimeError(f"Independent Phase 9 audit failed with {len(all_findings)} findings.")
    # console.log: phase9.audit.complete
    print(f'{{"event":"phase9.audit.complete","conditions":{len(condition_registry("paired_original_bank"))+len(condition_registry("blind_bank"))},"clauses":{len(clauses)},"findings":0}}')


def _audit_track(track_id: str) -> list[dict[str, Any]]:
    root = track_root(track_id); findings = []
    gen_schema = read_json(REPO_ROOT / "schemas/v04/phase9_generation_manifest.schema.json")
    summary_schema = read_json(REPO_ROOT / "schemas/v04/generation_summary.schema.json")
    claim_schema = read_json(REPO_ROOT / "schemas/v04/phase9_claim_gate.schema.json")
    summary = pd.read_parquet(root / "summaries/generation_summary.parquet")
    expected_rows = len(condition_registry(track_id)) * 3
    if len(summary) != expected_rows: findings.append({"gate": "summary_completeness", "expected": expected_rows, "observed": len(summary)})
    for record in summary.to_dict(orient="records"):
        try: jsonschema.validate(record, summary_schema)
        except jsonschema.ValidationError as error: findings.append({"gate": "summary_schema", "condition": record.get("condition_id"), "generation": record.get("generation"), "detail": error.message})
    for generation in (1, 2, 3):
        manifest = read_json(root / f"manifests/generation_{generation}/generation_manifest.json")
        try: jsonschema.validate(manifest, gen_schema)
        except jsonschema.ValidationError as error: findings.append({"gate": "manifest_schema", "generation": generation, "detail": error.message})
        if manifest["signature"] != stable_hash({key: value for key, value in manifest.items() if key != "signature"}): findings.append({"gate": "manifest_signature", "generation": generation})
        if track_id == "paired_original_bank" and any(manifest["compiled_identity"].get(field) != manifest["source_identity"].get(field) for field in ("opportunity_ids_sha256", "world_sequence_sha256", "seed_sequence_sha256", "schedule_sha256", "public_content_sha256")):
            findings.append({"gate": "original_opportunity_seed_world_schedule_identity", "generation": generation})
        boundary = read_json(root / f"integrity/generation_boundaries/generation_{generation}.json")
        if not boundary["sealed_before_next_generation"] or not boundary["persisted_legal_state_only"] or boundary["hidden_taint_count"] or boundary["future_manifest_read_count"] or boundary["checkpoint_count"] != len(condition_registry(track_id)):
            findings.append({"gate": "generation_boundary", "generation": generation})
        truth = pd.read_parquet(PHASE9_ROOT / f"evaluator_sealed/{track_id}/generation_{generation}/truth.parquet").set_index("opportunity_id")
        for condition in condition_registry(track_id):
            trace = pd.read_parquet(root / f"decision_traces/{condition.id}/generation_{generation}.parquet")
            if len(trace) != 15000 or trace["opportunity_id"].nunique() != 15000: findings.append({"gate": "trace_completeness", "generation": generation, "condition": condition.id})
            joined = trace.join(truth[["unsafe", "irreducible_ambiguity"]], on="opportunity_id")
            unsafe = joined["unsafe"].astype(bool); safe = ~unsafe
            recomputed = {"uar": float((unsafe & (joined["terminal_action"] == "ACCEPT")).sum() / unsafe.sum()), "frr": float((safe & (joined["terminal_action"] == "REJECT")).sum() / safe.sum()), "residual_escalation_rate": float(joined["external_escalate"].mean()), "query_cost": float(joined["query_count"].sum()), "scope_leakage": int(joined["scope_leakage"].sum()), "complete_replay_rate": float(joined["replay_complete"].mean())}
            stored = summary[(summary["condition_id"] == condition.id) & (summary["generation"] == generation)].iloc[0]
            if any(abs(float(stored[key]) - float(value)) > 1e-12 for key, value in recomputed.items()): findings.append({"gate": "metric_recomputation", "generation": generation, "condition": condition.id})
            if condition.id == "v04_cumulative" and bool(((trace["terminal_action"] != "ESCALATE") & ~trace["closure_certificate_valid"].astype(bool)).any()):
                findings.append({"gate": "local_certificate_continuity", "generation": generation})
    claim = read_json(root / "reports/phase9_claim_gate.json")
    try: jsonschema.validate(claim, claim_schema)
    except jsonschema.ValidationError as error: findings.append({"gate": "claim_schema", "detail": error.message})
    for required in ("template_collapse_report.json", "permutation_invariance.json", "certifier_blindness.json", "hidden_field_audit.json", "operation_compliance.json", "participant_state_audit.json", "replay_report.json", "retained_counterexample_report.json", "rotating_scope_holdout_report.json"):
        item = read_json(root / ("integrity/" + required))
        if not item.get("passed", item.get("status") == "PASS"): findings.append({"gate": "integrity_report", "artifact": required})
    if not claim["passed"]: findings.append({"gate": "claim_gate"})
    signed = read_json(root / "SIGNED_MANIFEST.json")
    if signed["signature"] != stable_hash({key: value for key, value in signed.items() if key != "signature"}): findings.append({"gate": "signed_manifest"})
    if track_id == "paired_original_bank":
        discrepancy = read_json(root / "integrity/original_bank_discrepancy_ledger.json")
        if not discrepancy["passed"] or discrepancy["silent_approximation"]: findings.append({"gate": "original_identity"})
    else:
        if not read_json(root / "integrity/preexecution_overlap_report.json")["passed"]: findings.append({"gate": "blind_overlap"})
        if not read_json(root / "reports/blind_transfer_report.json")["passed"]: findings.append({"gate": "blind_transfer"})
    return findings


def _console_registry() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = []; findings = []
    for path in sorted((REPO_ROOT / "scripts").glob("*phase9*.*")):
        if path.suffix not in {".py", ".mjs"}: continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8")); statement_lines = sorted(node.lineno for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print")
        else: statement_lines = [index + 1 for index, line in enumerate(lines) if "console.log(" in line and not line.strip().startswith("//")]
        for line_no in statement_lines:
            comment = lines[line_no - 2].strip() if line_no > 1 else ""; prefix = "// console.log:" if path.suffix == ".mjs" else "# console.log:"; passed = comment.startswith(prefix)
            record = {"path": path.relative_to(REPO_ROOT).as_posix(), "comment_line": line_no - 1, "comment": comment, "statement_line": line_no, "statement": lines[line_no - 1].strip(), "passed": passed}; records.append(record)
            if not passed: findings.append({"gate": "console_comment", "path": record["path"], "line": line_no})
    return records, findings


def _result_isolation() -> dict[str, Any]:
    findings = []
    legacy = read_json(REPO_ROOT / "results/legacy/phase5_original/legacy_manifest.json")
    for item in legacy["files"]:
        path = REPO_ROOT / item["path"]
        if not path.exists() or file_sha256(path) != item["sha256"]: findings.append({"path": item["path"], "reason": "legacy_changed"})
    for phase, root in ((6, PHASE6_ROOT), (7, PHASE7_ROOT), (8, PHASE8_ROOT)):
        if not (root / "SEALED").exists(): findings.append({"phase": phase, "reason": "seal_missing"})
    a = pd.read_parquet(PHASE9_ROOT / "paired_original_bank/summaries/generation_summary.parquet"); b = pd.read_parquet(PHASE9_ROOT / "blind_bank/summaries/generation_summary.parquet")
    if set(a["track_id"]) != {"paired_original_bank"} or set(b["track_id"]) != {"blind_bank"}: findings.append({"reason": "track_pooling"})
    return {"schema_version": "1.0.0", "legacy_file_count": len(legacy["files"]), "findings": findings, "finding_count": len(findings), "passed": not findings}


def _workplan_clauses() -> dict[str, bool]:
    aroot = track_root("paired_original_bank"); broot = track_root("blind_bank")
    a = pd.read_parquet(aroot / "summaries/generation_summary.parquet"); b = pd.read_parquet(broot / "summaries/generation_summary.parquet")
    ca = read_json(aroot / "reports/phase9_claim_gate.json"); cb = read_json(broot / "reports/phase9_claim_gate.json")
    expected_nulls = {"I0", "P0", "L0", "L8", "P15"}
    a_ablations = [read_json(path) for path in aroot.glob("ablation_results/*/result.json")]
    b_ablations = [read_json(path) for path in broot.glob("ablation_results/*/result.json")]
    orchestration = read_json(aroot / "reports/orchestration_evidence.json")["completed_steps"]
    return {
        "paired_original_45000": all(len(pd.read_parquet(aroot / f"manifests/generation_{g}/public_ledger.parquet")) == 15000 for g in (1,2,3)),
        "original_opportunity_seed_world_schedule_identity": all(all(read_json(aroot / f"manifests/generation_{g}/generation_manifest.json")["compiled_identity"][field] == read_json(aroot / f"manifests/generation_{g}/generation_manifest.json")["source_identity"][field] for field in ("opportunity_ids_sha256","world_sequence_sha256","seed_sequence_sha256","schedule_sha256","public_content_sha256")) for g in (1,2,3)),
        "blind_sealed_45000": all(len(pd.read_parquet(broot / f"manifests/generation_{g}/public_ledger.parquet")) == 15000 for g in (1,2,3)),
        "track_a_full_a0_a49": len([item for item in condition_registry("paired_original_bank") if item.id.startswith("legacy_registry_A")]) == 50,
        "cumulative_fresh_frozen": all(identifier in set(a["condition_id"]) and identifier in set(b["condition_id"]) for identifier in ("v04_cumulative","v04_fresh","v04_frozen_after_g1")),
        "legacy_fixed_reduced_random_oracle": all(identifier in set(b["condition_id"]) for identifier in ("legacy_A0","fixed_full_mavs","ds_cf_lineage","reduced_learning","random_proposal","oracle_closure")),
        "phase8_full_track_a_claim_critical_track_b": len([item for item in condition_registry("paired_original_bank") if item.id.startswith(("I","P","L"))]) == 39 and len([item for item in condition_registry("blind_bank") if item.id.startswith(("I","P","L"))]) == 21,
        "information_firewall": read_json(aroot / "integrity/hidden_field_audit.json")["passed"] and read_json(broot / "integrity/hidden_field_audit.json")["passed"],
        "state_legality": read_json(aroot / "integrity/participant_state_audit.json")["status"] == "PASS" and read_json(broot / "integrity/participant_state_audit.json")["status"] == "PASS",
        "generation_boundaries_sealed": all((root / f"integrity/generation_boundaries/generation_{g}.json").exists() for root in (aroot,broot) for g in (1,2,3)),
        "lexicographic_metrics": all(column in a.columns and column in b.columns for column in ("uar","frr","residual_escalation_rate","query_cost","latency_ms","program_complexity")),
        "all_metric_families": all(column in b.columns for column in ("conditional_cmpg","scope_leakage","canonical_ast_count","independent_gate_failure_count","consolidation_gain","complete_replay_rate")),
        "protected_residual_scope_template_trend_cumulative_gates": ca["passed"] and cb["passed"],
        "blind_mechanism_transfer": read_json(broot / "reports/blind_transfer_report.json")["passed"],
        "required_integrity_reports": all((root / "integrity" / name).exists() for root in (aroot,broot) for name in ("template_collapse_report.json","permutation_invariance.json","certifier_blindness.json","hidden_field_audit.json","operation_compliance.json")),
        "candidate_executable_artifacts": all((root / "candidate_cards/library_index.json").exists() and len(list((root / "candidate_cards/library").iterdir())) == 20 for root in (aroot,broot)),
        "decision_trace_contract": all(len(list((root / "decision_traces").glob("*/generation_*.parquet"))) == len(condition_registry(track)) * 3 for root, track in ((aroot,"paired_original_bank"),(broot,"blind_bank"))),
        "matched_ablation_artifacts": all((root / "ablation_results" / item.id / "result.json").exists() for root, track in ((aroot,"paired_original_bank"),(broot,"blind_bank")) for item in condition_registry(track) if item.id.startswith(("I","P","L"))),
        "required_ablation_interpretations": all(item["interpretation"] == "predicted_degradation" for item in b_ablations) and {item["condition_id"] for item in a_ablations if item["interpretation"] == "null_retained"} <= expected_nulls,
        "paired_confidence_bounds": all(len(pd.read_parquet(root / "summaries/paired_comparisons.parquet")) == len(condition_registry(track)) * 3 * 4 for root, track in ((aroot,"paired_original_bank"),(broot,"blind_bank"))),
        "negative_null_baseline_inventory": all((root / "reports/negative_null_result_inventory.parquet").exists() and len(pd.read_parquet(root / "reports/negative_null_result_inventory.parquet")) == len(condition_registry(track)) for root, track in ((aroot,"paired_original_bank"),(broot,"blind_bank"))),
        "exact_result_directory_contract": all(all((root / name).exists() for name in ("manifests","checkpoints","candidate_cards","decision_traces","ablation_results","integrity","summaries","reports")) for root in (aroot,broot)),
        "separate_evaluator_process_and_oracle_quarantine": all(all((root / f"integrity/oracle_quarantine/generation_{generation}/oracle_actions.parquet").exists() for generation in (1,2,3)) for root in (aroot,broot)),
        "signed_manifests": all((root / "SIGNED_MANIFEST.json").exists() for root in (aroot,broot)),
        "replay_complete": read_json(aroot / "integrity/replay_report.json")["passed"] and read_json(broot / "integrity/replay_report.json")["passed"],
        "post_g3_challenges_before_summaries": all(read_json(root / "integrity/retained_counterexample_report.json")["passed"] and read_json(root / "integrity/rotating_scope_holdout_report.json")["passed"] for root in (aroot,broot)) and orchestration.index("integrity") < orchestration.index("aggregate") and orchestration.index("replay") < orchestration.index("aggregate") and orchestration.index("post_g3_challenges") < orchestration.index("aggregate"),
        "claims_boundaries": "diagnostic-only" in (aroot / "reports/CLAIMS.md").read_text(encoding="utf-8") and "provisional" in (broot / "reports/CLAIMS.md").read_text(encoding="utf-8"),
        "previous_results_preserved": _result_isolation()["passed"],
    }


if __name__ == "__main__": main()
