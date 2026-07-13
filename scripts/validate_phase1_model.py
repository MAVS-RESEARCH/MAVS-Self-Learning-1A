"""Validate the frozen Phase 1 CTTA checkpoint and its blind-separation metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.hashing import file_sha256  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.envs.phase1_gauntlet import Phase1WorldCompiler  # noqa: E402


def main() -> int:
    root = REPO_ROOT / "artifacts/models/phase1_ctta"
    checkpoint = root / "phase1_ctta_source.npz"
    manifest = json.loads((root / "training_manifest.json").read_text(encoding="utf-8"))
    # console.log: phase1.validate_model.step01.start
    console_log("phase1.validate_model.step01.start", checkpoint=str(checkpoint.relative_to(REPO_ROOT)))
    errors = []
    if file_sha256(checkpoint) != manifest["checkpoint_sha256"]:
        errors.append("checkpoint hash mismatch")
    if len(manifest["trials"]) != 15:
        errors.append("expected 15 training grid trials")
    if set(manifest["training_domains"]) & set(manifest["blind_evaluation_domains"]):
        errors.append("training/blind domain overlap")
    if manifest["final_manifest_access"] is not False:
        errors.append("trainer accessed final manifest")
    compiler = Phase1WorldCompiler()
    current_train = compiler.compile_development("train", 1000, worlds_per_domain=5)
    current_validation = compiler.compile_development("validation", 10000, worlds_per_domain=5)
    if manifest["train_manifest"]["manifest_sha256"] != current_train.manifest["manifest_sha256"]:
        errors.append("checkpoint train bank does not reproduce from current source")
    if manifest["validation_manifest"]["manifest_sha256"] != current_validation.manifest["manifest_sha256"]:
        errors.append("checkpoint validation bank does not reproduce from current source")
    # console.log: phase1.validate_model.step02.complete
    console_log("phase1.validate_model.step02.complete", errors=errors, error_count=len(errors), checkpoint_sha256=manifest["checkpoint_sha256"])
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
