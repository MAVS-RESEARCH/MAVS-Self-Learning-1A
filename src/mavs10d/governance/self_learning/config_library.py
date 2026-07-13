"""Certified configuration library and fail-closed lifecycle transitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from mavs10d.core.contracts import ActiveGovernanceConfiguration, GovernanceComponent
from mavs10d.core.hashing import stable_hash
from mavs10d.governance.self_learning.diagnostic_grammar import RepairCandidate


@dataclass(frozen=True)
class ConfigurationRecord:
    config_id: str
    parent_id: str | None
    candidate_id: str | None
    status: str
    version: int
    eta: ActiveGovernanceConfiguration
    candidate: RepairCandidate | None
    certificate_hash: str | None
    rollback_target: str | None
    monitoring_conditions: tuple[str, ...]
    created_sequence: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.candidate is not None:
            payload["candidate"] = self.candidate.to_dict()
        return payload


class CertifiedConfigurationLibrary:
    TRANSITIONS: Mapping[str, frozenset[str]] = {
        "proposed": frozenset({"certified", "rejected", "quarantined"}),
        "certified": frozenset({"shadow", "rejected", "quarantined"}),
        "shadow": frozenset({"approved", "rejected", "quarantined"}),
        "approved": frozenset({"quarantined"}),
        "quarantined": frozenset({"rolled_back"}),
        "rolled_back": frozenset({"approved"}),
        "rejected": frozenset(),
    }

    def __init__(self, base_configuration: ActiveGovernanceConfiguration) -> None:
        base_configuration.validate(require_approved=True)
        self._records: dict[str, ConfigurationRecord] = {
            base_configuration.config_id: ConfigurationRecord(
                config_id=base_configuration.config_id,
                parent_id=base_configuration.parent_config_id,
                candidate_id=None,
                status="approved",
                version=0,
                eta=base_configuration,
                candidate=None,
                certificate_hash="genesis",
                rollback_target=None,
                monitoring_conditions=("selector_fallback", "trace_complete"),
                created_sequence=0,
            )
        }
        self._events: list[dict[str, Any]] = []
        self.base_config_id = base_configuration.config_id

    def register(self, candidate: RepairCandidate) -> ConfigurationRecord:
        if candidate.candidate_id in (item.candidate_id for item in self._records.values()):
            raise ValueError("Candidate already exists in the configuration library.")
        parent = self._records[candidate.parent_id]
        config_id = f"eta-{candidate.candidate_id.removeprefix('candidate-')}"
        eta = _derive_eta(parent.eta, candidate, config_id, "proposed", len(self._records))
        record = ConfigurationRecord(
            config_id=config_id,
            parent_id=parent.config_id,
            candidate_id=candidate.candidate_id,
            status="proposed",
            version=parent.version + 1,
            eta=eta,
            candidate=candidate,
            certificate_hash=None,
            rollback_target=candidate.rollback_target,
            monitoring_conditions=("protected_regression", "scope_leakage", "selector_uncertainty", "recurrence"),
            created_sequence=len(self._records),
        )
        self._records[config_id] = record
        self._event("register", config_id, "proposed")
        return record

    def certify(self, config_id: str, certificate_hash: str) -> ConfigurationRecord:
        return self._transition(config_id, "certified", certificate_hash=certificate_hash)

    def begin_shadow(self, config_id: str) -> ConfigurationRecord:
        return self._transition(config_id, "shadow")

    def promote(self, config_id: str) -> ConfigurationRecord:
        record = self._transition(config_id, "approved")
        record.eta.validate(require_approved=True)
        return record

    def reject(self, config_id: str) -> ConfigurationRecord:
        return self._transition(config_id, "rejected")

    def quarantine(self, config_id: str) -> ConfigurationRecord:
        return self._transition(config_id, "quarantined")

    def rollback(self, config_id: str) -> ConfigurationRecord:
        record = self._records[config_id]
        if not record.rollback_target or record.rollback_target not in self._records:
            raise ValueError("Rollback target is absent from the certified library.")
        target = self._records[record.rollback_target]
        if target.status != "approved":
            raise ValueError("Rollback target must remain approved.")
        return self._transition(config_id, "rolled_back")

    def restore_after_rehearsal(self, config_id: str) -> ConfigurationRecord:
        record = self._records[config_id]
        if not record.certificate_hash:
            raise ValueError("A rolled-back configuration cannot be restored without its certificate.")
        return self._transition(config_id, "approved")

    def record(self, config_id: str) -> ConfigurationRecord:
        return self._records[config_id]

    def approved(self) -> tuple[ConfigurationRecord, ...]:
        return tuple(item for item in self._records.values() if item.status == "approved")

    def all(self) -> tuple[ConfigurationRecord, ...]:
        return tuple(self._records.values())

    def events(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    @property
    def library_hash(self) -> str:
        return stable_hash({"records": [item.to_dict() for item in self._records.values()], "events": self._events})

    def _transition(self, config_id: str, target: str, *, certificate_hash: str | None = None) -> ConfigurationRecord:
        current = self._records[config_id]
        if target not in self.TRANSITIONS.get(current.status, frozenset()):
            raise ValueError(f"Illegal configuration transition {current.status} -> {target}.")
        status = "approved" if target == "approved" else ("rolled_back" if target == "rolled_back" else ("quarantined" if target == "quarantined" else "proposed"))
        eta = _change_eta_status(current.eta, status)
        updated = replace(current, status=target, eta=eta, certificate_hash=certificate_hash or current.certificate_hash)
        self._records[config_id] = updated
        self._event(current.status, config_id, target)
        return updated

    def _event(self, source: str, config_id: str, target: str) -> None:
        payload = {"sequence": len(self._events), "source": source, "config_id": config_id, "target": target}
        self._events.append({**payload, "event_hash": stable_hash(payload)})


def _derive_eta(
    parent: ActiveGovernanceConfiguration,
    candidate: RepairCandidate,
    config_id: str,
    approval_status: str,
    version: int,
) -> ActiveGovernanceConfiguration:
    graph_value = {
        "parent_graph": parent.G_t.value,
        "candidate_id": candidate.candidate_id,
        "operation": candidate.operation.value,
        "expression": candidate.exact_function.to_dict(),
    }
    graph = GovernanceComponent(
        symbol=parent.G_t.symbol,
        semantic_name=parent.G_t.semantic_name,
        definition=parent.G_t.definition,
        value_type="serializable_governance_graph",
        value=graph_value,
        bounds={"unrestricted_code": False, "max_mitigation": 0.12},
    )
    provisional = replace(
        parent,
        config_id=config_id,
        parent_config_id=parent.config_id,
        version=f"phase3.{version}",
        approval_status=approval_status,
        activation_scope=dict(candidate.intended_scope),
        G_t=graph,
        config_hash="",
    )
    return replace(provisional, config_hash=provisional.expected_hash())


def _change_eta_status(eta: ActiveGovernanceConfiguration, status: str) -> ActiveGovernanceConfiguration:
    provisional = replace(eta, approval_status=status, config_hash="")
    return replace(provisional, config_hash=provisional.expected_hash())
