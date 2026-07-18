"""Verify the frozen Version 0.4 release without writing evidence."""

from mavs10d.audit_v04.release_verify import verify_release


if __name__ == "__main__":
    result = verify_release()
    # Phase 10 step: report read-only frozen release verification.
    print({"event": "phase10.release.verify", **result})
    if result["status"] != "PASS":
        raise SystemExit(1)

