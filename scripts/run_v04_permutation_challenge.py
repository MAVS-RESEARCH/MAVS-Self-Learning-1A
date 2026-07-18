"""Run name, label, generation, and order permutation challenges."""

from mavs10d.audit_v04.permutation import run_permutation_challenge


if __name__ == "__main__":
    result = run_permutation_challenge()
    # Phase 10 step: report permutation invariance result.
    print({"event": "phase10.permutation.complete", **{key: result[key] for key in ("candidate_count", "changed_gate_count", "changed_metric_outcome_count", "changed_gate_or_decision_count", "status")}})
