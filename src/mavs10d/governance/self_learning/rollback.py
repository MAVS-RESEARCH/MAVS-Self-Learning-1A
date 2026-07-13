"""Verified rollback rehearsal, quarantine, restoration, and genealogy evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mavs10d.core.hashing import stable_hash
from mavs10d.governance.self_learning.config_library import CertifiedConfigurationLibrary


@dataclass(frozen=True)
class RollbackResult:
    rollback_id: str
    config_id: str
    rollback_target: str
    library_hash_before: str
    library_hash_after_rollback: str
    library_hash_after_restore: str
    fallback_verified: bool
    protected_replay_passed: bool
    restored_after_rehearsal: bool
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RollbackManager:
    def __init__(self, library: CertifiedConfigurationLibrary) -> None:
        self.library = library

    def rehearse(self, config_id: str, *, protected_replay_passed: bool) -> RollbackResult:
        record = self.library.record(config_id)
        if record.status != "approved" or not record.rollback_target:
            raise ValueError("Rollback rehearsal requires an approved configuration and target.")
        before = self.library.library_hash
        self.library.quarantine(config_id)
        rolled = self.library.rollback(config_id)
        after_rollback = self.library.library_hash
        fallback = self.library.record(rolled.rollback_target or "")
        fallback_verified = fallback.status == "approved"
        restored = self.library.restore_after_rehearsal(config_id)
        after_restore = self.library.library_hash
        passed = fallback_verified and protected_replay_passed and restored.status == "approved"
        payload = {
            "config_id": config_id,
            "target": rolled.rollback_target,
            "before": before,
            "after_rollback": after_rollback,
            "after_restore": after_restore,
        }
        return RollbackResult(
            rollback_id=f"rollback-{stable_hash(payload)[:24]}",
            config_id=config_id,
            rollback_target=str(rolled.rollback_target),
            library_hash_before=before,
            library_hash_after_rollback=after_rollback,
            library_hash_after_restore=after_restore,
            fallback_verified=fallback_verified,
            protected_replay_passed=protected_replay_passed,
            restored_after_rehearsal=restored.status == "approved",
            passed=passed,
        )
