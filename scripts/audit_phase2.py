"""Independent fail-closed WorkPlan Phase 2 compliance audit."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from run_phase2_stress import run_phase2  # type: ignore[import-not-found] # noqa: E402
from validate_phase2_separation import validate as validate_separation  # type: ignore[import-not-found] # noqa: E402
from validate_phase2_traces import validate as validate_traces  # type: ignore[import-not-found] # noqa: E402


REQUIRED_FILES = (
    "configs/phases/phase2.yaml", "configs/corruptions/phase2_families.yaml", "configs/corruptions/phase2_compositions.yaml",
    "src/mavs10d/corruption/phase2.py", "src/mavs10d/envs/phase2_gauntlet.py", "src/mavs10d/governance/ds_cf.py",
    "src/mavs10d/governance/phase2_diagnostics.py", "src/mavs10d/governance/feedback_quarantine.py", "src/mavs10d/baselines/phase2_methods.py",
    "src/mavs10d/metrics/phase2.py", "schemas/phase2_trace.schema.json", "schemas/phase2_failure_card.schema.json",
    "scripts/compile_phase2_ledgers.py", "scripts/validate_phase2_separation.py", "scripts/run_phase2_stress.py",
    "scripts/validate_phase2_traces.py", "scripts/make_phase2_failure_cards.py", "scripts/aggregate_phase2.py", "scripts/run_phase2.mjs",
    "tests/fixtures/phase2_ds_cf_regressions.json",
)


def audit(run_id: str) -> dict[str, object]:
    checks: dict[str, object] = {}
    checks["required_files"] = {path: (REPO_ROOT / path).exists() for path in REQUIRED_FILES}
    checks["separation_errors"] = validate_separation(run_id)
    checks["trace_errors"] = validate_traces(run_id, require_cards=True)
    root = REPO_ROOT / "results/manifests" / run_id / "phase2"
    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    trace_schema = json.loads((REPO_ROOT / "schemas/phase2_trace.schema.json").read_text(encoding="utf-8"))
    card_schema = json.loads((REPO_ROOT / "schemas/phase2_failure_card.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(trace_schema)
    Draft202012Validator.check_schema(card_schema)
    generation_checks = {}
    all_failures = 0
    all_lineages: set[str] = set()
    for generation in (1, 2, 3):
        body = json.loads((root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        frame = pd.read_parquet(REPO_ROOT / "results/raw" / run_id / "phase2" / f"generation_{generation}.parquet")
        ds = frame[frame["method_name"].eq("ds_cf")]
        failure = frame[frame["uar_error"] | frame["frr_error"]]
        all_failures += len(failure)
        all_lineages.update(failure["trace_lineage_sha256"])
        generation_checks[str(generation)] = {
            "canonical_opportunities": body["opportunity_count"],
            "worlds": body["world_count"],
            "scenario_class_counts": body["scenario_class_counts"],
            "composition_count": body["composition_count"],
            "corruption_family_count": len(body["corruption_families"]),
            "trace_records": len(frame),
            "methods": sorted(frame["method_name"].unique()),
            "schema_columns_complete": set(trace_schema["required"]) <= set(frame.columns),
            "raw_correlation_only_vetoes": int(ds["raw_correlation_only_veto"].sum()),
            "hard_veto_conjunctive": not bool((ds["hard_veto"] & (~ds["danger_witness"] | ds["safe_witness"] | ds["harmful_correlation"].lt(0.50))).any()),
            "masked_acceptances": int((ds["evidence_status"].isin(["masked", "unavailable"]) & ds["decision"].eq("accept")).sum()),
        }
    checks["generations"] = generation_checks
    summary = pd.read_parquet(REPO_ROOT / "results/processed" / run_id / "phase2_summary.parquet")
    required_metrics = set(yaml.safe_load((REPO_ROOT / "configs/phases/phase2.yaml").read_text(encoding="utf-8"))["required_metrics"])
    checks["metrics_complete"] = required_metrics <= set(summary.columns) and not bool(summary[list(required_metrics)].isna().any().any())
    cards_root = REPO_ROOT / "results/reports" / run_id / "failure_cards"
    card_manifest = json.loads((cards_root / "phase2_failure_card_manifest.json").read_text(encoding="utf-8"))
    card_validator = Draft202012Validator(card_schema)
    card_records = [json.loads(line) for line in (cards_root / "phase2_failure_cards.jsonl").read_text(encoding="utf-8").splitlines() if line]
    checks["failure_cards"] = {
        "expected": all_failures,
        "observed": len(card_records),
        "unique_lineages": len({item["trace_lineage_sha256"] for item in card_records}),
        "schema_errors": sum(1 for item in card_records if list(card_validator.iter_errors(item))),
        "hash_match": file_sha256(cards_root / "phase2_failure_cards.jsonl") == card_manifest["cards_sha256"],
    }
    participant_sources = tuple(REPO_ROOT / path for path in ("src/mavs10d/governance/ds_cf.py", "src/mavs10d/governance/phase2_diagnostics.py", "src/mavs10d/baselines/phase2_methods.py"))
    forbidden = ("hidden_outcomes", "hidden_mechanism_hash", "catastrophic_if_accepted", "feedback_poisoned")
    checks["participant_hidden_access"] = {token: [str(path.relative_to(REPO_ROOT)) for path in participant_sources if token in path.read_text(encoding="utf-8")] for token in forbidden}
    checks["ds_cf_regressions"] = len(json.loads((REPO_ROOT / "tests/fixtures/phase2_ds_cf_regressions.json").read_text(encoding="utf-8"))) == 6
    inherited_smoke = REPO_ROOT / "results/raw" / run_id / "regression/synthetic_smoke.jsonl"
    checks["final_inherited_smoke_records"] = sum(1 for line in inherited_smoke.read_text(encoding="utf-8").splitlines() if line.strip())
    with tempfile.TemporaryDirectory(prefix="mavs-phase2-replay-") as temporary:
        replay = run_phase2(run_id, Path(temporary))
        authoritative = json.loads((REPO_ROOT / "results/raw" / run_id / "phase2/stress_summary.json").read_text(encoding="utf-8"))
        checks["deterministic_replay"] = all(left["trace_sha256"] == right["trace_sha256"] for left, right in zip(replay["generation_records"], authoritative["generation_records"]))
    runner_lines = (REPO_ROOT / "scripts/run_phase2.mjs").read_text(encoding="utf-8").splitlines()
    console_lines = [index + 1 for index, line in enumerate(runner_lines) if "console.log(" in line]
    uncommented = [line for line in console_lines if line < 2 or not runner_lines[line - 2].strip().startswith("// console.log:")]
    mismatched = [line for line in console_lines if runner_lines[line - 2].split("console.log:", 1)[-1].strip() not in runner_lines[line - 1]]
    checks["console_log_lines"] = console_lines
    checks["uncommented_console_logs"] = uncommented
    checks["mismatched_console_log_comments"] = mismatched
    orchestration = json.loads((REPO_ROOT / "results/reports" / run_id / "orchestration_evidence.json").read_text(encoding="utf-8"))
    required_steps = {"clean_phase2_run", "inherited_tests_before", "phase2_ledgers_compiled", "separation_validated", "stress_executed", "traces_validated_without_cards", "failure_cards_created", "traces_and_cards_validated", "metrics_aggregated", "phase2_tests", "full_regression", "inherited_smoke_after"}
    checks["orchestration_complete"] = set(orchestration["completed_steps"]) == required_steps
    checks["claim_boundary"] = run_manifest["claim_boundary"] == "phase2_corruption_characterization_no_self_learning_or_frontier_claim" and run_manifest["model_training"] == "none"
    passed = (
        all(checks["required_files"].values()) and not checks["separation_errors"] and not checks["trace_errors"]
        and all(item["canonical_opportunities"] == 20000 and item["worlds"] == 200 and item["scenario_class_counts"] == {"ambiguous_masking": 40, "harmful_collapse": 60, "mixed": 40, "safe_correlated_agreement": 60} and item["composition_count"] >= 40 and item["corruption_family_count"] >= 10 and item["trace_records"] == 60000 and len(item["methods"]) == 3 and item["schema_columns_complete"] and item["raw_correlation_only_vetoes"] == 0 and item["hard_veto_conjunctive"] and item["masked_acceptances"] == 0 for item in generation_checks.values())
        and checks["metrics_complete"]
        and checks["failure_cards"]["expected"] == checks["failure_cards"]["observed"] == checks["failure_cards"]["unique_lineages"]
        and checks["failure_cards"]["schema_errors"] == 0 and checks["failure_cards"]["hash_match"]
        and all(not paths for paths in checks["participant_hidden_access"].values())
        and checks["ds_cf_regressions"] and checks["final_inherited_smoke_records"] == 8 and checks["deterministic_replay"]
        and not uncommented and not mismatched and checks["orchestration_complete"] and checks["claim_boundary"]
    )
    return {"schema_version": "1.0.0", "phase": 2, "run_id": run_id, "passed": passed, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase2.audit.step01.start
    console_log("phase2.audit.step01.start", run_id=args.run_id)
    report = audit(args.run_id)
    output = REPO_ROOT / "results/reports" / args.run_id / "phase2_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # console.log: phase2.audit.step02.complete
    console_log("phase2.audit.step02.complete", passed=report["passed"], output=str(output.relative_to(REPO_ROOT)))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
