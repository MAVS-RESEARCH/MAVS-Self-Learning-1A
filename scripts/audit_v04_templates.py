"""Validate the complete proposal population template audit."""

from mavs10d.audit_v04.candidate_audit import audit_candidates


if __name__ == "__main__":
    result = audit_candidates()
    # Phase 10 step: report full template audit status.
    print({"event": "phase10.templates.complete", "candidate_count": result["candidate_count"], "status": result["status"]})

