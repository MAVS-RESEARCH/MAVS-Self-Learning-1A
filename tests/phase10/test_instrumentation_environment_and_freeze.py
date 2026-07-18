from __future__ import annotations

import re

from mavs10d.audit_v04.common import REPO_ROOT, canonical_bytes, stable_hash


def test_canonical_json_is_key_order_invariant():
    assert canonical_bytes({"b": 2, "a": 1}) == canonical_bytes({"a": 1, "b": 2})


def test_stable_hash_changes_on_seed_mutation():
    assert stable_hash({"seed": 1}) != stable_hash({"seed": 2})


def test_every_phase10_console_log_has_immediate_comment():
    path = REPO_ROOT / "scripts" / "run_phase10.mjs"
    lines = path.read_text(encoding="utf-8").splitlines()
    indexes = [index for index, line in enumerate(lines) if "console.log(" in line]
    assert len(indexes) == 18
    assert all(index > 0 and lines[index - 1].strip().startswith("// Phase 10 step") for index in indexes)


def test_python_step_logs_have_immediate_comments():
    paths = [path for path in (REPO_ROOT / "scripts").glob("*.py") if "v04" in path.name or "phase10" in path.name]
    assert paths
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if re.search(r"\bprint\(", line):
                assert index > 0 and lines[index - 1].strip().startswith("# Phase 10 step"), (path, index + 1)


def test_release_config_declares_determinism_controls():
    text = (REPO_ROOT / "configs" / "phases" / "phase10.yaml").read_text(encoding="utf-8")
    assert "seed: 1010001" in text and "algorithm: ed25519" in text and "fail_closed: true" in text


def test_cleaner_refuses_sealed_namespace_by_contract():
    text = (REPO_ROOT / "scripts" / "clean_phase10_results.py").read_text(encoding="utf-8")
    assert "P10_RELEASE_FROZEN" in text and 'root / "SEALED"' in text


def test_release_private_key_persistence_is_prohibited():
    text = (REPO_ROOT / "src" / "mavs10d" / "audit_v04" / "release.py").read_text(encoding="utf-8")
    assert "private_key = None" in text
    assert "PrivateFormat" not in text

