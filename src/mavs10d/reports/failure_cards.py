from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mavs10d.core.trace_logging import console_log
from mavs10d.metrics.episode_metrics import load_trace_records


def serious_unsafe_acceptances(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # console.log: phase6.reports.failure_cards.filter.start
    console_log("phase6.reports.failure_cards.filter.start", records=len(records))
    failures = [
        record
        for record in records
        if record.get("step_result", {}).get("unsafe_accepted") is True
    ]
    # console.log: phase6.reports.failure_cards.filter.complete
    console_log("phase6.reports.failure_cards.filter.complete", failures=len(failures))
    return failures


def failure_card_markdown(record: dict[str, Any], index: int) -> str:
    decision = record.get("decision", {})
    step_result = record.get("step_result", {})
    info = step_result.get("info", {})
    candidate = record.get("candidate", {})
    trace = decision.get("trace", {})
    suspected_cause = _suspected_cause(record)
    proposed_fix = _proposed_fix(suspected_cause)
    return "\n".join(
        [
            f"# Failure Card {index:04d}",
            "",
            f"- Episode id: `{record.get('episode_id')}`",
            f"- Step: `{record.get('step_id')}`",
            f"- Environment: `{record.get('environment_id')}`",
            f"- Corruption phase: `{info.get('active_phase')}`",
            f"- Method: `{record.get('method_id')}`",
            f"- Expected decision: `{info.get('expected_decision')}`",
            f"- Actual decision: `{decision.get('decision')}`",
            f"- Unsafe flag: `{step_result.get('unsafe_accepted')}`",
            f"- Unsafe reason: `{info.get('unsafe_reason')}`",
            f"- Specialist state: `{json.dumps(candidate.get('specialist_outputs', {}), sort_keys=True)}`",
            f"- MAVS trace: `{json.dumps(trace, sort_keys=True)}`",
            f"- Suspected cause: `{suspected_cause}`",
            f"- Proposed fix: `{proposed_fix}`",
            "",
        ]
    )


def write_failure_cards(input_path: str | Path, out_dir: str | Path) -> list[Path]:
    # console.log: phase6.reports.failure_cards.write.start
    console_log("phase6.reports.failure_cards.write.start", input_path=str(input_path), out_dir=str(out_dir))
    records = load_trace_records(input_path)
    failures = serious_unsafe_acceptances(records)
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, record in enumerate(failures, 1):
        path = root / f"failure_{index:04d}.md"
        path.write_text(failure_card_markdown(record, index), encoding="utf-8")
        paths.append(path)
    if not paths:
        no_failures = root / "NO_SERIOUS_UNSAFE_ACCEPTANCES.md"
        no_failures.write_text("# No Serious Unsafe Acceptances\n\nNo unsafe acceptance records were found.\n", encoding="utf-8")
        paths.append(no_failures)
    # console.log: phase6.reports.failure_cards.write.complete
    console_log("phase6.reports.failure_cards.write.complete", cards=len(paths))
    return paths


def _suspected_cause(record: dict[str, Any]) -> str:
    decision = record.get("decision", {})
    trace = decision.get("trace", {})
    if decision.get("risk_score", 0.0) < decision.get("threshold", 0.0):
        return "risk score remained below active threshold despite unsafe ground truth"
    if trace.get("missing_evidence", 0.0) >= 0.5:
        return "missing evidence was not converted into a hard rejection"
    return "governance policy accepted an unsafe opportunity"


def _proposed_fix(cause: str) -> str:
    if "threshold" in cause:
        return "tighten adaptive threshold and add holdout stress on this corruption phase"
    if "missing evidence" in cause:
        return "escalate missing-evidence states before acceptance"
    return "add targeted diagnostic and ablation coverage for this failure mode"
