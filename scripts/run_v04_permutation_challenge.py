"""Run name, label, generation, and order permutation challenges."""

from mavs10d.audit_v04.permutation import run_permutation_challenge


if __name__ == "__main__":
    result = run_permutation_challenge()
    # Phase 10 step: report permutation invariance result.
    print({"event": "phase10.permutation.complete", **result})

