"""Compile immutable Phase 3 repair ledgers and sealed certification banks."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, git_commit_hash, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.phase3_gauntlet import Phase3WorldCompiler, load_repair_curricula  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner  # noqa: E402


def compile_phase3(run_id: str) -> dict[str, object]:
    implementation_sha = git_commit_hash(REPO_ROOT)
    if implementation_sha is None or len(implementation_sha) != 40:
        raise RuntimeError("Phase 3 requires a resolved implementation Git SHA.")
    compiler = Phase3WorldCompiler()
    root = REPO_ROOT / "results/manifests" / run_id / "phase3"
    root.mkdir(parents=True, exist_ok=True)
    curricula = load_repair_curricula()
    curriculum_manifest = {
        "schema_version": "1.0.0",
        "curricula_count": len(curricula),
        "curriculum_ids": [item.curriculum_id for item in curricula],
        "operations": [item.operation for item in curricula],
        "domains": sorted({item.domain for item in curricula}),
        "curriculum_config_hashes": {
            path.name: file_sha256(path)
            for path in sorted((REPO_ROOT / "configs/repair_curricula").glob("*.yaml"))
        },
        "proposal_synthesis_has_final_access": False,
        "model_training": "none",
    }
    curriculum_manifest["manifest_sha256"] = stable_hash(curriculum_manifest)
    _write_immutable_json(root / "curriculum_manifest.json", curriculum_manifest)
    generations = []
    for generation in (1, 2, 3):
        compiled = compiler.compile_generation(generation)
        directory = root / f"generation_{generation}"
        directory.mkdir(parents=True, exist_ok=True)
        ledger_path = directory / "world_ledger.parquet"
        hidden_path = directory / "hidden_outcomes.json"
        certification_path = directory / "certification_cases.json"
        pq.write_table(
            pa.Table.from_pylist([item.to_dict() for item in compiled.visible]),
            ledger_path,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        _write_immutable_json(hidden_path, {"outcomes": [item.to_dict() for item in compiled.hidden]})
        _write_immutable_json(certification_path, {"cases": [item.to_dict() for item in compiled.certification_cases]})
        body = {
            **compiled.manifest,
            "run_id": run_id,
            "implementation_git_sha": implementation_sha,
            "ledger_sha256": file_sha256(ledger_path),
            "hidden_outcomes_file_sha256": file_sha256(hidden_path),
            "certification_cases_file_sha256": file_sha256(certification_path),
            "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase3.yaml"),
            "curriculum_manifest_sha256": curriculum_manifest["manifest_sha256"],
            "participant_final_access": False,
        }
        signer = ManifestSigner(
            hashlib.sha256(f"phase3:{generation}:{implementation_sha}".encode()).digest(),
            f"phase3-g{generation}",
        )
        generation_manifest = directory / "generation_manifest.json"
        _write_immutable_json(generation_manifest, {"body": body, "signature": signer.sign(body)})
        generations.append(
            {
                "generation": generation,
                "ledger": str(ledger_path.relative_to(REPO_ROOT)),
                "ledger_sha256": body["ledger_sha256"],
                "manifest": str(generation_manifest.relative_to(REPO_ROOT)),
                "manifest_sha256": file_sha256(generation_manifest),
                "opportunities": len(compiled.visible),
                "certification_cases": len(compiled.certification_cases),
            }
        )
    run_manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": 3,
        "implementation_git_sha": implementation_sha,
        "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase3.yaml"),
        "curriculum_manifest_sha256": curriculum_manifest["manifest_sha256"],
        "environment_packages": {"python": platform.python_version(), "pyarrow": pa.__version__},
        "canonical_opportunities": 60000,
        "conditions": ["cumulative", "fresh"],
        "model_training": "none",
        "post_holdout_retuning": False,
        "claim_boundary": "controlled_mechanism_recovery_only",
        "generations": generations,
    }
    run_manifest["manifest_sha256"] = stable_hash(run_manifest)
    _write_immutable_json(root / "run_manifest.json", run_manifest)
    return run_manifest


def _write_immutable_json(path: Path, value: object) -> None:
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"Refusing to overwrite unequal Phase 3 artifact: {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        raise ValueError("run_id must be one safe path component")
    # console.log: phase3.compile.step01.start
    console_log("phase3.compile.step01.start", run_id=args.run_id)
    manifest = compile_phase3(args.run_id)
    # console.log: phase3.compile.step02.complete
    console_log("phase3.compile.step02.complete", implementation_git_sha=manifest["implementation_git_sha"], canonical_opportunities=manifest["canonical_opportunities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
