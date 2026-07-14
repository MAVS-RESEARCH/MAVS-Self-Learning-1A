"""Independent fail-closed Phase 8 audit from serialized raw artifacts only."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd

from mavs10d.core.hashing import file_sha256
from phase8_common import PHASE7_ROOT, REPO_ROOT, file_manifest, load_yaml, read_json, run_root, write_json


def metric_map(path: Path) -> dict[str, float]:
    frame = pd.read_parquet(path)
    return {str(row.metric): float(row.value) for row in frame.itertuples(index=False)}


def scan_console_registry() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    paths = sorted((REPO_ROOT / "scripts").glob("*phase8*.*"))
    for path in paths:
        if path.suffix not in {".py", ".mjs"}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8"))
            statement_lines = sorted(
                node.lineno for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"
            )
        else:
            statement_lines = [index + 1 for index, line in enumerate(lines) if "console.log(" in line and not line.strip().startswith("//")]
        for statement_line in statement_lines:
            index = statement_line - 1
            stripped = lines[index].strip()
            expected_prefix = "// console.log:" if path.suffix == ".mjs" else "# console.log:"
            comment = lines[index - 1].strip() if index else ""
            passed = comment.startswith(expected_prefix)
            record = {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "comment_line": index, "comment": comment,
                "statement_line": index + 1, "statement": stripped,
                "passed": passed,
            }
            records.append(record)
            if not passed:
                findings.append({"gate": "console_comment", "path": record["path"], "line": index + 1})
    return records, findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    phase = load_yaml("configs/phases/phase8.yaml")
    findings: list[dict[str, Any]] = []
    expected_ids = [*(f"I{index}" for index in range(12)), *(f"P{index}" for index in range(16)), *(f"L{index}" for index in range(11))]
    observed_ids = sorted((path.name for path in (root / "ablation_results").iterdir() if path.is_dir()), key=lambda value: expected_ids.index(value) if value in expected_ids else 10_000)
    if observed_ids != expected_ids:
        findings.append({"gate": "matrix_completeness", "observed": observed_ids})
    schemas = {
        name: read_json(REPO_ROOT / "schemas" / "v04" / f"{name}.schema.json")
        for name in ("ablation_result", "causal_contrast", "matched_budget")
    }
    required = {
        "full_config.json", "ablation_config.json", "config_diff.json", "shared_bank_manifest.json",
        "matched_budget.json", "seed_ledger.json", "metrics.parquet", "paired_deltas.parquet",
        "trace_index.json", "causal_contrast.json", "failures.parquet", "audit.json",
        "ablation_result.json", "confidence_intervals.json",
    }
    for condition_id in expected_ids:
        target = root / "ablation_results" / condition_id
        missing = sorted(item for item in required if not (target / item).exists())
        if missing:
            findings.append({"gate": "bundle_completeness", "condition_id": condition_id, "missing": missing})
            continue
        for name, filename in (("ablation_result", "ablation_result.json"), ("causal_contrast", "causal_contrast.json"), ("matched_budget", "matched_budget.json")):
            try:
                jsonschema.validate(read_json(target / filename), schemas[name])
            except jsonschema.ValidationError as error:
                findings.append({"gate": "schema", "condition_id": condition_id, "artifact": filename, "detail": error.message})
        diff = read_json(target / "config_diff.json")
        expected_diff = 0 if condition_id in {"I0", "P0", "L0"} else 1
        if int(diff["diff_count"]) != expected_diff or not diff["single_factor_valid"]:
            findings.append({"gate": "single_factor", "condition_id": condition_id})
        budget = read_json(target / "matched_budget.json")
        if not budget["matched"] or budget["mismatch_fields"] or any(float(budget["consumed"][key]) + float(budget["unused"][key]) != float(budget["declared"][key]) for key in budget["declared"]):
            findings.append({"gate": "matched_budget", "condition_id": condition_id})
        result = read_json(target / "ablation_result.json")
        if result["status"] in {"FAIL", "NULL", "THEORY_REVISION"} or not all(result["gate_results"].values()):
            findings.append({"gate": "condition_outcome", "condition_id": condition_id, "status": result["status"]})
        per_audit = read_json(target / "audit.json")
        if per_audit["status"] != "PASS" or int(per_audit["finding_count"]) != 0:
            findings.append({"gate": "condition_audit", "condition_id": condition_id})
        index = read_json(target / "trace_index.json")
        for trace in index["traces"]:
            path = root / trace["path"]
            if not path.exists() or file_sha256(path) != trace["sha256"] or len(pd.read_parquet(path)) != int(trace["rows"]):
                findings.append({"gate": "trace_index", "condition_id": condition_id, "path": trace["path"]})

    p0_frame = pd.read_parquet(root / "ablation_results" / "P0" / "auditor_case_outcomes.parquet")
    unsafe = p0_frame["truth_unsafe"].astype(bool)
    p0_recomputed = {
        "uar": float((unsafe & (p0_frame["terminal_action"] == "ACCEPT")).sum() / unsafe.sum()),
        "frr": float(((~unsafe) & (p0_frame["terminal_action"] == "REJECT")).sum() / (~unsafe).sum()),
        "residual_escalation": float(p0_frame["external_escalate"].mean()),
        "scope_leakage": float(p0_frame["scope_leakage"].sum()),
        "active_basis_max": float(p0_frame["active_basis"].max()),
    }
    p0_stored = metric_map(root / "ablation_results" / "P0" / "metrics.parquet")
    if any(abs(p0_recomputed[key] - p0_stored[key]) > 1e-12 for key in p0_recomputed):
        findings.append({"gate": "p0_metric_recomputation", "recomputed": p0_recomputed})
    if p0_recomputed["uar"] != 0 or p0_recomputed["frr"] != 0 or p0_recomputed["scope_leakage"] != 0 or p0_recomputed["active_basis_max"] > 2:
        findings.append({"gate": "p0_reference"})

    i0 = pd.read_parquet(root / "ablation_results" / "I0" / "candidate_traces.parquet")
    i1 = pd.read_parquet(root / "ablation_results" / "I1" / "candidate_traces.parquet")
    i2 = metric_map(root / "ablation_results" / "I2" / "metrics.parquet")
    i3 = metric_map(root / "ablation_results" / "I3" / "metrics.parquet")
    i0_metrics = metric_map(root / "ablation_results" / "I0" / "metrics.parquet")
    if i0["template_signature"].nunique() < 5 or int(i0["integrity_eligible"].sum()) != 20 or int(i1["certification_eligible"].sum()) != 0:
        findings.append({"gate": "synthesis_reference_or_i1"})
    if i2["certification_pressure"] <= i0_metrics["certification_pressure"] or i3["behavioral_equivalent_count"] <= i0_metrics["behavioral_equivalent_count"]:
        findings.append({"gate": "dedup_pressure"})
    for condition_id in ("I6", "I7"):
        metrics = metric_map(root / "ablation_results" / condition_id / "metrics.parquet")
        if metrics["firewall_detected"] != 1 or metrics["taint_count"] <= 0 or metrics["shared_uar"] != 0 or metrics["shared_frr"] != 0:
            findings.append({"gate": "firewall_attack", "condition_id": condition_id})

    l0 = metric_map(root / "ablation_results" / "L0" / "metrics.parquet")
    l3 = metric_map(root / "ablation_results" / "L3" / "metrics.parquet")
    if l0["uar"] != 0 or l0["frr"] != 0 or l0["scope_leakage"] != 0 or l0["active_basis_max"] > 2:
        findings.append({"gate": "l0_reference"})
    if l3["library_size"] <= l0["library_size"] or l3["scope_leakage"] <= l0["scope_leakage"]:
        findings.append({"gate": "consolidation_pathology"})

    phase4_p0 = metric_map(root / "ablation_results" / "P0" / "metrics.parquet")
    if phase4_p0["phase4_case_count"] != 25000 or phase4_p0["phase4_world_count"] != 500 or phase4_p0["phase4_residual_escalation"] >= phase4_p0["phase4_original_escalation"]:
        findings.append({"gate": "phase4_pre_rerun"})
    public = pd.read_parquet(root / "banks" / "phase4_pre_rerun_public.parquet")
    if "unsafe" in public.columns or len(public) != 25000:
        findings.append({"gate": "phase4_public_firewall"})

    isolation = read_json(root / "integrity" / "isolation_report.json")
    permutation = read_json(root / "integrity" / "permutation_report.json")
    hidden = read_json(root / "integrity" / "hidden_field_report.json")
    replay = read_json(root / "integrity" / "replay_report.json")
    phase_gates = read_json(root / "reports" / "phase8_gate_summary.json")
    if any(item["status"] != "PASS" or int(item.get("finding_count", 0)) != 0 for item in [isolation]):
        findings.append({"gate": "isolation_report"})
    if not permutation["passed"] or not hidden["passed"] or not replay["passed"] or not phase_gates["passed"]:
        findings.append({"gate": "phase_level_integrity"})
    theory = pd.read_parquet(root / "reports" / "theory_revision_ledger.parquet")
    if len(theory):
        findings.append({"gate": "unresolved_theory_revision", "count": len(theory)})

    phase7_audit_path = PHASE7_ROOT / "reports" / "phase7_audit.json"
    if file_sha256(phase7_audit_path).upper() != phase["phase7_dependency"]["audit_sha256"]:
        findings.append({"gate": "phase7_dependency_changed"})
    legacy = read_json(REPO_ROOT / "results" / "legacy" / "phase4_original" / "legacy_manifest.json")
    phase4_source = REPO_ROOT / phase["locked_banks"]["phase4_trace"]
    indexed = {item["path"]: item["sha256"] for item in legacy["files"]}
    if indexed.get(phase4_source.relative_to(REPO_ROOT).as_posix()) != file_sha256(phase4_source):
        findings.append({"gate": "legacy_phase4_changed"})
    if (REPO_ROOT / "results" / "perception_closure_v04" / "phase9").exists():
        findings.append({"gate": "phase9_started"})

    console_records, console_findings = scan_console_registry()
    findings.extend(console_findings)
    write_json(root / "reports" / "console_log_registry.json", {"schema_version": "1.0.0", "statement_count": len(console_records), "records": console_records, "passed": not console_findings})
    clauses = {
        "39_condition_matrix": len(observed_ids) == 39,
        "single_factor_serialized_configs": not any(item.get("gate") == "single_factor" for item in findings),
        "complete_per_id_bundles": not any(item.get("gate") == "bundle_completeness" for item in findings),
        "shared_locked_phase7_bank": len(p0_frame) == 384,
        "sealed_500_world_pre_rerun_bank": len(public) == 25000 and public["world_id"].nunique() == 500,
        "matched_budgets": not any(item.get("gate") == "matched_budget" for item in findings),
        "synthesis_integrity_ablations": len([item for item in observed_ids if item.startswith("I")]) == 12,
        "runtime_ablations": len([item for item in observed_ids if item.startswith("P")]) == 16,
        "persistence_ablations": len([item for item in observed_ids if item.startswith("L")]) == 11,
        "i1_rejected": int(i1["certification_eligible"].sum()) == 0,
        "dedup_pressure_measurable": i2["certification_pressure"] > i0_metrics["certification_pressure"] and i3["behavioral_equivalent_count"] > i0_metrics["behavioral_equivalent_count"],
        "metadata_attacks_quarantined": not any(item.get("gate") == "firewall_attack" for item in findings),
        "p0_outresolves_p1": p0_stored["local_resolution"] > metric_map(root / "ablation_results" / "P1" / "metrics.parquet")["local_resolution"],
        "scope_sparse_additive_consolidation_pathologies": phase_gates["gates"]["scope_sparse_additive_consolidation_pathologies"],
        "label_name_operation_order_invariance": permutation["passed"],
        "negative_null_inventory_retained": len(pd.read_parquet(root / "reports" / "negative_null_result_inventory.parquet")) == 39,
        "theory_revision_ledger_resolved": len(theory) == 0,
        "deterministic_replay": replay["passed"],
        "prior_results_preserved": not any(item.get("gate") in {"phase7_dependency_changed", "legacy_phase4_changed"} for item in findings),
        "phase9_not_started": not (REPO_ROOT / "results" / "perception_closure_v04" / "phase9").exists(),
        "claims_phase_limited": "not Phase 9" in (root / "reports" / "CLAIMS.md").read_text(encoding="utf-8") and "excluded from competitive claims" in (root / "reports" / "CLAIMS.md").read_text(encoding="utf-8"),
    }
    for clause, passed in clauses.items():
        if not passed:
            findings.append({"gate": "workplan_clause", "clause": clause})

    excluded = {"reports/phase8_audit.json", "reports/artifact_manifest.json"}
    manifest = file_manifest(root, excluded)
    write_json(root / "reports" / "artifact_manifest.json", {"schema_version": "1.0.0", "file_count": len(manifest), "files": manifest})
    source_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip()
    audit = {
        "schema_version": "1.0.0", "run_id": args.run_id, "source_commit": source_commit,
        "auditor_independence": "raw artifacts recomputed without importing Phase 8 execution adapters or aggregate gate function",
        "condition_count": len(observed_ids), "workplan_clause_count": len(clauses), "workplan_clauses": clauses,
        "recomputed_p0": p0_recomputed, "artifact_count": len(manifest),
        "findings": findings, "finding_count": len(findings), "status": "PASS" if not findings else "FAIL",
    }
    write_json(root / "reports" / "phase8_audit.json", audit)
    if findings:
        raise RuntimeError(f"Independent Phase 8 audit failed with {len(findings)} findings.")
    # console.log: phase8.audit.complete
    print(f'{{"event":"phase8.audit.complete","conditions":{len(observed_ids)},"clauses":{len(clauses)},"findings":0}}')


if __name__ == "__main__":
    main()
