"""Shared fail-closed filesystem and dependency helpers for Phase 7."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from mavs10d.core.hashing import file_sha256, git_commit_hash, stable_hash
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE7_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase7"
PHASE6_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase6" / "phase6_authoritative_reaudit_20260714"


def run_root(run_id: str) -> Path:
    if not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in run_id):
        raise ValueError("Run ID must contain only letters, numbers, hyphens, and underscores.")
    return PHASE7_ROOT / run_id


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_yaml(relative: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / relative).read_text(encoding="utf-8"))


def phase6_dependency() -> dict[str, Any]:
    config = load_yaml("configs/phases/phase7.yaml")["phase6_dependency"]
    seal_path = PHASE6_ROOT / "SEALED"
    seal = yaml.safe_load(seal_path.read_text(encoding="utf-8"))
    audit_path = PHASE6_ROOT / "reports" / "phase6_audit.json"
    audit = read_json(audit_path)
    inventory = pd.read_parquet(PHASE6_ROOT / "reports" / "candidate_inventory.parquet")
    promoted = inventory[inventory["lifecycle"] == "promoted"]
    validated_contracts = []
    for record in promoted.to_dict(orient="records"):
        candidate_path = PHASE6_ROOT / "candidates" / str(record["candidate_id"]) / "candidate.json"
        candidate = ExecutableDiagnostic.from_dict(read_json(candidate_path))
        gate_vector = read_json(candidate_path.parent / "independent_gate_vector.json")
        blind_request = read_json(candidate_path.parent / "blind_request.json")
        validated_contracts.append({
            "candidate_id": candidate.candidate_id,
            "semantic_hash": semantic_hash(candidate),
            "inventory_semantic_hash": str(record["semantic_hash"]),
            "blind_semantic_hash": str(blind_request["anonymous_semantic_id"]),
            "all_gates_passed": bool(gate_vector["all_passed"]),
            "contract_sha256": file_sha256(candidate_path),
        })
    checks = {
        "run_id": seal["run_id"] == config["run_id"],
        "source_commit": seal["source_commit"] == config["source_commit"],
        "audit_sha256": file_sha256(audit_path).upper() == config["audit_sha256"],
        "audit_status": audit["status"] == config["required_audit_status"] == seal["audit_status"],
        "audit_findings": int(audit["finding_count"]) == int(config["required_findings"]) == int(seal["audit_findings"]),
        "promoted_candidates": len(promoted) == 20,
        "promoted_all_gates": bool((promoted["gate_pass_count"] == promoted["gate_count"]).all()),
        "promoted_replay": bool(promoted["replay_passed"].all()),
        "promoted_contracts": len(validated_contracts) == 20 and all(item["semantic_hash"] == item["inventory_semantic_hash"] == item["blind_semantic_hash"] and item["all_gates_passed"] for item in validated_contracts),
        "phase7_previously_executed": not bool(seal["phase7_executed"]),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Sealed Phase 6 dependency check failed: {checks}")
    return {
        "phase6_root": PHASE6_ROOT.relative_to(REPO_ROOT).as_posix(),
        "seal": seal,
        "audit_sha256": file_sha256(audit_path),
        "promoted_candidate_count": len(promoted),
        "validated_contract_count": len(validated_contracts),
        "validated_contracts": validated_contracts,
        "promoted_candidate_ids": sorted(promoted["candidate_id"].astype(str).tolist()),
        "promoted_semantic_hashes": sorted(promoted["semantic_hash"].astype(str).tolist()),
        "checks": checks,
        "passed": True,
    }


def environment_lock() -> dict[str, Any]:
    packages = subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, capture_output=True, text=True).stdout.splitlines()
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": sorted(packages),
        "git_commit": git_commit_hash(REPO_ROOT),
    }


def file_manifest(root: Path, excluded: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = excluded or set()
    return [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": file_sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    ]


def hash_frame(frame: pd.DataFrame) -> str:
    return stable_hash(frame.sort_index(axis=1).to_dict(orient="records"))
