"""Validate update-decision schema and content-addressed decision hash."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.contracts import UpdateAction, UpdateDecision  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate_record(payload: dict[str, object]) -> list[str]:
    schema = json.loads((REPO_ROOT / "schemas/update_decision.schema.json").read_text(encoding="utf-8"))
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(payload)]
    if errors:
        return errors
    try:
        decision = UpdateDecision(**{**payload, "action": UpdateAction(str(payload["action"]))})
        decision.validate()
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    # console.log: phase0.validate_updates.step01.start
    console_log("phase0.validate_updates.step01.start", input=str(args.input))
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    errors = validate_record(payload)
    # console.log: phase0.validate_updates.step02.complete
    console_log("phase0.validate_updates.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
