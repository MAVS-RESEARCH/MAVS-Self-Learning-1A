"""Validate Phase 2 development/evaluation and cross-generation separation."""

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
    root = REPO_ROOT / "results/manifests" / run_id / "phase2"
    development = json.loads((root / "development_manifest.json").read_text(encoding="utf-8"))["manifest"]
    errors: list[str] = []
    evaluation_ids: set[str] = set()
    evaluation_worlds: set[str] = set()
    for generation in (1, 2, 3):
        body = json.loads((root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        if set(development["domains"]) & set(body["domains"]):
            errors.append(f"generation {generation}: development/evaluation domain overlap")
        if not (development["seed_max"] < body["seed_min"] or body["seed_max"] < development["seed_min"]):
            errors.append(f"generation {generation}: development/evaluation seed overlap")
        if body["opportunity_ids_sha256"] in evaluation_ids:
            errors.append(f"generation {generation}: evaluation opportunity identities reused")
        if body["world_ids_sha256"] in evaluation_worlds:
            errors.append(f"generation {generation}: evaluation world identities reused")
        evaluation_ids.add(body["opportunity_ids_sha256"])
        evaluation_worlds.add(body["world_ids_sha256"])
        if body["stage"] <= 0:
            errors.append(f"generation {generation}: evaluation stage not sealed after development")
        if body["composition_count"] < 40 or len(body["corruption_families"]) < 10:
            errors.append(f"generation {generation}: evaluation family/composition floor failed")
        if set(body["held_out_mechanisms"]) != {"feedback_poisoning", "evidence_source_compromise"}:
            errors.append(f"generation {generation}: held-out mechanisms missing")
    if development["held_out_mechanisms"]:
        errors.append("development manifest contains held-out mechanisms")
    if development["namespace"] == "phase2_eval_g1_v1":
        errors.append("development and evaluation namespaces overlap")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase2.separation.step01.start
    console_log("phase2.separation.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase2.separation.step02.complete
    console_log("phase2.separation.step02.complete", errors=errors, error_count=len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
