"""Fail-closed Phase 3 synthesis, holdout, adversarial, and visibility separation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.phase3_gauntlet import OPERATION_FEATURES, load_repair_curricula  # noqa: E402


def validate(run_id: str) -> list[str]:
    errors: list[str] = []
    config = yaml.safe_load((REPO_ROOT / "configs/phases/phase3.yaml").read_text(encoding="utf-8"))
    curricula = load_repair_curricula()
    if config["canonical_decisions_per_generation"] != 20000 or config["curricula_count"] != 10 or config["decisions_per_curriculum"] != 2000:
        errors.append("phase3_allocation_config_mismatch")
    if set(config["required_operations"]) != set(OPERATION_FEATURES):
        errors.append("phase3_operation_registry_mismatch")
    synthesis = {item.synthesis_seed for item in curricula}
    holdout = {item.holdout_seed for item in curricula}
    adversarial = {item.adversarial_seed for item in curricula}
    if synthesis & holdout or synthesis & adversarial or holdout & adversarial:
        errors.append("certification_seed_namespaces_overlap")
    if any(900000 <= seed <= 999999 for seed in synthesis | holdout | adversarial):
        errors.append("phase3_consumes_final_blind_seed")
    root = REPO_ROOT / "results/manifests" / run_id / "phase3"
    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest["model_training"] != "none" or run_manifest["post_holdout_retuning"] is not False:
        errors.append("phase3_model_or_retuning_policy_violation")
    opportunity_hashes: set[str] = set()
    world_ranges: list[set[int]] = []
    for generation in (1, 2, 3):
        body = json.loads((root / f"generation_{generation}/generation_manifest.json").read_text(encoding="utf-8"))["body"]
        if body["opportunity_count"] != 20000 or body["world_count"] != 200 or body["curricula_count"] != 10:
            errors.append(f"generation_{generation}_allocation_mismatch")
        if set(body["operations"]) != set(OPERATION_FEATURES):
            errors.append(f"generation_{generation}_operation_coverage")
        if set(body["synthesis_seeds"]) & set(body["holdout_seeds"]) or set(body["synthesis_seeds"]) & set(body["adversarial_seeds"]):
            errors.append(f"generation_{generation}_certification_seed_overlap")
        if body["participant_final_access"] is not False:
            errors.append(f"generation_{generation}_participant_final_access")
        opportunity_hashes.add(body["opportunity_ids_sha256"])
        world_ranges.append(set(range(int(body["world_seed_min"]), int(body["world_seed_max"]) + 1)))
        table = pq.read_table(root / f"generation_{generation}/world_ledger.parquet")
        if any(token in table.column_names for token in ("unsafe", "correct_action", "expected_operation", "hidden_repair_mechanism")):
            errors.append(f"generation_{generation}_hidden_column_exposed")
        visible_text = " ".join(str(value) for row in table.to_pylist()[:100] for value in row.values())
        for curriculum in curricula:
            if curriculum.hidden_mechanism in visible_text:
                errors.append(f"generation_{generation}_hidden_mechanism_exposed:{curriculum.curriculum_id}")
    if len(opportunity_hashes) != 3:
        errors.append("generation_opportunity_identity_reuse")
    if any(world_ranges[left] & world_ranges[right] for left in range(3) for right in range(left + 1, 3)):
        errors.append("generation_world_seed_overlap")
    participant_sources = (
        REPO_ROOT / "src/mavs10d/governance/self_learning/controller.py",
        REPO_ROOT / "src/mavs10d/governance/self_learning/meta_diagnostics.py",
        REPO_ROOT / "src/mavs10d/governance/self_learning/failure_attribution.py",
        REPO_ROOT / "src/mavs10d/governance/self_learning/proposal_engine.py",
        REPO_ROOT / "src/mavs10d/governance/self_learning/selector.py",
    )
    forbidden = ("hidden_outcomes", "certification_cases.json", "hidden_repair_mechanism", "expected_operation", "catastrophic_if_accepted", "feedback_poisoned")
    for path in participant_sources:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                errors.append(f"participant_hidden_access:{path.name}:{token}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase3.separation.step01.start
    console_log("phase3.separation.step01.start", run_id=args.run_id)
    errors = validate(args.run_id)
    # console.log: phase3.separation.step02.complete
    console_log("phase3.separation.step02.complete", errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
