"""Independently recompute candidate gates and Phase 9 metrics."""

from mavs10d.audit_v04.certification import recompute_certification, recompute_phase9_metrics
from mavs10d.audit_v04.common import result_root, write_json


if __name__ == "__main__":
    certification = recompute_certification()
    metrics = recompute_phase9_metrics()
    write_json(result_root() / "reports" / "certification_summary.json", certification)
    write_json(result_root() / "reports" / "metric_recomputation_summary.json", metrics)
    # Phase 10 step: report independent gate and metric recomputation.
    print({"event": "phase10.certification.complete", "certification": certification, "metrics": metrics})

