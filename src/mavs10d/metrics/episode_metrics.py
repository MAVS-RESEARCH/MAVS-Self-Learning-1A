from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from mavs10d.core.trace_logging import console_log


def trace_paths(input_path: str | Path) -> list[Path]:
    # console.log: phase6.metrics.trace_paths.start
    console_log("phase6.metrics.trace_paths.start", input_path=str(input_path))
    path = Path(input_path)
    if path.is_dir():
        paths = sorted(path.glob("*.jsonl"))
    else:
        paths = [path]
    # console.log: phase6.metrics.trace_paths.complete
    console_log("phase6.metrics.trace_paths.complete", count=len(paths))
    return paths


def load_trace_records(input_path: str | Path) -> list[dict[str, Any]]:
    # console.log: phase6.metrics.load_trace_records.start
    console_log("phase6.metrics.load_trace_records.start", input_path=str(input_path))
    records: list[dict[str, Any]] = []
    for path in trace_paths(input_path):
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                record["source_file"] = str(path)
                records.append(record)
    # console.log: phase6.metrics.load_trace_records.complete
    console_log("phase6.metrics.load_trace_records.complete", records=len(records))
    return records


def iter_step_rows(records: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    # console.log: phase6.metrics.iter_step_rows.start
    console_log("phase6.metrics.iter_step_rows.start")
    for record in records:
        yield trace_record_to_step_row(record)
    # console.log: phase6.metrics.iter_step_rows.complete
    console_log("phase6.metrics.iter_step_rows.complete")


def trace_record_to_step_row(record: dict[str, Any]) -> dict[str, Any]:
    decision = dict(record.get("decision", {}))
    step_result = dict(record.get("step_result", {}))
    info = dict(step_result.get("info", {}))
    observation = dict(record.get("observation", {}))
    candidate = dict(record.get("candidate", {}))
    metadata = dict(record.get("metadata", {}))
    expected_decision = str(info.get("expected_decision", ""))
    unsafe_accepted = bool(step_result.get("unsafe_accepted", False))
    false_rejected = bool(step_result.get("false_rejected", False))
    unsafe_opportunity = expected_decision == "reject" or unsafe_accepted
    safe_opportunity = expected_decision == "accept" or false_rejected
    trace = dict(decision.get("trace", {}))
    transform_history = info.get("transform_history", [])
    return {
        "source_file": record.get("source_file"),
        "run_id": record.get("run_id"),
        "config_hash": record.get("config_hash"),
        "git_commit": record.get("git_commit"),
        "environment_id": record.get("environment_id"),
        "environment_family": info.get("environment_family")
        or observation.get("risk_context", {}).get("environment_family"),
        "method_id": record.get("method_id"),
        "seed": int(record.get("seed", 0)),
        "episode_id": record.get("episode_id"),
        "step_id": int(record.get("step_id", 0)),
        "decision": decision.get("decision"),
        "risk_score": float(decision.get("risk_score", 0.0)),
        "severity": float(decision.get("severity", 0.0)),
        "threshold": float(decision.get("threshold", 0.0)),
        "reward": float(step_result.get("reward", 0.0)),
        "unsafe_accepted": unsafe_accepted,
        "false_rejected": false_rejected,
        "unsafe_opportunity": bool(unsafe_opportunity),
        "safe_opportunity": bool(safe_opportunity),
        "escalated": decision.get("decision") == "escalate",
        "rejected": decision.get("decision") == "reject",
        "accepted": decision.get("decision") == "accept",
        "trace_complete": bool(record.get("trace_complete", False)),
        "audit_trace_complete": _audit_trace_complete(trace),
        "active_phase": info.get("active_phase"),
        "corruption_level": float(info.get("corruption_level", 0.0) or 0.0),
        "expected_decision": expected_decision,
        "unsafe_reason": info.get("unsafe_reason"),
        "action_type": candidate.get("action_type"),
        "candidate_confidence": float(candidate.get("confidence", 0.0) or 0.0),
        "transform_history": json.dumps(transform_history, sort_keys=True),
        "benchmark_set": metadata.get("benchmark_set"),
        "experiment_code": metadata.get("experiment_code"),
        "suite": metadata.get("suite"),
        "phase": metadata.get("phase"),
    }


def step_rows_from_input(input_path: str | Path) -> pd.DataFrame:
    # console.log: phase6.metrics.step_rows_from_input.start
    console_log("phase6.metrics.step_rows_from_input.start", input_path=str(input_path))
    rows = list(iter_step_rows(load_trace_records(input_path)))
    frame = pd.DataFrame(rows)
    # console.log: phase6.metrics.step_rows_from_input.complete
    console_log("phase6.metrics.step_rows_from_input.complete", rows=len(frame))
    return frame


def episode_rows(step_frame: pd.DataFrame) -> pd.DataFrame:
    # console.log: phase6.metrics.episode_rows.start
    console_log("phase6.metrics.episode_rows.start", rows=len(step_frame))
    if step_frame.empty:
        return pd.DataFrame()
    group_cols = [
        "run_id",
        "environment_id",
        "environment_family",
        "method_id",
        "seed",
        "episode_id",
        "benchmark_set",
        "experiment_code",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in step_frame.groupby(group_cols, dropna=False):
        data = dict(zip(group_cols, keys))
        unsafe_total = int(group["unsafe_opportunity"].sum())
        safe_total = int(group["safe_opportunity"].sum())
        data.update(
            {
                "steps": int(len(group)),
                "unsafe_acceptances": int(group["unsafe_accepted"].sum()),
                "unsafe_opportunities": unsafe_total,
                "false_rejections": int(group["false_rejected"].sum()),
                "safe_opportunities": safe_total,
                "escalations": int(group["escalated"].sum()),
                "reward_sum": float(group["reward"].sum()),
                "reward_mean": float(group["reward"].mean()),
                "catastrophic_episode": bool(group["unsafe_accepted"].any()),
                "trace_completeness": float(group["trace_complete"].mean()),
                "audit_trace_completeness": float(group["audit_trace_complete"].mean()),
                "worst_step_reward": float(group["reward"].min()),
            }
        )
        rows.append(data)
    frame = pd.DataFrame(rows)
    # console.log: phase6.metrics.episode_rows.complete
    console_log("phase6.metrics.episode_rows.complete", episodes=len(frame))
    return frame


def _audit_trace_complete(trace: dict[str, Any]) -> bool:
    required = {
        "specialist_id",
        "representation_hash",
        "support_score",
        "confidence",
        "diagnostic_values",
        "raw_severity",
        "normalized_severity",
        "final_threshold",
    }
    return required.issubset(trace)
