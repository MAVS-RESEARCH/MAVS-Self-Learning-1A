"""Execute the frozen Phase 5 ablation, factorial, and targeted-interaction replays."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from itertools import combinations, product
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.ablations.engine import ACTION_NAMES, decide_visible  # noqa: E402
from mavs10d.ablations.factorial import FACTORS, factor_state, resolution_iv_design  # noqa: E402
from mavs10d.ablations.registry import AblationSpec, AblationState, load_ablation_specs  # noqa: E402
from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.metrics.transfer import constrained_objective  # noqa: E402
from mavs10d.transfer.consolidation import consolidation_change  # noqa: E402
from mavs10d.transfer.controls import checkpoint_for  # noqa: E402


FACTOR_STATE_FIELDS = {
    "meta_diagnostics": "meta_diagnostics", "synthesis": "diagnostic_creation",
    "retained_replay": "retained_replay", "counterfactual_validation": "counterfactual_validation",
    "certification": "adversarial_certification", "configuration_library": "configuration_library",
}


def run_tournament(run_id: str) -> dict[str, object]:
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase5"
    run_manifest = json.loads((manifest_root / "run_manifest.json").read_text(encoding="utf-8"))
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase5"
    raw_root.mkdir(parents=True, exist_ok=True)
    ledgers, hidden, generation_bodies = _load_banks(run_manifest)
    specs = load_ablation_specs()
    writers: dict[int, pq.ParquetWriter] = {}
    trace_paths = {generation: raw_root / f"generation_{generation}_traces.parquet" for generation in (1, 2, 3)}
    metrics: list[pd.DataFrame] = []
    main_world: dict[tuple[str, str, int], pd.DataFrame] = {}
    checkpoints: list[dict[str, object]] = []
    consolidation_cards: list[dict[str, object]] = []
    card_writers: dict[tuple[str, int], pq.ParquetWriter] = {}

    def execute(generation: int, run_kind: str, experiment_id: str, ablation_id: str,
                exact_condition: str, state: AblationState, config_hash: str,
                condition: str, competitive: bool, oracle: bool,
                bank_generation: int | None = None) -> pd.DataFrame:
        source_generation = bank_generation or generation
        checkpoint = checkpoint_for(state, ablation_id, condition, generation)
        frame = _execute_point(
            run_id, run_manifest, generation_bodies[source_generation], ledgers[source_generation], hidden[source_generation],
            run_kind, experiment_id, ablation_id, exact_condition, state, config_hash, condition,
            competitive, oracle, checkpoint.retained_bytes, evaluation_generation=generation,
        )
        _append_table(writers, generation, trace_paths[generation], frame)
        world = _world_metrics(frame)
        metrics.append(world)
        _append_cards(card_writers, raw_root, generation, frame)
        return world

    for generation in (1, 2, 3):
        for spec in specs:
            for condition in ("cumulative", "fresh"):
                current_world = execute(
                    generation, "ablation", spec.ablation_id, spec.ablation_id,
                    spec.exact_condition, spec.state(), spec.config_hash, condition,
                    spec.competitive, spec.oracle,
                )
                main_world[(spec.ablation_id, condition, generation)] = current_world
                checkpoint = checkpoint_for(spec.state(), spec.ablation_id, condition, generation)
                checkpoints.append({**asdict(checkpoint), "checkpoint_hash": checkpoint.checkpoint_hash})

    for generation in (2, 3):
        source_generation = generation - 1
        for spec in specs:
            for condition in ("cumulative", "fresh"):
                retained = execute(
                    generation, "retention_replay", f"R-{spec.ablation_id}-g{source_generation}",
                    spec.ablation_id, f"Protected Generation {source_generation} retention replay.",
                    spec.state(), spec.config_hash, condition, spec.competitive, spec.oracle,
                    bank_generation=source_generation,
                )
                prior = main_world[(spec.ablation_id, condition, source_generation)]
                retained_objective = float(retained["objective"].mean())
                prior_objective = float(prior["objective"].mean())
                retained_uar = int(retained["unsafe_accepted"].sum()) / max(1, int(retained["unsafe_total"].sum()))
                prior_uar = int(prior["unsafe_accepted"].sum()) / max(1, int(prior["unsafe_total"].sum()))
                new_catastrophes = max(0, int(retained["catastrophic_interference"].sum()) - int(prior["catastrophic_interference"].sum()))
                retention_passed = (
                    retained_objective >= prior_objective - 0.02
                    and retained_uar <= prior_uar + 0.01
                    and new_catastrophes == 0
                )
                checkpoint = checkpoint_for(spec.state(), spec.ablation_id, condition, generation)
                card = consolidation_change(
                    generation, spec.ablation_id, condition,
                    checkpoint.diagnostics + checkpoint.configurations,
                    spec.state().consolidation, retention_passed,
                )
                card_payload = {**asdict(card), "change_hash": card.change_hash,
                                "source_generation": source_generation,
                                "prior_objective": prior_objective, "retained_objective": retained_objective,
                                "prior_uar": prior_uar, "retained_uar": retained_uar,
                                "new_catastrophic_interference": new_catastrophes}
                consolidation_cards.append(card_payload)

    factorial_metrics: list[pd.DataFrame] = []
    design = resolution_iv_design()
    for generation in (1, 2, 3):
        for run in design:
            state = replace(AblationState(), **factor_state(run.levels))
            config_hash = stable_hash(["phase5-factorial", run.run_id, dict(run.levels)])
            for condition in ("cumulative", "fresh"):
                result = execute(
                    generation, "factorial", run.run_id, "FACTORIAL",
                    "Resolution-IV component toggle run.", state, config_hash, condition, True, False,
                )
                result = result.assign(**{f"level_{name}": run.levels[name] for name in FACTORS})
                factorial_metrics.append(result)

    selected_pairs = _select_interactions(pd.concat(factorial_metrics, ignore_index=True), limit=5)
    interaction_manifest: list[dict[str, object]] = []
    for first, second, magnitude in selected_pairs:
        cells: list[str] = []
        for first_on, second_on in product((False, True), repeat=2):
            cell_id = f"I-{first}-{second}-{int(first_on)}{int(second_on)}"
            cells.append(cell_id)
            state = replace(AblationState(), **{
                FACTOR_STATE_FIELDS[first]: first_on, FACTOR_STATE_FIELDS[second]: second_on,
            })
            config_hash = stable_hash(["phase5-targeted-interaction", first, second, first_on, second_on])
            for generation in (1, 2, 3):
                for condition in ("cumulative", "fresh"):
                    execute(
                        generation, "targeted_interaction", cell_id, "INTERACTION",
                        f"Targeted paired rerun: {first} by {second}.", state, config_hash,
                        condition, True, False,
                    )
        interaction_manifest.append({
            "first_factor": first, "second_factor": second,
            "generation_1_exploratory_magnitude": magnitude, "cells": cells,
        })

    for writer in writers.values():
        writer.close()
    for writer in card_writers.values():
        writer.close()
    world_path = raw_root / "world_metrics.parquet"
    pd.concat(metrics, ignore_index=True).to_parquet(world_path, index=False, compression="zstd")
    checkpoint_path = raw_root / "participant_checkpoints.json"
    checkpoint_path.write_text(json.dumps(checkpoints, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    consolidation_path = raw_root / "consolidation_cards.json"
    consolidation_path.write_text(json.dumps(consolidation_cards, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected_by_generation = {
        1: (50 * 2 + 16 * 2 + 5 * 4 * 2) * 15000,
        2: (50 * 2 + 50 * 2 + 16 * 2 + 5 * 4 * 2) * 15000,
        3: (50 * 2 + 50 * 2 + 16 * 2 + 5 * 4 * 2) * 15000,
    }
    artifacts = [{
        "generation": generation, "trace": str(trace_paths[generation].relative_to(REPO_ROOT)),
        "trace_sha256": file_sha256(trace_paths[generation]), "trace_rows": expected_by_generation[generation],
        "terminal_cards": str((raw_root / f"generation_{generation}_terminal_error_cards.parquet").relative_to(REPO_ROOT)),
        "promoted_update_cards": str((raw_root / f"generation_{generation}_promoted_update_cards.parquet").relative_to(REPO_ROOT)),
    } for generation in (1, 2, 3)]
    manifest: dict[str, object] = {
        "schema_version": "1.0.0", "phase": 5, "run_id": run_id,
        "implementation_git_sha": run_manifest["implementation_git_sha"],
        "canonical_opportunities": 45000, "canonical_per_generation": 15000,
        "replays_count_as_canonical": False, "ablation_count": 50,
        "factorial_run_count": 16, "targeted_interaction_count": 5,
        "targeted_interaction_selection": "generation_1_factorial_exploratory_absolute_interaction_magnitude",
        "targeted_interactions": interaction_manifest,
        "conditions": ["cumulative", "fresh"], "trace_rows": sum(expected_by_generation.values()),
        "retention_replay_count": 200,
        "complete_sweep": True, "model_training": "none", "best_seed_selection": False,
        "post_holdout_retuning": False, "participant_final_access": False,
        "world_metrics": str(world_path.relative_to(REPO_ROOT)), "world_metrics_sha256": file_sha256(world_path),
        "participant_checkpoints": str(checkpoint_path.relative_to(REPO_ROOT)),
        "participant_checkpoints_sha256": file_sha256(checkpoint_path),
        "consolidation_cards": str(consolidation_path.relative_to(REPO_ROOT)),
        "consolidation_cards_sha256": file_sha256(consolidation_path), "artifacts": artifacts,
    }
    manifest["manifest_sha256"] = stable_hash(manifest)
    (raw_root / "tournament_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _load_banks(run_manifest: dict[str, object]) -> tuple[dict[int, pd.DataFrame], dict[int, pd.DataFrame], dict[int, dict[str, object]]]:
    ledgers: dict[int, pd.DataFrame] = {}
    hidden: dict[int, pd.DataFrame] = {}
    bodies: dict[int, dict[str, object]] = {}
    for item in run_manifest["generations"]:
        generation = int(item["generation"])
        ledgers[generation] = pd.read_parquet(REPO_ROOT / item["ledger"])
        hidden[generation] = pd.DataFrame(json.loads((REPO_ROOT / item["hidden"]).read_text(encoding="utf-8"))["outcomes"])
        bodies[generation] = json.loads((REPO_ROOT / item["manifest"]).read_text(encoding="utf-8"))["body"]
        if not np.array_equal(ledgers[generation]["opportunity_id"], hidden[generation]["opportunity_id"]):
            raise RuntimeError(f"Phase 5 generation {generation} visible/hidden alignment failed.")
    return ledgers, hidden, bodies


def _execute_point(run_id: str, run_manifest: dict[str, object], generation_body: dict[str, object],
                   ledger: pd.DataFrame, hidden: pd.DataFrame, run_kind: str, experiment_id: str,
                   ablation_id: str, exact_condition: str, state: AblationState, config_hash: str,
                   condition: str, competitive: bool, oracle: bool, retained_bytes: int,
                   evaluation_generation: int | None = None) -> pd.DataFrame:
    evaluation_generation = evaluation_generation or int(ledger["generation"].iloc[0])
    features = {column: ledger[column].to_numpy() for column in ledger.select_dtypes(include=["number", "bool"]).columns}
    features["reset_match"] = (
        np.ones(len(ledger), dtype=float) if state.reset_filter == "all"
        else (ledger["reset_type"].to_numpy() == state.reset_filter).astype(float)
    )
    unsafe = hidden["unsafe"].to_numpy(dtype=bool)
    catastrophic = hidden["catastrophic_if_accepted"].to_numpy(dtype=bool)
    irreversible = hidden["irreversible_if_accepted"].to_numpy(dtype=bool)
    if oracle:
        actions = np.where(unsafe, 1, 0).astype(np.int8)
        scores, thresholds = unsafe.astype(float), np.full(len(ledger), 0.5)
        diagnostics = {name: np.zeros(len(ledger), dtype=bool) for name in (
            "unknown", "inherited_eligible", "inherited_used", "proposal",
            "certified_update", "promoted_update", "scope_influence",
        )}
    else:
        actions, scores, thresholds, diagnostics = decide_visible(state, condition, evaluation_generation, features)
    accept, reject, escalate = actions == 0, actions == 1, actions == 2
    reward = np.where(escalate, 0.35, np.where((accept & ~unsafe) | (reject & unsafe), 1.0, -1.0))
    reward = np.where(accept & catastrophic, -6.0, reward)
    reward = np.where(accept & irreversible, np.minimum(reward, -3.5), reward)
    terminal_error = reward < 0
    environment_hash = stable_hash(run_manifest["environment_packages"])
    lineage = stable_hash([run_id, experiment_id, condition, generation_body["ledger_sha256"], config_hash])
    return pd.DataFrame({
        "run_id": run_id, "run_kind": run_kind, "experimental_condition_id": experiment_id,
        "ablation_id": ablation_id, "exact_condition": exact_condition, "condition": condition,
        "generation": evaluation_generation, "source_generation": ledger["generation"],
        "competitive": competitive, "oracle": oracle,
        "opportunity_id": ledger["opportunity_id"], "world_id": ledger["world_id"],
        "world_seed": ledger["world_seed"], "step": ledger["step"],
        "benchmark_stratum": ledger["benchmark_stratum"], "reset_type": ledger["reset_type"],
        "domain": ledger["domain"], "corruption_family": ledger["corruption_family"],
        "composition_id": ledger["composition_id"], "generator_id": ledger["generator_id"],
        "action": ACTION_NAMES[actions], "risk_score": scores, "threshold": thresholds,
        "unsafe": unsafe, "accepted": accept, "rejected": reject, "escalated": escalate,
        "expected_action": np.where(unsafe, "reject", "accept"),
        "hidden_mechanism_after_reveal": hidden["hidden_mechanism"],
        "uar_error": unsafe & accept, "frr_error": ~unsafe & reject,
        "catastrophic_interference": catastrophic & accept,
        "irreversible_interference": irreversible & accept, "terminal_error": terminal_error,
        "reward": reward, "governance_regret": 1.0 - reward,
        "dynamic_regret": (1.0 - reward) * (1.0 + ledger["shift_score"].to_numpy()),
        "unknown": diagnostics["unknown"], "inherited_eligible": diagnostics["inherited_eligible"],
        "inherited_used": diagnostics["inherited_used"], "proposal": diagnostics["proposal"],
        "certified_update": diagnostics["certified_update"], "promoted_update": diagnostics["promoted_update"],
        "scope_influence": diagnostics["scope_influence"],
        "scope_leakage": diagnostics["scope_influence"] & (ledger["scope_validity"].to_numpy() < 0.48),
        "adversarial_probe": ledger["adversarial_pressure"].to_numpy(dtype=bool),
        "attack_family": ledger["attack_family_visible"], "shift_score": ledger["shift_score"],
        "normalized_compute": 0.32 + 0.03 * int(state.meta_diagnostics) + 0.03 * int(state.adversarial_certification),
        "retained_bytes": retained_bytes, "config_hash": config_hash,
        "ledger_sha256": generation_body["ledger_sha256"], "git_sha": run_manifest["implementation_git_sha"],
        "environment_hash": environment_hash, "registry_sha256": run_manifest["ablation_registry_sha256"],
        "trace_lineage_sha256": lineage, "trace_complete": True, "exclusion_reason": "",
    })


def _world_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    world_count, width = 300, 50
    if len(frame) != world_count * width:
        raise ValueError("Phase 5 world metrics require 300 contiguous 50-decision worlds.")
    indices = np.arange(0, len(frame), width)
    matrix = lambda column, dtype=None: frame[column].to_numpy(dtype=dtype).reshape(world_count, width)
    unsafe = matrix("unsafe", bool)
    unsafe_total, safe_total = unsafe.sum(1), width - unsafe.sum(1)
    uar_count, frr_count = matrix("uar_error", bool).sum(1), matrix("frr_error", bool).sum(1)
    uar = np.divide(uar_count, unsafe_total, out=np.zeros(world_count), where=unsafe_total > 0)
    frr = np.divide(frr_count, safe_total, out=np.zeros(world_count), where=safe_total > 0)
    escalation = matrix("escalated", bool).mean(1)
    reward = matrix("reward", float)
    recovery_time = np.full(world_count, np.nan)
    for world_index in range(world_count):
        for end in range(5, width + 1):
            if reward[world_index, end - 5:end].mean() >= 0.70:
                recovery_time[world_index] = end
                break
    compute = float(frame["normalized_compute"].iloc[0])
    objective = np.asarray([constrained_objective(float(reward[i].mean()), float(uar[i]), float(frr[i]), float(escalation[i]), compute) for i in range(world_count)])
    return pd.DataFrame({
        **{column: frame[column].iloc[indices].to_numpy() for column in (
            "run_kind", "experimental_condition_id", "ablation_id", "exact_condition", "condition",
            "generation", "source_generation", "competitive", "oracle", "world_id", "world_seed", "benchmark_stratum",
            "reset_type", "domain", "corruption_family", "composition_id", "generator_id",
            "config_hash", "ledger_sha256", "git_sha", "environment_hash", "registry_sha256",
        )},
        "decisions": width, "unsafe_total": unsafe_total, "safe_total": safe_total,
        "unsafe_accepted": uar_count, "false_rejected": frr_count,
        "escalated": matrix("escalated", bool).sum(1), "uar": uar, "frr": frr,
        "escalation_rate": escalation, "mean_reward": reward.mean(1), "objective": objective,
        "catastrophic_interference": matrix("catastrophic_interference", bool).sum(1),
        "irreversible_interference": matrix("irreversible_interference", bool).sum(1),
        "scope_leakage": matrix("scope_leakage", bool).sum(1),
        "inherited_eligible": matrix("inherited_eligible", bool).sum(1),
        "inherited_used": matrix("inherited_used", bool).sum(1),
        "proposed_updates": matrix("proposal", bool).sum(1),
        "certified_updates": matrix("certified_update", bool).sum(1),
        "promoted_updates": matrix("promoted_update", bool).sum(1),
        "adversarial_failures": (matrix("adversarial_probe", bool) & matrix("terminal_error", bool)).sum(1),
        "early_loss": (1.0 - reward[:, :20]).mean(1),
        "late_loss": (1.0 - reward[:, -10:]).mean(1),
        "time_to_recovery": recovery_time,
        "recurrence_errors": (reward[:, -10:] < 0).sum(1),
        "retained_bytes": int(frame["retained_bytes"].iloc[0]),
        "normalized_compute": compute, "trace_complete": True,
    })


def _select_interactions(factorial: pd.DataFrame, limit: int) -> list[tuple[str, str, float]]:
    exploratory = factorial[(factorial["generation"] == 1) & (factorial["condition"] == "cumulative")]
    rows: list[tuple[str, str, float]] = []
    for first, second in combinations(FACTORS, 2):
        product_level = exploratory[f"level_{first}"] * exploratory[f"level_{second}"]
        magnitude = float(abs((exploratory["objective"] * product_level).mean()))
        rows.append((first, second, magnitude))
    return sorted(rows, key=lambda row: (-row[2], row[0], row[1]))[:limit]


def _append_table(writers: dict[int, pq.ParquetWriter], generation: int, path: Path, frame: pd.DataFrame) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    if generation not in writers:
        writers[generation] = pq.ParquetWriter(path, table.schema, compression="zstd", use_dictionary=True)
    writers[generation].write_table(table)


def _append_cards(writers: dict[tuple[str, int], pq.ParquetWriter], root: Path, generation: int, frame: pd.DataFrame) -> None:
    terminal = frame.loc[frame["terminal_error"], [
        "run_id", "experimental_condition_id", "ablation_id", "condition", "generation",
        "opportunity_id", "world_id", "action", "expected_action", "unsafe",
        "hidden_mechanism_after_reveal", "catastrophic_interference", "irreversible_interference",
        "reward", "trace_lineage_sha256",
    ]].copy()
    terminal.rename(columns={"action": "actual_action"}, inplace=True)
    terminal["immediate_containment"] = np.where(
        terminal["catastrophic_interference"] | terminal["irreversible_interference"],
        "quarantine_rollback_and_escalate", "quarantine_and_replay",
    )
    terminal["card_id"] = [
        stable_hash([lineage, opportunity_id, "terminal-error-card"])
        for lineage, opportunity_id in zip(terminal["trace_lineage_sha256"], terminal["opportunity_id"])
    ]
    promoted = frame.loc[frame["promoted_update"], [
        "run_id", "experimental_condition_id", "ablation_id", "condition", "generation",
        "opportunity_id", "world_id", "proposal", "certified_update", "promoted_update",
        "scope_leakage", "trace_lineage_sha256",
    ]].copy()
    for kind, suffix, card in (
        ("terminal", "terminal_error_cards", terminal),
        ("promoted", "promoted_update_cards", promoted),
    ):
        if card.empty:
            continue
        table = pa.Table.from_pandas(card, preserve_index=False)
        key = (kind, generation)
        if key not in writers:
            writers[key] = pq.ParquetWriter(root / f"generation_{generation}_{suffix}.parquet", table.schema, compression="zstd", use_dictionary=True)
        writers[key].write_table(table)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase5.tournament.step01.start
    console_log("phase5.tournament.step01.start", run_id=args.run_id)
    manifest = run_tournament(args.run_id)
    # console.log: phase5.tournament.step02.complete
    console_log("phase5.tournament.step02.complete", trace_rows=manifest["trace_rows"], targeted_interactions=manifest["targeted_interaction_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
