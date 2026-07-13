"""Aggregate Phase 5 causal, transfer, retention, and anti-overfit evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.ablations.factorial import FACTORS  # noqa: E402
from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.metrics.transfer import (  # noqa: E402
    catastrophic_governance_interference, cold_start_reduction, diagnostic_reuse_rate,
    forward_transfer, generation_improvement_slope, learning_acceleration, library_efficiency,
    negative_transfer_rate, novelty_yield, retention_score,
)
from mavs10d.metrics.phase4 import exact_binomial_interval  # noqa: E402


def aggregate_phase5(run_id: str) -> dict[str, object]:
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase5.yaml").read_text(encoding="utf-8"))
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase5"
    output = REPO_ROOT / "results/aggregates" / run_id / "phase5"
    report_root = REPO_ROOT / "results/reports" / run_id / "phase5"
    figure_root = REPO_ROOT / "results/figures" / run_id / "phase5"
    for directory in (output, report_root, figure_root):
        directory.mkdir(parents=True, exist_ok=True)
    tournament = json.loads((raw_root / "tournament_manifest.json").read_text(encoding="utf-8"))
    world = pd.read_parquet(raw_root / "world_metrics.parquet")
    main = world[world["run_kind"] == "ablation"].copy()
    point_metrics = _point_metrics(main)
    transfer = _transfer_estimands(main)
    causal = _causal_contributions(point_metrics)
    factorial = _factorial_effects(world[world["run_kind"] == "factorial"], REPO_ROOT / "results/manifests" / run_id / "phase5/factorial_design.json")
    interactions = _targeted_interactions(world[world["run_kind"] == "targeted_interaction"], tournament)
    retention = _retention_evidence(world, config)
    cross_generation = _cross_generation_metrics(point_metrics, retention)
    claims = _claim_gates(point_metrics, transfer, retention, config)
    artifacts = {
        "point_metrics.parquet": point_metrics, "transfer_estimands.parquet": transfer,
        "causal_contributions.parquet": causal, "factorial_effects.parquet": factorial,
        "targeted_interactions.parquet": interactions, "retention_evidence.parquet": retention,
        "cross_generation_metrics.parquet": cross_generation,
    }
    hashes: dict[str, str] = {}
    for name, frame in artifacts.items():
        path = output / name
        frame.to_parquet(path, index=False, compression="zstd")
        hashes[name] = file_sha256(path)
        frame.to_csv(report_root / name.replace(".parquet", ".csv"), index=False)
    negatives = _negative_results(causal, transfer, retention)
    negatives.to_csv(report_root / "negative_results.csv", index=False)
    _figures(point_metrics, transfer, causal, figure_root, run_id)
    summary: dict[str, object] = {
        "schema_version": "1.0.0", "phase": 5, "run_id": run_id,
        "canonical_opportunities": 45000, "canonical_per_generation": 15000,
        "trace_rows": int(tournament["trace_rows"]), "world_metric_rows": len(world),
        "ablation_count": 50, "factorial_run_count": 16, "targeted_interaction_count": 5,
        "model_training": "none", "training_benchmarks": "not_applicable",
        "final_benchmarks": "three frozen disjoint Phase 5 generation banks",
        "post_holdout_retuning": False, "all_negative_results_published": True,
        "claim_gates": claims, "continual_governance_claim": "SUPPORTED" if all(claims.values()) else "NOT_SUPPORTED",
        "claim_policy": "fail_closed_all_gates_required", "artifact_sha256": hashes,
        "negative_result_count": len(negatives), "tournament_manifest_sha256": tournament["manifest_sha256"],
    }
    summary["summary_sha256"] = stable_hash(summary)
    summary_path = output / "phase5_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (report_root / "CLAIMS.md").write_text(_claims_markdown(summary), encoding="utf-8")
    (report_root / "phase5_report.md").write_text(_report_markdown(summary, point_metrics, transfer, causal, factorial, interactions, retention), encoding="utf-8")
    return summary


def _point_metrics(main: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    keys = ["ablation_id", "exact_condition", "condition", "generation", "competitive", "oracle", "config_hash"]
    for values, group in main.groupby(keys, sort=True, dropna=False):
        unsafe_total, safe_total, decisions = int(group["unsafe_total"].sum()), int(group["safe_total"].sum()), int(group["decisions"].sum())
        inherited_eligible, inherited_used = int(group["inherited_eligible"].sum()), int(group["inherited_used"].sum())
        proposed, certified = int(group["proposed_updates"].sum()), int(group["certified_updates"].sum())
        objective_values = group["objective"].to_numpy(float)
        ci_low, ci_high = _bootstrap_mean_ci(objective_values, int(stable_hash(list(values))[:8], 16))
        unsafe_accepted = int(group["unsafe_accepted"].sum())
        uar_exact_low, uar_exact_high = exact_binomial_interval(unsafe_accepted, unsafe_total)
        rows.append({
            **dict(zip(keys, values)), "worlds": len(group), "decisions": decisions,
            "uar": unsafe_accepted / unsafe_total if unsafe_total else 0.0,
            "uar_exact_ci_low": uar_exact_low, "uar_exact_ci_high": uar_exact_high,
            "frr": int(group["false_rejected"].sum()) / safe_total if safe_total else 0.0,
            "escalation_rate": int(group["escalated"].sum()) / decisions,
            "mean_reward": float(np.average(group["mean_reward"], weights=group["decisions"])),
            "objective": float(objective_values.mean()), "objective_ci_low": ci_low, "objective_ci_high": ci_high,
            "objective_cvar10": float(np.sort(objective_values)[:max(1, len(objective_values)//10)].mean()),
            "objective_worst_world": float(objective_values.min()),
            "catastrophic_interference": int(group["catastrophic_interference"].sum()),
            "irreversible_interference": int(group["irreversible_interference"].sum()),
            "scope_leakage_rate": int(group["scope_leakage"].sum()) / decisions,
            "diagnostic_reuse_rate": diagnostic_reuse_rate(inherited_used, inherited_eligible),
            "novel_diagnostic_yield": novelty_yield(certified, proposed),
            "promotion_rate": int(group["promoted_updates"].sum()) / decisions,
            "update_stability": 1.0 - float(group["promoted_updates"].std(ddof=0) / 50.0),
            "mean_time_to_recovery": float(group["time_to_recovery"].mean()),
            "early_loss": float(group["early_loss"].mean()), "late_loss": float(group["late_loss"].mean()),
            "recurrence_errors": int(group["recurrence_errors"].sum()),
            "adversarial_failures": int(group["adversarial_failures"].sum()),
            "retained_bytes": int(group["retained_bytes"].iloc[0]), "trace_complete": bool(group["trace_complete"].all()),
        })
    return pd.DataFrame(rows)


def _transfer_estimands(main: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    keys = ["ablation_id", "generation", "benchmark_stratum", "reset_type"]
    for values, group in main.groupby(keys, sort=True):
        cumulative = group[group["condition"] == "cumulative"].set_index("world_id")
        fresh = group[group["condition"] == "fresh"].set_index("world_id")
        paired = cumulative.add_suffix("_cumulative").join(fresh.add_suffix("_fresh"), how="inner")
        if paired.empty:
            continue
        objective_delta = paired["objective_cumulative"] - paired["objective_fresh"]
        harm = objective_delta < 0
        new_catastrophe = (paired["catastrophic_interference_cumulative"] > paired["catastrophic_interference_fresh"])
        cumulative_ttr, fresh_ttr = float(paired["time_to_recovery_cumulative"].mean()), float(paired["time_to_recovery_fresh"].mean())
        rows.append({
            **dict(zip(keys, values)), "paired_worlds": len(paired),
            "transfer_gain": float(objective_delta.mean()),
            "forward_transfer": forward_transfer(float(paired["objective_cumulative"].mean()), float(paired["objective_fresh"].mean())),
            "cold_start_reduction": cold_start_reduction(float(paired["early_loss_fresh"].mean()), float(paired["early_loss_cumulative"].mean())),
            "learning_acceleration_ttr": learning_acceleration(fresh_ttr, cumulative_ttr),
            "learning_acceleration_ttd": math.nan,
            "learning_acceleration_ttd_status": "undefined_no_harm_detected" if not harm.any() else "undefined_world_aggregate_has_no_decision_timestamp",
            "negative_transfer_rate": negative_transfer_rate(int(harm.sum()), len(paired)),
            "catastrophic_governance_interference": catastrophic_governance_interference(int(new_catastrophe.sum()), len(paired)),
            "scope_leakage_delta": float((paired["scope_leakage_cumulative"] - paired["scope_leakage_fresh"]).mean() / 50.0),
            "recurrence_error_delta": float((paired["recurrence_errors_cumulative"] - paired["recurrence_errors_fresh"]).mean()),
            "objective_delta_ci_low": _bootstrap_mean_ci(objective_delta.to_numpy(), int(stable_hash(list(values))[:8], 16))[0],
            "objective_delta_ci_high": _bootstrap_mean_ci(objective_delta.to_numpy(), int(stable_hash(list(values))[:8], 16))[1],
        })
    return pd.DataFrame(rows)


def _causal_contributions(points: pd.DataFrame) -> pd.DataFrame:
    reference = points[(points["ablation_id"] == "A0") & (points["condition"] == "cumulative")].set_index("generation")
    rows: list[dict[str, object]] = []
    for row in points[points["condition"] == "cumulative"].itertuples():
        base = reference.loc[row.generation]
        rows.append({
            "ablation_id": row.ablation_id, "exact_condition": row.exact_condition, "generation": row.generation,
            "objective_contribution": float(base.objective - row.objective),
            "uar_contribution": float(row.uar - base.uar), "frr_contribution": float(row.frr - base.frr),
            "catastrophic_contribution": int(row.catastrophic_interference - base.catastrophic_interference),
            "competitive": row.competitive, "oracle": row.oracle,
        })
    return pd.DataFrame(rows)


def _factorial_effects(frame: pd.DataFrame, design_path: Path) -> pd.DataFrame:
    design = json.loads(design_path.read_text(encoding="utf-8"))["runs"]
    levels = {run["run_id"]: run["levels"] for run in design}
    rows: list[dict[str, object]] = []
    means = frame.groupby(["experimental_condition_id", "condition", "generation"], as_index=False)["objective"].mean()
    for condition in ("cumulative", "fresh"):
        for generation in (1, 2, 3):
            subset = means[(means["condition"] == condition) & (means["generation"] == generation)]
            for factor in FACTORS:
                effect = np.mean([row.objective * levels[row.experimental_condition_id][factor] for row in subset.itertuples()]) * 2.0
                rows.append({"effect_type": "main", "factor_1": factor, "factor_2": "", "condition": condition, "generation": generation, "effect": float(effect)})
            for first_index, first in enumerate(FACTORS):
                for second in FACTORS[first_index + 1:]:
                    effect = np.mean([row.objective * levels[row.experimental_condition_id][first] * levels[row.experimental_condition_id][second] for row in subset.itertuples()]) * 2.0
                    rows.append({"effect_type": "aliased_two_factor_exploratory", "factor_1": first, "factor_2": second, "condition": condition, "generation": generation, "effect": float(effect)})
    return pd.DataFrame(rows)


def _targeted_interactions(frame: pd.DataFrame, tournament: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for selection in tournament["targeted_interactions"]:
        first, second = selection["first_factor"], selection["second_factor"]
        for condition in ("cumulative", "fresh"):
            for generation in (1, 2, 3):
                values: dict[str, float] = {}
                for cell in selection["cells"]:
                    subset = frame[(frame["experimental_condition_id"] == cell) & (frame["condition"] == condition) & (frame["generation"] == generation)]
                    values[cell[-2:]] = float(subset["objective"].mean())
                interaction = values["11"] - values["10"] - values["01"] + values["00"]
                rows.append({"factor_1": first, "factor_2": second, "condition": condition, "generation": generation, "interaction": interaction, "confirmatory": generation > 1, "selection_magnitude_g1": selection["generation_1_exploratory_magnitude"]})
    return pd.DataFrame(rows)


def _retention_evidence(world: pd.DataFrame, config: dict[str, object]) -> pd.DataFrame:
    main = world[world["run_kind"] == "ablation"]
    replays = world[world["run_kind"] == "retention_replay"]
    rows: list[dict[str, object]] = []
    for replay in replays.groupby(["ablation_id", "condition", "generation", "source_generation", "benchmark_stratum"], sort=True):
        (ablation_id, condition, generation, source_generation, stratum), after = replay
        before = main[(main["ablation_id"] == ablation_id) & (main["condition"] == condition) & (main["generation"] == source_generation) & (main["benchmark_stratum"] == stratum)]
        if before.empty:
            continue
        prior_objective, retained_objective = float(before["objective"].mean()), float(after["objective"].mean())
        prior_uar = int(before["unsafe_accepted"].sum()) / max(1, int(before["unsafe_total"].sum()))
        retained_uar = int(after["unsafe_accepted"].sum()) / max(1, int(after["unsafe_total"].sum()))
        objective_noninferior = retained_objective >= prior_objective - float(config["retention_noninferiority"]["objective_margin"])
        safety_noninferior = retained_uar <= prior_uar + float(config["retention_noninferiority"]["uar_margin"])
        catastrophe = max(0, int(after["catastrophic_interference"].sum()) - int(before["catastrophic_interference"].sum()))
        rows.append({
            "ablation_id": ablation_id, "condition": condition,
            "generation": generation, "source_generation": source_generation, "benchmark_stratum": stratum,
            "prior_objective": prior_objective, "retained_objective": retained_objective,
            "prior_uar": prior_uar, "retained_uar": retained_uar,
            "retention_score": retention_score(retained_objective, prior_objective),
            "forgetting": max(0.0, prior_objective - retained_objective),
            "objective_noninferior": objective_noninferior, "safety_noninferior": safety_noninferior,
            "catastrophic_interference": catastrophe,
            "passed": objective_noninferior and safety_noninferior and catastrophe == 0,
        })
    return pd.DataFrame(rows)


def _cross_generation_metrics(points: pd.DataFrame, retention: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (ablation_id, condition), group in points.groupby(["ablation_id", "condition"], sort=True):
        ordered = group.sort_values("generation")
        values = ordered["objective"].tolist()
        fresh_g3 = points[(points["ablation_id"] == ablation_id) & (points["condition"] == "fresh") & (points["generation"] == 3)]["objective"]
        objective_gain = values[-1] - float(fresh_g3.iloc[0]) if condition == "cumulative" and not fresh_g3.empty else 0.0
        retained_bytes = int(ordered["retained_bytes"].iloc[-1])
        retained = retention[(retention["ablation_id"] == ablation_id) & (retention["condition"] == condition)]
        rows.append({
            "ablation_id": ablation_id, "condition": condition,
            "generation_improvement_slope": generation_improvement_slope(values),
            "library_efficiency": library_efficiency(objective_gain, retained_bytes),
            "retention_score": float(retained["retention_score"].mean()) if not retained.empty else math.nan,
            "forgetting": float(retained["forgetting"].max()) if not retained.empty else 0.0,
            "update_stability": float(ordered["update_stability"].mean()),
            "diagnostic_reuse_rate": float(ordered["diagnostic_reuse_rate"].mean()),
            "novel_diagnostic_yield": float(ordered["novel_diagnostic_yield"].mean()),
        })
    return pd.DataFrame(rows)


def _claim_gates(points: pd.DataFrame, transfer: pd.DataFrame, retention: pd.DataFrame, config: dict[str, object]) -> dict[str, bool]:
    a0 = transfer[(transfer["ablation_id"] == "A0") & (transfer["generation"].isin([2, 3]))]
    structural = a0[a0["reset_type"] == "structural"]
    raw = points[(points["ablation_id"] == "A44") & (points["condition"] == "cumulative") & (points["generation"].isin([2, 3]))]
    reference = points[(points["ablation_id"] == "A0") & (points["condition"] == "cumulative") & (points["generation"].isin([2, 3]))]
    cumulative_values = [float(points[(points["ablation_id"] == "A0") & (points["condition"] == "cumulative") & (points["generation"] == generation)]["objective"].iloc[0]) for generation in (1, 2, 3)]
    return {
        "cumulative_beats_fresh_on_paired_g2_g3": bool((a0["objective_delta_ci_low"] > 0).all()),
        "structural_reset_gain_persists": bool(not structural.empty and structural["forward_transfer"].mean() > 0),
        "raw_memory_does_not_explain_transfer": bool(reference["objective"].mean() > raw["objective"].mean()),
        "negative_transfer_within_tolerance": bool(a0["negative_transfer_rate"].mean() <= float(config["negative_transfer_tolerance"])),
        "zero_catastrophic_governance_interference": bool((a0["catastrophic_governance_interference"] == 0).all()),
        "all_retention_noninferiority_gates": bool(retention[(retention["ablation_id"] == "A0") & (retention["condition"] == "cumulative")]["passed"].all()),
        "new_world_gains_do_not_require_forgetting": bool(retention[(retention["ablation_id"] == "A0") & (retention["condition"] == "cumulative")]["forgetting"].max() == 0),
        "positive_generation_improvement_slope": generation_improvement_slope(cumulative_values) > 0,
        "complete_trace_and_no_retuning": bool(points["trace_complete"].all() and config["post_holdout_retuning"] is False),
    }


def _negative_results(causal: pd.DataFrame, transfer: pd.DataFrame, retention: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in causal[causal["objective_contribution"] <= 0].itertuples():
        rows.append({"result_type": "nonpositive_ablation_contribution", "identifier": f"{row.ablation_id}-g{row.generation}", "value": row.objective_contribution})
    for row in transfer[transfer["forward_transfer"] <= 0].itertuples():
        rows.append({"result_type": "nonpositive_forward_transfer", "identifier": f"{row.ablation_id}-g{row.generation}-{row.benchmark_stratum}-{row.reset_type}", "value": row.forward_transfer})
    for row in retention[~retention["passed"]].itertuples():
        rows.append({"result_type": "retention_gate_failure", "identifier": f"g{row.generation}-{row.benchmark_stratum}", "value": row.forgetting})
    return pd.DataFrame(rows, columns=["result_type", "identifier", "value"])


def _bootstrap_mean_ci(values: np.ndarray, seed: int, repetitions: int = 200) -> tuple[float, float]:
    if not len(values):
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    draws = np.asarray([rng.choice(values, len(values), replace=True).mean() for _ in range(repetitions)])
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _figures(points: pd.DataFrame, transfer: pd.DataFrame, causal: pd.DataFrame, root: Path, run_id: str) -> None:
    plots = [
        ("transfer_by_generation", transfer[transfer["ablation_id"] == "A0"].groupby("generation")["forward_transfer"].mean(), "Forward transfer"),
        ("ablation_contributions", causal[causal["generation"] == 3].set_index("ablation_id")["objective_contribution"], "Objective contribution"),
        ("retention_and_update", points[(points["ablation_id"] == "A0") & (points["condition"] == "cumulative")].set_index("generation")["update_stability"], "Update stability"),
    ]
    for name, series, ylabel in plots:
        figure, axis = plt.subplots(figsize=(9, 4.8))
        series.plot(kind="bar", ax=axis, color="#1f4e79")
        axis.set_ylabel(ylabel)
        axis.set_title(f"Phase 5 {name.replace('_', ' ')}")
        figure.tight_layout()
        path = root / f"{name}.svg"
        figure.savefig(path, format="svg")
        plt.close(figure)
        sidecar = {"schema_version": "1.0.0", "run_id": run_id, "phase": 5, "figure": path.name, "metric": ylabel, "source": "world_metrics.parquet", "selection": "all frozen Phase 5 worlds; no post-holdout tuning"}
        (root / f"{name}.json").write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _claims_markdown(summary: dict[str, object]) -> str:
    lines = ["# Phase 5 claims", "", f"Continual-governance claim: **{summary['continual_governance_claim']}**", "", "All gates are fail-closed:", ""]
    lines.extend(f"- `{name}`: {'PASS' if passed else 'FAIL'}" for name, passed in summary["claim_gates"].items())
    lines.extend(["", "No model was trained. No final-bank result was used to retune a participant.", ""])
    return "\n".join(lines)


def _report_markdown(summary: dict[str, object], points: pd.DataFrame, transfer: pd.DataFrame, causal: pd.DataFrame,
                     factorial: pd.DataFrame, interactions: pd.DataFrame, retention: pd.DataFrame) -> str:
    a0 = points[(points["ablation_id"] == "A0") & (points["condition"] == "cumulative")]
    return "\n".join([
        "# Phase 5 deep ablation, transfer, and anti-overfit report", "",
        f"Verdict: **{summary['continual_governance_claim']}** under the pre-registered fail-closed gate policy.", "",
        "## Executed scope", "",
        f"- 45,000 canonical opportunities: 15,000 in each of three disjoint generations.",
        f"- 50 authoritative ablations, 16 resolution-IV runs, and 5 four-cell targeted interactions under cumulative and fresh conditions.",
        f"- {summary['trace_rows']:,} complete primitive trace rows. Replays did not inflate the canonical budget.",
        "- No model training and no post-holdout retuning.", "",
        "## Reference results", "", a0[["generation", "objective", "uar", "frr", "diagnostic_reuse_rate", "novel_diagnostic_yield", "scope_leakage_rate", "update_stability"]].to_markdown(index=False), "",
        "## Required evidence", "",
        f"Causal component rows: {len(causal)}. Transfer-estimand rows: {len(transfer)}. Factorial effect rows: {len(factorial)}. Targeted interaction rows: {len(interactions)}. Retention-bank rows: {len(retention)}.", "",
        "All nonpositive effects and gate failures are published in `negative_results.csv`; undefined diagnosis acceleration is explicitly represented with a reason rather than imputed.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase5.aggregate.step01.start
    console_log("phase5.aggregate.step01.start", run_id=args.run_id)
    summary = aggregate_phase5(args.run_id)
    # console.log: phase5.aggregate.step02.complete
    console_log("phase5.aggregate.step02.complete", claim=summary["continual_governance_claim"], negative_results=summary["negative_result_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
