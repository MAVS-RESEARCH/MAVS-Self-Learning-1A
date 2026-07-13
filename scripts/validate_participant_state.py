"""Schema and semantic validation for participant-state checkpoints."""

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

from mavs10d.core.contracts import ParticipantState  # noqa: E402
from mavs10d.core.hashing import stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate_path(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((REPO_ROOT / "schemas/participant_state.schema.json").read_text(encoding="utf-8"))
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(payload)]
    if errors:
        return errors
    try:
        ParticipantState(**payload)
        unsigned = dict(payload)
        observed_hash = unsigned.pop("checkpoint_hash")
        if observed_hash != stable_hash(unsigned):
            errors.append("participant checkpoint hash mismatch")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    # console.log: phase0.validate_participant_state.step01.start
    console_log("phase0.validate_participant_state.step01.start", input=str(args.input))
    errors = validate_path(args.input)
    # console.log: phase0.validate_participant_state.step02.complete
    console_log("phase0.validate_participant_state.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
