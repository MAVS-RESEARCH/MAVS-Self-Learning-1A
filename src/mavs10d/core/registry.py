from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable

from mavs10d.core.config import EnvironmentConfig, MethodConfig
from mavs10d.core.hashing import stable_hash
from mavs10d.core.interfaces import DynamicGovernanceEnv, GovernanceMethod
from mavs10d.core.types import (
    CandidateAction,
    GovernanceDecision,
    Observation,
    StepResult,
    mavs_trace_template,
)

EnvironmentFactory = Callable[[EnvironmentConfig], DynamicGovernanceEnv]
MethodFactory = Callable[[MethodConfig], GovernanceMethod]
ComponentFactory = Callable[[dict[str, Any]], Any]


class ComponentRegistry:
    def __init__(self) -> None:
        self._environments: dict[str, EnvironmentFactory] = {}
        self._methods: dict[str, MethodFactory] = {}
        self._baselines: dict[str, MethodFactory] = {}
        self._corruption_schedules: dict[str, ComponentFactory] = {}
        self._specialists: dict[str, ComponentFactory] = {}
        self._metrics: dict[str, ComponentFactory] = {}
        self._report_builders: dict[str, ComponentFactory] = {}

    def register_environment(
        self, component_type: str, factory: EnvironmentFactory
    ) -> None:
        if component_type in self._environments:
            raise ValueError(f"Environment already registered: {component_type}")
        self._environments[component_type] = factory

    def register_method(self, component_type: str, factory: MethodFactory) -> None:
        if component_type in self._methods:
            raise ValueError(f"Method already registered: {component_type}")
        self._methods[component_type] = factory

    def register_baseline(self, component_type: str, factory: MethodFactory) -> None:
        if component_type in self._baselines:
            raise ValueError(f"Baseline already registered: {component_type}")
        self._baselines[component_type] = factory

    def register_corruption_schedule(
        self, component_type: str, factory: ComponentFactory
    ) -> None:
        if component_type in self._corruption_schedules:
            raise ValueError(
                f"Corruption schedule already registered: {component_type}"
            )
        self._corruption_schedules[component_type] = factory

    def register_specialist(
        self, component_type: str, factory: ComponentFactory
    ) -> None:
        if component_type in self._specialists:
            raise ValueError(f"Specialist already registered: {component_type}")
        self._specialists[component_type] = factory

    def register_metric(self, component_type: str, factory: ComponentFactory) -> None:
        if component_type in self._metrics:
            raise ValueError(f"Metric already registered: {component_type}")
        self._metrics[component_type] = factory

    def register_report_builder(
        self, component_type: str, factory: ComponentFactory
    ) -> None:
        if component_type in self._report_builders:
            raise ValueError(f"Report builder already registered: {component_type}")
        self._report_builders[component_type] = factory

    def create_environment(self, config: EnvironmentConfig) -> DynamicGovernanceEnv:
        try:
            factory = self._environments[config.type]
        except KeyError as exc:
            raise KeyError(f"Unknown environment type: {config.type}") from exc
        return factory(config)

    def create_method(self, config: MethodConfig) -> GovernanceMethod:
        try:
            factory = self._methods[config.type]
        except KeyError as exc:
            raise KeyError(f"Unknown governance method type: {config.type}") from exc
        return factory(config)

    def create_baseline(self, config: MethodConfig) -> GovernanceMethod:
        try:
            factory = self._baselines[config.type]
        except KeyError as exc:
            raise KeyError(f"Unknown baseline type: {config.type}") from exc
        return factory(config)

    def create_corruption_schedule(
        self, component_type: str, params: dict[str, Any] | None = None
    ) -> Any:
        return self._create_generic(
            self._corruption_schedules,
            "corruption schedule",
            component_type,
            params,
        )

    def create_specialist(
        self, component_type: str, params: dict[str, Any] | None = None
    ) -> Any:
        return self._create_generic(
            self._specialists,
            "specialist",
            component_type,
            params,
        )

    def create_metric(
        self, component_type: str, params: dict[str, Any] | None = None
    ) -> Any:
        return self._create_generic(self._metrics, "metric", component_type, params)

    def create_report_builder(
        self, component_type: str, params: dict[str, Any] | None = None
    ) -> Any:
        return self._create_generic(
            self._report_builders,
            "report builder",
            component_type,
            params,
        )

    def environment_types(self) -> list[str]:
        return sorted(self._environments)

    def method_types(self) -> list[str]:
        return sorted(self._methods)

    def baseline_types(self) -> list[str]:
        return sorted(self._baselines)

    def corruption_schedule_types(self) -> list[str]:
        return sorted(self._corruption_schedules)

    def specialist_types(self) -> list[str]:
        return sorted(self._specialists)

    def metric_types(self) -> list[str]:
        return sorted(self._metrics)

    def report_builder_types(self) -> list[str]:
        return sorted(self._report_builders)

    def _create_generic(
        self,
        registry: dict[str, ComponentFactory],
        category_name: str,
        component_type: str,
        params: dict[str, Any] | None,
    ) -> Any:
        try:
            factory = registry[component_type]
        except KeyError as exc:
            raise KeyError(f"Unknown {category_name} type: {component_type}") from exc
        return factory(dict(params or {}))


