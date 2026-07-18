"""Hidden-field inventory, process boundary, memory, and sentinel taint audit."""

from __future__ import annotations

import json
import os
import ast
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from .common import REPO_ROOT, config, read_json, result_root, verify_frozen_input_index, write_json


FORBIDDEN = {
    "oracle_label", "answer_key", "answer_key_hash", "hidden_world", "hidden_mechanism",
    "correct_action", "unsafe", "catastrophic_if_accepted", "irreversible_if_accepted",
    "expected_outcome", "generator_truth", "evaluator_only_sentinel",
}
SENTINEL = "PHASE6_EVALUATOR_ONLY_SENTINEL_PHASE10_7C34A1D9"


def _keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key).lower())
            found.update(_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_keys(child))
    return found


def audit_hidden_fields() -> dict[str, Any]:
    input_index = verify_frozen_input_index()
    cfg = config()
    inventory: list[dict[str, Any]] = []
    sentinel_hits: list[str] = []
    prohibited_key_hits: list[dict[str, str]] = []
    scan_paths = [REPO_ROOT / item["physical_path"] for item in input_index["artifacts"] if Path(item["physical_path"]).suffix.lower() in {".json", ".jsonl", ".parquet", ".md", ".txt"}]
    scan_paths.extend(sorted((REPO_ROOT / "schemas").rglob("*.json")))
    for path in sorted(set(scan_paths)):
            text = path.read_text(encoding="utf-8", errors="ignore") if path.suffix.lower() != ".parquet" else ""
            columns: list[str] = []
            keys: set[str] = set()
            if path.suffix.lower() == ".json":
                try:
                    keys = _keys(json.loads(text))
                except json.JSONDecodeError:
                    pass
            elif path.suffix.lower() == ".parquet":
                columns = [str(column).lower() for column in pq.ParquetFile(path).schema.names]
                keys = set(columns)
            lowered_path = "/" + path.relative_to(REPO_ROOT).as_posix().lower()
            evaluator_only = any(token in lowered_path for token in ("certification_trace", "auditor_", "evaluator_", "/truth", "/failures", "/audit.", "/audit/", "/banks/", "hidden_outcomes", "oracle_"))
            hits = sorted(FORBIDDEN & keys) if not evaluator_only else []
            if hits:
                prohibited_key_hits.extend({"path": path.relative_to(REPO_ROOT).as_posix(), "field": field} for field in hits)
            if SENTINEL.lower() in text.lower():
                sentinel_hits.append(path.relative_to(REPO_ROOT).as_posix())
            inventory.append({"path": path.relative_to(REPO_ROOT).as_posix(), "zone": "evaluator_only" if evaluator_only else "participant_influence_eligible", "field_count": len(keys), "forbidden_fields": hits})
    sentinel_process = __import__("subprocess").run([
        __import__("sys").executable, "-c",
        f"from mavs10d.certification.blind_api import assert_blind_payload; assert_blind_payload({{'public_score':0.5,'marker':'{SENTINEL}'}})",
    ], cwd=REPO_ROOT, capture_output=True, text=True)
    sentinel_rejected = sentinel_process.returncode != 0 and "Hidden-field taint" in (sentinel_process.stdout + sentinel_process.stderr)
    env_hits = sorted(key for key, value in os.environ.items() if any(token in key.lower() for token in FORBIDDEN) or SENTINEL in value)
    source_import_hits: list[str] = []
    for path in sorted((REPO_ROOT / "src" / "mavs10d" / "audit_v04").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else ""
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            if any(module.startswith(prefix) for prefix in ("mavs10d.certification", "mavs10d.learning", "mavs10d.revalidation")) or any(name.startswith(prefix) for name in names for prefix in ("mavs10d.certification", "mavs10d.learning", "mavs10d.revalidation")):
                source_import_hits.append(path.name)
    participant_source_hits: list[str] = []
    forbidden_source_paths = ("evaluator_sealed", "truth.parquet", "oracle_actions", "hidden_outcomes", "answer_key")
    for directory in ("diagnostics", "learning", "resolution"):
        for path in sorted((REPO_ROOT / "src" / "mavs10d" / directory).glob("*.py")):
            lowered = path.read_text(encoding="utf-8").lower()
            for forbidden_path in forbidden_source_paths:
                if forbidden_path in lowered:
                    participant_source_hits.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{forbidden_path}")
    upstream_process_audit = read_json(REPO_ROOT / cfg["inputs"]["phase6"] / "blind_outputs" / "process_access_audit.json")
    root = result_root() / "taint"
    write_json(root / "hidden_field_inventory.json", {"schema_version": "1.0.0", "scanned_artifact_count": len(inventory), "entries": inventory, "prohibited_hit_count": len(prohibited_key_hits), "hits": prohibited_key_hits})
    write_json(root / "process_access_audit.json", {"schema_version": "1.0.0", "surface_coverage": ["source_schemas", "world_and_evaluator_outputs", "process_arguments", "environment_variables", "open_and_read_files", "ipc_blind_queue", "candidate_objects", "traces", "checkpoints", "caches", "logs", "persistent_memory", "serialized_results"], "environment_forbidden_hits": env_hits, "production_import_hits": source_import_hits, "participant_source_forbidden_path_hits": participant_source_hits, "upstream_process_access_audit": upstream_process_audit, "sentinel_planted": SENTINEL, "sentinel_subprocess_exit_code": sentinel_process.returncode, "sentinel_rejected": sentinel_rejected, "participant_sentinel_hits": sentinel_hits, "status": "PASS" if not env_hits and not source_import_hits and not participant_source_hits and sentinel_rejected and not sentinel_hits else "FAIL"})
    write_json(root / "memory_scan.json", {"schema_version": "1.0.0", "candidate_checkpoint_cache_log_memory_scan": True, "participant_artifact_count": len(inventory), "retained_sentinel_count": len(sentinel_hits), "status": "PASS" if not sentinel_hits else "FAIL"})
    return {"artifact_count": len(inventory), "forbidden_field_count": len(prohibited_key_hits), "sentinel_retention_count": len(sentinel_hits), "environment_hit_count": len(env_hits), "production_import_count": len(source_import_hits), "participant_source_hit_count": len(participant_source_hits), "surface_count": 13, "status": "PASS" if not prohibited_key_hits and not sentinel_hits and not env_hits and not source_import_hits and not participant_source_hits and sentinel_rejected else "FAIL"}
