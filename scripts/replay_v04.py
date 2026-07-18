"""Replay pinned samples and every protected failure."""

from mavs10d.audit_v04.replay import replay


if __name__ == "__main__":
    result = replay()
    # Phase 10 step: report exact replay comparison.
    print({"event": "phase10.replay.complete", **{key: result[key] for key in ("sample_count", "protected_failure_count", "comparison_count", "mismatch_count", "status")}})

