from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from mavs10d.core.types import EpisodeTrace, trace_supports_mavs_fields

REQUIRED_TRACE_FIELDS: tuple[str, ...] = (
    "run_id",
    "config_hash",
    "git_commit",
    "environment_id",
    "method_id",
    "seed",
    "episode_id",
    "step_id",
    "observation",
    "candidate",
    "decision",
    "step_result",
    "hidden_label_hash",
    "trace_complete",
    "created_at_utc",
    "metadata",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def console_log(event: str, **fields: Any) -> None:
    payload = json.dumps({"event": event, **fields}, sort_keys=True, default=str)
    print(f"console.log {payload}", file=sys.stdout)


@dataclass(frozen=True)
class TraceValidationResult:
    path: Path
    record_count: int
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


class JsonlTraceWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8", newline="\n")
        self.records_written = 0

    def write(self, trace: EpisodeTrace) -> None:
        record = trace.to_dict()
        self._handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._handle.flush()
        self.records_written += 1

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "JsonlTraceWriter":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def validate_trace_record(record: dict[str, Any], line_number: int) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_TRACE_FIELDS:
        if field not in record:
            errors.append(f"line {line_number}: missing required field {field}")
    decision = record.get("decision", {})
    if not isinstance(decision, dict):
        errors.append(f"line {line_number}: decision must be an object")
        return errors
    for field in (
        "decision",
        "risk_score",
        "severity",
        "rationale",
        "triggered_checks",
        "threshold",
        "trace",
    ):
        if field not in decision:
            errors.append(f"line {line_number}: missing decision field {field}")
    trace = decision.get("trace", {})
    if isinstance(trace, dict) and not trace_supports_mavs_fields(trace):
        errors.append(f"line {line_number}: decision trace lacks MAVS field support")
    if record.get("trace_complete") is not True:
        errors.append(f"line {line_number}: trace_complete is not true")
    return errors


def validate_trace_file(path: Path) -> TraceValidationResult:
    errors: list[str] = []
    record_count = 0
    if not path.exists():
        return TraceValidationResult(path=path, record_count=0, errors=["file missing"])
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record_count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc}")
                continue
            errors.extend(validate_trace_record(record, line_number))
    if record_count == 0:
        errors.append("file contains no trace records")
    return TraceValidationResult(path=path, record_count=record_count, errors=errors)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)

