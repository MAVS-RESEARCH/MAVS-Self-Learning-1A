"""Compile signed immutable Phase 0 ledgers for one or all generations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, git_commit_hash, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.world_compiler import InheritedStaticCompiler, RandomizedWorldCompiler  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner, write_generation_ledger  # noqa: E402


def compile_generation(run_id: str, generation: int, implementation_git_sha: str) -> dict[str, object]:
    phase_path = REPO_ROOT / "configs" / "phases" / "phase0.yaml"
    world_path = REPO_ROOT / "configs" / "worlds" / "generator_defaults.yaml"
    suite_path = REPO_ROOT / "configs" / "suites" / "self_learning_300k.yaml"
    phase = yaml.safe_load(phase_path.read_text(encoding="utf-8"))
    defaults = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    suite_seed = int(suite["generation_seed_ranges"][f"generation_{generation}"][0])
    compiler = RandomizedWorldCompiler(suite_seed, defaults)
    inherited_compiler = InheritedStaticCompiler(suite_seed, defaults)
    partitions = []
    world_offset = 0
    for partition, decisions in phase["allocations"].items():
        selected_compiler = inherited_compiler if partition == "inherited_static" else compiler
        compiled = selected_compiler.compile_partition(
            generation=generation,
            partition=str(partition),
            decisions=int(decisions),
            world_offset=world_offset,
        )
        partitions.append((str(partition), compiled))
        world_offset += len(compiled.worlds)
    signing_key = hashlib.sha256(f"mavs-sl-phase0:{suite_seed}".encode()).digest()
    signer = ManifestSigner(signing_key, f"phase0-generation-{generation}-deterministic")
    generator_hash = stable_hash(
        {
            "world_compiler": file_sha256(REPO_ROOT / "src/mavs10d/envs/world_compiler.py"),
            "world_ledger": file_sha256(REPO_ROOT / "src/mavs10d/envs/world_ledger.py"),
        }
    )
    artifacts = write_generation_ledger(
        output_directory=REPO_ROOT / "results" / "manifests" / run_id / f"generation_{generation}",
        generation=generation,
        partitions=partitions,
        config_hashes={
            "phase0": file_sha256(phase_path),
            "world_defaults": file_sha256(world_path),
            "suite": file_sha256(suite_path),
        },
        generator_package_hash=generator_hash,
        implementation_git_sha=implementation_git_sha,
        signer=signer,
    )
    checkpoint_directory = REPO_ROOT / "results/checkpoints" / run_id / f"generation_{generation}"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_directory / "phase0_diagnostic_bound.json"
    checkpoint_body = {
        "participant_id": "phase0_diagnostic_bound",
        "condition": "diagnostic_bound",
        "generation": generation,
        "persistence_eligible": False,
        "retained_bytes": 0,
        "component_hashes": {},
        "forbidden_state_audit": {
            "no_raw_hidden_labels": True,
            "no_future_manifests": True,
            "no_answer_keys": True,
            "no_final_metrics": True,
            "no_unapproved_configuration": True,
        },
        "prior_library_hash": None,
    }
    checkpoint_body["checkpoint_hash"] = stable_hash(checkpoint_body)
    checkpoint_content = json.dumps(checkpoint_body, indent=2, sort_keys=True) + "\n"
    if checkpoint_path.exists() and checkpoint_path.read_text(encoding="utf-8") != checkpoint_content:
        raise FileExistsError(f"Refusing to overwrite checkpoint: {checkpoint_path}")
    checkpoint_path.write_text(checkpoint_content, encoding="utf-8", newline="\n")
    return {
        "generation": generation,
        "ledger": str(artifacts.ledger_path.relative_to(REPO_ROOT)),
        "manifest": str(artifacts.manifest_path.relative_to(REPO_ROOT)),
        "ledger_sha256": artifacts.ledger_sha256,
        "manifest_sha256": artifacts.manifest_sha256,
        "opportunity_count": artifacts.opportunity_count,
        "participant_checkpoint": str(checkpoint_path.relative_to(REPO_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generation", choices=("1", "2", "3", "all"), default="all")
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        raise ValueError("run_id must be one safe path component.")
    generations = (1, 2, 3) if args.generation == "all" else (int(args.generation),)
    # console.log: phase0.compile_ledgers.step01.load_and_validate_arguments
    console_log("phase0.compile_ledgers.step01.load_and_validate_arguments", run_id=args.run_id, generations=generations)
    implementation_git_sha = git_commit_hash(REPO_ROOT)
    if len(implementation_git_sha) != 40:
        raise RuntimeError("Phase 0 requires a resolved 40-character implementation Git SHA.")
    generation_results = []
    for generation in generations:
        # console.log: phase0.compile_ledgers.step02.compile_generation
        console_log("phase0.compile_ledgers.step02.compile_generation", generation=generation)
        result = compile_generation(args.run_id, generation, implementation_git_sha)
        generation_results.append(result)
        # console.log: phase0.compile_ledgers.step03.generation_complete
        console_log("phase0.compile_ledgers.step03.generation_complete", **result)
    run_manifest_path = REPO_ROOT / "results/manifests" / args.run_id / "run_manifest.json"
    run_manifest = {
        "schema_version": "1.0.0",
        "run_id": args.run_id,
        "phase": 0,
        "implementation_git_sha": implementation_git_sha,
        "upstream_git_sha": "a1bfd52b59aaba69b2c041a5e7da0ee263125c1f",
        "claim_boundary": "infrastructure_only_no_self_learning_superiority_claim",
        "generations": generation_results,
        "logical_artifacts": {
            "generation_ledgers": [item["ledger"] for item in generation_results],
            "generation_manifests": [item["manifest"] for item in generation_results],
            "participant_checkpoints": [item["participant_checkpoint"] for item in generation_results],
        },
    }
    run_manifest["manifest_hash"] = stable_hash(run_manifest)
    run_manifest_content = json.dumps(run_manifest, indent=2, sort_keys=True) + "\n"
    if run_manifest_path.exists() and run_manifest_path.read_text(encoding="utf-8") != run_manifest_content:
        raise FileExistsError(f"Refusing to overwrite run manifest: {run_manifest_path}")
    run_manifest_path.write_text(run_manifest_content, encoding="utf-8", newline="\n")
    # console.log: phase0.compile_ledgers.step04.write_run_manifest
    console_log("phase0.compile_ledgers.step04.write_run_manifest", path=str(run_manifest_path.relative_to(REPO_ROOT)), manifest_hash=run_manifest["manifest_hash"])
    # console.log: phase0.compile_ledgers.step05.complete
    console_log("phase0.compile_ledgers.step05.complete", run_id=args.run_id, generation_count=len(generations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
