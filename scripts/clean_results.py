"""Safely remove generated artifacts only from this repository's results tree."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.trace_logging import console_log


RESULTS_ROOT = (REPO_ROOT / "results").resolve()
ALLOWED_PLACEHOLDERS = {".gitkeep"}


def clean_results(*, run_id: str | None, all_runs: bool) -> list[Path]:
    expected = (REPO_ROOT / "results").resolve()
    if RESULTS_ROOT != expected or RESULTS_ROOT.parent != REPO_ROOT.resolve():
        raise RuntimeError("Refusing cleanup: resolved results root is outside repository.")
    if run_id and (Path(run_id).name != run_id or run_id in {".", ".."}):
        raise ValueError("run_id must be one safe path component.")
    if not all_runs and not run_id:
        raise ValueError("Specify --run-id or --all-runs.")
    removed: list[Path] = []
    if not RESULTS_ROOT.exists():
        return removed
    candidates = list(RESULTS_ROOT.iterdir()) if all_runs else [root / str(run_id) for root in _run_roots()]
    for candidate in candidates:
        resolved = candidate.resolve()
        if RESULTS_ROOT not in resolved.parents:
            raise RuntimeError(f"Refusing cleanup outside results root: {resolved}")
        if not resolved.exists() or resolved.name in ALLOWED_PLACEHOLDERS:
            continue
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()
        removed.append(resolved)
    return removed


def _run_roots() -> tuple[Path, ...]:
    return tuple(RESULTS_ROOT / category for category in ("manifests", "checkpoints", "raw", "processed", "aggregates", "figures", "reports"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--all-runs", action="store_true")
    args = parser.parse_args()
    # console.log: phase0.clean_results.step01.verify_scope
    console_log("phase0.clean_results.step01.verify_scope", results_root=str(RESULTS_ROOT))
    removed = clean_results(run_id=args.run_id, all_runs=args.all_runs)
    if args.all_runs and RESULTS_ROOT.exists():
        unexpected = [
            path for path in RESULTS_ROOT.rglob("*")
            if path.is_file() and path.name not in ALLOWED_PLACEHOLDERS
        ]
        if unexpected:
            raise RuntimeError(f"Result cleaner left generated artifacts: {unexpected}")
    # console.log: phase0.clean_results.step02.complete
    console_log("phase0.clean_results.step02.complete", removed=[str(path) for path in removed])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
