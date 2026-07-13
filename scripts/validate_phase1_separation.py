"""Fail-closed Phase 1 development/calibration/evaluation separation audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log  # noqa: E402


def validate(run_id: str) -> list[str]:
    root = REPO_ROOT / "results/manifests" / run_id / "phase1"
    development = json.loads((root / "development_banks.json").read_text(encoding="utf-8"))
    selection = json.loads((root / "selected_configurations.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    banks = development["banks"]
    names = tuple(banks)
    for index, left_name in enumerate(names):
        left = banks[left_name]
        for right_name in names[index + 1 :]:
            right = banks[right_name]
            if not (left["seed_max"] < right["seed_min"] or right["seed_max"] < left["seed_min"]):
                errors.append(f"development seed overlap: {left_name}/{right_name}")
            if left["opportunity_ids_sha256"] == right["opportunity_ids_sha256"]:
                errors.append(f"development opportunity identity overlap: {left_name}/{right_name}")
    development_domains = set(banks["train"]["domains"])
    evaluation_ids: set[str] = set()
    for generation in (1, 2, 3):
        manifest = json.loads((root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        if development_domains & set(manifest["domains"]):
            errors.append(f"generation {generation}: development/evaluation domain overlap")
        if manifest["stage"] <= selection["selection_stage"]:
            errors.append(f"generation {generation}: evaluation was not frozen after selection")
        if manifest["opportunity_ids_sha256"] in evaluation_ids:
            errors.append(f"generation {generation}: reused opportunity identities")
        evaluation_ids.add(manifest["opportunity_ids_sha256"])
        if manifest["selection_sha256"] != selection["selection_sha256"]:
            errors.append(f"generation {generation}: selection hash mismatch")
    if selection["post_holdout_retuning"] is not False:
        errors.append("post-holdout retuning prohibition is not enforced")
    training = json.loads((REPO_ROOT / "artifacts/models/phase1_ctta/training_manifest.json").read_text(encoding="utf-8"))
    if set(training["training_domains"]) & set(training["blind_evaluation_domains"]):
        errors.append("CTTA training and blind evaluation domains overlap")
    if training["final_manifest_access"] is not False:
        errors.append("CTTA trainer recorded final-manifest access")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase1.separation.step01.start
    console_log("phase1.separation.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase1.separation.step02.complete
    console_log("phase1.separation.step02.complete", errors=errors, error_count=len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
