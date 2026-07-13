"""Validate adaptive/fixed Phase 1 participant-state boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.baselines.phase1_registry import ADAPTIVE_METHODS, expected_method_conditions  # noqa: E402
from mavs10d.core.hashing import stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    for generation in (1, 2, 3):
        path = REPO_ROOT / "results/checkpoints" / run_id / "phase1" / f"generation_{generation}/adaptive_baselines.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        states = payload["states"]
        expected = {f"{method}:{condition}" for method, condition in expected_method_conditions(generation)}
        if set(states) != expected:
            errors.append(f"generation {generation}: checkpoint method matrix mismatch")
        for key, state in states.items():
            observed_hash = state["state_sha256"]
            unsigned = {name: value for name, value in state.items() if name != "state_sha256"}
            if observed_hash != stable_hash(unsigned):
                errors.append(f"generation {generation}: state hash mismatch for {key}")
            method_name, condition = key.split(":", 1)
            if method_name in ADAPTIVE_METHODS and state["adaptive"] is not True:
                errors.append(f"generation {generation}: adaptive marker missing for {key}")
            if condition == "fixed" and state["adaptive"] is not False:
                errors.append(f"generation {generation}: fixed method retained adaptive state for {key}")
            serialized = json.dumps(state, sort_keys=True)
            for forbidden in ('"hidden_label"', '"future_manifest"', '"answer_key"', '"final_metric"'):
                if forbidden in serialized:
                    errors.append(f"generation {generation}: forbidden state {forbidden} in {key}")
            for event in state.get("feedback_history", []):
                if int(event["release_step"]) < int(event["origin_step"]):
                    errors.append(f"generation {generation}: feedback chronology invalid in {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase1.validate_checkpoints.step01.start
    console_log("phase1.validate_checkpoints.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase1.validate_checkpoints.step02.complete
    console_log("phase1.validate_checkpoints.step02.complete", errors=errors, error_count=len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
