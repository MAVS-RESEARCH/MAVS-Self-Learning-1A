from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_named_cleanup_includes_phase4_aggregate_root() -> None:
    spec = importlib.util.spec_from_file_location("phase4_clean_results", REPO_ROOT / "scripts/clean_results.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_id = "phase4-cleaner-regression-probe"
    created = []
    for category in ("manifests", "raw", "processed", "aggregates", "figures", "reports"):
        directory = REPO_ROOT / "results" / category / run_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "probe.txt").write_text("generated", encoding="utf-8")
        created.append(directory)
    removed = module.clean_results(run_id=run_id, all_runs=False)
    assert {path.parent.name for path in removed} == {"manifests", "raw", "processed", "aggregates", "figures", "reports"}
    assert all(not directory.exists() for directory in created)
