"""Compile Phase 1 development metadata, frozen tuning, and evaluation ledgers."""

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
from mavs10d.envs.phase1_gauntlet import Phase1WorldCompiler  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner  # noqa: E402
from mavs10d.training.phase1_tuning import tune_phase1_methods  # noqa: E402


def compile_phase1(run_id: str) -> dict[str, object]:
    implementation_sha = git_commit_hash(REPO_ROOT)
    if implementation_sha is None or len(implementation_sha) != 40:
        raise RuntimeError("Phase 1 requires a resolved implementation Git SHA.")
    compiler = Phase1WorldCompiler()
    train = compiler.compile_development("train", 1000, worlds_per_domain=5)
    validation = compiler.compile_development("validation", 10000, worlds_per_domain=5)
    calibration = compiler.compile_development("calibration", 20000, worlds_per_domain=5)
    tuning = compiler.compile_development("tuning", 30000, worlds_per_domain=5)
    root = REPO_ROOT / "results/manifests" / run_id / "phase1"
    root.mkdir(parents=True, exist_ok=True)
    development = {
        "schema_version": "1.0.0",
        "stage": 0,
        "implementation_git_sha": implementation_sha,
        "banks": {name: bank.manifest for name, bank in (("train", train), ("validation", validation), ("calibration", calibration), ("tuning", tuning))},
        "final_evaluation_access": False,
    }
    development["manifest_sha256"] = stable_hash(development)
    _write_immutable_json(root / "development_banks.json", development)
    selection = tune_phase1_methods(tuning, calibration, REPO_ROOT / "configs/baselines/phase1_dynamic.yaml")
    selection["implementation_git_sha"] = implementation_sha
    selection["development_banks_sha256"] = development["manifest_sha256"]
    selection["selection_sha256"] = stable_hash({key: value for key, value in selection.items() if key != "selection_sha256"})
    _write_immutable_json(root / "selected_configurations.json", selection)
    generations = []
    for generation in (1, 2, 3):
        bank = compiler.compile_evaluation(generation)
        directory = root / f"generation_{generation}"
        directory.mkdir(parents=True, exist_ok=True)
        visible_path = directory / "world_ledger.parquet"
        hidden_path = directory / "hidden_outcomes.json"
        table = pa.Table.from_pylist([row.to_dict() for row in bank.visible])
        pq.write_table(table, visible_path, compression="zstd", use_dictionary=False, write_statistics=True)
        _write_immutable_json(hidden_path, {"outcomes": [row.to_dict() for row in bank.hidden]})
        body = {
            **bank.manifest,
            "stage": 2,
            "run_id": run_id,
            "implementation_git_sha": implementation_sha,
            "ledger_sha256": file_sha256(visible_path),
            "hidden_outcomes_sha256": file_sha256(hidden_path),
            "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase1.yaml"),
            "world_config_sha256": file_sha256(REPO_ROOT / "configs/worlds/phase1_evaluation.yaml"),
            "selection_sha256": selection["selection_sha256"],
        }
        signer = ManifestSigner(hashlib.sha256(f"phase1:{generation}:{implementation_sha}".encode()).digest(), f"phase1-g{generation}")
        envelope = {"body": body, "signature": signer.sign(body)}
        manifest_path = directory / "generation_manifest.json"
        _write_immutable_json(manifest_path, envelope)
        generations.append({"generation": generation, "ledger": str(visible_path.relative_to(REPO_ROOT)), "ledger_sha256": body["ledger_sha256"], "manifest": str(manifest_path.relative_to(REPO_ROOT)), "manifest_sha256": file_sha256(manifest_path), "opportunities": len(bank.visible)})
    run_manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": 1,
        "implementation_git_sha": implementation_sha,
        "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase1.yaml"),
        "suite_config_sha256": file_sha256(REPO_ROOT / "configs/suites/self_learning_300k.yaml"),
        "selection_sha256": selection["selection_sha256"],
        "ctta_checkpoint_sha256": file_sha256(REPO_ROOT / "artifacts/models/phase1_ctta/phase1_ctta_source.npz"),
        "environment_packages": {"python": platform.python_version(), "pyarrow": pa.__version__},
        "claim_boundary": "dynamic_baseline_characterization_no_self_learning_superiority",
        "generations": generations,
    }
    run_manifest["manifest_sha256"] = stable_hash(run_manifest)
    _write_immutable_json(root / "run_manifest.json", run_manifest)
    return run_manifest


def _write_immutable_json(path: Path, value: object) -> None:
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"Refusing to overwrite unequal Phase 1 artifact: {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        raise ValueError("run_id must be one safe path component.")
    # console.log: phase1.compile.step01.validate_arguments
    console_log("phase1.compile.step01.validate_arguments", run_id=args.run_id)
    # console.log: phase1.compile.step02.compile_development_and_evaluation
    console_log("phase1.compile.step02.compile_development_and_evaluation")
    manifest = compile_phase1(args.run_id)
    # console.log: phase1.compile.step03.complete
    console_log("phase1.compile.step03.complete", run_id=args.run_id, implementation_git_sha=manifest["implementation_git_sha"], canonical_opportunities=sum(item["opportunities"] for item in manifest["generations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
