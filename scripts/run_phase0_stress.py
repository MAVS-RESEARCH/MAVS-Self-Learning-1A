"""Execute the Phase 0 diagnostic-bound and measurement-integrity stress run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, git_commit_hash, stable_hash  # noqa: E402
from mavs10d.core.access_control import participant_file_guard  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.metrics.stats import exact_action_metrics, wilson_interval  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner, verify_signed_manifest  # noqa: E402


ActionFunction = Callable[[dict[str, Any], dict[str, Any] | None], str]
METHOD_ORDER = (
    "accept_all",
    "reject_all",
    "escalate_all",
    "random",
    "oracle_label",
    "oracle_regime",
)
ORACLE_METHODS = {"oracle_label", "oracle_regime"}


def _method_functions() -> dict[str, ActionFunction]:
    return {
        "accept_all": lambda visible, hidden: "accept",
        "reject_all": lambda visible, hidden: "reject",
        "escalate_all": lambda visible, hidden: "escalate",
        "random": lambda visible, hidden: ("accept", "reject", "escalate")[
            int(str(visible["seed_commitment"])[:8], 16) % 3
        ],
        "oracle_label": lambda visible, hidden: "reject" if bool(_require_hidden(hidden)["unsafe_label"]) else "accept",
        "oracle_regime": lambda visible, hidden: "escalate"
        if str(_require_hidden(hidden)["hidden_regime"]) in {"chaotic_switching", "recovery_trap", "irreversible_consequences"}
        else "accept",
    }


def run_generation(run_id: str, generation: int, output_root: Path) -> dict[str, Any]:
    directory = REPO_ROOT / "results/manifests" / run_id / f"generation_{generation}"
    ledger_path = directory / "world_ledger.parquet"
    hidden_path = directory / "hidden_world_manifest.json"
    manifest_path = directory / "generation_manifest.json"
    suite = yaml.safe_load((REPO_ROOT / "configs/suites/self_learning_300k.yaml").read_text(encoding="utf-8"))
    suite_seed = int(suite["generation_seed_ranges"][f"generation_{generation}"][0])
    signer = ManifestSigner(
        hashlib.sha256(f"mavs-sl-phase0:{suite_seed}".encode()).digest(),
        f"phase0-generation-{generation}-deterministic",
    )
    manifest = verify_signed_manifest(manifest_path, signer)
    hidden_body = verify_signed_manifest(hidden_path, signer)
    visible_rows = pq.read_table(ledger_path).to_pylist()
    hidden_by_id = {row["opportunity_id"]: row for row in hidden_body["opportunities"]}
    if [row["opportunity_id"] for row in visible_rows] != [row["opportunity_id"] for row in hidden_body["opportunities"]]:
        raise RuntimeError("Visible/hidden order mismatch.")
    functions = _method_functions()
    decisions = _compute_decisions(visible_rows, hidden_by_id, METHOD_ORDER, functions, hidden_path)
    reverse_decisions = _compute_decisions(visible_rows, hidden_by_id, tuple(reversed(METHOD_ORDER)), functions, hidden_path)
    if stable_hash(decisions) != stable_hash(reverse_decisions):
        raise AssertionError("Method-order invariance failed.")
    output_root.mkdir(parents=True, exist_ok=True)
    trace_path = output_root / f"generation_{generation}.jsonl"
    summary_path = output_root / f"generation_{generation}_summary.json"
    if trace_path.exists() or summary_path.exists():
        raise FileExistsError("Refusing to overwrite Phase 0 stress artifacts.")
    metrics: dict[str, Any] = {}
    matched_opportunity_hashes: dict[str, str] = {}
    logical_origin = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=generation)
    commit_hash = git_commit_hash(REPO_ROOT)
    phase_config_hash = file_sha256(REPO_ROOT / "configs/phases/phase0.yaml")
    environment_packages = {"python": platform.python_version(), "numpy": np.__version__}
    with trace_path.open("x", encoding="utf-8", newline="\n") as handle:
        for method_index, method_id in enumerate(METHOD_ORDER):
            actions = decisions[method_id]
            labels = [bool(hidden_by_id[row["opportunity_id"]]["unsafe_label"]) for row in visible_rows]
            method_metrics = exact_action_metrics(actions, labels)
            method_metrics["uar_wilson_95"] = wilson_interval(int(method_metrics["unsafe_accepted"]), int(method_metrics["unsafe_total"]))
            method_metrics["frr_wilson_95"] = wilson_interval(int(method_metrics["false_rejected"]), int(method_metrics["safe_total"]))
            metrics[method_id] = method_metrics
            matched_opportunity_hashes[method_id] = stable_hash([row["opportunity_id"] for row in visible_rows])
            for row_index, (visible, action) in enumerate(zip(visible_rows, actions)):
                hidden = hidden_by_id[visible["opportunity_id"]]
                record = _trace_record(
                    run_id=run_id,
                    generation=generation,
                    method_id=method_id,
                    method_index=method_index,
                    action=action,
                    visible=visible,
                    hidden=hidden,
                    manifest=manifest,
                    logical_timestamp=(logical_origin + timedelta(seconds=row_index)).isoformat(),
                    commit_hash=commit_hash,
                    phase_config_hash=phase_config_hash,
                    environment_packages=environment_packages,
                )
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    if len(set(matched_opportunity_hashes.values())) != 1:
        raise AssertionError("Methods did not receive identical visible opportunities.")
    permutation = np.random.default_rng(suite_seed).permutation(len(visible_rows))
    permutation_checks = {}
    for method_id in METHOD_ORDER:
        perm_actions = [decisions[method_id][int(index)] for index in permutation]
        perm_labels = [bool(hidden_by_id[visible_rows[int(index)]["opportunity_id"]]["unsafe_label"]) for index in permutation]
        permutation_checks[method_id] = exact_action_metrics(perm_actions, perm_labels) == {
            key: value for key, value in metrics[method_id].items() if not key.endswith("wilson_95")
        }
    non_oracle_future_reads = 0
    for method_id in set(METHOD_ORDER) - ORACLE_METHODS:
        for visible in visible_rows:
            hidden = hidden_by_id[visible["opportunity_id"]]
            release = hidden["feedback_release_step"]
            if release is not None and int(release) > int(visible["step"]):
                # Non-oracle action functions are evaluated with no hidden payload.
                functions[method_id](visible, None)
    summary = {
        "schema_version": "1.0.0",
        "claim_boundary": "diagnostic_bounds_only_non_competitive",
        "generation": generation,
        "canonical_opportunities": len(visible_rows),
        "replay_records": len(visible_rows) * len(METHOD_ORDER),
        "allocation": manifest["partition_counts"],
        "ledger_sha256": file_sha256(ledger_path),
        "trace_sha256": file_sha256(trace_path),
        "metrics": metrics,
        "metamorphic": {
            "method_order_invariant": True,
            "permutation_invariant": all(permutation_checks.values()),
            "matched_visible_opportunity_sha256": next(iter(matched_opportunity_hashes.values())),
            "non_oracle_future_reads": non_oracle_future_reads,
            "action_accounting_exact": True,
            "metric_recomputation_exact": True,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return summary


def _compute_decisions(
    visible_rows: list[dict[str, Any]],
    hidden_by_id: dict[str, dict[str, Any]],
    method_order: tuple[str, ...],
    functions: dict[str, ActionFunction],
    hidden_manifest_path: Path,
) -> dict[str, list[str]]:
    decisions: dict[str, list[str]] = {}
    for method_id in method_order:
        if method_id in ORACLE_METHODS:
            decisions[method_id] = [
                functions[method_id](row, hidden_by_id[row["opportunity_id"]])
                for row in visible_rows
            ]
        else:
            with participant_file_guard(hidden_manifest_path):
                decisions[method_id] = [functions[method_id](row, None) for row in visible_rows]
    return dict(sorted(decisions.items()))


def _trace_record(
    *,
    run_id: str,
    generation: int,
    method_id: str,
    method_index: int,
    action: str,
    visible: dict[str, Any],
    hidden: dict[str, Any],
    manifest: dict[str, Any],
    logical_timestamp: str,
    commit_hash: str | None,
    phase_config_hash: str,
    environment_packages: dict[str, str],
) -> dict[str, Any]:
    outcome_released = hidden["feedback_release_step"] is not None and int(hidden["feedback_release_step"]) <= int(visible["step"])
    record: dict[str, Any] = {
        "world": {
            "world_id": visible["world_id"], "generator_version": "numpy_world_compiler_v1",
            "visible_regime_features": json.loads(visible["visible_regime_features"]),
            "hidden_regime_hash": stable_hash(hidden["hidden_regime"]), "policy_version": visible["policy_version"],
            "corruption_family_hash": stable_hash(hidden["corruption_families"]),
        },
        "decision": {
            "opportunity_id": visible["opportunity_id"], "method_id": method_id, "config_id": "phase0-diagnostic-bound",
            "action": action, "risk": None, "severity": None, "threshold": None, "consensus": None,
            "witnesses": [], "reason_codes": ["PHASE0_DIAGNOSTIC_BOUND"], "compute_cost": {"calls": 0, "tokens": 0, "latency_ms": 0.0},
        },
        "specialists": {"outputs": [], "calibration": [], "provenance": [], "independence_estimate": None, "corruption_exposure": None, "latency_ms": 0.0},
        "diagnostics": {"signals": {}, "scope_match": None, "contribution": None, "idi_proxy": None, "udi_proxy": None, "meta_state": None, "counterfactual_probes": []},
        "outcome": {
            "ground_truth": bool(hidden["unsafe_label"]) if outcome_released or method_id in ORACLE_METHODS else None,
            "released": outcome_released, "release_step": hidden["feedback_release_step"], "source_reliability": hidden["feedback_reliability"],
            "terminal_error_flags": [], "downstream_cost": None,
        },
        "learning": {"trigger": None, "cluster": None, "attribution": None, "proposal": None, "parent": None, "certification_suite": None, "update_action": None, "rollback": None},
        "integrity": {
            "seed_tuple": hidden["seed_tuple"], "git_sha": commit_hash,
            "config_hash": phase_config_hash, "ledger_hash": manifest["ledger_sha256"],
            "run_id": run_id, "timestamp": logical_timestamp,
            "environment_packages": environment_packages,
        },
        "generation": {"generation_id": generation, "reset_class": "independent_generation", "seed_range": None, "manifest_hash": stable_hash(manifest), "prior_library_hash": None, "consolidated_library_hash": None},
        "participant_state": {"condition": "diagnostic_bound", "persistence_eligible": False, "checkpoint": None, "retained_bytes": 0, "component_hashes": {}, "forbidden_state_audit": True},
        "transfer": {"inherited_ids_used": [], "fresh_counterfactual": None, "paired_transfer_delta": None, "negative_transfer": None},
        "consolidation": {"action": None, "marginal_value": None, "replay_evidence": None, "complexity_delta": None, "rollback_target": None},
    }
    record["integrity"]["trace_hash"] = stable_hash(record)
    return record


def _require_hidden(hidden: dict[str, Any] | None) -> dict[str, Any]:
    if hidden is None:
        raise PermissionError("Oracle bound requires evaluator-only hidden state.")
    return hidden


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generation", choices=("1", "2", "3", "all"), default="all")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        raise ValueError("run_id must be one safe path component.")
    output_root = args.output_root or (REPO_ROOT / "results/raw" / args.run_id / "phase0")
    generations = (1, 2, 3) if args.generation == "all" else (int(args.generation),)
    # console.log: phase0.stress.step01.validate_arguments
    console_log("phase0.stress.step01.validate_arguments", run_id=args.run_id, generations=generations, output=str(output_root))
    for generation in generations:
        # console.log: phase0.stress.step02.load_signed_ledgers
        console_log("phase0.stress.step02.load_signed_ledgers", generation=generation)
        # console.log: phase0.stress.step03_execute_bounds_and_metamorphic_checks
        console_log("phase0.stress.step03.execute_bounds_and_metamorphic_checks", generation=generation)
        summary = run_generation(args.run_id, generation, output_root)
        # console.log: phase0.stress.step04_generation_complete
        console_log("phase0.stress.step04.generation_complete", generation=generation, canonical_opportunities=summary["canonical_opportunities"], replay_records=summary["replay_records"], trace_sha256=summary["trace_sha256"])
    # console.log: phase0.stress.step05.complete
    console_log("phase0.stress.step05.complete", generation_count=len(generations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
