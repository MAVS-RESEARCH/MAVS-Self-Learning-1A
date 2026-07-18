"""Shared fail-closed Phase 9 filesystem and evidence helpers."""

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
PHASE9_ROOT = REPO_ROOT / "results/perception_closure_v04/phase9"
PHASE6_ROOT = REPO_ROOT / "results/perception_closure_v04/phase6/phase6_authoritative_reaudit_20260714"
PHASE7_ROOT = REPO_ROOT / "results/perception_closure_v04/phase7/phase7_authoritative_20260714"
PHASE8_ROOT = REPO_ROOT / "results/perception_closure_v04/phase8/phase8_authoritative_20260714"


def track_root(track_id: str) -> Path:
    if track_id not in {"paired_original_bank", "blind_bank"}:
        raise ValueError(f"Invalid Phase 9 track: {track_id}")
    return PHASE9_ROOT / track_id


def load_yaml(relative: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / relative).read_text(encoding="utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_frame(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression="zstd")


def dependency_lock() -> dict[str, Any]:
    phase = load_yaml("configs/phases/phase9.yaml")
    audit_path = PHASE8_ROOT / "reports/phase8_audit.json"
    audit = read_json(audit_path)
    seal = yaml.safe_load((PHASE8_ROOT / "SEALED").read_text(encoding="utf-8"))
    checks = {
        "phase6_sealed": (PHASE6_ROOT / "SEALED").exists(),
        "phase7_sealed": (PHASE7_ROOT / "SEALED").exists(),
        "phase8_sealed": (PHASE8_ROOT / "SEALED").exists(),
        "phase8_audit_hash": file_sha256(audit_path).upper() == phase["dependencies"]["phase8_audit_sha256"],
        "phase8_audit_pass": audit["status"] == phase["dependencies"]["phase8_required_status"],
        "phase8_zero_findings": int(audit["finding_count"]) == int(phase["dependencies"]["phase8_required_findings"]),
        "phase9_not_previously_executed": not bool(seal.get("phase9_executed", False)),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Phase 9 dependency lock failed: {checks}")
    return {"checks": checks, "phase8_audit_sha256": file_sha256(audit_path), "passed": True}


def environment_lock() -> dict[str, Any]:
    packages = subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, capture_output=True, text=True).stdout.splitlines()
    return {"python": sys.version, "platform": platform.platform(), "packages": sorted(packages), "git_commit": git_commit_hash(REPO_ROOT)}


def file_manifest(root: Path, excluded: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = excluded or set()
    return [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": file_sha256(path)}
        for path in sorted(root.rglob("*")) if path.is_file() and path.relative_to(root).as_posix() not in excluded
    ]


def frame_hash(frame: pd.DataFrame) -> str:
    return stable_hash(frame.sort_values(list(frame.columns[:1])).sort_index(axis=1).to_dict(orient="records"))