@dataclass
class SyntheticSmokeEnv:
    config: EnvironmentConfig

    def __post_init__(self) -> None:
        self.environment_id = self.config.id
        self.episode_steps = int(self.config.params.get("episode_steps", 4))
        self._rng = random.Random(0)
        self._seed = 0
        self._t = 0
        self._episode_id = "uninitialized"
        self._current_unsafe = False

    def reset(self, seed: int) -> Observation:
        self._seed = int(seed)
        self._rng = random.Random(self._seed)
        self._t = 0
        self._episode_id = f"synthetic_smoke_seed_{self._seed}"
        self._current_unsafe = self._is_unsafe(self._t)
        return self._observation()

    def propose_candidate(self, obs: Observation) -> CandidateAction:
        risk_proxy = 0.85 if self._current_unsafe else 0.15
        confidence = 1.0 - risk_proxy * 0.35
        return CandidateAction(
            action_type="synthetic_response",
            content=f"synthetic candidate seed={self._seed} step={obs.t}",
            confidence=confidence,
            specialist_outputs={
                "smoke_specialist_a": {
                    "score": 1.0 - risk_proxy,
                    "confidence": confidence,
                },
                "smoke_specialist_b": {
                    "score": 0.95 - risk_proxy * 0.8,
                    "confidence": confidence,
                },
            },
            provenance={
                "generator": "SyntheticSmokeEnv",
                "hidden_risk_proxy": risk_proxy,
                "seed": self._seed,
                "step": obs.t,
            },
        )

    def step(self, decision: GovernanceDecision) -> StepResult:
        was_unsafe = self._current_unsafe
        unsafe_accepted = was_unsafe and decision.decision == "accept"
        false_rejected = (not was_unsafe) and decision.decision == "reject"
        reward = 1.0 if not unsafe_accepted and not false_rejected else -1.0
        self._t += 1
        done = self._t >= self.episode_steps
        self._current_unsafe = self._is_unsafe(self._t)
        next_obs = self._observation()
        return StepResult(
            next_observation=next_obs,
            reward=reward,
            unsafe_accepted=unsafe_accepted,
            false_rejected=false_rejected,
            done=done,
            info={
                "expected_decision": "reject" if was_unsafe else "accept",
                "phase": "phase1_smoke",
            },
        )

    def hidden_labels(self) -> dict[str, Any]:
        return {
            "episode_id": self._episode_id,
            "t": self._t,
            "unsafe": self._current_unsafe,
            "expected_safe_action": "reject" if self._current_unsafe else "accept",
        }

    def _is_unsafe(self, t: int) -> bool:
        return ((self._seed + t) % 3) == 0

    def _observation(self) -> Observation:
        return Observation(
            episode_id=self._episode_id,
            t=self._t,
            visible_state={
                "stream_position": self._t,
                "episode_steps": self.episode_steps,
            },
            prompt=f"synthetic smoke prompt step {self._t}",
            risk_context={
                "environment": "phase1_smoke",
                "risk_family": "synthetic_governance_contract",
            },
            corruption_hint=None,
        )


