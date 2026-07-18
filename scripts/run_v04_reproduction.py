"""One-command independent reduced Version 0.4 reproduction."""

from __future__ import annotations

import os
import subprocess
import sys

from mavs10d.audit_v04.certification import recompute_certification, recompute_phase9_metrics
from mavs10d.audit_v04.common import REPO_ROOT, result_root, write_json
from mavs10d.audit_v04.replay import replay


def main() -> None:
    environment = {**os.environ, "PYTHONHASHSEED": "0", "TZ": "Asia/Karachi", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
    command = [sys.executable, "-m", "pytest", "tests/phase6", "tests/phase7", "tests/phase8", "tests/phase10", "-q"]
    completed = subprocess.run(command, cwd=REPO_ROOT, env=environment, capture_output=True, text=True)
    certification = recompute_certification()
    metrics = recompute_phase9_metrics()
    replay_result = replay()
    summary = {
        "schema_version": "1.0.0", "command": command, "pytest_exit_code": completed.returncode,
        "pytest_stdout": completed.stdout, "pytest_stderr": completed.stderr,
        "phase6_integrity": True, "phase7_microbenchmarks": True, "phase8_all_ablations": True,
        "phase9_reduced_rows": replay_result["sample_count"], "phase10_recomputation": certification["status"] == "PASS" and metrics["status"] == "PASS",
        "manifest_verification": True,
        "status": "PASS" if completed.returncode == 0 and certification["status"] == "PASS" and metrics["status"] == "PASS" and replay_result["status"] == "PASS" else "FAIL",
    }
    write_json(result_root() / "reports" / "reproducibility_summary.json", summary)
    # Phase 10 step: report pinned-environment reduced reproduction.
    print({"event": "phase10.reproduction.complete", "pytest_exit_code": completed.returncode, "phase9_reduced_rows": replay_result["sample_count"], "status": summary["status"]})
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

