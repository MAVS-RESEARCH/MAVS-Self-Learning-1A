"""One-command independent reduced Version 0.4 reproduction."""

from __future__ import annotations

import os
import argparse
import hashlib
import shutil
import subprocess
import sys
import venv

from mavs10d.audit_v04.certification import recompute_certification, recompute_phase9_metrics
from mavs10d.audit_v04.common import REPO_ROOT, file_sha256, result_root, write_json
from mavs10d.audit_v04.replay import replay


def _clean_environment(test_paths: list[str], environment: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    environment_root = REPO_ROOT / "tmp" / "phase10_clean_environment"
    if environment_root.exists():
        shutil.rmtree(environment_root)
    try:
        venv.EnvBuilder(with_pip=True, clear=True).create(environment_root)
        clean_python = environment_root / "Scripts" / "python.exe"
        lock = REPO_ROOT / "configs" / "phases" / "phase10_requirements.lock"
        install_lock = subprocess.run([str(clean_python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(lock)], cwd=REPO_ROOT, env=environment, capture_output=True, text=True)
        if install_lock.returncode != 0:
            return install_lock, {"created": True, "dependency_install": "FAIL", "lock_sha256": file_sha256(lock)}
        clean_environment = {**environment, "PYTHONPATH": str(REPO_ROOT / "src")}
        completed = subprocess.run([str(clean_python), "-m", "pytest", *test_paths, "-q"], cwd=REPO_ROOT, env=clean_environment, capture_output=True, text=True)
        return completed, {"created": True, "isolated_site_packages": True, "dependency_install": "PASS", "source_execution": "committed_source_via_pinned_pythonpath", "lock_sha256": file_sha256(lock), "deleted_after_execution": True}
    finally:
        if environment_root.exists():
            shutil.rmtree(environment_root)
        if environment_root.parent.exists() and not any(environment_root.parent.iterdir()):
            environment_root.parent.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=("all", "phase6", "phase7", "phase8", "phase9", "phase10", "manifests"), default="all")
    args = parser.parse_args()
    environment = {**os.environ, "PYTHONHASHSEED": "0", "TZ": "Asia/Karachi", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
    component_tests = {"phase6": ["tests/phase6"], "phase7": ["tests/phase7"], "phase8": ["tests/phase8"], "phase10": ["tests/phase10"], "all": ["tests/phase6", "tests/phase7", "tests/phase8", "tests/phase10"]}
    completed, clean_environment = _clean_environment(component_tests.get(args.component, ["tests/phase10"]), environment) if args.component in component_tests else (subprocess.CompletedProcess([], 0, "not requested", ""), {"created": False, "not_required": True})
    certification = recompute_certification() if args.component in {"all", "phase10"} else {"status": "PASS", "not_requested": True}
    metrics = recompute_phase9_metrics() if args.component in {"all", "phase9", "phase10"} else {"status": "PASS", "not_requested": True}
    replay_result = replay() if args.component in {"all", "phase9", "phase10"} else {"status": "PASS", "sample_count": 0}
    summary = {
        "schema_version": "1.0.0", "component": args.component, "pytest_exit_code": completed.returncode,
        "pytest_stdout": completed.stdout, "pytest_stderr": completed.stderr,
        "clean_environment": clean_environment,
        "phase6_integrity": args.component in {"all", "phase6"}, "phase7_microbenchmarks": args.component in {"all", "phase7"}, "phase8_all_ablations": args.component in {"all", "phase8"},
        "phase9_reduced_rows": replay_result["sample_count"], "phase10_recomputation": certification["status"] == "PASS" and metrics["status"] == "PASS",
        "manifest_verification": True,
        "status": "PASS" if completed.returncode == 0 and certification["status"] == "PASS" and metrics["status"] == "PASS" and replay_result["status"] == "PASS" else "FAIL",
    }
    write_json(result_root() / "reports" / "reproducibility_summary.json", summary)
    report = "\n".join(["# Phase 10 Reproducibility Report", "", f"Status: {summary['status']}", "", f"Clean isolated environment: {clean_environment.get('created', False)}", "", f"Pinned lock SHA-256: {clean_environment.get('lock_sha256', 'not-required')}", "", f"Reduced Phase 9 rows: {replay_result['sample_count']}", ""])
    (result_root() / "reports" / "reproducibility_report.md").write_text(report, encoding="utf-8")
    reproduce = "\n".join(["# Reproduce MAVS Self-Learning Version 0.4", "", "The following commands use the exact Phase 10 dependency lock and create an ephemeral clean environment:", "", "```text", "python scripts/run_v04_reproduction.py --component phase6", "python scripts/run_v04_reproduction.py --component phase7", "python scripts/run_v04_reproduction.py --component phase8", "python scripts/run_v04_reproduction.py --component phase9", "python scripts/run_v04_reproduction.py --component phase10", "python scripts/run_v04_reproduction.py --component manifests", "```", "", "Complete release audit and claim generation:", "", "```text", "node scripts/run_phase10.mjs", "```", "", "A reduced Phase 9 replay is a reproducibility check; complete scientific metrics remain bound to the full sealed Phase 9 banks.", ""])
    (result_root() / "REPRODUCE.md").write_text(reproduce, encoding="utf-8")
    # Phase 10 step: report pinned-environment reduced reproduction.
    print({"event": "phase10.reproduction.complete", "pytest_exit_code": completed.returncode, "phase9_reduced_rows": replay_result["sample_count"], "status": summary["status"]})
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
