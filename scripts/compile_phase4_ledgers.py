"""Compile immutable Phase 4 ledgers, hidden outcomes, and frozen sweep registry."""

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
sys.path.insert(0, str(REPO_ROOT / "src"))

from mavs10d.baselines.phase4_registry import registry_manifest  # noqa: E402
from mavs10d.core.hashing import file_sha256, git_commit_hash, stable_hash  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.phase4_tournament import Phase4TournamentCompiler  # noqa: E402
from mavs10d.envs.world_ledger import ManifestSigner  # noqa: E402


def compile_phase4(run_id: str) -> dict[str, object]:
    implementation_sha = git_commit_hash(REPO_ROOT)
    if implementation_sha is None or len(implementation_sha) != 40:
        raise RuntimeError("Phase 4 requires a resolved implementation Git SHA.")
    root = REPO_ROOT / "results/manifests" / run_id / "phase4"
    root.mkdir(parents=True, exist_ok=True)
    registry = registry_manifest()
    _write_immutable_json(root / "operating_points.json", registry)
    compiler = Phase4TournamentCompiler()
    generations: list[dict[str, object]] = []
    for generation in (1, 2, 3):
        compiled = compiler.compile_generation(generation)
        directory = root / f"generation_{generation}"
        directory.mkdir(parents=True, exist_ok=True)
        ledger_path = directory / "world_ledger.parquet"
        hidden_path = directory / "hidden_outcomes.json"
        pq.write_table(pa.Table.from_pylist(list(compiled.visible_rows)), ledger_path, compression="zstd", use_dictionary=True, write_statistics=True)
        _write_immutable_json(hidden_path, {"outcomes": list(compiled.hidden_rows)})
        body = {
            **compiled.manifest, "run_id": run_id, "implementation_git_sha": implementation_sha,
            "ledger_sha256": file_sha256(ledger_path), "hidden_outcomes_file_sha256": file_sha256(hidden_path),
            "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase4.yaml"),
            "sweep_config_sha256": file_sha256(REPO_ROOT / "configs/baselines/phase4_sweeps.yaml"),
            "operating_point_registry_sha256": registry["registry_hash"],
        }
        signer = ManifestSigner(hashlib.sha256(f"phase4:{generation}:{implementation_sha}".encode()).digest(), f"phase4-g{generation}")
        manifest_path = directory / "generation_manifest.json"
        _write_immutable_json(manifest_path, {"body": body, "signature": signer.sign(body)})
        generations.append({
            "generation": generation, "ledger": str(ledger_path.relative_to(REPO_ROOT)),
            "ledger_sha256": body["ledger_sha256"], "hidden": str(hidden_path.relative_to(REPO_ROOT)),
            "hidden_sha256": body["hidden_outcomes_file_sha256"], "manifest": str(manifest_path.relative_to(REPO_ROOT)),
            "manifest_sha256": file_sha256(manifest_path), "worlds": 500, "opportunities": 25000,
        })
    run_manifest: dict[str, object] = {
        "schema_version": "1.0.0", "run_id": run_id, "phase": 4,
        "implementation_git_sha": implementation_sha,
        "phase_config_sha256": file_sha256(REPO_ROOT / "configs/phases/phase4.yaml"),
        "sweep_config_sha256": file_sha256(REPO_ROOT / "configs/baselines/phase4_sweeps.yaml"),
        "operating_point_registry_sha256": registry["registry_hash"],
        "operating_point_count": len(registry["points"]), "canonical_opportunities": 75000,
        "replay_evaluations": 75000 * len(registry["points"]), "replay_counts_as_canonical": False,
        "environment_packages": {"python": platform.python_version(), "pyarrow": pa.__version__},
        "model_training": "none", "post_holdout_retuning": False, "selection_final_access": False,
        "claim_boundary": "complete_matched_tournament_only", "generations": generations,
    }
    run_manifest["manifest_sha256"] = stable_hash(run_manifest)
    _write_immutable_json(root / "run_manifest.json", run_manifest)
    return run_manifest


def _write_immutable_json(path: Path, value: object) -> None:
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"Refusing to overwrite unequal Phase 4 artifact: {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        raise ValueError("run_id must be one safe path component")
    # console.log: phase4.compile.step01.start
    console_log("phase4.compile.step01.start", run_id=args.run_id)
    manifest = compile_phase4(args.run_id)
    # console.log: phase4.compile.step02.complete
    console_log("phase4.compile.step02.complete", operating_points=manifest["operating_point_count"], canonical_opportunities=manifest["canonical_opportunities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
