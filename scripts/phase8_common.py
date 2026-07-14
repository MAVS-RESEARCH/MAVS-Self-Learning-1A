"""Shared fail-closed filesystem, dependency, and evidence helpers for Phase 8."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE8_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase8"
PHASE7_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase7" / "phase7_authoritative_20260714"
PHASE6_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase6" / "phase6_authoritative_reaudit_20260714"


def run_root(run_id: str) -> Path:
    if not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in run_id):
        raise ValueError("Run ID must contain only letters, numbers, hyphens, and underscores.")
    return PHASE8_ROOT / run_id


def load_yaml(relative: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / relative).read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records), encoding="utf-8")


def write_frame(path: Path, records: list[dict[str, Any]] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = records if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    frame.to_parquet(path, index=False, compression="zstd")


def phase7_dependency() -> dict[str, Any]:
    config = load_yaml("configs/phases/phase8.yaml")["phase7_dependency"]
    seal = yaml.safe_load((PHASE7_ROOT / "SEALED").read_text(encoding="utf-8"))
    audit_path = PHASE7_ROOT / "reports" / "phase7_audit.json"
    audit = read_json(audit_path)
    checks = {
        "run_id": seal["run_id"] == config["run_id"],
        "source_commit": seal["source_commit"] == config["source_commit"],
        "audit_sha256": file_sha256(audit_path).upper() == config["audit_sha256"],
        "audit_status": audit["status"] == config["required_audit_status"] == seal["audit_status"],
        "audit_findings": int(audit["finding_count"]) == int(config["required_findings"]) == int(seal["audit_findings"]),
        "gate_count": len(audit["gates"]) == int(config["required_gate_count"]),
        "family_gate_count": len(audit["family_checks"]) == int(config["required_family_gate_count"]),
        "phase8_previously_executed": not bool(seal["phase8_executed"]),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Sealed Phase 7 dependency check failed: {checks}")
    return {
        "phase7_root": PHASE7_ROOT.relative_to(REPO_ROOT).as_posix(),
        "seal": seal,
        "audit_sha256": file_sha256(audit_path),
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
