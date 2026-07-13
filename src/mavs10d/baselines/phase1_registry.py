"""Frozen Phase 1 method inventory and common-interface construction."""

from __future__ import annotations

from typing import Any

from mavs10d.baselines.context_fixed import ContextFixedBaseline
from mavs10d.baselines.drift import DriftBaseline
from mavs10d.baselines.neyman_pearson import NeymanPearsonBaseline
from mavs10d.baselines.online_conformal import OnlineConformalBaseline
from mavs10d.baselines.online_experts import OnlineExpertsBaseline
from mavs10d.baselines.phase1_common import Phase1Baseline
from mavs10d.baselines.selective import SelectiveBaseline
from mavs10d.baselines.test_time_adaptation import CTTABaseline
from mavs10d.core.config import MethodConfig


FIXED_METHODS: tuple[str, ...] = (
    "context_fixed",
    "confidence_gate",
    "entropy_gate",
    "margin_gate",
    "generalized_selective",
    "neyman_pearson",
    "cost_sensitive",
    "split_conformal",
    "conformal_risk_control",
)
ADAPTIVE_METHODS: tuple[str, ...] = (
    "adaptive_conformal",
    "online_conformal",
    "adwin",
    "page_hinkley",
    "online_experts",
    "ctta_entropy",
    "ctta_pseudo_label",
)


def build_phase1_method(method_name: str, condition: str, selected: dict[str, Any]) -> Phase1Baseline:
    common = {
        "reject_threshold": float(selected.get("reject_threshold", 0.62)),
        "escalate_threshold": float(selected.get("escalate_threshold", 0.45)),
        "calibration_size": int(selected.get("calibration_size", 0)),
        "latency_ms": float(selected.get("latency_ms", 1.0)),
        "memory_bytes": int(selected.get("memory_bytes", 1_048_576)),
    }
    method_id = f"{method_name}:{condition}"
    if method_name == "context_fixed":
        return ContextFixedBaseline(MethodConfig(method_id, "context_fixed", common))
    if method_name in {"confidence_gate", "entropy_gate", "margin_gate", "generalized_selective"}:
        mode = {
            "confidence_gate": "confidence",
            "entropy_gate": "entropy",
            "margin_gate": "margin",
            "generalized_selective": "generalized_selective",
        }[method_name]
        return SelectiveBaseline(MethodConfig(method_id, "selective", {**common, "mode": mode}))
    if method_name in {"neyman_pearson", "cost_sensitive"}:
        mode = "risk_constrained" if method_name == "neyman_pearson" else "cost_sensitive"
        return NeymanPearsonBaseline(MethodConfig(method_id, "neyman_pearson", {**common, "mode": mode, "likelihood_ratio": selected.get("likelihood_ratio", 2.0)}))
    if method_name in {"split_conformal", "conformal_risk_control", "adaptive_conformal", "online_conformal"}:
        mode = {
            "split_conformal": "split",
            "conformal_risk_control": "crc",
            "adaptive_conformal": "adaptive",
            "online_conformal": "online",
        }[method_name]
        return OnlineConformalBaseline(
            MethodConfig(
                method_id,
                "online_conformal",
                {
                    **common,
                    "mode": mode,
                    "alpha": selected.get("alpha", 0.05),
                    "window": selected.get("window", 64),
                    "calibration_scores": selected.get("calibration_scores", [0.2, 0.3, 0.4, 0.5, 0.6]),
                    "risk_limit": selected.get("risk_limit", 0.50),
                },
            )
        )
    if method_name in {"adwin", "page_hinkley"}:
        mode = "adwin" if method_name == "adwin" else "page_hinkley"
        return DriftBaseline(MethodConfig(method_id, "drift", {**common, "mode": mode, "delta": selected.get("delta", 0.025), "window": selected.get("window", 32)}))
    if method_name == "online_experts":
        return OnlineExpertsBaseline(MethodConfig(method_id, "online_experts", {**common, "eta": selected.get("eta", 0.05)}))
    if method_name in {"ctta_entropy", "ctta_pseudo_label"}:
        mode = "entropy" if method_name == "ctta_entropy" else "pseudo_label"
        return CTTABaseline(
            MethodConfig(
                method_id,
                "test_time_adaptation",
                {
                    **common,
                    "mode": mode,
                    "learning_rate": selected.get("learning_rate", 0.0001),
                    "confidence_floor": selected.get("confidence", 0.90),
                    "update_frequency": selected.get("update_frequency", 8),
                },
            )
        )
    raise KeyError(f"Unknown Phase 1 method: {method_name}")


def expected_method_conditions(generation: int) -> tuple[tuple[str, str], ...]:
    fixed = tuple((name, "fixed") for name in FIXED_METHODS)
    if generation == 1:
        adaptive = tuple((name, "cumulative") for name in ADAPTIVE_METHODS)
    else:
        adaptive = tuple((name, condition) for name in ADAPTIVE_METHODS for condition in ("cumulative", "fresh"))
    return fixed + adaptive
