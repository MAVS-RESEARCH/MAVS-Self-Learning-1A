from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Literal

Decision = Literal["accept", "reject", "escalate", "defer"]

MAVS_TRACE_FIELD_NAMES: tuple[str, ...] = (
    "specialist_id",
    "representation_hash",
    "support_score",
    "confidence",
    "source",
    "corruption_exposure",
    "diagnostic_values",
    "disagreement",
    "consistency",
    "missing_evidence",
    "policy_conflict",
    "corruption_signal",
    "raw_severity",
    "normalized_severity",
    "severity_contribution_breakdown",
    "base_threshold",
    "threshold_delta",
    "final_threshold",
    "escalation_reason",
    "fallback_action",
)


@dataclass(frozen=True)
class Observation:
    episode_id: str
    t: int
    visible_state: dict[str, Any]
    prompt: str | None
    risk_context: dict[str, Any]
    corruption_hint: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        return cls(
            episode_id=str(data["episode_id"]),
            t=int(data["t"]),
            visible_state=dict(data.get("visible_state", {})),
            prompt=data.get("prompt"),
            risk_context=dict(data.get("risk_context", {})),
            corruption_hint=(
                dict(data["corruption_hint"])
                if data.get("corruption_hint") is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class CandidateAction:
    action_type: str
    content: str
    confidence: float
    specialist_outputs: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateAction":
        return cls(
            action_type=str(data["action_type"]),
            content=str(data["content"]),
            confidence=float(data["confidence"]),
            specialist_outputs=dict(data.get("specialist_outputs", {})),
            provenance=dict(data.get("provenance", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class GovernanceDecision:
    decision: Decision
    risk_score: float
    severity: float
    rationale: str
    triggered_checks: list[str]
    threshold: float
    trace: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GovernanceDecision":
        decision = str(data["decision"])
        if decision not in {"accept", "reject", "escalate", "defer"}:
            raise ValueError(f"Unsupported governance decision: {decision}")
        return cls(
            decision=decision,  # type: ignore[arg-type]
            risk_score=float(data["risk_score"]),
            severity=float(data["severity"]),
            rationale=str(data["rationale"]),
            triggered_checks=list(data.get("triggered_checks", [])),
            threshold=float(data["threshold"]),
            trace=dict(data.get("trace", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class StepResult:
    next_observation: Observation
    reward: float
    unsafe_accepted: bool
    false_rejected: bool
    done: bool
    info: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepResult":
        return cls(
            next_observation=Observation.from_dict(data["next_observation"]),
            reward=float(data["reward"]),
            unsafe_accepted=bool(data["unsafe_accepted"]),
            false_rejected=bool(data["false_rejected"]),
            done=bool(data["done"]),
            info=dict(data.get("info", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class EpisodeTrace:
    run_id: str
    config_hash: str
    git_commit: str | None
    environment_id: str
    method_id: str
    seed: int
    episode_id: str
    step_id: int
    observation: Observation
    candidate: CandidateAction
    decision: GovernanceDecision
    step_result: StepResult
    hidden_label_hash: str
    trace_complete: bool
    created_at_utc: str
    metadata: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodeTrace":
        return cls(
            run_id=str(data["run_id"]),
            config_hash=str(data["config_hash"]),
            git_commit=data.get("git_commit"),
            environment_id=str(data["environment_id"]),
            method_id=str(data["method_id"]),
            seed=int(data["seed"]),
            episode_id=str(data["episode_id"]),
            step_id=int(data["step_id"]),
            observation=Observation.from_dict(data["observation"]),
            candidate=CandidateAction.from_dict(data["candidate"]),
            decision=GovernanceDecision.from_dict(data["decision"]),
            step_result=StepResult.from_dict(data["step_result"]),
            hidden_label_hash=str(data["hidden_label_hash"]),
            trace_complete=bool(data["trace_complete"]),
            created_at_utc=str(data["created_at_utc"]),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def mavs_trace_template() -> dict[str, Any]:
    return {field: None for field in MAVS_TRACE_FIELD_NAMES}


def trace_supports_mavs_fields(trace: dict[str, Any]) -> bool:
    return all(field in trace for field in MAVS_TRACE_FIELD_NAMES)

