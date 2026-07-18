"""Run hidden-field inventory and sentinel taint tests."""

from mavs10d.audit_v04.taint import audit_hidden_fields


if __name__ == "__main__":
    result = audit_hidden_fields()
    # Phase 10 step: report hidden-field taint status.
    print({"event": "phase10.taint.complete", **result})

