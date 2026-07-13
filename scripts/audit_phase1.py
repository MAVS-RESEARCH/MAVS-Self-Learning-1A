"""Independent, fail-closed audit of every Phase 1 WorkPlan requirement."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.baselines.phase1_registry import ADAPTIVE_METHODS, expected_method_conditions  # noqa: E402
from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.domain_adapters import DOMAIN_ADAPTERS  # noqa: E402
from run_phase1_stress import run_phase1  # type: ignore[import-not-found] # noqa: E402
from validate_phase1_separation import validate as validate_separation  # type: ignore[import-not-found] # noqa: E402
from validate_phase1_checkpoints import validate as validate_checkpoints  # type: ignore[import-not-found] # noqa: E402
from validate_phase1_traces import validate as validate_traces  # type: ignore[import-not-found] # noqa: E402


REQUIRED_FILES = (
    "configs/phases/phase1.yaml",
    "configs/worlds/phase1_development.yaml",
    "configs/worlds/phase1_evaluation.yaml",
    "configs/worlds/phase1_recovery.yaml",
    "configs/baselines/phase1_dynamic.yaml",
    "configs/training/phase1_ctta_source.yaml",
    "schemas/phase1_trace.schema.json",
    "src/mavs10d/envs/phase1_gauntlet.py",
    "src/mavs10d/envs/domain_adapters.py",
    "src/mavs10d/corruption/nonstationary.py",
    "src/mavs10d/baselines/selective.py",
    "src/mavs10d/baselines/neyman_pearson.py",
    "src/mavs10d/baselines/online_conformal.py",
    "src/mavs10d/baselines/drift.py",
    "src/mavs10d/baselines/online_experts.py",
    "src/mavs10d/baselines/test_time_adaptation.py",
    "src/mavs10d/baselines/context_fixed.py",
    "src/mavs10d/metrics/phase1.py",
    "src/mavs10d/training/phase1_proxy.py",
    "scripts/compile_phase1_ledgers.py",
    "scripts/validate_phase1_separation.py",
    "scripts/validate_phase1_traces.py",
    "scripts/run_phase1_stress.py",
    "scripts/aggregate_phase1.py",
    "scripts/run_phase1.mjs",
    "artifacts/models/phase1_ctta/phase1_ctta_source.npz",
    "artifacts/models/phase1_ctta/training_manifest.json",
    "docs/model_cards/phase1_ctta_source.md",
    "docs/baseline_sources.md",
)


def audit(run_id: str) -> dict[str, object]:
    checks: dict[str, object] = {}
    checks["required_files"] = {path: (REPO_ROOT / path).exists() for path in REQUIRED_FILES}
    checks["separation_errors"] = validate_separation(run_id)
    checks["trace_errors"] = validate_traces(run_id)
    checks["checkpoint_errors"] = validate_checkpoints(run_id)
    root = REPO_ROOT / "results/manifests" / run_id / "phase1"
    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    generation_checks = {}
    schema = json.loads((REPO_ROOT / "schemas/phase1_trace.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    expected_columns = set(schema["required"])
    for generation in (1, 2, 3):
        manifest = json.loads((root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        frame = pd.read_parquet(REPO_ROOT / "results/raw" / run_id / "phase1" / f"generation_{generation}.parquet")
        domain_counts = frame[["domain", "world_id"]].drop_duplicates().groupby("domain").size().to_dict()
        shift_counts = frame[["shift_class", "world_id"]].drop_duplicates().groupby("shift_class").size().to_dict()
        method_matrix = set(zip(frame["method_name"], frame["condition"]))
        generation_checks[str(generation)] = {
            "canonical_opportunities": manifest["opportunity_count"],
            "worlds": manifest["world_count"],
            "domain_counts": domain_counts,
            "shift_counts": shift_counts,
            "schedule_families": sorted(frame["schedule_family"].unique()),
            "trace_records": len(frame),
            "method_matrix_exact": method_matrix == set(expected_method_conditions(generation)),
            "schema_columns_complete": expected_columns <= set(frame.columns),
            "changing_cost_preferences": all(
                group["cost_preference"].nunique() == 3
                for _, group in pd.read_parquet(root / f"generation_{generation}/world_ledger.parquet").groupby("world_id")
            ),
        }
    checks["generations"] = generation_checks
    summary = pd.read_parquet(REPO_ROOT / "results/processed" / run_id / "phase1_summary.parquet")
    required_metrics = set(yaml.safe_load((REPO_ROOT / "configs/phases/phase1.yaml").read_text(encoding="utf-8"))["required_metrics"])
    checks["metrics_complete"] = required_metrics <= set(summary.columns) and not bool(summary[list(required_metrics)].isna().any().any())
    checks["domain_adapters_exact"] = set(DOMAIN_ADAPTERS) == {
        "text_safety", "tool_use", "cyber_triage", "medical_triage_proxy",
        "financial_approval_proxy", "multi_agent_operations", "synthetic_control", "retrieval_qa",
    }
    resource_fields = set(yaml.safe_load((REPO_ROOT / "configs/phases/phase1.yaml").read_text(encoding="utf-8"))["resource_accounting"])
    checks["resource_accounting_complete"] = resource_fields <= set(summary.columns) and not bool((summary[list(resource_fields)] < 0).any().any())
    later = summary[summary["generation"].isin([2, 3])]
    adaptive_conditions = later[later["method_name"].isin(ADAPTIVE_METHODS)].groupby(["generation", "method_name"])["condition"].apply(set)
    checks["adaptive_cumulative_fresh_complete"] = all(value == {"cumulative", "fresh"} for value in adaptive_conditions)
    blind = json.loads((REPO_ROOT / "results/reports" / run_id / "ctta_blind_evaluation.json").read_text(encoding="utf-8"))
    checks["ctta_blind_complete"] = (
        set(blind["training_domains"]).isdisjoint(blind["blind_domains"])
        and blind["post_blind_retuning"] is False
        and len(blind["metrics"]) == 10
    )
    baseline_sources = tuple(REPO_ROOT / path for path in (
        "src/mavs10d/baselines/selective.py", "src/mavs10d/baselines/neyman_pearson.py",
        "src/mavs10d/baselines/online_conformal.py", "src/mavs10d/baselines/drift.py",
        "src/mavs10d/baselines/online_experts.py", "src/mavs10d/baselines/test_time_adaptation.py",
        "src/mavs10d/baselines/context_fixed.py", "src/mavs10d/baselines/phase1_common.py",
    ))
    forbidden_source_tokens = ("hidden_outcomes", "latent_probability", "catastrophic_if_accepted")
    checks["baseline_hidden_access"] = {
        token: [str(path.relative_to(REPO_ROOT)) for path in baseline_sources if token in path.read_text(encoding="utf-8")]
        for token in forbidden_source_tokens
    }
    inherited_smoke = REPO_ROOT / "results/raw" / run_id / "regression/synthetic_smoke.jsonl"
    checks["final_inherited_smoke_records"] = sum(1 for line in inherited_smoke.read_text(encoding="utf-8").splitlines() if line.strip())
    with tempfile.TemporaryDirectory(prefix="mavs-phase1-replay-") as temporary:
        replay = run_phase1(run_id, Path(temporary))
        authoritative = json.loads((REPO_ROOT / "results/raw" / run_id / "phase1/stress_summary.json").read_text(encoding="utf-8"))
        checks["deterministic_replay"] = all(
            replay_item["trace_sha256"] == authority_item["trace_sha256"]
            for replay_item, authority_item in zip(replay["generation_records"], authoritative["generation_records"])
        )
    runner_lines = (REPO_ROOT / "scripts/run_phase1.mjs").read_text(encoding="utf-8").splitlines()
    console_lines = [index + 1 for index, line in enumerate(runner_lines) if "console.log(" in line]
    uncommented = [line for line in console_lines if line < 2 or not runner_lines[line - 2].strip().startswith("// console.log:")]
    mismatched = [line for line in console_lines if runner_lines[line - 2].split("console.log:", 1)[-1].strip() not in runner_lines[line - 1]]
    checks["console_log_lines"] = console_lines
    checks["uncommented_console_logs"] = uncommented
    checks["mismatched_console_log_comments"] = mismatched
    orchestration_path = REPO_ROOT / "results/reports" / run_id / "orchestration_evidence.json"
    orchestration = json.loads(orchestration_path.read_text(encoding="utf-8")) if orchestration_path.exists() else {}
    required_steps = {"clean_phase1_run", "inherited_tests_before", "ctta_checkpoint_verified", "phase1_ledgers_compiled", "separation_validated", "stress_executed", "traces_validated", "metrics_aggregated", "phase1_tests", "full_regression", "inherited_smoke_after"}
    checks["orchestration_complete"] = set(orchestration.get("completed_steps", [])) == required_steps
    checks["claim_boundary"] = run_manifest["claim_boundary"] == "dynamic_baseline_characterization_no_self_learning_superiority"
    passed = (
        all(checks["required_files"].values())
        and not checks["separation_errors"]
        and not checks["trace_errors"]
        and not checks["checkpoint_errors"]
        and all(
            value["canonical_opportunities"] == 15000
            and value["worlds"] == 150
            and set(value["domain_counts"].values()) == {30}
            and value["shift_counts"] == {"abrupt": 38, "gradual": 38, "mixed": 37, "recurring": 37}
            and len(value["schedule_families"]) == 7
            and value["method_matrix_exact"]
            and value["schema_columns_complete"]
            and value["changing_cost_preferences"]
            for value in generation_checks.values()
        )
        and checks["metrics_complete"]
        and checks["domain_adapters_exact"]
        and checks["resource_accounting_complete"]
        and checks["adaptive_cumulative_fresh_complete"]
        and checks["ctta_blind_complete"]
        and all(not paths for paths in checks["baseline_hidden_access"].values())
        and checks["final_inherited_smoke_records"] == 8
        and checks["deterministic_replay"]
        and not uncommented
        and not mismatched
        and checks["orchestration_complete"]
        and checks["claim_boundary"]
    )
    return {"schema_version": "1.0.0", "phase": 1, "run_id": run_id, "passed": passed, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase1.audit.step01.start
    console_log("phase1.audit.step01.start", run_id=args.run_id)
    report = audit(args.run_id)
    output = REPO_ROOT / "results/reports" / args.run_id / "phase1_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # console.log: phase1.audit.step02.complete
    console_log("phase1.audit.step02.complete", passed=report["passed"], output=str(output.relative_to(REPO_ROOT)))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
