from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from mavs10d.core.hashing import stable_hash

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

SELF_LEARNING_TRACE_FIELD_FLOOR: dict[str, tuple[str, ...]] = {
    "world": ("world_id", "generator_version", "visible_regime_features", "hidden_regime_hash", "policy_version", "corruption_family_hash"),
    "decision": ("opportunity_id", "method_id", "config_id", "action", "risk", "severity", "threshold", "consensus", "witnesses", "reason_codes", "compute_cost"),
    "specialists": ("outputs", "calibration", "provenance", "independence_estimate", "corruption_exposure", "latency_ms"),
    "diagnostics": ("signals", "scope_match", "contribution", "idi_proxy", "udi_proxy", "meta_state", "counterfactual_probes"),
    "outcome": ("ground_truth", "released", "release_step", "source_reliability", "terminal_error_flags", "downstream_cost"),
    "learning": ("trigger", "cluster", "attribution", "proposal", "parent", "certification_suite", "update_action", "rollback"),
    "integrity": ("seed_tuple", "git_sha", "config_hash", "ledger_hash", "run_id", "trace_hash", "timestamp", "environment_packages"),
    "generation": ("generation_id", "reset_class", "seed_range", "manifest_hash", "prior_library_hash", "consolidated_library_hash"),
    "participant_state": ("condition", "persistence_eligible", "checkpoint", "retained_bytes", "component_hashes", "forbidden_state_audit"),
    "transfer": ("inherited_ids_used", "fresh_counterfactual", "paired_transfer_delta", "negative_transfer"),
    "consolidation": ("action", "marginal_value", "replay_evidence", "complexity_delta", "rollback_target"),
}


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


def validate_self_learning_trace_file(path: Path, schema_path: Path) -> TraceValidationResult:
    """Validate Phase 0+ categorical traces and their per-record content hashes."""
    errors: list[str] = []
    record_count = 0
    if not path.exists():
        return TraceValidationResult(path=path, record_count=0, errors=["file missing"])
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
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
            errors.extend(
                f"line {line_number}: schema: {error.message}"
                for error in validator.iter_errors(record)
            )
            for category, required_fields in SELF_LEARNING_TRACE_FIELD_FLOOR.items():
                category_value = record.get(category)
                if not isinstance(category_value, dict):
                    errors.append(f"line {line_number}: {category} must be an object")
                    continue
                for field in required_fields:
                    if field not in category_value:
                        errors.append(f"line {line_number}: missing {category}.{field}")
            integrity = record.get("integrity", {})
            if isinstance(integrity, dict):
                observed_hash = integrity.get("trace_hash")
                unsigned = json.loads(json.dumps(record))
                unsigned.setdefault("integrity", {}).pop("trace_hash", None)
                if observed_hash != stable_hash(unsigned):
                    errors.append(f"line {line_number}: trace hash mismatch")
            else:
                errors.append(f"line {line_number}: integrity must be an object")
    if record_count == 0:
        errors.append("file contains no trace records")
    return TraceValidationResult(path=path, record_count=record_count, errors=errors)

