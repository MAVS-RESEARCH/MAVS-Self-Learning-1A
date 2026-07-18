"""Deterministic I/O, hashing, environment, and fail-closed utilities."""

from __future__ import annotations

import hashlib
import json
import locale
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml


SCHEMA_VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "configs" / "phases" / "phase10.yaml"
_GIT_BLOBS: dict[str, str] | None = None


class AuditFailure(RuntimeError):
    """Stable fail-closed audit error."""

    def __init__(self, reason_code: str, detail: str) -> None:
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def result_root() -> Path:
    return REPO_ROOT / config()["results_root"]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def run_git(*args: str, check: bool = True) -> str:
    completed = subprocess.run(["git", *args], cwd=REPO_ROOT, check=check, capture_output=True, text=True)
    return completed.stdout.strip()


def source_commit() -> str:
    return run_git("rev-parse", "HEAD")


def assert_clean_source_tree(allow_phase10_results: bool = True) -> None:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout
    lines = [line for line in status.splitlines() if line.strip()]
    if allow_phase10_results:
        allowed = ("results/perception_closure_v04/phase10/", "results/RESULTS_INDEX.md")
        lines = [line for line in lines if not porcelain_path(line).startswith(allowed)]
    if lines:
        raise AuditFailure("P10_DIRTY_TREE", "; ".join(lines[:20]))


def porcelain_path(line: str) -> str:
    if len(line) >= 4 and line[2] == " ":
        return line[3:].replace("\\", "/")
    return line.lstrip().split(" ", 1)[-1].replace("\\", "/")


def git_blob_oid(path: Path) -> str | None:
    global _GIT_BLOBS
    rel = relative(path)
    if _GIT_BLOBS is None:
        _GIT_BLOBS = {}
        for line in run_git("ls-files", "-s").splitlines():
            metadata, tracked_path = line.split("\t", 1)
            _GIT_BLOBS[tracked_path.replace("\\", "/")] = metadata.split()[1]
    return _GIT_BLOBS.get(rel)


def lfs_oid(path: Path) -> str | None:
    if path.stat().st_size > 512:
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if line.startswith("oid sha256:"):
            return line.split(":", 1)[1]
    return None


def artifact_role(path: Path) -> str:
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    if name in {"sealed", "signed_manifest.json"} or "seal" in name:
        return "seal"
    if "manifest" in name or "manifests" in parts:
        return "manifest"
    if "candidate" in parts or "candidates" in parts or "candidate" in name:
        return "candidate_evidence"
    if "trace" in name or "traces" in parts:
        return "trace"
    if "claim" in name:
        return "claim"
    if "report" in name or "reports" in parts or "integrity" in parts:
        return "audit_evidence"
    if path.suffix.lower() in {".yaml", ".yml"}:
        return "configuration"
    return "result_artifact"


def binding_flags(path: Path) -> dict[str, bool]:
    lowered = relative(path).lower()
    return {
        "code": any(token in lowered for token in ("manifest", "audit", "seal", "report")),
        "config": any(token in lowered for token in ("config", "manifest", "registry")),
        "data": True,
        "seed": any(token in lowered for token in ("seed", "manifest", "generation", "trace", "bank")),
        "environment": any(token in lowered for token in ("environment", "manifest", "seal", "audit")),
    }


def environment_record() -> dict[str, Any]:
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], capture_output=True, text=True, check=True).stdout.splitlines()
    node = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    return {
        "schema_version": SCHEMA_VERSION,
        "python": sys.version,
        "python_executable": sys.executable,
        "node": node,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "locale": locale.setlocale(locale.LC_ALL, None),
        "timezone": os.environ.get("TZ", "OS-configured Asia/Karachi"),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", "0-by-orchestrator"),
        "thread_controls": {key: os.environ.get(key, "1-by-orchestrator") for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        "device": "CPU",
        "nondeterministic_kernel": False,
        "dependencies": sorted(freeze),
        "dependency_lock_sha256": stable_hash(sorted(freeze)),
    }


def all_files(roots: Iterable[Path]) -> list[Path]:
    return sorted((path for root in roots for path in root.rglob("*") if path.is_file()), key=lambda item: relative(item))


def verify_frozen_input_index() -> dict[str, Any]:
    root = result_root()
    index_path = root / "manifests" / "input_artifact_index.json"
    marker = read_json(root / "manifests" / "INPUT_INDEX_FROZEN.json")
    actual_index_hash = file_sha256(index_path)
    if actual_index_hash != marker["input_artifact_index_sha256"]:
        raise AuditFailure("P10_INPUT_INDEX_MUTATION", f"expected {marker['input_artifact_index_sha256']} got {actual_index_hash}")
    index = read_json(index_path)
    mismatches: list[str] = []
    for entry in index["artifacts"]:
        path = REPO_ROOT / entry["physical_path"]
        if not path.is_file() or path.stat().st_size != entry["byte_size"] or file_sha256(path) != entry["sha256"]:
            mismatches.append(entry["physical_path"])
    if mismatches:
        raise AuditFailure("P10_INPUT_ARTIFACT_MISMATCH", "; ".join(mismatches[:20]))
    return index
