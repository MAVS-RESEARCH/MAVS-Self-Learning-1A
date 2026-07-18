"""Run candidate inventory and stratified lineage audit."""

from mavs10d.audit_v04.candidate_audit import audit_candidates


if __name__ == "__main__":
    result = audit_candidates()
    # Phase 10 step: report candidate reconciliation audit.
    print({"event": "phase10.candidates.complete", **result})

