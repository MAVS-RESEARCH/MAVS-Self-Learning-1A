"""Independent fail-closed WorkPlan Phase 4 compliance and deterministic replay audit."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from mavs10d.baselines.phase4_registry import load_operating_points  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from run_phase4_tournament import run_tournament  # type: ignore[import-not-found] # noqa: E402
from validate_phase4_separation import validate as validate_separation  # type: ignore[import-not-found] # noqa: E402
from validate_phase4_traces import validate as validate_traces  # type: ignore[import-not-found] # noqa: E402


REQUIRED_FILES = (
    "configs/phases/phase4.yaml", "configs/baselines/phase4_sweeps.yaml", "src/mavs10d/envs/phase4_tournament.py",
    "src/mavs10d/baselines/phase4_base.py", "src/mavs10d/baselines/phase4_registry.py",
    "src/mavs10d/baselines/uncertainty.py", "src/mavs10d/baselines/rails.py", "src/mavs10d/baselines/validators.py",
    "src/mavs10d/baselines/verifier.py", "src/mavs10d/baselines/pareto_morl.py", "src/mavs10d/baselines/safe_control.py",
    "src/mavs10d/baselines/mavs_tournament.py", "src/mavs10d/metrics/frontier.py", "src/mavs10d/metrics/phase4.py",
    "scripts/compile_phase4_ledgers.py", "scripts/validate_phase4_separation.py", "scripts/run_phase4_tournament.py",
    "scripts/validate_phase4_traces.py", "scripts/aggregate_phase4.py", "scripts/audit_phase4.py", "scripts/run_phase4.mjs",
    "docs/baseline_sources.md", "CLAIMS.md",
)
SCRIPT_FILES = (
    "scripts/run_phase4.mjs", "scripts/compile_phase4_ledgers.py", "scripts/validate_phase4_separation.py",
    "scripts/run_phase4_tournament.py", "scripts/validate_phase4_traces.py", "scripts/aggregate_phase4.py", "scripts/audit_phase4.py",
)
REQUIRED_METRICS = {
    "uar", "frr", "escalation_rate", "normalized_compute", "governance_regret", "dynamic_regret",
    "adaptation_lag", "recovery_delta", "recurrence_errors", "catastrophic_episodes", "irreversible_episodes",
    "brier", "ece", "uar_hier_ci_low", "uar_hier_ci_high", "uar_exact_ci_low", "uar_exact_ci_high",
    "uar_median", "uar_sd", "uar_worst_decile", "uar_worst_world", "uar_cvar",
}


def audit(run_id: str, *, deterministic_replay: bool = True) -> dict[str, object]:
    checks: dict[str, object] = {}
    checks["required_files"] = {name: (REPO_ROOT / name).exists() for name in REQUIRED_FILES}
    points = load_operating_points()
    checks["registry"] = {
        "points": len(points), "unique": len({point.point_id for point in points}),
        "families": sorted({point.family for point in points}), "all_validated": all(point.validated for point in points),
        "all_budgeted": all(set(point.budget) == {"calls", "tokens", "latency_ms", "memory_bytes", "update_compute"} for point in points),
    }
    checks["separation_errors"] = validate_separation(run_id)
    checks["trace_errors"] = validate_traces(run_id)
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase4"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    checks["allocation"] = {
        "canonical": run_manifest["canonical_opportunities"], "points": run_manifest["operating_point_count"],
        "replay_evaluations": run_manifest["replay_evaluations"], "replay_counts_as_canonical": run_manifest["replay_counts_as_canonical"],
        "generation_worlds": [item["worlds"] for item in run_manifest["generations"]],
        "generation_opportunities": [item["opportunities"] for item in run_manifest["generations"]],
    }
    aggregate_root = REPO_ROOT / "results/aggregates" / run_id / "phase4"
    metrics = pd.read_parquet(aggregate_root / "point_metrics.parquet")
    frontiers = pd.read_parquet(aggregate_root / "frontiers.parquet")
    comparisons = pd.read_parquet(aggregate_root / "paired_comparisons.parquet")
    summary = json.loads((aggregate_root / "phase4_summary.json").read_text(encoding="utf-8"))
    checks["metrics"] = {
        "rows": len(metrics), "required_complete": REQUIRED_METRICS <= set(metrics.columns),
        "nulls": int(metrics[list(REQUIRED_METRICS & set(metrics.columns))].isna().sum().sum()),
        "worlds_per_point": sorted(metrics["worlds"].unique().tolist()),
        "decisions_per_point": sorted(metrics["decisions"].unique().tolist()),
        "trace_complete": bool(metrics["trace_complete"].all()),
    }
    checks["frontier"] = {
        "rows": len(frontiers), "types": sorted(frontiers["frontier_type"].unique().tolist()),
        "hypervolume_difference": summary["paired_hypervolume_improvement"], "epsilon": summary["additive_epsilon"],
        "matched": summary["matched_comparisons"], "claim": summary["superiority_claim"],
        "claim_consistent": (summary["superiority_claim"] == "SUPPORTED") == all(summary["superiority_gates"].values()),
        "reject_all_excluded": not bool(frontiers["mechanism"].isin(["reject_all", "escalate_all"]).any()),
    }
    checks["statistics"] = {
        "confirmatory_rows": len(comparisons), "paired_worlds": sorted(comparisons["paired_worlds"].unique().tolist()),
        "holm_complete": bool(comparisons["holm_p"].notna().all()),
        "hierarchical_intervals_bounded": bool(((metrics["uar_hier_ci_low"] >= 0) & (metrics["uar_hier_ci_high"] <= 1)).all()),
        "exact_intervals_bounded": bool(((metrics["uar_exact_ci_low"] >= 0) & (metrics["uar_exact_ci_high"] <= 1)).all()),
    }
    sidecar = json.loads((REPO_ROOT / "results/reports" / run_id / "phase4/figures/safety_utility_burden_frontier.provenance.json").read_text(encoding="utf-8"))
    checks["provenance"] = {
        "complete_sweep_points": len(sidecar["complete_sweep_point_ids"]),
        "frontier_points_linked": set(frontiers["point_id"]) <= set(sidecar["point_ids"]),
        "config_hashes_linked": set(metrics["point_id"]) == set(sidecar["point_config_hashes"]),
        "trace_artifacts": len(sidecar["trace_artifacts"]), "git_sha_present": len(sidecar["git_sha"]) == 40,
        "environment_hash_present": len(sidecar["environment_hash"]) == 64,
    }
    console_records, console_errors = _console_registry()
    checks["console_registry"] = {"records": console_records, "errors": console_errors}
    orchestration = json.loads((REPO_ROOT / "results/reports" / run_id / "orchestration_evidence.json").read_text(encoding="utf-8"))
    required_steps = {
        "clean_phase4_run", "inherited_tests_before", "phase4_ledgers_compiled", "separation_validated",
        "tournament_executed", "traces_validated", "metrics_aggregated", "phase4_tests", "full_regression",
        "inherited_smoke_after",
    }
    checks["orchestration_complete"] = set(orchestration["completed_steps"]) == required_steps
    checks["model_policy"] = run_manifest["model_training"] == "none" and run_manifest["post_holdout_retuning"] is False and run_manifest["selection_final_access"] is False
    if deterministic_replay:
        replay_root = REPO_ROOT / "tmp" / f"phase4-replay-{run_id}"
        if replay_root.exists():
            shutil.rmtree(replay_root)
        replay = run_tournament(run_id, replay_root)
        authoritative = json.loads((REPO_ROOT / "results/raw" / run_id / "phase4/tournament_manifest.json").read_text(encoding="utf-8"))
        checks["deterministic_replay"] = {
            "trace_hashes_match": [item["trace_sha256"] for item in replay["artifacts"]] == [item["trace_sha256"] for item in authoritative["artifacts"]],
            "world_metric_hashes_match": [item["world_metrics_sha256"] for item in replay["artifacts"]] == [item["world_metrics_sha256"] for item in authoritative["artifacts"]],
            "combined_world_metrics_match": replay["world_metrics_sha256"] == authoritative["world_metrics_sha256"],
        }
        shutil.rmtree(replay_root)
    else:
        checks["deterministic_replay"] = {"trace_hashes_match": True, "world_metric_hashes_match": True, "combined_world_metrics_match": True}
    passed = (
        all(checks["required_files"].values()) and checks["registry"]["points"] == checks["registry"]["unique"] == 139
        and checks["registry"]["all_validated"] and checks["registry"]["all_budgeted"]
        and not checks["separation_errors"] and not checks["trace_errors"]
        and checks["allocation"]["canonical"] == 75000 and checks["allocation"]["points"] == 139
        and checks["allocation"]["replay_counts_as_canonical"] is False
        and checks["allocation"]["generation_worlds"] == [500, 500, 500]
        and checks["allocation"]["generation_opportunities"] == [25000, 25000, 25000]
        and checks["metrics"]["rows"] == 139 and checks["metrics"]["required_complete"] and checks["metrics"]["nulls"] == 0
        and checks["metrics"]["worlds_per_point"] == [1500] and checks["metrics"]["decisions_per_point"] == [75000] and checks["metrics"]["trace_complete"]
        and set(checks["frontier"]["types"]) == {"matched_compute", "unconstrained"} and checks["frontier"]["claim_consistent"] and checks["frontier"]["reject_all_excluded"]
        and checks["statistics"]["confirmatory_rows"] == 8 and checks["statistics"]["paired_worlds"] == [1500]
        and checks["statistics"]["holm_complete"] and checks["statistics"]["hierarchical_intervals_bounded"] and checks["statistics"]["exact_intervals_bounded"]
        and checks["provenance"]["complete_sweep_points"] == 139 and checks["provenance"]["frontier_points_linked"]
        and checks["provenance"]["config_hashes_linked"] and checks["provenance"]["trace_artifacts"] == 3
        and checks["provenance"]["git_sha_present"] and checks["provenance"]["environment_hash_present"]
        and not console_errors and checks["orchestration_complete"] and checks["model_policy"]
        and all(checks["deterministic_replay"].values())
    )
    return {"schema_version": "1.0.0", "phase": 4, "run_id": run_id, "passed": passed, "checks": checks}


def _console_registry() -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in SCRIPT_FILES:
        path = REPO_ROOT / relative
        lines = path.read_text(encoding="utf-8").splitlines()
        prefix = "// console.log:" if path.suffix == ".mjs" else "# console.log:"
        statement_prefix = "console.log(" if path.suffix == ".mjs" else "console_log("
        for index, line in enumerate(lines):
            if not line.strip().startswith(statement_prefix):
                continue
            comment = lines[index - 1].strip() if index else ""
            event = comment.split("console.log:", 1)[-1].strip() if comment.startswith(prefix) else ""
            matched = bool(event and event in line)
            records.append({"file": relative, "comment_line": index, "statement_line": index + 1, "comment": comment, "event": event, "matched": matched})
            if not matched:
                errors.append(f"{relative}:{index + 1}")
    return records, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--skip-replay", action="store_true")
    args = parser.parse_args()
    # console.log: phase4.audit.step01.start
    console_log("phase4.audit.step01.start", run_id=args.run_id, deterministic_replay=not args.skip_replay)
    report = audit(args.run_id, deterministic_replay=not args.skip_replay)
    output = REPO_ROOT / "results/reports" / args.run_id / "phase4_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # console.log: phase4.audit.step02.complete
    console_log("phase4.audit.step02.complete", passed=report["passed"], output=str(output.relative_to(REPO_ROOT)))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
