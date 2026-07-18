"""Audit legacy/current and paired/blind result isolation."""

from mavs10d.audit_v04.isolation import audit_isolation


if __name__ == "__main__":
    result = audit_isolation()
    # Phase 10 step: report results-isolation audit.
    print({"event": "phase10.isolation.complete", **result})

