"""Validate signed generation manifests, immutable hashes, and reset disjointness."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner, verify_signed_manifest  # noqa: E402


def validate_run(run_id: str) -> list[str]:
    errors: list[str] = []
    suite_path = REPO_ROOT / "configs/suites/self_learning_300k.yaml"
    phase_path = REPO_ROOT / "configs/phases/phase0.yaml"
    defaults_path = REPO_ROOT / "configs/worlds/generator_defaults.yaml"
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    run_manifest_path = REPO_ROOT / "results/manifests" / run_id / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8")) if run_manifest_path.exists() else {}
    seen_ids: set[str] = set()
    seen_commitments: set[str] = set()
    ledger_hashes: set[str] = set()
    for generation in (1, 2, 3):
        directory = REPO_ROOT / "results/manifests" / run_id / f"generation_{generation}"
        ledger_path = directory / "world_ledger.parquet"
        hidden_path = directory / "hidden_world_manifest.json"
        manifest_path = directory / "generation_manifest.json"
        if not all(path.exists() for path in (ledger_path, hidden_path, manifest_path)):
            errors.append(f"generation {generation}: required artifact missing")
            continue
        suite_seed = int(suite["generation_seed_ranges"][f"generation_{generation}"][0])
        signer = ManifestSigner(
            hashlib.sha256(f"mavs-sl-phase0:{suite_seed}".encode()).digest(),
            f"phase0-generation-{generation}-deterministic",
        )
        try:
            manifest = verify_signed_manifest(manifest_path, signer)
            hidden = verify_signed_manifest(hidden_path, signer)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        table = pq.read_table(ledger_path)
        rows = table.to_pylist()
        ids = [str(row["opportunity_id"]) for row in rows]
        commitments = [str(row["seed_commitment"]) for row in rows]
        expected_configs = {
            "phase0": file_sha256(phase_path),
            "world_defaults": file_sha256(defaults_path),
            "suite": file_sha256(suite_path),
        }
        checks = {
            "opportunity_count": int(manifest["opportunity_count"]) == 5000 == len(rows),
            "partition_budget": manifest["partition_counts"] == {
                "generated_world": 2000,
                "inherited_static": 1000,
                "trace_metric_metamorphic": 2000,
            },
            "ledger_hash": manifest["ledger_sha256"] == file_sha256(ledger_path),
            "hidden_file_hash": manifest["hidden_manifest_sha256"] == file_sha256(hidden_path),
            "hidden_parameter_hash": manifest["hidden_parameters_sha256"] == stable_hash(
                {
                    "opportunities": hidden["opportunities"],
                    "latent_world_parameters": hidden["latent_world_parameters"],
                }
            ),
            "row_order_hash": manifest["row_order_sha256"] == stable_hash(ids),
            "schema_hash": manifest["schema_sha256"] == stable_hash(str(table.schema)),
            "config_hashes": manifest["config_hashes"] == expected_configs,
            "implementation_git_sha": manifest["implementation_git_sha"] == run_manifest.get("implementation_git_sha"),
            "visible_hidden_count": len(hidden["opportunities"]) == len(rows),
        }
        errors.extend(f"generation {generation}: {name} mismatch" for name, passed in checks.items() if not passed)
        inherited_worlds = [
            world for world in hidden["worlds"]
            if world["benchmark_partition"] == "inherited_static"
        ]
        generated_worlds = [
            world for world in hidden["worlds"]
            if world["benchmark_partition"] == "generated_world"
        ]
        if len(inherited_worlds) != 10 or not all(
            str(world["generator_version"]).startswith("chapter10d_static_accuracy_adapter")
            for world in inherited_worlds
        ):
            errors.append(f"generation {generation}: inherited static adapter allocation mismatch")
        if len({world["domain"] for world in generated_worlds}) < 5:
            errors.append(f"generation {generation}: fewer than five generated-world domains")
        latent_by_world = {
            item["world_id"]: item for item in hidden["latent_world_parameters"]
        }
        for world in generated_worlds:
            latent = latent_by_world.get(world["world_id"], {})
            if not (
                0.01 <= float(latent.get("unsafe_prevalence", -1)) <= 0.70
                and 3 <= int(latent.get("specialist_count", -1)) <= 9
                and 1 <= len(latent.get("corruption_families", [])) <= 5
            ):
                errors.append(f"generation {generation}: latent world prior violation for {world['world_id']}")
        overlap_ids = seen_ids.intersection(ids)
        overlap_commitments = seen_commitments.intersection(commitments)
        if overlap_ids:
            errors.append(f"generation {generation}: opportunity IDs overlap prior generation")
        if overlap_commitments:
            errors.append(f"generation {generation}: seed commitments overlap prior generation")
        seen_ids.update(ids)
        seen_commitments.update(commitments)
        ledger_hashes.add(file_sha256(ledger_path))
    if len(ledger_hashes) != 3:
        errors.append("generation ledgers are not independently regenerated")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # console.log: phase0.validate_resets.step01.start
    console_log("phase0.validate_resets.step01.start", run_id=args.run_id)
    errors = validate_run(args.run_id)
    # console.log: phase0.validate_resets.step02.complete
    console_log("phase0.validate_resets.step02.complete", run_id=args.run_id, errors=errors, error_count=len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
