"""Development-only full-grid selection with lexicographic safety constraints."""

from __future__ import annotations

import itertools
from typing import Any

import numpy as np
import yaml

from mavs10d.core.hashing import stable_hash


def tune_phase1_methods(tuning_bank, calibration_bank, grid_path) -> dict[str, Any]:
    grid = yaml.safe_load(grid_path.read_text(encoding="utf-8"))["development_sweeps"]
    labels = np.asarray([row.unsafe for row in tuning_bank.hidden], dtype=bool)
    risks = np.asarray([row.risk_score for row in tuning_bank.visible], dtype=float)
    method_family = {
        "context_fixed": "selective",
        "confidence_gate": "confidence_gate",
        "entropy_gate": "selective",
        "margin_gate": "selective",
        "generalized_selective": "selective",
        "neyman_pearson": "neyman_pearson",
        "cost_sensitive": "neyman_pearson",
        "split_conformal": "conformal",
        "conformal_risk_control": "conformal",
        "adaptive_conformal": "conformal",
        "online_conformal": "conformal",
        "adwin": "drift",
        "page_hinkley": "drift",
        "online_experts": "online_experts",
        "ctta_entropy": "ctta",
        "ctta_pseudo_label": "ctta",
    }
    sweep_results: dict[str, list[dict[str, Any]]] = {}
    selected: dict[str, dict[str, Any]] = {}
    calibration_scores = [abs(row.risk_score - float(outcome.unsafe)) for row, outcome in zip(calibration_bank.visible, calibration_bank.hidden)]
    calibration_quantiles = [float(value) for value in np.quantile(calibration_scores, np.linspace(0.05, 0.95, 19))]
    for method, family in method_family.items():
        family_grid = dict(grid[family])
        keys = sorted(family_grid)
        combinations = [dict(zip(keys, values)) for values in itertools.product(*(family_grid[key] for key in keys))]
        rows: list[dict[str, Any]] = []
        for params in combinations:
            threshold = _threshold(params)
            escalate = max(0.15, threshold - float(params.get("escalation_band", 0.15)))
            actions = np.where(risks >= threshold, 2, np.where(risks >= escalate, 1, 0))
            uar = float(((actions == 0) & labels).sum() / max(1, labels.sum()))
            frr = float(((actions == 2) & ~labels).sum() / max(1, (~labels).sum()))
            escalation = float((actions == 1).mean())
            rows.append({"params": params, "uar": uar, "frr": frr, "escalation_rate": escalation})
        sweep_results[method] = rows
        winner = min(rows, key=lambda row: (row["uar"], row["frr"], row["escalation_rate"], stable_hash(row["params"])))
        selected[method] = {
            **winner["params"],
            "reject_threshold": _threshold(winner["params"]),
            "escalate_threshold": max(0.15, _threshold(winner["params"]) - float(winner["params"].get("escalation_band", 0.15))),
            "calibration_scores": calibration_quantiles,
            "calibration_size": len(calibration_scores),
            "memory_bytes": 1_048_576,
            "latency_ms": 1.0,
            "selection_metrics": {key: winner[key] for key in ("uar", "frr", "escalation_rate")},
        }
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "selection_stage": 1,
        "objective": "lexicographic_uar_then_frr_then_escalation",
        "tuning_manifest_hash": tuning_bank.manifest["manifest_sha256"],
        "calibration_manifest_hash": calibration_bank.manifest["manifest_sha256"],
        "sweep_results": sweep_results,
        "selected": selected,
        "post_holdout_retuning": False,
    }
    result["selection_sha256"] = stable_hash(result)
    return result


def _threshold(params: dict[str, Any]) -> float:
    if "risk_threshold" in params:
        return float(params["risk_threshold"])
    if "reject_below" in params:
        return min(0.90, max(0.30, 1.0 - float(params["reject_below"])))
    if "unsafe_risk_limit" in params:
        return min(0.85, max(0.35, 0.50 + float(params["unsafe_risk_limit"])))
    if "alpha" in params:
        return min(0.90, max(0.40, 0.65 - float(params["alpha"])))
    return 0.60
