from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mavs10d.core.trace_logging import console_log
from mavs10d.specialists.base import SpecialistOutput, clamp_score


@dataclass(frozen=True)
class SmallLMConfig:
    model_name: str
    revision: str
    parameter_count_b: float
    quantization: str
    device: str
    enabled: bool = False

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> "SmallLMConfig":
        # console.log: phase5.specialists.small_lm.config.from_params
        console_log("phase5.specialists.small_lm.config.from_params", params=params)
        config = cls(
            model_name=str(params.get("model_name", "unconfigured")),
            revision=str(params.get("revision", "unconfigured")),
            parameter_count_b=float(params.get("parameter_count_b", 0.0)),
            quantization=str(params.get("quantization", "none")),
            device=str(params.get("device", "cpu")),
            enabled=bool(params.get("enabled", False)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        # console.log: phase5.specialists.small_lm.config.validate
        console_log(
            "phase5.specialists.small_lm.config.validate",
            model_name=self.model_name,
            enabled=self.enabled,
        )
        if not self.enabled:
            return
        if not 1.0 <= self.parameter_count_b <= 3.0:
            raise ValueError("optional local model must be a 1B-3B instruction model")
        if self.quantization == "none":
            raise ValueError("optional local model must declare quantization")
        if self.revision == "unconfigured":
            raise ValueError("optional local model must declare exact revision")


@dataclass(frozen=True)
class SmallLMPlaceholderSpecialist:
    specialist_id: str
    config: SmallLMConfig

    def evaluate(self, scenario: dict[str, Any]) -> SpecialistOutput:
        # console.log: phase5.specialists.small_lm.evaluate
        console_log(
            "phase5.specialists.small_lm.evaluate",
            specialist_id=self.specialist_id,
            enabled=self.config.enabled,
            t=scenario.get("t"),
        )
        if not self.config.enabled:
            return SpecialistOutput(
                specialist_id=self.specialist_id,
                score=0.5,
                confidence=0.0,
                source="small_lm_placeholder_disabled",
                rationale="optional small local model mode is disabled in Phase 5",
                metadata={
                    "enabled": False,
                    "model_name": self.config.model_name,
                    "revision": self.config.revision,
                    "quantization": self.config.quantization,
                    "device": self.config.device,
                },
            )
        risk = float(scenario.get("risk_score", 0.0))
        return SpecialistOutput(
            specialist_id=self.specialist_id,
            score=clamp_score(1.0 - risk),
            confidence=0.50,
            source="small_lm_placeholder_enabled_metadata_only",
            rationale="metadata-only local model placeholder; no inference implementation in Phase 5",
            metadata={
                "enabled": True,
                "model_name": self.config.model_name,
                "revision": self.config.revision,
                "quantization": self.config.quantization,
                "device": self.config.device,
            },
        )

