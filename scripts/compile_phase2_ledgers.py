"""Compile immutable Phase 2 corruption ledgers and signed hidden manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256, git_commit_hash, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.phase2_gauntlet import Phase2WorldCompiler  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner  # noqa: E402


def compile_phase2(run_id: str) -> dict[str, object]:
    implementation_sha = git_commit_hash(REPO_ROOT)
    if implementation_sha is None or len(implementation_sha) != 40:
        raise RuntimeError("Phase 2 requires a resolved implementation Git SHA.")
    compiler = Phase2WorldCompiler(REPO_ROOT)
    development = compiler.compile_development()
    root = REPO_ROOT / "results/manifests" / run_id / "phase2"
    root.mkdir(parents=True, exist_ok=True)
    _write_immutable_json(root / "development_manifest.json", {"stage": 0, "final_evaluation_access": False, "manifest": development.manifest})
    generations = []
    for generation in (1, 2, 3):
        bank = compiler.compile_evaluation(generation)
        directory = root / f"generation_{generation}"
        directory.mkdir(parents=True, exist_ok=True)
        ledger_path = directory / "world_ledger.parquet"
        hidden_path = directory / "hidden_outcomes.json"
        pq.write_table(pa.Table.from_pylist([row.to_dict() for row in bank.visible]), ledger_path, compression="zstd", use_dictionary=False, write_statistics=True)
        hidden_payload = {
            "outcomes": [row.to_dict() for row in bank.hidden],
            "specialist_manifests": {world: [asdict(item) for item in items] for world, items in bank.specialist_manifests.items()},
        }
        _write_immutable_json(hidden_path, hidden_payload)
        body = {
            **bank.manifest,
            "stage": 2,
            "run_id": run_id,
            "implementation_git_sha": implementation_sha,
            "ledger_sha256": file_sha256(ledger_path),
            "hidden_outcomes_file_sha256": file_sha256(hidden_path),
            "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase2.yaml"),
            "family_config_sha256": file_sha256(REPO_ROOT / "configs/corruptions/phase2_families.yaml"),
            "composition_config_sha256": file_sha256(REPO_ROOT / "configs/corruptions/phase2_compositions.yaml"),
        }
        signer = ManifestSigner(hashlib.sha256(f"phase2:{generation}:{implementation_sha}".encode()).digest(), f"phase2-g{generation}")
        manifest_path = directory / "generation_manifest.json"
        _write_immutable_json(manifest_path, {"body": body, "signature": signer.sign(body)})
        generations.append({"generation": generation, "ledger": str(ledger_path.relative_to(REPO_ROOT)), "ledger_sha256": body["ledger_sha256"], "manifest": str(manifest_path.relative_to(REPO_ROOT)), "manifest_sha256": file_sha256(manifest_path), "opportunities": len(bank.visible)})
    run_manifest = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": 2,
        "implementation_git_sha": implementation_sha,
        "development_manifest_sha256": development.manifest["manifest_sha256"],
        "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase2.yaml"),
        "family_config_sha256": file_sha256(REPO_ROOT / "configs/corruptions/phase2_families.yaml"),
        "composition_config_sha256": file_sha256(REPO_ROOT / "configs/corruptions/phase2_compositions.yaml"),
        "environment_packages": {"python": platform.python_version(), "pyarrow": pa.__version__},
        "claim_boundary": "phase2_corruption_characterization_no_self_learning_or_frontier_claim",
        "model_training": "none",
        "generations": generations,
    }
    run_manifest["manifest_sha256"] = stable_hash(run_manifest)
    _write_immutable_json(root / "run_manifest.json", run_manifest)
    return run_manifest


def _write_immutable_json(path: Path, value: object) -> None:
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"Refusing to overwrite unequal Phase 2 artifact: {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        raise ValueError("run_id must be one safe path component")
    # console.log: phase2.compile.step01.start
    console_log("phase2.compile.step01.start", run_id=args.run_id)
    manifest = compile_phase2(args.run_id)
    # console.log: phase2.compile.step02.complete
    console_log("phase2.compile.step02.complete", implementation_git_sha=manifest["implementation_git_sha"], canonical_opportunities=sum(item["opportunities"] for item in manifest["generations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
