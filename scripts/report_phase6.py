"""Generate complete Phase 6 integrity, inventory, rejection, and claim artifacts."""

from __future__ import annotations

import argparse
from collections import Counter

import pandas as pd

from mavs10d.certification.blind_api import assert_blind_payload
from mavs10d.certification.persistent import lifecycle_decision
from mavs10d.integrity.hidden_field_audit import audit_payloads
from mavs10d.integrity.permutation_tests import run_permutation_suite
from mavs10d.metrics.synthesis_integrity import lifecycle_metrics
from mavs10d.reports.synthesis_integrity import render_claims, render_report
from phase6_common import load_candidates, read_json, run_root, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    state = read_json(root / "manifests" / "replay_state.json")
    candidates = load_candidates(root)
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    inventory = []
    for record in state:
        lifecycle, reason = lifecycle_decision(record["integrity_passed"], record["certification_passed"], record["replay_passed"])
        candidate = candidate_by_id[record["candidate_id"]]
        vector = read_json(root / "candidates" / record["candidate_id"] / "independent_gate_vector.json")
        inventory.append({**record, "operation": candidate.lineage["operation"], "lifecycle": lifecycle, "lifecycle_reason": reason, "gate_pass_count": sum(gate["passed"] for gate in vector["gates"].values()), "gate_count": len(vector["gates"])})
    metrics = lifecycle_metrics(inventory)
    outcomes = {record["candidate_id"]: record["lifecycle"] for record in inventory}
    permutation = run_permutation_suite(candidates, outcomes, 650001)
    write_json(root / "integrity" / "name_label_operation_permutation.json", permutation)
    blind_payloads = {record["candidate_id"]: read_json(root / "candidates" / record["candidate_id"] / "blind_request.json") for record in inventory}
    taint = audit_payloads(blind_payloads, "PHASE6_EVALUATOR_ONLY_SENTINEL_7F3B2D")
    write_json(root / "integrity" / "hidden_field_taint_report.json", taint)
    schema_failures = []
    for candidate_id, request in blind_payloads.items():
        try:
            assert_blind_payload(request)
        except ValueError as error:
            schema_failures.append({"candidate_id": candidate_id, "error": str(error)})
    write_json(root / "integrity" / "blind_api_schema_audit.json", {"requests": len(blind_payloads), "forbidden_field_findings": schema_failures, "allowlist_only": True, "passed": not schema_failures})
    reason_counts = Counter(record.get("integrity_reason") or "none" for record in inventory)
    write_json(root / "integrity" / "constant_noop_parent_identity_report.json", {"reason_counts": reason_counts, "forbidden_promotions": [record["candidate_id"] for record in inventory if record["lifecycle"] == "promoted" and record.get("integrity_reason")], "passed": not any(record["lifecycle"] == "promoted" and record.get("integrity_reason") for record in inventory)})
    gate_patterns = Counter(tuple(record["failed_certification_gates"]) for record in inventory)
    write_json(root / "integrity" / "gate_distribution_investigation.json", {"patterns": [{"failed_gates": list(pattern), "count": count} for pattern, count in gate_patterns.items()], "all_pass_count": gate_patterns.get((), 0), "all_fail_count": sum(count for pattern, count in gate_patterns.items() if len(pattern) == 15), "nondegenerate": len(gate_patterns) > 1, "passed": len(gate_patterns) > 1})
    pd.DataFrame(inventory).to_parquet(root / "reports" / "candidate_inventory.parquet", index=False)
    pd.DataFrame([record for record in inventory if record["lifecycle"] != "promoted"]).to_parquet(root / "reports" / "rejections.parquet", index=False)
    write_json(root / "reports" / "lifecycle_metrics.json", metrics)
    preliminary = {"status": "PENDING_INDEPENDENT_AUDIT", "finding_count": "pending"}
    (root / "reports" / "synthesis_integrity.md").write_text(render_report(metrics, preliminary), encoding="utf-8")
    (root / "CLAIMS.md").write_text(render_claims(metrics, "PENDING_INDEPENDENT_AUDIT"), encoding="utf-8")
    write_json(root / "manifests" / "lifecycle_state.json", inventory)
    # console.log: phase6.report.complete
    print(f'{{"event":"phase6.report.complete","promoted":{metrics["promoted"]},"rejected":{metrics["integrity_rejected"] + metrics["certification_rejected"]}}}')


if __name__ == "__main__":
    main()
