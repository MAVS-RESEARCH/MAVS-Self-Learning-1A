"""Shared filesystem helpers for Phase 6 command processes."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE6_ROOT = REPO_ROOT / "results" / "perception_closure_v04" / "phase6"


def run_root(run_id: str) -> Path:
    if not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in run_id):
        raise ValueError("Run ID must contain only letters, numbers, hyphens, and underscores.")
    return PHASE6_ROOT / run_id


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(relative: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / relative).read_text(encoding="utf-8"))


def load_candidates(root: Path) -> list[ExecutableDiagnostic]:
    return [ExecutableDiagnostic.from_dict(read_json(path)) for path in sorted((root / "candidates").glob("*/candidate.json"))]


def environment_lock() -> dict[str, Any]:
    packages = subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, capture_output=True, text=True).stdout.splitlines()
    return {"python": sys.version, "platform": platform.platform(), "packages": sorted(packages), "git_commit": git_commit_hash(REPO_ROOT)}


def file_manifest(root: Path) -> list[dict[str, Any]]:
    return [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": file_sha256(path)} for path in sorted(root.rglob("*")) if path.is_file()]


def bank_hashes(bank: pd.DataFrame) -> dict[str, str]:
    return {name: stable_hash(group.sort_values("case_id", kind="stable").to_dict(orient="records")) for name, group in bank.groupby("bank", sort=True)}

