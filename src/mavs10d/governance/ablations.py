from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from mavs10d.baselines.common import clamp
from mavs10d.core.hashing import stable_hash
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import Observation
from mavs10d.governance.escalation import DecisionFunctionalResult
from mavs10d.governance.severity import SeverityResult
from mavs10d.governance.thresholds import ThresholdResult, compute_threshold


REQUIRED_ABLATION_NAMES: tuple[str, ...] = (
    "full_mavs_gc",
    "no_severity",
    "fixed_severity",
    "noisy_severity",
    "no_diagnostics",
    "single_diagnostic_only",
    "randomized_diagnostic",
    "fixed_threshold",
    "delayed_threshold",
    "over_sensitive_threshold",
    "homogeneous_specialists",
    "heterogeneous_specialists",
    "shared_representation",
    "reject_only_fallback",
    "accept_reject_only_no_escalation",
    "no_escalation",
)


@dataclass(frozen=True)
class AblationConfig:
    name: str = "full_mavs_gc"
    severity_mode: str = "normal"
    diagnostics_mode: str = "normal"
    threshold_policy: str = "adaptive"
    specialist_bank: str = "heterogeneous"
    escalation_policy: str = "normal"
    representation_sharing: str = "normal"
    noise_injection: str = "none"
    single_diagnostic: str | None = None
    fixed_severity: float = 0.35
    diagnostic_noise: float = 0.10
    severity_noise: float = 0.10
    threshold_delay_steps: int = 3
    over_sensitive_multiplier: float = 2.0

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> "AblationConfig":
        # console.log: phase5.ablations.config.from_params
        console_log("phase5.ablations.config.from_params", params=params)
        if not params:
            return cls()
        if "name" in params and len(params) == 1:
            return named_ablation(str(params["name"]))
        return cls(
            name=str(params.get("name", "custom_ablation")),
            severity_mode=str(params.get("severity_mode", "normal")),
            diagnostics_mode=str(params.get("diagnostics_mode", "normal")),
            threshold_policy=str(params.get("threshold_policy", "adaptive")),
            specialist_bank=str(params.get("specialist_bank", "heterogeneous")),
            escalation_policy=str(params.get("escalation_policy", "normal")),
            representation_sharing=str(params.get("representation_sharing", "normal")),
            noise_injection=str(params.get("noise_injection", "none")),
            single_diagnostic=(
                str(params["single_diagnostic"])
                if params.get("single_diagnostic") is not None
                else None
            ),
            fixed_severity=float(params.get("fixed_severity", 0.35)),
            diagnostic_noise=float(params.get("diagnostic_noise", 0.10)),
            severity_noise=float(params.get("severity_noise", 0.10)),
            threshold_delay_steps=int(params.get("threshold_delay_steps", 3)),
            over_sensitive_multiplier=float(params.get("over_sensitive_multiplier", 2.0)),
        )

    def apply_diagnostics(
        self,
        diagnostics: dict[str, float],
        *,
        obs: Observation,
        seed: int,
    ) -> dict[str, float]:
        # console.log: phase5.ablations.apply_diagnostics.start
        console_log(
            "phase5.ablations.apply_diagnostics.start",
            ablation=self.name,
            diagnostics_mode=self.diagnostics_mode,
            t=obs.t,
        )
        adjusted = dict(diagnostics)
        if self.diagnostics_mode == "no_diagnostics":
            adjusted = {key: 0.0 for key in adjusted}
        elif self.diagnostics_mode == "single_diagnostic_only":
            selected = self.single_diagnostic or "policy_conflict"
            adjusted = {key: value if key == selected else 0.0 for key, value in adjusted.items()}
        elif self.diagnostics_mode == "randomized_diagnostic":
            rng = self._rng(seed, obs.t, "randomized_diagnostic")
            adjusted = {key: rng.random() for key in adjusted}
        if self.noise_injection == "diagnostic_noise":
            rng = self._rng(seed, obs.t, "diagnostic_noise")
            adjusted = {
                key: clamp(value + rng.uniform(-self.diagnostic_noise, self.diagnostic_noise))
                for key, value in adjusted.items()
            }
        # console.log: phase5.ablations.apply_diagnostics.complete
        console_log(
            "phase5.ablations.apply_diagnostics.complete",
            ablation=self.name,
            diagnostics=adjusted,
        )
        return adjusted

    def apply_severity(
        self,
        severity: SeverityResult,
        *,
        obs: Observation,
        seed: int,
    ) -> SeverityResult:
        # console.log: phase5.ablations.apply_severity.start
        console_log(
            "phase5.ablations.apply_severity.start",
            ablation=self.name,
            severity_mode=self.severity_mode,
            t=obs.t,
        )
        if self.severity_mode == "no_severity":
            result = SeverityResult(0.0, 0.0, {"ablation_no_severity": 0.0})
        elif self.severity_mode == "fixed_severity":
            fixed = clamp(self.fixed_severity)
            result = SeverityResult(fixed, fixed, {"ablation_fixed_severity": fixed})
        elif self.severity_mode == "noisy_severity":
            rng = self._rng(seed, obs.t, "noisy_severity")
            noisy = clamp(severity.normalized_severity + rng.uniform(-self.severity_noise, self.severity_noise))
            result = SeverityResult(
                raw_severity=noisy,
                normalized_severity=noisy,
                contribution_breakdown={
                    **severity.contribution_breakdown,
                    "ablation_severity_noise": noisy - severity.normalized_severity,
                },
            )
        else:
            result = severity
        # console.log: phase5.ablations.apply_severity.complete
        console_log(
            "phase5.ablations.apply_severity.complete",
            ablation=self.name,
            normalized_severity=result.normalized_severity,
        )
        return result

    def apply_weights(self, weights: dict[str, float]) -> dict[str, float]:
        # console.log: phase5.ablations.apply_weights
        console_log(
            "phase5.ablations.apply_weights",
            ablation=self.name,
            specialist_bank=self.specialist_bank,
        )
        if self.specialist_bank == "homogeneous" and weights:
            equal = 1.0 / len(weights)
            return {key: equal for key in weights}
        return weights

    def compute_threshold(
        self,
        *,
        obs: Observation,
        base_threshold: float,
        severity: float,
        mitigation_strength: float,
        hard_veto: bool,
        severity_sensitivity: float,
        max_mitigation_relaxation: float,
    ) -> ThresholdResult:
        # console.log: phase5.ablations.compute_threshold.start
        console_log(
            "phase5.ablations.compute_threshold.start",
            ablation=self.name,
            threshold_policy=self.threshold_policy,
            t=obs.t,
        )
        effective_severity = severity
        effective_sensitivity = severity_sensitivity
        if self.threshold_policy == "fixed":
            result = ThresholdResult(
                base_threshold=base_threshold,
                threshold_delta=0.0,
                final_threshold=base_threshold,
                mitigation_relaxation=0.0,
                hard_veto_applied=hard_veto,
            )
        else:
            if self.threshold_policy == "delayed" and obs.t < self.threshold_delay_steps:
                effective_severity = 0.0
            if self.threshold_policy == "over_sensitive":
                effective_sensitivity = severity_sensitivity * self.over_sensitive_multiplier
            result = compute_threshold(
                base_threshold=base_threshold,
                severity=effective_severity,
                mitigation_strength=mitigation_strength,
                hard_veto=hard_veto,
                severity_sensitivity=effective_sensitivity,
                max_mitigation_relaxation=max_mitigation_relaxation,
            )
        # console.log: phase5.ablations.compute_threshold.complete
        console_log(
            "phase5.ablations.compute_threshold.complete",
            ablation=self.name,
            final_threshold=result.final_threshold,
            threshold_delta=result.threshold_delta,
        )
        return result

    def apply_decision_policy(
        self,
        result: DecisionFunctionalResult,
        *,
        threshold: float,
    ) -> DecisionFunctionalResult:
        # console.log: phase5.ablations.apply_decision_policy.start
        console_log(
            "phase5.ablations.apply_decision_policy.start",
            ablation=self.name,
            escalation_policy=self.escalation_policy,
            decision=result.decision,
        )
        adjusted = result
        if self.escalation_policy == "reject_only_fallback" and result.decision == "escalate":
            adjusted = DecisionFunctionalResult(
                decision="reject",
                risk_score=result.risk_score,
                triggered_checks=[*result.triggered_checks, "ablation_reject_only_fallback"],
                escalation_reason=None,
                fallback_action="reject_only_fallback",
            )
        elif self.escalation_policy == "accept_reject_only_no_escalation" and result.decision == "escalate":
            decision = "reject" if result.risk_score >= threshold else "accept"
            adjusted = DecisionFunctionalResult(
                decision=decision,
                risk_score=result.risk_score,
                triggered_checks=[*result.triggered_checks, "ablation_accept_reject_only"],
                escalation_reason=None,
                fallback_action="accept_reject_only_no_escalation",
            )
        elif self.escalation_policy == "no_escalation" and result.decision == "escalate":
            adjusted = DecisionFunctionalResult(
                decision="accept",
                risk_score=result.risk_score,
                triggered_checks=[*result.triggered_checks, "ablation_no_escalation"],
                escalation_reason=None,
                fallback_action="no_escalation_accept",
            )
        # console.log: phase5.ablations.apply_decision_policy.complete
        console_log(
            "phase5.ablations.apply_decision_policy.complete",
            ablation=self.name,
            decision=adjusted.decision,
        )
        return adjusted

    def representation_payload(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # console.log: phase5.ablations.representation_payload
        console_log(
            "phase5.ablations.representation_payload",
            ablation=self.name,
            representation_sharing=self.representation_sharing,
        )
        if self.representation_sharing == "shared":
            shared_payload = dict(payload)
            candidate = dict(shared_payload.get("candidate", {}))
            candidate.pop("specialist_outputs", None)
            shared_payload["candidate"] = candidate
            shared_payload["representation_sharing"] = "shared"
            return shared_payload
        return payload

    def trace_details(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity_mode": self.severity_mode,
            "diagnostics_mode": self.diagnostics_mode,
            "threshold_policy": self.threshold_policy,
            "specialist_bank": self.specialist_bank,
            "escalation_policy": self.escalation_policy,
            "representation_sharing": self.representation_sharing,
            "noise_injection": self.noise_injection,
            "single_diagnostic": self.single_diagnostic,
        }

    def _rng(self, seed: int, t: int, salt: str) -> random.Random:
        derived = int(stable_hash({"seed": seed, "t": t, "salt": salt, "ablation": self.name})[:12], 16)
        return random.Random(derived)


def named_ablation(name: str) -> AblationConfig:
    # console.log: phase5.ablations.named
    console_log("phase5.ablations.named", name=name)
    mapping = {
        "full_mavs_gc": AblationConfig(name="full_mavs_gc"),
        "no_severity": AblationConfig(name="no_severity", severity_mode="no_severity"),
        "fixed_severity": AblationConfig(name="fixed_severity", severity_mode="fixed_severity"),
        "noisy_severity": AblationConfig(
            name="noisy_severity",
            severity_mode="noisy_severity",
            noise_injection="severity_noise",
        ),
        "no_diagnostics": AblationConfig(name="no_diagnostics", diagnostics_mode="no_diagnostics"),
        "single_diagnostic_only": AblationConfig(
            name="single_diagnostic_only",
            diagnostics_mode="single_diagnostic_only",
            single_diagnostic="policy_conflict",
        ),
        "randomized_diagnostic": AblationConfig(
            name="randomized_diagnostic",
            diagnostics_mode="randomized_diagnostic",
            noise_injection="diagnostic_noise",
        ),
        "fixed_threshold": AblationConfig(name="fixed_threshold", threshold_policy="fixed"),
        "delayed_threshold": AblationConfig(name="delayed_threshold", threshold_policy="delayed"),
        "over_sensitive_threshold": AblationConfig(
            name="over_sensitive_threshold",
            threshold_policy="over_sensitive",
        ),
        "homogeneous_specialists": AblationConfig(
            name="homogeneous_specialists",
            specialist_bank="homogeneous",
        ),
        "heterogeneous_specialists": AblationConfig(
            name="heterogeneous_specialists",
            specialist_bank="heterogeneous",
        ),
        "shared_representation": AblationConfig(
            name="shared_representation",
            representation_sharing="shared",
        ),
        "reject_only_fallback": AblationConfig(
            name="reject_only_fallback",
            escalation_policy="reject_only_fallback",
        ),
        "accept_reject_only_no_escalation": AblationConfig(
            name="accept_reject_only_no_escalation",
            escalation_policy="accept_reject_only_no_escalation",
        ),
        "no_escalation": AblationConfig(name="no_escalation", escalation_policy="no_escalation"),
    }
    try:
        return mapping[name]
    except KeyError as exc:
        raise ValueError(f"Unknown MAVS ablation: {name}") from exc


def phase5_ablation_method_configs() -> list[dict[str, Any]]:
    # console.log: phase5.ablations.method_configs
    console_log("phase5.ablations.method_configs", count=len(REQUIRED_ABLATION_NAMES))
    return [
        {
            "id": f"mavs_gc_{name}",
            "type": "mavs_gc",
            "params": {"ablation": {"name": name}},
        }
        for name in REQUIRED_ABLATION_NAMES
    ]

