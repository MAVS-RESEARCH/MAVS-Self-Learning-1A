"""Typed, serializable contracts for the Self-Learning MAVS experiment boundary.

These types deliberately separate visible participant inputs from evaluator-only
state. They are data contracts, not performance implementations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Literal, Mapping

from mavs10d.core.hashing import stable_hash


class ContractError(ValueError):
    """Raised when an experiment contract violates a declared invariant."""


class UpdateAction(StrEnum):
    PROMOTE = "promote"
    REJECT = "reject"
    QUARANTINE = "quarantine"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class SeedTuple:
    suite: int
    generation: int
    world: int
    episode: int
    step: int
    method: int

    def __post_init__(self) -> None:
        if min(asdict(self).values()) < 0:
            raise ContractError("Seed tuple components must be non-negative.")


@dataclass(frozen=True)
class WorldSpec:
    world_id: str
    generator_version: str
    domain: str
    horizon: int
    label_process: Mapping[str, Any]
    transition_kernel: Mapping[str, Any]
    observability: Mapping[str, Any]
    feedback: Mapping[str, Any]
    corruption_generator: Mapping[str, Any]
    policy_version_process: Mapping[str, Any]
    visible_projection: tuple[str, ...]
    hidden_state_hash: str
    seed_tuple: SeedTuple

    def __post_init__(self) -> None:
        if not 80 <= self.horizon <= 320:
            raise ContractError("World horizon must be within [80, 320].")
        if len(self.hidden_state_hash) != 64:
            raise ContractError("hidden_state_hash must be a SHA-256 hex digest.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VisibleOpportunity:
    opportunity_id: str
    world_id: str
    episode_id: str
    step: int
    domain: str
    visible_regime_features: Mapping[str, Any]
    policy_version: str
    observation: Mapping[str, Any]
    seed_commitment: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LearningEvent:
    event_id: str
    trigger: str
    trace_ids: tuple[str, ...]
    attributed_mechanism: str
    candidate_operations: tuple[str, ...]
    evidence_sufficient: bool
    feedback_provenance: str
    feedback_reliability: float

    def __post_init__(self) -> None:
        _unit_interval("feedback_reliability", self.feedback_reliability)


@dataclass(frozen=True)
class DiagnosticProposal:
    proposal_id: str
    name: str
    intended_scope: Mapping[str, Any]
    bounded_function: Mapping[str, Any]
    threshold: float
    allowed_influence: Mapping[str, float]
    invariants: tuple[str, ...]
    lineage: tuple[str, ...]
    provenance: Mapping[str, Any]
    validation_plan: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.invariants:
            raise ContractError("A diagnostic proposal requires named invariants.")
        for name, value in self.allowed_influence.items():
            if value < 0:
                raise ContractError(f"Allowed influence {name} must be non-negative.")


@dataclass(frozen=True)
class CandidateConfiguration:
    candidate_id: str
    parent_id: str
    exact_delta: Mapping[str, Any]
    proposal_bundle: tuple[str, ...]
    expected_gains: Mapping[str, float]
    expected_failures: tuple[str, ...]
    protected_metrics: tuple[str, ...]
    protected_families: tuple[str, ...]
    rollback_target: str

    def __post_init__(self) -> None:
        if not self.parent_id or not self.rollback_target:
            raise ContractError("Candidate configuration requires parent and rollback IDs.")


@dataclass(frozen=True)
class CertificationReport:
    report_id: str
    candidate_id: str
    trigger_replay: Mapping[str, Any]
    retained_replay: Mapping[str, Any]
    disjoint_temporal_holdout: Mapping[str, Any]
    boundary_counterfactual_tests: Mapping[str, Any]
    independent_adversarial_search: Mapping[str, Any]
    scope_audit: Mapping[str, Any]
    invariant_audit: Mapping[str, Any]
    shadow_results: Mapping[str, Any]
    pareto_deltas: Mapping[str, float]
    compute: Mapping[str, float]
    artifact_hashes: Mapping[str, str]
    passed: bool
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.reason_codes:
            raise ContractError("Certification report requires explicit reason codes.")


@dataclass(frozen=True)
class UpdateDecision:
    update_id: str
    candidate_id: str
    action: UpdateAction
    reason_codes: tuple[str, ...]
    activation_scope: Mapping[str, Any]
    fallback_configuration: str
    monitoring_conditions: tuple[str, ...]
    effective_time: str
    signer: str
    certification_report_hash: str
    decision_hash: str = field(default="")

    def unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("decision_hash", None)
        payload["action"] = self.action.value
        return payload

    def expected_hash(self) -> str:
        return stable_hash(self.unsigned_payload())

    def validate(self) -> None:
        if not self.reason_codes:
            raise ContractError("Update decision requires exact reason codes.")
        if not self.fallback_configuration:
            raise ContractError("Update decision requires a fallback configuration.")
        if self.decision_hash != self.expected_hash():
            raise ContractError("Update decision hash mismatch.")


@dataclass(frozen=True)
class ParticipantState:
    participant_id: str
    condition: str
    generation: int
    persistence_eligible: bool
    checkpoint_hash: str
    retained_bytes: int
    component_hashes: Mapping[str, str]
    forbidden_state_audit: Mapping[str, bool]
    prior_library_hash: str | None

    def __post_init__(self) -> None:
        if self.generation not in {1, 2, 3}:
            raise ContractError("Generation must be 1, 2, or 3.")
        if self.retained_bytes < 0:
            raise ContractError("retained_bytes cannot be negative.")
        if not all(self.forbidden_state_audit.values()):
            raise ContractError("Participant state failed a forbidden-state audit.")


@dataclass(frozen=True)
class GovernanceComponent:
    """One explicitly defined component of the active eta_t tuple."""

    symbol: str
    semantic_name: str
    definition: str
    value_type: str
    value: Any
    bounds: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.definition or not self.value_type:
            raise ContractError(f"Component {self.symbol} lacks typed semantics.")


ACTIVE_CONFIGURATION_SEMANTICS: Mapping[str, tuple[str, str]] = {
    "G_t": ("governance_graph", "Approved governance decision graph and ordering."),
    "A_t": ("aggregation_rule", "Approved specialist/evidence aggregation rule."),
    "W_t": ("specialist_weights", "Bounded specialist and evidence weights."),
    "P_t": ("policy_state", "Approved policy clauses and cost preferences."),
    "Theta_t": ("diagnostic_parameters", "Certified diagnostic parameter set."),
    "tau_hard_t": ("hard_veto_threshold", "Certified danger threshold for hard veto."),
    "alpha_t": ("mitigation_bound", "Maximum certified mitigating influence."),
    "lambda_t": ("burden_tradeoff", "Escalation and intervention cost weight."),
    "delta_t": ("decision_margin", "Required accept/reject decision margin."),
    "theta_0_t": ("base_threshold", "Base governance threshold before diagnostics."),
    "tau_G_t": ("selector_fallback_threshold", "Applicability threshold below which fallback applies."),
    "S_t": ("governed_selector", "Approved selector over certified configurations."),
}


@dataclass(frozen=True)
class ActiveGovernanceConfiguration:
    config_id: str
    parent_config_id: str | None
    version: str
    approval_status: Literal["approved", "proposed", "quarantined", "rolled_back"]
    activation_scope: Mapping[str, Any]
    omega_scope_policy: Mapping[str, Any]
    G_t: GovernanceComponent
    A_t: GovernanceComponent
    W_t: GovernanceComponent
    P_t: GovernanceComponent
    Theta_t: GovernanceComponent
    tau_hard_t: GovernanceComponent
    alpha_t: GovernanceComponent
    lambda_t: GovernanceComponent
    delta_t: GovernanceComponent
    theta_0_t: GovernanceComponent
    tau_G_t: GovernanceComponent
    S_t: GovernanceComponent
    config_hash: str = field(default="")

    def components(self) -> tuple[GovernanceComponent, ...]:
        return (
            self.G_t,
            self.A_t,
            self.W_t,
            self.P_t,
            self.Theta_t,
            self.tau_hard_t,
            self.alpha_t,
            self.lambda_t,
            self.delta_t,
            self.theta_0_t,
            self.tau_G_t,
            self.S_t,
        )

    def unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("config_hash", None)
        return payload

    def expected_hash(self) -> str:
        return stable_hash(self.unsigned_payload())

    def validate(self, *, require_approved: bool = False) -> None:
        expected_symbols = tuple(ACTIVE_CONFIGURATION_SEMANTICS)
        actual_symbols = tuple(component.symbol for component in self.components())
        if actual_symbols != expected_symbols:
            raise ContractError(
                f"eta_t component order/symbol mismatch: {actual_symbols!r}."
            )
        for component in self.components():
            semantic_name, definition = ACTIVE_CONFIGURATION_SEMANTICS[component.symbol]
            if component.semantic_name != semantic_name or component.definition != definition:
                raise ContractError(f"Semantic mismatch for {component.symbol}.")
        if self.config_hash != self.expected_hash():
            raise ContractError("Active configuration hash mismatch.")
        if require_approved and self.approval_status != "approved":
            raise ContractError("Fast loop may execute only an approved configuration.")


def _unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ContractError(f"{name} must be within [0, 1].")


def active_configuration_from_dict(payload: Mapping[str, Any]) -> ActiveGovernanceConfiguration:
    """Build an active configuration from the explicit YAML/JSON representation."""
    raw_components = payload.get("components")
    if not isinstance(raw_components, Mapping):
        raise ContractError("Active configuration requires a components mapping.")
    components: dict[str, GovernanceComponent] = {}
    for symbol in ACTIVE_CONFIGURATION_SEMANTICS:
        raw = raw_components.get(symbol)
        if not isinstance(raw, Mapping):
            raise ContractError(f"Missing active configuration component {symbol}.")
        components[symbol] = GovernanceComponent(symbol=symbol, **dict(raw))
    base = {
        "config_id": str(payload["config_id"]),
        "parent_config_id": payload.get("parent_config_id"),
        "version": str(payload["version"]),
        "approval_status": str(payload["approval_status"]),
        "activation_scope": dict(payload["activation_scope"]),
        "omega_scope_policy": dict(payload["omega_scope_policy"]),
        **components,
    }
    provisional = ActiveGovernanceConfiguration(**base)
    return ActiveGovernanceConfiguration(**base, config_hash=provisional.expected_hash())
