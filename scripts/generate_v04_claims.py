"""Generate fail-closed claims from completed audit gates."""

from mavs10d.audit_v04.claims import evaluate_cumulative_value, generate_claims
from mavs10d.audit_v04.common import REPO_ROOT, config, read_json, result_root, write_json


def main() -> None:
    root = result_root()
    candidates = read_json(root / "candidate_audit" / "candidate_audit_summary.json")
    certification = read_json(root / "reports" / "certification_summary.json")
    metrics = read_json(root / "reports" / "metric_recomputation_summary.json")
    permutation = read_json(root / "permutation" / "outcome_comparison.json")
    process = read_json(root / "taint" / "process_access_audit.json")
    memory = read_json(root / "taint" / "memory_scan.json")
    replay = read_json(root / "replay" / "artifact_comparison.json")
    trace = read_json(root / "trace" / "completeness.json")
    isolation = read_json(root / "isolation" / "results_isolation_audit.json")
    cumulative = evaluate_cumulative_value()
    write_json(root / "reports" / "cumulative_value_audit.json", cumulative)
    gates = {
        "input_integrity": True, "candidate_reconciliation": candidates["reconciliation_passed"],
        "template_integrity": candidates["all_semantic_behavioral_hashes_match"],
        "certification_match": certification["mismatch_count"] == 0,
        "metric_recomputation": metrics["mismatch_count"] == 0,
        "permutation_invariance": permutation["changed_gate_or_decision_count"] == 0,
        "hidden_taint_zero": process["status"] == "PASS" and memory["status"] == "PASS",
        "replay_match": replay["mismatch_count"] == 0, "trace_completeness": trace["status"] == "PASS",
        "result_isolation": isolation["status"] == "PASS",
        "phase9_blind_gate": read_json(REPO_ROOT / config()["inputs"]["phase9"] / "phase9_audit.json")["status"] == "PASS",
        "cumulative_value": cumulative["status"] == "PASS", "finite_covered_class_only": False, "external_operational_validation": False,
    }
    write_json(root / "reports" / "preclaim_gate_audit.json", {"schema_version": "1.0.0", "gates": gates, "fail_closed": True})
    result = generate_claims()
    # Phase 10 step: report mechanically generated claim statuses.
    print({"event": "phase10.claims.complete", **result})


if __name__ == "__main__":
    main()
