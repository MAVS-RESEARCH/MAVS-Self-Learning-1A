"""Deterministically replay every Phase 7 case and compare raw runtime artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

import pandas as pd

from mavs10d.core.hashing import stable_hash
from mavs10d.core.runtime import PerceptionClosureRuntime
from phase7_common import load_yaml, read_jsonl, run_root, write_json


def normalize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for record in records:
        row = {}
        for key, value in record.items():
            if isinstance(value, str) and value[:1] in {"[", "{"}:
                try:
                    row[key] = json.loads(value)
                    continue
                except json.JSONDecodeError:
                    pass
            row[key] = value
        normalized.append(row)
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = run_root(args.run_id)
    phase = load_yaml("configs/phases/phase7.yaml")
    runtime = PerceptionClosureRuntime(load_yaml("configs/perception_closure_v04/runtime.yaml"))
    cases = read_jsonl(root / "manifests" / "runtime_cases.jsonl")
    replayed = [runtime.resolve(case, size) for size in map(int, phase["microbenchmark"]["library_size_sweep"]) for case in cases]
    expected_traces = pd.read_parquet(root / "traces" / "perception_traces.parquet").to_dict(orient="records")
    expected_rounds = normalize(pd.read_parquet(root / "traces" / "perception_rounds.parquet").to_dict(orient="records"))
    expected_queries = normalize(pd.read_parquet(root / "traces" / "queries_and_probes.parquet").to_dict(orient="records"))
    expected_escalations = normalize(pd.read_parquet(root / "traces" / "escalations.parquet").to_dict(orient="records"))
    actual_traces = [item.trace for item in replayed]
    actual_rounds = [dict(record, library_size=item.library_size) for item in replayed for record in item.rounds]
    actual_queries = [dict(record, library_size=item.library_size) for item in replayed for record in item.queries_and_probes]
    actual_escalations = [dict(item.escalation, library_size=item.library_size) for item in replayed if item.escalation]
    comparisons = {
        "traces": stable_hash(expected_traces) == stable_hash(actual_traces),
        "rounds": stable_hash(expected_rounds) == stable_hash(actual_rounds),
        "queries_and_probes": stable_hash(expected_queries) == stable_hash(actual_queries),
        "escalations": stable_hash(expected_escalations) == stable_hash(actual_escalations),
    }
    report = {
        "execution_count": len(replayed), "comparisons": comparisons,
        "terminal_counts": dict(Counter(item.trace["terminal_action"] for item in replayed)),
        "expected_hashes": {
            "traces": stable_hash(expected_traces), "rounds": stable_hash(expected_rounds),
            "queries_and_probes": stable_hash(expected_queries), "escalations": stable_hash(expected_escalations),
        },
        "actual_hashes": {
            "traces": stable_hash(actual_traces), "rounds": stable_hash(actual_rounds),
            "queries_and_probes": stable_hash(actual_queries), "escalations": stable_hash(actual_escalations),
        },
        "passed": all(comparisons.values()),
    }
    write_json(root / "integrity" / "trace_replay.json", report)
    if not report["passed"]:
        raise RuntimeError(f"Phase 7 deterministic replay failed: {comparisons}")
    # console.log: phase7.replay.complete
    print(f'{{"event":"phase7.replay.complete","executions":{len(replayed)},"comparisons":4}}')


if __name__ == "__main__":
    main()