@dataclass
class RiskThresholdMethod:
    config: MethodConfig

    def __post_init__(self) -> None:
        self.method_id = self.config.id
        self.threshold = float(self.config.params.get("threshold", 0.5))
        self._seed = 0

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(
        self, obs: Observation, candidate: CandidateAction
    ) -> GovernanceDecision:
        risk = float(candidate.provenance.get("hidden_risk_proxy", 1 - candidate.confidence))
        decision = "reject" if risk >= self.threshold else "accept"
        trace = mavs_trace_template()
        trace.update(
            {
                "specialist_id": list(candidate.specialist_outputs),
                "representation_hash": stable_hash(
                    {
                        "obs": obs.visible_state,
                        "candidate": candidate.content,
                        "seed": self._seed,
                    }
                ),
                "support_score": 1.0 - risk,
                "confidence": candidate.confidence,
                "source": candidate.provenance.get("generator", "unknown"),
                "corruption_exposure": obs.corruption_hint,
                "diagnostic_values": {"risk_proxy": risk},
                "disagreement": 0.0,
                "consistency": 1.0,
                "missing_evidence": 0.0,
                "policy_conflict": risk,
                "corruption_signal": 0.0,
                "raw_severity": risk,
                "normalized_severity": risk,
                "severity_contribution_breakdown": {"risk_proxy": risk},
                "base_threshold": self.threshold,
                "threshold_delta": 0.0,
                "final_threshold": self.threshold,
                "escalation_reason": None,
                "fallback_action": None,
            }
        )
        return GovernanceDecision(
            decision=decision,  # type: ignore[arg-type]
            risk_score=risk,
            severity=risk,
            rationale="phase1 deterministic risk-threshold smoke method",
            triggered_checks=["risk_proxy_threshold"] if decision == "reject" else [],
            threshold=self.threshold,
            trace=trace,
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        return None


def build_default_registry() -> ComponentRegistry:
    from mavs10d.baselines.confidence_gate import ConfidenceGateBaseline
    from mavs10d.baselines.conformal import (
        AdaptiveConformalBaseline,
        ConformalAbstentionBaseline,
    )
    from mavs10d.baselines.critique_revise import CritiqueReviseBaseline
    from mavs10d.baselines.debate import DebateBaseline
    from mavs10d.baselines.disagreement_gate import DisagreementGateBaseline
    from mavs10d.baselines.judge import JudgeBaseline
    from mavs10d.baselines.policy_rails import PolicyRailBaseline
    from mavs10d.baselines.reject_option import RejectOptionBaseline
    from mavs10d.baselines.sanity import AlwaysAcceptBaseline, AlwaysRejectBaseline
    from mavs10d.baselines.self_consistency import SelfConsistencyBaseline
    from mavs10d.baselines.validator_stack import ValidatorStackBaseline
    from mavs10d.corruption.schedules import build_schedule_from_config
    from mavs10d.envs.correlated_collapse_env import CorrelatedCollapseEnv
    from mavs10d.envs.cyber_triage_env import CyberTriageEnv
    from mavs10d.envs.multi_agent_env import MultiAgentOperationsEnv
    from mavs10d.envs.static_accuracy_adapter import StaticAccuracyAdapterEnv
    from mavs10d.envs.synthetic_ops_env import SyntheticOpsEnv
    from mavs10d.envs.text_safety_env import TextSafetyStreamEnv
    from mavs10d.envs.tool_use_env import ToolUseSecurityEnv
    from mavs10d.governance.mavs_gc import MAVSGovernance
    from mavs10d.specialists.heuristic import HeuristicSpecialistBank

    registry = ComponentRegistry()
    registry.register_environment(
        "synthetic_smoke",
        lambda config: SyntheticSmokeEnv(config),
    )
    registry.register_environment(
        "text_safety_stream",
        lambda config: TextSafetyStreamEnv(config),
    )
    registry.register_environment(
        "tool_use_security",
        lambda config: ToolUseSecurityEnv(config),
    )
    registry.register_environment(
        "cyber_triage",
        lambda config: CyberTriageEnv(config),
    )
    registry.register_environment(
        "multi_agent_operations",
        lambda config: MultiAgentOperationsEnv(config),
    )
    registry.register_environment(
        "synthetic_ops",
        lambda config: SyntheticOpsEnv(config),
    )
    registry.register_environment(
        "correlated_representation_collapse",
        lambda config: CorrelatedCollapseEnv(config),
    )
    registry.register_environment(
        "static_accuracy_adapter",
        lambda config: StaticAccuracyAdapterEnv(config),
    )
    registry.register_method(
        "risk_threshold",
        lambda config: RiskThresholdMethod(config),
    )
    registry.register_method(
        "mavs_gc",
        lambda config: MAVSGovernance(config),
    )
    baseline_factories = {
        "policy_rails": lambda config: PolicyRailBaseline(config),
        "validator_stack": lambda config: ValidatorStackBaseline(config),
        "confidence_gate": lambda config: ConfidenceGateBaseline(config),
        "disagreement_gate": lambda config: DisagreementGateBaseline(config),
        "self_consistency": lambda config: SelfConsistencyBaseline(config),
        "conformal_static": lambda config: ConformalAbstentionBaseline(config),
        "conformal_adaptive": lambda config: AdaptiveConformalBaseline(config),
        "reject_option": lambda config: RejectOptionBaseline(config),
        "judge": lambda config: JudgeBaseline(config),
        "debate": lambda config: DebateBaseline(config),
        "critique_revise": lambda config: CritiqueReviseBaseline(config),
        "always_accept": lambda config: AlwaysAcceptBaseline(config),
        "always_reject": lambda config: AlwaysRejectBaseline(config),
    }
    for baseline_type, factory in baseline_factories.items():
        registry.register_method(baseline_type, factory)
        registry.register_baseline(baseline_type, factory)
    registry.register_corruption_schedule(
        "piecewise",
        lambda params: build_schedule_from_config({"type": "piecewise", **params}),
    )
    registry.register_corruption_schedule(
        "sweep",
        lambda params: build_schedule_from_config({"type": "sweep", **params}),
    )
    registry.register_specialist(
        "heuristic_bank",
        lambda params: HeuristicSpecialistBank.from_params(params),
    )
    return registry
