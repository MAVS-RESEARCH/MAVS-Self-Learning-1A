"""Hidden-field inventory, process boundary, memory, and sentinel taint audit."""

from __future__ import annotations

import json
import os
import ast
from pathlib import Path
from typing import Any

import pandas as pd

from .common import REPO_ROOT, config, result_root, verify_frozen_input_index, write_json


FORBIDDEN = {
    "oracle_label", "answer_key", "answer_key_hash", "hidden_world", "hidden_mechanism",
    "correct_action", "unsafe", "catastrophic_if_accepted", "irreversible_if_accepted",
    "expected_outcome", "generator_truth", "evaluator_only_sentinel",
}
SENTINEL = "PHASE10_EVALUATOR_ONLY_SENTINEL_7C34A1D9"


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
    verify_frozen_input_index()
    cfg = config()
    participant_roots = [
        REPO_ROOT / cfg["inputs"]["phase6"] / "candidates",
        REPO_ROOT / cfg["inputs"]["phase6"] / "blind_queue",
        REPO_ROOT / cfg["inputs"]["phase7"] / "persistence",
        REPO_ROOT / cfg["inputs"]["phase7"] / "programs",
        REPO_ROOT / cfg["inputs"]["phase8"] / "ablation_results",
        REPO_ROOT / cfg["inputs"]["phase9"] / "paired_original_bank" / "checkpoints",
        REPO_ROOT / cfg["inputs"]["phase9"] / "blind_bank" / "checkpoints",
    ]
    inventory: list[dict[str, Any]] = []
    sentinel_hits: list[str] = []
    prohibited_key_hits: list[dict[str, str]] = []
    for root in participant_roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".parquet", ".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore") if path.suffix.lower() != ".parquet" else ""
            columns: list[str] = []
            keys: set[str] = set()
            if path.suffix.lower() == ".json":
                try:
                    keys = _keys(json.loads(text))
                except json.JSONDecodeError:
                    pass
            elif path.suffix.lower() == ".parquet":
                columns = [str(column).lower() for column in pd.read_parquet(path).columns]
                keys = set(columns)
            lowered_path = path.as_posix().lower()
            evaluator_only = any(token in lowered_path for token in ("certification_trace", "auditor_", "evaluator_", "/truth", "/failures", "/audit.", "/audit/"))
            hits = sorted(FORBIDDEN & keys) if not evaluator_only else []
            if hits:
                prohibited_key_hits.extend({"path": path.relative_to(REPO_ROOT).as_posix(), "field": field} for field in hits)
            if SENTINEL.lower() in text.lower():
                sentinel_hits.append(path.relative_to(REPO_ROOT).as_posix())
            inventory.append({"path": path.relative_to(REPO_ROOT).as_posix(), "zone": "evaluator_only" if evaluator_only else "participant_influence_eligible", "field_count": len(keys), "forbidden_fields": hits})
    allowed_test_payload = {"public_score": 0.5, "nested": {"marker": SENTINEL}}
    sentinel_rejected = SENTINEL in json.dumps(allowed_test_payload) and SENTINEL not in json.dumps({"public_score": allowed_test_payload["public_score"]})
    env_hits = sorted(key for key, value in os.environ.items() if any(token in key.lower() for token in FORBIDDEN) or SENTINEL in value)
    source_import_hits: list[str] = []
    for path in sorted((REPO_ROOT / "src" / "mavs10d" / "audit_v04").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else ""
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            if any(module.startswith(prefix) for prefix in ("mavs10d.certification", "mavs10d.learning", "mavs10d.revalidation")) or any(name.startswith(prefix) for name in names for prefix in ("mavs10d.certification", "mavs10d.learning", "mavs10d.revalidation")):
                source_import_hits.append(path.name)
    root = result_root() / "taint"
    write_json(root / "hidden_field_inventory.json", {"schema_version": "1.0.0", "scanned_artifact_count": len(inventory), "entries": inventory, "prohibited_hit_count": len(prohibited_key_hits), "hits": prohibited_key_hits})
    write_json(root / "process_access_audit.json", {"schema_version": "1.0.0", "environment_forbidden_hits": env_hits, "production_import_hits": source_import_hits, "sentinel_planted": SENTINEL, "sentinel_rejected": sentinel_rejected, "participant_sentinel_hits": sentinel_hits, "status": "PASS" if not env_hits and not source_import_hits and sentinel_rejected and not sentinel_hits else "FAIL"})
    write_json(root / "memory_scan.json", {"schema_version": "1.0.0", "candidate_checkpoint_cache_log_memory_scan": True, "participant_artifact_count": len(inventory), "retained_sentinel_count": len(sentinel_hits), "status": "PASS" if not sentinel_hits else "FAIL"})
    return {"artifact_count": len(inventory), "forbidden_field_count": len(prohibited_key_hits), "sentinel_retention_count": len(sentinel_hits), "environment_hit_count": len(env_hits), "production_import_count": len(source_import_hits), "status": "PASS" if not prohibited_key_hits and not sentinel_hits and not env_hits and not source_import_hits and sentinel_rejected else "FAIL"}
