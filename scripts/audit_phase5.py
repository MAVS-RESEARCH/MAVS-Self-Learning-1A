"""Independent fail-closed Phase 5 implementation and evidence audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.ablations.factorial import resolution_iv_design  # noqa: E402
from mavs10d.ablations.registry import AUTHORITATIVE_CONDITIONS, load_ablation_specs  # noqa: E402
from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.phase5_transfer import Phase5TransferCompiler  # noqa: E402


REQUIRED_TRANSFER = {
    "transfer_gain", "forward_transfer", "cold_start_reduction", "learning_acceleration_ttr",
    "learning_acceleration_ttd", "diagnostic_reuse_rate", "novel_diagnostic_yield",
    "negative_transfer_rate", "catastrophic_governance_interference", "retention_score",
    "library_efficiency", "generation_improvement_slope", "scope_leakage_delta", "forgetting",
    "update_stability",
}


def audit(run_id: str) -> dict[str, object]:
    checks: dict[str, bool] = {}
    findings: list[str] = []
    specs = load_ablation_specs()
    checks["authoritative_a0_a49"] = len(specs) == 50 and tuple(spec.exact_condition for spec in specs) == AUTHORITATIVE_CONDITIONS
    checks["single_explicit_diff"] = not specs[0].changes and all(len(spec.changes) == 1 for spec in specs[1:])
    checks["resolution_iv"] = len(resolution_iv_design()) == 16
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase5"
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase5"
    aggregate_root = REPO_ROOT / "results/aggregates" / run_id / "phase5"
    report_root = REPO_ROOT / "results/reports" / run_id / "phase5"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    tournament = json.loads((raw_root / "tournament_manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((aggregate_root / "phase5_summary.json").read_text(encoding="utf-8"))
    checks["canonical_budget"] = run_manifest["canonical_opportunities"] == 45000 and run_manifest["replays_count_as_canonical"] is False
    checks["complete_replay_matrix"] = tournament["trace_rows"] == 10740000 and tournament["complete_sweep"] is True and tournament["retention_replay_count"] == 200
    checks["no_training_or_retuning"] = tournament["model_training"] == "none" and tournament["post_holdout_retuning"] is False
    checks["independent_adversary"] = _config_attack_is_independent()
    checks["artifact_hashes"] = all(file_sha256(REPO_ROOT / artifact["trace"]) == artifact["trace_sha256"] for artifact in tournament["artifacts"])
    checks["deterministic_bank_recompile"] = _deterministic_bank_check(manifest_root)
    checks["trace_validator"] = not _script_validate("validate_phase5_traces.py", run_id)
    checks["separation_validator"] = not _script_validate("validate_phase5_separation.py", run_id)
    points = pd.read_parquet(aggregate_root / "point_metrics.parquet")
    transfer = pd.read_parquet(aggregate_root / "transfer_estimands.parquet")
    retention = pd.read_parquet(aggregate_root / "retention_evidence.parquet")
    causal = pd.read_parquet(aggregate_root / "causal_contributions.parquet")
    factorial = pd.read_parquet(aggregate_root / "factorial_effects.parquet")
    interactions = pd.read_parquet(aggregate_root / "targeted_interactions.parquet")
    system = pd.read_parquet(aggregate_root / "cross_generation_metrics.parquet")
    available = set(transfer) | set(points) | set(retention) | set(system)
    checks["all_required_metrics"] = REQUIRED_TRANSFER <= available
    checks["generation_slope_derivable"] = points[(points["ablation_id"] == "A0") & (points["condition"] == "cumulative")]["generation"].nunique() == 3
    checks["library_efficiency_derivable"] = {"retained_bytes", "objective"} <= set(points)
    checks["causal_and_interaction_outputs"] = len(causal) == 150 and len(factorial) > 0 and len(interactions) == 30
    checks["retention_every_later_update_stratum"] = len(retention) == 1200
    checks["all_negative_results_published"] = summary["all_negative_results_published"] and (report_root / "negative_results.csv").exists()
    checks["fail_closed_claims"] = summary["continual_governance_claim"] == ("SUPPORTED" if all(summary["claim_gates"].values()) else "NOT_SUPPORTED")
    checks["console_comments_and_calls"] = _console_registry_check()
    checks["reports_and_sidecars"] = (report_root / "phase5_report.md").exists() and (report_root / "CLAIMS.md").exists() and len(list((REPO_ROOT / "results/figures" / run_id / "phase5").glob("*.json"))) == 3
    for name, passed in checks.items():
        if not passed:
            findings.append(name)
    result: dict[str, object] = {
        "schema_version": "1.0.0", "phase": 5, "run_id": run_id,
        "checks": checks, "finding_count": len(findings), "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    result["audit_sha256"] = stable_hash(result)
    output = report_root / "phase5_audit.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (report_root / "phase5_audit.md").write_text(_markdown(result), encoding="utf-8")
    return result


def _script_validate(name: str, run_id: str) -> list[str]:
    path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        return ["validator_import"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(run_id)


def _deterministic_bank_check(manifest_root: Path) -> bool:
    compiler = Phase5TransferCompiler()
    for generation in (1, 2, 3):
        compiled = compiler.compile_generation(generation)
        body = json.loads((manifest_root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        if compiled.manifest["opportunity_ids_sha256"] != body["opportunity_ids_sha256"]:
            return False
        if compiled.manifest["hidden_outcomes_sha256"] != body["hidden_outcomes_sha256"]:
            return False
    return True


def _config_attack_is_independent() -> bool:
    import yaml
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase5.yaml").read_text(encoding="utf-8"))
    return config["attack"]["generator"] not in config["generator_implementations"]


def _console_registry_check() -> bool:
    paths = sorted((REPO_ROOT / "scripts").glob("*phase5*"))
    paths.append(REPO_ROOT / "scripts/run_phase5.mjs")
    for path in set(paths):
        if not path.exists() or path.suffix not in {".py", ".mjs"}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if re.search(r"\b(console_log|console\.log)\(", line) and not line.lstrip().startswith("def console_log"):
                prior = lines[index - 1].strip() if index else ""
                if not prior.startswith("# console.log:") and not prior.startswith("// console.log:"):
                    return False
    return True


def _markdown(result: dict[str, object]) -> str:
    lines = ["# Phase 5 independent compliance audit", "", f"Verdict: **{result['verdict']}**", ""]
    lines.extend(f"- `{name}`: {'PASS' if passed else 'FAIL'}" for name, passed in result["checks"].items())
    lines.extend(["", f"Open findings: {result['finding_count']}.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase5.audit.step01.start
    console_log("phase5.audit.step01.start", run_id=args.run_id)
    result = audit(args.run_id)
    # console.log: phase5.audit.step02.complete
    console_log("phase5.audit.step02.complete", verdict=result["verdict"], finding_count=result["finding_count"])
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
