from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from jsonschema import Draft202012Validator

from mavs10d.metrics.phase1 import nondominated_frontier, phase1_method_summary
from mavs10d.training.phase1_proxy import predict_checkpoint


ROOT = Path(__file__).resolve().parents[2]


def _frame() -> pd.DataFrame:
    rows = []
    for step in range(100):
        unsafe = step % 4 == 0
        decision = "reject" if unsafe else "accept"
        rows.append({"generation": 1, "method_name": "test", "condition": "fixed", "world_id": "w", "domain": "text_safety", "shift_class": "abrupt", "schedule_family": "piecewise_hidden", "step": step, "unsafe": unsafe, "decision": decision, "risk_score": 0.8 if unsafe else 0.2, "uar_error": False, "frr_error": False, "escalated": False, "catastrophic_error": False, "intervention_loss": 0.0001, "oracle_loss": 0.0, "change_active": step >= 30, "recovery_active": step >= 70, "calls": step + 1, "tokens": 0, "latency_ms": step + 1.0, "wall_time_ms": step + 1.0, "memory_bytes": 1024, "update_operations": step, "configuration_switches": 0, "calibration_examples": 10})
    return pd.DataFrame(rows)


def test_phase1_metric_registry_produces_every_required_metric() -> None:
    summary, worlds = phase1_method_summary(_frame())
    required = set(yaml.safe_load((ROOT / "configs/phases/phase1.yaml").read_text(encoding="utf-8"))["required_metrics"])
    assert required <= set(summary.columns)
    assert not summary[list(required)].isna().any().any()
    assert len(worlds) == 1


def test_recovery_lag_penalizes_persistent_conservatism() -> None:
    frame = _frame()
    frame.loc[frame["recovery_active"] & ~frame["unsafe"], "decision"] = "reject"
    summary, _ = phase1_method_summary(frame)
    assert summary.iloc[0]["recovery_lag"] == 30


def test_frontier_removes_dominated_operating_point() -> None:
    summary = pd.DataFrame([{"generation": 1, "method_name": "a", "condition": "fixed", "uar": 0.1, "frr": 0.1, "escalation_rate": 0.1}, {"generation": 1, "method_name": "b", "condition": "fixed", "uar": 0.2, "frr": 0.2, "escalation_rate": 0.2}])
    assert nondominated_frontier(summary)["method_name"].tolist() == ["a"]


def test_ctta_checkpoint_is_frozen_and_inference_is_finite() -> None:
    checkpoint = ROOT / "artifacts/models/phase1_ctta/phase1_ctta_source.npz"
    manifest = json.loads((checkpoint.parent / "training_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["trials"]) == 15
    assert set(manifest["training_domains"]).isdisjoint(manifest["blind_evaluation_domains"])
    prediction = predict_checkpoint(checkpoint, np.zeros((3, 8), dtype=float))
    assert prediction.shape == (3,)
    assert np.isfinite(prediction).all() and ((prediction >= 0.0) & (prediction <= 1.0)).all()


def test_phase1_trace_schema_is_valid() -> None:
    schema = json.loads((ROOT / "schemas/phase1_trace.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_suite_seed_ranges_and_checkpoints_match_workplan() -> None:
    suite = yaml.safe_load((ROOT / "configs/suites/self_learning_300k.yaml").read_text(encoding="utf-8"))
    assert suite["generation_seed_ranges"] == {"generation_1": [100000, 199999], "generation_2": [300000, 399999], "generation_3": [500000, 599999]}
    assert suite["checkpoints"] == [0, 1000, 5000, 10000, 25000, 50000, 75000, 100000]
