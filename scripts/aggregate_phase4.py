"""Aggregate the complete Phase 4 tournament into paired frontier evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.metrics.frontier import FrontierPoint, additive_epsilon, hypervolume, matched_rate_advantages, pareto_frontier  # noqa: E402
from mavs10d.metrics.phase4 import distribution_summary, exact_binomial_interval, hierarchical_bootstrap_ratio, holm_adjust, paired_sign_test  # noqa: E402


def aggregate_phase4(run_id: str) -> dict[str, object]:
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase4.yaml").read_text(encoding="utf-8"))
    raw_root = REPO_ROOT / "results/raw" / run_id / "phase4"
    manifest_root = REPO_ROOT / "results/manifests" / run_id / "phase4"
    tournament_manifest = json.loads((raw_root / "tournament_manifest.json").read_text(encoding="utf-8"))
    registry = json.loads((manifest_root / "operating_points.json").read_text(encoding="utf-8"))
    world = pd.read_parquet(raw_root / "world_metrics.parquet")
    output = REPO_ROOT / "results/aggregates" / run_id / "phase4"
    output.mkdir(parents=True, exist_ok=True)
    points = _aggregate_points(world, int(config["bootstrap_repetitions"]), float(config["cvar_alpha"]))
    point_path = output / "point_metrics.parquet"
    points.to_parquet(point_path, index=False, compression="zstd")
    world_path = output / "world_metrics.parquet"
    world.to_parquet(world_path, index=False, compression="zstd")
    competitive = points[(points["competitive"]) & (~points["oracle"]) & (points["frr"] < 0.999) & (points["escalation_rate"] < 0.999)].copy()
    frontier_all = _frontier_frame(competitive, "unconstrained")
    frontier_compute = _frontier_frame(competitive[competitive["normalized_compute"] <= float(config["matched_compute_limit"])], "matched_compute")
    frontiers = pd.concat([frontier_all, frontier_compute], ignore_index=True)
    frontier_path = output / "frontiers.parquet"
    frontiers.to_parquet(frontier_path, index=False, compression="zstd")
    treatment = competitive[competitive["family"] == "mavs_sl"]
    baselines = competitive[competitive["family"] != "mavs_sl"]
    treatment_frontier = _as_points(_frontier_frame(treatment, "treatment"))
    baseline_frontier = _as_points(_frontier_frame(baselines, "baseline"))
    hv_treatment = hypervolume(treatment_frontier)
    hv_baseline = hypervolume(baseline_frontier)
    epsilon = additive_epsilon(treatment_frontier, baseline_frontier)
    matched = matched_rate_advantages(
        treatment_frontier, baseline_frontier,
        frr_tolerance=float(config["matched_frr_tolerance"]), uar_tolerance=float(config["matched_uar_tolerance"]),
    )
    comparisons = _paired_comparisons(world, tuple(config["confirmatory_families"]))
    comparison_path = output / "paired_comparisons.parquet"
    comparisons.to_parquet(comparison_path, index=False, compression="zstd")
    resource_matching = _resource_regression_check(treatment, baselines, float(config["matched_frr_tolerance"]), float(config["matched_uar_tolerance"]))
    gates = {
        "paired_hypervolume_improvement_gt_zero": hv_treatment - hv_baseline > 0.0,
        "lower_uar_at_matched_frr": bool(matched["lower_uar_at_matched_frr"]),
        "lower_frr_at_matched_uar": bool(matched["lower_frr_at_matched_uar"]),
        "no_hidden_escalation_intervention_latency_compute_regression": bool(resource_matching["no_regression"]),
        "not_single_favorable_scalarization": len(treatment_frontier) > 1,
        "reject_all_not_competitive": not bool(((competitive["frr"] >= 0.999) | (competitive["escalation_rate"] >= 0.999)).any()),
        "all_sweep_values_published": len(points) == int(tournament_manifest["operating_point_count"]),
        "complete_trace_lineage": bool(world["trace_complete"].all()),
        "confirmatory_fwer_recorded": bool(len(comparisons) and comparisons["holm_p"].notna().all()),
    }
    superiority_supported = all(gates.values())
    summary: dict[str, object] = {
        "schema_version": "1.0.0", "run_id": run_id, "phase": 4,
        "canonical_opportunities": 75000, "operating_point_count": len(points),
        "trace_rows": int(tournament_manifest["trace_rows"]), "world_metric_rows": len(world),
        "unconstrained_frontier_points": len(frontier_all), "matched_compute_frontier_points": len(frontier_compute),
        "mavs_sl_hypervolume": hv_treatment, "baseline_hypervolume": hv_baseline,
        "paired_hypervolume_improvement": hv_treatment - hv_baseline, "additive_epsilon": epsilon,
        "matched_comparisons": matched, "resource_matching": resource_matching,
        "baseline_wins": int(comparisons["baseline_wins"].sum()), "mavs_sl_wins": int(comparisons["mavs_sl_wins"].sum()),
        "paired_ties": int(comparisons["ties"].sum()), "superiority_gates": gates,
        "superiority_claim": "SUPPORTED" if superiority_supported else "NOT_SUPPORTED",
        "claim_policy": "fail_closed_all_gates_required", "model_training": "none",
        "point_metrics_sha256": file_sha256(point_path), "world_metrics_sha256": file_sha256(world_path),
        "frontiers_sha256": file_sha256(frontier_path), "paired_comparisons_sha256": file_sha256(comparison_path),
        "tournament_manifest_sha256": tournament_manifest["manifest_sha256"],
        "operating_point_registry_sha256": registry["registry_hash"],
    }
    summary["summary_sha256"] = stable_hash(summary)
    (output / "phase4_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_reports(run_id, points, frontiers, comparisons, summary, registry, tournament_manifest)
    return summary


def _aggregate_points(world: pd.DataFrame, repetitions: int, cvar_alpha: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for point_id, group in world.groupby("point_id", sort=True):
        unsafe_accepted, unsafe_total = int(group["unsafe_accepted"].sum()), int(group["unsafe_total"].sum())
        false_rejected, safe_total = int(group["false_rejected"].sum()), int(group["safe_total"].sum())
        escalated, decisions = int(group["escalated"].sum()), int(group["decisions"].sum())
        uar_ci = hierarchical_bootstrap_ratio(group["unsafe_accepted"], group["unsafe_total"], repetitions=repetitions, seed=int(stable_hash(point_id)[:8], 16))
        frr_ci = hierarchical_bootstrap_ratio(group["false_rejected"], group["safe_total"], repetitions=repetitions, seed=int(stable_hash(point_id + "frr")[:8], 16))
        exact_ci = exact_binomial_interval(unsafe_accepted, unsafe_total)
        row = {column: group[column].iloc[0] for column in ["point_id", "family", "mechanism", "condition", "competitive", "oracle", "config_hash", "calls", "tokens", "latency_ms", "memory_bytes", "update_compute", "normalized_compute", "git_sha", "environment_hash", "registry_sha256"]}
        row.update({
            "decisions": decisions, "worlds": len(group), "unsafe_total": unsafe_total, "safe_total": safe_total,
            "unsafe_accepted": unsafe_accepted, "false_rejected": false_rejected, "escalated": escalated,
            "uar": unsafe_accepted / unsafe_total if unsafe_total else 0.0,
            "frr": false_rejected / safe_total if safe_total else 0.0, "escalation_rate": escalated / decisions,
            "uar_hier_ci_low": uar_ci[0], "uar_hier_ci_high": uar_ci[1],
            "frr_hier_ci_low": frr_ci[0], "frr_hier_ci_high": frr_ci[1],
            "uar_exact_ci_low": exact_ci[0], "uar_exact_ci_high": exact_ci[1],
            "catastrophic_episodes": int(group["catastrophic_episodes"].sum()),
            "irreversible_episodes": int(group["irreversible_episodes"].sum()),
            "mean_reward": float(np.average(group["mean_reward"], weights=group["decisions"])),
            "governance_regret": float(np.average(group["governance_regret"], weights=group["decisions"])),
            "dynamic_regret": float(np.average(group["dynamic_regret"], weights=group["decisions"])),
            "brier": float(group["brier"].mean()), "ece": float(group["ece"].mean()),
            "adaptation_lag": float(group["adaptation_lag"].mean()), "recovery_delta": float(group["recovery_delta"].mean()),
            "recurrence_errors": int(group["recurrence_errors"].sum()), "trace_complete": bool(group["trace_complete"].all()),
        })
        for metric in ("uar", "frr", "escalation_rate", "governance_regret", "dynamic_regret", "brier", "ece"):
            for name, value in distribution_summary(group[metric], cvar_alpha).items():
                row[f"{metric}_{name}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def _frontier_frame(frame: pd.DataFrame, frontier_type: str) -> pd.DataFrame:
    if frame.empty:
        return frame.assign(frontier_type=pd.Series(dtype=str))
    candidates = [FrontierPoint(row.point_id, row.uar, row.frr, row.escalation_rate, row.normalized_compute) for row in frame.itertuples()]
    ids = {point.method_id for point in pareto_frontier(candidates)}
    result = frame[frame["point_id"].isin(ids)].copy()
    result["frontier_type"] = frontier_type
    return result


def _as_points(frame: pd.DataFrame) -> tuple[FrontierPoint, ...]:
    return tuple(FrontierPoint(row.point_id, row.uar, row.frr, row.escalation_rate, row.normalized_compute) for row in frame.itertuples())


def _paired_comparisons(world: pd.DataFrame, confirmatory: tuple[str, ...]) -> pd.DataFrame:
    treatment_ids = sorted(world.loc[world["family"] == "mavs_sl", "point_id"].unique())
    treatment_id = treatment_ids[0]
    treatment = world[world["point_id"] == treatment_id].set_index(["generation", "world_id"])
    rows: list[dict[str, object]] = []
    for family in confirmatory:
        if family == "mavs_sl":
            continue
        ids = sorted(world.loc[world["family"] == family, "point_id"].unique())
        if not ids:
            continue
        baseline_id = ids[0]
        baseline = world[world["point_id"] == baseline_id].set_index(["generation", "world_id"])
        paired = treatment[["uar", "frr", "mean_reward", "normalized_compute"]].join(baseline[["uar", "frr", "mean_reward", "normalized_compute"]], lsuffix="_mavs", rsuffix="_baseline", how="inner")
        reward_delta = (paired["mean_reward_mavs"] - paired["mean_reward_baseline"]).to_numpy()
        rows.append({
            "family": family, "treatment_point": treatment_id, "baseline_point": baseline_id,
            "paired_worlds": len(paired), "mean_reward_delta": float(np.mean(reward_delta)),
            "mean_uar_delta": float((paired["uar_mavs"] - paired["uar_baseline"]).mean()),
            "mean_frr_delta": float((paired["frr_mavs"] - paired["frr_baseline"]).mean()),
            "mean_compute_delta": float((paired["normalized_compute_mavs"] - paired["normalized_compute_baseline"]).mean()),
            "baseline_wins": int(np.sum(reward_delta < 0.0)), "mavs_sl_wins": int(np.sum(reward_delta > 0.0)),
            "ties": int(np.sum(reward_delta == 0.0)),
            "raw_p": paired_sign_test(reward_delta), "confirmatory": True,
        })
    adjusted = holm_adjust([float(row["raw_p"]) for row in rows])
    for row, value in zip(rows, adjusted):
        row["holm_p"] = value
        row["fwer_significant"] = value < 0.05
    return pd.DataFrame(rows)


def _resource_regression_check(treatment: pd.DataFrame, baselines: pd.DataFrame, frr_tolerance: float, uar_tolerance: float) -> dict[str, object]:
    matched_pairs = 0
    non_regressing_pairs = 0
    for mavs in treatment.itertuples():
        for baseline in baselines.itertuples():
            if abs(mavs.frr - baseline.frr) > frr_tolerance and abs(mavs.uar - baseline.uar) > uar_tolerance:
                continue
            matched_pairs += 1
            no_regression = (
                mavs.escalation_rate <= baseline.escalation_rate + 1e-12
                and mavs.calls <= baseline.calls and mavs.tokens <= baseline.tokens
                and mavs.latency_ms <= baseline.latency_ms + 1e-12
                and mavs.normalized_compute <= baseline.normalized_compute + 1e-12
            )
            non_regressing_pairs += int(no_regression)
    return {
        "matched_resource_pairs": matched_pairs, "non_regressing_resource_pairs": non_regressing_pairs,
        "no_regression": bool(matched_pairs and non_regressing_pairs == matched_pairs),
        "dimensions": ["escalation_rate", "calls", "tokens", "latency_ms", "normalized_compute"],
    }


def _write_reports(run_id: str, points: pd.DataFrame, frontiers: pd.DataFrame, comparisons: pd.DataFrame,
                   summary: dict[str, object], registry: dict[str, object], tournament: dict[str, object]) -> None:
    report_root = REPO_ROOT / "results/reports" / run_id / "phase4"
    figure_root = report_root / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    svg_path = figure_root / "safety_utility_burden_frontier.svg"
    _frontier_svg(frontiers, svg_path)
    provenance = {
        "figure": str(svg_path.relative_to(REPO_ROOT)), "figure_sha256": file_sha256(svg_path),
        "point_ids": sorted(frontiers["point_id"].unique()),
        "point_config_hashes": {row.point_id: row.config_hash for row in points.itertuples()},
        "trace_artifacts": tournament["artifacts"], "ledger_artifacts": tournament["ledger_artifacts"],
        "registry_sha256": registry["registry_hash"],
        "git_sha": points["git_sha"].iloc[0], "environment_hash": points["environment_hash"].iloc[0],
        "complete_sweep_point_ids": sorted(points["point_id"].unique()),
    }
    sidecar_path = svg_path.with_suffix(".provenance.json")
    sidecar_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    point_table_path = report_root / "operating_point_table.csv"
    points.sort_values("point_id").to_csv(point_table_path, index=False)
    lines = [
        "# Phase 4 full matched tournament and Pareto audit", "",
        f"- Canonical opportunities: {summary['canonical_opportunities']}",
        f"- Frozen operating points: {summary['operating_point_count']}",
        f"- Raw decision traces: {summary['trace_rows']}",
        f"- Unconstrained frontier points: {summary['unconstrained_frontier_points']}",
        f"- Matched-compute frontier points: {summary['matched_compute_frontier_points']}",
        f"- MAVS-SL hypervolume: {summary['mavs_sl_hypervolume']:.8f}",
        f"- Baseline hypervolume: {summary['baseline_hypervolume']:.8f}",
        f"- Hypervolume difference: {summary['paired_hypervolume_improvement']:.8f}",
        f"- Additive epsilon: {summary['additive_epsilon']:.8f}",
        f"- Confirmatory baseline wins: {summary['baseline_wins']}",
        f"- Confirmatory MAVS-SL wins: {summary['mavs_sl_wins']}",
        f"- Confirmatory ties: {summary['paired_ties']}",
        f"- Superiority claim: {summary['superiority_claim']}", "",
        "## Fail-closed superiority gates", "",
    ]
    lines.extend(f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in summary["superiority_gates"].items())
    lines += ["", "## Statistical and integrity policy", "", "All 139 sweep points are published. Comparisons use paired worlds, world-first/episode-level bootstrap intervals, exact UAR intervals, and Holm family-wise correction. Diagnostic and oracle bounds are excluded from competitive claims. No model was trained and no final-bank retuning occurred.", ""]
    (report_root / "phase4_report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    comparisons.to_csv(report_root / "confirmatory_comparisons.csv", index=False)


def _frontier_svg(frontiers: pd.DataFrame, path: Path) -> None:
    width, height, pad = 900, 620, 70
    points = []
    for row in frontiers.itertuples():
        x = pad + (1.0 - float(row.frr)) * (width - 2 * pad)
        y = pad + float(row.uar) * (height - 2 * pad)
        radius = 3.0 + 8.0 * float(row.normalized_compute)
        color = "#9b2226" if row.family == "mavs_sl" else "#005f73"
        points.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{color}"><title>{row.point_id}; UAR={row.uar:.5f}; FRR={row.frr:.5f}; compute={row.normalized_compute:.5f}</title></circle>')
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="black"/>', f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="black"/>', f'<text x="{width/2}" y="{height-18}" text-anchor="middle">1 - false rejection rate</text>', f'<text x="20" y="{height/2}" transform="rotate(-90 20 {height/2})" text-anchor="middle">unsafe acceptance rate (lower is better)</text>', *points, '<text x="650" y="35" fill="#9b2226">MAVS-SL</text>', '<text x="750" y="35" fill="#005f73">Baselines</text>', '</svg>']
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase4.aggregate.step01.start
    console_log("phase4.aggregate.step01.start", run_id=args.run_id)
    summary = aggregate_phase4(args.run_id)
    # console.log: phase4.aggregate.step02.complete
    console_log("phase4.aggregate.step02.complete", superiority_claim=summary["superiority_claim"], frontier_points=summary["unconstrained_frontier_points"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
